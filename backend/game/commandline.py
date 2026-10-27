import copy
import datetime
import fnmatch
import math
import random
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Literal, Tuple

from game.Context import CommandContext, ExecutionContext, SystemContext
from game.filenode import FileNode
from game.inode import Inode, NodeType
from game.InputBuffer import InputBuffer
from game.NetworkManager import NetworkManager
from game.Parser import (
    AndNode,
    AndOr,
    Atom,
    Command,
    CommandParser,
    ExecNode,
    FilterNode,
    FindParser,
    Job,
    NotNode,
    OrNode,
    Pipe,
    Sequence,
    SimpleCommand,
    lex,
)
from game.Process import ProcessState
from game.ProcessManager import ProcessManager
from game.Program import BackgroundJobProgram, HeredocProgram, RmProgram, SleepProgram
from game.ShellState import ShellState

from .command_contract import COMMAND_CONTRACTS, format_command_help
from .helpers import (
    determine_perms_fromstr,
)

CommandReturn = Tuple[int, Tuple[list[str], list[str]]]


def _input_text(content: InputBuffer) -> str:
    """Materialize the exact text stream represented by an input buffer."""
    text = "\n".join(content.lines)
    return text + ("\n" if content.lines and content.has_trailing_newline else "")


def _output_lines(text: str) -> list[str]:
    """Convert selected stream text to the command output line protocol."""
    if not text:
        return []
    lines = text.split("\n")
    if text.endswith("\n"):
        lines.pop()
    return lines


@dataclass
class Interaction:
    mode: str  # "foreground", "prompt"
    prompt: str | None = None


@dataclass
class CommandResult:
    status: int = 0
    stdout: list[str] = field(default_factory=list)
    stderr: list[str] = field(default_factory=list)
    kind: Literal["text", "app"] = "text"
    interaction: Interaction | None = None
    payload: dict[str, Any] | None = None


