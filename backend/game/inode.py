
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
        self.data: bytes = b""
        self.symlink_target: str | None = None
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

    # --------------------------------------------------
    # Serialization
    # --------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "data": base64.b64encode(self.data).decode("ascii"),
            "data_encoding": "base64",
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
        }

    def from_dict(self, i: dict) -> None:
        self.id = i["id"]
        Inode._next_id = max(Inode._next_id, self.id + 1)
        self.type = NodeType(i["type"])

        # New byte-based serialization format
        if i.get("data_encoding") == "base64":
            self.data = base64.b64decode(i["data"])

        # Legacy binary storage format
        elif i.get("binary_data") is not None:
            self.data = base64.b64decode(i["binary_data"])

        # Legacy list[str] storage format
        else:
            text = "\n".join(i.get("data", []))

            if i.get("has_trailing_newline", False):
                text += "\n"

            self.data = text.encode("utf-8")

        self.symlink_target = i.get("symlink_target")

        # Legacy symlink compatibility
        if self.type == NodeType.SYMLINK and self.symlink_target is None:
            legacy_data = i.get("data", [])

            if isinstance(legacy_data, list) and legacy_data:
                self.symlink_target = legacy_data[0]

        self.link_count = i.get("link_count", 1)
        self.owner = i.get("owner", "user")
        self.group = i.get("group", "user")
        self.permissions = i["permissions"]

        self.btime = datetime.fromisoformat(i["btimes"])
        self.ctime = datetime.fromisoformat(i["ctimes"])
        self.atime = datetime.fromisoformat(i["atimes"])
        self.mtime = datetime.fromisoformat(i["mtimes"])

    # --------------------------------------------------
    # Properties
    # --------------------------------------------------

    @property
    def size(self) -> int:
        return len(self.data)

    @property
    def has_trailing_newline(self) -> bool:
        return self.data.endswith(b"\n")

    @has_trailing_newline.setter
    def has_trailing_newline(self, value: bool) -> None:
        if value and not self.data.endswith(b"\n"):
            self.append_byte_data(b"\n")

        elif not value and self.data.endswith(b"\n"):
            self.set_byte_data(self.data[:-1])

    # --------------------------------------------------
    # Binary interface
    # --------------------------------------------------

    def get_byte_data(self) -> bytes:
        self.atime = datetime.now()
        return self.data

    def set_byte_data(self, data: bytes) -> None:
        self.data = bytes(data)
        self.mtime = datetime.now()

    def append_byte_data(self, data: bytes) -> None:
        if not data:
            return

        self.data += bytes(data)
        self.mtime = datetime.now()

    # --------------------------------------------------
    # Text interface
    # --------------------------------------------------

    def get_data(self) -> list[str]:
        data = self.get_byte_data()

        if not data:
            return []

        text = data.decode("utf-8", errors="surrogateescape")
        lines = text.split("\n")

        if text.endswith("\n"):
            lines.pop()

        return lines

    def set_data(self, data: list[str]) -> None:
        text = "\n".join(data)

        if data:
            text += "\n"

        self.set_byte_data(
            text.encode("utf-8", errors="surrogateescape")
        )

    def append_data(self, data: list[str]) -> None:
        if not data:
            return

        text = "\n".join(data) + "\n"

        self.append_byte_data(
            text.encode("utf-8", errors="surrogateescape")
        )
