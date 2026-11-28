"""touch MiniGames scenarios."""

from dataclasses import dataclass
from datetime import datetime

from ..filenode import FileNode
from ..inode import NodeType
from .core import BasePack, Challenge, Observation


@dataclass(frozen=True)
class TouchGoal:
    path: str
    prior_inode_id: int | None
    expected_mtime: datetime | None
    original_atime: datetime | None
    guard_path: str
    guard_inode_id: int
    solution: str

    def accepts(self, observation: Observation) -> bool:
        shell = observation.shell
        node = shell.fs.resolve(self.path)
        guard = shell.fs.resolve(self.guard_path)
        if (
            not isinstance(node, FileNode)
            or node.get_type() != NodeType.FILE
            or not isinstance(guard, FileNode)
            or guard.inode.id != self.guard_inode_id
        ):
            return False
        if self.prior_inode_id is not None and node.inode.id != self.prior_inode_id:
            return False
        if self.expected_mtime is not None and (
            node.inode.mtime != self.expected_mtime
            or node.inode.atime != self.original_atime
        ):
            return False
        return any(
            run.command == "touch" and node.inode.id in run.inode_ids
            for run in shell.command_runs
        )


class TouchPack(BasePack):
    command = "touch"
    root = "workspace"
    variants = ("report", "draft", "archive")
    modes = {"Update Modified Time": "mtime"}

    def build(self, index: int, mode: str, variant: str) -> Challenge:
        marker = self.token_hex(3)
        stem = f"{variant}-{index:02d}-{marker}"
        path = f"/{self.root}/{stem}.txt"
        guard_path = f"/{self.root}/keep-{stem}.txt"
        self.shell.fs.add_file(guard_path)
        guard = self.shell.fs.resolve(guard_path)
        assert isinstance(guard, FileNode)
        guard.set_data(["Keep this note"])
        if mode == "mtime":
            self.shell.fs.add_file(path)
            node = self.shell.fs.resolve(path)
            assert isinstance(node, FileNode)
            expected_mtime = datetime(2030, 1, 2, 12, 30)
            original_atime = node.inode.atime
            prior_inode_id = node.inode.id
            prompt = (
                f"Set only the modification time of {path} to "
                f"2030-01-02 12:30 using touch. Preserve {guard_path}."
            )
            example = "touch -m -t 203102031405 /workspace/sample.txt"
            solution = f"touch -m -t 203001021230 {path}"
        else:
            expected_mtime = None
            original_atime = None
            prior_inode_id = None
            prompt = f"Create the empty file {path} using touch. Preserve {guard_path}."
            example = "touch /workspace/sample.txt"
            solution = f"touch {path}"
        return Challenge(
            id=f"{self.round_number}-{index}",
            command=self.command,
            mode=mode,
            variant=variant,
            prompt=prompt,
            example=example,
            goal=TouchGoal(
                path, prior_inode_id, expected_mtime, original_atime,
                guard_path, guard.inode.id, solution,
            ),
        )
