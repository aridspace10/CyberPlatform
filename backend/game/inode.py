from __future__ import annotations
import base64
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
        self.data: list[str] = []
        self.binary_data: bytes | None = None
        self.symlink_target: str | None = None
        self.has_trailing_newline: bool = False
        self.owner = "user"
        self.group = "user"

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
            "symlink_target": self.symlink_target,
            "has_trailing_newline": self.has_trailing_newline,
            "link_count": self.link_count,
            "permissions": self.permissions,
            "owner": self.owner,
            "group": self.group,
            "btimes": self.btime.isoformat(),
            "ctimes": self.ctime.isoformat(),
            "atimes": self.atime.isoformat(),
            "mtimes": self.mtime.isoformat(),
            "binary_data": (
                base64.b64encode(self.binary_data).decode("ascii")
                if self.binary_data is not None
                else None
            ),
        }

    def from_dict(self, i: dict) -> None:
        self.id = i["id"]
        Inode._next_id = max(Inode._next_id, self.id + 1)
        self.type = NodeType(i["type"])
        self.data = i["data"]
        self.symlink_target = i.get("symlink_target")
        if self.type == NodeType.SYMLINK and self.symlink_target is None:
            legacy_data = self.data
            self.symlink_target = legacy_data[0] if legacy_data else None
        # Older saves have neither field. Their restored newline state was
        # false; keep that behavior because the original value is unknowable.
        self.has_trailing_newline = i.get("has_trailing_newline", False)
        self.link_count = i.get("link_count", 1)
        self.owner = i.get("owner", "user")
        self.group = i.get("group", "user")
        self.permissions = i["permissions"]
        self.btime = datetime.fromisoformat(i["btimes"])
        self.ctime = datetime.fromisoformat(i["ctimes"])
        self.atime = datetime.fromisoformat(i["atimes"])
        self.mtime = datetime.fromisoformat(i["mtimes"])

        encoded = i.get("binary_data")

        self.binary_data = (
            base64.b64decode(encoded)
            if encoded is not None
            else None
        )

    @property
    def size(self):
        return sum(len(line) for line in self.data)

    def get_data(self) -> list[str]:
        self.atime = datetime.now()
        return self.data

    def set_data(self, data: list[str]) -> None:
        self.mtime = datetime.now()
        self.data = data
        self.has_trailing_newline = bool(data)

    def append_data(self, data: list[str]) -> None:
        if not data:
            return
        self.mtime = datetime.now()
        if self.data and not self.has_trailing_newline:
            self.data[-1] += data[0]
            self.data.extend(data[1:])
        else:
            self.data.extend(data)
        self.has_trailing_newline = True
    
    def append_byte_data(self, data: bytes) -> None:
        if self.binary_data is None:
            self.binary_data = b""

        self.binary_data += data
        self.mtime = datetime.now()

    def get_byte_data(self) -> bytes:
        if self.binary_data is not None:
            return self.binary_data

        text = "\n".join(self.data)
        if self.has_trailing_newline:
            text += "\n"

        return text.encode("utf-8")