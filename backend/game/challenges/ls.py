"""ls MiniGames scenarios."""

from ..filenode import FileNode
from .core import Challenge, OutputPack


class LsPack(OutputPack):
    command = "ls"
    root = "inventory"
    variants = ("brief", "detailed", "busy")

    modes = {"Show Hidden": "hidden", "Long Listing": "long"}

    def build(self, index: int, mode: str, variant: str) -> Challenge:
        directory = f"/inventory/set-{index:02d}-{self.token_hex(2)}"
        self.shell.fs.add_directory(directory)
        marker = self.token_hex(3)
        entries = {
            "brief": (f"report-{marker}.txt", f".draft-{marker}"),
            "detailed": (
                "notes.txt",
                f"report-{marker}.txt",
                "index.csv",
                f".draft-{marker}",
            ),
            "busy": (
                "notes.txt",
                f"report-{marker}.txt",
                "index.csv",
                "summary.log",
                f".draft-{marker}",
                ".cache",
            ),
        }[variant]
        for name in entries:
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
        context = {
            "brief": "Check a new intake folder.",
            "detailed": "Review a mixed inventory.",
            "busy": "Audit a crowded inventory.",
        }[variant]
        examples = {
            "basic": "ls /inventory/sample",
            "hidden": "ls -A /inventory/sample",
            "long": "ls -l /inventory/sample",
        }
        return self._output_challenge(
            index,
            mode,
            variant,
            f"{context} {prompts[mode]}",
            examples[mode],
            f"ls {flag}{directory}",
            (node.inode.id,),
            expected,
        )
