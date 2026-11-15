"""Create and evaluate registered MiniGames challenges."""

import random

from .challenges.core import Challenge, Observation, OutputGoal
from .challenges.grep import GrepGoal
from .challenges.registry import PACK_TYPES
from .challenges.sed import SedGoal
from .ShellState import CommandRun, GrepMatch, SedChange, ShellState


class ChallengeEngine:
    def __init__(self, shell: ShellState, round_number: int, rng: random.Random):
        self.shell = shell
        self.round_number = round_number
        self.packs = {
            command: pack_type(shell, round_number, rng)
            for command, pack_type in PACK_TYPES.items()
        }
        self.challenges: dict[str, Challenge] = {}
        self.answers: dict[str, dict] = {}
        for pack in self.packs.values():
            pack._answers = self.answers

    def prepare(self, commands: list[str]) -> None:
        for command in commands:
            self.packs[command].prepare()

    def create(self, index: int, command: str, mode: str, variant: str) -> Challenge:
        pack = self.packs[command]
        challenge = pack.build(index, mode, variant)
        self.challenges[challenge.id] = challenge
        return challenge

    def evaluate(self, observation: Observation, completed: set[str]) -> list[str]:
        return [
            challenge.id
            for challenge in self.challenges.values()
            if challenge.id not in completed and challenge.goal.accepts(observation)
        ]

    def evaluate_runs(
        self, runs: list[CommandRun], stdout: list[str], completed: set[str]
    ) -> list[str]:
        return [
            challenge.id
            for challenge in self.challenges.values()
            if challenge.id not in completed
            and isinstance(challenge.goal, OutputGoal)
            and challenge.goal.accepts_runs(runs, stdout)
        ]

    def evaluate_grep(
        self,
        matches: set[GrepMatch],
        stdout: list[str] | None,
        completed: set[str],
    ) -> list[str]:
        return [
            challenge.id
            for challenge in self.challenges.values()
            if challenge.id not in completed
            and isinstance(challenge.goal, GrepGoal)
            and challenge.goal.accepts_matches(matches, stdout)
        ]

    def evaluate_sed(
        self,
        changes: list[SedChange],
        stdout: list[str],
        shell: ShellState,
        completed: set[str],
    ) -> list[str]:
        return [
            challenge.id
            for challenge in self.challenges.values()
            if challenge.id not in completed
            and isinstance(challenge.goal, SedGoal)
            and challenge.goal.accepts_changes(changes, stdout, shell)
        ]
