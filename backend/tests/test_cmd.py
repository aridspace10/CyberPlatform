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
def shell_empty(fs_empty):
    s = ShellState()
    s.fs = fs_empty
    s.cwd = "/"
    return s

@pytest.fixture
def fs_fouritems():
    fs = FileSystem()
    fs.add_file("f1.txt")
    fs.add_file("f2.txt")
    fs.add_file("f3.txt")
    fs.add_file("f4.txt")
    return fs

@pytest.fixture
def fs_basic():
    fs = FileSystem()
    fs.add_file("f1.txt")
    fs.add_file("f2.txt")
    fs.add_directory("d1")
    fs.add_file("d1/f3.txt")
    fs.add_file("d1/f4.txt")
    return fs

@pytest.fixture
def shell_basic(fs_basic):
    s = ShellState()
    s.fs = fs_basic
    s.cwd = "/"
    return s

@pytest.fixture
def shell_fouritems(fs_fouritems):
    s = ShellState()
    s.fs = fs_fouritems
    s.cwd = "/"
    return s

@pytest.fixture
def cl():
    return CommandLine()

######### ECHO #################
def test_echo_basic(cl, shell_empty):
    # echo should return stdout containing the args joined
    stderr, stdout = cl.enter_command('echo hello world', shell_empty)
    assert stderr == []
    assert stdout == ['hello world']

######## MKDIR #################
def test_mkdir_basic(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('mkdir a', shell_empty)
    assert stderr == []
    assert stdout == []
    assert len(shell_empty.fs.current.items) == 1
    assert shell_empty.fs.current.items[0].name == "a"

def test_mkdir_none(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('mkdir', shell_empty)
    assert stderr == ["mkdir: at least one argument should be given"]
    assert stdout == []
    assert len(shell_empty.fs.current.items) == 0

def test_mkdir_verbose(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('mkdir -v a', shell_empty)
    assert stderr == []
    assert stdout == ["mkdir: sucessfully created a"]
    assert len(shell_empty.fs.current.items) == 1
    assert shell_empty.fs.current.items[0].name == "a"

######### LS ###################
def test_ls_empty(cl, shell_empty):
    stderr, stdout = cl.enter_command('ls', shell_empty)
    assert stderr == []
    assert stdout == []

def test_ls_basic(cl, shell_fouritems):
    stderr, stdout = cl.enter_command('ls', shell_fouritems)
    assert stderr == []
    assert stdout == ['f1.txt','f2.txt','f3.txt','f4.txt']

####### CD ####################
def test_cd_basic(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('cd d1', shell_basic)
    assert stderr == []
    assert len(shell_basic.fs.current.items) == 2

def test_cd_missing(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('cd missing', shell_empty)
    assert stderr == ["No directory named missing"]
    assert stdout == []

def test_cd_empty(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('cd', shell_empty)
    assert stderr == ["cd: must give argument"]
    assert stdout == []

def test_cat_nonexistent_file(cl, shell_empty):
    # reading missing file returns error
    stderr, stdout = cl.enter_command('cat missing.txt', shell_empty)
    # cat sets stderr in stdout list per your implementation
    assert len(stdout) == 1
    assert "does not exist" in stdout[0]

def test_redirection_writes_file(cl, shell_empty, fs_empty):
    # use > redirect to create a file and write
    cl.enter_command('echo hi > out.txt', shell_empty)
    # search filesystem for the written file and check contents
    # depending on your FS API; example:
    fs_empty.search('out.txt')   # moves current pointer to file
    fnode = fs_empty.current
    assert fnode.get_data().strip() == 'hi'