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

class Process():
    _next_id = 1
    def __init__(self, command: str, parent: int, status: ProcessState = ProcessState.RUNNING):
        self.pid: int = Process._next_id
        Process._next_id += 1
        self.ppid: int = parent
        self.command: str = command
        self.status: str = status
        self.stdout: list[str] = []
        self.stderr: list[str] = []
        self.foreground: bool = False
        self.program: Program | None = None
    
    def __repr__(self):
        return f"PID={self.pid} PPID={self.ppid} {self.command}"