import pytest
from game.filenode import FileNode
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.command_helpers import assert_help


def test_cp_dot_paths_copy_source_and_destination(
    run_dot_command, dot_shell, dot_prefix
):
    current = dot_shell.fs.current
    source = current.access("data.txt")
    result = run_dot_command(
        f"cp {dot_prefix}data.txt {dot_prefix}copy.txt", unchanged=False
    )
    copied = current.access("copy.txt")
    assert copied is not None
    assert copied.parent is current
    assert copied is not source
    assert copied.inode is not source.inode
    assert copied.inode.data == source.inode.data
    assert copied.inode.data is not source.inode.data
    assert_success(result)


def test_cp_dot_paths_destination_directory(run_dot_command, dot_shell, dot_directory):
    operand, destination = dot_directory
    source = dot_shell.fs.current.access("branch").access("leaf.txt")
    if destination is source.parent:
        assert_failure(run_dot_command(f"cp ./branch/leaf.txt {operand}"))
        return
    result = run_dot_command(f"cp ./branch/leaf.txt {operand}", unchanged=False)
    copied = destination.access("leaf.txt")
    assert copied is not None
    assert copied.parent is destination
    assert copied is not source
    assert copied.inode is not source.inode
    assert copied.inode.data == ["leaf:3"]
    assert_success(result)


@pytest.mark.parametrize(
    "arguments",
    [
        "./data.txt branch/../data.txt",
        "-r . ./branch",
        "-r .. .",
        "-r branch/.. ./branch/copy",
    ],
)
def test_cp_dot_paths_reject_self_and_descendant_copies(run_dot_command, arguments):
    assert_failure(run_dot_command(f"cp {arguments}"))


def test_cp_dot_paths_reject_invalid_source(run_dot_command, invalid_dot_path):
    assert_failure(run_dot_command(f"cp {invalid_dot_path} ./copy.txt"))


def test_cp_dot_paths_reject_invalid_destination(run_dot_command, invalid_dot_path):
    assert_failure(run_dot_command(f"cp ./data.txt {invalid_dot_path}"))


def test_cp_basic(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("cp f1.txt copied.txt", shell_fouritems)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == []
    fn = shell_fouritems.fs.get_file("copied.txt")
    assert isinstance(fn, FileNode)
    assert fn.get_data() == ["ERROR 1", "ERROR 2", "INFO 1"]

    CmdResult = cl.enter_command("cp -v f2.txt f3.txt", shell_fouritems)
    assert CmdResult.stdout == ["cp: Copied 'f2.txt' to 'f3.txt'"]
    assert CmdResult.stderr == []
    fn = shell_fouritems.fs.get_file("f3.txt")
    assert isinstance(fn, FileNode)
    assert fn.get_data() == ["ERROR 3", "ERROR 4", "INFO 2"]


def test_cp_directory(cl, shell_cp: ShellState):
    CmdResult = cl.enter_command("cp -vr project project_backup", shell_cp)
    assert CmdResult.stdout == ["cp: Copied 'project' to 'project_backup'"]
    assert CmdResult.stderr == []
    f1 = shell_cp.fs.get_file("project")
    f2 = shell_cp.fs.get_file("project_backup")
    assert isinstance(f1, FileNode) and isinstance(f2, FileNode)
    assert f1.items == f2.items

    CmdResult = cl.enter_command("cp -vr project project2", shell_cp)
    assert CmdResult.stdout == ["cp: Copied 'project' to 'project2'"]
    assert CmdResult.stderr == []
    f1 = shell_cp.fs.get_file("project")
    f2 = shell_cp.fs.get_file("project2/project")
    assert isinstance(f1, FileNode) and isinstance(f2, FileNode)
    assert f1.items == f2.items


def test_cp_file_directory(cl, shell_fouritems: ShellState):
    shell_fouritems.fs.add_directory("d1")
    CmdResult = cl.enter_command("cp f1.txt f2.txt d1", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    f1 = shell_fouritems.fs.get_file("d1")
    f2 = shell_fouritems.fs.get_file("f1.txt")
    f3 = shell_fouritems.fs.get_file("f2.txt")
    f4 = shell_fouritems.fs.get_file("d1/f1.txt")
    f5 = shell_fouritems.fs.get_file("d1/f2.txt")
    assert (
        isinstance(f1, FileNode)
        and isinstance(f2, FileNode)
        and isinstance(f3, FileNode)
    )
    assert len(f1.items) == 2
    assert f2 == f4
    assert f3 == f5


def test_cp_errors(cl, shell_cp: ShellState):
    CmdResult = cl.enter_command("cp project project_backup", shell_cp)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == ["cp: -r not specified; omitting directory 'project'"]

    CmdResult = cl.enter_command("cp -r project f1.txt", shell_cp)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == [
        "cp: cannot overwrite non-directory 'f1.txt' with directory 'project'"
    ]


def test_cp_errors2(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("cp f1.txt f2.txt f12.txt", shell_fouritems)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == ["cp: target 'f12.txt' is not a directory"]


def test_cp_help(cl, shell_empty):
    assert_help(cl, shell_empty, "cp")
