"""Local terminal adapter for the real command engine and foreground programs."""

import argparse
import sys
import time
import traceback
from typing import TextIO

from game.commandline import CommandLine, CommandResult, Interaction
from game.Events import ProcessTerminatedEvent
from game.filenode import FileNode
from game.NetworkManager import NetworkManager
from game.Process import Process, ProcessState
from game.ProcessManager import ProcessManager
from game.Scheduler import Scheduler
from game.ShellState import ShellState


class DevShell:
    def __init__(self, empty: bool = False):
        self.empty = empty
        self.reset()

    def reset(self) -> None:
        self.shell = ShellState()
        self.process_manager = ProcessManager()
        self.process_manager.boot()
        self.scheduler = Scheduler(self.process_manager)
        self.commandline = CommandLine(self.process_manager, NetworkManager())
        self.shell.last_status = 0
        self.background_output: list[tuple[int, int, list[str], list[str]]] = []
        if not self.empty:
            self.shell.fs.add_directory("logs")
            for path, lines in {
                "notes.txt": ["hello world", "testing command fixes"],
                "logs/app.log": ["INFO started", "ERROR example", "INFO finished"],
            }.items():
                self.shell.fs.add_file(path)
                node = self.shell.fs.get_file(path)
                assert isinstance(node, FileNode)
                node.set_data(lines)

    @property
    def foreground(self) -> Process | None:
        pid = self.shell.foreground_pid
        return self.process_manager.get_process(pid) if pid is not None else None

    @property
    def last_status(self) -> int:
        return self.shell.last_status

    @last_status.setter
    def last_status(self, status: int) -> None:
        self.shell.last_status = status

    @property
    def prompt(self) -> str:
        proc = self.foreground
        if proc and proc.program and proc.program.prompt is not None:
            return proc.program.prompt + " "
        return f"cyber:{self.shell.fs.display_path(self.shell.fs.current)}$ "

    def reap(self) -> None:
        self.scheduler.tick()
        for event in self.process_manager.events:
            if (
                isinstance(event, ProcessTerminatedEvent)
                and self.shell.foreground_pid == event.process.pid
            ):
                had_continuation = self.shell.continuation is not None
                result = self.commandline.resume_foreground(
                    self.shell,
                    event.process,
                    CommandResult(
                        status=event.process.exit_status,
                        stdout=event.process.stdout.copy(),
                        stderr=event.process.stderr.copy(),
                    ),
                )
                self.last_status = result.status
                if had_continuation:
                    write_lines(result.stdout, sys.stdout)
                    write_lines(result.stderr, sys.stderr)
        proc = self.foreground
        if proc is None or proc.status == ProcessState.TERMINATED:
            self.shell.foreground_pid = None
        for event in self.process_manager.events:
            process = getattr(event, "process", None)
            if process is not None and process.pid in self.shell.background_jobs:
                self.background_output.append(
                    (
                        process.pid,
                        process.exit_status,
                        process.stdout,
                        process.stderr,
                    )
                )
                self.shell.background_jobs.pop(process.pid, None)
                self.shell.background_children.pop(process.pid, None)
        self.process_manager.events.clear()

    def take_background_output(self) -> list[tuple[int, int, list[str], list[str]]]:
        output, self.background_output = self.background_output, []
        return output

    def cancel_background_job(self, pid: int) -> bool:
        return self.commandline.cancel_background_job(pid, self.shell)

    def shutdown(self) -> None:
        for pid in list(self.shell.background_jobs):
            self.cancel_background_job(pid)
        self.reap()

    def interrupt(self) -> None:
        proc = self.foreground
        if proc:
            proc.status = ProcessState.TERMINATED
            proc.exit_status = 130
            had_continuation = self.shell.continuation is not None
            result = self.commandline.resume_foreground(
                self.shell, proc, CommandResult(status=130)
            )
            if had_continuation:
                write_lines(result.stdout, sys.stdout)
                write_lines(result.stderr, sys.stderr)
        if proc is None or self.shell.foreground_pid == proc.pid:
            self.shell.foreground_pid = None
        self.reap()
        self.last_status = result.status if proc else 130

    def execute(self, raw: str) -> CommandResult:
        proc = self.foreground
        if proc and proc.program:
            if raw in ("\x03", "^C"):
                proc.status = ProcessState.TERMINATED
                proc.exit_status = 130
                result = CommandResult(status=130)
            elif proc.status != ProcessState.WAITING_INPUT:
                result = CommandResult(
                    status=1,
                    stderr=["Foreground process is not accepting input"],
                    interaction=Interaction(
                        mode="foreground", prompt=proc.program.prompt
                    ),
                )
            else:
                stdout, stderr = proc.program.receive_input(raw)
                result = CommandResult(
                    status=(
                        proc.exit_status
                        if proc.status == ProcessState.TERMINATED
                        else (1 if stderr else 0)
                    ),
                    stdout=stdout,
                    stderr=stderr,
                    interaction=(
                        None
                        if proc.status == ProcessState.TERMINATED
                        else Interaction(mode="foreground", prompt=proc.program.prompt)
                    ),
                )
            if proc.status == ProcessState.TERMINATED:
                result = self.commandline.resume_foreground(self.shell, proc, result)
        elif not raw.strip():
            return CommandResult(status=self.last_status)
        else:
            result = self.commandline.enter_command(raw, self.shell)
        self.last_status = result.status
        return result

    def wait_for_foreground(self) -> None:
        while (proc := self.foreground) is not None:
            if proc.status == ProcessState.WAITING_INPUT:
                return
            if proc.status != ProcessState.TERMINATED:
                time.sleep(1)
            self.reap()
        if self.shell.background_jobs:
            self.reap()


