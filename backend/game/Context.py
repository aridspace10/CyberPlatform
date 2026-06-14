from dataclasses import dataclass

from game.filesystem import FileNode, FileSystem
from game.NetworkManager import NetworkManager
from game.ProcessManager import ProcessManager
from game.ShellState import ShellState


@dataclass
class SystemContext:
    fs: FileSystem
    pm: ProcessManager
    nm: NetworkManager
    shell: ShellState


@dataclass
class ExecutionContext:
    stdin: FileNode | str | None = None
    stdout: FileNode | str | None = None


@dataclass
class CommandContext:
    system: SystemContext
    command: str
    args: list[str]
    stdin: FileNode
    stdout: FileNode | None
