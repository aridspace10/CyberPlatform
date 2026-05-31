from game.filenode import FileNode
from game.filesystem import FileSystem
from collections import deque
from dataclasses import dataclass, field
from typing import Literal, Tuple, Any
from game.inode import Inode, NodeType
import random
import datetime
from .helpers import determine_perms_fromstr
from game.Parser import CommandParser, lex, Sequence, Pipe, AndOr, Command, Atom, SimpleCommand, Subshell, VarDeclaration, VarUse, FindParser, AndNode, OrNode, NotNode, FilterNode
from game.ShellState import ShellState
from game.NetworkManager import NetworkManager
from game.ProcessManager import ProcessManager
import copy
import re

CommandReturn = Tuple[int, Tuple[list[str], list[str]]]

@dataclass
class CommandResult:
    status: int = 0
    stdout: list[str] = field(default_factory=list)
    stderr: list[str] = field(default_factory=list)
    kind: Literal["text", "app"] = "text"
    payload: dict[str, Any] | None = None

class CommandLine:
    def __init__(self) -> None:
        self.process_manager = ProcessManager()
        self.process_manager.boot()
        self.network = NetworkManager()

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
                    item.set_data([])
                self.filesystem.current = saved_current
                return item
        inode = Inode(NodeType.FILE)
        self.filesystem.current.add_child(lst[-1], inode)  
        self.filesystem.search_withaccess(lst[-1]) # search with access will set new filenode as self.filesystem.current
        result = self.filesystem.current
        self.filesystem.current = saved_current
        return result
    
    def enter_command(self, raw: str, shell: ShellState) -> CommandResult:
        self.filesystem = shell.fs
        if (self.filesystem.cwd != shell.cwd):
            self.filesystem.search(shell.cwd)
            self.filesystem.cwd = shell.cwd
        self.shell = shell
        tokens = lex(raw)
        parser = CommandParser(tokens)
        ast = parser.parse()
        if isinstance(ast, Sequence):
            return self.execute_sequence(ast.parts)
        else:
            raise Exception("Enter command given no sequence object")

    def execute_pipe(self, parts: list[AndOr]) -> CommandResult:
        status = 0
        stderr, stdout = [], []
        cmd_result = None
        prev_pipe = None  # holds virtual pipe between commands

        for part in parts:
            # feed previous pipe into next command
            self.fdin = prev_pipe
            self.fdout = None

            cmd_result = self.execute_andor(part)

            # create a new pipe from stdout for next command
            if cmd_result.stdout:
                pipe_inode = Inode(NodeType.FILE)
                pipe_node = FileNode(None, "pipe", pipe_inode)
                # + ("\n" if stdout else "") for wc
                pipe_node.set_data(cmd_result.stdout)
                prev_pipe = pipe_node
            else:
                prev_pipe = None

        self.fdin = None
        self.fdout = None
        if (cmd_result == None):
            raise Exception("No Cmd Result given")
        return cmd_result
    
    def execute_andor(self, elem: AndOr) -> CommandResult:
        cmd_result = self.execute_command(elem.first)
        for (op, cmd) in elem.rest:
            if ((op == "&&" and not cmd_result.status) or (op == "||" and cmd_result.status)):
                tmp_result = self.execute_command(cmd)
                cmd_result.stderr.extend(tmp_result.stderr)
                cmd_result.stdout.extend(tmp_result.stdout)
                cmd_result.status = tmp_result.status
            else:
                break
        return cmd_result

    def execute_command(self, command: Command) -> CommandResult:
        redirs = command.pre_redirs + command.post_redirs
        for assign in command.assignments:
            self.shell.vars[assign.name] = assign.value.parts[0]

        for redir in redirs:
            if (redir.op == "<"):
                self.fdin = self.get_fd(redir.target)
                if (isinstance(self.fdin, str)):
                    cmd_result = CommandResult(1, [], [self.fdin], 'text', None)
                    return cmd_result
            elif (redir.op == ">"):
                self.fdout = self.get_fd(redir.target, True)
                if (isinstance(self.fdout, str)):
                    cmd_result = CommandResult(1, [], [self.fdout], 'text', None)
                    return cmd_result
            elif (redir.op == ">>"):
                self.fdout = self.get_fd(redir.target)
                if (isinstance(self.fdout, str)):
                    cmd_result = CommandResult(1, [], [self.fdout], 'text', None)
                    return cmd_result
        cmd_result = self.execute_atom(command.atom)
        if command.pre_redirs or command.post_redirs:
            if isinstance(self.fdout, FileNode):
                self.fdout.append_data(cmd_result.stdout)
                cmd_result.stdout = []
        else:
            # No redirection → leave stdout alone
            self.fdout = None
        return cmd_result

    def execute_atom(self, atom: Atom) -> CommandResult:
        if (isinstance(atom, SimpleCommand)):
            if self.fdin is None:
                fdin = FileNode(None, "stdin", Inode(NodeType.FILE))
                fdin.set_data([])
            elif isinstance(self.fdin, str):
                raise Exception("Look here")
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
                            return CommandResult(1, [], [f'Var Used which is unassigned: {part.name}'], 'text', None)
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
            cmd_result = self.execute_sequence(atom.sequence.parts)
            #restore state
            self.shell.cwd = saved_cwd
            self.shell.vars = saved_env
            self.filesystem.current = saved_fs_current
            self.filesystem.cwd = saved_fs_cwd
            self.fdin = saved_fdin
            self.fdout = saved_fdout
            return cmd_result

    def execute_sequence(self, parts: list[Pipe]) -> CommandResult:
        last_status = 0
        stdout, stderr = [], []
        cmd_result = None

        for part in parts:
            cmd_result = self.execute_pipe(part.parts)

        if (cmd_result == None):
            raise Exception("cmd being empty")
        
        return cmd_result
 
    def run_command(self, args: list[str], fdin: FileNode) -> CommandResult:
        if (not (len(args))):
            return CommandResult(0, [], [], 'text', None)
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
            case "wc":
                return self.wc(args[1:], fdin)
            case "ping":
                return self.ping(args[1:], fdin)
            case "ps":
                return self.ps(args[1:], fdin)
            case _:
                return CommandResult(1, [], ["Unknown command given"], 'text', None)

    def useage(self, type: str) -> list[str]:
        output = []
        with open(f"../static/help/{type}.txt") as f:
            for line in f:
                output.append(line)
        return output
    
    def ps(self, args: list[str], input: FileNode) -> CommandResult:
        if ("--help" in args):
            idx = args.index("--help")
            if (idx + 1 < len(args)):
                ty = args[idx + 1]
                if ty == "simple" or ty == "s":
                    return CommandResult(stdout=self.useage("ps-simple"))
                elif ty == "list" or ty == "l":
                    return CommandResult(stdout=self.useage("ps-list"))
                elif ty == "output" or ty == "o":
                    return CommandResult(stdout=self.useage("ps-output"))
                elif ty == "all" or ty == "a":
                    return CommandResult(stdout=self.useage("ps-all"))
            return CommandResult(stdout=self.useage("ps"))
        parameters: dict[str, Any] = {}
        while (len(args)):
            arg = args.pop(0)
            for option in arg:
                match (option):
                    case ("-e"):
                        parameters["selectionTy"] = "e"
                    case ("-A"):
                        parameters["selectionTy"] = "e"
                    case "-C":
                        parameters["command"] = args.pop(0)
                    case "-p":
                        parameters["pid"] = args.pop(0)
                    case "-q":
                        parameters["qpid"] = args.pop(0)
                    case "-l":
                        parameters["long"] = True
        self.process_manager.list_processes(parameters)

        return CommandResult()
    
    def ping(self, args: list[str], input: FileNode) -> CommandResult:
        if ("--help" in args or "-h" in args or "-help" in args):
            return CommandResult(stdout=self.useage("ping"))
        between = 0
        preload = 3
        while len(args) > 1:
            arg = args.pop(0)
            if (arg[0] == "-"):
                for option in arg:
                    match (arg):
                        case "i":
                            val = None
                            try:
                                val = args.pop(0)
                                between = int(val)
                            except:
                                return CommandResult(stderr=[f"Expected an integer for -i, got {val if val else ""}"])
                        case "l":
                            val = None
                            try:
                                val = args.pop(0)
                                preload = int(val)
                            except:
                                return CommandResult(stderr=[f"Expected an integer for -l   , got {val if val else ""}"])
        dnsname = args.pop(0)
        return CommandResult()
    
    def find(self, args: list[str], input: FileNode) -> CommandResult:
        if (len(args) < 1):
            return CommandResult(1, stderr=["find: atleast one argument needs to be given"])
        while (len(args) and args[0][0] == "-"):
            arg = args.pop(0)
        if (not len(args)):
            return CommandResult(1, stderr=["find: starting locaiton needs to be given"])
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
                return CommandResult(2, stderr=[f"find: {str(e)}"])
        stdout = []
        stderr = []
        for start in starting:
            if (err := self.filesystem.search(start)):
                stderr.append(err)
                continue

            start_node = self.filesystem.current   # AFTER search
            (toprints, execs) = start_node.find(node, ".")
            stdout.extend(toprints)
        return CommandResult(0, stdout, stderr)
    
    def sed(self, args: list[str], input: FileNode) -> CommandResult:
        if "--help" in args:
            return CommandResult(0, stdout=self.useage("sed"))
        if (len(args) < 1):
            return CommandResult(2, stderr=["sed [OPTION]... {script-only-if-no-other-script} [input-file]..."])
        files = []
        expressions = []
        backup = ""
        suppress_print = False
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
                        case ("n"):
                            suppress_print = True
                        case _:
                            return CommandResult(1, stderr=[f"sed: unknown option given - {option}"])

        while (len(args)):
            arg = args.pop(0)
            if (not len(expressions)):
                expressions.append(arg)
            else:
                files.append(arg)

        cur = self.filesystem.current
        stdout = []
        stderr = []
        for file in files:
            # Get file data
            if (err := self.filesystem.search(file)):
                stderr.append(f"sed: {err}")
                continue

            old = self.filesystem.current.get_data()

            # Save backup if request
            if backup not in ("", "-i"):
                inode = Inode(NodeType.FILE)
                inode.set_data(old)
                assert self.filesystem.current.parent != None
                self.filesystem.current.parent.add_child(backup.replace("-i", self.filesystem.current.name, 1), inode)

            # Apply commands to line
            new = old
            printed = []
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
                print_after_sub = False
                write = True

                # Parse Expression
                index = 0
                while index < l and expression[index] not in ["s", "d", "p"]:
                    before_s += expression[index]
                    index += 1

                single = None
                rev_single = False
                between = []
                regex_addr = None
                if len(before_s):
                    if before_s.startswith("/") and before_s.endswith("/"):
                        regex_addr = before_s[1:-1]
                    else:
                        sp = before_s.split(",")
                        if len(sp) == 2:
                            try:
                                between = [int(sp[0]) - 1, int(sp[1]) - 1]
                            except:
                                return CommandResult(1, stderr=[f"sed: expected int, got {before_s}"])
                        else:
                            try:
                                if before_s[-1] == "!":
                                    single = int(before_s[:-1])
                                    rev_single = True
                                elif before_s == "$":
                                    single = -1
                                else:
                                    single = int(before_s)
                            except:
                                return CommandResult(1, stderr=[f"sed: expected int, got {before_s}"])
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
                        return CommandResult(1, stderr=["sed: substution expects s/pattern/replacement/"])
                    index += 1
                    while index < l and expression[index] != delim:
                        replacement += expression[index]
                        index += 1
                    if (index == l and expression[index - 1] != delim):
                        return CommandResult(1, stderr=["sed: expected terminating delim"])
                    index += 1
                    noccurences = 0
                    while index < l:
                        match (expression[index]):
                            case "g":
                                glob = True
                            case "I":
                                csensentive = False
                            case "w":
                                write = True
                            case "p":
                                print_after_sub = True
                            case _:
                                if expression[index].isdigit():
                                    num = ""
                                    while index < l and expression[index].isdigit():
                                        num += expression[index]
                                        index += 1
                                    noccurences = int(num)
                                    continue
                                else:
                                    return CommandResult(1, stderr=[f"sed: unknown expression flag - {expression[index]}"])
                        index += 1
                    count = 1
                    for i, line in enumerate(new):
                        if (single is not None):
                            if (not rev_single and single != i) or (rev_single and single == i):
                                continue
                        elif (between != []):
                            if between[0] > i:
                                continue # go to next line
                            if between[1] < i:
                                break # give up we out of range
                        flags = 0 if csensentive else re.IGNORECASE
                        if glob:
                            if noccurences != 0:
                                matches_seen = 0
                                def repl(match):
                                    nonlocal matches_seen
                                    matches_seen += 1

                                    if matches_seen >= noccurences:
                                        return replacement
                                    return match.group(0)
                                new_line, subs = re.subn(
                                    pattern,
                                    repl,
                                    line,
                                    flags=flags
                                )
                            else:
                                new_line, subs = re.subn(
                                    pattern,
                                    replacement,
                                    line,
                                    flags=flags
                                )
                        elif noccurences != 0:
                            matches_seen = 0
                            def repl(match):
                                nonlocal matches_seen
                                matches_seen += 1

                                if matches_seen == noccurences:
                                    return replacement

                                return match.group(0)
                            new_line, subs = re.subn(
                                pattern,
                                repl,
                                line,
                                flags=flags
                            )
                        else:
                            new_line, subs = re.subn(
                                pattern,
                                replacement,
                                line,
                                count=1,
                                flags=flags
                            )
                        new[i] = new_line
                        if print_after_sub and subs > 0:
                            printed.append(new_line)
                elif (expression[index] == "d"):
                    tmp = []
                    for i, line in enumerate(new):
                        delete_line = False
                        if regex_addr is not None:
                            if re.search(regex_addr, line):
                                delete_line = True
                        elif single is not None:
                            if single == -1:
                                delete_line = (i == len(new) - 1)
                            elif rev_single:
                                delete_line = (i != single)
                            else:
                                delete_line = (i == single)
                        elif between != []:
                            delete_line = between[0] <= i <= between[1]
                        if not delete_line:
                            tmp.append(line)
                    new = tmp
                elif (expression[index] == "p"):
                    for i, line in enumerate(new):
                        should_print = False

                        if single is not None:
                            if single == -1:
                                should_print = (i == len(new) - 1)
                            elif rev_single:
                                should_print = (i != single)
                            else:
                                should_print = (i == single)

                        elif between != []:
                            should_print = between[0] <= i <= between[1]

                        elif regex_addr is not None:
                            if re.search(regex_addr, line):
                                should_print = True

                        else:
                            should_print = True

                        if should_print:
                            printed.append(line)
                else:
                    return CommandResult(1, stderr=["sed: unknown expression given"])
            if (backup):
                self.filesystem.current.set_data(new)
            elif (suppress_print):
                stdout.extend(printed)
            else:
                stdout.extend(new)
            self.filesystem.current = cur
        return CommandResult(0, stdout, stderr)

    def wc(self, args: list[str], input: FileNode) -> CommandResult:
        stdout = []
        stderr = []

        words = bytes_flag = chars = lines = False
        files = []

        for arg in args:
            if arg in ("-c","--bytes"):
                bytes_flag = True
            elif arg in ("-m","--chars"):
                chars = True
            elif arg in ("-l","--lines"):
                lines = True
            elif arg in ("-w","--words"):
                words = True
            else:
                files.append(arg)

        if not any([words, bytes_flag, chars, lines]):
            words = bytes_flag = chars = lines = True

        if (not len(files)):
            files.append("-")

        total_lines = 0
        total_words = 0
        total_chars = 0
        total_bytes = 0

        cur = self.filesystem.current
        for file in files:
            if (file == "-"):
                self.filesystem.current = input
            else:
                # Get filenode
                if (err := self.filesystem.search(file)):
                    stderr.append(err)
                    continue

                # Check for file
                if (self.filesystem.current.get_type() == NodeType.DIRECTORY):
                    stderr.append(f"wc: cannot perform operation on directory ({file})")
                    continue
            
            node = self.filesystem.current
            data = node.get_data()
            self.filesystem.current = cur

            lcount = len(data)
            if data and not node.inode.has_trailing_newline:
                lcount -= 1
            wcount = len(" ".join(data).split())
            ccount = len("\n".join(data))
            bcount = len("\n".join(data).encode())

            total_lines += lcount
            total_words += wcount
            total_chars += ccount
            total_bytes += bcount

            parts = []

            if lines:
                parts.append(str(lcount))

            if words:
                parts.append(str(wcount))

            if chars:
                parts.append(str(ccount))

            if bytes_flag:
                parts.append(str(bcount))

            if len(files) > 1:
                parts.append(file)

            stdout.append(" ".join(parts))

        if len(files) > 1:
            parts = []

            if lines:
                parts.append(str(total_lines))

            if words:
                parts.append(str(total_words))

            if chars:
                parts.append(str(total_chars))

            if bytes_flag:
                parts.append(str(total_bytes))

            parts.append("total")

            stdout.append(" ".join(parts))


        return CommandResult(0, stdout, stderr)

    def cp(self, args: list[str], input: FileNode) -> CommandResult:
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
        stdout = []
        stderr = []
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
                return CommandResult(1, stderr=[f"cp: target '{target}' is not a directory"])
        target_fnode = self.filesystem.current
        target_ty = target_fnode.get_type()
        self.filesystem.current = tmp
        for file in files:
            self.filesystem.current = tmp
            self.filesystem.search(file)
            source_fnode = self.filesystem.current
            source_ty = source_fnode.get_type()
            if source_ty == NodeType.DIRECTORY and not recursive:
                stderr.append(f"cp: -r not specified; omitting directory '{file}'")
                continue
            if (source_ty == NodeType.DIRECTORY):
                if (target_ty == NodeType.FILE):
                    stderr.append(f"cp: cannot overwrite non-directory '{target}' with directory '{file}'")
                    continue
                elif (target_ty == NodeType.DIRECTORY):
                    if destination_created:
                        target_fnode.items.extend(copy.deepcopy(source_fnode.items))
                    else:
                        target_fnode.items.append(copy.deepcopy(source_fnode))
                    if (verbose):
                        stdout.append(f"cp: Copied '{file}' to '{target}'")
                elif (target_ty == NodeType.SYMLINK):
                    pass
            elif (source_ty == NodeType.FILE):
                if (target_ty == NodeType.FILE):
                    target_fnode.inode = source_fnode.inode
                    if (verbose):
                        stdout.append(f"cp: Copied '{file}' to '{target}'")
                elif (target_ty == NodeType.DIRECTORY):
                    target_fnode.items.append(source_fnode)
                    if (verbose):
                        stdout.append(f"cp: Copied '{file}' to '{target}'")
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
        return CommandResult(1, stdout, stderr)
    
    def mv(self, args: list[str], input: FileNode) -> CommandResult:
        verbose = False
        clobber = False
        stdout = []
        stderr = []
        if ("--help" in args):
            return CommandResult(0, stdout=self.useage("mv"))
        if len(args) < 2:
            stderr.append("cp: expected at least two arguments")
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
                return CommandResult(0, stderr=[f"mv: could not find file {files[0]}"])
            ttype = NodeType.DIRECTORY if len(target.split(".")) == 1 else NodeType.FILE
            if ftype == ttype:
                if (verbose):
                    stdout.append(f"Renamed {self.filesystem.current.name} -> {target}")
                self.filesystem.current.name = target
                self.filesystem.current = tmp
                return CommandResult(0, stdout, stderr)
            elif (ftype == NodeType.FILE and ttype == NodeType.DIRECTORY):
                if (self.filesystem.current.parent == None): # literally impossible to be true
                    return CommandResult(2) # pragma: no cover
                self.filesystem.current = self.filesystem.current.parent
                saved = None
                for idx, item in enumerate(self.filesystem.current.items):
                    if (item.name == files[0]):
                        saved = item
                        self.filesystem.current.items.pop(idx)
                        break
                if (saved == None):
                    return CommandResult(2, stderr=[f"mv: could not find file {target}"])
                self.filesystem.search(target)
                self.filesystem.current.items.append(saved)
                if (verbose):
                    stdout.append(f"Moved {files[0]} to {target}")
                self.filesystem.current = tmp
                return CommandResult(0, stdout, stderr)
        # multiple files were given
        self.filesystem.search(target)
        targetfnode = self.filesystem.current
        self.filesystem.current = tmp
        for file in files:
            ftype = self.filesystem.search(file)
            if (ftype != ""):
                stderr.append(f"mv: could not find file {file}")
            fnode = self.filesystem.current
            if (fnode.parent is None): continue
            fnode.parent.items = [item for item in fnode.parent.items if item.name != fnode.name]
            self.filesystem.current = targetfnode
            self.filesystem.current.items.append(fnode)
            if verbose:
                stdout.append(f"Moved {file} to {target}")
            self.filesystem.current = tmp
        return CommandResult(0, stdout, stderr)
    
    def grep(self, args: list[str], input: FileNode) -> CommandResult:
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
        stdout = []
        stderr = []
        while args:
            arg = args.pop(0)
            if (arg.startswith("--include=")):
                lst = arg.split("=")
                include.append(lst[1])
            elif (arg.startswith("--exclude-dir=")):
                lst = arg.split("=")
                exclude.append(lst[1])
            elif (arg == "--help"):
                return CommandResult(0, stdout=self.useage("grep"))
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
                            return CommandResult(1, stderr=["grep: unknown argument given"])
            else:
                pattern = arg
                files = args
                break
        if (not pattern):
            return CommandResult(1, stderr=["grep: pattern not given"])
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
            lst = item.get_data()
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
                    stdout.append(tmp)
                    if (filename and not linenum):
                        return

        for file in files:
            saved_current = self.filesystem.current
            if (file == "-"):
                ty = input.inode.type
                self.filesystem.current = input
            else:
                err = self.filesystem.search(file)
                if err:
                    stderr.append(f"grep: {file} can not be found")
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
                    stderr.append("Can't recursivly search directory without -r option")
            elif (ty == NodeType.FILE):
                search_file(self.filesystem.current)
            else:
                stderr.append(f"Can't open file/directory given: {file}")
            self.filesystem.current = saved_current
        if (countmatch):
            return CommandResult(0, stdout=[str(len(stdout))])
        else:
            return CommandResult(0, stdout, stderr)
    
    def chmod(self, args: list[str], input: FileNode) -> CommandResult:
        recurse = False
        verbose = False
        stdout = []
        stderr = []
        if (len(args) == 1 and args[0] == "--help"):
            return CommandResult(0, stdout=self.useage("chmod"))
        if len(args) < 2 and args[0] != "--help":
            stderr.append("chmod: expected at least two arguments")
            return CommandResult(1, stderr=stderr)
        while len(args) > 2:
            arg = args[0]
            if (arg[0] == "-"):
                for option in arg[1:]:
                    if (option == "R"):
                        recurse = True
                    elif (option == "v"):
                        verbose = True
                    else:
                        return CommandResult(1, stderr=["chmod: Unknown output given"])
                
            args = args[1:]
        permissions = args[0]
        d = determine_perms_fromstr(permissions)
        if isinstance(d, str):
            return CommandResult(1, stderr=[d])
        file = args[1]
        saved_current = self.filesystem.current
        if (error := self.filesystem.search(file)) != "":
            self.filesystem.current = saved_current
            stderr.append(f"chmod: {error}")
            return CommandResult(1, stderr=stderr)
        temp = self.filesystem.current.update_permissions(d, recurse)
        if verbose:
            stdout.extend(temp)
        self.filesystem.current = saved_current
        return CommandResult(0, stdout, stderr)
    
    def echo(self, args: list[str], input: FileNode) -> CommandResult:
        output = " ".join(args)
        if (output == "$?"):
            return CommandResult(0, stdout=[str(self.filesystem.lcs)])
        return CommandResult(0, stdout=" ".join(args).split("\n"))

    def touch(self, args: list[str], input: FileNode) -> CommandResult:
        if "--help" in args:
            return CommandResult(0, stdout=self.useage("touch"))
        if (not len(args)):
            return CommandResult(1, stderr=["touch: must give atleast one argument"])
        files = []
        create = True
        changeaccess = True
        changemod = True
        date = datetime.datetime.now()
        stdout = []
        stderr = []
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
                                return CommandResult(1, stderr=["touch: unknown argument given"])
            else:
                files.append(arg)
        if (not len(files)):
            return CommandResult(1, stderr=["touch: no file given"])
        for file in files:
            sc = self.filesystem.current
            ty = self.filesystem.search(file)
            if (ty.startswith("No directory named") and len(file.split("/")) > 1):
                stderr.append(ty)
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
        return CommandResult(0, stdout, stderr)

    def cat(self, args: list[str], input: FileNode) -> CommandResult:
        stdout = []
        stderr = []
        if len(args) == 1 and args[0] == "--help":
            return CommandResult(0, stdout=self.useage("cat"))
        while len(args) > 1:
            arg = args[0]
            if (arg == "--help"):
                return CommandResult(0, stdout=self.useage("cat"))
            args = args[1:]
        filename = args[0]
        content = self.filesystem.get_file(filename)
        if (content == None or isinstance(content, str)):
            return CommandResult(1, stderr=[f"File {filename} does not exist"])
        data = content.get_data()
        for line in data:
            stdout.append(line)
        return CommandResult(0, stdout, stderr)

    def head(self, args: list[str], input: FileNode) -> CommandResult:
        lines = 10
        b = -1
        curb = 0
        rev = False
        files = []
        stdout = []
        stderr = []
        while args:
            arg = args.pop(0)
            if (arg == "-"):
                files.append(input)
            elif (arg[0] == "-"):
                if (arg == "--help"):
                    return CommandResult(0, stdout=self.useage("head"))
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
                    stderr.append(f"head: Unknown argument (${arg}) given")
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
                stderr.append(f"head: ${file} is a directory")
                continue
            if (content == None or isinstance(content, str)):
                return CommandResult(1)
            counter = 0
            data = content.get_data()
            if (data == ''):
                return CommandResult(0)
            if rev and b != -1:
                raw = "\n".join(data)
                encoded = raw.encode("utf-8")
                trimmed = encoded[:b]  # or [-b:] depending on mode

                decoded = trimmed.decode("utf-8", errors="ignore")

                for line in decoded.split("\n"):
                    stdout.append(line)
            else:
                for line in data:
                    line_bytes = len(line.encode("utf-8")) + 1
                    if b != -1 and curb + line_bytes > b:
                        # output partial line if there are remaining bytes
                        remaining = b - curb
                        if remaining > 0:
                            stdout.append(line.encode("utf-8")[:remaining].decode("utf-8"))
                        break
                    stdout.append(line)
                    curb += line_bytes
                    counter += 1
                    if b == -1 and counter >= lines:
                        break
            self.filesystem.current = saved_current
        return CommandResult(0, stdout, stderr)

    def tail(self, args: list[str], input: FileNode) -> CommandResult:
        if "--help" in args:
            return CommandResult(0, stdout=self.useage("tail"))
        stdout = []
        stderr = []
        lines = -1
        byte = -1
        ahead = False
        outputType = 0
        while len(args) and args[0][0] == "-":
            arg = args.pop(0)
            if (arg == "-c" or arg.startswith("--bytes=")):
                if (arg == "-c"):
                    if (not len(args)):
                        return CommandResult(1, stderr=["tail: argument required for -c"])
                    num = args.pop(0)
                else:
                    num = arg.split("=")[1]
                try:
                    if (num[0] == "+"):
                        ahead = True
                        byte = int(num[1:])
                    else:
                        lines = int(num)
                except (ValueError):
                    return CommandResult(1, stderr=["tail: argument for -c must be an integar with a possible + prefix"])

            elif (arg == "-n" or arg.startswith("--lines=")):
                if (arg == "-n"):
                    if (not len(args)):
                        return CommandResult(1, stderr=["tail: argument required for -n"])
                    num = args.pop(0)
                else:
                    num = arg.split("=")[1]
                try:
                    if (num[0] == "+"):
                        ahead = True
                        lines = int(num[1:])
                    else:
                        lines = int(num)
                except (ValueError):
                    return CommandResult(1, stderr=["tail: argument for -c must be an integar with a possible + prefix"])

            elif (arg == "-q" or arg == "--quiet" or arg == "--silent"):
                outputType = -1
            elif (arg == "-v" or arg == "--verbose"):
                outputType = 1
            elif arg[1:].isdigit():
                lines = int(arg[1:])
            else:
                return CommandResult(1, stderr=[f"tail: unknown argument given {arg}"])
        files = args
        if (len(files) == 0):
            files = ["-"]
        for file in files:
            # Create header if needed
            if ((len(files) > 1 and outputType != -1) or (len(files) == 1 and outputType == 1)):
                stdout.append(f"==> {file} <==")
            
            # Get filenode
            saved_current = self.filesystem.current
            if (file == "-"):
                content = input
                ty = content.get_type()
            else: 
                ty = self.filesystem.search_withaccess(file)
                content = self.filesystem.current
                self.filesystem.current = saved_current

            # Check is file
            if (ty == NodeType.DIRECTORY):
                stderr.append(f"tail: ${file} is a directory")
                continue

            if ty is None:
                stderr.append(f"tail: cannot open '{file}'")
                continue
            
            # Get data
            data = content.get_data()
            if (data == []):
                continue

            if (lines == -1 and byte == -1):
                lines = 10

            # modify data for return
            if (ahead):
                if (lines != -1):
                    stdout.extend(data[lines-1:] if lines > 0 else data)
                else:
                    raw = "\n".join(data)
                    encoded = raw.encode("utf-8")
                    trimmed = encoded[byte - 1:]
                    decoded = trimmed.decode("utf-8", errors="ignore")
                    for line in decoded.split("\n"):
                        stdout.append(line)
            else:
                if (lines != -1):
                    if (lines == 0):
                        continue
                    stdout.extend(data[-lines:])
                else:
                    raw = "\n".join(data)
                    encoded = raw.encode("utf-8")
                    trimmed = encoded[-byte:]
                    decoded = trimmed.decode("utf-8", errors="ignore")
                    for line in decoded.split("\n"):
                        stdout.append(line)
        return CommandResult(0, stdout, stderr)

    def rm(self, args: list[str], input: FileNode) -> CommandResult:
        recurse, verbose = False, False
        stdout = []
        stderr = []
        if ("--help" in args):
            return CommandResult(0, stdout=self.useage("rm"))
        
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
            stderr.append(f"rm: {filename} was not found")
        elif (result == "dir"):
            stderr.append(f"rm: cannot remove '{filename}': Is a directory")
        elif (verbose):
            stdout.append("rm: File sucessfully deleted")
        return CommandResult(0, stdout, stderr)

    def pwd(self, args: list[str], input: FileNode) -> CommandResult:
        ty = "l"
        while len(args) > 1:
            arg = args[0]
            if (arg == "--help"):
                return CommandResult(0, stdout=self.useage("pwd"))
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
        return CommandResult(0, stdout=[direct])
        
    def mkdir(self, args: list[str], input: FileNode) -> CommandResult:
        perms = {"user": {"r": True, "w": True, "x": True},
            "group": {"r": True, "w": False, "x": True},
            "public": {"r": True, "w": False, "x": True}}
        verbose, parent = False, False
        if not len(args):
            return CommandResult(0, stderr=["mkdir: at least one argument should be given"])
        name = ""
        while len(args) > 0:
            arg = args.pop(0)
            if (arg[0] == "-"): 
                if (arg == "-m" or arg == "--mode"):
                    arg = args.pop(0)
                    if (arg.startswith("a=")):
                        perms = determine_perms_fromstr(arg[2:])
                        if isinstance(perms, str):
                            return CommandResult(1, stderr=[perms])
                    else:
                        return CommandResult(1, stderr=["mkdir: option given to -m or --mode is not correct"])
                elif (arg == "-v" or arg == "--verbose"):
                    verbose = True
                elif (arg == "-p" or arg == "--parents"):
                    parent = True
                elif (arg == "-h" or arg == "--help"):
                    return CommandResult(0, stdout=self.useage("mkdir"))
                else:
                    return CommandResult(1, stderr=["mkdir: unknown argument given"])
            else:
                name = arg
        if (name == ""):
            return CommandResult(1, stderr=["mkdir: no name given for new directory"])
        
        saved_current = self.filesystem.current
        err = self.filesystem.add_directory(name, parent, perms)
        self.filesystem.current = saved_current
        if (err):
            return CommandResult(1, stderr=[f"mkdir: {err}"])
        if (verbose):
            return CommandResult(0, stdout=[f"mkdir: sucessfully created {name}"])
        return CommandResult(1)

    def ls(self, args: list[str], input: FileNode) -> CommandResult:
        deep, detail = False, 0
        extra: dict[str, bool | str] = {}
        oneline = False
        listdir = False
        target = ""
        stdout = []
        stderr = []
        while args:
            arg = args[0]
            if (arg[0] == "-"):
                if (arg == "--help"):
                    return CommandResult(0, stdout=self.useage("ls"))
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
                            return CommandResult(2, stderr=["ls: unknown argument given"])
            else:
                target = arg
            args = args[1:]
        saved_current = self.filesystem.current
        lines = self.filesystem.list_files(target, -1 if deep else 0, detail, extra)
        self.filesystem.current = saved_current
        for line in lines: 
            stdout.append(" ".join(line))
        return CommandResult(0, stdout, stderr)
    
    def cd(self, args: list[str], input: FileNode) -> CommandResult:
        if (not args):
            return CommandResult(1, stderr=["cd: must give argument"])
        arg = args[0]
        if (error := self.filesystem.search(arg)):
            return CommandResult(1, stderr=["cd:" + error])
        self.shell.cwd += "/" + arg
        self.filesystem.cwd += "/" + arg
        return CommandResult(0)
    
    def ln(self, args: list[str], input: FileNode) -> CommandResult:
        linkty = "hard"
        if (len(args) == 1 and args[0] == "--help"):
            return CommandResult(0, stdout=self.useage("ln"))
        while len(args) > 2:
            arg = args.pop(0)
            if (arg[0] == "-"):
                options = arg[1:]
                for option in options:
                    match option:
                        case "s":
                            linkty = "sym"
                        case _:
                            return CommandResult(2, stderr=["Unknown Argument Given"])
        target = args[0]
        destination = args[1]
        saved_current = self.filesystem.current
        if (err := self.filesystem.search(target)) != "":
            return CommandResult(1, stderr=[err])
        target_inode = self.filesystem.current.inode
        self.filesystem.current = saved_current
        self.filesystem.add_file(destination)
        self.filesystem.search(destination)
        if (linkty == "hard"):
            self.filesystem.current.inode = target_inode
            self.filesystem.current.inode.link_count += 1
        else:
            inode = Inode(NodeType.SYMLINK)
            inode.set_data(target.splitlines())
            self.filesystem.current.inode = inode
        self.filesystem.current = saved_current
        return CommandResult(1)
    
    def uniq(self, args: list[str], input: FileNode) -> CommandResult:
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
        data = input.get_data()
        output = list(dict.fromkeys(data))
        return CommandResult(0, stdout=output)

    def sort(self, args: list[str], input: FileNode) -> CommandResult:
        if "--help" in args:
            return CommandResult(0, stdout=self.useage("sort"))
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
                            return CommandResult(2, stderr=[f"sort: unknown option given ({arg})"])
            else:
                file = arg
        if (file == "" or file == "-"):
            content = input.get_data()
        else:
            saved_current = self.filesystem.current
            self.filesystem.search(file)
            content = self.filesystem.current.get_data()
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
                        return CommandResult(1)
                    else:
                        return CommandResult(1, stderr=[f"sort: {file}:{i}: disorder: {content[i]}"])
            return CommandResult(0)
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
            self.filesystem.current.set_data(modified)
            self.filesystem.current = saved_current
            return CommandResult(0)
        return CommandResult(0, stdout=modified)