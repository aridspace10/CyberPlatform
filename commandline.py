from filenode import FileNode
from filesystem import FileSystem
from collections import deque
from typing import Literal, Tuple
from inode import Inode, NodeType

class CommandLine:
    def __init__(self):
        self.filesystem = FileSystem()
        self.history = []
        self.hpoint = -1
        self.lcs = 0

    def get_fd(self, path: str, removing: bool = False) -> FileNode:
        lst = path.split("/")
        saved_current = self.filesystem.current
        # only go to path if a path is given
        if (len(lst) > 1 and (error := self.filesystem.search("/".join(lst[0:-1]))) != ""):
            self.filesystem.current = saved_current
            print (error)
        for idx, item in enumerate(self.filesystem.current.items):
            if item.name == lst[-1]:
                if (removing):
                    item.set_data("")
                return item
        inode = Inode(NodeType.FILE)
        self.filesystem.current.add_child(lst[-1], inode)  
        self.filesystem.search_withaccess(lst[-1]) # search with access will set new filenode as self.filesystem.current
        result = self.filesystem.current
        self.filesystem.current = saved_current
        return result
    
    def enter_command(self, raw: str) -> None:
        self.history.append(raw)
        self.hpoint = len(self.history)
        commands = raw.split("|")
        fdin, fdout = None, None
        for idx, command in enumerate(commands):
            lst = command.split(" ")
            args = []
            while lst:
                arg = lst.pop(0)
                if (arg == "<"):
                    fdin = self.get_fd(lst.pop(0))
                elif (arg == ">"):
                    fdout = self.get_fd(lst.pop(0), True)
                elif (arg == ">>"):
                    fdout = self.get_fd(lst.pop(0))
                else:
                    args.append(arg)
            input = fdin.get_data().split("\n") if fdin else []
            self.lcs, output = self.run_command(" ".join(args), input)
            # stdout given
            if fdout is not None:
                fdout.append_data("\n".join(output))
            # last command
            elif idx + 1 == len(commands):
                for line in output:
                    print (line)
                return
            # more commands to go
            else:
                inode = Inode(NodeType.FILE)
                inode.set_data("\n".join(output))
                fdout = FileNode(None, "stdout", inode)
            fdin = fdout
            fdout = None
        """
        args = raw.split(" ")
        output: list[str] = []
        if (any(x in args for x in ["<", ">", ">>", "<<"])):
            for ch in ("<", ">", ">>", "<<"):
                if ch in args:
                    idx = args.index(ch)
                    self.lcs, output = self.run_command(" ".join(args[0:idx]))
                    args = args[idx + 1:]
                    if (len(args) > 1):
                        print ("Not implemtned")
                    else:
                        lst = args[0].split("/")
                        saved_current = self.filesystem.current
                        # only go to path if a path is given
                        if (len(lst) > 1 and (error := self.filesystem.search("/".join(lst[0:-1]))) != ""):
                            self.filesystem.current = saved_current
                            print (error)
                        for idx, item in enumerate(self.filesystem.current.items):
                            if item.name == lst[-1]:
                                if ch == ">":
                                    self.filesystem.current.items[idx].set_data("\n".join(output))
                                    return
                                elif ch == ">>":
                                    self.filesystem.current.items[idx].append_data("\n".join(output))
                                    return
                        # Reaches here if no item found
                        inode = Inode(NodeType.FILE)
                        self.filesystem.current.add_child(lst[-1], inode)       
                        self.filesystem.search_withaccess(lst[-1])
                        if ch == ">":
                            self.filesystem.current.set_data("\n".join(output))
                            self.filesystem.current = saved_current
                            return
                        elif ch == ">>":
                            self.filesystem.current.append_data("\n".join(output))
                            self.filesystem.current = saved_current
                            return
            else:
                idx = -1
        else:
            self.lcs, output = self.run_command(" ".join(args[0:idx]))
            for line in output:
                print (line)
        """
    def run_command(self, raw: str, fdin: list[str] = []) -> Tuple[int, list[str]]:
        args = raw.split(" ")
        match args[0]:
            case "ls":
                return self.ls(args[1:])
            case "mkdir":
                return self.mkdir(args[1:])
            case "cd":
                return self.cd(args[1:])
            case "pwd":
                return self.pwd(args[1:])
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
            case "grep":
                return self.grep(args[1:])
            case "ln":
                return self.ln(args[1:])
            case _:
                return ["Unknown command given"]

    def get_past_command(self) -> None:
        r = self.history[self.hpoint]
        if (self.hpoint < 0):
            self.hpoint -= 1
            return r
        
    def useage(self, type: str) -> list[str]:
        output = []
        with open(f"static/help/{type}.txt") as f:
            for line in f:
                output.append(line)
        return output

    def cp(self, args: list[str]) -> Tuple[int, list[str]]:
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
        return (1, [])
    
    def mv(self, args: list[str]) -> Tuple[int, list[str]]:
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
                        return (0, self.useage("mv"))
                else:    
                    options = arg[1:].split()
                    for option in options:
                        if (option == "v"):
                            verbose = True
                        elif (option == "h"):
                            return (0, self.useage("mv"))
            else:
                files.append(arg)
            args = args[1:]
        target = args[0]
        tmp = self.filesystem.current
        if (len(files) == 1):
            ftype = self.filesystem.search_withaccess(files[0])
            ttype = NodeType.DIRECTORY if len(target.split(".")) == 1 else NodeType.FILE
            if ftype == ttype:
                if (verbose):
                    output.append(f"Renamed '${self.filesystem.current.name}' -> '{target}'")
                self.filesystem.current.name = target
                self.filesystem.current = tmp
                return (0, output)
            elif (ftype == NodeType.FILE and ttype == NodeType.DIRECTORY):
                if (self.filesystem.current.parent == None): # literally impossible to be true
                    return []
                self.filesystem.current = self.filesystem.current.parent
                saved = None
                for idx, item in enumerate(self.filesystem.current.items):
                    if (item.name == files[0]):
                        saved = item
                        self.filesystem.current.items.pop(idx)
                        break
                if (saved == None):
                    return []
                self.filesystem.search(target)
                self.filesystem.current.items.append(saved)
                if (verbose):
                    output.append(f"Moved '${files[0]}' to '{target}'")
                self.filesystem.current = tmp
                return (0, output)
        # multiple files were given
        self.filesystem.search_withaccess(target)
        targetfnode = self.filesystem.current
        self.filesystem.current = tmp
        for file in files:
            ftype = self.filesystem.search_withaccess(file)
            if (ftype == None):
                continue
            fnode = self.filesystem.current
            self.filesystem.current = targetfnode
            self.filesystem.current.items.append(fnode)
            if verbose:
                output.append(f"Moved '${file}' to '${target}'")
            self.filesystem.current = tmp
        return (0, output)
    
    def grep(self, args: list[str]) -> Tuple[int, list[str]]:
        case_sentive = False
        invert = False
        linenum = False
        filename = False
        countmatch = False
        matchwhole = False
        matchline = False
        showmatched = False
        quiet = False
        recursive = False
        include = []
        exclude = []
        output = []
        while args[0][0] != "\"":
            arg = args[0]
            if (arg[0] == "-"):
                for option in args[1:]:
                    match (option):
                        case "i":
                            case_sentive = True
                        case "v":
                            invert = True
                        case "n":
                            linenum = True
                        case "l":
                            filename = True
                        case "c":
                            countmatch = True
                        case "w":
                            matchwhole = True
                        case "x":
                            matchline = True
                        case "o":
                            showmatched = True
                        case "q":
                            quiet = True
                        case "r":
                            recursive = True
            if (arg.startswith("--include=")):
                lst = arg[0].split("=")
                include.append(lst[1])
            elif (arg.startswith("--exclude-dir=")):
                lst = arg[0].split("=")
                exclude.append(lst[1])
            elif (arg == "--help"):
                return self.useage("grep")
            else:
                return (1, ["grep: unknown argument given"])
            args = args[1:]

        pattern = args[0].replace("\"", '').replace("\"", '')
        if (not case_sentive):
            pattern = pattern.lower()
        files = args[1:]
        saved_current = self.filesystem.current
        
        if (matchwhole):
            match_cond_func = lambda line: len([w for w in line if pattern == w])
        elif (matchline):
            match_cond_func = lambda line: line == pattern
        else:
            # if the pattern exists in the line, there will be an element in the string comp
            match_cond_func = lambda line: len([w for w in line.split() if pattern in w])

        def search_file(item: FileNode) -> None:
            lst = item.get_data().split("\n")
            for idx, line in enumerate(lst):
                if (not case_sentive):
                    line = line.lower()
                if ((l := match_cond_func(line)) and not invert) or (l == 0 and invert):
                    if (filename):
                        tmp = item.name
                    elif (showmatched):
                        tmp = [w for w in line.split() if pattern in w][0]
                    else:
                        tmp = line
                    if (linenum):
                        tmp = f"${idx}: ${tmp}"
                    output.append(tmp)
                    if (filename and not linenum):
                        return

        for file in files:
            ty = self.filesystem.search_withaccess(file)
            if (ty == NodeType.DIRECTORY):
                if (recursive):
                    def recursively_search(pointer: FileNode):
                        for item in pointer.items:
                            if item.get_type() == NodeType.DIRECTORY:
                                recursively_search(item)
                            else:
                                search_file(item)
                    pointer = self.filesystem.current
                    recursively_search(pointer)
                else:
                    output.append("Can't recursivly search directory without -r option")
            elif (ty == NodeType.FILE):
                search_file(self.filesystem.current)
            else:
                output.append(f"Can't open file/directory given: {file}")
            self.filesystem.current = saved_current
        if (countmatch):
            return (0, [str(len(output))])
        else:
            return (0, output)
    
    def chmod(self, args: list[str]) -> Tuple[int, list[str]]:
        recurse = False
        verbose = False
        output = []
        if len(args) > 2:
            output.append("chmod: expected at least two arguments")
            return (1, output)
        while len(args) > 2:
            arg = args[0]
            if (arg[0] == "-"):
                if (arg[1:] == "-help"):
                    return (0, self.useage("chmod"))
                options = arg[1:].split()
                for option in options:
                    if (option == "R"):
                        recurse = True
                    elif (option == "v"):
                        verbose = True
                    else:
                        return (1, ["chmod: Unknown output given"])
                
            args = args[1:]
        permissions = args[0]
        if (len(permissions.rstrip()) != 3):
            output.append("chmod: value given for permissions which is not of length of 3")
            return (1, output)
        ORDER = ["user", "group", "public"]
        d = {"user": {"r": False, "w": False, "x": False},
                            "group": {"r": False, "w": False, "x": False},
                            "public": {"r": False, "w": False, "x": False}}
        for idx, permission in enumerate(permissions):
            try:
                if (int(permission) > 7):
                    output.append("chmod: value given which is higher then needed")
                    return (1, output)
            except ValueError:
                output.append("chmod: value other then given integer given for permissions")
                return (1, output)
            finally:
                permission = int(permission)
                bits = [(permission >> i) & 1 for i in range(7, -1, -1)]
                d[ORDER[idx]]["x"] = bool(bits[-1])
                d[ORDER[idx]]["w"] = bool(bits[-2])
                d[ORDER[idx]]["r"] = bool(bits[-3])
        file = args[1]
        saved_current = self.filesystem.current
        lst = file.split("/")
        if ("." in lst[-1].split()):
            if (error := self.filesystem.search(file)) != "":
                self.current = saved_current
                output.append(error)
                return (1, output)
            output = self.filesystem.current.update_permissions(d, recurse, [])
            if (verbose):
                for line in output:
                    output.append(line)
            return (0, output)
        else:
            if (error := self.filesystem.search("/".join(lst[0:-1]))) != "":
                self.current = saved_current
                output.append(error)
                return (1, output)
            for idx, item in enumerate(self.filesystem.current.items):
                if (item.name == lst[-1]):
                    self.filesystem.current.items[idx].update_permissions(d, False, [])
                    return (0, output)
        output.append("chmod: file given can not be found")
        return (1, output)
    
    def echo(self, args: list[str]) -> Tuple[int, list[str]]:
        output = " ".join(args)
        if (output == "$?"):
            return (0, [(str(self.lcs))])
        return (0, [(" ".join(args))])

    def touch(self, args: list[str]) -> Tuple[int, list[str]]:
        return (0, [])

    def cat(self, args: list[str]) -> Tuple[int, list[str]]:
        output = []
        while len(args) > 1:
            arg = args[0]
            if (arg == "--help"):
                return (0, self.useage("cat"))
            args = args[1:]
        filename = args[0]
        content = self.filesystem.get_file(filename)
        if (content == None or isinstance(content, str)):
            return (1, [f"File {filename} does not exist"])
        data = content.get_data()
        for line in data.split("\n"):
            output.append(line)
        return (0, output)

    def head(self, args: list[str]) -> Tuple[int, list[str]]:
        num = 10
        output = []
        while len(args) > 1:
            arg = args[0]
            if (arg == "--help"):
                return (0, self.useage("head"))
            if (arg == "-n"):
                args = args[1:]
                num = int(args[0])
            args = args[1:]
        filename = args[0]
        content = self.filesystem.get_file(filename)
        if (content == None or isinstance(content, str)):
            return []
        counter = 0
        data = content.get_data()
        for line in data.split("\n"):
            output.append(line)
            counter += 1
            if (counter >= num):
                break
        return (0, output)

    def tail(self, args: list[str]) -> Tuple[int, list[str]]:
        return []

    def rm(self, args: list[str]) -> Tuple[int, list[str]]:
        recurse, verbose = False, False
        output = []
        while len(args) > 1:
            arg = args[0]
            if (arg[0] == "-"):
                if (arg == "--help"):
                    return (0, self.useage("rm"))
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
                output.append("No file deleted")
            else:
                output.append("File sucessfully deleted")
        return (0, output)

    def pwd(self, args: list[str]) -> Tuple[int, list[str]]:
        ty = "l"
        while len(args) > 1:
            arg = args[0]
            if (arg == "--help"):
                return (0, self.useage("pwd"))
            elif (arg == "-l"):
                ty = "l"
            elif (arg == "-p"):
                ty = "p"
            args = args[1:]
        pointer = self.filesystem.current
        direct = ""
        while (pointer != None):
            if (direct):
                direct = pointer.name + "/" + direct
            else:
                direct = pointer.name
            pointer = pointer.parent
        return (0, [direct])
        
    def mkdir(self, args: list[str]) -> Tuple[int, list[str]]:
        permissions = {"r": True, "w": True, "x": True}
        verbose, parent = False, False
        if (len(args) <= 1):
            return (0, ["mkdir: at least one argument should be given"])
        name = ""
        while len(args) > 0:
            arg = args.pop(0)
            if (arg[0] == "-"): 
                if (arg == "-m" or arg == "--mode"):
                    arg = args.pop(0)
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
                        return ["mkdir: option given to -m or --mode is not correct"]
                elif (arg == "-v" or arg == "--verbose"):
                    verbose = True
                elif (arg == "-p" or arg == "--parents"):
                    parent = True
                elif (arg == "-h" or arg == "--help"):
                    return (0, self.useage("mkdir"))
                else:
                    return (1, ["mkdir: unknown argument given"])
            else:
                name = arg
        if (name == ""):
            return (1, ["mkdir: no name given for new directory"])
        
        saved_current = self.filesystem.current
        err = self.filesystem.add_directory(name, parent, permissions)
        self.filesystem.current = saved_current
        if (err):
            return (1, [err])
        if (verbose):
            return (0, [f"mkdir: sucessfully created ${args[0]}"])
        return (1, ["mkdir: Unknown error occured"])

    def ls(self, args: list[str]) -> Tuple[int, list[str]]:
        deep, detail = False, 0
        extra: dict[str, bool | str] = {}
        oneline = False
        listdir = False
        output = []
        while args:
            arg = args[0]
            if (arg[0] == "-"):
                if (arg == "--help"):
                    return (0, self.useage("ls"))
                options = arg[1:]
                for option in options:
                    match option:
                        case "R":
                            deep = True
                        case "l":
                            detail = 1
                        case "i":
                            extra["inode"] = True
                        case "1":
                            oneline = True
                        case "a":
                            extra["showhiddenall"] = True
                        case "A":
                            extra["showhidden"] = True
                        case "d":
                            extra["listdir"] = True
                        case "h":
                            extra["humanreadable"] = True
                        case "s":
                            extra["showblocks"] = True
                        case "t":
                            extra["sortby"] = "mod"
                        case "c":
                            extra["sortby"] = "ctime"
                        case "u":
                            extra["sortby"] = "atime"
                        case "r":
                            extra["reverse"] = True
                        case "S":
                            extra["sortby"] = "size"
                        case "X":
                            extra["sortby"] = "ext"
                        case _:
                            return (2, ["ls: unknown directory given"])
            args = args[1:]
        lines = self.filesystem.list_files("", -1 if deep else 0, detail, extra)
        for line in lines: 
            output.append(" ".join(line))
        return (0, output)
    
    def find(self, args: list[str]) -> Tuple[int, list[str]]:
        return (1, [])
    
    def cd(self, args: list[str]) -> Tuple[int, list[str]]:
        arg = args[0]
        if (error := self.filesystem.search(arg)):
            return (1, [error])
        return (0, [])
    
    def ln(self, args: list[str]) -> Tuple[int, list[str]]:
        linkty = "hard"
        while len(args) > 2:
            arg = args.pop(0)
            if (arg[0] == "-"):
                if (arg == "--help"):
                    return self.useage("ln")
                options = arg[1:]
                for option in options:
                    match option:
                        case "s":
                            linkty = "sym"
                        case _:
                            return (2, ["Unknown Argument Given"])
        target = args[0]
        destination = args[1]
        saved_current = self.filesystem.current
        self.filesystem.search_withaccess(target)
        target_inode = self.filesystem.current.inode
        self.filesystem.current = saved_current
        self.filesystem.add(destination)
        if (linkty == "hard"):
            self.filesystem.current.inode = target_inode
            self.filesystem.current.inode.link_count += 1
        else:
            inode = Inode(NodeType.SYMLINK)
            inode.data = target
            self.filesystem.current.inode = inode
        self.filesystem.current = saved_current
        return (1, [])

cl = CommandLine()
cl.filesystem.setup_system("filesystems/example.txt")
while (1):
    command = input("Input: ")
    cl.enter_command(command)