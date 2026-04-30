import pytest
import datetime
import random
import math
from game.commandline import CommandLine
from game.ShellState import ShellState
from game.filesystem import FileSystem
from game.filenode import FileNode, Inode, NodeType
from wonderwords import RandomWord
from ..game.helpers import determine_perms_fromstr
import os
import time

LS_FILES = ["xms.bin", "silly.c", "sigma.dat", "crap.js", 
             "sheet.xsl", "nope.csv", "nothing.log", "cool.png",
             "record.ods", "stuff.sql", "annoying.java", "yikes.py"
        ]
random.shuffle(LS_FILES)

f = random.sample(LS_FILES, 10)
sizes = f[0:5]
atimes = f[5:]

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
    inode = Inode(NodeType.FILE)
    inode.set_data("ERROR 1\nERROR 2\nINFO 1")
    fn = FileNode(None, "f1.txt", inode)
    fs.add_file("f1.txt", fn)
    inode = Inode(NodeType.FILE)
    inode.set_data("ERROR 3\nERROR 4\nINFO 2")
    fn = FileNode(None, "f2.txt", inode)
    fs.add_file("f2.txt", fn)
    fs.add_file("f3.txt")
    fs.add_file("f4.txt")
    return fs

@pytest.fixture
def fs_basic():
    fs = FileSystem()
    fs.add_file("f1.txt")
    fs.current.items[0].set_data("ERROR no\nINFO hey\nERROR no2\nerror 1")
    fs.add_file("f2.txt")
    fs.current.items[1].set_data('\n'.join([str(i) for i in range(25)]))
    fs.add_directory("d1")
    fs.add_file("d1/f3.txt")
    inode = Inode(NodeType.FILE)
    inode.set_data("ERROR 1\nERROR 2\nINFO 1")
    fn = FileNode(None, "f4.txt", inode)
    fs.add_file("d1/f4.txt", fn)
    return fs

@pytest.fixture
def fs_sed():
    fs = FileSystem()
    fs.add_file("f1.txt")
    fs.current.items[0].set_data("cat wolf cat\nhi cat\n")
    fs.add_file("f2.txt")
    fs.current.items[1].set_data("cat CaT Cat")
    fs.add_file("f3.txt")
    fs.current.items[2].set_data("cat wolf cat\nhi cat\n whats up\n the cat\n test cat here")
    return fs

@pytest.fixture
def fs_cp():
    fs = FileSystem()
    fs.add_file("f1.txt")
    fs.add_directory("project")
    fs.add_file("project/here.txt")
    fs.add_directory("project/files")
    fs.add_file("project/files/f1.txt")
    fs.add_file("project/files/f2.txt")
    fs.add_directory("project/empty")
    fs.add_directory("project2")
    return fs

@pytest.fixture
def fs_ls():
    fs = FileSystem()
    # files = LS_FILES.copy()
    # random.shuffle(LS_FILES)
    for file in LS_FILES:
        time.sleep(0.1)
        fs.add_file(file)
    time.sleep(0.5)
    fn = fs.get_file(sizes[0])
    assert isinstance(fn, FileNode)
    fn.set_data("123456789" * 1000)
    fn = fs.get_file(atimes[0])
    assert isinstance(fn, FileNode)
    fn.get_data()
    time.sleep(0.1)
    fn = fs.get_file(sizes[1])
    assert isinstance(fn, FileNode)
    fn.set_data("123456789" * 100)
    fn = fs.get_file(atimes[1])
    assert isinstance(fn, FileNode)
    fn.get_data()
    time.sleep(0.1)
    fn = fs.get_file(sizes[2])
    assert isinstance(fn, FileNode)
    fn.set_data("123456789" * 50)
    fn = fs.get_file(atimes[2])
    assert isinstance(fn, FileNode)
    fn.get_data()
    time.sleep(0.1)
    fn = fs.get_file(sizes[3])
    assert isinstance(fn, FileNode)
    fn.set_data("123456789" * 10)
    fn = fs.get_file(atimes[3])
    assert isinstance(fn, FileNode)
    fn.get_data()
    time.sleep(0.1)
    fn = fs.get_file(sizes[4])
    assert isinstance(fn, FileNode)
    fn.set_data("123456789" * 1)
    fn = fs.get_file(atimes[4])
    assert isinstance(fn, FileNode)
    fn.get_data()
    return fs

# ---------------- WC TEST FIXTURES ----------------

@pytest.fixture
def shell_emptyfile():
    fs = FileSystem()
    fs.add_file("empty.txt")
    fn = fs.get_file("empty.txt")
    assert isinstance(fn, FileNode)
    fn.set_data("")
    s = ShellState()
    s.fs = fs
    s.cwd = "/"
    return s


@pytest.fixture
def shell_one_line_no_newline():
    fs = FileSystem()
    fs.add_file("f1.txt")
    fn = fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    fn.set_data("hello")
    s = ShellState()
    s.fs = fs
    s.cwd = "/"
    return s


@pytest.fixture
def shell_one_line_newline(): 
    fs = FileSystem()
    fs.add_file("f1.txt")
    fn = fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    fn.set_data("hello\n")
    s = ShellState()
    s.fs = fs
    s.cwd = "/"
    return s


@pytest.fixture
def shell_blank_lines():
    fs = FileSystem()
    fs.add_file("blank.txt")
    fn = fs.get_file("blank.txt")
    assert isinstance(fn, FileNode)
    fn.set_data("\n\n\n")
    s = ShellState()
    s.fs = fs
    s.cwd = "/"
    return s


@pytest.fixture
def shell_only_newlines():
    fs = FileSystem()
    fs.add_file("nl.txt")
    fn = fs.get_file("nl.txt")
    assert isinstance(fn, FileNode)
    fn.set_data("\n\n\n\n")
    s = ShellState()
    s.fs = fs
    s.cwd = "/"
    return s


@pytest.fixture
def shell_whitespace_lines():
    fs = FileSystem()
    fs.add_file("white.txt")
    fn = fs.get_file("white.txt")
    assert isinstance(fn, FileNode)
    fn.set_data("   \n\t\nhello\n")
    s = ShellState()
    s.fs = fs
    s.cwd = "/"
    return s


