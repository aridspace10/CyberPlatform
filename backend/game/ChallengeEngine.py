"""Build and evaluate output challenges for terminal minigames."""

import secrets
from dataclasses import dataclass

from .filenode import FileNode
from .ShellState import CommandRun, ShellState


@dataclass(frozen=True)
class OutputGoal:
    """The private result and source files that a challenge requires."""

    command: str
    inode_ids: tuple[int, ...]
    expected_stdout: tuple[str, ...]
    solution: str

    def accepts(self, runs: list[CommandRun], stdout: list[str]) -> bool:
        if tuple(stdout) != self.expected_stdout:
            return False
        return any(
            run.command == self.command
            and run.inode_ids == self.inode_ids
            and run.output == self.expected_stdout
            for run in runs
        )


@dataclass(frozen=True)
class Challenge:
    id: str
    command: str
    mode: str
    prompt: str
    example: str
    goal: OutputGoal

    def public_data(self) -> dict:
        return {
            "id": self.id,
            "command": self.command,
            "mode": self.mode,
            "prompt": self.prompt,
            "example": self.example,
        }


class ChallengeEngine:
    """Own challenge definitions and score an observed shell result."""

    def __init__(self, shell: ShellState, round_number: int):
        self.shell = shell
        self.round_number = round_number
        self.challenges: dict[str, Challenge] = {}

    def prepare(self, commands: list[str]) -> None:
        roots = {"ls": "inventory", "cat": "documents", "wc": "metrics"}
        for command in commands:
            if command in roots:
                self.shell.fs.add_directory(roots[command])

    def create(self, index: int, command: str, mode: str) -> Challenge:
        builders = {
            "ls": self._build_ls,
            "cat": self._build_cat,
            "wc": self._build_wc,
        }
        challenge = builders[command](index, mode)
        self.challenges[challenge.id] = challenge
        return challenge

    def evaluate(
        self, runs: list[CommandRun], stdout: list[str], completed: set[str]
    ) -> list[str]:
        return [
            challenge.id
            for challenge in self.challenges.values()
            if challenge.id not in completed and challenge.goal.accepts(runs, stdout)
        ]

    def _output_challenge(
        self,
        index: int,
        command: str,
        mode: str,
        prompt: str,
        example: str,
        solution: str,
        inode_ids: tuple[int, ...],
        expected_stdout: list[str],
    ) -> Challenge:
        return Challenge(
            id=f"{self.round_number}-{index}",
            command=command,
            mode=mode,
            prompt=prompt,
            example=example,
            goal=OutputGoal(command, inode_ids, tuple(expected_stdout), solution),
        )

    def _build_ls(self, index: int, mode: str) -> Challenge:
        directory = f"/inventory/set-{index:02d}-{secrets.token_hex(2)}"
        self.shell.fs.add_directory(directory)
        marker = secrets.token_hex(3)
        for name in (f"report-{marker}.txt", "notes.txt", f".draft-{marker}"):
            self.shell.fs.add_file(f"{directory}/{name}")
        node = self.shell.fs.resolve(directory)
        assert isinstance(node, FileNode)
        flag = {"basic": "", "hidden": "-A ", "long": "-l "}[mode]
        detail = 1 if mode == "long" else 0
        extras = {"showhidden": True} if mode == "hidden" else {}
        rows = self.shell.fs.list_files(directory, detail=detail, extras=extras)
        assert isinstance(rows, list)
        expected = [" ".join(row) for row in rows]
        prompts = {
            "basic": f"Use ls to list the visible entries in {directory}",
            "hidden": f"Use ls to include hidden entries in {directory}",
            "long": f"Use ls to show a long listing of {directory}",
        }
        examples = {
            "basic": "ls /inventory/sample",
            "hidden": "ls -A /inventory/sample",
            "long": "ls -l /inventory/sample",
        }
        return self._output_challenge(
            index,
            "ls",
            mode,
            prompts[mode],
            examples[mode],
            f"ls {flag}{directory}",
            (node.inode.id,),
            expected,
        )

    def _build_cat(self, index: int, mode: str) -> Challenge:
        marker = secrets.token_hex(3)
        path = f"/documents/note-{index:02d}-{marker}.txt"
        lines = [f"REF {marker} opened", "owner notified"]
        self.shell.fs.add_file(path)
        node = self.shell.fs.resolve(path)
        assert isinstance(node, FileNode)
        node.set_data(list(lines))
        paths = [path]
        inode_ids = [node.inode.id]
        if mode == "multiple":
            second = f"/documents/appendix-{index:02d}-{marker}.txt"
            self.shell.fs.add_file(second)
            second_node = self.shell.fs.resolve(second)
            assert isinstance(second_node, FileNode)
            second_node.set_data([f"REF {marker} closed"])
            paths.append(second)
            inode_ids.append(second_node.inode.id)
            lines.append(f"REF {marker} closed")
        expected = (
            [f"{number} {line}" for number, line in enumerate(lines, 1)]
            if mode == "numbered"
            else lines
        )
        flag = "-n " if mode == "numbered" else ""
        prompt = (
            f"Use cat to print both files in order: {paths[0]} then {paths[1]}"
            if mode == "multiple"
            else f"Use cat to {'number and print' if mode == 'numbered' else 'print'} "
            f"the lines in {path}"
        )
        examples = {
            "basic": "cat /documents/sample.txt",
            "numbered": "cat -n /documents/sample.txt",
            "multiple": "cat /documents/first.txt /documents/second.txt",
        }
        return self._output_challenge(
            index,
            "cat",
            mode,
            prompt,
            examples[mode],
            f"cat {flag}{' '.join(paths)}",
            tuple(inode_ids),
            expected,
        )

    def _build_wc(self, index: int, mode: str) -> Challenge:
        marker = secrets.token_hex(3)
        path = f"/metrics/report-{index:02d}-{marker}.txt"
        lines = [f"café {marker}", "delta echo"]
        self.shell.fs.add_file(path)
        node = self.shell.fs.resolve(path)
        assert isinstance(node, FileNode)
        node.set_data(lines)
        content = "\n".join(lines) + "\n"
        counts = {
            "lines": str(content.count("\n")),
            "words": str(len(content.split())),
            "bytes": str(len(content.encode("utf-8"))),
            "chars": str(len(content)),
        }
        flag = {
            "basic": "",
            "lines": "-l ",
            "words": "-w ",
            "bytes": "-c ",
            "chars": "-m ",
        }[mode]
        expected = (
            [" ".join(counts[key] for key in ("lines", "words", "bytes"))]
            if mode == "basic"
            else [counts[mode]]
        )
        task = {
            "basic": "show line, word, and byte counts",
            "lines": "count lines",
            "words": "count words",
            "bytes": "count bytes",
            "chars": "count characters",
        }[mode]
        examples = {
            "basic": "wc /metrics/sample.txt",
            "lines": "wc -l /metrics/sample.txt",
            "words": "wc -w /metrics/sample.txt",
            "bytes": "wc -c /metrics/sample.txt",
            "chars": "wc -m /metrics/sample.txt",
        }
        return self._output_challenge(
            index,
            "wc",
            mode,
            f"Use wc to {task} in {path}",
            examples[mode],
            f"wc {flag}{path}",
            (node.inode.id,),
            expected,
        )
