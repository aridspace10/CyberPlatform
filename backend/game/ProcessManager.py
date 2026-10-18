from game.Process import Process, ProcessState


class ProcessManager:
    def __init__(self) -> None:
        self.processes: dict[int, Process] = {}
        self.events = []

    def create_process(
        self, command: str, parent: int, status: ProcessState = ProcessState.RUNNING
    ) -> Process:
        process = Process(command, parent, status)
        self.processes[process.pid] = process
        return process

    def get_process(self, pid: int) -> Process | None:
        return self.processes.get(pid)

    def remove_process(self, pid: int) -> Process | None:
        proc = self.processes[pid]
        del self.processes[pid]
        return proc

    def list_processes(self, parameters: dict) -> list[str]:
        """Return the simulated process table, excluding already terminated jobs.

        The scheduler removes completed processes. Filtering terminated entries
        here also keeps the output correct between termination and the next tick.
        """
        processes = [
            process
            for process in self.processes.values()
            if process.status != ProcessState.TERMINATED
        ]

        pids = parameters.get("pid")
        if pids is not None:
            processes = [process for process in processes if process.pid in pids]
        command = parameters.get("command")
        if command is not None:
            processes = [process for process in processes if process.command == command]

        header = "PID  STATE          PPID  COMMAND"
        if parameters.get("long"):
            header = "PID  STATE          PPID  PROGRAM         COMMAND"
        rows = [header]
        for process in processes:
            state = process.status.value.lower()
            if parameters.get("long"):
                program = type(process.program).__name__ if process.program else "-"
                rows.append(
                    f"{process.pid:<4} {state:<14} {process.ppid:<5} "
                    f"{program:<15} {process.command}"
                )
            else:
                rows.append(
                    f"{process.pid:<4} {state:<14} {process.ppid:<5} {process.command}"
                )
        return rows

    def modify_process(self, pid: int, status: ProcessState) -> None:
        self.processes[pid].status = status

    def boot(self):
        self.create_process("init", 0, status=ProcessState.SLEEPING)
        self.create_process("networkd", 1, status=ProcessState.SLEEPING)
        self.create_process("sshd", 1, status=ProcessState.SLEEPING)
        self.create_process("journald", 1, status=ProcessState.SLEEPING)
        self.create_process("cron", 1, status=ProcessState.SLEEPING)
        self.create_process("bash", 1, status=ProcessState.SLEEPING)
        Process._next_id = 100
