"""Directory navigation questions for MiniGames."""

from dataclasses import dataclass

from ..filenode import FileNode
from .core import BasePack, Challenge, Observation


@dataclass(frozen=True)
class DirectoryGoal:
    path: str
    inode_id: int
    relative: bool
    solution: str

    def accepts(self, observation: Observation) -> bool:
        shell = observation.shell
        if (
            shell.cwd != self.path
            or shell.fs.display_path(shell.fs.current) != self.path
        ):
            return False
        return any(
            run.command == "cd"
            and run.inode_ids == (self.inode_id,)
            and run.output == ()
            and run.args
            and (not self.relative or not run.args[0].startswith("/"))
            for run in shell.command_runs
        )


class CdPack(BasePack):
    command = "cd"
    root = "navigation"
    variants = ("harbor", "forest", "workshop")
    modes = {"Relative Path": "relative"}

    def build(self, index: int, mode: str, variant: str) -> Challenge:
        parent = f"/{self.root}/{variant}-{index:02d}-{self.token_hex(2)}"
        target = f"{parent}/finish"
        self.shell.fs.add_directory(parent)
        self.shell.fs.add_directory(target)
        self.shell.fs.add_directory(f"{parent}/other")
        node = self.shell.fs.resolve(target)
        assert isinstance(node, FileNode)

        relative = mode == "relative"
        prompt = (
            f"Go to {parent}, then use a relative cd path so your final "
            f"working directory is {target}."
            if relative
            else f"Use cd so your final working directory is {target}."
        )
        example = "cd /demo; cd sample" if relative else "cd /demo/sample"
        solution = f"cd {parent}; cd finish" if relative else f"cd {target}"
        return Challenge(
            id=f"{self.round_number}-{index}",
            command=self.command,
            mode=mode,
            variant=variant,
            prompt=prompt,
            example=example,
            goal=DirectoryGoal(target, node.inode.id, relative, solution),
        )
