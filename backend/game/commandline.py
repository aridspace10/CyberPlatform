from game.filenode import FileNode
from game.filesystem import FileSystem
from collections import deque
from typing import Literal, Tuple
from game.inode import Inode, NodeType
import random
import datetime
from .helpers import determine_perms_fromstr
from game.Parser import CommandParser, lex, Sequence, Pipe, AndOr, Command, Atom, SimpleCommand, Subshell, VarDeclaration, VarUse, FindParser, AndNode, OrNode, NotNode, FilterNode
from game.ShellState import ShellState
import copy

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
                self.filesystem.current = saved_current
                return item
        inode = Inode(NodeType.FILE)
        self.filesystem.current.add_child(lst[-1], inode)  
        self.filesystem.search_withaccess(lst[-1]) # search with access will set new filenode as self.filesystem.current
        result = self.filesystem.current
        self.filesystem.current = saved_current
        return result
    
    def enter_command(self, raw: str, shell: ShellState) -> Tuple[list[str], list[str]]:
        self.filesystem = shell.fs
        if (self.filesystem.cwd != shell.cwd):
            self.filesystem.search(shell.cwd)
            self.filesystem.cwd = shell.cwd
        self.shell = shell
        tokens = lex(raw)
        parser = CommandParser(tokens)
        ast = parser.parse()
        if isinstance(ast, Sequence):
            shell.ls, (stderr, stdout) = self.execute_sequence(ast.parts)
            return (stderr, stdout)
        else:
            return ([], ["Admin Error: Code AAA112"]) 

    def execute_pipe(self, parts: list[AndOr]) -> CommandReturn:
        status = 0
        stderr, stdout = [], []

        prev_pipe = None  # holds virtual pipe between commands

        for part in parts:
            # feed previous pipe into next command
            self.fdin = prev_pipe
            self.fdout = None

            status, (stderr, stdout) = self.execute_andor(part)

            # create a new pipe from stdout for next command
            if stdout:
                pipe_inode = Inode(NodeType.FILE)
                pipe_node = FileNode(None, "pipe", pipe_inode)
                pipe_node.set_data("\n".join(stdout))
                prev_pipe = pipe_node
            else:
                prev_pipe = None

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
        for assign in command.assignments:
            self.shell.vars[assign.name] = assign.value.parts[0]

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
        if command.pre_redirs or command.post_redirs:
            if isinstance(self.fdout, FileNode):
                self.fdout.append_data("\n".join(stdout))
                stdout = []
        else:
            # No redirection → leave stdout alone
            self.fdout = None
        return (status, (stderr, stdout))

    def execute_atom(self, atom: Atom) -> CommandReturn:
        if (isinstance(atom, SimpleCommand)):
            if self.fdin is None:
                fdin = FileNode(None, "stdin", Inode(NodeType.FILE))
                fdin.set_data("")
            elif isinstance(self.fdin, str):
                return (1, ([], ["Admin Error: AAA113"]))
            else:
                fdin = self.fdin
            args = []
            for arg in atom.args:
                word = ""
                for part in arg.parts:
                    if isinstance(part, str):
                        word += part
                    else:
                        if part.name not in self.shell.vars:
                            return (1, ([f'Var Used which is unassigned: {part.name}'], []))
                        word += self.shell.vars[part.name]
                args.append(word)
            return self.run_command(args, fdin)
        else:
            # save state
            saved_cwd = self.shell.cwd
            saved_env = self.shell.vars.copy()
            saved_fs_current = self.filesystem.current
            saved_fs_cwd = self.filesystem.cwd
            saved_fdin = self.fdin
            saved_fdout = self.fdout
            #execute
            status, (stderr, stdout) = self.execute_sequence(atom.sequence.parts)
            #restore state
            self.shell.cwd = saved_cwd
            self.shell.vars = saved_env
            self.filesystem.current = saved_fs_current
            self.filesystem.cwd = saved_fs_cwd
            self.fdin = saved_fdin
            self.fdout = saved_fdout
            return (status, (stderr, stdout))

    def execute_sequence(self, parts: list[Pipe]) -> CommandReturn:
        last_status = 0
        stdout, stderr = [], []

        for part in parts:
            last_status, (stdout, stderr) = self.execute_pipe(part.parts)

        return last_status, (stdout, stderr)
 
    def run_command(self, args: list[str], fdin: FileNode) -> CommandReturn:
        print (args)
        if (not (len(args))):
            return (0, ([], []))
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
            case "sort":    
                return self.sort(args[1:], fdin)
            case "find":
                return self.find(args[1:], fdin)
            case "sed":
                return self.sed(args[1:], fdin)
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
    
    def find(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        if (len(args) < 1):
            return (1, (["find: atleast one argument needs to be given"], []))
        while (len(args) and args[0][0] == "-"):
            arg = args.pop(0)
        if (not len(args)):
            return (1, (["find: starting locaiton needs to be given"], []))
        starting = []
        while len(args) and not args[0].startswith("-") and args[0] not in ["(", "!", ")"]:
            starting.append(args.pop(0))
        if (not len(starting)):
            starting = ["."]
        if (not len(args)):
            node = FilterNode("","")
        else:
            fparser = FindParser(args)
            try:
                node = fparser.parse()
            except Exception as e:
                return (2, ([f"find: {str(e)}"], []))
        output = ([], [])
        for start in starting:
            if (err := self.filesystem.search(start)):
                output[0].append(err)
                continue

            start_node = self.filesystem.current   # AFTER search
            (toprints, execs) = start_node.find(node, ".")
            output[1].extend(toprints)
        return (0, output)
    
    def sed(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        if "--help" in args:
            return (0, ([], self.useage("sed")))
        if (len(args) < 1):
            return (2, (["sed [OPTION]... {script-only-if-no-other-script} [input-file]..."], []))
        files = []
        expressions = []
        backup = ""
        while (len(args) and args[0][0] == "-"):
            arg = args.pop(0)
            if (arg.startswith("--file=")):
                files.append(arg.split("=")[1])
            elif (arg.startswith("--expression=")):
                expressions.append(arg.split("=")[1])
            elif (arg.startswith("-i.")):
                backup = arg
            else:
                for option in arg[1:]:
                    match (option):
                        case ("f"):
                            files.append(args.pop(0))
                        case ("e"):
                            expressions.append(args.pop(0))
                        case ("i"):
                            backup = "-i"
                        case _:
                            return (1, ([f"sed: unknown option given - {option}"], []))

        while (len(args)):
            arg = args.pop(0)
            if (not len(expressions)):
                expressions.append(arg)
            else:
                files.append(arg)

        cur = self.filesystem.current
        output = ([], [])
        for file in files:
            # Get file data
            self.filesystem.search(file)
            old = self.filesystem.current.get_data()

            # Save backup if request
            if backup not in ("", "-i"):
                inode = Inode(NodeType.FILE)
                inode.set_data(old)
                assert self.filesystem.current.parent != None
                self.filesystem.current.parent.add_child(backup.replace("-i", self.filesystem.current.name, 1), inode)

            # Apply commands to line
            new = old.split("\n")
            for expression in expressions:
                # Setup 
                l = len(expression)
                before_s = ""
                pattern = ""
                replacement = ""
                glob = False
                delete = False
                sprint = False
                occur = 1
                csensentive = True
                write = True

                # Parse Expression
                index = 0
                while index < l and expression[index] not in ["s", "d"]:
                    before_s += expression[index]
                    index += 1

                single = None
                rev_single = False
                between = []
                if (len(before_s)):
                    sp = before_s.split(",")
                    if (len(sp) == 2):
                        try:
                            between = [int(sp[0]) - 1, int(sp[1]) - 1]
                        except:
                            return (1, ([f"sed: expected int, got {before_s}"], []))
                    else:
                        single = None
                        rev_single = False
                        try:
                            if (before_s[-1] == "!"):
                                single = int(before_s[:-1])
                                rev_single = True
                            elif (before_s == "$"):
                                single = -1
                            else:
                                single = int(before_s)
                        except:
                            return (1, ([f"sed: expected int, got {before_s}"], []))
                        single = single - 1 if single != -1 else single
                # Substituion
                if (expression[index] == "s"):
                    index += 1
                    delim = expression[index]
                    index += 1
                    
                    while index < l and expression[index] != delim:
                        pattern += expression[index]
                        index += 1
                    if (index == l):
                        return (1, (["sed: substution expects s/pattern/replacement/"], []))
                    index += 1
                    while index < l and expression[index] != delim:
                        replacement += expression[index]
                        index += 1
                    if (index == l and expression[index - 1] != delim):
                        return (1, (["sed: expected terminating delim"], []))
                    index += 1
                    while index < l:
                        match (expression[index]):
                            case "g":
                                glob = True
                            case "I":
                                csensentive = False
                            case "w":
                                write = True
                            case _:
                                return (1, ([f"sed: unknown expression flag - {expression[index]}"],[]))
                        index += 1
                    # Check each line
                    for i, line in enumerate(new):
                        if (single is not None):
                            if (not rev_single and single != i) or (rev_single and single == i):
                                continue
                        elif (between != []):
                            if between[0] > i:
                                continue # go to next line
                            if between[1] < i:
                                break # give up we out of range
                        new[i] = line.replace(pattern, replacement, -1 if glob else 1)
                elif (expression[index] == "d"):
                    if (single == -1):
                        print ("hehe")
                        new.pop()
                        continue
                    tmp = []
                    for i, line in enumerate(new):
                        if (single is not None):
                            if (rev_single and single == i) or (not rev_single and single != i):
                                # no Delete time
                                tmp.append(line)
                        else:
                            print (between)
                            if (between[0] > i or between[1] < i):
                                # no Delete time
                                tmp.append(line)
                    new = tmp
                else:
                    raise SyntaxError("Unknown Expression Given")
            if (backup):
                self.filesystem.current.set_data("\n".join(new))
            else:
                output[1].extend(new)
            self.filesystem.current = cur
        return (0, output)

    def cp(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        verbose = False
        interactive = False
        clobbar = True
        recursive = False
        verbose = False
        dereference = True
        hardlink = False
        symlink = False
        preserve = False
        update = False
        files = []
        output = ([], [])
        while len(args) > 1:
            arg = args[0]
            if (arg[0] == "-"):
                for option in arg[1:]:
                    match (option):
                        case "n":
                            clobbar = False
                        case "i":
                            interactive = True
                        case "r":
                            recursive = True
                        case "R":
                            recursive = False
                        case "u":
                            update = True
                        case "L":
                            dereference = True
                        case "d":
                            dereference = False
                        case "v":
                            verbose = True
            else:
                files.append(arg)
            args = args[1:]
        target = args[0]
        tmp = self.filesystem.current
        destination_created = False
        if (error := self.filesystem.search(target)):
            # Directory/file doesn't exist
            if len(files) == 1:
                destination_created = True
                # peek at source type before creating destination
                self.filesystem.search(files[0])
                source_peek = self.filesystem.current
                self.filesystem.current = tmp  # restore current
                
                if source_peek.get_type() == NodeType.DIRECTORY:
                    self.filesystem.add_directory(target)
                else:
                    self.filesystem.add_file(target)
                self.filesystem.search(target)
            else:
                return (1, ([f"cp: target '{target}' is not a directory"],[]))
        target_fnode = self.filesystem.current
        target_ty = target_fnode.get_type()
        self.filesystem.current = tmp
        for file in files:
            self.filesystem.current = tmp
            self.filesystem.search(file)
            source_fnode = self.filesystem.current
            source_ty = source_fnode.get_type()
            if source_ty == NodeType.DIRECTORY and not recursive:
                output[0].append(f"cp: -r not specified; omitting directory '{file}'")
                continue
            if (source_ty == NodeType.DIRECTORY):
                if (target_ty == NodeType.FILE):
                    output[0].append(f"cp: cannot overwrite non-directory '{target}' with directory '{file}'")
                    continue
                elif (target_ty == NodeType.DIRECTORY):
                    if destination_created:
                        target_fnode.items.extend(copy.deepcopy(source_fnode.items))
                    else:
                        target_fnode.items.append(copy.deepcopy(source_fnode))
                    if (verbose):
                        output[1].append(f"cp: Copied '{file}' to '{target}'")
                elif (target_ty == NodeType.SYMLINK):
                    pass
            elif (source_ty == NodeType.FILE):
                if (target_ty == NodeType.FILE):
                    target_fnode.inode = source_fnode.inode
                    if (verbose):
                        output[1].append(f"cp: Copied '{file}' to '{target}'")
                elif (target_ty == NodeType.DIRECTORY):
                    target_fnode.items.append(source_fnode)
                    if (verbose):
                        output[1].append(f"cp: Copied '{file}' to '{target}'")
                elif (target_ty == NodeType.SYMLINK):
                    pass
            elif (source_ty == NodeType.SYMLINK):
                if (target_ty == NodeType.FILE):
                    pass
                elif (target_ty == NodeType.DIRECTORY):
                    pass
                elif (target_ty == NodeType.SYMLINK):
                    pass
            self.filesystem.current = tmp
        self.filesystem.current = tmp
        return (1, output)
    
    def mv(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        verbose = False
        clobber = False
        output = ([], [])
        if ("--help" in args):
            return (0, ([], self.useage("mv")))
        if len(args) < 2:
            output[0].append("cp: expected at least two arguments")
        files = []
        while len(args) and len(args[0]) and args[0][0] == "-":
            arg = args.pop(0)
            for option in arg[1:]:
                if (option == "v"):
                    verbose = True
        files = args[:-1]
        target = args[-1]
        tmp = self.filesystem.current
        if (len(files) == 1):
            ftype = self.filesystem.search_withaccess(files[0])
            if ftype == None:
                return (0, ([f"mv: could not find file {files[0]}"], []))
            ttype = NodeType.DIRECTORY if len(target.split(".")) == 1 else NodeType.FILE
            if ftype == ttype:
                if (verbose):
                    output[1].append(f"Renamed {self.filesystem.current.name} -> {target}")
                self.filesystem.current.name = target
                self.filesystem.current = tmp
                return (0, output)
            elif (ftype == NodeType.FILE and ttype == NodeType.DIRECTORY):
                if (self.filesystem.current.parent == None): # literally impossible to be true
                    return (2, ([], [])) # pragma: no cover
                self.filesystem.current = self.filesystem.current.parent
                saved = None
                for idx, item in enumerate(self.filesystem.current.items):
                    if (item.name == files[0]):
                        saved = item
                        self.filesystem.current.items.pop(idx)
                        break
                if (saved == None):
                    return (2, ([f"mv: could not find file {target}"], []))
                self.filesystem.search(target)
                self.filesystem.current.items.append(saved)
                if (verbose):
                    output[1].append(f"Moved {files[0]} to {target}")
                self.filesystem.current = tmp
                return (0, output)
        # multiple files were given
        self.filesystem.search(target)
        targetfnode = self.filesystem.current
        self.filesystem.current = tmp
        for file in files:
            ftype = self.filesystem.search(file)
            if (ftype != ""):
                output[0].append(f"mv: could not find file {file}")
            fnode = self.filesystem.current
            if (fnode.parent is None): continue
            fnode.parent.items = [item for item in fnode.parent.items if item.name != fnode.name]
            self.filesystem.current = targetfnode
            self.filesystem.current.items.append(fnode)
            if verbose:
                output[1].append(f"Moved {file} to {target}")
            self.filesystem.current = tmp
        return (0, output)
    
    def grep(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        case_insentive = False
        invert = False
        linenum = False
        filename = False
        countmatch = False
        matchwhole = False
        matchline = False
        showmatched = False
        quiet = False
        recursive = False
        pattern = ""
        files = []
        include = []
        exclude = []
        output = ([], [])
        while args:
            arg = args.pop(0)
            if (arg.startswith("--include=")):
                lst = arg.split("=")
                include.append(lst[1])
            elif (arg.startswith("--exclude-dir=")):
                lst = arg.split("=")
                exclude.append(lst[1])
            elif (arg == "--help"):
                return (0, ([], self.useage("grep")))
            elif (arg[0] == "-"):
                for option in arg[1:]:
                    match (option):
                        case "i":
                            case_insentive = True
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
                        case _:
                            return (1, (["grep: unknown argument given"], []))
            else:
                pattern = arg
                files = args
                break
        if (not pattern):
            return (1, (["grep: pattern not given"], []))
        if (not len(files)):
            files = ["-"]
        saved_current = self.filesystem.current
        if (matchwhole):
            match_cond_func = lambda line, pat: any(pat == w for w in line.split())
        elif (matchline):
            match_cond_func = lambda line, pat: line == pat
        else:
            # if the pattern exists in the line, there will be an element in the string comp
            match_cond_func = lambda line, pat: pat in line

        def search_file(item: FileNode) -> None:
            lst = item.get_data().split("\n")
            for idx, line in enumerate(lst):
                if case_insentive:
                    line_cmp = line.lower()
                    pattern_cmp = pattern.lower()
                else:
                    line_cmp = line
                    pattern_cmp = pattern
                matched = match_cond_func(line_cmp, pattern_cmp)
                if matched ^ invert:
                    if (filename):
                        tmp = item.name
                    elif (showmatched):
                        tmp = [w for w in line.split() if pattern in w][0]
                    else:
                        tmp = line
                    if (linenum):
                        tmp = f"{idx+1}:{tmp}"
                    print (tmp)
                    output[1].append(tmp)
                    if (filename and not linenum):
                        return

        for file in files:
            saved_current = self.filesystem.current
            if (file == "-"):
                ty = input.inode.type
                print (f"data: {input.inode.data}")
                self.filesystem.current = input
            else:
                err = self.filesystem.search(file)
                if err:
                    output[0].append(f"grep: {file} can not be found")
                    continue
                ty = self.filesystem.current.get_type()
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
        if (len(args) == 1 and args[0] == "--help"):
            return (0, ([], self.useage("chmod")))
        if len(args) < 2 and args[0] != "--help":
            output[0].append("chmod: expected at least two arguments")
            return (1, output)
        while len(args) > 2:
            arg = args[0]
            if (arg[0] == "-"):
                for option in arg[1:]:
                    if (option == "R"):
                        recurse = True
                    elif (option == "v"):
                        verbose = True
                    else:
                        return (1, (["chmod: Unknown output given"], []))
                
            args = args[1:]
        permissions = args[0]
        d = determine_perms_fromstr(permissions)
        if isinstance(d, str):
            return (1, ([d], []))
        file = args[1]
        saved_current = self.filesystem.current
        if (error := self.filesystem.search(file)) != "":
            self.filesystem.current = saved_current
            output[0].append(f"chmod: {error}")
            return (1, output)
        temp = self.filesystem.current.update_permissions(d, recurse)
        if verbose:
            output[1].extend(temp)
        self.filesystem.current = saved_current
        return (0, output)
    
    def echo(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        output = " ".join(args)
        if (output == "$?"):
            return (0, ([], [(str(self.filesystem.lcs))]))
        return (0, ([], [(" ".join(args))]))

    def touch(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        if "--help" in args:
            return (0, ([], self.useage("touch")))
        if (not len(args)):
            return (1, (["touch: must give atleast one argument"], []))
        files = []
        create = True
        changeaccess = True
        changemod = True
        date = datetime.datetime.now()
        output = ([], [])
        while args:
            arg = args.pop(0)
            if (arg == "-"):
                pass
            elif (arg[0] == "-"):
                if arg[1] == "-":
                    if (arg == "--no-create"):
                        create = False
                    if (arg.startswith("--date=")):
                        date = datetime.datetime.strptime(arg.split("=")[1], "%Y-%m-%d")
                else:
                    for option in arg[1:]:
                        match option:
                            case "c":
                                create = False
                                break
                            case "a":
                                changeaccess = True
                                changemod = False
                            case "m":
                                changeaccess = False
                                changemod = True
                            case "d":
                                date = datetime.datetime.strptime(args.pop(0), "%Y-%m-%d")
                                break
                            case "t":
                                date = datetime.datetime.strptime(args.pop(0), "%Y%m%d%H%M")
                                break
                            case _:
                                return (1, (["touch: unknown argument given"], []))
            else:
                files.append(arg)
        if (not len(files)):
            return (1, (["touch: no file given"], []))
        for file in files:
            sc = self.filesystem.current
            ty = self.filesystem.search(file)
            if (ty.startswith("No directory named") and len(file.split("/")) > 1):
                output[0].append(ty)
                continue
            if (ty != ""): 
                if (not create):
                    continue
                self.filesystem.current = sc
                self.filesystem.add_file(file)
                self.filesystem.search(file)
            fn = self.filesystem.current
            self.filesystem.current = sc
            if (changeaccess):
                fn.inode.atime = date
            if (changemod):
                fn.inode.mtime = date
        return (0, output)

    def cat(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        output = ([], [])
        if len(args) == 1 and args[0] == "--help":
            return (0, ([], self.useage("cat")))
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
                        lines = int(val)
                elif (arg == "-c"):
                    b = int(args.pop(0))
                elif (arg.startswith("--bytes=")):
                    val = arg.split("=")[1]
                    if (val[0] == "-"):
                        rev = True
                        b = int(val[1:]) * -1
                    else:
                        b = int(val)
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
            print(f"content: {content.inode.data}")
            if (ty == NodeType.DIRECTORY):
                output[0].append(f"head: ${file} is a directory")
                continue
            if (content == None or isinstance(content, str)):
                return (1, ([],[]))
            counter = 0
            data = content.get_data()
            if (data == ''):
                return (0, ([], []))
            if rev and b != -1:
                trimmed = data.encode("utf-8")[:b]  # b is negative, slices off last abs(b) bytes
                for line in trimmed.decode("utf-8").split("\n"):
                    output[1].append(line)
            else:
                for line in data.split("\n"):
                    line_bytes = len(line.encode("utf-8")) + 1
                    if b != -1 and curb + line_bytes > b:
                        # output partial line if there are remaining bytes
                        remaining = b - curb
                        if remaining > 0:
                            output[1].append(line.encode("utf-8")[:remaining].decode("utf-8"))
                        break
                    output[1].append(line)
                    curb += line_bytes
                    counter += 1
                    if b == -1 and counter >= lines:
                        break
            self.filesystem.current = saved_current
        return (0, output)

    def tail(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        return (0, ([], []))

    def rm(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        recurse, verbose = False, False
        output = ([], [])
        if ("--help" in args):
            return (0, ([], self.useage("rm")))
        
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
        result = self.filesystem.current.delete_child(filename, recurse)
        if (result == ""):
            output[0].append(f"rm: {filename} was not found")
        elif (result == "dir"):
            output[0].append(f"rm: cannot remove '{filename}': Is a directory")
        elif (verbose):
            output[1].append("rm: File sucessfully deleted")
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
        perms = {"user": {"r": True, "w": True, "x": True},
            "group": {"r": True, "w": False, "x": True},
            "public": {"r": True, "w": False, "x": True}}
        verbose, parent = False, False
        if not len(args):
            return (0, (["mkdir: at least one argument should be given"], []))
        name = ""
        while len(args) > 0:
            arg = args.pop(0)
            if (arg[0] == "-"): 
                if (arg == "-m" or arg == "--mode"):
                    arg = args.pop(0)
                    if (arg.startswith("a=")):
                        perms = determine_perms_fromstr(arg[2:])
                        if isinstance(perms, str):
                            return (1, ([perms], []))
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
        err = self.filesystem.add_directory(name, parent, perms)
        self.filesystem.current = saved_current
        if (err):
            return (1, ([f"mkdir: {err}"], []))
        if (verbose):
            return (0, ([], [f"mkdir: sucessfully created {name}"]))
        return (1, ([], []))

    def ls(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        deep, detail = False, 0
        extra: dict[str, bool | str] = {}
        oneline = False
        listdir = False
        target = ""
        output = ([], [])
        while args:
            arg = args[0]
            if (arg[0] == "-"):
                if (arg == "--help"):
                    return (0, ([], self.useage("ls")))
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
                            return (2, (["ls: unknown argument given"], []))
            else:
                target = arg
            args = args[1:]
        saved_current = self.filesystem.current
        lines = self.filesystem.list_files(target, -1 if deep else 0, detail, extra)
        self.filesystem.current = saved_current
        for line in lines: 
            output[1].append(" ".join(line))
        print (output)
        return (0, output)
    
    def cd(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        if (not args):
            return (1, (["cd: must give argument"], []))
        arg = args[0]
        if (error := self.filesystem.search(arg)):
            return (1, (["cd:" + error], []))
        self.shell.cwd += "/" + arg
        self.filesystem.cwd += "/" + arg
        return (0, ([],[]))
    
    def ln(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        linkty = "hard"
        if (len(args) == 1 and args[0] == "--help"):
            return (0, ([], self.useage("ln")))
        while len(args) > 2:
            arg = args.pop(0)
            if (arg[0] == "-"):
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
        if (err := self.filesystem.search(target)) != "":
            return (1, ([err], []))
        target_inode = self.filesystem.current.inode
        self.filesystem.current = saved_current
        self.filesystem.add_file(destination)
        self.filesystem.search(destination)
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
        output = list(dict.fromkeys(data))
        return (0, ([], output))

    def sort(self, args: list[str], input: FileNode) -> Tuple[int, Tuple[list[str], list[str]]]:
        if "--help" in args:
            return (0, ([], self.useage("sort")))
        file = ""
        igblanks = False
        reverse = False
        randomize = False
        check = False
        scheck = False
        fold = False
        clean = False
        remove_dups = False
        output = ""
        while args:
            arg = args.pop(0)
            if (arg[0] == "-"):
                if (arg == "-"):
                    file = "-"
                    continue
                for option in arg[1:]:
                    match (option):
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
                        case "u":
                            remove_dups = True
                        case _:
                            return (2, ([f"sort: unknown option given ({arg})"], []))
            else:
                file = arg
        if (file == "" or file == "-"):
            content = input.get_data().split("\n") 
        else:
            saved_current = self.filesystem.current
            self.filesystem.search(file)
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
                    # Silent check or not
                    if scheck:
                        return (1, ([], []))
                    else:
                        return (1, ([f"sort: {file}:{i}: disorder: {content[i]}"], []))
            return (0, ([], []))
        if remove_dups:
            modified = list(dict.fromkeys(modified))
        if randomize:
            r = []
            # while an element hasn't been moved
            while len(modified):
                # Pick a random element in modified
                vid = random.randrange(len(modified))
                # if there is multiple of one element move backwards
                while vid > 0 and modified[vid-1] == modified[vid]:
                    vid -= 1
                # Get element and append to end of new array
                element = modified.pop(vid)
                r.append(element)
                # Keep removing element which are the saeme
                while vid < len(modified) and modified[vid] == element:
                    r.append(modified.pop(vid))
            modified = r
        if output:
            saved_current = self.filesystem.current
            # If file don't exist already
            if (self.filesystem.search(output) != ""):
                self.filesystem.add_file(output)
                self.filesystem.search(output)
            self.filesystem.current.set_data("\n".join(modified))
            self.filesystem.current = saved_current
            return (0, ([], []))
        return (0, ([], modified))
