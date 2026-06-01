import asyncio

import pytest

from network.SessionManger import GameSession
from game.ShellState import ShellState
from game.ProcessManager import ProcessState


@pytest.mark.asyncio
async def test_sleep_process_runs_and_terminates():

    # Setup machine
    session = GameSession("1")

    # Start scheduler
    scheduler_task = asyncio.create_task(
        session.scheduler_loop()
    )

    try:

        shell = ShellState()

        result = session.commandline.enter_command(
            "sleep 2",
            shell
        )

        assert result.stderr == []

        # Find the sleep process
        sleep_proc = next(
            (
                proc
                for proc in session.process_manager.processes.values()
                if proc.command == "sleep 2"
            ),
            None
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
async def test_multiple_sleep_processes():

    session = GameSession("1")

    scheduler_task = asyncio.create_task(
        session.scheduler_loop()
    )

    try:

        shell = ShellState()

        session.commandline.enter_command(
            "sleep 2",
            shell
        )

        session.commandline.enter_command(
            "sleep 5",
            shell
        )

        processes = [
            p
            for p in session.process_manager.processes.values()
            if p.command.startswith("sleep")
        ]

        assert len(processes) == 2

        await asyncio.sleep(3)

        sleep2 = next(
            p for p in processes
            if p.command == "sleep 2"
        )

        sleep5 = next(
            p for p in processes
            if p.command == "sleep 5"
        )

        assert sleep2.status == ProcessState.TERMINATED
        assert sleep5.status == ProcessState.RUNNING

    finally:

        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass