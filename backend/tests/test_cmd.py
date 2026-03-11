import pytest
import datetime
import random
from game.commandline import CommandLine
from game.ShellState import ShellState
from game.filesystem import FileSystem
from game.filenode import FileNode, Inode, NodeType
from wonderwords import RandomWord

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

######## HELPS #################
def test_cmd_helps(cl, shell_empty):
    cmds = ['mkdir', 'cat', 'chmod', 'grep', 'head', 'ln', 'ls', 'mv', 'sort', 'touch']
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
    assert stderr == ['No directory named a']
    assert stdout == []
    assert len(shell_empty.fs.current.items) == 0

######### LS ###################
def test_ls_empty(cl, shell_empty):
    stderr, stdout = cl.enter_command('ls', shell_empty)
    assert stderr == []
    assert stdout == []

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

def test_redirection_rewrites_file(cl, shell_basic: ShellState, fs_basic: FileSystem):
    cl.enter_command('echo hi >> f1.txt', shell_basic)
    fs_basic.search('f1.txt')
    fnode = fs_basic.current
    assert fnode.get_data().strip() == "ERROR no\nINFO hey\nERROR no2\nhi"

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

def test_grep_matchline(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('grep -x \"ERROR no\" f1.txt', shell_basic)
    assert stderr == []
    assert stdout == ["ERROR no"]

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
    assert shell_basic.env["X"] == "5"

    stderr, stdout = cl.enter_command('echo $X', shell_basic)
    assert stderr == []
    assert stdout == ["5"]

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