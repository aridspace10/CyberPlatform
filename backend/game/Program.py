from types import SimpleNamespace
from typing import Callable

from game.Context import SystemContext
from game.inode import NodeType
from game.Process import Process, ProcessState

ProgramOutput = tuple[list[str], list[str]]
HeredocComplete = Callable[[list[str]], ProgramOutput]


class Program:
    def __init__(self) -> None:
        self.prompt: str | None = None

    def start(self) -> ProgramOutput:
        raise NotImplementedError()

    def receive_input(self, line: str) -> ProgramOutput:
        raise NotImplementedError()

    def tick(self):
        raise NotImplementedError()


class SleepProgram(Program):
    def __init__(self, process: Process, ticks: int):
        super().__init__()
        self.process = process
        self.remaining = ticks

    def tick(self):
        self.remaining -= 1

        if self.remaining <= 0:
            self.process.status = ProcessState.TERMINATED


class BackgroundJobProgram(Program):
    """Run one shell job on a scheduler tick and collect its eventual result."""

    def __init__(self, process: Process, run, children: list[Process]):
        super().__init__()
        self.process = process
        self.run = run
        self.children = children
        self.started = False
        self.continuation = None

    def tick(self):
        if not self.started or (
            self.continuation is not None
            and all(child.status == ProcessState.TERMINATED for child in self.children)
        ):
            continuation = self.continuation
            completed = None
            if continuation is not None:
                completed = SimpleNamespace(
                    status=self.children[-1].exit_status if self.children else 0,
                    stdout=[],
                    stderr=[],
                    kind="text",
                    interaction=None,
                    payload=None,
                )
                self.continuation = None
            self.started = True
            try:
                stdout, stderr, status, interaction, next_continuation = self.run(
                    continuation, completed
                )
            except Exception as error:
                self.process.stderr.append(f"background job failed: {error}")
                for child in self.children:
                    child.status = ProcessState.TERMINATED
                self.process.exit_status = 1
                self.process.status = ProcessState.TERMINATED
                return

            self.process.stdout.extend(stdout)
            self.process.stderr.extend(stderr)
            self.process.exit_status = status
            if interaction is not None and interaction.mode == "background_wait":
                # Even a final sleep has no AST tail to resume, but it still has
                # to keep the job alive until its child exits.
                self.continuation = next_continuation or (lambda completed: completed)
                return
            if interaction is not None:
                self.process.stderr.append(
                    "background job cannot wait for interactive input"
                )
                self.process.exit_status = 1
                for child in self.children:
                    child.status = ProcessState.TERMINATED
                self.process.status = ProcessState.TERMINATED
                return

        if all(child.status == ProcessState.TERMINATED for child in self.children):
            self.process.status = ProcessState.TERMINATED


class RmProgram(Program):
    def __init__(
        self,
        process: Process,
        files: list[str],
        sys: SystemContext,
        recursive: bool = False,
    ):
        super().__init__()
        self.process = process
        self.files = files.copy()
        self.current_file: str | None = None
        self.sys = sys
        self.recursive = recursive

    def start(self) -> ProgramOutput:
        self.process.status = ProcessState.RUNNING
        output = self.next_file()
        if output[1]:
            self.process.exit_status = 1
        return output

    def next_file(self) -> ProgramOutput:
        stderr = []
        self.prompt = None

        while self.files:
            self.current_file = self.files.pop(0)
            fn = self.sys.fs.get_file(self.current_file)

            if fn is None or isinstance(fn, str):
                stderr.append(f"rm: cannot remove '{self.current_file}': No such file")
                continue

            kind = "directory" if fn.get_type().value == "directory" else "regular file"
            self.prompt = f"rm: remove {kind} '{self.current_file}'?"
            self.process.status = ProcessState.WAITING_INPUT
            return [], stderr

        self.current_file = None
        self.process.status = ProcessState.TERMINATED
        return [], stderr

    def receive_input(self, line: str) -> ProgramOutput:
        self.process.status = ProcessState.RUNNING
        stderr = []

        if self.current_file is None:
            self.process.status = ProcessState.TERMINATED
            return [], ["rm: interactive process has no current target"]

        if line.lower() in ["y", "yes"]:
            target = self.sys.fs.get_file(self.current_file)
            if (
                target is not None
                and not isinstance(target, str)
                and target.get_type() == NodeType.DIRECTORY
                and target.items
            ):
                stderr.append(
                    f"rm: cannot remove '{self.current_file}': Directory not empty"
                )
            else:
                result = self.sys.fs.delete(
                    self.current_file,
                    recursive=self.recursive,
                )
                if isinstance(result, str):
                    stderr.append(f"rm: {result}")

        stdout, next_errors = self.next_file()
        stderr.extend(next_errors)
        if stderr:
            self.process.exit_status = 1
        return stdout, stderr


class HeredocProgram(Program):
    def __init__(
        self,
        process: Process,
        delimiter: str,
        on_complete: HeredocComplete,
    ):
        super().__init__()
        self.process = process
        self.delimiter = delimiter
        self.on_complete = on_complete
        self.lines: list[str] = []

    def start(self) -> ProgramOutput:
        self.process.status = ProcessState.WAITING_INPUT
        self.prompt = ">"
        return [], []

    def receive_input(self, line: str) -> ProgramOutput:
        if line == self.delimiter:
            self.prompt = None
            stdout, stderr = self.on_complete(self.lines)
            self.process.status = ProcessState.TERMINATED
            return stdout, stderr

        self.lines.append(line)
        self.process.status = ProcessState.WAITING_INPUT
        self.prompt = ">"
        return [], []
