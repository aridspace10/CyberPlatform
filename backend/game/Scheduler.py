from game.ProcessManager import ProcessManager, ProcessState, Process

class Scheduler:
    def __init__(self, pm: ProcessManager):
        self.pm = pm

    def tick(self):
        dead = []
        for proc in self.pm.processes.values():

            if proc.status != ProcessState.RUNNING:
                continue

            if proc.status == ProcessState.TERMINATED:
                dead.append(proc.pid)
                continue

            if proc.program:
                proc.program.tick()

        for pid in dead:
            self.pm.remove_process(pid)