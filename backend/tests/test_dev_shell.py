"""Cross-command integration coverage for the development console adapter."""

import subprocess
import sys
import time
from pathlib import Path

import pytest
from game.dev_shell import DevShell, repl, run_line

LAUNCHER = Path(__file__).resolve().parents[2] / "run_shell.py"


def run_console(tmp_path, *args, input_text=""):
    return subprocess.run(
        [sys.executable, str(LAUNCHER), *args],
        input=input_text,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=10,
    )


def test_interactive_session_preserves_files_directory_and_pipes(tmp_path):
    result = run_console(
        tmp_path,
        "--empty",
        input_text=(
            "mkdir -p work/demo\ncd work/demo\necho hello > example.txt\n"
            "cat example.txt | grep hello\npwd\n:exit\n"
        ),
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert "cyber:/root/work/demo$ hello\n" in result.stdout
    assert "cyber:/root/work/demo$ root/work/demo\n" in result.stdout
    assert not (tmp_path / "work").exists()
    assert not (tmp_path / "app.db").exists()


def test_foreground_responses_and_heredoc_content_use_the_same_session(tmp_path):
    result = run_console(
        tmp_path,
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
    assert result.stdout.endswith("cyber:/root$ cyber:/root$ ")


@pytest.mark.parametrize("empty", [False, True])
def test_reset_restores_starting_state_and_eof_exits(tmp_path, empty):
    result = run_console(
        tmp_path,
        *(["--empty"] if empty else []),
        input_text="mkdir scratch\ncd scratch\necho changed > file.txt\n:reset\nls\n",
    )
    assert result.returncode == 0
    assert result.stderr == ""
    after_reset = result.stdout.split("Fresh filesystem ready.", 1)[1]
    assert "cyber:/root$ " in after_reset
    assert "scratch" not in after_reset
    assert "file.txt" not in after_reset
    assert ("notes.txt" in after_reset) is not empty


def test_repeated_commands_keep_state_and_print_status(tmp_path):
    result = run_console(
        tmp_path,
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


def test_command_mode_returns_engine_failure_status(tmp_path):
    result = run_console(tmp_path, "-c", "missing-command")
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Unknown command given\n"


def test_command_mode_does_not_hang_on_unanswered_prompt(tmp_path):
    result = run_console(tmp_path, "-c", "rm -i notes.txt")
    assert result.returncode == 2
    assert "waiting for input" in result.stderr


def test_command_mode_accepts_responses_as_later_inputs(tmp_path):
    result = run_console(
        tmp_path, "-c", "rm -i notes.txt", "-c", "n", "-c", "cat notes.txt"
    )
    assert result.returncode == 0
    assert result.stdout == "hello world\ntesting command fixes\n"
    assert result.stderr == ""


def test_help_uses_correct_working_directory_and_preserves_newlines(tmp_path):
    result = run_console(tmp_path, "-c", "mkdir --help")
    expected = (LAUNCHER.parent / "static/help/mkdir.txt").read_text()
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == expected.rstrip("\n") + "\n"


def test_blank_input_and_error_do_not_end_the_console(tmp_path):
    result = run_console(
        tmp_path, input_text="\n   \nmissing-command\n:status\necho recovered\n:exit\n"
    )
    assert result.returncode == 0
    assert result.stderr == "Unknown command given\n"
    assert "cyber:/root$ 1\n" in result.stdout
    assert "cyber:/root$ recovered\n" in result.stdout


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


def test_launcher_waits_for_real_sleep_before_next_input(tmp_path):
    started = time.monotonic()
    result = run_console(tmp_path, "-c", "sleep 1", "-c", "echo awake")
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
