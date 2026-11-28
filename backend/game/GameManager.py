"""Shared question and round state for terminal minigames."""

import copy
import random
import secrets
import time

from .ChallengeEngine import ChallengeEngine
from .challenges.core import Observation
from .challenges.planner import RoundPlanner
from .challenges.registry import QUESTION_MODES
from .ShellState import CommandRun, GrepMatch, SedChange, ShellState

DEFAULT_QUESTION_COUNT = 10


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
        self._challenge_engine: ChallengeEngine | None = None
        self._planner = RoundPlanner()
        self.seed = 0
        self._completed: dict[str, set[str]] = {}
        self._scores: dict[str, int] = {}
        self.round_number = 0
        self.deadline: float | None = None
        self.finished = False
        self.finish_reason: str | None = None

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
        configured_seed = self.options.get("seed")
        self.seed = (
            secrets.randbits(64) if configured_seed is None else int(configured_seed)
        )
        self._planner = RoundPlanner()
        self.shell = ShellState()
        self.shell.commands = list(self.commands)
        self.shell.allow_pipes = self.allow_pipes
        self.questions = []
        self._answers = {}
        self._challenge_engine = None
        self._completed = {}
        self._scores = {}
        self.round_number = 0
        self.deadline = None
        self.finished = False
        self.finish_reason = None

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
            raise ValueError("A selected command has no MiniGames questions")
        if self.finished or self.round_number >= self.num_rounds:
            raise ValueError("No rounds remain")

        self.round_number += 1
        self.shell = ShellState()
        self.shell.commands = list(self.commands)
        self.shell.allow_pipes = self.allow_pipes
        rng = random.Random(self.seed + self.round_number)
        self._challenge_engine = ChallengeEngine(self.shell, self.round_number, rng)
        self._challenge_engine.prepare(self.commands)
        self.questions = []
        self._answers = self._challenge_engine.answers
        self._completed = {str(player_id): set() for player_id in player_ids}
        for player_id in player_ids:
            self._scores.setdefault(str(player_id), 0)

        plan = self._planner.plan(
            self.commands,
            self.command_config,
            self.question_count,
            QUESTION_MODES,
            self._challenge_engine.packs,
            rng,
        )
        for index, item in enumerate(plan, start=1):
            challenge = self._challenge_engine.create(
                index, item.command, item.mode, item.variant
            )
            self.questions.append(challenge.public_data())

        self.deadline = (
            time.time() + self.time_limit_seconds
            if self.play_type == "Versus"
            else None
        )
        return self.get_shell()

    def _credit(self, player_id: str, question_id: str) -> None:
        self._completed.setdefault(str(player_id), set()).add(question_id)
        self._scores[str(player_id)] = self._scores.get(str(player_id), 0) + 1

    def _credit_evaluated(self, player_id: str, question_ids: list[str]) -> bool:
        for question_id in question_ids:
            self._credit(player_id, question_id)
        return bool(question_ids)

    def record_attempt(
        self, player_id: str, shell: ShellState, stdout: list[str]
    ) -> bool:
        """Evaluate one successful terminal input against active challenges."""
        if not self.questions or self.finished or self.is_expired():
            return False
        completed = self._completed.setdefault(str(player_id), set())
        matched = self._challenge_engine.evaluate(Observation(shell, stdout), completed)
        return self._credit_evaluated(player_id, matched)

    def record_command_runs(
        self, player_id: str, runs: list[CommandRun], stdout: list[str]
    ) -> bool:
        """Compatibility entry point for command-specific gameplay tests."""
        if not self.questions or self.finished or self.is_expired():
            return False
        completed = self._completed.setdefault(str(player_id), set())
        matched = self._challenge_engine.evaluate_runs(runs, stdout, completed)
        return self._credit_evaluated(player_id, matched)

    def record_grep(
        self,
        player_id: str,
        matches: set[GrepMatch],
        stdout: list[str] | None = None,
    ) -> bool:
        if not self.questions or self.finished or self.is_expired():
            return False
        completed = self._completed.setdefault(str(player_id), set())
        matched = self._challenge_engine.evaluate_grep(matches, stdout, completed)
        return self._credit_evaluated(player_id, matched)

    def record_sed(
        self,
        player_id: str,
        changes: list[SedChange],
        stdout: list[str],
        shell: ShellState,
    ) -> bool:
        if not self.questions or self.finished or self.is_expired():
            return False
        completed = self._completed.setdefault(str(player_id), set())
        matched = self._challenge_engine.evaluate_sed(changes, stdout, shell, completed)
        return self._credit_evaluated(player_id, matched)

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
            "finishReason": self.finish_reason,
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
