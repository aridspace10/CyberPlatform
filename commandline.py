from filenode import FileNode
from filesystem import FileSystem

class CommandLine:
    def __init__(self):
        self.filesystem = FileSystem()
        self.history = []