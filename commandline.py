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
            case "cd":
                self.cd(args[1:])
            case "pwd":
                self.pwd()
            case "rm":
                self.rm(args[1:])
            case "touch":
                self.touch(args[1:])
            case "cat":
                self.cat(args[1:])
            case "head":
                self.head(args[1:])
            case "tail":
                self.tail(args[1:])
            case "echo":
                self.echo(args[1:])
    
    def echo(self, args: list[str]):
        print (" ".join(args))

    def touch(self, args: list[str]):
        pass 

    def cat(self, args: list[str]):
        while len(args) > 1:
            arg = args[0]
            pass
            args = args[1:]
        filename = args[0]
        content = self.filesystem.get_file(filename)
        if (content == None or isinstance(content, str)):
            return None
        for line in content.data.split("\n"):
            print (line)

    def head(self, args: list[str]):
        num = 10
        while len(args) > 1:
            arg = args[0]
            if (arg == "-n"):
                args = args[1:]
                num = int(args[0])
            args = args[1:]
        filename = args[0]
        content = self.filesystem.get_file(filename)
        if (content == None or isinstance(content, str)):
            return None
        counter = 0
        for line in content.data.split("\n"):
            print (line)
            counter += 1
            if (counter >= num):
                break

    def tail(self, args: list[str]):
        pass

    def rm(self, args: list[str]):
        recurse, verbose = False, False
        while len(args) > 1:
            arg = args[0]
            if (arg[0] == "-"):
                options = arg[1:].split()
                for option in options:
                    if (option == "r" or option == "R"):
                        recurse = True
                    elif (option == "-v"):
                        verbose = True
            args = args[1:]
        filename = args[0]
        result = self.filesystem.current.delete_child(filename)
        if (verbose):
            if (result == None):
                print("No file deleted")
            else:
                print("File sucessfully deleted")

    def pwd(self):
        pointer = self.filesystem.current
        direct = ""
        while (pointer != None):
            if (direct):
                direct = pointer.name + "/" + direct
            else:
                direct = pointer.name
            pointer = pointer.parent
        print (direct)
        
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
    
    def cd(self, args: list[str]):
        arg = args[0]
        if (error := self.filesystem.search(arg)):
            print (error)


cl = CommandLine()
cl.filesystem.setup_system("filesystems/example.txt")
cl.enter_command("ls -R")
cl.enter_command("mkdir d3")
cl.enter_command("pwd")
cl.enter_command("cd ..")
cl.enter_command("ls -R")
cl.enter_command("echo \"Fornite battle pass\"")