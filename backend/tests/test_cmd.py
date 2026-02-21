import pytest
from game.commandline import CommandLine
from game.ShellState import ShellState
from game.filesystem import FileSystem
from game.filenode import FileNode, Inode, NodeType

# Basic helpers to create a filesystem with one file
@pytest.fixture
def fs_empty():
    fs = FileSystem()
    # ensure root present and empty
    return fs

@pytest.fixture
def shell(fs_empty):
    s = ShellState()
    s.fs = fs_empty
    s.cwd = "/"
    return s

@pytest.fixture
def cl():
    return CommandLine()

def test_echo_basic(cl, shell):
    # echo should return stdout containing the args joined
    stderr, stdout = cl.enter_command('echo hello world', shell)
    assert stderr == []
    assert stdout == ['hello world']

def test_cat_nonexistent_file(cl, shell):
    # reading missing file returns error
    stderr, stdout = cl.enter_command('cat missing.txt', shell)
    # cat sets stderr in stdout list per your implementation
    assert len(stdout) == 1
    assert "does not exist" in stdout[0]

def test_redirection_writes_file(cl, shell, fs_empty):
    # use > redirect to create a file and write
    cl.enter_command('echo hi > out.txt', shell)
    # search filesystem for the written file and check contents
    # depending on your FS API; example:
    fs_empty.search('out.txt')   # moves current pointer to file
    fnode = fs_empty.current
    assert fnode.get_data().strip() == 'hi'