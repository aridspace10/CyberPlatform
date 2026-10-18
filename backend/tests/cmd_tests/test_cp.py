import pytest
from game.identity import EffectiveIdentity
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


def test_cp_requires_source_read_and_destination_parent_write(cl, shell_basic):
    source = shell_basic.fs.filehead.access("f1.txt")
    source.inode.permissions["user"]["r"] = False

    result = cl.enter_command("cp f1.txt copied.txt", shell_basic)

    assert_failure(result)
    assert shell_basic.fs.filehead.access("copied.txt") is None
    source.inode.permissions["user"]["r"] = True
    shell_basic.fs.filehead.inode.permissions["user"]["w"] = False
    result = cl.enter_command("cp f1.txt copied.txt", shell_basic)
    assert_failure(result)
    assert shell_basic.fs.filehead.access("copied.txt") is None


def test_cp_overwrite_preserves_target_inode_metadata_and_hard_links(cl, shell_basic):
    assert_success(cl.enter_command("touch alias.txt", shell_basic))
    assert_success(cl.enter_command("ln alias.txt target.txt", shell_basic))
    source = shell_basic.fs.filehead.access("f1.txt")
    target = shell_basic.fs.filehead.access("target.txt")
    alias = shell_basic.fs.filehead.access("alias.txt")
    target.inode.owner = "alice"
    target.inode.group = "writers"
    target.inode.permissions["group"]["w"] = True
    shell_basic.identity = EffectiveIdentity("bob", "writers", frozenset({"writers"}))
    original_inode = target.inode

    result = cl.enter_command("cp f1.txt target.txt", shell_basic)

    assert_success(result)
    assert target.inode is original_inode
    assert alias.inode is original_inode
    assert target.inode.owner == "alice"
    assert target.inode.group == "writers"
    assert alias.inode.data == source.inode.data


def test_recursive_cp_preserves_links_without_following_targets(cl, shell_basic):
    assert_success(cl.enter_command("ln -s f1.txt d1/link", shell_basic))
    source = shell_basic.fs.filehead.access("f1.txt")
    source.inode.permissions["user"]["r"] = False

    result = cl.enter_command("cp -R d1 copy", shell_basic)

    assert_success(result)
    copied = shell_basic.fs.filehead.access("copy")
    link = copied.access("link")
    assert link.get_type().value == "symlink"
    assert link.inode.symlink_target == "f1.txt"


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
    source = shell_fouritems.fs.get_file("f1.txt")
    assert isinstance(source, FileNode)
    original = source.get_data().copy()
    CmdResult = cl.enter_command("cp f1.txt copied.txt", shell_fouritems)
    assert CmdResult.status == 0
    assert CmdResult.stdout == []
    assert CmdResult.stderr == []
    fn = shell_fouritems.fs.get_file("copied.txt")
    assert isinstance(fn, FileNode)
    assert fn is not source
    assert fn.inode is not source.inode
    assert fn.inode.id != source.inode.id
    assert fn.get_data() == original

    CmdResult = cl.enter_command("echo CHANGED > copied.txt", shell_fouritems)
    assert CmdResult.status == 0
    assert fn.get_data() == ["CHANGED"]
    assert source.get_data() == original

    CmdResult = cl.enter_command("cp -v f2.txt f3.txt", shell_fouritems)
    assert CmdResult.status == 0
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
    assert f2.parent is shell_cp.fs.filehead
    assert f1.items == f2.items
    source_file = shell_cp.fs.get_file("project/files/f1.txt")
    copied_file = shell_cp.fs.get_file("project_backup/files/f1.txt")
    assert isinstance(source_file, FileNode) and isinstance(copied_file, FileNode)
    assert copied_file.parent is shell_cp.fs.get_file("project_backup/files")
    assert copied_file.inode is not source_file.inode
    assert copied_file.inode.id != source_file.inode.id
    copied_file.set_data(["changed in copied tree"])
    assert source_file.get_data() == []

    CmdResult = cl.enter_command("cp -vR project project2", shell_cp)
    assert CmdResult.stdout == ["cp: Copied 'project' to 'project2'"]
    assert CmdResult.stderr == []
    f1 = shell_cp.fs.get_file("project")
    f2 = shell_cp.fs.get_file("project2/project")
    assert isinstance(f1, FileNode) and isinstance(f2, FileNode)
    assert f2.parent is shell_cp.fs.get_file("project2")
    assert f1.items == f2.items
    assert CmdResult.status == 0


def test_cp_refuses_duplicate_names_without_partial_copy(cl, shell_fouritems):
    shell_fouritems.fs.add_directory("d1")
    result = cl.enter_command("cp f1.txt f1.txt d1", shell_fouritems)

    assert_failure(result)
    assert shell_fouritems.fs.get_file("d1").items == []


def test_cp_missing_source_does_not_create_destination(cl, shell_empty):
    result = cl.enter_command("cp missing.txt copied.txt", shell_empty)

    assert_failure(result)
    assert isinstance(shell_empty.fs.resolve("copied.txt"), str)


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
    assert f4.parent is f1
    assert f5.parent is f1


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


def test_cp_does_not_copy_the_current_directory(cl, shell_empty):
    result = cl.enter_command("cp -R . copied", shell_empty)

    assert_failure(result)
    assert isinstance(shell_empty.fs.resolve("copied"), str)


def test_cp_recursive_clone_depth_uses_destination_parent(cl, shell_cp):
    shell_cp.fs.add_directory("destination")
    shell_cp.fs.add_directory("destination/nested")
    destination = shell_cp.fs.get_file("destination/nested")
    source = shell_cp.fs.get_file("project")
    assert isinstance(destination, FileNode) and isinstance(source, FileNode)

    result = cl.enter_command("cp -R project destination/nested", shell_cp)

    copied = shell_cp.fs.get_file("destination/nested/project")
    copied_files = shell_cp.fs.get_file("destination/nested/project/files")
    copied_file = shell_cp.fs.get_file("destination/nested/project/files/f1.txt")
    assert result.status == 0
    assert isinstance(copied, FileNode)
    assert isinstance(copied_files, FileNode)
    assert isinstance(copied_file, FileNode)
    assert copied.depth == destination.depth + 1
    assert copied_files.depth == copied.depth + 1
    assert copied_file.depth == copied_files.depth + 1
