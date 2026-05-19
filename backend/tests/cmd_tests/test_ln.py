import pytest

from game.filesystem import FileSystem
from game.ShellState import ShellState
from game.filenode import FileNode
from game.inode import NodeType
from game.commandline import CommandLine

######## LN ###################
def test_ln_basic(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command('ln f1.txt s1.txt', shell_basic)

    assert CommandResult.stderr == []
    assert CommandResult.stdout == []

    f1 = shell_basic.fs.get_file("f1.txt")
    s1 = shell_basic.fs.get_file("s1.txt")

    assert isinstance(f1, FileNode)
    assert isinstance(s1, FileNode)

    # Initial contents should match
    assert f1.get_data() == s1.get_data()

    # Modifying original updates link
    CommandResult = cl.enter_command('echo "Example" >> f1.txt', shell_basic)

    assert CommandResult.stderr == []
    assert CommandResult.stdout == []

    f1 = shell_basic.fs.get_file("f1.txt")
    s1 = shell_basic.fs.get_file("s1.txt")
    assert isinstance(f1, FileNode)
    assert isinstance(s1, FileNode)

    assert f1.get_data() == s1.get_data()

    # Modifying link updates original
    CommandResult = cl.enter_command('echo "Example2" >> s1.txt', shell_basic)

    assert CommandResult.stderr == []
    assert CommandResult.stdout == []

    f1 = shell_basic.fs.get_file("f1.txt")
    s1 = shell_basic.fs.get_file("s1.txt")

    assert isinstance(f1, FileNode)
    assert isinstance(s1, FileNode)

    assert f1.get_data() == s1.get_data()


def test_ln_nested_directory(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command('ln d1/f3.txt d1/s3.txt', shell_basic)

    assert CommandResult.stderr == []
    assert CommandResult.stdout == []

    f3 = shell_basic.fs.get_file("d1/f3.txt")
    s3 = shell_basic.fs.get_file("d1/s3.txt")

    assert isinstance(f3, FileNode)
    assert isinstance(s3, FileNode)

    assert f3.get_data() == s3.get_data()

    cl.enter_command('echo "HELLO" >> d1/f3.txt', shell_basic)

    assert f3.get_data() == s3.get_data()


def test_ln_existing_target(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command('ln f1.txt f2.txt', shell_basic)

    assert CommandResult.stderr == ["ln: f2.txt: File exists"]
    assert CommandResult.stdout == []

    # Original target should remain unchanged
    f2 = shell_basic.fs.get_file("f2.txt")

    assert isinstance(f2, FileNode)
    assert f2.get_data() == [str(i) for i in range(25)]


def test_ln_missing_source(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command('ln missing.txt s1.txt', shell_basic)

    assert CommandResult.stderr != []
    assert CommandResult.stdout == []

    # Link should not exist
    assert shell_basic.fs.get_file("s1.txt") is None


def test_ln_directory_should_fail(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command('ln d1 s1', shell_basic)

    assert CommandResult.stderr != []
    assert CommandResult.stdout == []


def test_ln_multiple_links_same_inode(cl, shell_basic: ShellState):
    cl.enter_command('ln f1.txt s1.txt', shell_basic)
    cl.enter_command('ln f1.txt s2.txt', shell_basic)

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
    cl.enter_command('ln f1.txt s1.txt', shell_basic)

    f1 = shell_basic.fs.get_file("f1.txt")
    s1 = shell_basic.fs.get_file("s1.txt")

    assert isinstance(f1, FileNode)
    assert isinstance(s1, FileNode)

    # Stronger hard-link check:
    # both file nodes should point to same inode object
    assert f1.inode is s1.inode


def test_ln_chain_links(cl, shell_basic: ShellState):
    cl.enter_command('ln f1.txt s1.txt', shell_basic)
    cl.enter_command('ln s1.txt s2.txt', shell_basic)

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
    CommandResult = cl.enter_command('ln', shell_basic)

    assert CommandResult.stderr != []
    assert CommandResult.stdout == []


def test_ln_one_argument(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command('ln f1.txt', shell_basic)

    assert CommandResult.stderr != []
    assert CommandResult.stdout == []


def test_ln_symbolic_basic(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command(
        'ln -s f1.txt sym1.txt',
        shell_basic
    )

    assert CommandResult.stderr == []
    assert CommandResult.stdout == []

    sym = shell_basic.fs.get_file("sym1.txt")

    assert isinstance(sym, FileNode)

    # Symlink should NOT share inode with original
    original = shell_basic.fs.get_file("f1.txt")

    assert isinstance(original, FileNode)

    assert sym.inode is not original.inode
    assert sym.inode.type == NodeType.SYMLINK

    # Symlink stores target path
    assert sym.inode.get_data() == ["f1.txt"]


def test_ln_symbolic_nested(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command(
        'ln -s d1/f3.txt d1/sym3.txt',
        shell_basic
    )

    assert CommandResult.stderr == []
    assert CommandResult.stdout == []

    sym = shell_basic.fs.get_file("d1/sym3.txt")

    assert isinstance(sym, FileNode)

    assert sym.inode.type == NodeType.SYMLINK
    assert sym.inode.get_data() == ["d1/f3.txt"]


def test_ln_symbolic_directory_allowed(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command(
        'ln -s d1 d1link',
        shell_basic
    )

    assert CommandResult.stderr == []
    assert CommandResult.stdout == []

    link = shell_basic.fs.get_file("d1link")

    assert isinstance(link, FileNode)

    # Symlinks to directories should be allowed
    assert link.inode.type == NodeType.SYMLINK
    assert link.inode.get_data() == ["d1"]


def test_ln_symbolic_does_not_share_inode(cl, shell_basic: ShellState):
    cl.enter_command('ln -s f1.txt sym1.txt', shell_basic)

    original = shell_basic.fs.get_file("f1.txt")
    sym = shell_basic.fs.get_file("sym1.txt")

    assert isinstance(original, FileNode)
    assert isinstance(sym, FileNode)

    assert original.inode is not sym.inode


def test_ln_symbolic_existing_destination(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command(
        'ln -s f1.txt f2.txt',
        shell_basic
    )

    assert CommandResult.stderr != []
    assert CommandResult.stdout == []

    f2 = shell_basic.fs.get_file("f2.txt")

    assert isinstance(f2, FileNode)

    # Existing file should remain unchanged
    assert f2.get_data() == [str(i) for i in range(25)]


def test_ln_symbolic_missing_target_allowed(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command(
        'ln -s missing.txt sym_missing.txt',
        shell_basic
    )

    # POSIX symlinks can point to missing targets
    assert CommandResult.stderr == []
    assert CommandResult.stdout == []

    sym = shell_basic.fs.get_file("sym_missing.txt")

    assert isinstance(sym, FileNode)

    assert sym.inode.type == NodeType.SYMLINK
    assert sym.inode.get_data() == ["missing.txt"]


def test_ln_invalid_option(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command(
        'ln -z f1.txt s1.txt',
        shell_basic
    )

    assert CommandResult.stderr != []
    assert CommandResult.stdout == []

    assert shell_basic.fs.get_file("s1.txt") is None


def test_ln_combined_options(cl, shell_basic: ShellState):
    CommandResult = cl.enter_command(
        'ln -s f1.txt slink.txt',
        shell_basic
    )

    assert CommandResult.stderr == []
    assert CommandResult.stdout == []

    slink = shell_basic.fs.get_file("slink.txt")

    assert isinstance(slink, FileNode)

    assert slink.inode.type == NodeType.SYMLINK


def test_ln_symbolic_multiple(cl, shell_basic: ShellState):
    cl.enter_command('ln -s f1.txt sym1.txt', shell_basic)
    cl.enter_command('ln -s f1.txt sym2.txt', shell_basic)

    sym1 = shell_basic.fs.get_file("sym1.txt")
    sym2 = shell_basic.fs.get_file("sym2.txt")

    assert isinstance(sym1, FileNode)
    assert isinstance(sym2, FileNode)

    # Different symlink inodes
    assert sym1.inode is not sym2.inode

    # But same target path
    assert sym1.inode.get_data() == ["f1.txt"]
    assert sym2.inode.get_data() == ["f1.txt"]