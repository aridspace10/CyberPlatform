from game.Events import ProcessTerminatedEvent
from game.ProcessManager import ProcessManager, ProcessState


class Scheduler:
    def __init__(self, pm: ProcessManager):
        self.pm = pm

    def tick(self):
        dead = []
        for proc in list(self.pm.processes.values()):

            if proc.status == ProcessState.TERMINATED:
                self.pm.events.append(ProcessTerminatedEvent(proc))
                dead.append(proc.pid)
                continue

            if proc.status != ProcessState.RUNNING:
                continue

            if proc.program:
                proc.program.tick()

            if proc.status == ProcessState.TERMINATED:
                self.pm.events.append(ProcessTerminatedEvent(proc))
                dead.append(proc.pid)

        for pid in dead:
            self.pm.remove_process(pid)
