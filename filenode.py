from __future__ import annotations
from typing import Literal, Tuple
import datetime

class FileNode:
    def __init__(self, parent: FileNode | None, name: str, type: Literal["directory", "file"]):
        self.name = name
        self.parent: FileNode | None = parent
        self.depth = 0
        self.type = type
        self.items: list[Tuple[FileNode, Literal["directory", "file"]]] = []
        self.data: str = ""
        self.permissions = {"user": {"r": True, "w": True, "x": True},
                            "group": {"r": True, "w": True, "x": True},
                            "public": {"r": True, "w": True, "x": True}}
        self.btime = datetime.datetime.now()
        self.ctime = datetime.datetime.now()
        self.atime = datetime.datetime.now()
        self.mtime = datetime.datetime.now()
    
    def __str__(self):
        return f"name: {self.name}, items: {self.items}"
    
    def __repr__(self):
        return self.__str__()

    @property
    def size(self):
        if isinstance(self.data, bytes):
            return len(self.data)
        return len(self.data.encode("utf-8"))
    
    def get_permission_str(self, item: FileNode):
        permission = "d" if item.type == "directory" else "-"
        for i in item.permissions.values():
            for key, value in i.items():
                permission += key if value else "-"
        return permission
    
    def update_permissions(self, updated: dict, recurse: bool, verbose: list[str]) -> list[str]:
        self.ctime = datetime.datetime.now()
        self.permissions = updated

        verbose.append(f"Updated permissions of ${self.name} with ${self.get_permission_str(self)}")
        if (recurse):
            for item in self.items:
                verbose.extend(item[0].update_permissions(updated, recurse, verbose))
        return verbose

    def get_data(self) -> str:
        self.atime = datetime.datetime.now()
        return self.data
    
    def set_data(self, data: str) -> None:
        self.mtime = datetime.datetime.now()
        self.data = data
    
    def append_data(self, data: str) -> None:
        self.mtime = datetime.datetime.now()
        self.data += "\n" + data

    def accumualate_depth(self) -> None:
        self.depth += 1
        if (self.parent != None):
            self.parent.accumualate_depth()
    
    def preorder_traversal(self, content: list[Tuple[int, str]], move: int) -> list[Tuple[int, str]]:
        if (self.items):
            mid = len(self.items) // 2
            for idx, item in enumerate(self.items):
                if (idx == mid):
                    content.append((move, self.name + "-|"))
                content = (item[0].preorder_traversal(content, move + 1))
        else:
            content.append((move, "--"))
            move += 1
            content.append((move, self.name))
        return content

    def add_child(self, name: str, mode: Literal["directory", "file"]) -> FileNode:
        file = FileNode(self, name, mode)
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

    def delete_child(self, name: str) -> FileNode | None:
        for idx, item in enumerate(self.items):
            if (item[0].name == name):
                return self.items.pop(idx)[0]
        return None
                
    def len(self) -> int:
        return len(self.items)

    def list_content(self, prev: str, deep: int = 0, detail: int = 0) -> list:
        content = []
        for item in self.items:
            itemname = prev + "/" + item[0].name if prev else item[0].name
            if (not detail):
                content.append(itemname)
            else:
                content.append([self.get_permission_str(item[0]), str(1), "user", "user", str(item[0].size), str(self.mtime.strftime("%b")), str(self.mtime.day), str(self.mtime.year), itemname])

            if item[1] == "directory" and deep:
                deep -= 1
                content.extend(item[0].list_content(prev + "/" + item[0].name, deep))
        return content