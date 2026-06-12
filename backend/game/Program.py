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
    def __init__(self, process: Process, files: list[str]):
        self.process = process
        self.files = files
        self.current_file = None

    def start(self):
        self.next_file()

    def next_file(self):
        if not self.files:
            self.process.status = ProcessState.TERMINATED
            return

        self.current_file = self.files.pop(0)

    def receive_input(self, text):
        if text.lower() in ["y", "yes"]:
            # delete file
            pass

        self.next_file()
