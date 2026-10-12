from dataclasses import dataclass

from game.filenode import FileNode
from game.filesystem import FileSystem
from game.InputBuffer import InputBuffer
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
    stdin: InputBuffer | None = None
    stdout: FileNode | str | None = None


@dataclass
class CommandContext:
    system: SystemContext
    command: str
    args: list[str]
    stdin: InputBuffer
    stdout: FileNode | None
