import pytest
from game.Scheduler import Scheduler
from tests.command_helpers import assert_command_error_without_mutation, assert_help


def test_ps_dot_paths_do_not_change_filesystem(run_dot_command):
    # ps has no path operands. Its filesystem contract is cwd/tree preservation.
    result = run_dot_command("ps")
    assert result.status == 0
    assert result.stderr == []


def test_ps_help(cl, shell_empty):
    assert_help(cl, shell_empty, "ps")


def test_ps_missing_option_value_returns_command_error(cl, shell_empty):
    result = assert_command_error_without_mutation(cl, shell_empty, "ps -C")
    assert result.stderr == ["ps: argument required for -C"]


def test_ps_shows_boot_processes_and_simulated_states(cl, shell_empty):
    cl.process_manager.boot()

    result = cl.enter_command("ps -e", shell_empty)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout[0] == "PID  STATE          PPID  COMMAND"
    for command in ("init", "networkd", "sshd", "journald", "cron", "bash"):
        row = next(line for line in result.stdout[1:] if line.endswith(command))
        assert "sleeping" in row
    assert "host" not in "\n".join(result.stdout).lower()


def test_ps_lists_foreground_sleep_rm_and_heredoc(cl, shell_empty):
    sleep = cl.enter_command("sleep 10", shell_empty)
    assert sleep.interaction is not None
    rm = cl.enter_command("touch victim", shell_empty)
    assert rm.status == 0
    rm = cl.enter_command("rm -i victim", shell_empty)
    assert rm.interaction is not None
    heredoc = cl.enter_command("cat << EOF", shell_empty)
    assert heredoc.interaction is not None

    result = cl.enter_command("ps", shell_empty)

    assert any("running" in line and "sleep 10" in line for line in result.stdout)
    assert any("waiting_input" in line and "rm victim" in line for line in result.stdout)
    assert any("waiting_input" in line and "heredoc EOF" in line for line in result.stdout)


def test_ps_selects_pids_and_command(cl, shell_empty):
    cl.process_manager.boot()
    processes = list(cl.process_manager.processes.values())
    target = processes[1]

    by_pid = cl.enter_command(f"ps -p {target.pid}", shell_empty)
    by_command = cl.enter_command(f"ps -C {target.command}", shell_empty)
    combined = cl.enter_command(f"ps -p {target.pid} -C {target.command}", shell_empty)

    assert len(by_pid.stdout) == len(by_command.stdout) == len(combined.stdout) == 2
    assert str(target.pid) in combined.stdout[1]
    assert target.command in combined.stdout[1]


def test_ps_no_matches_prints_header_only(cl, shell_empty):
    cl.process_manager.boot()

    result = cl.enter_command("ps -C no-such-command", shell_empty)

    assert result.status == 0
    assert result.stdout == ["PID  STATE          PPID  COMMAND"]


def test_ps_long_output_shows_simulated_program_type(cl, shell_empty):
    cl.enter_command("sleep 10", shell_empty)

    result = cl.enter_command("ps -l", shell_empty)

    assert result.stdout[0] == "PID  STATE          PPID  PROGRAM         COMMAND"
    assert any("SleepProgram" in line and "sleep 10" in line for line in result.stdout)


@pytest.mark.parametrize("pid_list", ["abc", "0", "1,,2", "-1"])
def test_ps_rejects_invalid_pid_lists(cl, shell_empty, pid_list):
    result = cl.enter_command(f"ps -p {pid_list}", shell_empty)

    assert result.status == 1
    assert result.stderr == [f"ps: invalid process ID list '{pid_list}'"]


def test_ps_omits_completed_processes(cl, shell_empty):
    cl.process_manager.boot()
    cl.enter_command("sleep 1", shell_empty)
    process = cl.process_manager.get_process(shell_empty.foreground_pid)
    assert process is not None
    Scheduler(cl.process_manager).tick()

    result = cl.enter_command("ps", shell_empty)

    assert process.pid not in cl.process_manager.processes
    assert all("sleep 1" not in line for line in result.stdout)