def write_lines(lines: list[str], stream: TextIO) -> None:
    for line in lines:
        stream.write(line if line.endswith("\n") else line + "\n")
    stream.flush()


def run_line(console: DevShell, raw: str, show_status: bool) -> None:
    try:
        result = console.execute(raw)
        write_lines(result.stdout, sys.stdout)
        write_lines(result.stderr, sys.stderr)
        console.wait_for_foreground()
        for pid, status, stdout, stderr in console.take_background_output():
            write_lines([f"[job {pid}] completed with status {status}"], sys.stdout)
            write_lines(stdout, sys.stdout)
            write_lines(stderr, sys.stderr)
    except KeyboardInterrupt:
        console.interrupt()
        print("^C", file=sys.stderr)
    except Exception:
        # A developer needs the traceback, but should be able to try another input.
        console.interrupt()
        console.last_status = 1
        traceback.print_exc()
    if show_status:
        print(f"[status={console.last_status}]", file=sys.stderr)


def repl(console: DevShell, show_status: bool = False) -> int:
    print("CyberPlatform development shell (in-memory filesystem).")
    print(":help for commands, :reset for a fresh filesystem, :exit to quit.")
    if not console.empty:
        print("Sample files: notes.txt, logs/app.log")
    while True:
        try:
            raw = input(console.prompt)
        except EOFError:
            console.interrupt()
            console.shutdown()
            print()
            return 0
        except KeyboardInterrupt:
            console.interrupt()
            print("\n^C", file=sys.stderr)
            continue
        # While a program is reading input, even ':exit' is literal input.
        if console.foreground is None:
            control = raw.strip()
            if control in (":exit", "exit", "quit"):
                console.shutdown()
                return 0
            if control == ":reset":
                console.reset()
                print(
                    "Fresh filesystem ready. Restart the launcher to load code edits."
                )
                continue
            if control == ":status":
                print(console.last_status)
                continue
            if control.startswith(":cancel "):
                try:
                    pid = int(control.split(maxsplit=1)[1])
                except (IndexError, ValueError):
                    print("Usage: :cancel PID", file=sys.stderr)
                else:
                    print(
                        "Background job cancelled"
                        if console.cancel_background_job(pid)
                        else "No active background job with that PID",
                        file=sys.stderr,
                    )
                continue
            if control == ":help":
                print("Commands: " + " ".join(sorted(console.commandline.commands)))
                print(":reset  Reset files and shell state (keeps the current code).")
                print(":status Show the last returned status; --status shows each one.")
                print(":cancel PID Cancel a background job.")
                print(":exit   Quit. Ctrl+C cancels foreground input or waiting.")
                continue
        run_line(console, raw, show_status)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--empty", action="store_true", help="start without sample files"
    )
    parser.add_argument(
        "--status", action="store_true", help="show each returned status"
    )
    parser.add_argument(
        "-c",
        "--command",
        action="append",
        help="run an input and exit; repeat to keep state",
    )
    args = parser.parse_args(argv)
    console = DevShell(empty=args.empty)
    if args.command is None:
        return repl(console, args.status)
    for raw in args.command:
        run_line(console, raw, args.status)
        if console.last_status == 130:
            return 130
    if console.foreground is not None:
        print(
            "A program is waiting for input. Use the interactive shell "
            "or add another -c with its response.",
            file=sys.stderr,
        )
        return 2
    return console.last_status
