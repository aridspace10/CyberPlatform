from filenode import FileNode
from filesystem import FileSystem
from collections import deque

class CommandLine:
    def __init__(self):
        self.filesystem = FileSystem()
        self.history = []
        self.hpoint = -1
    
    def enter_command(self, raw: str) -> None:
        self.history.append(raw)
        self.hpoint = len(self.history)
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
            case "chmod":
                self.chmod(args[1:])
            case "cp":
                self.cp(args[1:])
            case "mv":
                self.mv(args[1:])

    def get_past_command(self) -> None:
        r = self.history[self.hpoint]
        self.hpoint -= 1
        return r

    def cp(self, args: list[str]):
        recurse = False
        verbose = False
        files = []
        while len(args) > 1:
            arg = args[0]
            if (arg[0] == "-"):
                options = arg[1:].split()
                for option in options:
                    if (option == "v"):
                        verbose = True
            else:
                files.append(arg)
            args = args[1:]
        target = args[0]

    def mv_useage(self):
        print("mv [OPTION]... SOURCE DEST\nmv [OPTION]... SOURCE... DIRECTORY")
        print("Move or rename files.")
    
    def mv(self, args: list[str]):
        verbose = False
        clobber = False
        if len(args) > 2:
            print("cp: expected at least two arguments")
        files = []
        while len(args) > 1:
            arg = args[0]
            if (arg[0] == "-"):
                if (arg[1] == "-"):
                    if (arg[2:] == "help"):
                        self.mv_useage()
                else:    
                    options = arg[1:].split()
                    for option in options:
                        if (option == "v"):
                            verbose = True
                        elif (option == "h"):
                            self.mv_useage()
            else:
                files.append(arg)
            args = args[1:]
        target = args[0]
        if (len(files) == 1):
            ftype = self.filesystem.search_withaccess(files[0])
            ttype = "directory" if len(target.split(".")) == 1 else "file"
            if ftype == ttype:
                if (verbose):
                    print(f"Renamed '${self.filesystem.current.name}' -> '{target}'")
                self.filesystem.current.name = target
                return

        tmp = self.filesystem.current
        self.filesystem.search_withaccess(target)
        targetfnode = self.filesystem.current
        self.filesystem.current = tmp
        for file in files:
            ftype = self.filesystem.search_withaccess(file)
            if (ftype == None):
                continue
            fnode = self.filesystem.current
            self.filesystem.current = targetfnode
            self.filesystem.current.items.append((fnode, ftype))
            if verbose:
                print(f"Moved '${file}' to '${target}'")
            self.filesystem.current = tmp
    
    def chmod(self, args: list[str]):
        recurse = False
        verbose = False
        if len(args) > 2:
            print("chmod: expected at least two arguments")
        while len(args) > 2:
            arg = args[0]
            if (arg[0] == "-"):
                options = arg[1:].split()
                for option in options:
                    if (option == "R"):
                        recurse = True
                    elif (option == "v"):
                        verbose = True
            args = args[1:]
        permissions = args[0]
        if (len(permissions.rstrip()) != 3):
            print("chmod: value given for permissions which is not of length of 3")
            return
        ORDER = ["user", "group", "public"]
        d = {"user": {"r": False, "w": False, "x": False},
                            "group": {"r": False, "w": False, "x": False},
                            "public": {"r": False, "w": False, "x": False}}
        for idx, permission in enumerate(permissions):
            try:
                if (int(permission) > 7):
                    print("chmod: value given which is higher then needed")
            except ValueError:
                print("chmod: value other then given integer given for permissions")
                return
            finally:
                permission = int(permission)
                bits = [(permission >> i) & 1 for i in range(7, -1, -1)]
                d[ORDER[idx]]["x"] = bool(bits[-1])
                d[ORDER[idx]]["w"] = bool(bits[-2])
                d[ORDER[idx]]["r"] = bool(bits[-3])
        file = args[1]
        saved_current = self.filesystem.current
        lst = file.split("/")
        if (error := self.filesystem.search("/".join(lst[0:-1]))) != "":
            self.current = saved_current
            return error
        for idx, item in enumerate(self.filesystem.current.items):
            if (item[0].name == lst[-1]):
                self.filesystem.current.items[idx][0].update_permissions(d)
                return
        print ("chmod: file given can not be found")
    
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
        deep, detail = False, 0
        while args:
            arg = args[0]
            if (arg[0] == "-"):
                options = arg[1:].split()
                for option in options:
                    match option:
                        case "R":
                            deep = True
                        case "l":
                            detail = 1
            args = args[1:]
        lines = self.filesystem.list_files("", -1 if deep else 0, detail)
        for line in lines:
            if (not detail):
                print(line)
            else:
                print(" ".join(line))
    
    def cd(self, args: list[str]):
        arg = args[0]
        if (error := self.filesystem.search(arg)):
            print (error)


cl = CommandLine()
cl.filesystem.setup_system("filesystems/example.txt")
cl.enter_command("mkdir d3")
cl.enter_command("cd ..")
cl.enter_command("chmod 000 f1.txt")
cl.enter_command("rm f2.txt")
cl.enter_command("mv f1.txt d1")
cl.enter_command("ls -R")
cl.enter_command("echo \"Fornite battle pass\"")