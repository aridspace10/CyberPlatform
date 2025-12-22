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
        output: list[str] = []
        if (any(x in args for x in ["<", ">"])):
            for ch in ("<", ">"):
                if ch in args:
                    idx = args.index(ch)
                    output = self.run_command(" ".join(args[0:idx]))
                    args = args[idx + 1:]
                    if (len(args) > 1):
                        print ("Not implemtned")
                    else:
                        lst = args[0].split("/")
                        saved_current = self.filesystem.current
                        if (len(lst) > 1 and (error := self.filesystem.search("/".join(lst[0:-1]))) != ""):
                            self.filesystem.current = saved_current
                            print (error)
                        for idx, item in enumerate(self.filesystem.current.items):
                                if item[0].name == lst[-1]:
                                    if ch == ">":
                                        self.filesystem.current.items[idx][0].set_data("\n".join(output))
                                        return
                                    elif ch == ">>":
                                        self.filesystem.current.items[idx][0].append_data("\n".join(output))
                                        return
                        # Reaches here if no item found
                        self.filesystem.current.add_child(lst[-1], 'file')       
                        self.filesystem.search_withaccess(lst[-1])
                        if ch == ">":
                            self.filesystem.current.set_data("\n".join(output))
                            return
                        elif ch == ">>":
                            self.filesystem.current.append_data("\n".join(output))
                            return             
            else:
                idx = -1
        else:
            output = self.run_command(" ".join(args))
            for line in output:
                print (line)

    def run_command(self, raw: str) -> list[str]:
        args = raw.split(" ")
        match args[0]:
            case "ls":
                return (self.ls(args[1:]))
            case "mkdir":
                return self.mkdir(args[1:])
            case "cd":
                return self.cd(args[1:])
            case "pwd":
                return self.pwd()
            case "rm":
                return self.rm(args[1:])
            case "touch":
                return self.touch(args[1:])
            case "cat":
                return self.cat(args[1:])
            case "head":
                return self.head(args[1:])
            case "tail":
                return self.tail(args[1:])
            case "echo":
                return self.echo(args[1:])
            case "chmod":
                return self.chmod(args[1:])
            case "cp":
                return self.cp(args[1:])
            case "mv":
                return self.mv(args[1:])

    def get_past_command(self) -> None:
        r = self.history[self.hpoint]
        if (self.hpoint < 0):
            self.hpoint -= 1
            return r

    def cp(self, args: list[str]) -> list[str]:
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
        return []

    def mv_useage(self) -> list[str]:
        output = []
        output.append("mv [OPTION]... SOURCE DEST\nmv [OPTION]... SOURCE... DIRECTORY")
        output.append("Move or rename files.")
        return output
    
    def mv(self, args: list[str]) -> list[str]:
        verbose = False
        clobber = False
        output = []
        if len(args) > 2:
            output.append("cp: expected at least two arguments")
        files = []
        while len(args) > 1:
            arg = args[0]
            if (arg[0] == "-"):
                if (arg[1] == "-"):
                    if (arg[2:] == "help"):
                        return self.mv_useage()
                else:    
                    options = arg[1:].split()
                    for option in options:
                        if (option == "v"):
                            verbose = True
                        elif (option == "h"):
                            return self.mv_useage()
            else:
                files.append(arg)
            args = args[1:]
        target = args[0]
        if (len(files) == 1):
            ftype = self.filesystem.search_withaccess(files[0])
            ttype = "directory" if len(target.split(".")) == 1 else "file"
            if ftype == ttype:
                if (verbose):
                    output.append(f"Renamed '${self.filesystem.current.name}' -> '{target}'")
                self.filesystem.current.name = target
                return output

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
                output.append(f"Moved '${file}' to '${target}'")
            self.filesystem.current = tmp
        return output
    
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
        if ("." in lst[-1].split("")):
            if (error := self.filesystem.search(file)) != "":
                self.current = saved_current
                return error
            output = self.filesystem.current.update_permissions(d, recurse, [])
            if (verbose):
                for line in output:
                    print (line)
        else:
            if (error := self.filesystem.search("/".join(lst[0:-1]))) != "":
                self.current = saved_current
                return error
            for idx, item in enumerate(self.filesystem.current.items):
                if (item[0].name == lst[-1]):
                    self.filesystem.current.items[idx][0].update_permissions(d, False, [])
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