from enum import StrEnum

class ProcessState(StrEnum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    TERMINATED = "TERMINATED"

class Process():
    _next_id = 1
    def __init__(self, name: str, parent: int, command: str = "", status: ProcessState = ProcessState.RUNNING):
        self.pid: int = Process._next_id
        Process._next_id += 1
        self.ppid: int = parent
        self.name: str = name
        self.command: str = command
        self.status: str = status

class ProcessManager():
    def __init__(self) -> None:
        self.processes: dict[int, Process] = {}

    def create_process(self, name: str, parent: int, command: str = ""):
        process = Process(name, parent)
        self.processes[parent] = process

    def setup_system(self):
        self.create_process("init", 0)
        self.create_process("networkd", 1)
        self.create_process("sshd", 1)
        self.create_process("journald", 1)
        self.create_process("cron", 1)
        self.create_process("bash", 1)
