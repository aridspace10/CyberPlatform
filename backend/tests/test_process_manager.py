from game.Events import ProcessTerminatedEvent
from game.Process import ProcessState
from game.Scheduler import Scheduler
from game.ShellState import ShellState
from network.SessionManger import GameSession


def _session_shell():
    shell = ShellState()
    shell.fs.add_file("victim")
    return shell


def test_boot_process_ids_and_parent_references_are_consistent():
    session = GameSession("process-ids-boot")
    manager = session.process_manager

    init = manager.get_process(1)
    assert init is not None
    assert init.command == "init"
    for pid in range(2, 7):
        process = manager.get_process(pid)
        assert process is not None
        assert process.ppid == init.pid

    manager.boot()
    assert len(manager.processes) == 6
    command_process = manager.create_process("sleep 1", parent=init.pid)
    assert command_process.pid == 100
    assert command_process.ppid in manager.processes


def test_unbooted_manager_uses_system_root_as_parent(cl, shell_empty):
    result = cl.enter_command("sleep 1", shell_empty)

    assert result.interaction is not None
    process = cl.process_manager.get_process(shell_empty.foreground_pid)
    assert process is not None
    assert process.ppid == 0


def test_interleaved_sessions_keep_sleep_rm_and_heredoc_processes_isolated():
    session_a = GameSession("process-ids-a")
    shell_a = _session_shell()
    manager_a = session_a.process_manager

    session_a.commandline.enter_command("sleep 30", shell_a)
    sleep_a = manager_a.get_process(shell_a.foreground_pid)
    assert sleep_a is not None
    assert sleep_a.pid == 100

    rm_a_result = session_a.commandline.enter_command("rm -i victim", shell_a)
    rm_a = manager_a.get_process(shell_a.foreground_pid)
    assert rm_a is not None
    assert rm_a_result.interaction is not None

    heredoc_a_result = session_a.commandline.enter_command("cat << EOF", shell_a)
    heredoc_a = manager_a.get_process(shell_a.foreground_pid)
    assert heredoc_a is not None
    assert heredoc_a_result.interaction is not None

    # Booting another game session must not reset session A's next PID.
    session_b = GameSession("process-ids-b")
    shell_b = _session_shell()
    manager_b = session_b.process_manager

    session_b.commandline.enter_command("sleep 2", shell_b)
    sleep_b = manager_b.get_process(shell_b.foreground_pid)
    assert sleep_b is not None
    assert sleep_b.pid == sleep_a.pid
    assert sleep_b is not sleep_a

    rm_b_result = session_b.commandline.enter_command("rm -i victim", shell_b)
    rm_b = manager_b.get_process(shell_b.foreground_pid)
    assert rm_b is not None
    assert rm_b_result.interaction is not None

    heredoc_b_result = session_b.commandline.enter_command("cat << EOF", shell_b)
    heredoc_b = manager_b.get_process(shell_b.foreground_pid)
    assert heredoc_b is not None
    assert heredoc_b_result.interaction is not None

    # A's original live process remains registered, and later IDs keep advancing.
    session_a.commandline.enter_command("sleep 2", shell_a)
    sleep_a_later = manager_a.get_process(shell_a.foreground_pid)
    assert sleep_a_later is not None
    assert sleep_a_later.pid > sleep_a.pid
    assert manager_a.get_process(sleep_a.pid) is sleep_a
    assert sleep_a.program.remaining == 30

    # Foreground input is delivered only to the owning session's programs.
    rm_a.program.receive_input("yes")
    assert shell_a.fs.get_file("victim") is None
    assert shell_b.fs.get_file("victim") is not None
    assert rm_b.status == ProcessState.WAITING_INPUT

    assert heredoc_a.program.receive_input("from session A") == ([], [])
    assert heredoc_a.program.receive_input("EOF") == (["from session A"], [])
    assert heredoc_a.status == ProcessState.TERMINATED
    assert heredoc_b.status == ProcessState.WAITING_INPUT

    Scheduler(manager_a).tick()
    terminated_a = [event.process for event in manager_a.events]
    assert any(
        isinstance(event, ProcessTerminatedEvent) and event.process is rm_a
        for event in manager_a.events
    )
    assert any(
        isinstance(event, ProcessTerminatedEvent) and event.process is heredoc_a
        for event in manager_a.events
    )
    assert rm_a in terminated_a
    assert heredoc_a in terminated_a
    assert not manager_b.events

    scheduler_b = Scheduler(manager_b)
    scheduler_b.tick()
    assert manager_b.get_process(sleep_b.pid) is sleep_b
    scheduler_b.tick()
    assert any(
        isinstance(event, ProcessTerminatedEvent) and event.process is sleep_b
        for event in manager_b.events
    )
    assert manager_a.get_process(sleep_a.pid) is sleep_a
