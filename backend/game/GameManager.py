"""Shared question and round state for terminal minigames."""

import copy
import random
import secrets
import time

from .filenode import FileNode
from .ShellState import GrepMatch, SedChange, ShellState

DEFAULT_QUESTION_COUNT = 10
LOG_WORDS = ("access", "audit", "build", "deploy", "network", "system")
LOG_LEVELS = ("INFO", "WARN", "ERROR")
TRACE_ALPHABET = "2345679ACDEF"
QUESTION_MODES = {
    "grep": {
        "Case Insensitive": "ignore_case",
        "Find By Filename": "files_with_matches",
        "Match By Line": "line_regexp",
        "Match By Word": "word_regexp",
        "Show Line Number": "line_number",
        "Invert Match": "invert_match",
        "Count Matches": "count",
        "Only Matching Text": "only_matching",
        "Recursive Search": "recursive",
        "Show Filename": "with_filename",
        "Hide Filename": "no_filename",
        "Explicit Pattern": "regexp",
        "Include Files": "include",
        "Exclude Files": "exclude",
        "Exclude Directories": "exclude_dir",
        "Regular Expression": "regex",
    },
    "sed": {
        "Save a backup": "backup",
        "Case Insensitive": "ignore_case",
        "Replace All": "global",
        "Replace Occurrence": "occurrence",
        "Print Changes": "print_substitution",
        "Quiet Output": "quiet",
        "Expression Option": "expression_option",
        "Script File": "script_file",
        "Edit In Place": "in_place",
        "Line Address": "address_line",
        "Pattern Address": "address_regex",
        "Last Line Address": "address_last",
        "Address Range": "range",
        "Negated Address": "negated_address",
        "Delete Lines": "delete",
        "Print Lines": "print",
        "Multiple Expressions": "multiple_expressions",
        "Alternate Delimiter": "custom_delimiter",
        "Regex Substitution": "regex_substitution",
    },
}
GREP_FLAGS = {
    "ignore_case": "i",
    "files_with_matches": "l",
    "line_regexp": "x",
    "word_regexp": "w",
    "line_number": "n",
    "invert_match": "v",
    "count": "c",
    "only_matching": "o",
    "recursive": "r",
    "with_filename": "H",
    "no_filename": "h",
    "regexp": "e",
    "include": "include=*.log",
    "exclude": "exclude=*.tmp",
    "exclude_dir": "exclude-dir=archive-*",
}


