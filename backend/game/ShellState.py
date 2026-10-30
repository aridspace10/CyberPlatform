from typing import Callable

from game.filesystem import FileSystem
from game.identity import EffectiveIdentity


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
        self.identity = EffectiveIdentity()
