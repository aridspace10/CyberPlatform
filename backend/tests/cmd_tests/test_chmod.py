from copy import deepcopy
from datetime import datetime

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


def test_chmod_help_describes_supported_numeric_scope(cl, shell_empty):
    result = cl.enter_command("chmod --help", shell_empty)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout
    help_text = "".join(result.stdout)
    assert "OCTAL-MODE" in help_text
    assert "--recursive" in help_text
    assert "--verbose" in help_text
    assert "--reference" not in help_text
    assert "Each MODE is of the form" not in help_text


def test_chmod_applies_one_numeric_mode_to_every_target(cl, shell_basic):
    first = shell_basic.fs.filehead.access("f1.txt")
    second = shell_basic.fs.filehead.access("f2.txt")
    untouched = shell_basic.fs.filehead.access("d1")
    assert all(isinstance(node, FileNode) for node in (first, second, untouched))

    original_current = shell_basic.fs.current
    original_cwd = shell_basic.cwd
    original_fs_cwd = shell_basic.fs.cwd
    before_data = [list(node.inode.data) for node in (first, second)]
    before_mtime = [node.inode.mtime for node in (first, second)]
    untouched_permissions = deepcopy(untouched.inode.permissions)

    result = cl.enter_command("chmod 640 f1.txt f2.txt", shell_basic)

    assert_success(result)
    assert first.get_permission_str(first) == "-rw-r-----"
    assert second.get_permission_str(second) == "-rw-r-----"
    assert untouched.inode.permissions == untouched_permissions
    assert [node.inode.data for node in (first, second)] == before_data
    assert [node.inode.mtime for node in (first, second)] == before_mtime
    assert shell_basic.fs.current is original_current
    assert shell_basic.cwd == original_cwd
    assert shell_basic.fs.cwd == original_fs_cwd


@pytest.mark.parametrize("command", ["chmod", "chmod -R", "chmod 644", "chmod -R 644"])
def test_chmod_missing_mode_or_target_returns_command_error(cl, shell_basic, command):
    target = shell_basic.fs.filehead.access("f1.txt")
    original_permissions = deepcopy(target.inode.permissions)

    result = cl.enter_command(command, shell_basic)

    assert_failure(result)
    assert target.inode.permissions == original_permissions


@pytest.mark.parametrize("mode", ["888", "6a5", "21"])
def test_chmod_invalid_mode_rejects_all_targets_without_changes(cl, shell_basic, mode):
    nodes = [shell_basic.fs.filehead.access(name) for name in ("f1.txt", "f2.txt")]
    before = [deepcopy(node.inode.permissions) for node in nodes]

    result = cl.enter_command(f"chmod {mode} f1.txt f2.txt", shell_basic)

    assert_failure(result)
    assert [node.inode.permissions for node in nodes] == before


def test_chmod_continues_after_missing_target_and_reports_failure(cl, shell_basic):
    first = shell_basic.fs.filehead.access("f1.txt")
    second = shell_basic.fs.filehead.access("f2.txt")

    result = cl.enter_command("chmod 600 f1.txt missing.txt f2.txt", shell_basic)

    assert_failure(result)
    assert any("missing.txt" in error for error in result.stderr)
    assert first.get_permission_str(first) == "-rw-------"
    assert second.get_permission_str(second) == "-rw-------"


def test_chmod_recursive_verbose_mode_handles_multiple_targets(cl, shell_basic):
    root = shell_basic.fs.filehead
    file = root.access("f1.txt")
    directory = root.access("d1")
    nested_files = list(directory.items)

    result = cl.enter_command("chmod -Rv 750 f1.txt d1", shell_basic)

    assert result.status == 0
    assert result.stderr == []
    assert file.get_permission_str(file) == "-rwxr-x---"
    assert directory.get_permission_str(directory) == "drwxr-x---"
    assert all(
        child.get_permission_str(child) == "-rwxr-x---" for child in nested_files
    )
    assert len(result.stdout) == 2 + len(nested_files)


def test_chmod_updates_shared_inode_ctime_without_changing_content_or_mtime(
    cl, shell_basic
):
    source = shell_basic.fs.filehead.access("f1.txt")
    assert_success(cl.enter_command("ln f1.txt linked.txt", shell_basic))
    link = shell_basic.fs.filehead.access("linked.txt")
    assert source.inode is link.inode

    old_ctime = datetime(2000, 1, 1)
    source.inode.ctime = old_ctime
    before_mtime = source.inode.mtime
    before_data = list(source.inode.data)

    result = cl.enter_command("chmod 600 linked.txt", shell_basic)

    assert_success(result)
    assert source.inode.ctime > old_ctime
    assert link.inode.ctime == source.inode.ctime
    assert source.get_permission_str(source) == "-rw-------"
    assert link.get_permission_str(link) == "-rw-------"
    assert source.inode.mtime == before_mtime
    assert source.inode.data == before_data


def test_chmod_recursive_updates_descendant_inode_ctimes(cl, shell_basic):
    directory = shell_basic.fs.filehead.access("d1")
    descendants_before = list(descendants(directory))
    old_ctime = datetime(2000, 1, 1)
    original_data = [list(node.inode.data) for node in descendants_before]
    original_mtime = [node.inode.mtime for node in descendants_before]
    for node in descendants_before:
        node.inode.ctime = old_ctime

    result = cl.enter_command("chmod -R 700 d1", shell_basic)

    assert_success(result)
    assert all(node.inode.ctime > old_ctime for node in descendants_before)
    assert [node.inode.data for node in descendants_before] == original_data
    assert [node.inode.mtime for node in descendants_before] == original_mtime


def test_chmod_recursive_skips_symbolic_links(cl, shell_basic):
    assert_success(cl.enter_command("ln -s f1.txt d1/link", shell_basic))
    directory = shell_basic.fs.filehead.access("d1")
    link = directory.access("link")
    external_file = shell_basic.fs.filehead.access("f1.txt")
    old_ctime = datetime(2000, 1, 1)
    link.inode.ctime = old_ctime
    link_permissions = deepcopy(link.inode.permissions)
    external_permissions = deepcopy(external_file.inode.permissions)

    result = cl.enter_command("chmod --recursive --verbose 700 d1", shell_basic)

    assert result.status == 0
    assert result.stderr == []
    assert all("link" not in line for line in result.stdout)
    assert link.inode.ctime == old_ctime
    assert link.inode.permissions == link_permissions
    assert external_file.inode.permissions == external_permissions