class GameManager:
    def __init__(self):
        self.init_config: dict = {}
        self.gen_config: dict = {}
        self.session_name = ""
        self.play_type = "SinglePlayer"
        self.game_type = ""
        self.creator_id: int | None = None
        self.command_config: dict[str, dict] = {}
        self.commands: list[str] = []
        self.options: dict = {}
        self.allow_pipes = False
        self.num_rounds = 0
        self.question_count = DEFAULT_QUESTION_COUNT
        self.time_limit_seconds = 300
        self.shell = ShellState()
        self.questions: list[dict] = []
        self._answers: dict[str, dict] = {}
        self._completed: dict[str, set[str]] = {}
        self._scores: dict[str, int] = {}
        self.round_number = 0
        self.deadline: float | None = None
        self.finished = False

    def set_config(self, config: dict) -> None:
        self.init_config = copy.deepcopy(config)
        self.gen_config = copy.deepcopy(config)
        self.session_name = config.get("name", "")
        self.play_type = config.get("playType", "SinglePlayer")
        self.game_type = config.get("gameType", config.get("name", ""))
        self.creator_id = config.get("creatorID")
        self.command_config = copy.deepcopy(config.get("commands", {}))
        self.commands = [
            name
            for name, state in self.command_config.items()
            if state.get("selected", False)
        ]
        self.options = copy.deepcopy(config.get("options", {}))
        self.allow_pipes = bool(self.options.get("allowPipes", False))
        self.num_rounds = int(self.options.get("rounds", 0))
        self.question_count = int(
            self.options.get("questionCount", DEFAULT_QUESTION_COUNT)
        )
        self.time_limit_seconds = int(self.options.get("timeLimitSeconds", 300))
        self.shell = ShellState()
        self.shell.commands = list(self.commands)
        self.shell.allow_pipes = self.allow_pipes
        self.questions = []
        self._answers = {}
        self._completed = {}
        self._scores = {}
        self.round_number = 0
        self.deadline = None
        self.finished = False

    def get_shell(self) -> dict:
        return {
            "vars": copy.deepcopy(self.shell.vars),
            "cmds": list(self.shell.commands),
            "fs": self.shell.fs.to_dict(),
            "allowPipes": self.allow_pipes,
        }

    def start_round(self, player_ids: list[str]) -> dict:
        """Generate the configured mix of tasks for every player."""
        if self.game_type != "MiniGames" or not self.commands:
            raise ValueError("Select a command to play MiniGames")
        if any(command not in QUESTION_MODES for command in self.commands):
            raise ValueError("Only grep and sed questions are available")
        if self.finished or self.round_number >= self.num_rounds:
            raise ValueError("No rounds remain")

        self.round_number += 1
        self.shell = ShellState()
        self.shell.commands = list(self.commands)
        self.shell.allow_pipes = self.allow_pipes
        if "grep" in self.commands:
            self.shell.fs.add_directory("logs")
        if "sed" in self.commands:
            self.shell.fs.add_directory("data")
        self.questions = []
        self._answers = {}
        self._completed = {str(player_id): set() for player_id in player_ids}
        for player_id in player_ids:
            self._scores.setdefault(str(player_id), 0)

        commands = [
            self.commands[index % len(self.commands)]
            for index in range(self.question_count)
        ]
        random.shuffle(commands)
        mode_queues: dict[str, list[str]] = {}
        for command in self.commands:
            selected = [
                QUESTION_MODES[command][option]
                for option in self.command_config[command].get("options", [])
                if option in QUESTION_MODES[command]
            ]
            modes = selected + (
                ["basic"] if commands.count(command) > len(selected) else []
            )
            random.shuffle(modes)
            mode_queues[command] = [
                modes[index % len(modes)] for index in range(commands.count(command))
            ]

        for index, command in enumerate(commands, start=1):
            mode = mode_queues[command].pop(0)
            if command == "grep":
                self._add_grep_question(index, mode)
            else:
                self._add_sed_question(index, mode)

        self.deadline = (
            time.time() + self.time_limit_seconds
            if self.play_type == "Versus"
            else None
        )
        return self.get_shell()

    def _add_grep_question(self, index: int, mode: str) -> None:
        label = random.choice(LOG_WORDS)
        path = f"/logs/{label}-{index:02d}-{secrets.token_hex(2)}.log"
        marker = "TRACE_" + "".join(secrets.choice(TRACE_ALPHABET) for _ in range(8))
        stored_marker = marker.lower() if mode == "ignore_case" else marker
        line = f"{random.choice(LOG_LEVELS)} {stored_marker} {label} event"
        contents = [f"INFO {label} started", line, f"INFO {label} complete"]
        if mode == "word_regexp":
            contents.insert(1, f"INFO before{marker}after decoy")
        if mode == "invert_match":
            contents = [f"INFO {marker} rejected", f"INFO {label} accepted"]
            line = contents[1]
        if mode == "only_matching":
            contents[1] = f"INFO prefix-{marker}-suffix {label} event"
            line = contents[1]
        if mode == "regex":
            contents[1] = f"INFO {marker} {label} event"
            line = contents[1]
        if mode == "recursive":
            directory = f"/logs/active-{index:02d}"
            self.shell.fs.add_directory(directory)
            path = f"{directory}/{label}-{secrets.token_hex(2)}.log"
        self.shell.fs.add_file(path)
        node = self.shell.fs.resolve(path)
        assert isinstance(node, FileNode)
        node.set_data(contents)

        if mode in {"include", "exclude", "exclude_dir"}:
            if mode == "exclude_dir":
                decoy_dir = f"/logs/archive-{index:02d}"
                self.shell.fs.add_directory(decoy_dir)
                decoy = f"{decoy_dir}/decoy.log"
            else:
                decoy = f"/logs/decoy-{index:02d}-{secrets.token_hex(2)}.tmp"
            self.shell.fs.add_file(decoy)
            self.shell.fs.resolve(decoy).set_data([f"WARN {marker} decoy"])
        if mode == "no_filename":
            decoy = f"/logs/other-{index:02d}-{secrets.token_hex(2)}.log"
            self.shell.fs.add_file(decoy)
            self.shell.fs.resolve(decoy).set_data(["INFO unrelated event"])

        prompts = {
            "basic": f"Use grep to print the line containing {marker} from {path}",
            "ignore_case": f"Use grep -i to find {marker} regardless of case in {path}",
            "files_with_matches": (
                f"Use grep -rl to print the filename containing {marker} under /logs"
            ),
            "line_regexp": f'Use grep -x to print exactly "{line}" from {path}',
            "word_regexp": f"Use grep -w to find {marker} as a whole word in {path}",
            "line_number": (
                f"Use grep -n to print {marker} with its line number from {path}"
            ),
        }
        examples = {
            "basic": f"grep {marker} {path}",
            "ignore_case": f"grep -i {marker} {path}",
            "files_with_matches": f"grep -rl {marker} /logs",
            "line_regexp": f'grep -x "{line}" {path}',
            "word_regexp": f"grep -w {marker} {path}",
            "line_number": f"grep -n {marker} {path}",
            "invert_match": f"grep -v {marker} {path}",
            "count": f"grep -c {marker} {path}",
            "only_matching": f"grep -o {marker} {path}",
            "recursive": f"grep -rH {marker} /logs",
            "with_filename": f"grep -H {marker} {path}",
            "no_filename": (
                f"grep -h {marker} {path} {decoy}" if mode == "no_filename" else ""
            ),
            "regexp": f"grep -e {marker} {path}",
            "include": f"grep -rH --include='*.log' {marker} /logs",
            "exclude": f"grep -rH --exclude='*.tmp' {marker} /logs",
            "exclude_dir": f"grep -rH --exclude-dir='archive-*' {marker} /logs",
            "regex": f"grep 'TRACE_[A-F0-9]{{8}}' {path}",
        }
        if mode not in prompts:
            descriptions = {
                "invert_match": "print lines that do not contain",
                "count": "count lines containing",
                "only_matching": "print only the matching text",
                "recursive": "search recursively under /logs for",
                "with_filename": "print the matching line with its filename for",
                "no_filename": "print the matching line without a filename for",
                "regexp": "supply the pattern with -e to find",
                "include": "search /logs while including only *.log files for",
                "exclude": "search /logs while excluding *.tmp files for",
                "exclude_dir": "search /logs while excluding archive-* directories for",
                "regex": "use a regular expression to find a TRACE marker in",
            }
            prompts[mode] = f"Use grep to {descriptions[mode]} {marker} in {path}"
        pattern = "TRACE_[A-F0-9]{8}" if mode == "regex" else marker
        if mode == "line_regexp":
            pattern = line
        expected_stdout = None
        if mode in {
            "invert_match", "count", "only_matching", "recursive",
            "with_filename", "no_filename", "regexp", "include",
            "exclude", "exclude_dir", "regex",
        }:
            output = {
                "invert_match": line,
                "count": "1",
                "only_matching": marker,
                "recursive": f"{path}:{line}",
                "with_filename": f"{path}:{line}",
                "no_filename": line,
                "regexp": line,
                "include": f"{path}:{line}",
                "exclude": f"{path}:{line}",
                "exclude_dir": f"{path}:{line}",
                "regex": line,
            }[mode]
            expected_stdout = [output]
        question_id = f"{self.round_number}-{index}"
        self.questions.append(
            {
                "id": question_id,
                "command": "grep",
                "mode": mode,
                "prompt": prompts[mode],
                "example": examples[mode],
            }
        )
        self._answers[question_id] = {
            "command": "grep",
            "inode_id": node.inode.id,
            "pattern": pattern,
            "line": line,
            "required_option": GREP_FLAGS.get(mode),
            "expected_stdout": expected_stdout,
        }

    def _add_sed_question(self, index: int, mode: str) -> None:
        if mode not in {"basic", "backup", "ignore_case"}:
            self._add_extended_sed_question(index, mode)
            return
        label = random.choice(LOG_WORDS)
        path = f"/data/{label}-{index:02d}-{secrets.token_hex(2)}.txt"
        source = f"old{secrets.token_hex(3)}"
        replacement = f"new{secrets.token_hex(3)}"
        stored_source = source.upper() if mode == "ignore_case" else source
        before = (f"INFO {label} started", f"{stored_source} {label} event")
        after = (before[0], f"{replacement} {label} event")
        self.shell.fs.add_file(path)
        node = self.shell.fs.resolve(path)
        assert isinstance(node, FileNode)
        node.set_data(list(before))

        prompts = {
            "basic": (
                f"Use sed to replace {source} with {replacement} in {path} "
                "and print the changed line"
            ),
            "ignore_case": (
                f"Use sed's I flag to replace {source} with {replacement} "
                f"regardless of case in {path} and print the changed line"
            ),
            "backup": (
                f"Use sed -i.bak to replace {source} with {replacement} "
                f"in {path} and keep a backup"
            ),
        }
        question_id = f"{self.round_number}-{index}"
        flag = "I" if mode == "ignore_case" else ""
        example = (
            f"sed -i.bak 's/{source}/{replacement}/' {path}"
            if mode == "backup"
            else f"sed 's/{source}/{replacement}/{flag}' {path}"
        )
        self.questions.append({
            "id": question_id, "command": "sed", "mode": mode,
            "prompt": prompts[mode], "example": example,
        })
        self._answers[question_id] = {
            "command": "sed",
            "inode_id": node.inode.id,
            "path": path,
            "before": before,
            "after": after,
            "line": after[1],
            "required_option": mode,
        }

    def _add_extended_sed_question(self, index: int, mode: str) -> None:
        label = random.choice(LOG_WORDS)
        path = f"/data/{label}-{index:02d}-{secrets.token_hex(2)}.txt"
        source = f"old{secrets.token_hex(3)}"
        replacement = f"new{secrets.token_hex(3)}"
        before = (f"INFO {label} started", f"{source} {label} event")
        after = (before[0], f"{replacement} {label} event")
        script = f"s/{source}/{replacement}/"
        prefix = ""
        script_file = None
        if mode == "global":
            before = (f"{source} {source} event",)
            after = (f"{replacement} {replacement} event",)
            script += "g"
        elif mode == "occurrence":
            before = (f"{source} {source} {source} event",)
            after = (f"{source} {replacement} {source} event",)
            script += "2"
        elif mode == "print_substitution":
            prefix = "-n "
            script += "p"
        elif mode == "quiet":
            prefix = "-n "
            script = "2p"
            after = before
        elif mode == "expression_option":
            prefix = "-e "
        elif mode == "script_file":
            script_file = f"/data/script-{index:02d}-{secrets.token_hex(2)}.sed"
            self.shell.fs.add_file(script_file)
            self.shell.fs.resolve(script_file).set_data([script])
        elif mode == "in_place":
            prefix = "-i "
        elif mode == "address_line":
            before = (f"{source} decoy", f"{source} target")
            after = (before[0], f"{replacement} target")
            script = "2" + script
        elif mode == "address_regex":
            before = (f"{source} decoy", f"TARGET {source}")
            after = (before[0], f"TARGET {replacement}")
            script = "/TARGET/" + script
        elif mode == "address_last":
            before = (f"{source} first", f"{source} last")
            after = (before[0], f"{replacement} last")
            script = "$" + script
        elif mode == "range":
            before = (f"{source} first", f"{source} second", f"{source} third")
            after = (before[0], f"{replacement} second", f"{replacement} third")
            script = "2,3" + script
        elif mode == "negated_address":
            before = (f"{source} first", f"{source} second")
            after = (before[0], f"{replacement} second")
            script = "1!" + script
        elif mode == "delete":
            before = ("keep first", f"remove {source}", "keep last")
            after = (before[0], before[2])
            script = "2d"
        elif mode == "print":
            script = "2p"
            after = before
        elif mode == "multiple_expressions":
            final = f"done{secrets.token_hex(3)}"
            after = (before[0], f"{final} {label} event")
            prefix = f"-e '{script}' -e "
            script = f"s/{replacement}/{final}/"
        elif mode == "custom_delimiter":
            script = f"s|{source}|{replacement}|"
        elif mode == "regex_substitution":
            before = (f"old42 {label} event",)
            after = (f"{replacement} {label} event",)
            script = f"s/old[0-9]+/{replacement}/"

        self.shell.fs.add_file(path)
        node = self.shell.fs.resolve(path)
        assert isinstance(node, FileNode)
        node.set_data(list(before))
        example = (
            f"sed -f {script_file} {path}" if script_file else
            f"sed {prefix}'{script}' {path}"
        )
        expected_stdout = list(after)
        if mode in {"quiet", "print_substitution"}:
            expected_stdout = [after[1]]
        elif mode == "print":
            expected_stdout = [before[0], before[1], before[1]]
        elif mode == "in_place":
            expected_stdout = []
        target = (
            f"File should contain: {'; '.join(after)}"
            if mode == "in_place" else
            f"Expected output: {'; '.join(expected_stdout)}"
        )
        question_id = f"{self.round_number}-{index}"
        self.questions.append({
            "id": question_id, "command": "sed", "mode": mode,
            "prompt": f"Use sed's {mode.replace('_', ' ')} feature on {path}. {target}",
            "example": example,
        })
        self._answers[question_id] = {
            "command": "sed", "inode_id": node.inode.id, "path": path,
            "before": before, "after": after, "line": after[-1],
            "required_option": mode, "required_features": {mode},
            "expected_stdout": expected_stdout,
            "in_place": mode == "in_place",
        }

    def _credit(self, player_id: str, question_id: str) -> None:
        self._completed.setdefault(str(player_id), set()).add(question_id)
        self._scores[str(player_id)] = self._scores.get(str(player_id), 0) + 1

    def record_grep(
        self,
        player_id: str,
        matches: set[GrepMatch],
        stdout: list[str] | None = None,
    ) -> bool:
        """Credit a grep task when the requested search result was printed."""
        if not self.questions or self.finished or self.is_expired():
            return False
        completed = self._completed.setdefault(str(player_id), set())
        changed = False
        for question_id, answer in self._answers.items():
            if answer["command"] != "grep" or question_id in completed:
                continue
            if (answer.get("expected_stdout") is not None
                    and stdout != answer["expected_stdout"]):
                continue
            if any(
                match.inode_id == answer["inode_id"]
                and match.pattern == answer["pattern"]
                and match.line == answer["line"]
                and (
                    answer["required_option"] is None
                    or answer["required_option"] in match.options
                )
                and (("l" in match.options) == (answer["required_option"] == "l"))
                and all(
                    flag not in match.options or answer["required_option"] == flag
                    for flag in ("c", "o", "v")
                )
                and (stdout is None or match.output in stdout)
                for match in matches
            ):
                self._credit(player_id, question_id)
                changed = True
        return changed

    def record_sed(
        self,
        player_id: str,
        changes: list[SedChange],
        stdout: list[str],
        shell: ShellState,
    ) -> bool:
        """Credit a sed task after the expected edit and backup are observed."""
        if not self.questions or self.finished or self.is_expired():
            return False
        completed = self._completed.setdefault(str(player_id), set())
        changed = False
        for question_id, answer in self._answers.items():
            if answer["command"] != "sed" or question_id in completed:
                continue
            for edit in changes:
                if (
                    edit.inode_id != answer["inode_id"]
                    or edit.before != answer["before"]
                    or edit.after != answer["after"]
                ):
                    continue
                mode = answer["required_option"]
                if "required_features" in answer:
                    if not answer["required_features"].issubset(edit.features):
                        continue
                    if edit.in_place != answer["in_place"]:
                        continue
                    if edit.in_place:
                        current = shell.fs.resolve(answer["path"])
                        if (not isinstance(current, FileNode)
                                or tuple(current.get_data()) != answer["after"]):
                            continue
                    if stdout != answer["expected_stdout"]:
                        continue
                    if (edit.output != tuple(answer["expected_stdout"])
                            and not edit.in_place):
                        continue
                    self._credit(player_id, question_id)
                    changed = True
                    break
                if mode == "backup":
                    if not edit.in_place or not edit.backup_suffix:
                        continue
                    backup = shell.fs.resolve(answer["path"] + edit.backup_suffix)
                    if not isinstance(backup, FileNode):
                        continue
                    if tuple(backup.get_data()) != answer["before"]:
                        continue
                elif (
                    edit.in_place
                    or answer["line"] not in edit.output
                    or answer["line"] not in stdout
                    or (mode == "ignore_case" and not edit.ignore_case)
                ):
                    continue
                self._credit(player_id, question_id)
                changed = True
                break
        return changed

    def is_expired(self) -> bool:
        return self.deadline is not None and time.time() >= self.deadline

    def all_finished(self, player_ids: list[str]) -> bool:
        return bool(player_ids) and all(
            len(self._completed.get(str(player_id), set())) == len(self.questions)
            for player_id in player_ids
        )

    def get_game_data(
        self, session_name: str | None = None, player_id: str | None = None
    ) -> dict:
        completed = (
            self._completed.get(str(player_id), set())
            if player_id is not None
            else set()
        )
        questions = [
            {
                **question,
                "status": "completed" if question["id"] in completed else "active",
            }
            for question in self.questions
        ]
        return {
            "sessionName": session_name or self.session_name,
            "gameType": self.game_type,
            "playType": self.play_type,
            "creatorID": self.creator_id,
            "round": self.round_number,
            "rounds": self.num_rounds,
            "deadline": self.deadline,
            "finished": self.finished,
            "questions": questions,
            "progress": {
                "completed": len(completed),
                "total": len(questions) or self.question_count,
            },
            "leaderboard": [
                {"playerID": pid, "completed": score}
                for pid, score in sorted(
                    self._scores.items(), key=lambda item: (-item[1], item[0])
                )
            ],
        }
