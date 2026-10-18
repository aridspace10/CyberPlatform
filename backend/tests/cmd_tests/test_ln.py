import pytest
from game.filenode import FileNode
from game.inode import NodeType
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.command_helpers import assert_help
from tests.filesystem_helpers import restored_filesystem


######## LN ###################
def test_ln_basic(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln f1.txt s1.txt", shell_basic)

    assert cmd.stderr == []
    assert cmd.stdout == []

    f1 = shell_basic.fs.get_file("f1.txt")
    s1 = shell_basic.fs.get_file("s1.txt")

    assert isinstance(f1, FileNode)
    assert isinstance(s1, FileNode)

    # Initial contents should match
    assert f1.get_data() == s1.get_data()

    # Modifying original updates link
    cmd = cl.enter_command('echo "Example" >> f1.txt', shell_basic)

    assert cmd.stderr == []
    assert cmd.stdout == []

    f1 = shell_basic.fs.get_file("f1.txt")
    s1 = shell_basic.fs.get_file("s1.txt")
    assert isinstance(f1, FileNode)
    assert isinstance(s1, FileNode)

    assert f1.get_data() == s1.get_data()

    # Modifying link updates original
    cmd = cl.enter_command('echo "Example2" >> s1.txt', shell_basic)

    assert cmd.stderr == []
    assert cmd.stdout == []

    f1 = shell_basic.fs.get_file("f1.txt")
    s1 = shell_basic.fs.get_file("s1.txt")

    assert isinstance(f1, FileNode)
    assert isinstance(s1, FileNode)

    assert f1.get_data() == s1.get_data()


def test_ln_hard_link_survives_filesystem_restore(cl, shell_basic: ShellState):
    assert_success(cl.enter_command("ln f1.txt h.txt", shell_basic))
    shell_basic.fs = restored_filesystem(shell_basic.fs)

    source = shell_basic.fs.get_file("f1.txt")
    link = shell_basic.fs.get_file("h.txt")
    assert source.inode is link.inode
    assert source.inode.link_count == 2

    assert_success(cl.enter_command('echo "after restore" >> h.txt', shell_basic))
    assert source.get_data() == link.get_data()
    assert "after restore" in source.get_data()


def test_ln_nested_directory(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln d1/f3.txt d1/s3.txt", shell_basic)

    assert cmd.stderr == []
    assert cmd.stdout == []

    f3 = shell_basic.fs.get_file("d1/f3.txt")
    s3 = shell_basic.fs.get_file("d1/s3.txt")

    assert isinstance(f3, FileNode)
    assert isinstance(s3, FileNode)

    assert f3.get_data() == s3.get_data()

    cl.enter_command('echo "HELLO" >> d1/f3.txt', shell_basic)

    assert f3.get_data() == s3.get_data()


def test_ln_existing_target(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln f1.txt f2.txt", shell_basic)

    assert cmd.stderr == ["ln: f2.txt: File exists"]
    assert cmd.stdout == []

    # Original target should remain unchanged
    f2 = shell_basic.fs.get_file("f2.txt")

    assert isinstance(f2, FileNode)
    assert f2.get_data() == [str(i) for i in range(25)]


def test_ln_missing_source(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln missing.txt s1.txt", shell_basic)

    assert cmd.stderr != []
    assert cmd.stdout == []

    # Link should not exist
    assert shell_basic.fs.get_file("s1.txt") is None


def test_ln_directory_should_fail(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln d1 s1", shell_basic)

    assert cmd.stderr != []
    assert cmd.stdout == []


def test_ln_multiple_links_same_inode(cl, shell_basic: ShellState):
    cl.enter_command("ln f1.txt s1.txt", shell_basic)
    cl.enter_command("ln f1.txt s2.txt", shell_basic)

    f1 = shell_basic.fs.get_file("f1.txt")
    s1 = shell_basic.fs.get_file("s1.txt")
    s2 = shell_basic.fs.get_file("s2.txt")

    assert isinstance(f1, FileNode)
    assert isinstance(s1, FileNode)
    assert isinstance(s2, FileNode)

    assert f1.get_data() == s1.get_data()
    assert s1.get_data() == s2.get_data()

    cl.enter_command('echo "MULTI" >> s2.txt', shell_basic)

    assert f1.get_data() == s1.get_data()
    assert s1.get_data() == s2.get_data()


def test_ln_preserves_shared_inode_behavior(cl, shell_basic: ShellState):
    cl.enter_command("ln f1.txt s1.txt", shell_basic)

    f1 = shell_basic.fs.get_file("f1.txt")
    s1 = shell_basic.fs.get_file("s1.txt")

    assert isinstance(f1, FileNode)
    assert isinstance(s1, FileNode)

    # Stronger hard-link check:
    # both file nodes should point to same inode object
    assert f1.inode is s1.inode


def test_ln_chain_links(cl, shell_basic: ShellState):
    cl.enter_command("ln f1.txt s1.txt", shell_basic)
    cl.enter_command("ln s1.txt s2.txt", shell_basic)

    f1 = shell_basic.fs.get_file("f1.txt")
    s1 = shell_basic.fs.get_file("s1.txt")
    s2 = shell_basic.fs.get_file("s2.txt")

    assert isinstance(f1, FileNode)
    assert isinstance(s1, FileNode)
    assert isinstance(s2, FileNode)

    assert f1.inode is s1.inode
    assert s1.inode is s2.inode

    cl.enter_command('echo "CHAIN" >> s2.txt', shell_basic)

    assert f1.get_data() == s1.get_data()
    assert s1.get_data() == s2.get_data()


def test_ln_no_arguments(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln", shell_basic)

    assert cmd.stderr != []
    assert cmd.stdout == []


def test_ln_one_argument(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln f1.txt", shell_basic)

    assert cmd.stderr != []
    assert cmd.stdout == []


def test_ln_symbolic_basic(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln -s f1.txt sym1.txt", shell_basic)

    assert cmd.stderr == []
    assert cmd.stdout == []

    sym = shell_basic.fs.get_file("sym1.txt")

    assert isinstance(sym, FileNode)

    # Symlink should NOT share inode with original
    original = shell_basic.fs.get_file("f1.txt")

    assert isinstance(original, FileNode)

    assert sym.inode is not original.inode
    assert sym.inode.type == NodeType.SYMLINK

    # Symlink stores target path
    assert sym.inode.symlink_target == "f1.txt"


def test_ln_symbolic_nested(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln -s d1/f3.txt d1/sym3.txt", shell_basic)

    assert cmd.stderr == []
    assert cmd.stdout == []

    sym = shell_basic.fs.get_file("d1/sym3.txt")

    assert isinstance(sym, FileNode)

    assert sym.inode.type == NodeType.SYMLINK
    assert sym.inode.symlink_target == "d1/f3.txt"


def test_ln_symbolic_directory_allowed(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln -s d1 d1link", shell_basic)

    assert cmd.stderr == []
    assert cmd.stdout == []

    link = shell_basic.fs.get_file("d1link")

    assert isinstance(link, FileNode)

    # Symlinks to directories should be allowed
    assert link.inode.type == NodeType.SYMLINK
    assert link.inode.symlink_target == "d1"


def test_ln_symbolic_does_not_share_inode(cl, shell_basic: ShellState):
    cl.enter_command("ln -s f1.txt sym1.txt", shell_basic)

    original = shell_basic.fs.get_file("f1.txt")
    sym = shell_basic.fs.get_file("sym1.txt")

    assert isinstance(original, FileNode)
    assert isinstance(sym, FileNode)

    assert original.inode is not sym.inode


def test_ln_symbolic_existing_destination(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln -s f1.txt f2.txt", shell_basic)

    assert cmd.stderr != []
    assert cmd.stdout == []

    f2 = shell_basic.fs.get_file("f2.txt")

    assert isinstance(f2, FileNode)

    # Existing file should remain unchanged
    assert f2.get_data() == [str(i) for i in range(25)]


def test_ln_symbolic_missing_target_allowed(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln -s missing.txt sym_missing.txt", shell_basic)

    # POSIX symlinks can point to missing targets
    assert cmd.stderr == []
    assert cmd.stdout == []

    sym = shell_basic.fs.get_file("sym_missing.txt")

    assert isinstance(sym, FileNode)

    assert sym.inode.type == NodeType.SYMLINK
    assert sym.inode.symlink_target == "missing.txt"


def test_ln_invalid_option(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln -z f1.txt s1.txt", shell_basic)

    assert cmd.stderr != []
    assert cmd.stdout == []

    assert shell_basic.fs.get_file("s1.txt") is None


def test_ln_combined_options(cl, shell_basic: ShellState):
    cmd = cl.enter_command("ln -s f1.txt slink.txt", shell_basic)

    assert cmd.stderr == []
    assert cmd.stdout == []

    slink = shell_basic.fs.get_file("slink.txt")

    assert isinstance(slink, FileNode)

    assert slink.inode.type == NodeType.SYMLINK


def test_ln_symbolic_multiple(cl, shell_basic: ShellState):
    cl.enter_command("ln -s f1.txt sym1.txt", shell_basic)
    cl.enter_command("ln -s f1.txt sym2.txt", shell_basic)

    sym1 = shell_basic.fs.get_file("sym1.txt")
    sym2 = shell_basic.fs.get_file("sym2.txt")

    assert isinstance(sym1, FileNode)
    assert isinstance(sym2, FileNode)

    # Different symlink inodes
    assert sym1.inode is not sym2.inode

    # But same target path
    assert sym1.inode.symlink_target == "f1.txt"
    assert sym2.inode.symlink_target == "f1.txt"


def test_ln_help(cl, shell_empty):
    assert_help(cl, shell_empty, "ln")


def test_ln_dot_paths_link_source_and_destination(
    run_dot_command, dot_shell, dot_prefix
):
    current = dot_shell.fs.current
    source = current.access("data.txt")
    count = source.inode.link_count
    result = run_dot_command(
        f"ln {dot_prefix}data.txt {dot_prefix}linked.txt", unchanged=False
    )
    linked = current.access("linked.txt")
    assert linked is not None
    assert linked is not source
    assert linked.parent is current
    assert linked.inode is source.inode
    assert source.inode.link_count == count + 1
    assert_success(result)


def test_ln_dot_paths_reject_directory_hard_link(run_dot_command, dot_directory):
    operand, _ = dot_directory
    assert_failure(run_dot_command(f"ln {operand} ./linked.txt"))


def test_ln_dot_paths_reject_invalid_source(run_dot_command, invalid_dot_path):
    assert_failure(run_dot_command(f"ln {invalid_dot_path} ./linked.txt"))


def test_ln_dot_paths_reject_invalid_destination(run_dot_command, invalid_dot_path):
    assert_failure(run_dot_command(f"ln ./data.txt {invalid_dot_path}"))


@pytest.mark.parametrize("target", [".", "..", "../data.txt"])
def test_ln_dot_paths_symbolic_target_stays_literal(run_dot_command, dot_shell, target):
    branch = dot_shell.fs.current.access("branch")
    result = run_dot_command(f"ln -s {target} ./branch/link", unchanged=False)
    linked = branch.access("link")
    assert linked is not None
    assert linked.parent is branch
    assert linked.inode.type.value == "symlink"
    assert linked.inode.symlink_target == target
    assert_success(result)


def test_symbolic_links_resolve_relative_nested_and_chained_targets(cl, shell_basic):
    assert_success(cl.enter_command("ln -s ../f1.txt d1/relative", shell_basic))
    assert_success(cl.enter_command("ln -s d1/relative chained", shell_basic))
    result = cl.enter_command("cat chained", shell_basic)
    assert result.stderr == []
    assert result.stdout == shell_basic.fs.get_file("f1.txt").get_data()
    assert shell_basic.fs.resolve("d1/relative").name == "f1.txt"

    current = shell_basic.fs.resolve("d1")
    shell_basic.fs.current = current
    shell_basic.fs.cwd = "/d1"
    shell_basic.cwd = "/d1"
    assert shell_basic.fs.resolve("relative").name == "f1.txt"
    assert shell_basic.fs.current is current
    assert shell_basic.fs.cwd == shell_basic.cwd == "/d1"


def test_symbolic_links_resolve_absolute_targets_and_intermediate_directories(
    cl, shell_basic
):
    assert_success(cl.enter_command("ln -s /d1 dirlink", shell_basic))
    assert_success(cl.enter_command("ln -s /f1.txt absolute", shell_basic))
    assert shell_basic.fs.resolve("dirlink/f3.txt").name == "f3.txt"
    assert shell_basic.fs.resolve("absolute").name == "f1.txt"


def test_grep_reads_through_symbolic_link(cl, shell_basic):
    assert_success(cl.enter_command("ln -s f1.txt readable", shell_basic))
    expected = cl.enter_command("grep ERROR f1.txt", shell_basic)
    actual = cl.enter_command("grep ERROR readable", shell_basic)
    assert actual.stdout == expected.stdout
    assert actual.stderr == expected.stderr == []


def test_symbolic_link_cycle_and_dangling_errors_are_deterministic(cl, shell_basic):
    assert_success(cl.enter_command("ln -s loop-b loop-a", shell_basic))
    assert_success(cl.enter_command("ln -s loop-a loop-b", shell_basic))
    assert shell_basic.fs.resolve("loop-a") == "Too many levels of symbolic links"

    assert_success(cl.enter_command("ln -s absent dangling", shell_basic))
    assert shell_basic.fs.resolve("dangling").startswith("Dangling symbolic link:")


def test_unlink_symlink_removes_link_not_target(cl, shell_basic):
    assert_success(cl.enter_command("ln -s f1.txt sym", shell_basic))
    target = shell_basic.fs.get_file("f1.txt")
    assert_success(cl.enter_command("rm sym", shell_basic))
    assert shell_basic.fs.get_file("sym") is None
    assert shell_basic.fs.get_file("f1.txt") is target


def test_unlink_hard_link_decrements_shared_inode_count(cl, shell_basic):
    assert_success(cl.enter_command("ln f1.txt hard", shell_basic))
    source = shell_basic.fs.get_file("f1.txt")
    assert source.inode.link_count == 2
    assert_success(cl.enter_command("rm hard", shell_basic))
    assert source.inode.link_count == 1
    assert shell_basic.fs.get_file("f1.txt") is source


def test_recursive_directory_removal_releases_descendant_inode_links(cl, shell_basic):
    assert_success(cl.enter_command("ln f1.txt d1/hard", shell_basic))
    source = shell_basic.fs.get_file("f1.txt")
    assert source.inode.link_count == 2
    assert_success(cl.enter_command("rm -r d1", shell_basic))
    assert source.inode.link_count == 1
