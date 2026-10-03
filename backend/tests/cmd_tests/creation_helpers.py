"""Shared filesystem setup and assertions for command regression tests."""

from datetime import datetime

from game.filenode import FileNode
from game.inode import Inode

OLD_ATIME = datetime(2001, 1, 2, 3, 4, 5)
OLD_MTIME = datetime(2002, 2, 3, 4, 5, 6)
REQUESTED_TIME = datetime(2024, 2, 29)


def child(parent, name, node_type):
    """Build fixtures without exercising the add_file/add_directory subjects."""
    assert parent.add_child(name, Inode(node_type)) == ""
    node = parent.access(name)
    assert isinstance(node, FileNode)
    node.inode.atime = OLD_ATIME
    node.inode.mtime = OLD_MTIME
    return node


def node_at(shell, path):
    """Inspect a root-relative path without lookup side effects or atime reads."""
    node = shell.fs.filehead
    for name in path.strip("/").split("/"):
        if node is None:
            return None
        node = node.access(name)
    return node


def assert_success(result, stdout=None):
    assert result.stderr == []
    assert result.stdout == ([] if stdout is None else stdout)
    assert result.status == 0


def assert_failure(result):
    assert result.stderr, "A failed command must explain the error"
    assert result.stdout == []
    assert result.status != 0


def assert_created(shell, path, node_type):
    node = node_at(shell, path)
    assert isinstance(node, FileNode), f"{path} was not created"
    assert node.inode.type == node_type
    parent_path, _, _ = path.rpartition("/")
    parent = node_at(shell, parent_path) if parent_path else shell.fs.filehead
    assert node.parent is parent
    assert sum(item.name == node.name for item in parent.items) == 1
    return node
