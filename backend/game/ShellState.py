from typing import Callable

from game.filesystem import FileSystem


class ShellState:
    def __init__(self):
        self.cwd = ""
        self.fs = FileSystem()
        self.commands: list[str] = []
        self.vars: dict = {}
        self.ls: int = 0
        self.last_status: int = 0
        self.foreground_pid: int | None = None
        self.continuation: Callable[[object], object] | None = None
