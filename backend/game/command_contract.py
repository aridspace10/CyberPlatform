"""The supported user-facing contract for the shell command registry.

Keep this inventory aligned with ``CommandLine.commands`` and the handlers.
It deliberately describes this shell's subset instead of claiming GNU
compatibility.
"""

COMMAND_CONTRACTS = {
    "ls": ("List directory entries.", "[PATH]", "none", "-R -l -i -a -A -d -h -s -t -c -u -r -S -X --help", "Returns 1 when a path or option fails.", "No color, sorting choices beyond implemented keys, or GNU formatting."),
    "mkdir": ("Create directories.", "DIRECTORY...", "none", "-p/--parents -m/--mode MODE -v/--verbose -h/--help", "Returns 1 when any directory cannot be created.", "Mode is this filesystem's three-digit permission model."),
    "cd": ("Change the shell working directory.", "DIRECTORY", "none", "none", "Returns 1 for a missing or non-directory operand.", "A directory operand is required; HOME and OLDPWD are not implemented."),
    "pwd": ("Print the current shell directory.", "none", "none", "--help", "Returns 1 for any operand.", "No -L/-P flags; the shell prints its current path from the filesystem tree."),
    "rm": ("Remove files or directories.", "FILE...", "none", "-r/-R/--recursive -i/--interactive -v/--verbose -f/--force --help", "Returns 1 if any requested removal fails.", "Interactive deletion prompts; recursive removal is supported. No GNU traversal semantics."),
    "touch": ("Create files or update supported timestamps.", "FILE...", "none", "-a -c/--no-create -d/--date VALUE/--date=VALUE -m -t STAMP --help", "Returns 1 when a file operation fails.", "Only the no-create, access/modification selection, and date forms implemented by this filesystem are supported."),
    "cat": ("Copy files or standard input to output.", "[FILE...]; '-' means stdin", "yes", "-n --help", "Returns 1 if a file cannot be read.", "Squeeze, show-ends, and display-control options are not implemented."),
    "head": ("Print the start of input files.", "[FILE...]; '-' means stdin", "yes", "-n N/--lines=N -c N/--bytes=N --help", "Returns 1 if any input cannot be read.", "Multipliers and GNU header controls are not supported."),
    "tail": ("Print the end of input files.", "[FILE...]; '-' means stdin", "yes", "-n N/--lines=N -c N/--bytes=N -q/--quiet -v/--verbose --help", "Returns 1 if any input cannot be read.", "Follow mode and GNU byte-offset variants are not implemented."),
    "echo": ("Print arguments joined by spaces and one trailing newline.", "[STRING...]", "no", "none", "Always succeeds.", "Backslash escapes are literal; -n does not suppress the newline. --help is literal text."),
    "chmod": ("Change file permissions using an octal mode.", "OCTAL-MODE FILE...", "none", "-R/--recursive -v/--verbose -- --help", "Returns 1 if a target or mode is invalid.", "Symbolic modes are not supported; permission bits are educational metadata only and are not enforced. There is no effective user/group or ownership policy."),
    "cp": ("Copy files and supported directory trees.", "SOURCE... DEST", "none", "-r -R -v --help", "Returns 1 if a copy fails.", "GNU overwrite, metadata, link, backup, and target-directory options are not implemented."),
    "mv": ("Move or rename files and directories.", "SOURCE... DEST", "none", "-v --help", "Returns 1 if a move fails.", "GNU interactive, backup, and no-clobber options are not implemented."),
    "grep": ("Print lines matching a literal pattern.", "PATTERN [FILE...]; '-' means stdin", "yes", "-i -v -n -l -c -w -x -o -r --include=GLOB --exclude-dir=GLOB --help", "Status 0 means a match; status 1 means no match or an input error.", "Matching is literal substring/word/whole-line matching, not regular expressions."),
    "ln": ("Create a hard link, or a symbolic link with -s.", "[-s] TARGET LINK_NAME", "none", "-s --help", "Returns nonzero if the source or destination is invalid.", "Directory-target and GNU backup/force forms are not supported."),
    "uniq": ("Filter adjacent repeated lines.", "[INPUT]; '-' means stdin", "yes", "-d -f N/--skip-fields=N -i -s N --help", "Returns 1 on an input/output error.", "Only adjacent lines are compared; counts, unique-only output, and GNU grouping/output options are unsupported."),
    "sort": ("Sort input lines lexicographically.", "[FILE]; '-' means stdin", "yes", "-b -r -R -o FILE -c -C -f -i -u --help", "Returns 1 if an input cannot be read or check mode finds disorder.", "Numeric, key, field, locale, random-source, and GNU stable-sort options are unsupported."),
    "find": ("Find filesystem entries using the implemented name/type predicates.", "PATH [PREDICATE...]", "none", "-name PATTERN -type TYPE --help", "Returns nonzero for invalid expressions or paths.", "A starting path is normally required; actions, depth controls, and the broader GNU expression language are unsupported."),
    "sed": ("Apply supported substitutions to input lines.", "[-i] SCRIPT [FILE...]; '-' means stdin", "yes", "-e SCRIPT -f FILE -i --help", "Returns nonzero for invalid scripts or file errors.", "Only the implemented substitution form is supported; address and GNU script features are limited."),
    "wc": ("Count lines, words, and characters.", "[FILE...]; '-' means stdin", "yes", "-l -w -m -c --lines --words --chars --bytes --help", "Returns 1 if any input cannot be read.", "No maximum-line-length, locale byte accounting, or GNU formatting options."),
    "ping": ("Validate a host and optional positive interval and packet size values.", "HOST [-i VALUE] [-l VALUE]", "none", "-i VALUE -l VALUE -h/-help/--help", "Returns 1 when arguments are invalid; otherwise returns 0.", "This command does not send network packets or produce probe output; accepted option values are validated but unused."),
    "ps": ("List processes managed by this shell.", "none", "none", "-e/-A -l -C NAME -p PID -q PID --help", "Returns 0 for a valid listing.", "Shows simulated shell processes only; output selection is limited."),
    "sleep": ("Wait for one integer duration.", "INTEGER[ s|m|h|d ]", "none", "--help", "Returns 1 for a missing, fractional, or invalid duration.", "One duration only; decimals and multiple durations are unsupported."),
    "cut": ("Select delimiter-separated fields from lines.", "-f LIST [-d CHAR] [-s] [FILE...]; '-' means stdin", "yes", "-d CHAR -f N[,N...] -s -- --help", "Returns 1 for invalid options or input errors.", "Field numbers are positive comma-separated integers; ranges, character selection, and long/attached options are unsupported."),
}

