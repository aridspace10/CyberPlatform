"""pwd MiniGames scenarios."""

from ..filenode import FileNode
from .core import Challenge, OutputPack


class PwdPack(OutputPack):
    command = "pwd"
    root = "workspaces"
    variants = ("incident", "release", "team")
    modes = {"Current Path": "basic"}

    def build(self, index: int, mode: str, variant: str) -> Challenge:
        token = self.token_hex(2)
        directory, context = {
            "incident": (
                f"/workspaces/incident-{index:02d}-{token}/logs",
                "Inspect an incident's log directory.",
            ),
            "release": (
                f"/workspaces/release-{index:02d}-{token}/reports/drafts",
                "Check the draft reports for a release.",
            ),
            "team": (
                f"/workspaces/team-{index:02d}-{token}/archive",
                "Find a team's archive.",
            ),
        }[variant]
        self.shell.fs.add_directory(directory, creating=True)
        node = self.shell.fs.resolve(directory)
        assert isinstance(node, FileNode)
        return self._output_challenge(
            index,
            mode,
            variant,
            f"{context} Change into {directory}, then run pwd to print "
            "that exact working directory.",
            "cd /practice/sample; pwd",
            f"cd {directory}; pwd",
            (node.inode.id,),
            [directory],
        )
