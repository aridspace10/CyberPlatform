from __future__ import annotations
from typing import Literal

class FileNode:
    def __init__(self, parent: FileNode | None, name: str):
        self.name = name
        self.parent = parent
        self.items = []

    def add_child(self, name: str, mode: Literal["directory", "file"]) -> FileNode:
        file = FileNode(self, name)
        self.items.append((file, mode))
        return file
