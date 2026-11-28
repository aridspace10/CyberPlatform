"""mkdir MiniGames scenarios."""

from dataclasses import dataclass

from ..filenode import FileNode
from ..inode import NodeType
from .core import BasePack, Challenge, Observation


@dataclass(frozen=True)
class MkdirGoal:
    path: str
    expected_paths: tuple[str, ...]
    required_flag: str | None
    solution: str

    def accepts(self, observation: Observation) -> bool:
        nodes = [observation.shell.fs.resolve(path) for path in self.expected_paths]
        if not all(
            isinstance(node, FileNode) and node.get_type() == NodeType.DIRECTORY
            for node in nodes
        ):
            return False
        target = nodes[-1]
        return any(
            run.command == "mkdir"
            and target.inode.id in run.inode_ids
            and (
                self.required_flag is None
                or self.required_flag in run.args
                or (self.required_flag == "-p" and "--parents" in run.args)
            )
            for run in observation.shell.command_runs
        )


class MkdirPack(BasePack):
    command = "mkdir"
    root = "workspaces"
    variants = ("project", "report", "archive")
    modes = {"Create Parents": "parents"}

    def build(self, index: int, mode: str, variant: str) -> Challenge:
        marker = self.token_hex(3)
        group = f"{variant}-{index:02d}-{marker}"
        if mode == "parents":
            parent = f"/{self.root}/{group}"
            path = f"{parent}/handoff"
            expected_paths = (parent, path)
            solution = f"mkdir -p {path}"
            prompt = (
                f"Create the {path} directory and any missing parent directories "
                "using mkdir's parents option."
            )
            example = "mkdir -p /workspaces/sample/notes"
        else:
            path = f"/{self.root}/{group}"
            expected_paths = (path,)
            solution = f"mkdir {path}"
            prompt = f"Create the {path} directory using mkdir."
            example = "mkdir /workspaces/sample"
        return Challenge(
            id=f"{self.round_number}-{index}",
            command=self.command,
            mode=mode,
            variant=variant,
            prompt=prompt,
            example=example,
            goal=MkdirGoal(
                path, expected_paths, "-p" if mode == "parents" else None, solution
            ),
        )
