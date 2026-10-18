import posixpath
from datetime import datetime

from game.filenode import FileNode
from game.identity import EffectiveIdentity
from game.inode import Inode, NodeType


class PathResolutionError(str):
    """A readable path error with the original path and a machine-usable code."""

    def __new__(cls, path: str, message: str, code: str):
        error = super().__new__(cls, message)
        error.path = path
        error.code = code
        return error


class FileSystem:
    def __init__(self):
        inode = Inode(NodeType.DIRECTORY)
        self.filehead = FileNode(None, "root", inode)
        self.current: FileNode = self.filehead
        self.lcs = 0
        self.cwd = "/"
        self.identity = EffectiveIdentity()

    def permission_error(self, node: FileNode, permission: str) -> str | None:
        """Return a simulated permission error, if the current identity lacks access."""
        identity = self.identity
        if identity.privileged:
            return None
        if identity.username == node.inode.owner:
            class_name = "user"
        elif node.inode.group in identity.groups or node.inode.group == identity.primary_group:
            class_name = "group"
        else:
            class_name = "public"
        bits = node.inode.permissions.get(class_name, {})
        if bits.get(permission, False):
            return None
        action = {"r": "read", "w": "write", "x": "search"}.get(permission, permission)
        return f"Permission denied: {action} '{node.name}'"

    def require_permission(self, node: FileNode, permission: str) -> str:
        return self.permission_error(node, permission) or ""

    def read_node(self, node: FileNode):
        """Read a regular file after applying the current simulated identity."""
        from game.InputBuffer import InputBuffer

        if node.get_type() != NodeType.FILE:
            return "Not a regular file"
        if error := self.permission_error(node, "r"):
            return error
        return InputBuffer.from_file(node)

    def write_node(
        self, node: FileNode, data: list[str], *, append: bool = False
    ) -> str:
        """Write or append to a regular file after checking its mode bits."""
        if node.get_type() != NodeType.FILE:
            return "Not a regular file"
        if error := self.permission_error(node, "w"):
            return error
        if append:
            node.append_data(data)
        else:
            node.set_data(data)
        return ""

    def can_chmod(self, node: FileNode) -> bool:
        return self.identity.privileged or self.identity.username == node.inode.owner

    def change_permissions(
        self, node: FileNode, updated: dict, recurse: bool = False
    ) -> tuple[list[str], list[str]]:
        selected: list[FileNode] = []
        errors: list[str] = []
        pending = [node]
        visited: set[int] = set()
        while pending:
            current = pending.pop()
            if id(current) in visited:
                errors.append("chmod: filesystem cycle detected")
                continue
            visited.add(id(current))
            if current.get_type() == NodeType.SYMLINK:
                continue
            if not self.can_chmod(current):
                errors.append(
                    f"chmod: changing permissions of '{current.name}': Operation not permitted"
                )
                continue
            selected.append(current)
            if recurse and current.get_type() == NodeType.DIRECTORY:
                if not self.identity.privileged:
                    denied = next(
                        (
                            self.permission_error(current, permission)
                            for permission in ("r", "x")
                            if self.permission_error(current, permission)
                        ),
                        None,
                    )
                    if denied:
                        errors.append(f"chmod: {denied}")
                        continue
                pending.extend(reversed(current.items))
        changes: list[str] = []
        for current in selected:
            changes.extend(current.update_permissions(updated, recurse=False))
        return changes, errors

    def change_ownership(
        self, node: FileNode, owner: str, group: str, recurse: bool = False
    ) -> list[str]:
        if not self.identity.privileged:
            return ["chown: Operation not permitted"]
        pending = [node]
        visited: set[int] = set()
        while pending:
            current = pending.pop()
            if id(current) in visited:
                return ["chown: filesystem cycle detected"]
            visited.add(id(current))
            if current.get_type() == NodeType.SYMLINK:
                continue
            current.inode.owner = owner
            current.inode.group = group
            current.inode.ctime = datetime.now()
            if recurse and current.get_type() == NodeType.DIRECTORY:
                pending.extend(reversed(current.items))
        return []

    def _stamp_owner(self, inode: Inode, parent: FileNode | None = None) -> None:
        inode.owner = self.identity.username
        inode.group = parent.inode.group if parent is not None else self.identity.primary_group

    def create_child(
        self, parent: FileNode, name: str, inode: Inode, *, stamp_owner: bool = True
    ) -> str:
        for permission in ("w", "x"):
            if error := self.permission_error(parent, permission):
                return error
        if stamp_owner:
            self._stamp_owner(inode, parent)
        return parent.add_child(name, inode)

    def _can_recurse_delete(self, node: FileNode) -> str | None:
        pending = [node]
        visited: set[int] = set()
        while pending:
            current = pending.pop()
            if current.get_type() != NodeType.DIRECTORY:
                continue
            if id(current) in visited:
                return "Filesystem cycle detected"
            visited.add(id(current))
            for permission in ("r", "w", "x"):
                if error := self.permission_error(current, permission):
                    return error
            pending.extend(
                child
                for child in current.items
                if child.get_type() == NodeType.DIRECTORY
            )
        return None

    def to_dict(self) -> dict:
        return {"lcs": self.lcs, "nodes": self.filehead.to_dict()}

    def from_dict(self, fs: dict) -> None:
        try:
            root = FileNode(None, "root", Inode(NodeType.DIRECTORY))
            inodes: dict[int, Inode] = {}
            root.from_dict(fs["nodes"], 0, None, inodes)

            # Count directory entries rather than trusting saved counts, which
            # are absent in old saves and can be stale after link deletion.
            counts = {inode_id: 0 for inode_id in inodes}

            def count_links(node: FileNode) -> None:
                counts[node.inode.id] += 1
                for child in node.items:
                    count_links(child)

            count_links(root)
            for inode_id, inode in inodes.items():
                inode.link_count = counts[inode_id]

            self.lcs = fs["lcs"]
            self.filehead = root
            self.current = root
            self.cwd = "/"
        except Exception as err:
            raise Exception("Syncronization failure") from err

    def get_file(self, path: str) -> FileNode | str | None:
        resolved_parent = self.resolve_parent(path)
        if isinstance(resolved_parent, str):
            return resolved_parent
        parent, name = resolved_parent
        return parent.access(name)

    def list_files(
        self,
        path: str,
        deep: int = 0,
        detail: int = 0,
        extras: dict[str, bool | str] | None = None,
    ) -> list[list[str]] | str:
        node = self.current if path == "" else self.resolve(path)
        if isinstance(node, str):
            return node
        if node.get_type() == NodeType.DIRECTORY:
            for permission in ("r", "x"):
                if error := self.permission_error(node, permission):
                    return error
        if deep:
            pending = [node]
            visited: set[int] = set()
            while pending:
                directory = pending.pop()
                if id(directory) in visited:
                    return "Filesystem cycle detected"
                visited.add(id(directory))
                for child in directory.items:
                    if child.get_type() == NodeType.DIRECTORY:
                        for permission in ("r", "x"):
                            if error := self.permission_error(child, permission):
                                return error
                        pending.append(child)
        display_path = path if node.get_type() != NodeType.DIRECTORY else ""
        return node.list_content(display_path, deep, detail, extras)

    def _resolve(
        self,
        path: str,
        start: FileNode,
        seen_links: set[int],
        creating: bool = False,
    ) -> FileNode | PathResolutionError:
        node = self.filehead if path.startswith("/") else start
        if path == "":
            return node
        for part in path.split("/"):
            if node.get_type() != NodeType.DIRECTORY:
                return PathResolutionError(
                    path, f"{node.name} is not a directory", "not_directory"
                )
            if error := self.permission_error(node, "x"):
                return PathResolutionError(path, error, "permission_denied")
            if part in ("", "."):
                continue
            if part == "..":
                node = node.parent or node
                continue
            child = node.access(part)
            if child is None and creating:
                error = self.create_child(node, part, Inode(NodeType.DIRECTORY))
                if error:
                    return PathResolutionError(path, error, "permission_denied")
                child = node.access(part)
            if child is None:
                return PathResolutionError(
                    path, f"No directory named {part}", "missing"
                )
            if child.get_type() == NodeType.SYMLINK:
                if child.inode.id in seen_links:
                    return PathResolutionError(
                        path, "Too many levels of symbolic links", "symlink_loop"
                    )
                target_path = child.inode.symlink_target
                if target_path is None and child.inode.data:
                    # Older callers and save files stored the target in data.
                    target_path = child.inode.data[0]
                if target_path is None:
                    return PathResolutionError(
                        path, f"Invalid symbolic link: {child.name}", "invalid_symlink"
                    )
                target = self._resolve(
                    target_path, node, seen_links | {child.inode.id}, creating
                )
                if isinstance(target, PathResolutionError):
                    if target.code == "missing":
                        return PathResolutionError(
                            path,
                            f"Dangling symbolic link: {child.name}",
                            "dangling_symlink",
                        )
                    return PathResolutionError(path, str(target), target.code)
                node = target
            else:
                node = child
        return node

    def resolve(self, path: str) -> FileNode | PathResolutionError:
        """Resolve a path without changing the current directory."""
        return self._resolve(path, self.current, set())

    def display_path(self, node: FileNode) -> str:
        """Return a canonical absolute path, with the filesystem root as '/'."""
        parts = []
        while node.parent is not None:
            parts.append(node.name)
            node = node.parent
        return "/" + "/".join(reversed(parts))

    def search(self, path: str, creating: bool = False) -> str:
        """Validate a path without changing cwd or creating filesystem entries."""
        node = self._resolve(path, self.current, set())
        if isinstance(node, PathResolutionError):
            return str(node)
        return ""

    def search_withaccess(self, path: str, creating: bool = False) -> NodeType | None:
        parent_path, name = posixpath.split(path)
        parent = self.resolve(parent_path or ".")
        if isinstance(parent, str) or parent.get_type() != NodeType.DIRECTORY:
            return None
        item = parent.access(name)
        if item is None:
            return None
        return item.get_type()

    def add(self, path: str) -> str:
        if "." in path:
            return self.add_file(path)
        else:
            return self.add_directory(path)

    def add_directory(
        self, path: str, creating: bool = False, permissions: dict | None = None
    ) -> str:
        if permissions is None:
            permissions = {
                "user": {"r": True, "w": True, "x": True},
                "group": {"r": True, "w": True, "x": True},
                "public": {"r": True, "w": True, "x": True},
            }
        if path == "." or path == "/":
            return ""
        parent_path, name = posixpath.split(path)
        if name in ("", ".", ".."):
            return f"Invalid filename: {path}"
        parent = self._resolve(parent_path or ".", self.current, set(), creating)
        if isinstance(parent, PathResolutionError):
            return str(parent)
        if parent.get_type() != NodeType.DIRECTORY:
            return f"{parent_path} is a file"
        inode = Inode(NodeType.DIRECTORY)
        inode.permissions = permissions
        return self.create_child(parent, name, inode)

    def add_file(self, path: str, fn: FileNode | None = None):
        parent_path, name = posixpath.split(path)
        if name in ("", ".", ".."):
            return f"Invalid filename: {path}"
        parent = self.resolve(parent_path or ".")
        if isinstance(parent, PathResolutionError):
            return str(parent)
        if parent.get_type() != NodeType.DIRECTORY:
            return f"{parent_path} is not a directory"
        if fn is None:
            inode = Inode(NodeType.FILE)
            return self.create_child(parent, name, inode)
        else:
            return self.create_child(parent, fn.name, fn.inode, stamp_owner=False)

    def delete(self, path: str, recursive: bool = False) -> FileNode | str:
        parent_info = self.resolve_parent(path.rstrip("/"))
        if isinstance(parent_info, str):
            return str(parent_info)
        parent, name = parent_info
        for permission in ("w", "x"):
            if error := self.permission_error(parent, permission):
                return error
        target = parent.access(name)
        if target is not None and recursive:
            if error := self._can_recurse_delete(target):
                return error
        result = parent.delete_child(name, recurse=recursive)

        if result == "":
            return f"cannot remove '{path}': No such file or directory"
        if result == "dir":
            return f"cannot remove '{path}': Is a directory"
        return result

    def resolve_parent(self, path: str) -> tuple[FileNode, str] | str:
        parent_path, filename = posixpath.split(path)

        if filename in ("", ".", ".."):
            return PathResolutionError(path, f"Invalid filename: {path}", "invalid")

        parent = self.resolve(parent_path or ".")

        if isinstance(parent, str):
            return parent

        if parent.get_type() != NodeType.DIRECTORY:
            return PathResolutionError(
                path, f"{parent_path} is not a directory", "not_directory"
            )

        return parent, filename


"""
f = FileSystem()
f.setup_system("filesystems/example.txt")
print (f.list_files("", 1))
content = f.tree()
for p in content:
    print ("".join(p))
"""
