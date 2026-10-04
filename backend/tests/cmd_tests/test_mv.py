import pytest
from game.filenode import FileNode
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.command_helpers import assert_help


def test_mv_dot_paths_source_and_destination(run_dot_command, dot_shell, dot_prefix):
    current = dot_shell.fs.current
    source = current.access("data.txt")
    inode = source.inode
    result = run_dot_command(
        f"mv {dot_prefix}data.txt {dot_prefix}moved.txt", unchanged=False
    )
    assert current.access("data.txt") is None
    moved = current.access("moved.txt")
    assert moved is not None
    assert moved.inode is inode
    assert moved.parent is current
    assert moved.inode.data == ["beta:2", "alpha:1", "alpha:1"]
    assert_success(result)


def test_mv_dot_paths_destination_directory(run_dot_command, dot_shell, dot_directory):
    operand, destination = dot_directory
    branch = dot_shell.fs.current.access("branch")
    inode = branch.access("leaf.txt").inode
    if destination is branch:
        assert_failure(run_dot_command(f"mv ./branch/leaf.txt {operand}"))
        return
    result = run_dot_command(f"mv ./branch/leaf.txt {operand}", unchanged=False)
    assert branch.access("leaf.txt") is None
    moved = destination.access("leaf.txt")
    assert moved is not None
    assert moved.parent is destination
    assert moved.inode is inode
    assert_success(result)


@pytest.mark.parametrize(
    "arguments",
    [". ./renamed", ".. ./renamed", "./branch .", "./branch ./branch/../branch"],
)
def test_mv_dot_paths_reject_reserved_source_or_self_move(run_dot_command, arguments):
    assert_failure(run_dot_command(f"mv {arguments}"))


def test_mv_dot_paths_reject_invalid_source(run_dot_command, invalid_dot_path):
    assert_failure(run_dot_command(f"mv {invalid_dot_path} ./moved.txt"))


def test_mv_dot_paths_reject_invalid_destination(run_dot_command, invalid_dot_path):
    assert_failure(run_dot_command(f"mv ./data.txt {invalid_dot_path}"))


@pytest.mark.parametrize(
    ("source", "target", "node_name"),
    [
        ("data.txt", "archive", "data.txt"),
        ("branch", "archive.txt", "branch"),
    ],
)
def test_mv_missing_target_keeps_source_type(
    run_dot_command, dot_shell, source, target, node_name
):
    current = dot_shell.fs.current
    original = current.access(node_name)

    assert_success(run_dot_command(f"mv {source} {target}", unchanged=False))

    assert current.access(node_name) is None
    assert current.access(target) is original
    assert original.parent is current


def test_mv_replaces_existing_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    source = current.access("data.txt")
    old_target = current.access(".hidden")

    assert_success(run_dot_command("mv data.txt .hidden", unchanged=False))

    assert current.access("data.txt") is None
    assert current.access(".hidden") is source
    assert all(item is not old_target for item in current.items)
    assert source.parent is current


@pytest.mark.parametrize(
    "command",
    [
        "mv branch branch/child",
        "mv branch branch/.",
        "mv data.txt branch data.txt",
    ],
)
def test_mv_rejects_invalid_destination_relationship(run_dot_command, command):
    assert_failure(run_dot_command(command))


def test_mv_multiple_sources_keep_parent_links(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    branch = current.access("branch")
    data = current.access("data.txt")
    hidden = current.access(".hidden")

    assert_success(
        run_dot_command("mv ./data.txt ./.hidden ./branch", unchanged=False)
    )

    assert branch.access("data.txt") is data
    assert branch.access(".hidden") is hidden
    assert data.parent is branch
    assert hidden.parent is branch


def test_mv_rename(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("mv f1.txt", shell_basic)
    assert CmdResult.stderr == ["mv: expected at least two arguments"]
    assert CmdResult.stdout == []
    # rename
    CmdResult = cl.enter_command("mv f1.txt abc.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert isinstance(shell_basic.fs.get_file("abc.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)

    CmdResult = cl.enter_command("mv -v abc.txt f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["Renamed abc.txt -> f1.txt"]
    assert isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("abc.txt"), FileNode)

    CmdResult = cl.enter_command("mv abc.txt f4.txt", shell_basic)
    assert CmdResult.stderr == ["mv: could not find file abc.txt"]
    assert CmdResult.stdout == []
    assert not isinstance(shell_basic.fs.get_file("f4.txt"), FileNode)


def test_vm_move_norename(cl, shell_basic: ShellState):
    # move to directory
    CmdResult = cl.enter_command("mv f1.txt d1", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert isinstance(shell_basic.fs.get_file("d1/f1.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)

    CmdResult = cl.enter_command("mv -v f2.txt d1", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["Moved f2.txt to d1"]
    assert isinstance(shell_basic.fs.get_file("d1/f2.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f2.txt"), FileNode)

    CmdResult = cl.enter_command("mv f3.txt d1", shell_basic)
    assert CmdResult.stderr == ["mv: could not find file f3.txt"]
    assert CmdResult.stdout == []


def test_vm_move_multiple(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("mv f1.txt f2.txt d1", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert isinstance(shell_basic.fs.get_file("d1/f1.txt"), FileNode)
    assert isinstance(shell_basic.fs.get_file("d1/f2.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f2.txt"), FileNode)

    CmdResult = cl.enter_command("mv f5.txt f6.txt d1", shell_basic)
    assert CmdResult.stderr == [
        "mv: could not find file f5.txt",
        "mv: could not find file f6.txt",
    ]
    assert CmdResult.stdout == []
    assert not isinstance(shell_basic.fs.get_file("d1/f5.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("d1/f6.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f5.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f6.txt"), FileNode)


def test_vm_move_multiple2(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("mv -v f1.txt f2.txt d1", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["Moved f1.txt to d1", "Moved f2.txt to d1"]
    assert isinstance(shell_basic.fs.get_file("d1/f1.txt"), FileNode)
    assert isinstance(shell_basic.fs.get_file("d1/f2.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f2.txt"), FileNode)


def test_mv_help(cl, shell_empty):
    assert_help(cl, shell_empty, "mv")
