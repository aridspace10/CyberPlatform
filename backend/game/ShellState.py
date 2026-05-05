from game.filesystem import FileSystem

class ShellState:
    def __init__(self):
        self.cwd = ""
        self.fs = FileSystem()
        self.commands = []
        self.vars = {}
        self.ls = 0
    
    def serialize(self) -> dict:
        return {
            "vars": self.vars,
            "cmds": self.commands,
            "fs": self.fs.to_dict()
        }