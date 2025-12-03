from filenode import FileNode
from filesystem import FileSystem

class CommandLine:
    def __init__(self):
        self.filesystem = FileSystem()
        self.history = []
    
    def enter_command(self, raw: str) -> None:
        args = raw.split(" ")
        match args[0]:
            case "ls":
                print (self.ls(args[1:]))
            case "mkdir":
                self.mkdir(args[1:])
    
    def mkdir(self, args: list[str]):
        permissions = {"r": True, "w": True, "x": True}
        verbose, parent = False, False
        while len(args) > 1:
            arg = args[0]
            if (arg == "-m" or arg == "--mode"):
                args = args[1:]
                arg = args[0]
                if (arg.startswith("a=")):
                    permissions = {"r": False, "w": False, "x": False}
                    while arg:
                        match arg[0]:
                            case "r":
                                permissions["r"] = True
                            case "w":
                                permissions["w"] = True
                            case "x":
                                permissions["x"] = True
                        arg = arg[1:]
                else:
                    return "mkdir: option given to -m or --mode is not correct"
            elif (arg == "-v" or arg == "--verbose"):
                verbose = True
            elif (arg == "-p" or arg == "--parents"):
                parent = True
            else:
                return "mkdir: unknown argument given"
            args = args[1:]
        self.filesystem.add_directory(args[0], parent, permissions)
        if (verbose):
            print (f"mkdir: sucessfully created ${args[0]}")

    def ls(self, args: list[str]):
        deep = False
        while args:
            arg = args[0]
            if (arg[0] == "-"):
                options = arg[1:].split()
                for option in options:
                    match option:
                        case "R":
                            deep = True
            args = args[1:]
        return self.filesystem.list_files("", -1 if deep else 0)

cl = CommandLine()
cl.filesystem.setup_system("filesystems/example.txt")
cl.enter_command("ls -R")