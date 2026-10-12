"""Shared fixtures for command tests."""

import pytest
from game.commandline import CommandResult
from game.inode import Inode, NodeType
from tests.cmd_tests.creation_helpers import child
from tests.cmd_tests.path_helpers import tree_state


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


@pytest.fixture(params=["operand", "redirect", "pipe", "heredoc"])
def run_buffered_command(cl, shell_empty, request):
    """Exercise each input adapter and check that reading cannot edit its source."""

    def run(command, lines):
        source = child(shell_empty.fs.current, "input.txt", NodeType.FILE)
        source.set_data(list(lines))
        before = tree_state(shell_empty)
        mtime = source.inode.mtime
        next_inode = Inode._next_id
        current = shell_empty.fs.current
        fs_cwd, shell_cwd = shell_empty.fs.cwd, shell_empty.cwd

        if request.param == "operand":
            result = cl.enter_command(f"{command} input.txt", shell_empty)
        elif request.param == "redirect":
            result = cl.enter_command(f"{command} - < input.txt", shell_empty)
        elif request.param == "pipe":
            result = cl.enter_command(f"cat input.txt | {command}", shell_empty)
        else:
            result = cl.enter_command(f"{command} << EOF", shell_empty)
            assert result.interaction is not None
            program = cl.process_manager.get_process(shell_empty.foreground_pid).program
            for line in lines:
                assert program.receive_input(line) == ([], [])
            stdout, stderr = program.receive_input("EOF")
            result = CommandResult(1 if stderr else 0, stdout, stderr)

        assert Inode._next_id == next_inode
        assert tree_state(shell_empty) == before
        assert source.inode.mtime == mtime
        assert shell_empty.fs.current is current
        assert shell_empty.fs.cwd == fs_cwd
        assert shell_empty.cwd == shell_cwd
        return result

    return run
