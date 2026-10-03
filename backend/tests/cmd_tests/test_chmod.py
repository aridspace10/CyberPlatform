from copy import deepcopy

import pytest
from game.filenode import FileNode
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_tree, descendants, tree_state
from tests.command_helpers import assert_help


@pytest.mark.parametrize("option", ["", "-R"])
def test_chmod_dot_paths_change_only_target_permissions(
    run_dot_command, dot_shell, dot_directory, option
):
    operand, target = dot_directory
    nodes = assert_tree(dot_shell)
    original_tree = tree_state(dot_shell, include_permissions=False)
    before = {id(node): deepcopy(node.inode.permissions) for node in nodes}
    selected = list(descendants(target)) if option else [target]
    selected_ids = {id(node) for node in selected}
    result = run_dot_command(f"chmod {option} 700 {operand}", unchanged=False)
    assert tree_state(dot_shell, include_permissions=False) == original_tree
    expected = {
        "user": {"r": True, "w": True, "x": True},
        "group": {"r": False, "w": False, "x": False},
        "public": {"r": False, "w": False, "x": False},
    }
    for node in nodes:
        assert node.inode.permissions == (
            expected if id(node) in selected_ids else before[id(node)]
        )
    assert_success(result)


def test_chmod_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    assert_failure(run_dot_command(f"chmod 700 {invalid_dot_path}"))


def test_chmod_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("chmod 000 f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    fn = shell_basic.fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    assert shell_basic.fs.current.get_permission_str(fn) == "----------"
    CmdResult = cl.enter_command("chmod 777 f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    fn = shell_basic.fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    assert shell_basic.fs.current.get_permission_str(fn) == "-rwxrwxrwx"
    CmdResult = cl.enter_command("chmod -Rv 000 d1", shell_basic)
    assert CmdResult.stdout == [
        "Updated permissions of d1 with d---------",
        "Updated permissions of f3.txt with ----------",
        "Updated permissions of f4.txt with ----------",
    ]
    assert CmdResult.stderr == []
    fn = shell_basic.fs.get_file("d1")
    assert isinstance(fn, FileNode)
    assert shell_basic.fs.current.get_permission_str(fn) == "d---------"
    assert isinstance(fn.items[0], FileNode)
    assert fn.get_permission_str(fn.items[0]) == "----------"


def test_chmod_errors(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("chmod -y 888 not_exist.txt", shell_basic)
    assert CmdResult.stderr == ["chmod: Unknown output given"]
    assert CmdResult.stdout == []
    CmdResult = cl.enter_command("chmod 777 not_exist.txt", shell_basic)
    assert CmdResult.stderr == ["chmod: No directory named not_exist.txt"]
    assert CmdResult.stdout == []
    CmdResult = cl.enter_command("chmod 888 f1.txt", shell_basic)
    assert CmdResult.stderr == ["chmod: value given which is higher then needed"]
    assert CmdResult.stdout == []
    CmdResult = cl.enter_command("chmod f1.txt", shell_basic)
    assert CmdResult.stderr == ["chmod: expected at least two arguments"]
    assert CmdResult.stdout == []
    CmdResult = cl.enter_command("chmod 21 f1.txt", shell_basic)
    assert CmdResult.stderr == [
        "chmod: value given for permissions which is not of length of 3"
    ]
    assert CmdResult.stdout == []
    CmdResult = cl.enter_command("chmod 6a5 f1.txt", shell_basic)
    assert CmdResult.stderr == [
        "chmod: value other then given integer given for permissions"
    ]
    assert CmdResult.stdout == []


def test_chmod_help(cl, shell_empty):
    assert_help(cl, shell_empty, "chmod")
