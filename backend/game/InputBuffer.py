from collections.abc import Iterable
from dataclasses import dataclass

from game.filenode import FileNode


@dataclass(frozen=True, slots=True)
class InputBuffer:
    """An immutable snapshot of batch input, without filesystem identity."""

    lines: tuple[str, ...] = ()
    has_trailing_newline: bool = False

    def __post_init__(self) -> None:
        # Defensively snapshot even callers that supply a mutable sequence.
        object.__setattr__(self, "lines", tuple(self.lines))

    @classmethod
    def from_file(cls, node: FileNode) -> "InputBuffer":
        return cls(tuple(node.get_data()), node.inode.has_trailing_newline)

    @classmethod
    def from_lines(cls, lines: Iterable[str]) -> "InputBuffer":
        """Adapt line-oriented command output or completed heredoc lines.

        The current output API has no final-newline metadata: each returned
        entry represents a terminated line. An empty sequence is explicit EOF.
        """
        snapshot = tuple(lines)
        return cls(snapshot, bool(snapshot))
