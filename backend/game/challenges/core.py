"""Shared challenge data and evaluation context."""

import random
from dataclasses import dataclass
from typing import Callable, Protocol

from ..filenode import FileNode
from ..ShellState import CommandRun, ShellState


@dataclass(frozen=True)
class Observation:
    shell: ShellState
    stdout: list[str]


class Goal(Protocol):
    def accepts(self, observation: Observation) -> bool: ...


@dataclass(frozen=True)
class OutputGoal:
    command: str
    inode_ids: tuple[int, ...]
    expected_stdout: tuple[str, ...]
    solution: str

    def accepts(self, observation: Observation) -> bool:
        return self.accepts_runs(observation.shell.command_runs, observation.stdout)

    def accepts_runs(self, runs: list[CommandRun], stdout: list[str]) -> bool:
        if tuple(stdout) != self.expected_stdout:
            return False
        return any(
            run.command == self.command
            and run.inode_ids == self.inode_ids
            and run.output == self.expected_stdout
            for run in runs
        )


@dataclass(frozen=True)
class FileContentGoal:
    """Require an existing file to have the requested final contents."""

    path: str
    inode_id: int
    expected_lines: tuple[str, ...]

    def accepts(self, observation: Observation) -> bool:
        return self.matches(observation.shell)

    def matches(self, shell: ShellState) -> bool:
        node = shell.fs.resolve(self.path)
        return (
            isinstance(node, FileNode)
            and node.inode.id == self.inode_id
            and tuple(node.get_data()) == self.expected_lines
        )


@dataclass(frozen=True)
class Challenge:
    id: str
    command: str
    mode: str
    variant: str
    prompt: str
    example: str
    goal: Goal

    def public_data(self) -> dict:
        return {
            "id": self.id,
            "command": self.command,
            "mode": self.mode,
            "prompt": self.prompt,
            "example": self.example,
        }


class BasePack:
    command: str
    root: str
    variants: tuple[str, ...]

    def __init__(self, shell: ShellState, round_number: int, rng: random.Random):
        self.shell = shell
        self.round_number = round_number
        self.rng = rng
        self._answers: dict[str, dict] = {}

    def prepare(self) -> None:
        self.shell.fs.add_directory(self.root)

    def token_hex(self, byte_count: int) -> str:
        return self.rng.randbytes(byte_count).hex()

    def _challenge_from_answer(
        self,
        question: dict,
        variant: str,
        goal_factory: Callable[[dict], Goal],
    ) -> Challenge:
        return Challenge(
            id=question["id"],
            command=question["command"],
            mode=question["mode"],
            variant=variant,
            prompt=question["prompt"],
            example=question["example"],
            goal=goal_factory(self._answers[question["id"]]),
        )


class OutputPack(BasePack):
    def _output_challenge(
        self,
        index: int,
        mode: str,
        variant: str,
        prompt: str,
        example: str,
        solution: str,
        inode_ids: tuple[int, ...],
        expected_stdout: list[str],
    ) -> Challenge:
        return Challenge(
            id=f"{self.round_number}-{index}",
            command=self.command,
            mode=mode,
            variant=variant,
            prompt=prompt,
            example=example,
            goal=OutputGoal(self.command, inode_ids, tuple(expected_stdout), solution),
        )
