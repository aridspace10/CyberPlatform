from .filenode import FileNode
from .filesystem import FileSystem
from collections import deque
from typing import Literal, Tuple
from .inode import Inode, NodeType
import random
import datetime
from .Parser import Parser, lex, Sequence, Pipe, AndOr, Command, Atom, SimpleCommand, Subshell, VarDeclaration, VarUse
from .ShellState import ShellState

CommandReturn = Tuple[int, Tuple[list[str], list[str]]]

class CommandLine:
    def get_fd(self, path: str, removing: bool = False) -> FileNode | str:
        lst = path.split("/")
        saved_current = self.filesystem.current
        # only go to path if a path is given
        if (len(lst) > 1 and (error := self.filesystem.search("/".join(lst[0:-1]))) != ""):
            self.filesystem.current = saved_current
            return (error)
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
    
    def enter_command(self, raw: str, shell: ShellState) -> Tuple[list[str], list[str]]:
        self.filesystem = shell.fs
        self.filesystem.search(shell.cwd)
        self.shell = shell
        tokens = lex(raw)
        parser = Parser(tokens)
        ast = parser.parse()
        print (ast)
        if isinstance(ast, Sequence):
            shell.ls, (stderr, stdout) = self.execute_sequence(ast.parts)
            return (stderr, stdout)
        else:
            return ([], ["Admin Error: Code AAA112"])

    def execute_pipe(self, parts: list[AndOr]) -> CommandReturn:
        self.fdin = None
        self.fdout = None
        status, stderr, stdout = 0, [], []
        for part in parts:
            self.fdin = self.fdout
            self.fdout = None
            status, (stderr, stdout) = self.execute_andor(part)
        self.fdin = None
        self.fdout = None
        return (status, (stderr, stdout))
    
    def execute_andor(self, elem: AndOr) -> CommandReturn:
        status, (stderr, stdout) = self.execute_command(elem.first)
        for (op, cmd) in elem.rest:
            if ((op == "&&" and not status) or (op == "||" and status)):
                status, (tmperr, tmpout) = self.execute_command(cmd)
                stderr.extend(tmperr)
                stdout.extend(tmpout)
            else:
                break
        return (status, (stderr, stdout))

    def execute_command(self, command: Command) -> CommandReturn:
        redirs = command.pre_redirs + command.post_redirs
        for redir in redirs:
            if (redir.op == "<"):
                self.fdin = self.get_fd(redir.target)
                if (isinstance(self.fdin, str)):
                    return (1, ([self.fdin], []))
            elif (redir.op == ">"):
                self.fdout = self.get_fd(redir.target, True)
                if (isinstance(self.fdout, str)):
                    return (1, ([self.fdout], []))
            elif (redir.op == ">>"):
                self.fdout = self.get_fd(redir.target)
                if (isinstance(self.fdout, str)):
                    return (1, ([self.fdout], []))
        status, (stderr, stdout) = self.execute_atom(command.atom)
        if (isinstance(self.fdout, FileNode)):
            self.fdout.append_data("\n".join(stdout))
            stdout = []
        else:
            inode = Inode(NodeType.FILE)
            inode.set_data("\n".join(stdout))
            self.fdout = FileNode(None, "stdout", inode)
        return (status, (stderr, stdout))

    def execute_atom(self, atom: Atom) -> CommandReturn:
        if (isinstance(atom, SimpleCommand)):
            if self.fdin is None:
                fdin = FileNode(None, "stdin", Inode(NodeType.FILE))
            elif isinstance(self.fdin, str):
                return (1, ([], ["Admin Error: AAA113"]))
            else:
                fdin = self.fdin
            args = []
            for arg in atom.args:
                if (isinstance(arg, VarUse)):
                    args.append(str(self.shell.env[arg.name]))
                else:
                    args.append(arg)
            return self.run_command(args, fdin)
        elif (isinstance(atom, Subshell)):
            return self.execute_sequence(atom.sequence.parts)
        elif (isinstance(atom, VarDeclaration)):
            self.shell.env[atom.name] = atom.value
            return (0, ([], []))

    def execute_sequence(self, parts: list[Pipe]) -> CommandReturn:
        last_status = 0
        stdout, stderr = [], []

        for part in parts:
            last_status, (stdout, stderr) = self.execute_pipe(part.parts)

        return last_status, (stdout, stderr)
 
    def run_command(self, args: list[str], fdin: FileNode) -> CommandReturn:
        match args[0]:
            case "ls":
                return self.ls(args[1:], fdin)
            case "mkdir":
                return self.mkdir(args[1:], fdin)
            case "cd":
                return self.cd(args[1:], fdin)
            case "pwd":
                return self.pwd(args[1:], fdin)
            case "rm":
                return self.rm(args[1:], fdin)
            case "touch":
                return self.touch(args[1:], fdin)
            case "cat":
                return self.cat(args[1:], fdin)
            case "head":
                return self.head(args[1:], fdin)
            case "tail":
                return self.tail(args[1:], fdin)
            case "echo":
                return self.echo(args[1:], fdin)
            case "chmod":
                return self.chmod(args[1:], fdin)
            case "cp":
                return self.cp(args[1:], fdin)
            case "mv":
                return self.mv(args[1:], fdin)
            case "grep":
                return self.grep(args[1:], fdin)
            case "ln":
                return self.ln(args[1:], fdin)
            case "uniq":
                return self.uniq(args[1:], fdin)
            case _:
                return (1, (["Unknown command given"], []))

    # def get_past_command(self) -> None:
    #     r = self.history[self.hpoint]
    #     if (self.hpoint < 0):
    #         self.hpoint -= 1
    #         return r
        
    def useage(self, type: str) -> list[str]:
        output = []
        with open(f"../static/help/{type}.txt") as f:
            for line in f:
                output.append(line)
        return output

    def cp(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
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
        return (1, ([], []))
    
    def mv(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        verbose = False
        clobber = False
        output = ([], [])
        if len(args) < 2 and args[0] != "--help":
            output[0].append("cp: expected at least two arguments")
        files = []
        while len(args) > 1:
            arg = args[0]
            if (arg[0] == "-"):
                if (arg[1] == "-"):
                    if (arg[2:] == "help"):
                        return (0, (self.useage("mv"), []))
                else:    
                    options = arg[1:].split()
                    for option in options:
                        if (option == "v"):
                            verbose = True
                        elif (option == "h"):
                            return (0, (self.useage("mv"), []))
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
                    output[1].append(f"Renamed '${self.filesystem.current.name}' -> '{target}'")
                self.filesystem.current.name = target
                self.filesystem.current = tmp
                return (0, output)
            elif (ftype == NodeType.FILE and ttype == NodeType.DIRECTORY):
                if (self.filesystem.current.parent == None): # literally impossible to be true
                    return (2, ([], []))
                self.filesystem.current = self.filesystem.current.parent
                saved = None
                for idx, item in enumerate(self.filesystem.current.items):
                    if (item.name == files[0]):
                        saved = item
                        self.filesystem.current.items.pop(idx)
                        break
                if (saved == None):
                    return (2, ([], []))
                self.filesystem.search(target)
                self.filesystem.current.items.append(saved)
                if (verbose):
                    output[1].append(f"Moved '${files[0]}' to '{target}'")
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
                output[1].append(f"Moved '${file}' to '${target}'")
            self.filesystem.current = tmp
        return (0, output)
    
    def grep(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
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
        output = ([], [])
        while len(args) and args[0][0] != "\"":
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
                return (0, ([], self.useage("grep")))
            else:
                return (1, (["grep: unknown argument given"], []))
            args = args[1:]
        if (not len(args)):
            return (1, (["grep: pattern not given"], []))
        pattern = args.pop(0).replace("\"", '').replace("\"", '')
        if (not case_sentive):
            pattern = pattern.lower()
        if (len(args)):
            files = args
        else:
            files = ["-"]
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
                    output[1].append(tmp)
                    if (filename and not linenum):
                        return

        for file in files:
            if (file == "-"):
                ty = input.inode.type
                self.filesystem.current = input
            else:
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
                    output[0].append("Can't recursivly search directory without -r option")
            elif (ty == NodeType.FILE):
                search_file(self.filesystem.current)
            else:
                output[0].append(f"Can't open file/directory given: {file}")
            self.filesystem.current = saved_current
        if (countmatch):
            return (0, ([], [str(len(output[1]))]))
        else:
            return (0, output)
    
    def chmod(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        recurse = False
        verbose = False
        output = ([], [])
        if len(args) > 2 and args[0] != "--help":
            output[1].append("chmod: expected at least two arguments")
            return (1, output)
        while len(args) > 2:
            arg = args[0]
            if (arg[0] == "-"):
                if (arg[1:] == "-help"):
                    return (0, ([], self.useage("chmod")))
                options = arg[1:].split()
                for option in options:
                    if (option == "R"):
                        recurse = True
                    elif (option == "v"):
                        verbose = True
                    else:
                        return (1, ([], ["chmod: Unknown output given"]))
                
            args = args[1:]
        permissions = args[0]
        if (len(permissions.rstrip()) != 3):
            output[0].append("chmod: value given for permissions which is not of length of 3")
            return (1, output)
        ORDER = ["user", "group", "public"]
        d = {"user": {"r": False, "w": False, "x": False},
                            "group": {"r": False, "w": False, "x": False},
                            "public": {"r": False, "w": False, "x": False}}
        for idx, permission in enumerate(permissions):
            try:
                if (int(permission) > 7):
                    output[0].append("chmod: value given which is higher then needed")
                    return (1, output)
            except ValueError:
                output[0].append("chmod: value other then given integer given for permissions")
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
                output[0].append(error)
                return (1, output)
            temp = self.filesystem.current.update_permissions(d, recurse, [])
            if (verbose):
                for line in temp:
                    output[1].append(line)
            return (0, output)
        else:
            if (error := self.filesystem.search("/".join(lst[0:-1]))) != "":
                self.current = saved_current
                output[0].append(error)
                return (1, output)
            for idx, item in enumerate(self.filesystem.current.items):
                if (item.name == lst[-1]):
                    self.filesystem.current.items[idx].update_permissions(d, False, [])
                    return (0, output)
        output[0].append("chmod: file given can not be found")
        return (1, output)
    
    def echo(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        output = " ".join(args)
        if (output == "$?"):
            return (0, ([], [(str(self.filesystem.lcs))]))
        return (0, ([], [(" ".join(args))]))

    def touch(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        if "--help" in args:
            return (0, ([], self.useage("touch")))
        files = []
        create = True
        onlychangeaccess = False
        onlychangemod = False
        date = datetime.datetime.now()
        while args:
            arg = args.pop(0)
            if (arg == "-"):
                pass
            elif (arg[0] == "-"):
                if arg[1] == "-":
                    if (arg == "--no-create"):
                        create = False
                    if (arg.startswith("--date=")):
                        date = datetime.datetime.strptime(arg.split("=")[1], "%Y-%m-%d").date()
                else:
                    for option in arg[1:]:
                        match option:
                            case "c":
                                create = False
                            case "a":
                                onlychangeaccess = True
                            case "m":
                                onlychangemod = True
                            case "d":
                                date = datetime.datetime.strptime(args.pop(0), "%Y-%m-%d").date()
                                break
            else:
                files.append(arg)
        return (0, ([], []))

    def cat(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        output = ([], [])
        while len(args) > 1:
            arg = args[0]
            if (arg == "--help"):
                return (0, ([], self.useage("cat")))
            args = args[1:]
        filename = args[0]
        content = self.filesystem.get_file(filename)
        if (content == None or isinstance(content, str)):
            return (1, ([], [f"File {filename} does not exist"]))
        data = content.get_data()
        for line in data.split("\n"):
            output[1].append(line)
        return (0, output)

    def head(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        lines = 10
        b = -1
        curb = 0
        rev = False
        files = []
        output = ([], [])
        while args:
            arg = args.pop(0)
            if (arg == "-"):
                files.append(input)
            elif (arg[0] == "-"):
                if (arg == "--help"):
                    return (0, ([], self.useage("head")))
                elif (arg == "-n"):
                    lines = int(args.pop(0))
                elif (arg.startswith("--lines=")):
                    val = arg.split("=")[1]
                    if (val[0] == "-"):
                        rev = True
                        lines = int(val[1:]) * -1
                    else:
                        lines = int(val[1:])
                elif (arg == "-c"):
                    b = int(args.pop(0))
                elif (arg.startswith("--lines=")):
                    val = arg.split("=")[1]
                    if (val[0] == "-"):
                        rev = True
                        b = int(val[1:]) * -1
                    else:
                        b = int(val[1:])
                else:
                    output[0].append(f"head: Unknown argument (${arg}) given")
            else:
                files.append(arg)
        if (not len(files)):
            files = [input]
        saved_current = self.filesystem.current
        for file in files:
            if (isinstance(file, FileNode)):
                content = file
                ty = content.get_type()
            else: 
                ty = self.filesystem.search_withaccess(file)
                content = self.filesystem.current
            if (ty == NodeType.DIRECTORY):
                output[0].append(f"head: ${file} is a directory")
                continue
            if (content == None or isinstance(content, str)):
                return (1, ([],[]))
            counter = 0
            data = content.get_data()
            for line in data.split("\n"):
                output[1].append(line)
                counter += 1
                curb += len(line.encode("utf-8"))
                if (b == -1 and counter >= lines):
                    break
                if (b != -1 and curb >= b):
                    break
            self.filesystem.current = saved_current
        return (0, output)

    def tail(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        return (0, ([], []))

    def rm(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        recurse, verbose = False, False
        output = ([], [])
        while len(args) > 1:
            arg = args[0]
            if (arg[0] == "-"):
                if (arg == "--help"):
                    return (0, ([], self.useage("rm")))
                options = arg[1:].split()
                for option in options:
                    if (option == "r" or option == "R"):
                        recurse = True
                    elif (option == "-v"):
                        verbose = True
            args = args[1:]
        filename = args[0]
        result = self.filesystem.current.delete_child(filename)
        if (result == None):
            output[0].append(f"{filename} was not found")
        if (verbose):
            output[1].append("File sucessfully deleted")
        return (0, output)

    def pwd(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        ty = "l"
        while len(args) > 1:
            arg = args[0]
            if (arg == "--help"):
                return (0, ([], self.useage("pwd")))
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
        return (0, ([], [direct]))
        
    def mkdir(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        permissions = {"r": True, "w": True, "x": True}
        verbose, parent = False, False
        if (len(args) <= 1) and args[0] != "--help":
            return (0, (["mkdir: at least one argument should be given"], []))
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
                        return (1, (["mkdir: option given to -m or --mode is not correct"], []))
                elif (arg == "-v" or arg == "--verbose"):
                    verbose = True
                elif (arg == "-p" or arg == "--parents"):
                    parent = True
                elif (arg == "-h" or arg == "--help"):
                    return (0, ([], self.useage("mkdir")))
                else:
                    return (1, (["mkdir: unknown argument given"], []))
            else:
                name = arg
        if (name == ""):
            return (1, (["mkdir: no name given for new directory"], []))
        
        saved_current = self.filesystem.current
        err = self.filesystem.add_directory(name, parent, permissions)
        self.filesystem.current = saved_current
        if (err):
            return (1, ([err], []))
        if (verbose):
            return (0, ([], [f"mkdir: sucessfully created ${args[0]}"]))
        return (1, (["mkdir: Unknown error occured"], []))

    def ls(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        deep, detail = False, 0
        extra: dict[str, bool | str] = {}
        oneline = False
        listdir = False
        output = ([], [])
        while args:
            arg = args[0]
            if (arg[0] == "-"):
                if (arg == "--help"):
                    return (0, (self.useage("ls"), []))
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
                            return (2, (["ls: unknown directory given"], []))
            args = args[1:]
        lines = self.filesystem.list_files("", -1 if deep else 0, detail, extra)
        for line in lines: 
            output[1].append(" ".join(line))
        return (0, output)
    
    def find(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        return (1, ([], []))
    
    def cd(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        if (not args):
            return (1, (["cd: must give argument"], []))
        arg = args[0]
        if (error := self.filesystem.search(arg)):
            return (1, ([error], []))
        return (0, ([],[]))
    
    def ln(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        linkty = "hard"
        while len(args) > 2:
            arg = args.pop(0)
            if (arg[0] == "-"):
                if (arg == "--help"):
                    return (0, ([], self.useage("ln")))
                options = arg[1:]
                for option in options:
                    match option:
                        case "s":
                            linkty = "sym"
                        case _:
                            return (2, (["Unknown Argument Given"], []))
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
        return (1, ([],[]))
    
    def uniq(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        count = False
        repeated = False
        printdup = False
        skip = 0
        unique = False
        file = ""
        while args:
            arg = args.pop(0)
            if (arg == "-c" or arg == "--count"):
                count = True
            elif (arg == "-d" or arg == "repeated"):
                repeated = True
            elif (arg == "-D"):
                printdup = True
            elif (arg.startswith("--skip-fields")):
                skip = int(arg.split("=")[1])
            elif (arg == "-f"):
                skip = int(args.pop(0))
            else:
                file = arg
        if (file != ""):
            self.filesystem.search_withaccess(file)
            input = self.filesystem.current
        data = input.get_data().split("\n")
        output = ([], [])
        index = 1
        while (index != len(data)):
            if (data[index-1] != data[index]):
                output[1].append(data[index-1])
        return (0, output)

    def sort(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        if "--help" in args:
            return (0, ([], self.useage("sort.txt")))
        file = ""
        igblanks = False
        reverse = False
        randomize = False
        check = False
        scheck = False
        fold = False
        clean = False
        output = ""
        while args:
            arg = args.pop(0)
            if (arg[0] == "-"):
                if (arg == "-"):
                    file = "-"
                    continue
                for option in arg[1:]:
                    match (arg):
                        case "b":
                            igblanks = True
                        case "r":
                            reverse = True
                        case "R":
                            randomize = True
                        case "o":
                            output = args.pop(0)
                        case "c":
                            check = True
                        case "C":
                            scheck = True
                        case "f":
                            fold = True
                        case "i":
                            clean = True
                        case _:
                            return (2, ([f"sort: unknown option given ({arg})"], []))
        if (file == "" or file == "-"):
            content = input.get_data().split("\n") 
        else:
            saved_current = self.filesystem.current
            self.filesystem.search_withaccess(file)
            content = self.filesystem.current.get_data().split("\n")
            self.filesystem.current = saved_current
        for idx, line in enumerate(content):
            if igblanks:
                content[idx] = line.lstrip()
            if fold:
                content[idx] = line.upper()
            if clean:
                content[idx] = ''.join(c for c in line if c.isprintable())
        modified = sorted(content, reverse=reverse)
        if check or scheck:
            for i in range(0, len(modified)):
                if modified[i] != content[i]:
                    if scheck:
                        return (1, ([], []))
                    else:
                        return (1, ([f"sort: {file}:{i}: disorder: {content[i]}"], []))
            return (0, ([], []))
        if randomize:
            r = []
            while len(modified):
                vid = random.randrange(len(modified))
                while vid > 0 and modified[vid-1] == modified[vid]:
                    vid -= 1
                element = modified.pop(vid)
                r.append(element)
                while vid < len(modified) and modified[vid] == element:
                    r.append(modified.pop(vid))
            modified = r
            return (0, ([], []))
        if output:
            saved_current = self.filesystem.current
            self.filesystem.search_withaccess(file)
            self.filesystem.current.set_data("\n".join(modified))
            self.filesystem.current = saved_current
        return (0, ([], modified))