from .filesystem import FileSystem

class ShellState:
    def __init__(self):
        self.cwd = "/"
        self.fs = FileSystem()
        self.env = {}
        self.vars = {}
        self.ls = 0