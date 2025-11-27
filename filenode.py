from __future__ import annotations
from typing import Literal, Tuple

class FileNode:
    def __init__(self, parent: FileNode | None, name: str):
        self.name = name
        self.parent = parent
        self.items: list[Tuple[FileNode, Literal["directory", "file"]]] = []

    def add_child(self, name: str, mode: Literal["directory", "file"]) -> FileNode:
        file = FileNode(self, name)
        self.items.append((file, mode))
        return file
    
    def search(self, name: str) -> Literal["directory", "file", None]:
        for item in self.items:
            if (item[0].name == name):
                return item[1]
        return None
    
    def access(self, name: str) -> FileNode | None:
        for item in self.items:
            if (item[0].name == name):
                return item[0]
        return None

    def delete_child(self, name: str) -> None:
        for idx, item in enumerate(self.items):
            if (item[0].name == name):
                self.items.pop(idx)
                
