from game.Process import Process, ProcessState

class ProcessManager():
    def __init__(self) -> None:
        self.processes: dict[int, Process] = {}

    def create_process(self, command: str, parent: int, status: ProcessState = ProcessState.RUNNING) -> Process:
        process = Process(command, parent, status)
        self.processes[process.pid] = process
        return process

    def get_process(self, pid: int) -> Process | None:
        return self.processes.get(pid)
    
    def remove_process(self, pid: int) -> Process | None:
        proc = self.processes[pid]
        del self.processes[pid]
        return proc
    
    def list_processes(self, paramaters: dict) -> list[str]:
        return []
    
    def modify_process(self, pid: int, status: ProcessState) -> None:
        self.processes[pid].status = status

    def boot(self):
        self.create_process("init",     0, status=ProcessState.SLEEPING)
        self.create_process("networkd", 1, status=ProcessState.SLEEPING)
        self.create_process("sshd",     1, status=ProcessState.SLEEPING)
        self.create_process("journald", 1, status=ProcessState.SLEEPING)
        self.create_process("cron",     1, status=ProcessState.SLEEPING)
        self.create_process("bash",     1, status=ProcessState.SLEEPING)
        Process._next_id = 100
