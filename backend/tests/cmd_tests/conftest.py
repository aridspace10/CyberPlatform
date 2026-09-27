"""Shared fixtures for command tests."""

import pytest
from game.inode import NodeType
from tests.cmd_tests.creation_helpers import child


@pytest.fixture
def creation_shell(shell_empty):
    root = shell_empty.fs.filehead
    work = child(root, "work", NodeType.DIRECTORY)
    parent = child(work, "parent", NodeType.DIRECTORY)
    child(root, "other", NodeType.DIRECTORY)
    child(parent, "keep.txt", NodeType.FILE).inode.data = ["keep nested content"]
    child(work, "existing.txt", NodeType.FILE).inode.data = ["keep existing content"]
    child(work, "blocker", NodeType.FILE).inode.data = ["not a directory"]
    shell_empty.fs.current = work
    shell_empty.fs.cwd = "/work"
    shell_empty.cwd = "/work"
    return shell_empty


@pytest.fixture
def run_creation(cl, creation_shell):
    def run(command):
        fs = creation_shell.fs
        before_current = fs.current
        before_fs_cwd = fs.cwd
        before_shell_cwd = creation_shell.cwd
        result = cl.enter_command(command, creation_shell)
        assert fs.current is before_current, f"{command!r} changed fs.current"
        assert fs.cwd == before_fs_cwd, f"{command!r} changed fs.cwd"
        assert creation_shell.cwd == before_shell_cwd, f"{command!r} changed shell.cwd"
        return result

    return run
