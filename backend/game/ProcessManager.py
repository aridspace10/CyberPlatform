from enum import StrEnum

class ProcessState(StrEnum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    TERMINATED = "TERMINATED"

class Process():
    _next_id = 1
    def __init__(self, user: str, command: str = "", status: ProcessState = ProcessState.RUNNING):
        self.pid: int = Process._next_id
        Process._next_id += 1
        self.user: str = user
        self.command: str = command
        self.status: str = status

class ProcessManager():
    def __init__(self) -> None:
        self.processes: list[Process] = []

    def create_process(self, user: str, command: str = ""):
        process = Process(user, command)
        self.processes.append(process)