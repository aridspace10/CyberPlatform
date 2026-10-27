import asyncio

from game.commandline import CommandResult
from game.Events import ProcessTerminatedEvent
from game.Process import ProcessState
from game.Scheduler import Scheduler
from game.ShellState import ShellState
from network.SessionManger import GameSession, Player


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


def test_create_before_boot_keeps_command_children_attached_to_init(cl, shell_empty):
    early = cl.process_manager.create_process("early-job", parent=0)

    cl.process_manager.boot()
    init = next(
        process
        for process in cl.process_manager.processes.values()
        if process.command == "init"
    )
    result = cl.enter_command("sleep 1", shell_empty)

    assert result.interaction is not None
    process = cl.process_manager.get_process(shell_empty.foreground_pid)
    assert process is not None
    assert process.pid != early.pid
    assert init.pid == cl.process_manager.default_parent_pid
    assert process.ppid == init.pid


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




def test_background_failure_reports_nonzero_status(cl, shell_empty):
    result = cl.enter_command("unknown-command &", shell_empty)
    job = cl.process_manager.get_process(next(iter(shell_empty.background_jobs)))
    assert result.interaction is None
    assert job is not None

    Scheduler(cl.process_manager).tick()

    assert job.status == ProcessState.TERMINATED
    assert job.exit_status == 1
    assert job.stderr == ["Unknown command given"]


def test_session_shutdown_cleans_up_background_processes():
    session = GameSession("background-shutdown")
    player = Player(None, "worker", "1")
    session.players[player.username] = player
    session.commandline.enter_command("sleep 30 &", player.shell)
    job_id = next(iter(player.shell.background_jobs))
    session.scheduler.tick()
    children = player.shell.background_children[job_id]
    assert children

    asyncio.run(session.stop_scheduler())

    assert job_id not in session.process_manager.processes
    assert all(child.pid not in session.process_manager.processes for child in children)
    assert player.shell.background_jobs == {}


def test_background_job_runs_on_scheduler_and_reports_its_result(cl, shell_empty):
    result = cl.enter_command("echo before & echo foreground", shell_empty)

    assert result.stdout == ["[job 1] started echo before", "foreground"]
    assert shell_empty.foreground_pid is None
    job = cl.process_manager.get_process(1)
    assert job is not None
    assert job.command == "echo before"
    assert job.status == ProcessState.RUNNING
    assert job.stdout == []

    Scheduler(cl.process_manager).tick()

    assert job.status == ProcessState.TERMINATED
    assert job.stdout == ["before"]
    assert job.exit_status == 0
    assert shell_empty.last_status == result.status
    assert shell_empty.foreground_pid is None


def test_background_sleep_does_not_take_foreground_and_can_be_cancelled(
    cl, shell_empty
):
    result = cl.enter_command("sleep 30 &", shell_empty)
    job_id = next(iter(shell_empty.background_jobs))
    job = cl.process_manager.get_process(job_id)

    assert result.interaction is None
    assert shell_empty.foreground_pid is None
    assert job is not None
    Scheduler(cl.process_manager).tick()
    children = shell_empty.background_children[job_id]
    assert len(children) == 1
    assert children[0].program.remaining == 30

    assert cl.cancel_background_job(job_id, shell_empty)
    assert children[0].status == ProcessState.TERMINATED
    assert job.exit_status == 130
    Scheduler(cl.process_manager).tick()
    assert any(event.process is job for event in cl.process_manager.events)


def test_background_interactive_command_fails_without_stealing_prompt(cl, shell_empty):
    shell_empty.fs.add_file("victim")
    result = cl.enter_command("rm -i victim &", shell_empty)
    job = cl.process_manager.get_process(next(iter(shell_empty.background_jobs)))

    assert result.interaction is None
    assert shell_empty.foreground_pid is None
    Scheduler(cl.process_manager).tick()
    assert job is not None
    assert job.exit_status == 1
    assert "cannot wait for interactive input" in job.stderr[0]
    assert shell_empty.fs.get_file("victim") is not None


def test_background_andor_waits_for_sleep_before_running_tail(cl, shell_empty):
    result = cl.enter_command("echo before && sleep 2 && echo after &", shell_empty)
    job_id = next(iter(shell_empty.background_jobs))
    job = cl.process_manager.get_process(job_id)
    scheduler = Scheduler(cl.process_manager)

    assert result.stdout[0].startswith("[job ")
    scheduler.tick()
    assert job.stdout == ["before"]
    assert job.status == ProcessState.RUNNING

    scheduler.tick()
    scheduler.tick()
    assert job.stdout == ["before"]
    assert job.status == ProcessState.RUNNING

    scheduler.tick()
    assert job.stdout == ["before", "after"]
    assert job.status == ProcessState.TERMINATED
    assert job.exit_status == 0


def test_rejected_background_interaction_keeps_foreground_continuation(cl, shell_empty):
    shell_empty.fs.add_file("victim")
    result = cl.enter_command(
        "rm -i victim && echo should-not-run & sleep 2; echo foreground", shell_empty
    )
    background_id = next(iter(shell_empty.background_jobs))
    background = cl.process_manager.get_process(background_id)
    foreground_id = shell_empty.foreground_pid
    foreground = cl.process_manager.get_process(foreground_id)
    foreground_continuation = shell_empty.continuation

    assert result.interaction is not None
    assert foreground is not None
    assert foreground_continuation is not None

    scheduler = Scheduler(cl.process_manager)
    for _ in range(5):
        scheduler.tick()
        pending = list(cl.process_manager.events)
        cl.process_manager.events.clear()
        for event in pending:
            if event.process.pid == foreground_id:
                cl.resume_foreground(
                    shell_empty,
                    event.process,
                    CommandResult(
                        status=event.process.exit_status,
                        stdout=event.process.stdout.copy(),
                        stderr=event.process.stderr.copy(),
                    ),
                )

    assert background is not None
    assert background.status == ProcessState.TERMINATED
    assert background.exit_status == 1
    assert "should-not-run" not in background.stdout
    assert shell_empty.foreground_pid is None
    assert shell_empty.last_status == 0


def test_disconnected_background_completion_replays_once_on_reconnect():
    class FakeWebSocket:
        def __init__(self):
            self.messages = []

        async def send_json(self, message):
            self.messages.append(message)

    async def scenario():
        session = GameSession("background-reconnect")
        player = Player(None, "worker", "1")
        session.players[player.username] = player
        session.commandline.enter_command("sleep 2 && echo done &", player.shell)
        session.ensure_scheduler()

        await asyncio.sleep(3.2)
        assert len(player.background_completions) == 1
        assert player.background_completions[0]["stdout"] == ["done"]

        first_socket = FakeWebSocket()
        await session.connect(first_socket, player.username, player.user_id)
        completions = [
            message
            for message in first_socket.messages
            if message.get("type") == "background_job_complete"
        ]
        assert len(completions) == 1
        assert completions[0]["stdout"] == ["done"]
        assert player.background_completions == []

        second_socket = FakeWebSocket()
        await session.disconnect(first_socket)
        await session.connect(second_socket, player.username, player.user_id)
        assert not any(
            message.get("type") == "background_job_complete"
            for message in second_socket.messages
        )
        await session.stop_scheduler()

    asyncio.run(scenario())
