import asyncio

import pytest
from game.ProcessManager import ProcessState
from game.ShellState import ShellState
from network.SessionManger import GameSession


###### non async ##############
def test_sleep_error1(cl, shell_empty: ShellState):
    cmd = cl.enter_command("sleep", shell_empty)
    assert cmd.stderr != []
    assert cmd.stdout == []


def test_sleep_error2(cl, shell_empty: ShellState):
    cmd = cl.enter_command("sleep hello", shell_empty)
    assert cmd.stderr != []
    assert cmd.stdout == []


# Async


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
