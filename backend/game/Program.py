from game.ProcessManager import Process, ProcessState

class Program:
    def start(self):
        pass

    def receive_input(self, text: str):
        pass

    def tick(self):
        pass

class SleepProgram(Program):
    def __init__(self, process: Process, ticks: int):
        self.process = process
        self.remaining = ticks

    def tick(self):
        self.remaining -= 1

        if self.remaining <= 0:
            self.process.status = ProcessState.TERMINATED