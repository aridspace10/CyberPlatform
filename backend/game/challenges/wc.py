"""wc MiniGames scenarios."""

from ..filenode import FileNode
from .core import Challenge, OutputPack


class WcPack(OutputPack):
    command = "wc"
    root = "metrics"
    variants = ("brief", "detailed", "busy")

    modes = {
        "Count Lines": "lines",
        "Count Words": "words",
        "Count Bytes": "bytes",
        "Count Characters": "chars",
    }

    def build(self, index: int, mode: str, variant: str) -> Challenge:
        marker = self.token_hex(3)
        path = f"/metrics/report-{index:02d}-{marker}.txt"
        lines = {
            "brief": [f"alpha {marker}"],
            "detailed": [f"café {marker}", "delta echo"],
            "busy": [f"café {marker}", "delta echo", "résumé review done"],
        }[variant]
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
        context = {
            "brief": "Measure a short report.",
            "detailed": "Check a multilingual report.",
            "busy": "Review a longer activity report.",
        }[variant]
        return self._output_challenge(
            index,
            mode,
            variant,
            f"{context} Use wc to {task} in {path}",
            examples[mode],
            f"wc {flag}{path}",
            (node.inode.id,),
            expected,
        )