COMMAND_EXAMPLES = {
    "ls": "ls /",
    "mkdir": "mkdir demo",
    "cd": "cd /",
    "pwd": "pwd",
    "rm": "rm -f missing-file",
    "touch": "touch note.txt",
    "cat": "cat -",
    "head": "head -n 2",
    "tail": "tail -n 2",
    "echo": "echo hello",
    "chmod": "chmod 644 note.txt",
    "cp": "cp note.txt copy.txt",
    "mv": "mv copy.txt moved.txt",
    "grep": "grep hello note.txt",
    "ln": "ln note.txt hardlink",
    "uniq": "uniq",
    "sort": "sort",
    "find": "find / -type f",
    "sed": "sed s/hello/hi/",
    "wc": "wc",
    "ping": "ping gateway",
    "ps": "ps",
    "sleep": "sleep 1",
    "cut": "cut -f 1",
}


def format_command_help(command: str) -> list[str]:
    summary, operands, stdin, options, status, limits = COMMAND_CONTRACTS[command]
    return [
        f"Usage: {command} {operands}\n",
        f"{summary}\n",
        f"Standard input: {stdin}.\n",
        f"Supported options: {options}.\n",
        "Option syntax: grouped short flags and attached values are supported only where explicitly listed.\n",
        "A standalone -- ends option parsing only for commands that list it. Other commands apply their documented operand rules.\n",
        f"Status: {status}\n",
        f"Limitations: {limits}\n",
        f"Example: {COMMAND_EXAMPLES[command]}\n",
    ]
