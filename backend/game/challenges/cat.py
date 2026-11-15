"""cat MiniGames scenarios."""

from ..filenode import FileNode
from .core import Challenge, OutputPack


class CatPack(OutputPack):
    command = "cat"
    root = "documents"
    variants = ("brief", "detailed", "busy")

    modes = {"Number Lines": "numbered", "Combine Files": "multiple"}

    def build(self, index: int, mode: str, variant: str) -> Challenge:
        marker = self.token_hex(3)
        path = f"/documents/note-{index:02d}-{marker}.txt"
        lines = {
            "brief": [f"REF {marker} opened", "owner notified"],
            "detailed": [f"REF {marker} opened", "review queued", "owner notified"],
            "busy": [
                f"REF {marker} opened",
                "review queued",
                "owner notified",
                "archive requested",
            ],
        }[variant]
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
        context = {
            "brief": "Read a short handoff note.",
            "detailed": "Review a status update.",
            "busy": "Check a longer incident record.",
        }[variant]
        examples = {
            "basic": "cat /documents/sample.txt",
            "numbered": "cat -n /documents/sample.txt",
            "multiple": "cat /documents/first.txt /documents/second.txt",
        }
        return self._output_challenge(
            index,
            mode,
            variant,
            f"{context} {prompt}",
            examples[mode],
            f"cat {flag}{' '.join(paths)}",
            tuple(inode_ids),
            expected,
        )
