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
QUESTION_MODES = {
    "grep": {
        "Case Insensitive": "ignore_case",
        "Find By Filename": "files_with_matches",
        "Match By Line": "line_regexp",
        "Match By Word": "word_regexp",
        "Show Line Number": "line_number",
    },
    "sed": {
        "Save a backup": "backup",
        "Case Insensitive": "ignore_case",
    },
}
GREP_FLAGS = {
    "ignore_case": "i",
    "files_with_matches": "l",
    "line_regexp": "x",
    "word_regexp": "w",
    "line_number": "n",
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
        marker = f"TRACE_{secrets.token_hex(4).upper()}"
        stored_marker = marker.lower() if mode == "ignore_case" else marker
        line = f"{random.choice(LOG_LEVELS)} {stored_marker} {label} event"
        contents = [f"INFO {label} started", line, f"INFO {label} complete"]
        if mode == "word_regexp":
            contents.insert(1, f"INFO before{marker}after decoy")
        self.shell.fs.add_file(path)
        node = self.shell.fs.resolve(path)
        assert isinstance(node, FileNode)
        node.set_data(contents)

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
        question_id = f"{self.round_number}-{index}"
        self.questions.append(
            {
                "id": question_id,
                "command": "grep",
                "mode": mode,
                "prompt": prompts[mode],
            }
        )
        self._answers[question_id] = {
            "command": "grep",
            "inode_id": node.inode.id,
            "pattern": line if mode == "line_regexp" else marker,
            "line": line,
            "required_option": GREP_FLAGS.get(mode),
        }

    def _add_sed_question(self, index: int, mode: str) -> None:
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
        self.questions.append(
            {"id": question_id, "command": "sed", "mode": mode, "prompt": prompts[mode]}
        )
        self._answers[question_id] = {
            "command": "sed",
            "inode_id": node.inode.id,
            "path": path,
            "before": before,
            "after": after,
            "line": after[1],
            "required_option": mode,
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
            if any(
                match.inode_id == answer["inode_id"]
                and match.pattern == answer["pattern"]
                and match.line == answer["line"]
                and (
                    answer["required_option"] is None
                    or answer["required_option"] in match.options
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
