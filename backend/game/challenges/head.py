"""head MiniGames scenarios."""

from dataclasses import dataclass

from ..filenode import FileNode
from .core import BasePack, Challenge, Observation


def _has_count(args: tuple[str, ...], kind: str, count: int) -> bool:
    short, long = ("-c", "--bytes") if kind == "bytes" else ("-n", "--lines")
    return (
        any(args[index:index + 2] == (flag, str(count))
            for index in range(len(args) - 1) for flag in (short, long))
        or f"{long}={count}" in args
    )


@dataclass(frozen=True)
class HeadGoal:
    inode_id: int
    expected_stdout: tuple[str, ...]
    kind: str
    count: int
    solution: str

    def accepts(self, observation: Observation) -> bool:
        if tuple(observation.stdout) != self.expected_stdout:
            return False
        return any(
            run.command == "head"
            and run.inode_ids == (self.inode_id,)
            and run.output == self.expected_stdout
            and (self.kind == "basic" or _has_count(run.args, self.kind, self.count))
            for run in observation.shell.command_runs
        )


class HeadPack(BasePack):
    command = "head"
    root = "reports"
    variants = ("intake", "release", "audit")
    modes = {"First Lines": "lines", "First Bytes": "bytes"}

    def build(self, index: int, mode: str, variant: str) -> Challenge:
        marker = self.token_hex(3)
        path = f"/{self.root}/{variant}-{index:02d}-{marker}.txt"
        lines = [
            f"{variant.upper()} {marker} entry {number}"
            for number in range(1, 15)
        ]
        self.shell.fs.add_file(path)
        node = self.shell.fs.resolve(path)
        assert isinstance(node, FileNode)
        node.set_data(lines)
        if mode == "bytes":
            count = len(lines[0].encode("utf-8")) + 1 + 5
            expected = (lines[0], lines[1][:5])
            task = f"print exactly the first {count} bytes"
            example = "head -c 7 /reports/sample.txt"
            solution = f"head -c {count} {path}"
        elif mode == "lines":
            count = 3
            expected = tuple(lines[:count])
            task = f"print exactly the first {count} lines"
            example = "head -n 4 /reports/sample.txt"
            solution = f"head -n {count} {path}"
        else:
            count = 10
            expected = tuple(lines[:count])
            task = "print the first ten lines"
            example = "head /reports/sample.txt"
            solution = f"head {path}"
        return Challenge(
            id=f"{self.round_number}-{index}",
            command=self.command,
            mode=mode,
            variant=variant,
            prompt=f"Review the {variant} report: use head to {task} of {path}.",
            example=example,
            goal=HeadGoal(node.inode.id, expected, mode, count, solution),
        )