@pytest.fixture
def shell_twofiles():
    fs = FileSystem()

    fs.add_file("f1.txt")
    fn = fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    fn.set_data("a\nb\n")

    fs.add_file("f2.txt")
    fn = fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    fn.set_data("1\n2\n3\n")

    s = ShellState()
    s.fs = fs
    s.cwd = "/"
    return s


@pytest.fixture
def shell_mixfiles():
    fs = FileSystem()

    fs.add_file("a.txt")
    fn = fs.get_file("a.txt")
    assert isinstance(fn, FileNode)
    fn.set_data("")

    fs.add_file("b.txt")
    fn = fs.get_file("b.txt")
    assert isinstance(fn, FileNode)
    fn.set_data("1\n2\n3\n4\n")

    s = ShellState()
    s.fs = fs
    s.cwd = "/"
    return s


@pytest.fixture
def shell_largefile():
    fs = FileSystem()

    fs.add_file("huge.txt")
    fn = fs.get_file("huge.txt")
    assert isinstance(fn, FileNode)
    fn.set_data(
        "\n".join(str(i) for i in range(1000)) + "\n"
    )

    s = ShellState()
    s.fs = fs
    s.cwd = "/"
    return s


@pytest.fixture
def shell_trailing_newline():
    fs = FileSystem()

    fs.add_file("t.txt")
    fn = fs.get_file("t.txt")
    assert isinstance(fn, FileNode)
    fn.set_data("a\nb\n")

    s = ShellState()
    s.fs = fs
    s.cwd = "/"
    return s


@pytest.fixture
def shell_no_final_newline():
    fs = FileSystem()

    fs.add_file("t.txt")
    fn = fs.get_file("t.txt")
    assert isinstance(fn, FileNode)
    fn.set_data("a\nb")

    s = ShellState()
    s.fs = fs
    s.cwd = "/"
    return s

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
def shell_cp(fs_cp):
    s = ShellState()
    s.fs = fs_cp
    s.cwd = "/"
    return s

@pytest.fixture
def shell_ls(fs_ls):
    s = ShellState()
    s.fs = fs_ls
    s.cwd = "/"
    return s

@pytest.fixture
def shell_sed(fs_sed):
    s = ShellState()
    s.fs = fs_sed
    s.cwd = "/"
    return s

@pytest.fixture
def cl():
    return CommandLine()

######## HELPS #################
def test_cmd_helps(cl, shell_empty):
    cmds = ['mkdir', 'cat', 'chmod', 'grep', 'head', 'ln', 'ls', 'mv', 'sort', 'touch', "rm"]
    for cmd in cmds:
        stderr, stdout = cl.enter_command(f'{cmd} --help', shell_empty)
        with open(f"../static/help/{cmd}.txt") as f:
            assert stderr == []
            assert stdout == f.readlines()

####### Unknown #############
def test_cmd_unknown(cl, shell_empty):
    stderr, stdout = cl.enter_command("test abcd", shell_empty)
    assert stderr == ["Unknown command given"]
    assert stdout == []

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

    stderr, stdout = cl.enter_command('mkdir a', shell_empty)
    assert stderr == ["mkdir: Filename 'a' already exists"]
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

