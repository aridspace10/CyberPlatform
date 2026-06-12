class ProcessTerminatedEvent:
    def __init__(self, process):
        self.process = process


class HereDocTerminateEvent:
    def __init__(self, process):
        self.process = process
