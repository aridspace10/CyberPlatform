"""Local terminal adapter for the real command engine and foreground programs."""

import argparse
import sys
import time
import traceback
from typing import TextIO

from game.commandline import CommandLine, CommandResult
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
        self.last_status = 0
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
    def prompt(self) -> str:
        proc = self.foreground
        if proc and proc.program and proc.program.prompt is not None:
            return proc.program.prompt + " "
        parts = []
        node: FileNode | None = self.shell.fs.current
        while node is not None:
            parts.append(node.name)
            node = node.parent
        return f"cyber:/{'/'.join(reversed(parts))}$ "

    def reap(self) -> None:
        self.scheduler.tick()
        proc = self.foreground
        if proc is None or proc.status == ProcessState.TERMINATED:
            self.shell.foreground_pid = None
        # This console has one shell and no WebSocket event consumers.
        self.process_manager.events.clear()

    def interrupt(self) -> None:
        proc = self.foreground
        if proc:
            proc.status = ProcessState.TERMINATED
        self.shell.foreground_pid = None
        self.reap()
        self.last_status = 130

    def execute(self, raw: str) -> CommandResult:
        proc = self.foreground
        if proc and proc.program:
            stdout, stderr = proc.program.receive_input(raw)
            result = CommandResult(
                status=1 if stderr else 0, stdout=stdout, stderr=stderr
            )
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
            if control == ":help":
                print("Commands: " + " ".join(sorted(console.commandline.commands)))
                print(":reset  Reset files and shell state (keeps the current code).")
                print(":status Show the last returned status; --status shows each one.")
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
