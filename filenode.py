from __future__ import annotations
from typing import Literal, Tuple

class FileNode:
    def __init__(self, parent: FileNode | None, name: str):
        self.name = name
        self.parent: FileNode | None = parent
        self.depth = 0
        self.nodes = 0
        self.items: list[Tuple[FileNode, Literal["directory", "file"]]] = []

    def accumualate_depth(self) -> None:
        self.depth += 1
        if (self.parent != None):
            self.parent.accumualate_depth()
    
    def preorder_traversal(self, content: list[Tuple[int, str]], move: int) -> list[Tuple[int, str]]:
        if (self.items):
            mid = len(self.items) // 2
            for idx, item in enumerate(self.items):
                if (idx == mid):
                    content.append((move, self.name))
                content = (item[0].preorder_traversal(content, move + 1))
        else:
            content.append((move, self.name))
        return content


    def add_child(self, name: str, mode: Literal["directory", "file"]) -> FileNode:
        file = FileNode(self, name)
        if (not len(self.items)):
            self.depth = 1
            if (self.parent is not None):
                self.parent.accumualate_depth()
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

    def len(self) -> int:
        return len(self.items)

    def list_content(self, deep: int = 0) -> list:
        content = []
        for item in self.items:
            content.append(item[0].name)
            if item[1] == "directory" and deep:
                deep -= 1
                content.extend(item[0].list_content(deep))
        return content