class CommandLine:
    def __init__(self, pm: ProcessManager, nm: NetworkManager) -> None:
        self.process_manager = pm
        self.network = nm

        self.commands = {
            "ls": self.ls,
            "mkdir": self.mkdir,
            "cd": self.cd,
            "pwd": self.pwd,
            "rm": self.rm,
            "touch": self.touch,
            "cat": self.cat,
            "head": self.head,
            "tail": self.tail,
            "echo": self.echo,
            "chmod": self.chmod,
            "cp": self.cp,
            "mv": self.mv,
            "grep": self.grep,
            "ln": self.ln,
            "uniq": self.uniq,
            "sort": self.sort,
            "find": self.find,
            "sed": self.sed,
            "wc": self.wc,
            "ping": self.ping,
            "ps": self.ps,
            "sleep": self.sleep,
            "cut": self.cut,
        }

    def safe_args_param_pop(self, ctx: CommandContext, param: str) -> str:
        if ctx.args:
            return ctx.args.pop(0)
        raise ValueError(f"{ctx.command}: parameter expected for {param}")

    def open_redirection(
        self, path: str, mode: Literal["read", "truncate", "append"], sys: SystemContext
    ) -> InputBuffer | FileNode | str:
        if mode == "read":
            node = sys.fs.resolve(path)
            if isinstance(node, str):
                return node
            if node.get_type() != NodeType.FILE:
                return "Not a regular file"
            return InputBuffer.from_file(node)

        parent_result = sys.fs.resolve_parent(path)
        if isinstance(parent_result, str):
            return parent_result
        parent, name = parent_result
        node = parent.access(name)
        if node is None:
            inode = Inode(NodeType.FILE)
            error = parent.add_child(name, inode)
            if error:
                return error
            node = parent.access(name)
        elif node.get_type() == NodeType.SYMLINK:
            node = sys.fs.resolve(path)
            if isinstance(node, str):
                return node

        if node.get_type() != NodeType.FILE:
            return "Not a regular file"
        if mode == "truncate":
            node.set_data([])
        return node

    def enter_command(self, raw: str, shell: ShellState) -> CommandResult:
        if not raw.strip():
            return CommandResult(status=shell.last_status)

        sys = SystemContext(shell.fs, self.process_manager, self.network, shell)
        try:
            tokens = lex(raw)
            parser = CommandParser(tokens)
            ast = parser.parse()
        except SyntaxError as error:
            message = str(error) or "invalid command syntax"
            result = CommandResult(2, stderr=[f"syntax error: {message}"])
            shell.last_status = result.status
            return result
        if isinstance(ast, Sequence):
            shell.continuation = None
            result = self.execute_sequence(ast.parts, sys)
        else:
            result = CommandResult(2, stderr=["syntax error: expected a command"])
        shell.last_status = result.status
        return result

    def _chain_continuation(self, shell: ShellState, callback) -> None:
        previous = shell.continuation

        def resume(completed: CommandResult) -> CommandResult:
            result = previous(completed) if previous is not None else completed
            return callback(result)

        shell.continuation = resume

    def resume_foreground(
        self, shell: ShellState, process, completed: CommandResult
    ) -> CommandResult:
        """Resume suspended AST execution after its foreground process ends."""
        if shell.foreground_pid == process.pid:
            shell.foreground_pid = None
        shell.last_status = completed.status
        continuation = shell.continuation
        shell.continuation = None
        if continuation is None:
            return completed
        try:
            result = continuation(completed)
            shell.last_status = result.status
            return result
        except Exception:
            if shell.foreground_pid is not None:
                active = self.process_manager.get_process(shell.foreground_pid)
                if active is not None:
                    active.status = ProcessState.TERMINATED
                    active.exit_status = 1
            shell.foreground_pid = None
            shell.continuation = None
            raise

    def execute_pipeline(
        self,
        pipe: Pipe,
        sys: SystemContext,
        inherited_stdin: InputBuffer | None = None,
    ) -> CommandResult:
        return self._run_pipeline(pipe.parts, 0, sys, inherited_stdin, [])

    def _run_pipeline(
        self,
        parts: list[Command],
        index: int,
        sys: SystemContext,
        stdin: InputBuffer | None,
        prior_stderr: list[str],
    ) -> CommandResult:
        if index >= len(parts):
            raise Exception("No Cmd Result given")
        result = self.execute_command(
            parts[index], sys, ExecutionContext(stdin=stdin)
        )
        stderr = prior_stderr + result.stderr
        sys.shell.last_status = result.status

        if result.interaction:
            if index + 1 < len(parts):
                # A suspended command's completed stdout becomes the next stage's
                # stdin. Earlier pipeline stderr was returned with the prompt already.
                self._chain_continuation(
                    sys.shell,
                    lambda completed: self._run_pipeline(
                        parts,
                        index + 1,
                        sys,
                        InputBuffer.from_lines(completed.stdout),
                        [],
                    ),
                )
                return CommandResult(
                    status=result.status,
                    stderr=stderr,
                    kind=result.kind,
                    interaction=result.interaction,
                    payload=result.payload,
                )
            result.stderr = stderr
            return result

        if index + 1 == len(parts):
            result.stderr = stderr
            return result
        return self._run_pipeline(
            parts,
            index + 1,
            sys,
            InputBuffer.from_lines(result.stdout),
            stderr,
        )

    def execute_andor(
        self, elem: AndOr, sys: SystemContext, exec_ctx: ExecutionContext
    ) -> CommandResult:
        cmd_result = self.execute_pipeline(elem.first, sys, exec_ctx.stdin)
        sys.shell.last_status = cmd_result.status
        return self._run_andor_rest(cmd_result, elem.rest, sys, exec_ctx)

    def _run_andor_rest(
        self,
        result: CommandResult,
        rest: list[tuple[str, Pipe]],
        sys: SystemContext,
        exec_ctx: ExecutionContext,
    ) -> CommandResult:
        if result.interaction:
            if rest:
                self._chain_continuation(
                    sys.shell,
                    lambda completed: self._run_andor_rest(
                        completed, rest, sys, exec_ctx
                    ),
                )
            return result
        if not rest:
            sys.shell.last_status = result.status
            return result

        operator, next_pipe = rest[0]
        should_run = (operator == "&&" and result.status == 0) or (
            operator == "||" and result.status != 0
        )
        if not should_run:
            return self._run_andor_rest(result, rest[1:], sys, exec_ctx)

        next_result = self.execute_pipeline(next_pipe, sys, exec_ctx.stdin)
        sys.shell.last_status = next_result.status
        if next_result.interaction:
            if rest[1:]:
                # Results before this suspension have already been returned to the
                # client; the continuation emits only output produced after resuming.
                self._chain_continuation(
                    sys.shell,
                    lambda completed: self._run_andor_rest(
                        completed, rest[1:], sys, exec_ctx
                    ),
                )
            return self._combine_results(result, next_result)
        return self._run_andor_rest(
            self._combine_results(result, next_result), rest[1:], sys, exec_ctx
        )

    @staticmethod
    def _combine_results(
        first: CommandResult | None, second: CommandResult
    ) -> CommandResult:
        if first is None:
            return second
        return CommandResult(
            status=second.status,
            stdout=first.stdout + second.stdout,
            stderr=first.stderr + second.stderr,
            kind=second.kind,
            interaction=second.interaction,
            payload=second.payload,
        )

    def execute_command(
        self, command: Command, sys: SystemContext, exec_ctx: ExecutionContext
    ) -> CommandResult:
        # A branch inherits stdin but owns its redirection descriptors.
        local_ctx = ExecutionContext(stdin=exec_ctx.stdin)
        redirs = command.pre_redirs + command.post_redirs
        for assign in command.assignments:
            sys.shell.vars[assign.name] = assign.value.parts[0]

        if (
            command.assignments
            and isinstance(command.atom, SimpleCommand)
            and not command.atom.args
        ):
            return CommandResult(0)

        for redir in redirs:
            if redir.op == "<":
                source = self.open_redirection(redir.target, "read", sys)
                if isinstance(source, str):
                    return CommandResult(1, stderr=[f"{redir.target}: {source}"])
                local_ctx.stdin = source
            elif redir.op == "<<":
                heredoc_command = copy.deepcopy(command)
                heredoc_command.pre_redirs = [
                    item for item in heredoc_command.pre_redirs if item.op != "<<"
                ]
                heredoc_command.post_redirs = [
                    item for item in heredoc_command.post_redirs if item.op != "<<"
                ]
                proc = self.process_manager.create_process(
                    f"heredoc {redir.target}",
                    parent=self.process_manager.default_parent_pid,
                )

                def complete_heredoc(
                    lines: list[str],
                    pending_command: Command = heredoc_command,
                    heredoc_process=proc,
                ):
                    result = self.execute_command(
                        pending_command,
                        sys,
                        ExecutionContext(stdin=InputBuffer.from_lines(lines)),
                    )
                    heredoc_process.exit_status = result.status
                    return result.stdout, result.stderr
                proc.program = HeredocProgram(
                    proc,
                    redir.target,
                    complete_heredoc,
                )
                stdout, stderr = proc.program.start()
                sys.shell.foreground_pid = proc.pid
                return CommandResult(
                    stdout=stdout,
                    stderr=stderr,
                    interaction=Interaction(
                        mode="foreground",
                        prompt=proc.program.prompt,
                    ),
                )
            elif redir.op == ">":
                local_ctx.stdout = self.open_redirection(redir.target, "truncate", sys)
                if isinstance(local_ctx.stdout, str):
                    return CommandResult(1, stderr=[local_ctx.stdout])
            elif redir.op == ">>":
                local_ctx.stdout = self.open_redirection(redir.target, "append", sys)
                if isinstance(local_ctx.stdout, str):
                    return CommandResult(1, stderr=[local_ctx.stdout])
        cmd_result = self.execute_atom(command.atom, sys, local_ctx)
        if isinstance(local_ctx.stdout, FileNode):
            local_ctx.stdout.append_data(cmd_result.stdout)
            cmd_result.stdout = []
        return cmd_result

    def execute_atom(
        self, atom: Atom, sys: SystemContext, exec_ctx: ExecutionContext
    ) -> CommandResult:
        if isinstance(atom, SimpleCommand):
            if exec_ctx.stdin is None:
                fdin = InputBuffer()
            else:
                fdin = exec_ctx.stdin
            args = []
            for arg in atom.args:
                word = ""
                for part in arg.parts:
                    if isinstance(part, str):
                        word += part
                    else:
                        if part.name == "?":
                            word += str(sys.shell.last_status)
                        elif part.name not in sys.shell.vars:
                            return CommandResult(
                                1,
                                [],
                                [f"Var Used which is unassigned: {part.name}"],
                                "text",
                                None,
                            )
                        else:
                            word += sys.shell.vars[part.name]
                args.append(word)
            return self.execute(args, fdin, sys)
        else:
            # save state
            saved_cwd = sys.shell.cwd
            saved_env = sys.shell.vars.copy()
            saved_fs_current = sys.fs.current
            saved_fs_cwd = sys.fs.cwd
            try:
                return self.execute_sequence(atom.sequence.parts, sys, exec_ctx.stdin)
            finally:
                sys.shell.cwd = saved_cwd
                sys.shell.vars = saved_env
                sys.fs.current = saved_fs_current
                sys.fs.cwd = saved_fs_cwd

    def execute_sequence(
        self,
        parts: list[Job],
        sys: SystemContext,
        inherited_stdin: InputBuffer | None = None,
    ) -> CommandResult:
        return self._run_sequence(parts, 0, sys, inherited_stdin)

    def _run_sequence(
        self,
        parts: list[Job],
        index: int,
        sys: SystemContext,
        stdin: InputBuffer | None,
        accumulated: CommandResult | None = None,
    ) -> CommandResult:
        if index >= len(parts):
            raise Exception("cmd being empty")
        job = parts[index]
        if job.background:
            result = self._schedule_background_job(job, sys, stdin)
            aggregate = self._combine_results(accumulated, result)
            if index + 1 == len(parts):
                return aggregate
            return self._run_sequence(
                parts, index + 1, sys, stdin, aggregate
            )

        result = self.execute_andor(job.pipeline, sys, ExecutionContext(stdin=stdin))
        aggregate = self._combine_results(accumulated, result)
        if result.interaction and index + 1 < len(parts):
            self._chain_continuation(
                sys.shell,
                lambda completed: self._run_sequence(
                    parts,
                    index + 1,
                    sys,
                    stdin,
                    self._combine_results(accumulated, completed),
                ),
            )
            # Defer completed jobs' output while the list is suspended. The resumed
            # result includes that prefix once, along with the commands that follow.
            return result
        if result.interaction or index + 1 == len(parts):
            return aggregate
        return self._run_sequence(parts, index + 1, sys, stdin, aggregate)

    def _schedule_background_job(
        self, job: Job, sys: SystemContext, stdin: InputBuffer | None
    ) -> CommandResult:
        description = self.describe_andor(job.pipeline)
        launch_cwd = sys.shell.cwd
        launch_vars = sys.shell.vars.copy()
        launch_fs_current = sys.fs.current
        launch_fs_cwd = sys.fs.cwd
        process = self.process_manager.create_process(
            description, parent=self.process_manager.default_parent_pid
        )
        sys.shell.background_jobs[process.pid] = description

        def run_background(
            continuation=None,
            completed=None,
            job=job,
            process=process,
            launch_cwd=launch_cwd,
            launch_vars=launch_vars,
            launch_fs_current=launch_fs_current,
            launch_fs_cwd=launch_fs_cwd,
        ):
            prior_status = sys.shell.last_status
            current_cwd = sys.shell.cwd
            current_vars = sys.shell.vars.copy()
            current_fs_current = sys.fs.current
            current_fs_cwd = sys.fs.cwd
            current_foreground_pid = sys.shell.foreground_pid
            current_continuation = sys.shell.continuation
            sys.shell.continuation = None
            sys.shell.foreground_pid = None
            sys.shell.cwd = launch_cwd
            sys.shell.vars = launch_vars.copy()
            sys.fs.current = launch_fs_current
            sys.fs.cwd = launch_fs_cwd
            sys.shell.background_pid = process.pid
            sys.shell.background_children.setdefault(process.pid, [])
            try:
                result = (
                    continuation(completed)
                    if continuation is not None
                    else self.execute_andor(
                        job.pipeline,
                        sys,
                        ExecutionContext(stdin=stdin),
                    )
                )
                job_continuation = sys.shell.continuation
                sys.shell.continuation = None
                if result.interaction is not None:
                    if result.interaction.mode != "background_wait":
                        interactive_pid = sys.shell.foreground_pid
                        interactive = (
                            self.process_manager.get_process(interactive_pid)
                            if interactive_pid is not None
                            else None
                        )
                        if interactive is not None:
                            interactive.status = ProcessState.TERMINATED
                        if sys.shell.foreground_pid == interactive_pid:
                            sys.shell.foreground_pid = None
                        job_continuation = None
                return (
                    result.stdout,
                    result.stderr,
                    result.status,
                    result.interaction,
                    job_continuation,
                )
            finally:
                sys.shell.background_pid = None
                sys.shell.continuation = current_continuation
                sys.shell.foreground_pid = current_foreground_pid
                sys.shell.cwd = current_cwd
                sys.shell.vars = current_vars
                sys.fs.current = current_fs_current
                sys.fs.cwd = current_fs_cwd
                sys.shell.last_status = prior_status

        children = sys.shell.background_children.setdefault(process.pid, [])
        process.program = BackgroundJobProgram(process, run_background, children)
        return CommandResult(stdout=[f"[job {process.pid}] started {description}"])

    @staticmethod
    def describe_andor(andor: AndOr) -> str:
        def describe_word(word) -> str:
            return "".join(
                part if isinstance(part, str) else f"${part.name}"
                for part in word.parts
            )

        def describe_command(command: Command) -> str:
            if isinstance(command.atom, SimpleCommand):
                text = " ".join(describe_word(arg) for arg in command.atom.args)
            else:
                text = "( … )"
            for redirection in command.pre_redirs + command.post_redirs:
                text += f" {redirection.op} {redirection.target}"
            return text.strip()

        def describe_pipe(pipe: Pipe) -> str:
            return " | ".join(describe_command(command) for command in pipe.parts)

        text = describe_pipe(andor.first)
        for operator, pipe in andor.rest:
            text += f" {operator} {describe_pipe(pipe)}"
        return text

    def cancel_background_job(self, pid: int, shell: ShellState) -> bool:
        if pid not in shell.background_jobs:
            return False
        process = self.process_manager.get_process(pid)
        if process is None or process.status == ProcessState.TERMINATED:
            return False
        for child in shell.background_children.get(pid, []):
            child.status = ProcessState.TERMINATED
        process.exit_status = 130
        process.stderr.append("background job cancelled")
        process.status = ProcessState.TERMINATED
        return True

    def execute(
        self, args: list[str], fdin: InputBuffer, sys: SystemContext
    ) -> CommandResult:

        if not args:
            return CommandResult(1, stderr=["No command given"])

        command = args[0]

        ctx = CommandContext(
            system=sys,
            command=command,
            args=args[1:],
            stdin=fdin,
            stdout=None,
        )

        handler = self.commands.get(command)

        if handler is None:
            return CommandResult(1, stderr=["Unknown command given"])

        # Help is shared by all registered commands. echo explicitly treats
        # --help as ordinary text, as documented by its contract.
        if command not in {"echo", "cat"} and "--help" in ctx.args:
            return CommandResult(0, stdout=self.useage(command))

        return handler(ctx)

    def useage(self, type: str) -> list[str]:
        if type not in COMMAND_CONTRACTS:
            return [f"{type}: help is unavailable\n"]
        return format_command_help(type)

    def sleep(self, ctx: CommandContext) -> CommandResult:
        if ctx.args == ["--help"]:
            return CommandResult(0, stdout=self.useage("sleep"))
        if not ctx.args:
            return CommandResult(1, stderr=["sleep: Missing Argument"])

        total_seconds = 0
        multipliers = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}
        for duration in ctx.args:
            # Match a complete signed decimal magnitude and an optional unit;
            # fullmatch rejects unsupported suffixes and trailing text.
            match = re.fullmatch(
                r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))([smhd]?)", duration
            )
            if match is None:
                return CommandResult(
                    1, stderr=[f"sleep: invalid time interval '{duration}'"]
                )
            # Keep decimal durations exact so converting them to scheduler ticks
            # never depends on binary floating point rounding.
            value = Fraction(match.group(1))
            if value < 0:
                return CommandResult(
                    1, stderr=[f"sleep: invalid time interval '{duration}'"]
                )
            total_seconds += value * multipliers[match.group(2)]

        ticks = math.ceil(total_seconds)
        if ticks == 0:
            return CommandResult()

        # Create process
        proc = self.process_manager.create_process(
            f"sleep {" ".join(ctx.args)}",
            parent=(
                ctx.system.shell.background_pid
                if ctx.system.shell.background_pid is not None
                else self.process_manager.default_parent_pid
            ),
        )

        proc.program = SleepProgram(proc, ticks=ticks)
        shell = ctx.system.shell
        if shell.background_pid is not None:
            shell.background_children.setdefault(shell.background_pid, []).append(proc)
            return CommandResult(0, interaction=Interaction(mode="background_wait"))

        proc.foreground = True
        shell.foreground_pid = proc.pid
        return CommandResult(0, interaction=Interaction(mode="foreground"))

    def cut(self, ctx: CommandContext) -> CommandResult:
        delimiter = "\t"
        fields: list[int] | None = None
        files: list[str] = []
        only_delim = False

        try:
            while ctx.args:
                arg = ctx.args.pop(0)
                if arg == "--":
                    files.extend(ctx.args)
                    ctx.args.clear()
                    break
                elif arg == "-d":
                    delimiter = self.safe_args_param_pop(ctx, "-d")
                    if len(delimiter) > 1:
                        raise ValueError("cut: delimiter must be a single character")
                    delimiter = delimiter or "\0"
                elif arg == "-f":
                    if fields is not None:
                        raise ValueError("cut: only one field list may be specified")
                    value = self.safe_args_param_pop(ctx, "-f")
                    try:
                        fields = [int(field) for field in value.split(",")]
                    except ValueError:
                        raise ValueError("cut: bad value given for -f") from None
                    if any(field < 1 for field in fields):
                        raise ValueError("cut: fields are numbered from 1")
                elif arg == "-s":
                    only_delim = True
                elif arg == "-" or not arg.startswith("-"):
                    files.append(arg)
                else:
                    raise ValueError(f"cut: unknown option '{arg}'")

            if fields is None:
                raise ValueError("cut: a field list must be specified with -f")
        except ValueError as error:
            return CommandResult(1, stderr=[str(error)])

        fields = sorted(set(fields))
        stdout = []
        stderr = []
        for filename in files or ["-"]:
            if filename == "-":
                content = ctx.stdin
            else:
                node = ctx.system.fs.resolve(filename)
                if isinstance(node, str):
                    if "/" not in filename and node.startswith("No directory named "):
                        stderr.append(f"cut: {filename} does not exist")
                        continue
                    stderr.append(f"cut: {filename}: {node}")
                    continue
                if node.get_type() == NodeType.DIRECTORY:
                    stderr.append(f"cut: {filename}: Is a directory")
                    continue
                content = InputBuffer.from_file(node)

            for line in content.lines:
                if delimiter not in line:
                    if not only_delim:
                        stdout.append(line)
                    continue
                parts = line.split(delimiter)
                selected = [parts[field - 1] for field in fields if field <= len(parts)]
                stdout.append(delimiter.join(selected))

        return CommandResult(1 if stderr else 0, stdout=stdout, stderr=stderr)

    def ps(self, ctx: CommandContext) -> CommandResult:
        if "--help" in ctx.args:
            idx = ctx.args.index("--help")
            if idx + 1 < len(ctx.args):
                ty = ctx.args[idx + 1]
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
        args = list(ctx.args)
        while args:
            arg = args.pop(0)
            if arg in ("-e", "-A"):
                parameters["all"] = True
            elif arg == "-l":
                parameters["long"] = True
            elif arg in ("-C", "-p", "-q"):
                if not args or not args[0]:
                    return CommandResult(1, stderr=[f"ps: argument required for {arg}"])
                value = args.pop(0)
                if arg == "-C":
                    parameters["command"] = value
                    continue
                try:
                    pids = [int(pid) for pid in value.split(",")]
                    if any(pid <= 0 for pid in pids):
                        raise ValueError
                except ValueError:
                    return CommandResult(1, stderr=[f"ps: invalid process ID list '{value}'"])
                parameters["pid"] = set(pids)
            else:
                return CommandResult(1, stderr=[f"ps: unknown option '{arg}'"])
        return CommandResult(stdout=self.process_manager.list_processes(parameters))

    def ping(self, ctx: CommandContext) -> CommandResult:
        if ctx.args in (["--help"], ["-h"]):
            return CommandResult(stdout=self.useage("ping"))
        args = list(ctx.args)
        host = None
        count = 4
        timeout = Fraction(1)
        while args:
            arg = args.pop(0)
            if arg in ("-c", "-W"):
                if not args or not args[0]:
                    return CommandResult(
                        1, stderr=[f"ping: argument required for {arg}"]
                    )
                value = args.pop(0)
                if arg == "-c":
                    if len(value) > 2 or not re.fullmatch(r"\d+", value):
                        return CommandResult(
                            1, stderr=[f"ping: invalid count: '{value}'"]
                        )
                    count = int(value)
                    if not 1 <= count <= 10:
                        return CommandResult(
                            1, stderr=["ping: count must be between 1 and 10"]
                        )
                else:
                    # Accept unsigned decimal seconds (including .5 or 1.) but
                    # reject signs, exponent notation, whitespace, and suffixes.
                    if len(value) > 20 or not re.fullmatch(
                        r"(?:\d+(?:\.\d*)?|\.\d+)", value
                    ):
                        return CommandResult(
                            1, stderr=[f"ping: invalid timeout: '{value}'"]
                        )
                    timeout = Fraction(value)
                    if timeout <= 0 or timeout > 60:
                        return CommandResult(
                            1,
                            stderr=[
                                "ping: timeout must be greater than 0 and at most 60 seconds"
                            ],
                        )
            elif arg.startswith("-"):
                return CommandResult(1, stderr=[f"ping: unknown option '{arg}'"])
            elif host is None:
                host = arg
            else:
                return CommandResult(1, stderr=["ping: expected one destination"])
        if not host:
            return CommandResult(1, stderr=["ping: destination required"])

        network = self.network.get_network(host)
        if network is None:
            return CommandResult(
                2, stderr=[f"ping: unknown simulated destination '{host}'"]
            )

        stdout = [f"PING {host} ({network.ip}): 56 data bytes"]
        received = 0
        for sequence in range(1, count + 1):
            if not network.online:
                stdout.append(
                    f"From {network.ip} icmp_seq={sequence} "
                    "Destination Host Unreachable"
                )
            elif timeout < Fraction(1, 100):
                stdout.append(f"Request timeout for icmp_seq={sequence}")
            else:
                received += 1
                stdout.append(
                    f"64 bytes from {network.ip}: icmp_seq={sequence} "
                    "ttl=64 time=10.0 ms"
                )

        lost = count - received
        loss_percent = lost * 100 // count
        stdout.extend(
            [
                f"--- {host} ping statistics ---",
                f"{count} packets transmitted, {received} received, "
                f"{loss_percent}% packet loss",
            ]
        )
        return CommandResult(0 if received == count else 1, stdout=stdout)

    def find(self, ctx: CommandContext) -> CommandResult:
        if len(ctx.args) < 1:
            return CommandResult(
                1, stderr=["find: atleast one argument needs to be given"]
            )
        if ctx.args[0] in ("-h", "--help"):
            return CommandResult(0, stdout=self.useage("find"))
        if ctx.args[0].startswith("-"):
            return CommandResult(2, stderr=[f"find: unsupported option '{ctx.args[0]}'"])
        if not len(ctx.args):
            return CommandResult(
                1, stderr=["find: starting locaiton needs to be given"]
            )
        starting = []
        while (
            len(ctx.args)
            and not ctx.args[0].startswith("-")
            and ctx.args[0] not in ["(", "!", ")"]
        ):
            starting.append(ctx.args.pop(0))
        if not len(starting):
            starting = ["."]
        if not len(ctx.args):
            node = FilterNode("", "")
        else:
            fparser = FindParser(ctx.args)
            try:
                node = fparser.parse()
            except (SyntaxError, ValueError, RecursionError) as e:
                return CommandResult(2, stderr=[f"find: {str(e)}"])

        # Supported predicates are deliberately small and side-effect free.
        # Actions are rejected until find has a safe command-action contract.
        pending = [node]
        expression_nodes = 0
        while pending:
            expression = pending.pop()
            expression_nodes += 1
            if expression_nodes > 256:
                return CommandResult(2, stderr=["find: expression is too complex"])
            if isinstance(expression, FilterNode):
                if expression.type in ("", "-true", "-false", "-empty"):
                    continue
                if expression.type == "-type":
                    if expression.value not in ("f", "d", "l"):
                        return CommandResult(
                            2,
                            stderr=[
                                f"find: Value for -type not allowed: {expression.value}"
                            ],
                        )
                    continue
                if expression.type == "-name":
                    continue
                if expression.type == "-delete":
                    return CommandResult(
                        2, stderr=["find: -delete actions are not supported"]
                    )
                return CommandResult(
                    2, stderr=[f"find: unsupported predicate: {expression.type}"]
                )
            if isinstance(expression, ExecNode):
                return CommandResult(
                    2, stderr=["find: -exec actions are not supported"]
                )
            if isinstance(expression, NotNode):
                pending.append(expression.node)
            elif isinstance(expression, (AndNode, OrNode)):
                pending.extend((expression.left, expression.right))
            else:
                return CommandResult(2, stderr=["find: unsupported expression"])
        stdout = []
        stderr = []
        for start in starting:
            # Do not follow a final symlink: find reports links as leaves by
            # default, while path components before the final one still resolve.
            parent_info = ctx.system.fs.resolve_parent(start.rstrip("/"))
            start_node = None
            if not isinstance(parent_info, str):
                parent, leaf = parent_info
                candidate = parent.access(leaf)
                if candidate is not None and candidate.get_type() == NodeType.SYMLINK:
                    start_node = candidate
            if start_node is None:
                start_node = ctx.system.fs.resolve(start)
            if isinstance(start_node, str):
                stderr.append(start_node)
                continue

            try:
                path_prefix = start.rstrip("/") or "/"
                toprints, execs = start_node.find(node, ".", path_prefix)
            except (SyntaxError, ValueError, re.error, RecursionError) as error:
                return CommandResult(2, stderr=[f"find: {error}"])
            stdout.extend(toprints)
        return CommandResult(1 if stderr else 0, stdout, stderr)

    def sed(self, ctx: CommandContext) -> CommandResult:
        from game.sed_engine import run_sed

        return run_sed(ctx, self.useage)

    def wc(self, ctx: CommandContext) -> CommandResult:
        stdout = []
        stderr = []
        status = 0
        words = bytes_flag = chars = lines = False
        files: list[str] = []

        for arg in ctx.args:
            if arg in ("-c", "--bytes"):
                bytes_flag = True
            elif arg in ("-m", "--chars"):
                chars = True
            elif arg in ("-l", "--lines"):
                lines = True
            elif arg in ("-w", "--words"):
                words = True
            elif arg.startswith("-") and arg != "-":
                return CommandResult(1, stderr=[f"wc: unknown option '{arg}'"])
            else:
                files.append(arg)

        if not any([words, bytes_flag, chars, lines]):
            # Match the conventional default wc columns: lines, words, bytes.
            words = bytes_flag = lines = True

        if not len(files):
            files.append("-")

        total_lines = 0
        total_words = 0
        total_chars = 0
        total_bytes = 0

        for file in files:
            if file == "-":
                content = ctx.stdin
            else:
                # Get filenode
                node = ctx.system.fs.resolve(file)
                if isinstance(node, str):
                    stderr.append(node)
                    status = 1
                    continue

                # Check for file
                if node.get_type() == NodeType.DIRECTORY:
                    stderr.append(f"wc: cannot perform operation on directory ({file})")
                    status = 1
                    continue
                content = InputBuffer.from_file(node)

            text = _input_text(content)
            lcount = text.count("\n")
            wcount = len(text.split())
            ccount = len(text)
            bcount = len(text.encode("utf-8"))

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

        return CommandResult(status, stdout, stderr)

    def cp(self, ctx: CommandContext) -> CommandResult:
        if "--help" in ctx.args:
            return CommandResult(0, stdout=self.useage("cp"))

        args = list(ctx.args)
        recursive = False
        verbose = False
        while args and args[0].startswith("-") and args[0] != "-":
            option_arg = args.pop(0)
            for option in option_arg[1:]:
                if option in ("r", "R"):
                    recursive = True
                elif option == "v":
                    verbose = True
                else:
                    return CommandResult(
                        1, stderr=[f"cp: unknown argument ({option}) given"]
                    )
        if len(args) < 2:
            return CommandResult(1, stderr=["cp: expected at least two arguments"])

        sources, target_path = args[:-1], args[-1]
        if not target_path:
            return CommandResult(1, stderr=["cp: invalid destination ''"])
        if any(not source_path for source_path in sources):
            return CommandResult(1, stderr=["cp: cannot stat '': Invalid path"])
        fs = ctx.system.fs
        stdout: list[str] = []
        stderr: list[str] = []
        target = fs.resolve(target_path)
        target_exists = not isinstance(target, str)
        target_parent = None
        target_name = None
        if not target_exists:
            parent_info = fs.resolve_parent(target_path)
            if isinstance(parent_info, str):
                return CommandResult(1, stderr=[f"cp: {parent_info}"])
            target_parent, target_name = parent_info
            existing_child = target_parent.access(target_name)
            if existing_child is not None:
                target = existing_child
                target_exists = True
            elif len(sources) > 1:
                return CommandResult(
                    1, stderr=[f"cp: target '{target_path}' is not a directory"]
                )

        resolved_sources: list[tuple[str, FileNode]] = []
        for source_path in sources:
            source = fs.resolve(source_path)
            if isinstance(source, str):
                return CommandResult(
                    1, stderr=[f"cp: cannot stat '{source_path}': {source}"]
                )
            resolved_sources.append((source_path, source))

        target_type = target.get_type() if target_exists else None
        if (
            len(resolved_sources) > 1
            and target_exists
            and target_type != NodeType.DIRECTORY
        ):
            return CommandResult(
                1, stderr=[f"cp: target '{target_path}' is not a directory"]
            )

        for source_path, source in resolved_sources:
            if target_exists and source is target:
                return CommandResult(
                    1,
                    stderr=[
                        f"cp: '{source_path}' and '{target_path}' are the same file"
                    ],
                )
            if source.get_type() != NodeType.DIRECTORY:
                continue
            if not recursive:
                stderr.append(
                    f"cp: -r not specified; omitting directory '{source_path}'"
                )
                continue
            if target_exists and target_type == NodeType.FILE:
                return CommandResult(
                    1,
                    stderr=[
                        f"cp: cannot overwrite non-directory '{target_path}' "
                        f"with directory '{source_path}'"
                    ],
                )
            ancestor = target if target_exists else target_parent
            while ancestor is not None:
                if ancestor is source:
                    return CommandResult(
                        1,
                        stderr=[
                            f"cp: cannot copy a directory, '{source_path}', "
                            f"into itself, '{target_path}'"
                        ],
                    )
                ancestor = ancestor.parent

        def clone_inode(source_inode: Inode) -> Inode:
            inode = Inode(source_inode.type)
            inode.data = copy.deepcopy(source_inode.data)
            inode.has_trailing_newline = source_inode.has_trailing_newline
            inode.permissions = copy.deepcopy(source_inode.permissions)
            return inode

        def clone_with_name(node: FileNode, name: str, parent: FileNode) -> FileNode:
            clone = FileNode(parent, name, clone_inode(node.inode))
            clone.depth = parent.depth + 1
            clone.items = [
                clone_with_name(child, child.name, clone) for child in node.items
            ]
            return clone

        if target_exists and target_type == NodeType.DIRECTORY:
            planned_names: set[str] = set()
            for _, source in resolved_sources:
                if source.get_type() == NodeType.DIRECTORY and not recursive:
                    continue
                if (
                    source.name in planned_names
                    or target.access(source.name) is not None
                ):
                    return CommandResult(
                        1,
                        stderr=[
                            f"cp: cannot create '{target_path}/{source.name}': File exists"
                        ],
                    )
                planned_names.add(source.name)

        for source_path, source in resolved_sources:
            source_type = source.get_type()
            if source_type == NodeType.DIRECTORY and not recursive:
                continue
            if target_exists and target_type == NodeType.DIRECTORY:
                copied = clone_with_name(source, source.name, target)
                target.items.append(copied)
            elif target_exists and target_type == NodeType.FILE:
                if source_type != NodeType.FILE:
                    continue
                target.inode = clone_inode(source.inode)
            else:
                if target_parent is None or target_name is None:
                    return CommandResult(
                        1,
                        stdout,
                        stderr + [f"cp: invalid destination '{target_path}'"],
                    )
                copied = clone_with_name(source, target_name, target_parent)
                target_parent.items.append(copied)
                target = copied
                target_type = copied.get_type()
                target_exists = True
            if verbose:
                stdout.append(f"cp: Copied '{source_path}' to '{target_path}'")

        return CommandResult(1 if stderr else 0, stdout, stderr)

    def mv(self, ctx: CommandContext) -> CommandResult:
        verbose = False
        stdout = []
        stderr = []
        if "--help" in ctx.args:
            return CommandResult(0, stdout=self.useage("mv"))
        args = ctx.args.copy()
        while args and args[0].startswith("-") and args[0] != "-":
            arg = args.pop(0)
            for option in arg[1:]:
                if option == "v":
                    verbose = True
                else:
                    return CommandResult(
                        1, stderr=[f"mv: unknown argument ({option}) given"]
                    )
        if len(args) < 2:
            return CommandResult(1, stderr=["mv: expected at least two arguments"])

        files, target = args[:-1], args[-1]
        fs = ctx.system.fs
        target_node = fs.resolve(target)
        target_directory = (
            not isinstance(target_node, str)
            and target_node.get_type() == NodeType.DIRECTORY
        )
        if len(files) > 1 and not target_directory:
            return CommandResult(
                1, stderr=[f"mv: target '{target}' is not a directory"]
            )

        if target_directory:
            destination_parent = target_node
            destination_name = None
        else:
            destination = fs.resolve_parent(target)
            if isinstance(destination, str):
                return CommandResult(1, stderr=[f"mv: {target}: {destination}"])
            destination_parent, destination_name = destination

        # Resolve and validate all operands before changing any tree entries.
        moves: list[tuple[str, FileNode, FileNode, str, FileNode | None]] = []
        for file in files:
            source = fs.resolve_parent(file)
            if isinstance(source, str):
                stderr.append(f"mv: could not find file {file}")
                continue
            source_parent, source_name = source
            source_node = source_parent.access(source_name)
            if source_node is None:
                stderr.append(f"mv: could not find file {file}")
                continue

            name = source_name if destination_name is None else destination_name
            if source_node.get_type() == NodeType.DIRECTORY:
                ancestor = destination_parent
                while ancestor is not None and ancestor is not source_node:
                    ancestor = ancestor.parent
                if ancestor is source_node:
                    stderr.append(f"mv: cannot move '{file}' into itself")
                    continue

            existing = destination_parent.access(name)
            if existing is source_node:
                stderr.append(f"mv: '{file}' and '{target}' are the same file")
                continue
            if existing is not None and (
                source_node.get_type() != NodeType.FILE
                or existing.get_type() != NodeType.FILE
            ):
                stderr.append(f"mv: cannot overwrite '{target}' with '{file}'")
                continue
            moves.append((file, source_parent, source_node, name, existing))

        source_nodes = {id(move[2]) for move in moves}
        final_names: set[str] = set()
        for file, _, source_node, name, existing in moves:
            if name in final_names:
                stderr.append(f"mv: duplicate destination name '{name}'")
            final_names.add(name)
            if existing is not None and id(existing) in source_nodes:
                stderr.append(f"mv: cannot overwrite '{target}' with '{file}'")

        if stderr:
            return CommandResult(1, stdout, stderr)

        for _, _, _, _, existing in moves:
            if existing is not None:
                destination_parent.items = [
                    item for item in destination_parent.items if item is not existing
                ]
        for file, source_parent, source_node, name, _ in moves:
            source_parent.items = [
                item for item in source_parent.items if item is not source_node
            ]
            source_node.name = name
            source_node.parent = destination_parent
            destination_parent.items.append(source_node)
            if verbose:
                action = "Moved" if target_directory else "Renamed"
                connector = "to" if target_directory else "->"
                stdout.append(f"{action} {file} {connector} {target}")

        fs.filehead.update_subtree_depth()
        return CommandResult(0, stdout, stderr)

    def grep(self, ctx: CommandContext) -> CommandResult:
        ignore_case = False
        invert = False
        line_numbers = False
        list_files = False
        count_lines = False
        whole_word = False
        whole_line = False
        only_matching = False
        recursive = False
        force_filename = False
        suppress_filename = False
        includes: list[str] = []
        excludes: list[str] = []
        excluded_dirs: list[str] = []
        pattern: str | None = None
        args = list(ctx.args)
        files: list[str] = []
        index = 0

        # Consume options before the positional pattern, then treat remaining words
        # as file operands. Copying args keeps command execution from mutating parser state.
        while index < len(args):
            arg = args[index]
            index += 1
            if arg == "--":
                # After --, option-looking text is data: the first word is the pattern
                # if one has not been supplied, and every later word names an input.
                if pattern is None:
                    if index >= len(args):
                        return CommandResult(2, stderr=["grep: pattern not given"])
                    pattern = args[index]
                    index += 1
                files.extend(args[index:])
                break
            if arg == "--help":
                return CommandResult(0, stdout=self.useage("grep"))
            if arg.startswith("--include="):
                # Split only once so a glob may itself contain '=' characters.
                includes.append(arg.split("=", 1)[1])
            elif arg.startswith("--exclude="):
                excludes.append(arg.split("=", 1)[1])
            elif arg.startswith("--exclude-dir="):
                excluded_dirs.append(arg.split("=", 1)[1])
            elif arg in ("--include", "--exclude", "--exclude-dir"):
                if index >= len(args):
                    return CommandResult(2, stderr=[f"grep: argument required for {arg}"])
                value = args[index]
                index += 1
                {"--include": includes, "--exclude": excludes, "--exclude-dir": excluded_dirs}[arg].append(value)
            elif arg == "-e" or arg.startswith("--regexp="):
                if pattern is not None:
                    return CommandResult(2, stderr=["grep: only one pattern is supported"])
                if arg == "-e":
                    if index >= len(args):
                        return CommandResult(2, stderr=["grep: pattern not given"])
                    pattern = args[index]
                    index += 1
                else:
                    pattern = arg.split("=", 1)[1]
            elif arg in (
                "--ignore-case", "--invert-match", "--line-number",
                "--files-with-matches", "--count", "--word-regexp",
                "--line-regexp", "--only-matching", "--recursive",
                "--with-filename", "--no-filename",
            ):
                if arg == "--ignore-case":
                    ignore_case = True
                elif arg == "--invert-match":
                    invert = True
                elif arg == "--line-number":
                    line_numbers = True
                elif arg == "--files-with-matches":
                    list_files = True
                elif arg == "--count":
                    count_lines = True
                elif arg == "--word-regexp":
                    whole_word = True
                elif arg == "--line-regexp":
                    whole_line = True
                elif arg == "--only-matching":
                    only_matching = True
                elif arg == "--recursive":
                    recursive = True
                elif arg == "--with-filename":
                    force_filename = True
                else:
                    suppress_filename = True
            elif arg.startswith("-") and arg != "-":
                # Short flags may be grouped (for example, -in); reject unsupported
                # letters before opening inputs so a typo cannot look like no matches.
                for option in arg[1:]:
                    if option == "i":
                        ignore_case = True
                    elif option == "v":
                        invert = True
                    elif option == "n":
                        line_numbers = True
                    elif option == "l":
                        list_files = True
                    elif option == "c":
                        count_lines = True
                    elif option == "w":
                        whole_word = True
                    elif option == "x":
                        whole_line = True
                    elif option == "o":
                        only_matching = True
                    elif option == "r":
                        recursive = True
                    elif option == "H":
                        force_filename = True
                    elif option == "h":
                        suppress_filename = True
                    else:
                        return CommandResult(2, stderr=[f"grep: unsupported option '-{option}'"])
            elif pattern is None:
                pattern = arg
                files = args[index:]
                if files and files[0] == "--":
                    files = files[1:]
                break
            else:
                files.append(arg)

        if pattern is None:
            return CommandResult(2, stderr=["grep: pattern not given"])
        if not files:
            files = ["-"]
        # Listing matching files and printing per-file counts have distinct output
        # formats, so reject their ambiguous combination before scanning any input.
        if list_files and count_lines:
            return CommandResult(2, stderr=["grep: -l and -c cannot be combined"])

        regex_pattern = pattern
        if whole_word:
            regex_pattern = rf"(?<!\w)(?:{regex_pattern})(?!\w)"
        try:
            regex = re.compile(regex_pattern, re.IGNORECASE if ignore_case else 0)
        except re.error as error:
            return CommandResult(2, stderr=[f"grep: invalid regular expression: {error}"])

        stderr: list[str] = []
        candidates: list[tuple[str, InputBuffer]] = []
        had_error = False

        def file_is_selected(name: str) -> bool:
            # File filters match basenames; multiple include patterns are alternatives,
            # while any matching exclude pattern takes precedence.
            return (
                (not includes or any(fnmatch.fnmatchcase(name, item) for item in includes))
                and not any(fnmatch.fnmatchcase(name, item) for item in excludes)
            )

        def collect_file(node: FileNode, name: str) -> None:
            if node.get_type() == NodeType.FILE and file_is_selected(node.name):
                candidates.append((name, InputBuffer.from_file(node)))

        def collect_directory(node: FileNode, display_path: str) -> None:
            # Walk iteratively so deeply nested trees cannot exhaust Python's call
            # stack. Track node identities defensively in case a malformed tree cycles.
            pending = [(node, display_path)]
            visited: set[int] = set()
            while pending:
                current, current_path = pending.pop()
                if current.get_type() == NodeType.DIRECTORY:
                    if id(current) in visited:
                        continue
                    visited.add(id(current))

                    # Reverse the push order so popping keeps filesystem order.
                    # Directory symlinks are not pushed, which prevents link loops.
                    for child in reversed(current.items):
                        child_path = (
                            f"{current_path.rstrip('/')}/{child.name}"
                            if current_path
                            else child.name
                        )
                        if child.get_type() == NodeType.DIRECTORY:
                            if any(
                                fnmatch.fnmatchcase(child.name, item)
                                for item in excluded_dirs
                            ):
                                continue
                            pending.append((child, child_path))
                        elif child.get_type() == NodeType.FILE:
                            pending.append((child, child_path))
                elif current.get_type() == NodeType.FILE:
                    collect_file(current, current_path)

        for file in files:
            if file == "-":
                candidates.append(("(standard input)", ctx.stdin))
                continue
            node = ctx.system.fs.resolve(file)
            if isinstance(node, str):
                stderr.append(f"grep: {file} can not be found")
                had_error = True
            elif node.get_type() == NodeType.DIRECTORY:
                if not recursive:
                    stderr.append("Can't recursively search directory without -r option")
                    had_error = True
                else:
                    collect_directory(node, file)
            elif node.get_type() == NodeType.FILE:
                collect_file(node, file)
            else:
                stderr.append(f"grep: {file}: Not a regular file")
                had_error = True

        # Prefix output when the search can produce results from multiple inputs.
        # Explicit -H/-h options override this default in either direction.
        show_filenames = force_filename or (
            not suppress_filename
            and (len(files) > 1 or len(candidates) > 1)
        )
        stdout: list[str] = []
        any_selected = False
        for name, content in candidates:
            file_selected = False
            selected_count = 0
            file_output: list[str] = []
            for line_index, line in enumerate(content.lines, start=1):
                matches = list(regex.finditer(line))
                matched = regex.fullmatch(line) is not None if whole_line else bool(matches)
                selected = matched != invert
                if not selected:
                    continue
                file_selected = True
                selected_count += 1
                if count_lines or list_files:
                    continue
                if only_matching:
                    if invert:
                        continue
                    line_matches = [regex.fullmatch(line)] if whole_line else matches
                    for match in line_matches:
                        if match is None:
                            continue
                        text = match.group(0)
                        if line_numbers:
                            text = f"{line_index}:{text}"
                        if show_filenames:
                            text = f"{name}:{text}"
                        file_output.append(text)
                else:
                    text = line
                    if line_numbers:
                        text = f"{line_index}:{text}"
                    if show_filenames:
                        text = f"{name}:{text}"
                    file_output.append(text)

            any_selected |= file_selected
            if list_files:
                if file_selected:
                    stdout.append(name)
            elif count_lines:
                count_text = str(selected_count)
                if show_filenames:
                    count_text = f"{name}:{count_text}"
                stdout.append(count_text)
            else:
                stdout.extend(file_output)

        # Errors take precedence over matches; otherwise the shell status reports
        # whether at least one line was selected across all readable inputs.
        status = 2 if had_error else (0 if any_selected else 1)
        return CommandResult(status, stdout, stderr)

    def chmod(self, ctx: CommandContext) -> CommandResult:
        recurse = False
        verbose = False
        stdout = []
        stderr = []
        if ctx.args == ["--help"]:
            return CommandResult(0, stdout=self.useage("chmod"))
        args = ctx.args
        index = 0
        while index < len(args):
            arg = args[index]
            if arg == "--":
                index += 1
                break
            if arg == "--recursive":
                recurse = True
            elif arg == "--verbose":
                verbose = True
            elif arg.startswith("-") and arg != "-":
                for option in arg[1:]:
                    if option == "R":
                        recurse = True
                    elif option == "v":
                        verbose = True
                    else:
                        return CommandResult(1, stderr=["chmod: Unknown output given"])
            else:
                break
            index += 1

        operands = args[index:]
        if len(operands) < 2:
            return CommandResult(1, stderr=["chmod: expected at least two arguments"])
        d = determine_perms_fromstr(operands[0])
        if isinstance(d, str):
            return CommandResult(1, stderr=[d])

        for file in operands[1:]:
            target = ctx.system.fs.resolve(file)
            if isinstance(target, str):
                stderr.append(f"chmod: {target}")
                continue
            changes = target.update_permissions(d, recurse)
            if verbose:
                stdout.extend(changes)
        return CommandResult(1 if stderr else 0, stdout, stderr)

    def echo(self, ctx: CommandContext) -> CommandResult:
        output = " ".join(ctx.args)
        if output == "$?":
            return CommandResult(0, stdout=[str(ctx.system.fs.lcs)])
        return CommandResult(0, stdout=" ".join(ctx.args).split("\n"))

    @staticmethod
    def _parse_touch_date(
        date_text: str, date_format: str = "%Y-%m-%d"
    ) -> datetime.datetime | CommandResult:
        """Parse a touch date or return a command error for invalid input."""
        try:
            return datetime.datetime.strptime(date_text, date_format)
        except ValueError:
            return CommandResult(1, stderr=[f"touch: invalid date '{date_text}'"])

    def touch(self, ctx: CommandContext) -> CommandResult:
        if "--help" in ctx.args:
            return CommandResult(0, stdout=self.useage("touch"))
        if not len(ctx.args):
            return CommandResult(1, stderr=["touch: must give atleast one argument"])
        files: list[str] = []
        create = True
        changeaccess = False
        changemod = False
        date = datetime.datetime.now()
        stdout: list[str] = []
        stderr: list[str] = []
        status: int = 0
        while ctx.args:
            arg = ctx.args.pop(0)
            if arg == "-":
                pass
            elif arg.startswith("-"):
                if arg[1] == "-":
                    if arg == "--no-create":
                        create = False
                    elif arg.startswith("--date="):
                        date = self._parse_touch_date(arg.split("=", 1)[1])
                    elif arg == "--date":
                        if not len(ctx.args):
                            return CommandResult(
                                1, stderr=["touch: no parameter given for --date"]
                            )
                        date = self._parse_touch_date(ctx.args.pop(0))
                    else:
                        return CommandResult(
                            1, stderr=[f"touch: unknown parameter is given ({arg})"]
                        )
                else:
                    for option in arg[1:]:
                        match option:
                            case "c":
                                create = False
                            case "a":
                                changeaccess = True
                            case "m":
                                changemod = True
                            case "d":
                                if not len(ctx.args):
                                    return CommandResult(
                                        1, stderr=["touch: no parameter given for -d"]
                                    )
                                date = self._parse_touch_date(ctx.args.pop(0))
                                break
                            case "t":
                                if not len(ctx.args):
                                    return CommandResult(
                                        1, stderr=["touch: no parameter given for -t"]
                                    )
                                date = self._parse_touch_date(
                                    ctx.args.pop(0), "%Y%m%d%H%M"
                                )
                                break
                            case _:
                                return CommandResult(
                                    1, stderr=["touch: unknown argument given"]
                                )
            else:
                files.append(arg)
            if isinstance(date, CommandResult):
                return date
        if not len(files):
            return CommandResult(1, stderr=["touch: no file given"])
        if not changeaccess and not changemod:
            changeaccess = changemod = True
        fs = ctx.system.fs
        for file in files:
            fn = fs.resolve(file)
            if isinstance(fn, str):
                if not create:
                    continue

                resolved_parent = fs.resolve_parent(file)
                if isinstance(resolved_parent, str):
                    stderr.append(f"touch: {file}: {resolved_parent}")
                    status = 1
                    continue

                parent, filename = resolved_parent
                error = parent.add_child(filename, Inode(NodeType.FILE))
                if error:
                    stderr.append(f"touch: {file}: {error}")
                    status = 1
                    continue

                fn = parent.access(filename)
                if fn is None:
                    stderr.append(f"touch: {file}: unable to create file")
                    status = 1
                    continue

            if changeaccess:
                fn.inode.atime = date
            if changemod:
                fn.inode.mtime = date
        return CommandResult(status, stdout, stderr)

    def cat(self, ctx: CommandContext) -> CommandResult:
        stdout = []
        stderr = []
        status = 0
        numbering = False
        files = []
        while ctx.args:
            arg = ctx.args.pop(0)
            if arg == "--":
                files.extend(ctx.args)
                ctx.args.clear()
                break
            if arg == "--help":
                return CommandResult(0, stdout=self.useage("cat"))
            if arg == "-" or not arg.startswith("-"):
                files.append(arg)
                files.extend(ctx.args)
                ctx.args.clear()
                break
            for option in arg[1:]:
                match option:
                    case "n":
                        numbering = True
                    case _:
                        return CommandResult(
                            1, stderr=[f"cat: Unknown Argument Given ({option})"]
                        )

        files = files or ["-"]
        line_number = 1
        for filename in files:
            if filename == "-":
                content = ctx.stdin
            else:
                node = ctx.system.fs.resolve(filename)
                if isinstance(node, str):
                    stderr.append(f"cat: {filename}: {node}")
                    status = 1
                    continue

                if node.get_type() == NodeType.DIRECTORY:
                    stderr.append(f"cat: {filename}: Is a directory")
                    status = 1
                    continue
                content = InputBuffer.from_file(node)

            for line in content.lines:
                if numbering:
                    line = f"{line_number} {line}"
                    line_number += 1
                stdout.append(line)

        return CommandResult(status, stdout, stderr)

    def head(self, ctx: CommandContext) -> CommandResult:
        line_count: int | None = 10
        byte_count: int | None = None
        from_start = False
        files = []
        stdout = []
        stderr = []
        status = 0
        while ctx.args:
            arg = ctx.args.pop(0)
            if arg == "-":
                files.append(arg)
            elif arg.startswith("-"):
                if arg == "--help":
                    return CommandResult(0, stdout=self.useage("head"))
                elif arg in ("-n", "--lines"):
                    if not ctx.args:
                        return CommandResult(
                            1, stderr=["head: argument required for -n"]
                        )
                    value = ctx.args.pop(0)
                    try:
                        if value.startswith("++"):
                            raise ValueError
                        from_start = value.startswith("+")
                        line_count = int(value.lstrip("+"))
                    except ValueError:
                        return CommandResult(
                            1, stderr=[f"head: invalid line count '{value}'"]
                        )
                elif arg.startswith("--lines="):
                    val = arg.split("=", 1)[1]
                    try:
                        if val.startswith("++"):
                            raise ValueError
                        from_start = val.startswith("+")
                        line_count = int(val.lstrip("+"))
                    except ValueError:
                        return CommandResult(
                            1, stderr=[f"head: invalid line count '{val}'"]
                        )
                elif arg in ("-c", "--bytes"):
                    if not ctx.args:
                        return CommandResult(
                            1, stderr=["head: argument required for -c"]
                        )
                    value = ctx.args.pop(0)
                    try:
                        if value.startswith("++"):
                            raise ValueError
                        from_start = value.startswith("+")
                        byte_count = int(value.lstrip("+"))
                    except ValueError:
                        return CommandResult(
                            1, stderr=[f"head: invalid byte count '{value}'"]
                        )
                elif arg.startswith("--bytes="):
                    val = arg.split("=", 1)[1]
                    try:
                        if val.startswith("++"):
                            raise ValueError
                        from_start = val.startswith("+")
                        byte_count = int(val.lstrip("+"))
                    except ValueError:
                        return CommandResult(
                            1, stderr=[f"head: invalid byte count '{val}'"]
                        )
                else:
                    return CommandResult(1, stderr=[f"head: unknown argument '{arg}'"])
            else:
                files.append(arg)
        if not len(files):
            files = ["-"]
        if from_start and (
            (line_count is not None and line_count < 1)
            or (byte_count is not None and byte_count < 1)
        ):
            return CommandResult(
                1, stderr=["head: starting position must be greater than zero"]
            )
        for file in files:
            if file == "-":
                content = ctx.stdin
            else:
                node = ctx.system.fs.resolve(file)
                if isinstance(node, str):
                    stderr.append(f"head: {file}: {node}")
                    status = 1
                    continue
                if node.get_type() == NodeType.DIRECTORY:
                    stderr.append(f"head: {file} is a directory")
                    status = 1
                    continue
                content = InputBuffer.from_file(node)
            if len(files) > 1:
                stdout.append(f"==> {file} <==")
            text = _input_text(content)
            if byte_count is not None:
                encoded = text.encode("utf-8")
                if from_start:
                    selected = encoded[max(byte_count - 1, 0):]
                elif byte_count >= 0:
                    selected = encoded[:byte_count]
                else:
                    selected = encoded[:byte_count]
                stdout.extend(
                    _output_lines(selected.decode("utf-8", errors="replace"))
                )
            elif line_count is not None:
                data = content.lines
                if from_start:
                    selected_lines = data[max(line_count - 1, 0):]
                elif line_count < 0:
                    selected_lines = data[:line_count]
                else:
                    selected_lines = data[:line_count]
                stdout.extend(selected_lines)
            else:
                stdout.extend(content.lines[:10])
        return CommandResult(status, stdout, stderr)

    def tail(self, ctx: CommandContext) -> CommandResult:
        if "--help" in ctx.args:
            return CommandResult(0, stdout=self.useage("tail"))
        stdout = []
        stderr = []
        status = 0
        line_count: int | None = None
        byte_count: int | None = None
        from_start = False
        outputType = 0
        while ctx.args and ctx.args[0].startswith("-") and ctx.args[0] != "-":
            arg = ctx.args.pop(0)
            if arg in ("-c", "--bytes") or arg.startswith("--bytes="):
                if arg in ("-c", "--bytes"):
                    if not len(ctx.args):
                        return CommandResult(
                            1, stderr=["tail: argument required for -c"]
                        )
                    num = ctx.args.pop(0)
                else:
                    num = arg.split("=")[1]
                try:
                    if num.startswith("++"):
                        raise ValueError
                    from_start = num.startswith("+")
                    byte_count = int(num.lstrip("+"))
                except ValueError:
                    return CommandResult(
                        1,
                        stderr=[
                            "tail: argument for -c must be an integar "
                            "with a possible + prefix"
                        ],
                    )

            elif arg in ("-n", "--lines") or arg.startswith("--lines="):
                if arg in ("-n", "--lines"):
                    if not len(ctx.args):
                        return CommandResult(
                            1, stderr=["tail: argument required for -n"]
                        )
                    num = ctx.args.pop(0)
                else:
                    num = arg.split("=")[1]
                try:
                    if num.startswith("++"):
                        raise ValueError
                    from_start = num.startswith("+")
                    line_count = int(num.lstrip("+"))
                except ValueError:
                    return CommandResult(
                        1,
                        stderr=[
                            "tail: argument for -c must be "
                            "an integar with a possible + prefix"
                        ],
                    )

            elif arg == "-q" or arg == "--quiet" or arg == "--silent":
                outputType = -1
            elif arg == "-v" or arg == "--verbose":
                outputType = 1
            elif arg[1:].isdigit():
                line_count = int(arg[1:])
            else:
                return CommandResult(1, stderr=[f"tail: unknown argument given {arg}"])

        if from_start and (
            (line_count is not None and line_count < 1)
            or (byte_count is not None and byte_count < 1)
        ):
            return CommandResult(
                1, stderr=["tail: starting position must be greater than zero"]
            )
        if not from_start and (
            (line_count is not None and line_count < 0)
            or (byte_count is not None and byte_count < 0)
        ):
            return CommandResult(1, stderr=["tail: count must not be negative"])

        files = ctx.args
        if len(files) == 0:
            files = ["-"]
        for file in files:
            # Create header if needed
            if (len(files) > 1 and outputType != -1) or (
                len(files) == 1 and outputType == 1
            ):
                stdout.append(f"==> {file} <==")

            if file == "-":
                content = ctx.stdin
            else:
                node = ctx.system.fs.resolve(file)
                if isinstance(node, str):
                    status = 1
                    stderr.append(f"tail: {file} can not be found")
                    continue

                if node.get_type() == NodeType.DIRECTORY:
                    status = 1
                    stderr.append(f"tail: {file} is a directory")
                    continue
                content = InputBuffer.from_file(node)

            text = _input_text(content)
            if byte_count is not None:
                encoded = text.encode("utf-8")
                if from_start:
                    selected = encoded[max(byte_count - 1, 0):]
                elif byte_count == 0:
                    selected = b""
                else:
                    selected = encoded[-byte_count:]
                stdout.extend(
                    _output_lines(selected.decode("utf-8", errors="replace"))
                )
            else:
                data = content.lines
                count = 10 if line_count is None else line_count
                if from_start:
                    stdout.extend(data[max(count - 1, 0):])
                else:
                    stdout.extend(data[-count:] if count > 0 else [])
        return CommandResult(status, stdout, stderr)

    def rm(self, ctx: CommandContext) -> CommandResult:
        recurse, verbose, interactive, force = False, False, False, False
        stdout = []
        stderr = []
        if "--help" in ctx.args:
            return CommandResult(0, stdout=self.useage("rm"))

        while len(ctx.args) and ctx.args[0].startswith("-"):
            arg = ctx.args.pop(0)
            if arg in ("--recursive", "--interactive", "--verbose", "--force"):
                recurse = recurse or arg == "--recursive"
                interactive = interactive or arg == "--interactive"
                verbose = verbose or arg == "--verbose"
                force = force or arg == "--force"
            else:
                for option in arg[1:]:
                    if option in ("r", "R"):
                        recurse = True
                    elif option == "v":
                        verbose = True
                    elif option == "i":
                        interactive = True
                    elif option == "f":
                        force = True
                    else:
                        return CommandResult(
                            1,
                            stderr=[f"rm: invalid option -- '{option}'"],
                        )

        files = ctx.args.copy()
        if not files:
            return CommandResult(1, stderr=["rm: missing operand"])

        targets = []
        if recurse:
            for file in files:
                node = ctx.system.fs.get_file(file)
                if isinstance(node, FileNode):
                    targets.extend(node.expand_targets(file))
                else:
                    targets.append(file)
        else:
            targets = files

        if interactive:
            proc = self.process_manager.create_process(
                f"rm {" ".join(files)}",
                parent=self.process_manager.default_parent_pid,
            )
            proc.program = RmProgram(
                proc,
                targets,
                ctx.system,
                recursive=recurse,
            )
            stdout, stderr = proc.program.start()

            if proc.status == ProcessState.TERMINATED:
                ctx.system.shell.foreground_pid = None
                return CommandResult(
                    status=1 if stderr else 0,
                    stdout=stdout,
                    stderr=stderr,
                )

            ctx.system.shell.foreground_pid = proc.pid
            return CommandResult(
                status=0,
                stdout=stdout,
                stderr=stderr,
                interaction=Interaction(
                    mode="foreground",
                    prompt=proc.program.prompt,
                ),
            )

        for filename in targets:
            result = ctx.system.fs.delete(filename, recursive=recurse)
            if isinstance(result, str):
                if force and isinstance(ctx.system.fs.resolve(filename), str):
                    continue
                stderr.append(f"rm: {result}")
            elif verbose:
                stdout.append(f"removed '{filename}'")
        return CommandResult(1 if stderr else 0, stdout, stderr)

    def pwd(self, ctx: CommandContext) -> CommandResult:
        if ctx.args == ["--help"]:
            return CommandResult(0, stdout=self.useage("pwd"))
        if ctx.args:
            return CommandResult(1, stderr=[f"pwd: unexpected operand '{ctx.args[0]}'"])
        return CommandResult(
            0, stdout=[ctx.system.fs.display_path(ctx.system.fs.current)]
        )

    def mkdir(self, ctx: CommandContext) -> CommandResult:
        perms = {
            "user": {"r": True, "w": True, "x": True},
            "group": {"r": True, "w": False, "x": True},
            "public": {"r": True, "w": False, "x": True},
        }
        verbose, parent = False, False
        if not len(ctx.args):
            return CommandResult(
                1, stderr=["mkdir: at least one argument should be given"]
            )
        names: list[str] = []
        while len(ctx.args):
            arg: str = ctx.args.pop(0)
            if arg.startswith("-"):
                if arg == "-m" or arg == "--mode" or arg.startswith("--mode="):
                    if arg in ["-m", "--mode"]:
                        if not len(ctx.args):
                            return CommandResult(
                                1, stderr=[f"mkdir: parameter required for {arg}"]
                            )
                        arg = ctx.args.pop(0)
                    else:

                        arg = arg.split("=", 1)[1]
                    perms = determine_perms_fromstr(arg)
                    if isinstance(perms, str):
                        return CommandResult(1, stderr=[perms])
                elif arg == "-v" or arg == "--verbose":
                    verbose = True
                elif arg == "-p" or arg == "--parents":
                    parent = True
                elif arg == "-h" or arg == "--help":
                    return CommandResult(0, stdout=self.useage("mkdir"))
                else:
                    return CommandResult(1, stderr=["mkdir: unknown argument given"])
            else:
                names.append(arg)
        if len(names) == 0:
            return CommandResult(1, stderr=["mkdir: no name given for new directory"])
        saved_current = ctx.system.fs.current
        stdout = []
        stderr = []
        status = 0
        for name in names:
            existing = ctx.system.fs.resolve(name)
            if isinstance(existing, FileNode):
                if parent and existing.get_type() == NodeType.DIRECTORY:
                    continue
                stderr.append(f"mkdir: Filename '{name}' already exists")
                status = 1
                continue
            err = ctx.system.fs.add_directory(name, parent, perms)
            ctx.system.fs.current = saved_current
            if err:
                stderr.append(f"mkdir: {err}")
                status = 1
            if verbose and not err:
                stdout.append(f"mkdir: sucessfully created {name}")
        return CommandResult(status, stdout, stderr)

    def ls(self, ctx: CommandContext) -> CommandResult:
        deep, detail = False, 0
        extra: dict[str, bool | str] = {}
        target = ""
        stdout = []
        stderr = []
        while ctx.args:
            arg = ctx.args[0]
            if not arg:
                return CommandResult(1, stderr=["ls: empty path"])
            if arg.startswith("-"):
                if arg == "--help":
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
                            return CommandResult(
                                2, stderr=["ls: unknown argument given"]
                            )
            else:
                target = arg
            ctx.args = ctx.args[1:]
        saved_current = ctx.system.fs.current
        lines = ctx.system.fs.list_files(target, -1 if deep else 0, detail, extra)
        ctx.system.fs.current = saved_current
        if isinstance(lines, str):
            return CommandResult(1, stderr=[f"ls: {target}: {lines}"])
        for line in lines:
            stdout.append(" ".join(line))
        return CommandResult(0, stdout, stderr)

    def cd(self, ctx: CommandContext) -> CommandResult:
        if not ctx.args:
            return CommandResult(1, stderr=["cd: must give argument"])
        arg = ctx.args[0]
        target = ctx.system.fs.resolve(arg)
        if isinstance(target, str):
            return CommandResult(1, stderr=["cd:" + str(target)])
        if target.get_type() != NodeType.DIRECTORY:
            return CommandResult(1, stderr=[f"cd: {target.name} is not a directory"])
        ctx.system.fs.current = target
        cwd = ctx.system.fs.display_path(target)
        ctx.system.shell.cwd = cwd
        ctx.system.fs.cwd = cwd
        return CommandResult(0)

    def ln(self, ctx: CommandContext) -> CommandResult:
        linkty = "hard"
        if len(ctx.args) == 1 and ctx.args[0] == "--help":
            return CommandResult(0, stdout=self.useage("ln"))
        if len(ctx.args) < 2:
            return CommandResult(2, stderr=["Invalid number of arguments"])
        while len(ctx.args) > 2:
            arg = ctx.args.pop(0)
            if arg.startswith("-"):
                options = arg[1:]
                for option in options:
                    match option:
                        case "s":
                            linkty = "sym"
                        case _:
                            return CommandResult(2, stderr=["Unknown Argument Given"])
        target = ctx.args[0]
        destination = ctx.args[1]
        target_inode = None
        if linkty == "hard":
            source = ctx.system.fs.resolve(target)
            if isinstance(source, str):
                return CommandResult(1, stderr=[source])
            if source.get_type() == NodeType.DIRECTORY:
                return CommandResult(1, stderr=["Cannot hard link directory"])
            target_inode = source.inode

        resolved_destination = ctx.system.fs.resolve_parent(destination)
        if isinstance(resolved_destination, str):
            return CommandResult(1, stderr=[f"ln: {resolved_destination}"])
        parent, name = resolved_destination
        if parent.access(name) is not None:
            return CommandResult(1, stderr=[f"ln: {destination}: File exists"])

        if linkty == "hard":
            inode = target_inode
        else:
            inode = Inode(NodeType.SYMLINK)
            inode.symlink_target = target

        if error := parent.add_child(name, inode):
            return CommandResult(1, stderr=[f"ln: {error}"])
        if linkty == "hard":
            inode.link_count += 1
        return CommandResult()

    def uniq(self, ctx: CommandContext) -> CommandResult:
        count = False
        duplicates_only = False
        unique_only = False
        ignore_case = False
        skip_fields = 0
        skip_chars = 0
        input_file: str | None = None
        args = list(ctx.args)
        index = 0

        def parse_count(value: str, label: str) -> int | CommandResult:
            try:
                parsed = int(value)
            except ValueError:
                return CommandResult(1, stderr=[f"uniq: invalid {label} '{value}'"])
            if parsed < 0:
                return CommandResult(
                    1, stderr=[f"uniq: {label} must be non-negative"]
                )
            return parsed

        while index < len(args):
            arg = args[index]
            index += 1
            if arg == "--":
                if index < len(args):
                    if input_file is not None or len(args) - index > 1:
                        return CommandResult(
                            1, stderr=["uniq: expected at most one input file"]
                        )
                    input_file = args[index]
                break
            if arg == "--help":
                return CommandResult(0, stdout=self.useage("uniq"))

            long_name, separator, long_value = arg.partition("=")
            if arg == "-":
                if input_file is not None:
                    return CommandResult(
                        1, stderr=["uniq: expected at most one input file"]
                    )
                input_file = arg
                continue
            if arg.startswith("--"):
                if long_name in ("--count", "--repeated", "--unique", "--ignore-case"):
                    if separator:
                        return CommandResult(1, stderr=[f"uniq: unexpected value for {long_name}"])
                    if long_name == "--count":
                        count = True
                    elif long_name == "--repeated":
                        duplicates_only = True
                    elif long_name == "--unique":
                        unique_only = True
                    else:
                        ignore_case = True
                    continue
                if long_name in ("--skip-fields", "--skip-chars"):
                    if separator:
                        value = long_value
                    elif index < len(args):
                        value = args[index]
                        index += 1
                    else:
                        return CommandResult(1, stderr=[f"uniq: value required for {long_name}"])
                    label = "field count" if long_name == "--skip-fields" else "character count"
                    parsed = parse_count(value, label)
                    if isinstance(parsed, CommandResult):
                        return parsed
                    if long_name == "--skip-fields":
                        skip_fields = parsed
                    else:
                        skip_chars = parsed
                    continue
                return CommandResult(1, stderr=[f"uniq: unsupported option '{arg}'"])

            if arg.startswith("-"):
                options = arg[1:]
                option_index = 0
                while option_index < len(options):
                    option = options[option_index]
                    option_index += 1
                    if option == "i":
                        ignore_case = True
                    elif option == "c":
                        count = True
                    elif option == "d":
                        duplicates_only = True
                    elif option == "u":
                        unique_only = True
                    elif option in ("f", "s"):
                        if option_index < len(options):
                            value = options[option_index:]
                            option_index = len(options)
                        elif index < len(args):
                            value = args[index]
                            index += 1
                        else:
                            return CommandResult(1, stderr=[f"uniq: argument required for -{option}"])
                        label = "field count" if option == "f" else "character count"
                        parsed = parse_count(value, label)
                        if isinstance(parsed, CommandResult):
                            return parsed
                        if option == "f":
                            skip_fields = parsed
                        else:
                            skip_chars = parsed
                    else:
                        return CommandResult(1, stderr=[f"uniq: unsupported option '-{option}'"])
                continue

            if input_file is not None:
                return CommandResult(1, stderr=["uniq: expected at most one input file"])
            input_file = arg

        if duplicates_only and unique_only:
            return CommandResult(1, stderr=["uniq: -d and -u cannot be used together"])

        if input_file not in (None, "-"):
            node = ctx.system.fs.resolve(input_file)
            if isinstance(node, str):
                return CommandResult(1, stderr=[f"uniq: {input_file}: {node}"])
            if node.get_type() == NodeType.DIRECTORY:
                return CommandResult(1, stderr=[f"uniq: {input_file}: Is a directory"])
            if node.get_type() != NodeType.FILE:
                return CommandResult(1, stderr=[f"uniq: {input_file}: Not a regular file"])
            content = InputBuffer.from_file(node)
        else:
            content = ctx.stdin

        def comparison_key(line: str) -> str:
            offset = 0
            for _ in range(skip_fields):
                while offset < len(line) and line[offset].isspace():
                    offset += 1
                while offset < len(line) and not line[offset].isspace():
                    offset += 1
            while offset < len(line) and line[offset].isspace():
                offset += 1
            key = line[offset:]
            if skip_chars:
                key = key[skip_chars:]
            return key.casefold() if ignore_case else key

        lines = content.lines
        keys = [comparison_key(line) for line in lines]
        output: list[str] = []
        start = 0
        while start < len(lines):
            end = start + 1
            while end < len(lines) and keys[end] == keys[start]:
                end += 1
            group_size = end - start
            if (not duplicates_only or group_size > 1) and (
                not unique_only or group_size == 1
            ):
                line = lines[start]
                output.append(f"{group_size} {line}" if count else line)
            start = end

        return CommandResult(0, stdout=output)

    def sort(self, ctx: CommandContext) -> CommandResult:
        if "--help" in ctx.args:
            return CommandResult(0, stdout=self.useage("sort"))
        files = []
        igblanks = False
        reverse = False
        randomize = False
        check = False
        scheck = False
        fold = False
        clean = False
        remove_dups = False
        output = ""
        while ctx.args:
            arg = ctx.args.pop(0)
            if not arg:
                return CommandResult(2, stderr=["sort: empty path"])
            if arg.startswith("-"):
                if arg == "-":
                    files.append("-")
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
                            if not ctx.args or not ctx.args[0]:
                                return CommandResult(
                                    2, stderr=["sort: argument required for -o"]
                                )
                            output = ctx.args.pop(0)
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
                            return CommandResult(
                                2, stderr=[f"sort: unknown option given ({arg})"]
                            )
            else:
                files.append(arg)
        if not files:
            files = ["-"]
        content = []
        for file in files:
            if file == "-":
                content.extend(ctx.stdin.lines)
                continue
            tmp = ctx.system.fs.resolve(file)
            if isinstance(tmp, str):
                return CommandResult(1, stderr=[f"sort: {file}: {tmp}"])
            if tmp.get_type() == NodeType.DIRECTORY:
                return CommandResult(1, stderr=[f"sort: {file}: Is a directory"])
            if tmp.get_type() != NodeType.FILE:
                return CommandResult(1, stderr=[f"sort: {file}: Not a regular file"])
            content.extend(InputBuffer.from_file(tmp).lines)

        def comparison_key(line: str) -> str:
            key = line.lstrip() if igblanks else line
            if clean:
                key = "".join(character for character in key if character.isprintable())
            if fold:
                key = key.casefold()
            return key

        keys = [comparison_key(line) for line in content]
        indexed = list(enumerate(content))
        modified = [
            line
            for _, line in sorted(
                indexed,
                key=lambda item: (
                    comparison_key(item[1]), -item[0] if reverse else item[0]
                ),
                reverse=reverse,
            )
        ]
        if check or scheck:
            for i in range(1, len(content)):
                out_of_order = (
                    keys[i - 1] > keys[i]
                    if not reverse
                    else keys[i - 1] < keys[i]
                )
                if out_of_order:
                    # Silent check or not
                    if scheck:
                        return CommandResult(1)
                    else:
                        return CommandResult(
                            1, stderr=[f"sort: {files[0]}:{i + 1}: disorder: {content[i]}"]
                        )
            return CommandResult(0)
        if remove_dups:
            unique = []
            previous = object()
            for line in modified:
                key = comparison_key(line)
                if key != previous:
                    unique.append(line)
                    previous = key
            modified = unique
        if randomize:
            r = []
            # while an element hasn't been moved
            while len(modified):
                # Pick a random element in modified
                vid = random.randrange(len(modified))
                # if there is multiple of one element move backwards
                while (
                    vid > 0
                    and comparison_key(modified[vid - 1])
                    == comparison_key(modified[vid])
                ):
                    vid -= 1
                # Get element and append to end of new array
                element = modified.pop(vid)
                r.append(element)
                # Keep removing element which are the saeme
                while (
                    vid < len(modified)
                    and comparison_key(modified[vid]) == comparison_key(element)
                ):
                    r.append(modified.pop(vid))
            modified = r
        if output:
            target = ctx.system.fs.resolve(output)
            if isinstance(target, str):
                destination = ctx.system.fs.resolve_parent(output)
                if isinstance(destination, str):
                    return CommandResult(1, stderr=[f"sort: {output}: {destination}"])
                parent, name = destination
                error = parent.add_child(name, Inode(NodeType.FILE))
                if error:
                    return CommandResult(1, stderr=[f"sort: {output}: {error}"])
                target = parent.access(name)
            elif target.get_type() == NodeType.DIRECTORY:
                return CommandResult(1, stderr=[f"sort: {output}: Is a directory"])
            elif target.get_type() != NodeType.FILE:
                return CommandResult(1, stderr=[f"sort: {output}: Not a regular file"])
            target.set_data(modified)
            return CommandResult(0)
        return CommandResult(0, stdout=modified)
