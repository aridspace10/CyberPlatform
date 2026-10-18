from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.Program import Program


class ProcessState(StrEnum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    TERMINATED = "TERMINATED"
    SLEEPING = "SLEEPING"
    WAITING_INPUT = "WAITING_INPUT"


class Process:
    def __init__(
        self,
        pid: int,
        command: str,
        parent: int,
        status: ProcessState = ProcessState.RUNNING,
    ):
        self.pid: int = pid
        self.ppid: int = parent
        self.command: str = command
        self.status: str = status
        self.stdout: list[str] = []
        self.stderr: list[str] = []
        self.foreground: bool = False
        self.program: Program | None = None

    def __repr__(self):
        return f"PID={self.pid} PPID={self.ppid} {self.command}"
