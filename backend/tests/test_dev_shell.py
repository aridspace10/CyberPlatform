"""Cross-command integration coverage for the development console adapter."""

import subprocess
import sys
import time
from pathlib import Path

import pytest
from game.command_contract import (
    COMMAND_CONTRACTS,
    COMMAND_EXAMPLES,
    format_command_help,
)
from game.dev_shell import DevShell, repl, run_line

LAUNCHER = Path(__file__).resolve().parents[2] / "run_shell.py"


def run_console(console_workdir, *args, input_text=""):
    return subprocess.run(
        [sys.executable, str(LAUNCHER), *args],
        input=input_text,
        capture_output=True,
        text=True,
        cwd=console_workdir,
        timeout=10,
    )


def test_interactive_session_preserves_files_directory_and_pipes(console_workdir):
    result = run_console(
        console_workdir,
        "--empty",
        input_text=(
            "mkdir -p work/demo\ncd work/demo\necho hello > example.txt\n"
            "cat example.txt | grep hello\npwd\n:exit\n"
        ),
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert "cyber:/work/demo$ hello\n" in result.stdout
    assert "cyber:/work/demo$ /work/demo\n" in result.stdout
    assert not (console_workdir / "work").exists()
    assert not (console_workdir / "app.db").exists()


def test_foreground_responses_and_heredoc_content_use_the_same_session(console_workdir):
    result = run_console(
        console_workdir,
        "--empty",
        input_text=(
            "cat << EOF > example.txt\nhello\n\n:exit\nEOF\n"
            "cat example.txt\nrm -i example.txt\nn\ncat example.txt\n"
            "rm -i example.txt\ny\nls\n:exit\n"
        ),
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.count("hello\n\n:exit\n") == 2
    assert result.stdout.count("rm: remove regular file 'example.txt'? ") == 2
    assert result.stdout.endswith("cyber:/$ cyber:/$ ")


@pytest.mark.parametrize("empty", [False, True])
def test_reset_restores_starting_state_and_eof_exits(console_workdir, empty):
    result = run_console(
        console_workdir,
        *(["--empty"] if empty else []),
        input_text="mkdir scratch\ncd scratch\necho changed > file.txt\n:reset\nls\n",
    )
    assert result.returncode == 0
    assert result.stderr == ""
    after_reset = result.stdout.split("Fresh filesystem ready.", 1)[1]
    assert "cyber:/$ " in after_reset
    assert "scratch" not in after_reset
    assert "file.txt" not in after_reset
    assert ("notes.txt" in after_reset) is not empty


def test_repeated_commands_keep_state_and_print_status(console_workdir):
    result = run_console(
        console_workdir,
        "--empty",
        "--status",
        "-c",
        "mkdir work",
        "-c",
        "cd work",
        "-c",
        "echo hello > file.txt",
        "-c",
        "cat file.txt",
    )
    assert result.returncode == 0
    assert result.stdout == "hello\n"
    assert result.stderr == "[status=0]\n" * 4


def test_command_mode_returns_engine_failure_status(console_workdir):
    result = run_console(console_workdir, "-c", "missing-command")
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Unknown command given\n"


def test_command_mode_does_not_hang_on_unanswered_prompt(console_workdir):
    result = run_console(console_workdir, "-c", "rm -i notes.txt")
    assert result.returncode == 2
    assert "waiting for input" in result.stderr


def test_command_mode_accepts_responses_as_later_inputs(console_workdir):
    result = run_console(
        console_workdir, "-c", "rm -i notes.txt", "-c", "n", "-c", "cat notes.txt"
    )
    assert result.returncode == 0
    assert result.stdout == "hello world\ntesting command fixes\n"
    assert result.stderr == ""


def test_help_uses_correct_working_directory_and_preserves_newlines(console_workdir):
    result = run_console(console_workdir, "-c", "mkdir --help")
    expected = "".join(format_command_help("mkdir"))
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == expected


def test_documented_command_examples_execute(monkeypatch, capsys):
    console = DevShell(empty=True)
    monkeypatch.setattr("game.dev_shell.time.sleep", lambda _seconds: None)
    assert set(COMMAND_EXAMPLES) == set(console.commandline.commands) == set(
        COMMAND_CONTRACTS
    )
    assert console.shell.fs.add_file("note.txt") == ""
    note = console.shell.fs.get_file("note.txt")
    assert not isinstance(note, str)
    note.set_data(["hello world"])

    for command in console.commandline.commands:
        run_line(console, COMMAND_EXAMPLES[command], False)
        assert console.foreground is None, command
        assert console.last_status == 0, command

    capsys.readouterr()


def test_blank_input_and_error_do_not_end_the_console(console_workdir):
    result = run_console(
        console_workdir,
        input_text="\n   \nmissing-command\n:status\necho recovered\n:exit\n",
    )
    assert result.returncode == 0
    assert result.stderr == "Unknown command given\n"
    assert "cyber:/$ 1\n" in result.stdout
    assert "cyber:/$ recovered\n" in result.stdout


def test_console_waits_for_scheduler_then_accepts_next_command(monkeypatch, capsys):
    console = DevShell(empty=True)
    waits = []
    monkeypatch.setattr("game.dev_shell.time.sleep", waits.append)
    run_line(console, "sleep 2", False)
    assert waits == [1, 1]
    assert console.foreground is None
    assert console.shell.foreground_pid is None
    assert not console.process_manager.events
    run_line(console, "echo ready", False)
    assert capsys.readouterr().out == "ready\n"


def test_launcher_waits_for_real_sleep_before_next_input(console_workdir):
    started = time.monotonic()
    result = run_console(console_workdir, "-c", "sleep 1", "-c", "echo awake")
    assert time.monotonic() - started >= 1
    assert result.returncode == 0
    assert result.stdout == "awake\n"
    assert result.stderr == ""


def test_interrupt_during_wait_returns_control_to_shell(monkeypatch, capsys):
    console = DevShell(empty=True)

    def interrupt(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr("game.dev_shell.time.sleep", interrupt)
    run_line(console, "sleep 100", False)
    assert console.foreground is None
    assert console.last_status == 130
    run_line(console, "echo recovered", False)
    captured = capsys.readouterr()
    assert captured.err == "^C\n"
    assert captured.out == "recovered\n"


def test_sleep_continuation_runs_after_scheduler_tick(monkeypatch, capsys):
    console = DevShell(empty=True)
    monkeypatch.setattr("game.dev_shell.time.sleep", lambda _seconds: None)
    run_line(console, "sleep 1 && echo completed", False)
    assert console.foreground is None
    assert console.last_status == 0
    assert capsys.readouterr().out == "completed\n"


@pytest.mark.parametrize(
    "command",
    [
        "echo before; sleep 1; echo after",
        "echo before && sleep 1 && echo after",
    ],
)
def test_sleep_sequence_retains_output_before_and_after_foreground_job(
    monkeypatch, capsys, command
):
    console = DevShell(empty=True)
    monkeypatch.setattr("game.dev_shell.time.sleep", lambda _seconds: None)

    run_line(console, command, False)

    assert console.foreground is None
    assert console.last_status == 0
    assert capsys.readouterr().out == "before\nafter\n"


def test_sleep_continuation_propagates_following_command_status(monkeypatch, capsys):
    console = DevShell(empty=True)
    monkeypatch.setattr("game.dev_shell.time.sleep", lambda _seconds: None)
    run_line(console, "sleep 1 && missing-command", False)
    assert console.foreground is None
    assert console.last_status == 1
    assert "Unknown command given" in capsys.readouterr().err


def test_interrupt_resumes_failure_conditional(monkeypatch, capsys):
    console = DevShell(empty=True)

    def interrupt(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr("game.dev_shell.time.sleep", interrupt)
    run_line(console, "sleep 100 || echo cancelled", False)
    captured = capsys.readouterr()
    assert captured.out == "cancelled\n"
    assert captured.err == "^C\n"
    assert console.foreground is None
    assert console.last_status == 0


def test_interrupt_during_prompt_discards_pending_input(monkeypatch, capsys):
    console = DevShell(empty=True)
    inputs = iter(
        ["cat << EOF", "unfinished", KeyboardInterrupt(), "echo ready", ":exit"]
    )

    def read_input(_prompt):
        value = next(inputs)
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr("builtins.input", read_input)
    assert repl(console) == 0
    assert console.foreground is None
    captured = capsys.readouterr()
    assert "^C" in captured.err
    assert "ready\n" in captured.out
    assert "unfinished" not in captured.out


def test_engine_exception_shows_traceback_and_allows_recovery(monkeypatch, capsys):
    console = DevShell(empty=True)
    original = console.commandline.enter_command

    def broken_command(_raw, _shell):
        raise ValueError("example command bug")

    monkeypatch.setattr(console.commandline, "enter_command", broken_command)
    run_line(console, "broken", False)
    assert console.last_status == 1
    assert "ValueError: example command bug" in capsys.readouterr().err
    monkeypatch.setattr(console.commandline, "enter_command", original)
    run_line(console, "echo recovered", False)
    assert capsys.readouterr().out == "recovered\n"
