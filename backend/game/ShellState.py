from game.filesystem import FileSystem
from typing import List

class ShellState:
    def __init__(self):
        self.cwd = ""
        self.fs = FileSystem()
        self.commands = CommandHistory()
        self.vars = {}
        self.ls = 0

    def __str__(self) -> str:
        return f"cwd: {self.cwd}, command: {str(self.commands)}"

class CommandHistory:
    def __init__(self, maxlen=1000):
        self.commands = []
        self.maxlen = maxlen

    def get_commands(self) -> List:
        return self.commands

    def add(self, cmd: str):
        self.commands.append(cmd)
        if len(self.commands) > self.maxlen:
            self.commands.pop(0)

    def get(self, n: int):
        if n < len(self.commands):
            return self.commands[n]
        else:
            return ""