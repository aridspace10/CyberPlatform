from dataclasses import dataclass
from typing import Callable

from game.filesystem import FileSystem
from game.identity import EffectiveIdentity


@dataclass(frozen=True)
class GrepMatch:
    inode_id: int
    pattern: str
    line: str
    options: frozenset[str]
    output: str


@dataclass(frozen=True)
class SedChange:
    inode_id: int
    before: tuple[str, ...]
    after: tuple[str, ...]
    output: tuple[str, ...]
    in_place: bool
    backup_suffix: str
    ignore_case: bool
    features: frozenset[str] = frozenset()


class ShellState:
    def __init__(self):
        self.cwd = "/"
        self.fs = FileSystem()
        self.commands: list[str] = []
        self.vars: dict = {}
        self.ls: int = 0
        self.last_status: int = 0
        self.foreground_pid: int | None = None
        self.continuation: Callable[[object], object] | None = None
        self.background_pid: int | None = None
        self.background_jobs: dict[int, str] = {}
        self.background_children: dict[int, list] = {}
        self.grep_matches: set[GrepMatch] = set()
        self.sed_changes: list[SedChange] = []
        self.allow_pipes = True
        self.identity = EffectiveIdentity()
