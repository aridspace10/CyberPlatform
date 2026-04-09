from game.filesystem import FileSystem

class ShellState:
    def __init__(self):
        self.cwd = ""
        self.fs = FileSystem()
        self.commands = CommandHistory()
        self.vars = {}
        self.ls = 0

class CommandHistory:
    def __init__(self, maxlen=1000):
        self.commands = []
        self.maxlen = maxlen

    def add(self, cmd: str):
        self.commands.append(cmd)
        if len(self.commands) > self.maxlen:
            self.commands.pop(0)

    def get(self, n: int):
        return self.commands[n - 1]