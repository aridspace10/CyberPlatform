"""Parser and executor for the supported sed command subset."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from game.Context import CommandContext
from game.InputBuffer import InputBuffer
from game.inode import Inode, NodeType
from game.commandline import CommandResult


@dataclass(frozen=True)
class Address:
    kind: str
    value: int | str | re.Pattern[str] | None = None


@dataclass(frozen=True)
class SedCommand:
    first: Address | None
    second: Address | None
    negate: bool
    operation: str
    pattern: re.Pattern[str] | None = None
    replacement: str = ""
    global_replace: bool = False
    occurrence: int | None = None
    print_substitution: bool = False
    ignore_case: bool = False


def _read_delimited(script: str, index: int, delimiter: str) -> tuple[str, int]:
    value: list[str] = []
    while index < len(script):
        char = script[index]
        if char == delimiter:
            return "".join(value), index + 1
        if char == "\\" and index + 1 < len(script):
            next_char = script[index + 1]
            if next_char == delimiter:
                value.append(next_char)
            else:
                value.extend((char, next_char))
            index += 2
            continue
        value.append(char)
        index += 1
    raise ValueError("sed: expected terminating delim")


def _parse_address(script: str, index: int) -> tuple[Address, int]:
    if index >= len(script):
        raise ValueError("sed: expected address")
    if script[index] == "$":
        return Address("last"), index + 1
    if script[index] == "/":
        regex, index = _read_delimited(script, index + 1, "/")
        try:
            return Address("regex", re.compile(regex)), index
        except re.error as error:
            raise ValueError(f"sed: invalid expression: {error}") from error
    start = index
    while index < len(script) and script[index].isdigit():
        index += 1
    if start == index:
        tail = script[index:]
        command_end = next((i for i, char in enumerate(tail) if char in "sdp"), len(tail))
        raise ValueError(f"sed: expected int, got {tail[:command_end]}")
    return Address("line", int(script[start:index])), index


def _parse_script(script: str) -> list[SedCommand]:
    commands: list[SedCommand] = []
    index = 0
    while index < len(script):
        while index < len(script) and (script[index].isspace() or script[index] == ";"):
            index += 1
        if index >= len(script):
            break

        first = second = None
        negate = False
        if script[index] not in "sdp":
            first, index = _parse_address(script, index)
            if index < len(script) and script[index] == ",":
                second, index = _parse_address(script, index + 1)
            if index < len(script) and script[index] == "!":
                negate = True
                index += 1
            while index < len(script) and script[index].isspace():
                index += 1

        if index >= len(script) or script[index] not in "sdp":
            raise ValueError("sed: unknown or incomplete expression")
        operation = script[index]
        index += 1

        if operation != "s":
            if index < len(script) and script[index] not in ";\n\r" and not script[index].isspace():
                raise ValueError("sed: unknown expression given")
            commands.append(SedCommand(first, second, negate, operation))
            continue

        if index >= len(script):
            raise ValueError("sed: substution expects s/pattern/replacement/")
        delimiter = script[index]
        index += 1
        try:
            pattern_text, index = _read_delimited(script, index, delimiter)
        except ValueError:
            raise ValueError("sed: substution expects s/pattern/replacement/") from None
        replacement, index = _read_delimited(script, index, delimiter)
        # This game supports global, case-insensitive, print-on-change, and
        # numeric occurrence flags. Parse all script flags before processing
        # inputs so an invalid later expression cannot leave partial edits.
        flags = ""
        occurrence_text = ""
        while index < len(script) and script[index] not in ";\n\r" and not script[index].isspace():
            char = script[index]
            if char.isdigit():
                occurrence_text += char
            elif char in "gIp":
                flags += char
            else:
                raise ValueError(f"sed: unknown expression flag - {char}")
            index += 1
        try:
            pattern = re.compile(pattern_text, re.IGNORECASE if "I" in flags else 0)
        except re.error as error:
            raise ValueError(f"sed: invalid expression: {error}") from error
        commands.append(
            SedCommand(
                first,
                second,
                negate,
                operation,
                pattern,
                replacement,
                "g" in flags,
                int(occurrence_text) if occurrence_text else None,
                "p" in flags,
                "I" in flags,
            )
        )
    if not commands:
        raise ValueError("sed: empty expression")
    return commands


def _matches(address: Address | None, line_number: int, line_count: int, line: str) -> bool:
    if address is None:
        return True
    if address.kind == "line":
        return line_number == address.value
    if address.kind == "last":
        return line_number == line_count
    return bool(address.value.search(line))


def _command_selected(
    command: SedCommand,
    state: dict[int, bool],
    command_index: int,
    line_number: int,
    line_count: int,
    line: str,
) -> bool:
    if command.first is None:
        selected = True
    elif command.second is None:
        selected = _matches(command.first, line_number, line_count, line)
    elif state.get(command_index, False):
        selected = True
        if _matches(command.second, line_number, line_count, line):
            state[command_index] = False
    elif _matches(command.first, line_number, line_count, line):
        selected = True
        if not _matches(command.second, line_number, line_count, line):
            state[command_index] = True
    else:
        selected = False
    return not selected if command.negate else selected


def _apply_commands(
    lines: tuple[str, ...], commands: list[SedCommand], suppress_print: bool
) -> tuple[list[str], list[str], int | None]:
    output: list[str] = []
    edited_lines: list[str] = []
    ranges: dict[int, bool] = {}
    line_count = len(lines)
    last_source_index = None
    for line_number, original in enumerate(lines, 1):
        line = original
        deleted = False
        printed: list[str] = []
        for command_index, command in enumerate(commands):
            if not _command_selected(
                command, ranges, command_index, line_number, line_count, line
            ):
                continue
            if command.operation == "d":
                deleted = True
                break
            if command.operation == "p":
                printed.append(line)
            elif command.operation == "s":
                assert command.pattern is not None
                if command.occurrence is not None:
                    matches = list(command.pattern.finditer(line))
                    end = None if command.global_replace else command.occurrence
                    selected = matches[command.occurrence - 1 : end]
                    if selected:
                        chunks: list[str] = []
                        cursor = 0
                        for match_index, match in enumerate(matches, 1):
                            chunks.append(line[cursor : match.start()])
                            if match_index >= command.occurrence and (
                                command.global_replace or match_index == command.occurrence
                            ):
                                chunks.append(match.expand(command.replacement))
                            else:
                                chunks.append(match.group(0))
                            cursor = match.end()
                        chunks.append(line[cursor:])
                        line = "".join(chunks)
                    changed = bool(selected)
                else:
                    line, count = command.pattern.subn(
                        command.replacement,
                        line,
                        count=0 if command.global_replace else 1,
                    )
                    changed = count > 0
                if changed and command.print_substitution:
                    printed.append(line)
        output.extend(printed)
        if not deleted:
            edited_lines.append(line)
            last_source_index = line_number - 1
            if not suppress_print:
                output.append(line)
    return output, edited_lines, last_source_index


def run_sed(ctx: CommandContext, useage: Callable[[str], list[str]]) -> CommandResult:
    args = list(ctx.args)
    if "--help" in args:
        return CommandResult(0, stdout=useage("sed"))
    if not args:
        return CommandResult(
            2,
            stderr=["sed [OPTION]... {script-only-if-no-other-script} [input-file]..."],
        )

    scripts: list[str] = []
    script_files: list[str] = []
    in_place = False
    backup_suffix = ""
    suppress_print = False
    positional: list[str] = []
    options = True
    while args:
        arg = args.pop(0)
        if options and arg == "--":
            options = False
            continue
        if options and arg in ("-n", "--quiet", "--silent"):
            suppress_print = True
            continue
        if options and arg in ("-e", "--expression"):
            if not args:
                return CommandResult(1, stderr=["sed: argument required for -e"])
            scripts.append(args.pop(0))
            continue
        if options and arg.startswith("--expression="):
            scripts.append(arg.split("=", 1)[1])
            continue
        if options and arg in ("-f", "--file"):
            if not args:
                return CommandResult(1, stderr=["sed: argument required for -f"])
            script_files.append(args.pop(0))
            continue
        if options and arg.startswith("--file="):
            script_files.append(arg.split("=", 1)[1])
            continue
        if options and arg.startswith("-i"):
            in_place = True
            suffix = arg[2:]
            backup_suffix = suffix[1:] if suffix.startswith("=") else suffix
            continue
        if options and arg.startswith("-") and arg != "-":
            return CommandResult(1, stderr=[f"sed: unknown option given - {arg[1:]}"])
        positional.append(arg)

    if not scripts and not script_files:
        if not positional:
            return CommandResult(2, stderr=["sed: empty expression"])
        scripts.append(positional.pop(0))
    input_files = positional or ["-"]

    for filename in script_files:
        source = ctx.system.fs.resolve(filename)
        if isinstance(source, str):
            return CommandResult(1, stderr=[f"sed: {source}"])
        if source.get_type() != NodeType.FILE:
            return CommandResult(1, stderr=[f"sed: {filename}: Not a regular file"])
        content = ctx.system.fs.read_node(source)
        if isinstance(content, str):
            return CommandResult(1, stderr=[f"sed: {filename}: {content}"])
        scripts.extend(content.lines)
    try:
        commands = [command for script in scripts for command in _parse_script(script)]
    except ValueError as error:
        return CommandResult(1, stderr=[str(error)])
    except re.error as error:
        return CommandResult(1, stderr=[f"sed: invalid expression: {error}"])

    stdout: list[str] = []
    stderr: list[str] = []
    status = 0
    for filename in input_files:
        source = None
        if filename == "-":
            if in_place:
                stderr.append("sed: cannot edit standard input in place")
                status = 1
                continue
            content = ctx.stdin
        else:
            source = ctx.system.fs.resolve(filename)
            if isinstance(source, str):
                stderr.append(f"sed: {source}")
                status = 1
                continue
            if source.get_type() == NodeType.DIRECTORY:
                stderr.append(f"sed: {filename}: Is a directory")
                status = 1
                continue
            if source.get_type() != NodeType.FILE:
                stderr.append(f"sed: {filename}: Not a regular file")
                status = 1
                continue
            content = ctx.system.fs.read_node(source)
            if isinstance(content, str):
                stderr.append(f"sed: {filename}: {content}")
                status = 1
                continue

        output, new, last_source_index = _apply_commands(
            content.lines, commands, suppress_print
        )
        if in_place:
            assert source is not None and source.parent is not None
            if error := ctx.system.fs.permission_error(source, "w"):
                stderr.append(f"sed: {filename}: {error}")
                status = 1
                continue
            if backup_suffix:
                backup_name = source.name + backup_suffix
                if source.parent.access(backup_name) is not None:
                    stderr.append(f"sed: backup file '{backup_name}' already exists")
                    status = 1
                    continue
                backup_inode = Inode(NodeType.FILE)
                backup_inode.set_data(list(content.lines))
                backup_inode.has_trailing_newline = content.has_trailing_newline
                error = ctx.system.fs.create_child(
                    source.parent, backup_name, backup_inode
                )
                if error:
                    stderr.append(f"sed: {error}")
                    status = 1
                    continue
            if error := ctx.system.fs.write_node(source, new):
                stderr.append(f"sed: {filename}: {error}")
                status = 1
                continue
            source.inode.has_trailing_newline = bool(new) and (
                content.has_trailing_newline
                if last_source_index == len(content.lines) - 1
                else True
            )
        else:
            stdout.extend(output)
    return CommandResult(status, stdout, stderr)