def test_mkdir_error(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('mkdir a/b', shell_empty)
    assert stderr == ['mkdir: No directory named a']
    assert stdout == []
    assert len(shell_empty.fs.current.items) == 0

    stderr, stdout = cl.enter_command('mkdir -p', shell_empty)
    assert stderr == ["mkdir: no name given for new directory"]
    assert stdout == []
    assert len(shell_empty.fs.current.items) == 0

def test_mkdir_permissions(cl, shell_empty: ShellState):
    perm_str = ''.join([str(random.randint(1,7)) for _ in range(0,3)])
    perm = determine_perms_fromstr(perm_str)
    stderr, stdout = cl.enter_command(f'mkdir -m a={perm_str} a', shell_empty)
    assert stderr == []
    assert stdout == []
    assert len(shell_empty.fs.current.items) == 1
    fn = shell_empty.fs.current.items[0]
    assert fn.name == "a"
    assert perm == fn.inode.permissions

    stderr, stdout = cl.enter_command(f'mkdir -m a=00 a', shell_empty)
    assert stderr == ['chmod: value given for permissions which is not of length of 3']
    assert stdout == []

    stderr, stdout = cl.enter_command(f'mkdir -m randomstuff a', shell_empty)
    assert stderr == ["mkdir: option given to -m or --mode is not correct"]
    assert stdout == []

def test_mkdir_parents(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('mkdir -p a/b/c', shell_empty)
    assert stderr == []
    assert stdout == []
    assert len(shell_empty.fs.current.items) == 1
    fn = shell_empty.fs.current.items[0]
    assert fn.name == "a"
    assert len(fn.items) == 1
    fn2 = fn.items[0]
    assert fn2.name == "b"
    assert len(fn2.items) == 1
    fn3 = fn2.items[0]
    assert fn3.name == "c"

######### LS ###################
def test_ls_empty(cl, shell_empty):
    stderr, stdout = cl.enter_command('ls', shell_empty)
    assert stderr == []
    assert stdout == []

def test_ls_error(cl, shell_empty):
    stderr, stdout = cl.enter_command('ls -y', shell_empty)
    assert stderr == ["ls: unknown argument given"]
    assert stdout == []

def test_ls_target(cl, shell_basic):
    stderr, stdout = cl.enter_command('ls d1', shell_basic)
    assert stderr == []
    assert stdout == ["f3.txt", "f4.txt"]

def test_ls_basic(cl, shell_fouritems):
    stderr, stdout = cl.enter_command('ls', shell_fouritems)
    assert stderr == []
    assert stdout == ['f1.txt','f2.txt','f3.txt','f4.txt']

def test_ls_reverse(cl, shell_fouritems):
    stderr, stdout = cl.enter_command('ls -r', shell_fouritems)
    assert stderr == []
    assert stdout == ['f4.txt','f3.txt','f2.txt','f1.txt']

def test_ls_deep(cl, shell_basic):
    stderr, stdout = cl.enter_command('ls -R', shell_basic)
    assert stderr == []
    assert stdout == ['f1.txt', 'f2.txt', 'd1', '/d1/f3.txt', '/d1/f4.txt']

def test_ls_organisation(cl, shell_ls: ShellState):
    stderr, stdout = cl.enter_command('ls -X', shell_ls)
    files = LS_FILES.copy()
    assert stderr == []
    sorted_files = sorted(files, key=lambda f: os.path.splitext(f)[1])
    assert stdout == sorted_files

    stderr, stdout = cl.enter_command('ls -S', shell_ls)
    assert stderr == []
    for i in range(0, 5):
        assert stdout[i] == sizes[i]

    stderr, stdout = cl.enter_command('ls -t', shell_ls)
    times = sizes.copy()
    times.reverse()
    assert stderr == []
    for i in range(0, 5):
        assert stdout[i] == times[i]

    stderr, stdout = cl.enter_command('ls -u', shell_ls)
    atimes.reverse()
    assert stderr == []
    for i in range(0, 5):
        assert stdout[i] == atimes[i]

    stderr, stdout = cl.enter_command('ls -c', shell_ls)
    print (stdout)
    print (LS_FILES)
    assert stderr == []
    for i in range(0, 5):
        assert stdout[i] == LS_FILES[-(i+1)]
    

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
def test_redirection_writes_file(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('echo hi > d1/f3.txt', shell_basic)
    assert stdout == []
    assert stderr == []
    stderr, stdout = cl.enter_command('cat d1/f3.txt', shell_basic)
    assert stdout == ['hi']
    assert stderr == []  

def test_redirection_path_error(cl, shell_basic: ShellState, fs_basic):
    stderr, stdout = cl.enter_command('echo hi > not/f3.txt', shell_basic)
    assert stderr == ['No directory named not']
    assert stdout == []

    stderr, stdout = cl.enter_command('echo hi >> not/f3.txt', shell_basic)
    assert stderr == ['No directory named not']
    assert stdout == []

def test_redirection_rewrites_file(cl, shell_basic: ShellState, fs_basic: FileSystem):
    cl.enter_command('echo hi >> f1.txt', shell_basic)
    fs_basic.search('f1.txt')
    fnode = fs_basic.current
    assert fnode.get_data().strip() == "ERROR no\nINFO hey\nERROR no2\nerror 1\nhi"

def test_redirection_writes_newfile(cl, shell_basic: ShellState, fs_basic: FileSystem):
    cl.enter_command('echo hi >> f3.txt', shell_basic)
    fs_basic.search('f3.txt')
    fnode = fs_basic.current
    assert fnode.get_data().strip() == "hi"

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
    assert stdout == ["ERROR no", "INFO hey", "ERROR no2", "error 1"]

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

def test_head_bytes(cl, shell_basic: ShellState):
    r = random.randint(5, 20)
    stderr, stdout = cl.enter_command(f'head -c {r} f2.txt', shell_basic)
    assert stderr == []
    expected_lines = math.ceil(r / 2)
    assert len(stdout) == expected_lines
    for i, line in enumerate(stdout):
        assert line == str(i)

    stderr, stdout = cl.enter_command(f'head --bytes={r} f2.txt', shell_basic)
    assert stderr == []
    expected_lines = math.ceil(r / 2)
    assert len(stdout) == expected_lines
    for i, line in enumerate(stdout):
        assert line == str(i)
    

######### TOUCH ############
def test_touch_basic(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('touch --no-create f1.txt', shell_basic)
    assert stderr == []
    assert stdout == []
    assert isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)

    stderr, stdout = cl.enter_command('touch f3.txt', shell_basic)
    assert stderr == []
    assert stdout == []

    stderr, stdout = cl.enter_command('touch -c f4.txt', shell_basic)
    assert stderr == []
    assert stdout == []
    assert not isinstance(shell_basic.fs.get_file("f4.txt"), FileNode)

    stderr, stdout = cl.enter_command('touch -x', shell_basic)
    assert stderr == ["touch: unknown argument given"]
    assert stdout == []

    stderr, stdout = cl.enter_command('touch -a --date=2025-01-01 f2.txt', shell_basic)
    assert stderr == []
    assert stdout == []
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    assert fn.inode.atime != fn.inode.mtime

    stderr, stdout = cl.enter_command('touch -m --date=2025-02-01 f1.txt', shell_basic)
    assert stderr == []
    assert stdout == []
    fn = shell_basic.fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    assert fn.inode.atime != fn.inode.mtime

def test_touch_error(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('touch', shell_basic)
    assert stderr == ["touch: must give atleast one argument"]
    assert stdout == []

    stderr, stdout = cl.enter_command('touch a/f1.txt', shell_basic)
    assert stderr == ["No directory named a"]
    assert stdout == []

    stderr, stdout = cl.enter_command('touch -a', shell_basic)
    assert stderr == ["touch: no file given"]
    assert stdout == []

######## GREP ##############
def test_grep_basic(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('grep ERROR f1.txt', shell_basic)
    assert stderr == []
    assert stdout == ["ERROR no", "ERROR no2"]

def test_grep_count(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('grep -c ERROR f1.txt', shell_basic)
    assert stderr == []
    assert stdout == ["2"]

def test_grep_error(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('grep -c', shell_basic)
    assert stderr == ["grep: pattern not given"]
    assert stdout == []

    stderr, stdout = cl.enter_command('grep -a', shell_basic)
    assert stderr == ["grep: unknown argument given"]
    assert stdout == []

    stderr, stdout = cl.enter_command('grep text notexist.txt', shell_basic)
    assert stderr == ["grep: notexist.txt can not be found"]
    assert stdout == []

def test_grep_matchline(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('grep -x \"ERROR no\" f1.txt', shell_basic)
    assert stderr == []
    assert stdout == ["ERROR no"]

def test_grep_matchwhole(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('grep -i ERROR f1.txt', shell_basic)
    assert stderr == []
    assert stdout == ["ERROR no", "ERROR no2", "error 1"]

def test_grep_dir(cl, shell_fouritems: ShellState):
    stderr, stdout = cl.enter_command('grep -r ERROR .', shell_fouritems)
    assert stderr == []
    assert stdout == ["ERROR 1", "ERROR 2", "ERROR 3", "ERROR 4"]

def test_grep_dir2(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('grep -r ERROR .', shell_basic)
    assert stderr == []
    assert stdout == ['ERROR no', 'ERROR no2', 'ERROR 1', 'ERROR 2']

def test_grep_dir3(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('grep ERROR .', shell_basic)
    assert stderr == ["Can't recursivly search directory without -r option"]
    assert stdout == []

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
    stderr, stdout = cl.enter_command('chmod -Rv 000 d1', shell_basic)
    assert stdout == ["Updated permissions of d1 with d---------", 'Updated permissions of f3.txt with ----------', 'Updated permissions of f4.txt with ----------']
    assert stderr == []
    fn = shell_basic.fs.get_file("d1")
    assert isinstance(fn,FileNode)
    assert shell_basic.fs.current.get_permission_str(fn) == "d---------"
    assert isinstance(fn.items[0], FileNode)
    assert fn.get_permission_str(fn.items[0]) == "----------"

def test_chmod_errors(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('chmod -y 888 not_exist.txt', shell_basic)
    assert stderr == ["chmod: Unknown output given"]
    assert stdout == []
    stderr, stdout = cl.enter_command('chmod 777 not_exist.txt', shell_basic)
    assert stderr == ["chmod: No directory named not_exist.txt"]
    assert stdout == []
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

def test_and_failure(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('cd d3 && ls', shell_basic)
    assert stderr == ['cd:No directory named d3']
    assert stdout == []


######## LN ###################
def test_ln_basic(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('ln f1.txt s1.txt', shell_basic)
    assert stderr == []
    assert stdout == []
    f1, f2 = shell_basic.fs.get_file("f1.txt"), shell_basic.fs.get_file("s1.txt")
    assert isinstance(f1, FileNode)
    assert isinstance(f2, FileNode)
    assert f1.get_data() == f2.get_data()
    stderr, stdout = cl.enter_command('echo "Example" >> f1.txt', shell_basic)
    f1, f2 = shell_basic.fs.get_file("f1.txt"), shell_basic.fs.get_file("s1.txt")
    assert isinstance(f1, FileNode)
    assert isinstance(f2, FileNode)
    assert stderr == []
    assert stdout == []
    assert f1.get_data() == f2.get_data()
    stderr, stdout = cl.enter_command('echo "Example2" >> s1.txt', shell_basic)
    f1, f2 = shell_basic.fs.get_file("f1.txt"), shell_basic.fs.get_file("s1.txt")
    assert isinstance(f1, FileNode)
    assert isinstance(f2, FileNode)
    assert stderr == []
    assert stdout == []
    assert f1.get_data() == f2.get_data()

######### MV ##################
def test_mv_rename(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('mv f1.txt', shell_basic)
    assert stderr == ["cp: expected at least two arguments"]
    assert stdout == []
    # rename
    stderr, stdout = cl.enter_command('mv f1.txt abc.txt', shell_basic)
    assert stderr == []
    assert stdout == []
    assert isinstance(shell_basic.fs.get_file("abc.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)

    stderr, stdout = cl.enter_command('mv -v abc.txt f1.txt', shell_basic)
    assert stderr == []
    assert stdout == ["Renamed abc.txt -> f1.txt"]
    assert isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("abc.txt"), FileNode)

    stderr, stdout = cl.enter_command('mv abc.txt f4.txt', shell_basic)
    assert stderr == ["mv: could not find file abc.txt"]
    assert stdout == []
    assert not isinstance(shell_basic.fs.get_file("f4.txt"), FileNode)

def test_vm_move_norename(cl, shell_basic: ShellState):
    #move to directory
    stderr, stdout = cl.enter_command('mv f1.txt d1', shell_basic)
    assert stderr == []
    assert stdout == []
    assert isinstance(shell_basic.fs.get_file("d1/f1.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)

    stderr, stdout = cl.enter_command('mv -v f2.txt d1', shell_basic)
    assert stderr == []
    assert stdout == ["Moved f2.txt to d1"]
    assert isinstance(shell_basic.fs.get_file("d1/f2.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f2.txt"), FileNode)

    stderr, stdout = cl.enter_command('mv f3.txt d1', shell_basic)
    assert stderr == ["mv: could not find file f3.txt"]
    assert stdout == []

def test_vm_move_multiple(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('mv f1.txt f2.txt d1', shell_basic)
    assert stderr == []
    assert stdout == []
    assert isinstance(shell_basic.fs.get_file("d1/f1.txt"), FileNode)
    assert isinstance(shell_basic.fs.get_file("d1/f2.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f2.txt"), FileNode)

    stderr, stdout = cl.enter_command('mv f5.txt f6.txt d1', shell_basic)
    assert stderr == ["mv: could not find file f5.txt", "mv: could not find file f6.txt"]
    assert stdout == []
    assert not isinstance(shell_basic.fs.get_file("d1/f5.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("d1/f6.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f5.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f6.txt"), FileNode)

def test_vm_move_multiple2(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('mv -v f1.txt f2.txt d1', shell_basic)
    assert stderr == []
    assert stdout == ["Moved f1.txt to d1", "Moved f2.txt to d1"]
    assert isinstance(shell_basic.fs.get_file("d1/f1.txt"), FileNode)
    assert isinstance(shell_basic.fs.get_file("d1/f2.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)
    assert not isinstance(shell_basic.fs.get_file("f2.txt"), FileNode)

########## SUBSHELL #################
def test_subshell_basic(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('(cd d1 && ls)', shell_basic)
    assert stderr == []
    assert stdout == ["f3.txt", "f4.txt"]
    stderr, stdout = cl.enter_command('ls', shell_basic)
    assert stderr == []
    assert stdout == ["f1.txt", "f2.txt", "d1"]

def test_semicolon_basic(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('cd d1; ls', shell_basic)
    assert stderr == []
    assert stdout == ["f3.txt", "f4.txt"]

########## VAR #####################
def test_var_basic(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('X=5', shell_basic)
    assert stderr == []
    assert stdout == []
    assert shell_basic.vars["X"] == "5"

    stderr, stdout = cl.enter_command('echo $X', shell_basic)
    assert stderr == []
    assert stdout == ["5"]

def test_var_error(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('echo $X', shell_basic)
    assert stderr == ["Var Used which is unassigned: X"]
    assert stdout == []

######## SORT ######################
def setup_names(s: ShellState, name: str) -> list[str]:
    amount = random.randint(5, 25)
    names = []
    r = RandomWord()
    for _ in range(0, amount):
        names.append(r.word())
    s.fs.search(name)
    s.fs.current.set_data('\n'.join(names))
    s.fs.current = s.fs.filehead
    names.sort()
    return names

def test_sort_basic(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    stderr, stdout = cl.enter_command('sort f2.txt', shell_basic)
    assert stderr == []
    for i in range(0, len(names)):
        assert stdout[i] == names[i]

def test_sort_random(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    name = random.choice(names)
    names.append(name)
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    fn.append_data(name)
    stderr, stdout = cl.enter_command('sort -R f2.txt', shell_basic)
    assert stderr == []
    for i in range(0, len(names)-1):
        if (stdout[i] == name):
            assert stdout[i+1] == name
            return
    assert False

def test_sort_dups(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    name = random.choice(names)
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    fn.append_data(name)
    stderr, stdout = cl.enter_command('sort -u f2.txt', shell_basic)
    assert stderr == []
    assert len(stdout) == len(names)
    for i in range(0, len(names)):
        assert stdout[i] == names[i]

def test_sort_output(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    stderr, stdout = cl.enter_command('sort -o f1.txt f2.txt', shell_basic)
    shell_basic.fs.search("f1.txt")
    data = shell_basic.fs.current.get_data().split("\n")
    shell_basic.fs.current = shell_basic.fs.filehead
    assert stderr == []
    assert stdout == []
    for i in range(0, len(names)):
        assert data[i] == names[i]

def test_sort_sorted(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    stderr, stdout = cl.enter_command('sort -o s1.txt f2.txt', shell_basic)
    shell_basic.fs.search("s1.txt")
    data = shell_basic.fs.current.get_data().split("\n")
    shell_basic.fs.current = shell_basic.fs.filehead
    assert stderr == []
    assert stdout == []
    for i in range(0, len(names)):
        assert data[i] == names[i]
    stderr, stdout = cl.enter_command('sort -C s1.txt', shell_basic)
    assert stderr == []
    assert stdout == []
    assert shell_basic.ls == 0
    stderr, stdout = cl.enter_command('sort -C f2.txt', shell_basic)
    assert stderr == []
    assert stdout == []
    assert shell_basic.ls == 1
    stderr, stdout = cl.enter_command('sort -c f2.txt', shell_basic)
    assert len(stderr)
    assert stderr[0].startswith("sort:")
    assert stdout == []
    assert shell_basic.ls == 1

######### PIPES #################
def test_pipes_lsgrep(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('ls | grep f', shell_basic)
    assert stderr == []
    assert stdout == ["f1.txt", "f2.txt"]

def test_pipes_lshead(cl, shell_fouritems: ShellState):
    stderr, stdout = cl.enter_command('ls | head --lines=2', shell_fouritems)
    assert stderr == []
    assert stdout == ["f1.txt", "f2.txt"]

def test_pipes_lshead2(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('ls | head', shell_empty)
    assert stderr == []
    assert stdout == []

def test_pipes_sortuniq(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    name = random.choice(names)
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    fn.append_data(name)
    stderr, stdout = cl.enter_command('sort f2.txt | uniq', shell_basic)
    assert stderr == []
    assert len(stdout) == len(names)
    for i in range(0, len(names)):
        assert stdout[i] == names[i]

def test_pipes_lsgrep_inverse(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('ls | grep -v f1', shell_basic)
    assert stderr == []
    assert stdout == ["f2.txt", "d1"]


def test_pipes_lssort(cl, shell_fouritems: ShellState):
    stderr, stdout = cl.enter_command('ls | sort', shell_fouritems)
    assert stderr == []
    assert stdout == sorted(stdout)


def test_pipes_ls_tail(cl, shell_fouritems: ShellState):
    stderr, stdout = cl.enter_command('ls | tail --lines=2', shell_fouritems)
    assert stderr == []
    assert stdout == ["f3.txt", "f4.txt"]


def test_pipes_catgrep(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | grep cat', shell_sed)
    assert stderr == []
    assert stdout == ["cat wolf cat", "hi cat"]


def test_pipes_catgrephead(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | grep cat | head --lines=1', shell_sed)
    assert stderr == []
    assert stdout == ["cat wolf cat"]


def test_pipes_catgreptail(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | grep cat | tail --lines=1', shell_sed)
    assert stderr == []
    assert stdout == ["hi cat"]


def test_pipes_catwc_lines(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | wc -l', shell_sed)
    assert stderr == []
    assert stdout == ["2"]


def test_pipes_catwc_words(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | wc -w', shell_sed)
    assert stderr == []
    assert stdout == ["5"]


def test_pipes_cat_sort(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | sort', shell_sed)
    assert stderr == []
    assert stdout == sorted(stdout)


def test_pipes_catuniq(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f2.txt | uniq', shell_sed)
    assert stderr == []
    assert stdout == ["cat CaT Cat"]


def test_pipes_grep_wc(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | grep cat | wc -l', shell_sed)
    assert stderr == []
    assert stdout == ["2"]


def test_pipes_lsgrepwc(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('ls | grep txt | wc -l', shell_basic)
    assert stderr == []
    assert stdout == ["2"]


def test_pipes_multiple_grep(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | grep cat | grep wolf', shell_sed)
    assert stderr == []
    assert stdout == ["cat wolf cat"]


def test_pipes_head_tail_combo(cl, shell_fouritems: ShellState):
    stderr, stdout = cl.enter_command('ls | head --lines=3 | tail --lines=1', shell_fouritems)
    assert stderr == []
    assert stdout == ["f3.txt"]


def test_pipes_ls_grep_no_match(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('ls | grep xyz', shell_basic)
    assert stderr == []
    assert stdout == []


def test_pipes_empty_chain(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('ls | grep f | wc -l', shell_empty)
    assert stderr == []
    assert stdout == ["0"]


def test_pipes_long_chain(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command(
        'cat f1.txt | grep cat | sort | head --lines=1 | wc -w',
        shell_sed
    )
    assert stderr == []
    assert stdout == ["3"]


def test_pipes_cat_grep_ignorecase(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f2.txt | grep -i cat', shell_sed)
    assert stderr == []
    assert stdout == ["cat CaT Cat"]


def test_pipes_ls_head_wc(cl, shell_fouritems: ShellState):
    stderr, stdout = cl.enter_command('ls | head --lines=3 | wc -l', shell_fouritems)
    assert stderr == []
    assert stdout == ["3"]


def test_pipes_sort_tail(cl, shell_fouritems: ShellState):
    stderr, stdout = cl.enter_command('ls | sort | tail --lines=1', shell_fouritems)
    assert stderr == []
    assert stdout == ["f4.txt"]

######### CP ###################
def test_cp_basic(cl, shell_fouritems: ShellState):
    stderr, stdout = cl.enter_command('cp f1.txt copied.txt', shell_fouritems)
    assert stdout == []
    assert stderr == []
    fn = shell_fouritems.fs.get_file("copied.txt")
    assert isinstance(fn, FileNode)
    assert fn.get_data() == "ERROR 1\nERROR 2\nINFO 1"

    stderr, stdout = cl.enter_command('cp -v f2.txt f3.txt', shell_fouritems)
    assert stdout == ["cp: Copied 'f2.txt' to 'f3.txt'"]
    assert stderr == []
    fn = shell_fouritems.fs.get_file("f3.txt")
    assert isinstance(fn, FileNode)
    assert fn.get_data() == "ERROR 3\nERROR 4\nINFO 2"

def test_cp_directory(cl, shell_cp: ShellState):
    stderr, stdout = cl.enter_command('cp -vr project project_backup', shell_cp)
    assert stdout == ["cp: Copied 'project' to 'project_backup'"]
    assert stderr == []
    f1 = shell_cp.fs.get_file("project")
    f2 = shell_cp.fs.get_file("project_backup")
    assert isinstance(f1, FileNode) and isinstance(f2, FileNode)
    assert f1.items == f2.items

    stderr, stdout = cl.enter_command('cp -vr project project2', shell_cp)
    assert stdout == ["cp: Copied 'project' to 'project2'"]
    assert stderr == []
    f1 = shell_cp.fs.get_file("project")
    f2 = shell_cp.fs.get_file("project2/project")
    assert isinstance(f1, FileNode) and isinstance(f2, FileNode)
    assert f1.items == f2.items

def test_cp_file_directory(cl, shell_fouritems: ShellState):
    shell_fouritems.fs.add_directory("d1")
    stderr, stdout = cl.enter_command('cp f1.txt f2.txt d1', shell_fouritems)
    assert stderr == []
    assert stdout == []
    f1 = shell_fouritems.fs.get_file("d1")
    f2 = shell_fouritems.fs.get_file("f1.txt")
    f3 = shell_fouritems.fs.get_file("f2.txt")
    f4 = shell_fouritems.fs.get_file("d1/f1.txt")
    f5 = shell_fouritems.fs.get_file("d1/f2.txt")
    assert isinstance(f1, FileNode) and isinstance(f2, FileNode) and isinstance(f3, FileNode)
    assert len(f1.items) == 2
    assert f2 == f4
    assert f3 == f5

def test_cp_errors(cl, shell_cp: ShellState):
    stderr, stdout = cl.enter_command('cp project project_backup', shell_cp)
    assert stdout == []
    assert stderr == ["cp: -r not specified; omitting directory 'project'"]

    stderr, stdout = cl.enter_command('cp -r project f1.txt', shell_cp)
    assert stdout == []
    assert stderr == ["cp: cannot overwrite non-directory 'f1.txt' with directory 'project'"]

def test_cp_errors2(cl, shell_fouritems: ShellState):
    stderr, stdout = cl.enter_command('cp f1.txt f2.txt f12.txt', shell_fouritems)
    assert stdout == []
    assert stderr == ["cp: target 'f12.txt' is not a directory"]

################# FIND ##################
def test_find_error(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('find', shell_basic)
    assert stdout == []
    assert stderr == ["find: atleast one argument needs to be given"]

    stderr, stdout = cl.enter_command('find \( -type f -o -type d', shell_basic)
    assert stdout == []
    assert stderr == ["find: Missing )"]

    stderr, stdout = cl.enter_command('find . -type', shell_basic)
    assert stdout == []
    assert stderr == ["find: No value for given for: -type"]

    stderr, stdout = cl.enter_command('find . -exec cat {}', shell_basic)
    assert stdout == []
    assert stderr == ["find: Expected ; or +"]

    stderr, stdout = cl.enter_command('find not_exist.jsx -type f', shell_basic)
    assert stdout == []
    assert stderr == ["No directory named not_exist.jsx"]

    stderr, stdout = cl.enter_command('find -h', shell_basic)
    assert stdout == []
    assert stderr == ["find: starting locaiton needs to be given"]

def test_find_basic(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('find .', shell_basic)
    assert stdout == [".","./f1.txt","./f2.txt","./d1" ,"./d1/f3.txt", "./d1/f4.txt"]
    assert stderr == []

def test_find_file(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('find . -type f', shell_basic)
    assert stdout == ["./f1.txt","./f2.txt","./d1/f3.txt", "./d1/f4.txt"]
    assert stderr == []

def test_find_or(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('find . -type f -o -type d', shell_basic)
    assert stdout == [".","./f1.txt","./f2.txt","./d1" ,"./d1/f3.txt", "./d1/f4.txt"]
    assert stderr == []

def test_find_name(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('find . -name \"f*.txt\"', shell_basic)
    assert stdout == ["./f1.txt","./f2.txt","./d1/f3.txt", "./d1/f4.txt"]
    assert stderr == []

    stderr, stdout = cl.enter_command('find . -name f4.txt', shell_basic)
    assert stdout == ["./d1/f4.txt"]
    assert stderr == []

def test_find_not(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('find . ! -name \"f*.txt\"', shell_basic)
    assert stdout == [".", "./d1"]
    assert stderr == []

def test_find_and(cl, shell_basic: ShellState):
    shell_basic.fs.add_file("f3.txt")
    stderr, stdout = cl.enter_command('find . -type d -name f3.txt', shell_basic)
    assert stdout == []
    assert stderr == []

def test_find_delete(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('find . -type f -name f3.txt -delete', shell_basic)
    assert stdout == []
    assert stderr == []

###### SED ##############
def test_sed_error(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command("sed", shell_empty)
    assert stderr == ["sed [OPTION]... {script-only-if-no-other-script} [input-file]..."]
    assert stdout == []

def test_sed_malformed1(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command("sed s/foo f1.txt", shell_basic)
    assert stderr == ["sed: substution expects s/pattern/replacement/"]
    assert stdout == []

def test_sed_malformed2(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command("sed 's/foo/bar' f1.txt", shell_basic)
    assert stderr == ["sed: expected terminating delim"]
    assert stdout == []

def test_sed_malformed3(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command("sed 's/foo/bar/z' f1.txt", shell_basic)
    assert stderr == ["sed: unknown expression flag - z"]
    assert stdout == []

def test_sed_malformed4(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command("sed -a 's/foo/bar/' f1.txt", shell_basic)
    assert stderr == ["sed: unknown option given - a"]
    assert stdout == []

def test_sed_basic(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's/cat/dog/' f1.txt", shell_sed)
    assert stdout == ["dog wolf cat", "hi dog"]
    assert stderr == []

def test_sed_global(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's/cat/dog/g' f1.txt", shell_sed)
    assert stdout == ["dog wolf dog", "hi dog"]
    assert stderr == []

def test_sed_nochange(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's/not/exist/' f1.txt", shell_sed)
    assert stderr == []
    assert stdout == ["cat wolf cat", "hi cat"]

def test_sed_emreplace(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's/cat//' f1.txt", shell_sed)
    assert stderr == []
    assert stdout == [" wolf dog", "hi "]

def test_sed_alternatedelim(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's|cat|dog|g' f1.txt", shell_sed)
    assert stderr == []
    assert stdout == ["cat wolf cat\nhi cat"]

    stderr, stdout = cl.enter_command("sed 's#cat#dog#' f1.txt", shell_sed)
    assert stderr == []
    assert stdout == ["cat wolf dog", "hi cat"]

def test_sed_noccurences(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's/cat/dog/2' f1.txt", shell_sed)
    assert stdout == ["cat wolf dog", "hi cat"]
    assert stderr == []

def test_sed_cinsentive(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's/cat/dog/Ig' f2.txt", shell_sed)
    assert stdout == ["dog wolf dog", "hi dog"]
    assert stderr == []

def test_sed_addressing(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed '2s/cat/dog/' f1.txt", shell_sed)
    assert stdout == ["cat wolf cat\nhi dog"]
    assert stderr == []

    stderr, stdout = cl.enter_command("sed '$s/cat/dog/' f1.txt", shell_sed)
    assert stdout == ["cat wolf cat", "hi dog"]
    assert stderr == []

def test_sed_addressing2(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed '2,4s/cat/dog/' f3.txt", shell_sed)
    assert stdout == ["cat wolf cat", "hi dog", "whats up", " the dog", " test cat here"]
    assert stderr == []

def test_sed_delete(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed '2d' f1.txt", shell_sed)
    assert stdout == ["cat wolf cat"]
    assert stderr == []

    stderr, stdout = cl.enter_command("sed '$d' f1.txt", shell_sed)
    assert stdout == ["cat wolf cat"]
    assert stderr == []

    stderr, stdout = cl.enter_command("sed '2,4d' f3.txt", shell_sed)
    assert stdout == ["cat wolf cat", " test cat here"]
    assert stderr == []

def test_sed_multexpr(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed -e 's/cat/dog/' -e 's/wolf/howl/ f1.txt", shell_sed)
    assert stdout == ["dog howl cat", "hi dog"]
    assert stderr == []

def test_sed_print_flag(cl, shell_sed):
    stderr, stdout = cl.enter_command(
        "sed -n 's/cat/dog/p' f1.txt",
        shell_sed
    )
    assert stderr == []
    assert stdout == [
        "dog wolf cat",
        "hi dog"
    ]

def test_sed_print_flag_no_match(cl, shell_sed):
    stderr, stdout = cl.enter_command(
        "sed -n 's/bird/fish/p' f1.txt",
        shell_sed
    )
    assert stderr == []
    assert stdout == []

def test_sed_expression_order(cl, shell_sed):
    stderr, stdout = cl.enter_command(
        "sed -e 's/cat/dog/' -e 's/dog/wolf/' f1.txt",
        shell_sed
    )

    assert stderr == []
    assert stdout == [
        "wolf wolf cat",
        "hi wolf"
    ]

def test_sed_case_insensitive_single(cl, shell_sed):
    stderr, stdout = cl.enter_command(
      "sed 's/cat/dog/I' f2.txt",
      shell_sed
    )

    assert stderr == []
    assert stdout == [
      "dog CaT Cat"
    ]

def test_sed_delete_blank_lines(cl, shell_sed):
    shell_sed.fs.add_file("blank.txt")
    shell_sed.fs.current.items[0].set_data(
      "a\n\nb\n\nc"
    )

    stderr, stdout = cl.enter_command(
      r"sed '/^$/d' blank.txt",
      shell_sed
    )

    assert stderr == []
    assert stdout == [
      "a","b","c"
    ]

def test_sed_path_delimiters(cl, shell_sed):
    shell_sed.fs.add_file("path.txt")
    shell_sed.fs.current.items[0].set_data(
      "/usr/bin"
    )

    stderr, stdout = cl.enter_command(
      "sed 's|/usr/bin|/opt/bin|' path.txt",
      shell_sed
    )

    assert stderr == []
    assert stdout == [
      "/opt/bin"
    ]

def test_sed_empty_file(cl, shell_sed):
    shell_sed.fs.add_file("empty.txt")

    stderr, stdout = cl.enter_command(
      "sed 's/cat/dog/' empty.txt",
      shell_sed
    )

    assert stderr == []
    assert stdout == []
  
def test_sed_expression_order_changes_result(cl, shell_sed):
    stderr, stdout = cl.enter_command(
        "sed -e 's/dog/wolf/' -e 's/cat/dog/' f1.txt",
        shell_sed
    )

    assert stderr == []
    assert stdout == [
        "dog wolf dog",
        "hi dog"
    ]

def test_sed_reverse_range(cl, shell_sed):
    stderr, stdout = cl.enter_command(
      "sed '5,2d' f3.txt",
      shell_sed
    )

    assert stderr == []

def test_sed_bad_address(cl, shell_sed):
    stderr, stdout = cl.enter_command(
      "sed 'x,4d' f1.txt",
      shell_sed
    )

    assert stdout == []
    assert stderr == ["sed: expected int, got x,4"]

def test_sed_inplace_backup(cl, shell_sed):
    old = shell_sed.fs.get_file("f1.txt").get_data()
    stderr, stdout = cl.enter_command(
      "sed -i.bak 's/cat/dog/g' f1.txt",
      shell_sed
    )

    assert stderr == []
    assert stdout == []
    fn = shell_sed.fs.get_file("f1.txt.bak")
    print (shell_sed.fs.current.items)
    assert isinstance(fn, FileNode)
    assert fn.get_data() == old
    new = shell_sed.fs.get_file("f1.txt")
    assert isinstance(new, FileNode)
    assert new.get_data() == "dog wolf dog\nhi dog"
    

def test_sed_overlapping(cl, shell_sed):
    shell_sed.fs.current.items[0].set_data("aaaa")

    stderr, stdout = cl.enter_command(
      "sed 's/aa/b/g' f1.txt",
      shell_sed
    )

    assert stdout == ["bb"]

def test_sed_negated_line_address(cl, shell_sed):
    stderr, stdout = cl.enter_command(
      "sed '2!d' f1.txt",
      shell_sed
    )

    assert stderr == []
    assert stdout == [
      "hi cat"
    ]

# ---------- BASIC ----------

def test_wc_l_empty_file(cl, shell_emptyfile: ShellState):
    stderr, stdout = cl.enter_command('wc -l empty.txt', shell_emptyfile)
    assert stderr == []
    assert stdout == ["0"]


def test_wc_l_single_line_no_newline(cl, shell_one_line_no_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -l f1.txt', shell_one_line_no_newline)
    assert stderr == []
    assert stdout == ["0"]


def test_wc_l_single_line_with_newline(cl, shell_one_line_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -l f1.txt', shell_one_line_newline)
    assert stderr == []
    assert stdout == ["1"]


def test_wc_l_two_lines(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('wc -l f1.txt', shell_sed)
    assert stderr == []
    assert stdout == ["2"]


# ---------- BLANK LINES ----------

def test_wc_l_blank_lines(cl, shell_blank_lines: ShellState):
    stderr, stdout = cl.enter_command('wc -l blank.txt', shell_blank_lines)
    assert stderr == []
    assert stdout == ["3"]


def test_wc_l_only_newlines(cl, shell_only_newlines: ShellState):
    stderr, stdout = cl.enter_command('wc -l nl.txt', shell_only_newlines)
    assert stderr == []
    assert stdout == ["4"]


def test_wc_l_whitespace_lines_count(cl, shell_whitespace_lines: ShellState):
    stderr, stdout = cl.enter_command('wc -l white.txt', shell_whitespace_lines)
    assert stderr == []
    assert stdout == ["3"]


# ---------- PIPE INPUT ----------

def test_wc_l_pipe_cat(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | wc -l', shell_sed)
    assert stderr == []
    assert stdout == ["2"]


def test_wc_l_pipe_empty(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('ls | wc -l', shell_empty)
    assert stderr == []
    assert stdout == ["0"]


def test_wc_l_pipe_grep(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | grep cat | wc -l', shell_sed)
    assert stderr == []
    assert stdout == ["2"]


def test_wc_l_pipe_filtered_single(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command(
        'cat f1.txt | grep wolf | wc -l',
        shell_sed
    )
    assert stderr == []
    assert stdout == ["1"]


def test_wc_l_pipe_no_matches(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command(
        'cat f1.txt | grep zebra | wc -l',
        shell_sed
    )
    assert stderr == []
    assert stdout == ["0"]


# ---------- MULTIPLE FILES ----------

def test_wc_l_two_files(cl, shell_twofiles: ShellState):
    stderr, stdout = cl.enter_command('wc -l f1.txt f2.txt', shell_twofiles)
    assert stderr == []
    assert stdout == [
        "2 f1.txt",
        "3 f2.txt",
        "5 total"
    ]


def test_wc_l_multiple_files_one_empty(cl, shell_mixfiles: ShellState):
    stderr, stdout = cl.enter_command(
        'wc -l a.txt b.txt',
        shell_mixfiles
    )
    assert stderr == []
    assert stdout == [
        "0 a.txt",
        "4 b.txt",
        "4 total"
    ]


# ---------- EDGE CASES ----------

def test_wc_l_file_not_found(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('wc -l fake.txt', shell_basic)
    assert stdout == []
    assert len(stderr) > 0


def test_wc_l_directory_error(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('wc -l d1', shell_basic)
    assert stdout == []
    assert stderr == ["wc: cannot perform operation on directory (d1)"]


def test_wc_l_no_arguments(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('wc -l', shell_basic)
    # depends whether your shell reads stdin or errors
    assert stderr == [] or len(stderr) > 0


# ---------- STRESS / ODDITIES ----------

def test_wc_l_large_file(cl, shell_largefile: ShellState):
    stderr, stdout = cl.enter_command('wc -l huge.txt', shell_largefile)
    assert stderr == []
    assert stdout == ["1000"]


def test_wc_l_trailing_newline_matters(cl, shell_trailing_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -l t.txt', shell_trailing_newline)
    assert stderr == []
    assert stdout == ["2"]


def test_wc_l_no_final_newline(cl, shell_no_final_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -l t.txt', shell_no_final_newline)
    assert stderr == []
    assert stdout == ["1"]