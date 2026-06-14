from game.Context import SystemContext
from game.filesystem import FileNode
from game.Parser import Command
from game.Process import Process, ProcessState


class Program:
    def start(self):
        pass

    def receive_input(self, text: str):
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
        self.output = []

    def start(self):
        self.next_file()

    def next_file(self):
        if not self.files:
            self.process.status = ProcessState.TERMINATED
            return

        self.current_file = self.files.pop(0)
        fn = self.sys.fs.get_file(self.current_file)
        if isinstance(fn, str):
            self.output.append(fn)
            self.next_file()
        elif isinstance(fn, FileNode):
            self.process.status = ProcessState.WAITING_INPUT
            self.output.append(f"rm: remove regular file '{self.current_file}'? ")

    def receive_input(self, text):
        assert self.current_file
        if text.lower() in ["y", "yes"]:
            self.sys.fs.delete(self.current_file)
        self.next_file()


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
