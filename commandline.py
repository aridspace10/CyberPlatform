from filenode import FileNode
from filesystem import FileSystem

class CommandLine:
    def __init__(self):
        self.filesystem = FileSystem()
        self.history = []
    
    def enter_command(self, raw: str) -> None:
        args = raw.split(" ")
        if (args[0] == "ls"):
            print (self.ls(args[1:]))

    def ls(self, args: list[str]):
        deep = False
        while args:
            arg = args[0]
            if (arg[0] == "-"):
                options = arg[1:].split("")
                for option in options:
                    match option:
                        case "R":
                            deep = True
            args = args[1:]
        return self.filesystem.list_files("", -1 if deep else 0)

cl = CommandLine()
cl.filesystem.setup_system("filesystems/example.txt")
cl.enter_command("ls")