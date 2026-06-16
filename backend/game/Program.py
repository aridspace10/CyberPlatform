from game.Context import SystemContext
from game.filesystem import FileNode
from game.Parser import Command
from game.Process import Process, ProcessState


class Program:
    def start(self) -> tuple[list[str], list[str]]:
        raise NotImplementedError()

    def receive_input(self, text: str) -> tuple[list[str], list[str]]:
        raise NotImplementedError()

    def tick(self):
        raise NotImplementedError()


class SleepProgram(Program):
    def __init__(self, process: Process, ticks: int):
        self.process = process
        self.remaining = ticks

    def tick(self):
        self.remaining -= 1

        if self.remaining <= 0:
            self.process.status = ProcessState.TERMINATED


class RmProgram(Program):
    def __init__(self, process: Process, files: list[str], sys: SystemContext):
        self.process = process
        self.files = files
        self.current_file = None
        self.sys = sys
        self.output = ([], [])

    # Starts the program and returns (stdout, stderr)
    def start(self) -> tuple[list[str], list[str]]:
        self.process.status = ProcessState.RUNNING
        return self.next_file()

    def next_file(self) -> tuple[list[str], list[str]]:
        if not self.files:
            self.process.status = ProcessState.TERMINATED
            return self.output

        self.current_file = self.files.pop(0)
        fn = self.sys.fs.get_file(self.current_file)
        if isinstance(fn, str):
            self.output[1].append(fn)
            self.next_file()
        elif isinstance(fn, FileNode):
            self.process.status = ProcessState.WAITING_INPUT
            self.output[0].append(f"rm: remove regular file '{self.current_file}'?")
        return self.output

    def receive_input(self, text) -> tuple[list[str], list[str]]:
        self.process.status = ProcessState.RUNNING
        self.output = ([], [])
        assert self.current_file
        if text.lower() in ["y", "yes"]:
            self.sys.fs.delete(self.current_file)
        return self.next_file()


class HeredocProgram(Program):
    def __init__(self, proc: Process, command: Command, delimiter: str):
        self.proc = proc
        self.command = command
        self.delimiter = delimiter
        self.lines = []

    def on_input(self, line: str):
        if line == self.delimiter:
            self.proc.status = ProcessState.TERMINATED
            return

        self.lines.append(line)
