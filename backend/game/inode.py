from __future__ import annotations
from typing import Literal, Tuple
from datetime import datetime

from enum import Enum

class NodeType(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"

class Inode:
    _next_id = 1

    def __init__(self, type: NodeType):
        self.id = Inode._next_id
        Inode._next_id += 1

        self.type: NodeType = type
        self.link_count = 1
        self.data: str = ""

        self.permissions = {
            "user": {"r": True, "w": True, "x": True},
            "group": {"r": True, "w": True, "x": True},
            "public": {"r": True, "w": True, "x": True},
        }

        now = datetime.now()
        self.btime = now
        self.ctime = now
        self.atime = now
        self.mtime = now
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "permissions": self.permissions,
            "btimes": self.btime.isoformat(),
            "ctimes": self.ctime.isoformat(),
            "atimes": self.atime.isoformat(),
            "mtimes": self.mtime.isoformat(),
        }
    
    def from_dict(self, i: dict) -> None:
        self.id = i["id"]
        self.type = NodeType(i['type'])
        self.data = i["data"]
        self.permissions = i["permissions"]
        self.btime = datetime.fromisoformat(i["btimes"])
        self.ctime = datetime.fromisoformat(i["ctimes"])
        self.atime = datetime.fromisoformat(i["atimes"])
        self.mtime = datetime.fromisoformat(i["mtimes"])

    @property
    def size(self):
        if isinstance(self.data, bytes):
            return len(self.data)
        return len(self.data.encode("utf-8"))
    
    def get_data(self) -> str:
        self.atime = datetime.now()
        return self.data
    
    def set_data(self, data: str) -> None:
        self.mtime = datetime.now()
        self.data = data
    
    def append_data(self, data: str) -> None:
        self.mtime = datetime.now()
        self.data += "\n" + data