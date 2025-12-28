from __future__ import annotations
from typing import Literal, Tuple
import datetime

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

        now = datetime.datetime.now()
        self.btime = now
        self.ctime = now
        self.atime = now
        self.mtime = now

    @property
    def size(self):
        if isinstance(self.data, bytes):
            return len(self.data)
        return len(self.data.encode("utf-8"))
    
    def get_data(self) -> str:
        self.atime = datetime.datetime.now()
        return self.data
    
    def set_data(self, data: str) -> None:
        self.mtime = datetime.datetime.now()
        self.data = data
    
    def append_data(self, data: str) -> None:
        self.mtime = datetime.datetime.now()
        self.data += "\n" + data