import pytest
import datetime
import random
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
    fs.current.items[0].set_data("ERROR no\nINFO hey\nERROR no2")
    fs.add_file("f2.txt")
    fs.current.items[1].set_data('\n'.join([str(i) for i in range(25)]))
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
    assert stderr == ["cd:No directory named missing"]
    assert stdout == []

def test_cd_empty(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('cd', shell_empty)
    assert stderr == ["cd: must give argument"]
    assert stdout == []

########### REDIRECTION ##########
def test_redirection_writes_file(cl, shell_empty, fs_empty):
    # use > redirect to create a file and write
    cl.enter_command('echo hi > f1.txt', shell_empty)
    # search filesystem for the written file and check contents
    # depending on your FS API; example:
    fs_empty.search('f1.txt')   # moves current pointer to file
    fnode = fs_empty.current
    assert fnode.get_data().strip() == 'hi'

def test_redirection_rewrites_file(cl, shell_basic: ShellState, fs_basic: FileSystem):
    cl.enter_command('echo hi >> f1.txt', shell_basic)
    fs_basic.search('f1.txt')
    fnode = fs_basic.current
    assert fnode.get_data().strip() == "ERROR no\nINFO hey\nERROR no2\nhi"

########### RM #################
def test_rm_basic(cl, shell_fouritems: ShellState):
    stderr, stdout = cl.enter_command('rm f2.txt', shell_fouritems)
    assert stderr == []
    assert stdout == []
    assert len(shell_fouritems.fs.current.items) == 3

def test_rm_dir(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('rm d1', shell_basic)
    assert len(shell_basic.fs.current.items) == 3
    assert stderr == ["rm: cannot remove 'd1': Is a directory"]
    assert stdout == []
    stderr, stdout = cl.enter_command('rm -r d1', shell_basic)
    assert len(shell_basic.fs.current.items) == 2
    assert stderr == []
    assert stdout == []

######### CAT ##############
def test_cat_nonexistent_file(cl, shell_empty):
    # reading missing file returns error
    stderr, stdout = cl.enter_command('cat missing.txt', shell_empty)
    # cat sets stderr in stdout list per your implementation
    assert len(stdout) == 1
    assert "does not exist" in stdout[0]

def test_cat_basic(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt', shell_basic)
    assert stderr == []
    assert stdout == ["ERROR no", "INFO hey", "ERROR no2"]

######## HEAD ##############
def test_head_basic(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('head f2.txt', shell_basic)
    assert stderr == []
    for i, line in enumerate(stdout):
        assert line == str(i)

def test_head_count(cl, shell_basic: ShellState):
    r = random.randint(1,20)
    stderr, stdout = cl.enter_command(f'head -n {r} f2.txt', shell_basic)
    assert stderr == []
    for i in range(r):
        assert stdout[i] == str(i)
    stderr, stdout = cl.enter_command(f'head --lines={r} f2.txt', shell_basic)
    assert stderr == []
    for i in range(r):
        assert stdout[i] == str(i)
    stderr, stdout = cl.enter_command(f'head --lines=-{r} f2.txt', shell_basic)
    assert stderr == []
    for i in range(r, 0):
        assert stdout[-i] == str(i)

######## GREP ##############
def test_grep_basic(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('grep \"ERROR\" f1.txt', shell_basic)
    assert stderr == []
    assert stdout == ["ERROR no", "ERROR no2"]

def test_grep_count(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('grep -c \"ERROR\" f1.txt', shell_basic)
    assert stderr == []
    assert stdout == ["2"]

####### CHMOD #############
def test_chmod_basic(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('chmod 000 f1.txt', shell_basic)
    assert stderr == []
    assert stdout == []
    fn = shell_basic.fs.get_file("f1.txt")
    assert isinstance(fn,FileNode)
    assert shell_basic.fs.current.get_permission_str(fn) == "----------"
    stderr, stdout = cl.enter_command('chmod 777 f1.txt', shell_basic)
    assert stderr == []
    assert stdout == []
    fn = shell_basic.fs.get_file("f1.txt")
    assert isinstance(fn,FileNode)
    assert shell_basic.fs.current.get_permission_str(fn) == "-rwxrwxrwx"
    stderr, stdout = cl.enter_command('chmod -R 000 d1', shell_basic)
    assert stderr == []
    assert stdout == []
    fn = shell_basic.fs.get_file("d1")
    assert isinstance(fn,FileNode)
    assert shell_basic.fs.current.get_permission_str(fn) == "d---------"
    assert isinstance(fn.items[0], FileNode)
    assert fn.get_permission_str(fn.items[0]) == "----------"

def test_chmod_errors(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('chmod 888 f1.txt', shell_basic)
    assert stderr == ["chmod: value given which is higher then needed"]
    assert stdout == []
    stderr, stdout = cl.enter_command('chmod f1.txt', shell_basic)
    assert stderr == ["chmod: expected at least two arguments"]
    assert stdout == []
    stderr, stdout = cl.enter_command('chmod 21 f1.txt', shell_basic)
    assert stderr == ["chmod: value given for permissions which is not of length of 3"]
    assert stdout == []
    stderr, stdout = cl.enter_command('chmod 6a5 f1.txt', shell_basic)
    assert stderr == ["chmod: value other then given integer given for permissions"]
    assert stdout == []

######## AND OR ################
def test_andor(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('cd d1 && ls', shell_basic)
    assert stderr == []
    assert stdout == ["f3.txt", "f4.txt"]