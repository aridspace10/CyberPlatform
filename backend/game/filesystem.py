import posixpath

from game.filenode import FileNode
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
            if part in ("", "."):
                continue
            if part == "..":
                node = node.parent or node
                continue
            child = node.access(part)
            if child is None and creating:
                node.add_child(part, Inode(NodeType.DIRECTORY))
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
        node = self._resolve(path, self.current, set(), creating)
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
            permissions = {}
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
        return parent.add_child(name, inode)

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
            return parent.add_child(name, inode)
        else:
            return parent.add_child(fn.name, fn.inode)

    def delete(self, path: str, recursive: bool = False) -> FileNode | str:
        parent_info = self.resolve_parent(path.rstrip("/"))
        if isinstance(parent_info, str):
            return str(parent_info)
        parent, name = parent_info
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
