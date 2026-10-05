import asyncio

import pytest
from game.ProcessManager import ProcessState
from game.ShellState import ShellState
from network.SessionManger import GameSession
from tests.cmd_tests.creation_helpers import assert_failure
from tests.command_helpers import assert_help


@pytest.mark.parametrize("duration", [".", ".."])
def test_sleep_dot_paths_are_invalid_durations(
    run_dot_command, dot_shell, cl, duration
):
    processes = dict(cl.process_manager.processes)
    result = run_dot_command(f"sleep {duration}")
    assert dot_shell.foreground_pid is None
    assert cl.process_manager.processes == processes
    assert_failure(result)


def test_sleep_dot_paths_preserve_directory_while_starting(run_dot_command, dot_shell):
    result = run_dot_command("sleep 1")
    assert result.status == 0
    assert result.stderr == []
    assert result.interaction is not None
    assert dot_shell.foreground_pid is not None


###### non async ##############
def test_sleep_error1(cl, shell_empty: ShellState):
    cmd = cl.enter_command("sleep", shell_empty)
    assert cmd.stderr != []
    assert cmd.stdout == []


def test_sleep_error2(cl, shell_empty: ShellState):
    cmd = cl.enter_command("sleep hello", shell_empty)
    assert cmd.stderr != []
    assert cmd.stdout == []


def test_sleep_empty_duration_is_a_command_error_without_starting_process(
    cl, shell_empty
):
    processes = dict(cl.process_manager.processes)
    result = cl.enter_command('sleep ""', shell_empty)
    assert_failure(result)
    assert result.stderr
    assert shell_empty.foreground_pid is None
    assert cl.process_manager.processes == processes


# Async


@pytest.mark.asyncio
async def test_session_scheduler_is_started_only_once():
    session = GameSession("scheduler-test")

    first = session.ensure_scheduler()
    second = session.ensure_scheduler()

    assert first is second
    assert session.scheduler_task is first

    await session.stop_scheduler()
    assert session.scheduler_task is None


@pytest.mark.asyncio
async def test_sleep_process_runs_and_terminates():

    # Setup machine
    session = GameSession("1")

    # Start scheduler
    scheduler_task = asyncio.create_task(session.scheduler_loop())

    try:

        shell = ShellState()

        result = session.commandline.enter_command("sleep 2", shell)

        assert result.stderr == []

        # Find the sleep process
        sleep_proc = next(
            (
                proc
                for proc in session.process_manager.processes.values()
                if proc.command == "sleep 2"
            ),
            None,
        )

        assert sleep_proc is not None
        assert sleep_proc.status == ProcessState.RUNNING

        # Wait for scheduler ticks
        await asyncio.sleep(3)

        assert sleep_proc.status == ProcessState.TERMINATED

    finally:

        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_sleep_process_minutes():
    # Setup machine
    session = GameSession("1")
    # Start scheduler
    scheduler_task = asyncio.create_task(session.scheduler_loop())
    try:
        shell = ShellState()
        result = session.commandline.enter_command("sleep 1m", shell)
        assert result.stderr == []
        # Find the sleep process
        sleep_proc = next(
            (
                proc
                for proc in session.process_manager.processes.values()
                if proc.command == "sleep 1m"
            ),
            None,
        )
        assert sleep_proc is not None
        assert sleep_proc.status == ProcessState.RUNNING

        # Tick 3 times (simulate 3 seconds) - should still be running
        for _ in range(3):
            session.scheduler.tick()
        assert sleep_proc.status == ProcessState.RUNNING

        # Tick remaining ~57 times (simulate 60s total) - should now be terminated
        for _ in range(57):
            session.scheduler.tick()
        assert sleep_proc.status == ProcessState.TERMINATED
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_sleep_process_hours():
    # Setup machine
    session = GameSession("1")
    # Start scheduler
    scheduler_task = asyncio.create_task(session.scheduler_loop())
    try:
        shell = ShellState()
        result = session.commandline.enter_command("sleep 1h", shell)
        assert result.stderr == []
        # Find the sleep process
        sleep_proc = next(
            (
                proc
                for proc in session.process_manager.processes.values()
                if proc.command == "sleep 1h"
            ),
            None,
        )
        assert sleep_proc is not None
        assert sleep_proc.status == ProcessState.RUNNING

        # Tick 3 times (simulate 3 seconds) - should still be running
        for _ in range(3):
            session.scheduler.tick()
        assert sleep_proc.status == ProcessState.RUNNING

        # Tick remaining ~57 times (simulate 60s total) - should now be terminated
        for _ in range(3597):
            session.scheduler.tick()
        assert sleep_proc.status == ProcessState.TERMINATED
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_sleep_process_days():
    # Setup machine
    session = GameSession("1")
    # Start scheduler
    scheduler_task = asyncio.create_task(session.scheduler_loop())
    try:
        shell = ShellState()
        result = session.commandline.enter_command("sleep 1d", shell)
        assert result.stderr == []
        # Find the sleep process
        sleep_proc = next(
            (
                proc
                for proc in session.process_manager.processes.values()
                if proc.command == "sleep 1d"
            ),
            None,
        )
        assert sleep_proc is not None
        assert sleep_proc.status == ProcessState.RUNNING

        # Tick 3 times (simulate 3 seconds) - should still be running
        for _ in range(3):
            session.scheduler.tick()
        assert sleep_proc.status == ProcessState.RUNNING

        # Tick remaining ~57 times (simulate 60s total) - should now be terminated
        for _ in range(86397):
            session.scheduler.tick()
        assert sleep_proc.status == ProcessState.TERMINATED
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_multiple_sleep_processes():

    session = GameSession("1")

    scheduler_task = asyncio.create_task(session.scheduler_loop())

    try:

        shell = ShellState()

        session.commandline.enter_command("sleep 2", shell)

        session.commandline.enter_command("sleep 5", shell)

        processes = [
            p
            for p in session.process_manager.processes.values()
            if p.command.startswith("sleep")
        ]

        assert len(processes) == 2

        await asyncio.sleep(3)

        sleep2 = next(p for p in processes if p.command == "sleep 2")

        sleep5 = next(p for p in processes if p.command == "sleep 5")

        assert sleep2.status == ProcessState.TERMINATED
        assert sleep5.status == ProcessState.RUNNING

    finally:

        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


def test_sleep_help(cl, shell_empty):
    assert_help(cl, shell_empty, "sleep")
