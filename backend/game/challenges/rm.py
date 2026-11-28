"""rm MiniGames scenarios."""

from dataclasses import dataclass

from ..filenode import FileNode
from ..inode import NodeType
from .core import BasePack, Challenge, Observation


@dataclass(frozen=True)
class RmGoal:
    target_path: str
    target_inode_id: int
    guard_path: str
    guard_inode_id: int
    recursive: bool
    solution: str

    def accepts(self, observation: Observation) -> bool:
        shell = observation.shell
        guard = shell.fs.resolve(self.guard_path)
        if not isinstance(shell.fs.resolve(self.target_path), str):
            return False
        if (
            not isinstance(guard, FileNode)
            or guard.inode.id != self.guard_inode_id
            or guard.get_type() != NodeType.FILE
        ):
            return False
        return any(
            run.command == "rm"
            and self.target_inode_id in run.inode_ids
            and (not self.recursive or _has_recursive_option(run.args))
            for run in shell.command_runs
        )


def _has_recursive_option(args: tuple[str, ...]) -> bool:
    return any(
        arg == "--recursive" or (arg.startswith("-") and not arg.startswith("--")
        and any(option in arg[1:] for option in "rR"))
        for arg in args
    )


class RmPack(BasePack):
    command = "rm"
    root = "cleanup"
    variants = ("draft", "temp", "stale")
    modes = {"Remove Tree": "recursive"}

    def build(self, index: int, mode: str, variant: str) -> Challenge:
        marker = self.token_hex(3)
        stem = f"{variant}-{index:02d}-{marker}"
        guard_path = f"/{self.root}/keep-{stem}.txt"
        self.shell.fs.add_file(guard_path)
        guard = self.shell.fs.resolve(guard_path)
        assert isinstance(guard, FileNode)
        guard.set_data(["Keep this file"])
        if mode == "recursive":
            target_path = f"/{self.root}/discard-{stem}"
            self.shell.fs.add_directory(target_path)
            self.shell.fs.add_file(f"{target_path}/old.txt")
            solution = f"rm -r {target_path}"
            prompt = (
                f"Remove the {target_path} directory and its contents using rm's "
                f"recursive option. Preserve {guard_path}."
            )
            example = "rm -r /cleanup/sample-folder"
        else:
            target_path = f"/{self.root}/discard-{stem}.txt"
            self.shell.fs.add_file(target_path)
            solution = f"rm {target_path}"
            prompt = f"Remove {target_path} using rm. Preserve {guard_path}."
            example = "rm /cleanup/sample.txt"
        target = self.shell.fs.resolve(target_path)
        assert isinstance(target, FileNode)
        return Challenge(
            id=f"{self.round_number}-{index}",
            command=self.command,
            mode=mode,
            variant=variant,
            prompt=prompt,
            example=example,
            goal=RmGoal(
                target_path, target.inode.id, guard_path, guard.inode.id,
                mode == "recursive", solution,
            ),
        )
