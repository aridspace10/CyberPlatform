"""Independent observations of the simulated filesystem for path regressions.

Never use the production resolver or FileNode.__eq__ as a test oracle: those
are part of the behavior under test, and equality can recurse on a broken tree.
"""

import json

from game.inode import NodeType


def assert_tree(shell):
    """Fail promptly on cycles, reused nodes, reserved names, or bad parents."""
    root = shell.fs.filehead
    seen = set()
    nodes = []
    pending = [(root, None)]
    while pending:
        node, parent = pending.pop()
        assert id(node) not in seen, f"Cycle or reused FileNode: {node.name!r}"
        seen.add(id(node))
        assert node.parent is parent, f"Wrong parent for {node.name!r}"
        if parent is not None:
            assert node.name not in ("", ".", ".."), node.name
            assert "/" not in node.name, f"Path stored as a child name: {node.name!r}"
        names = [item.name for item in node.items]
        assert len(names) == len(set(names)), f"Duplicate children in {node.name!r}"
        if node.inode.type != NodeType.DIRECTORY:
            assert not node.items, f"Non-directory {node.name!r} has children"
        nodes.append(node)
        pending.extend((item, node) for item in reversed(node.items))
    assert id(shell.fs.current) in seen, "Current directory was detached from the tree"
    assert (
        shell.fs.current.inode.type == NodeType.DIRECTORY
    ), "Current directory points at a non-directory"
    # Check serialization only after the bounded walk has ruled out cycles.
    json.dumps(shell.fs.to_dict())
    return nodes


def tree_state(shell, *, include_permissions=True):
    """Capture identity, topology, and data; metadata tests check timestamps."""
    return tuple(
        (
            id(node),
            node.name,
            id(node.parent),
            tuple(id(item) for item in node.items),
            id(node.inode),
            node.inode.id,
            node.inode.type,
            tuple(node.inode.data),
            node.inode.has_trailing_newline,
            node.inode.link_count,
            (
                json.dumps(node.inode.permissions, sort_keys=True)
                if include_permissions
                else None
            ),
        )
        for node in assert_tree(shell)
    )


def canonical_path(node):
    parts = []
    while node.parent is not None:
        parts.append(node.name)
        node = node.parent
    return "/" + "/".join(reversed(parts))


def descendants(node):
    """Only call on fixture trees or after assert_tree has verified integrity."""
    yield node
    for item in node.items:
        yield from descendants(item)


def assert_directory_error(result):
    assert result.status != 0, "Directory operands must fail for file-only commands"
    assert result.stdout == []
    assert result.stderr
    assert any("director" in line.lower() for line in result.stderr), result.stderr
