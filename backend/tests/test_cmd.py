import math
import random

from game.filenode import FileNode
from game.filesystem import FileSystem
from game.ShellState import ShellState
from wonderwords import RandomWord

from ..game.helpers import determine_perms_fromstr


######## HELPS #################
def test_cmd_helps(cl, shell_empty):
    cmds = [
        "mkdir",
        "cat",
        "chmod",
        "grep",
        "head",
        "ln",
        "ls",
        "mv",
        "sort",
        "touch",
        "rm",
        "sed",
        "ps",
        "ping",
    ]
    for cmd in cmds:
        CmdResult = cl.enter_command(f"{cmd} --help", shell_empty)
        with open(f"../static/help/{cmd}.txt") as f:
            assert CmdResult.stderr == []
            assert CmdResult.stdout == f.readlines()


####### Unknown #############
def test_cmd_unknown(cl, shell_empty):
    CmdResult = cl.enter_command("test abcd", shell_empty)
    assert CmdResult.stderr == ["Unknown command given"]
    assert CmdResult.stdout == []


######### ECHO #################
def test_echo_basic(cl, shell_empty):
    # echo should return CmdResult.stdout containing the args joined
    CmdResult = cl.enter_command("echo hello world", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hello world"]


######## MKDIR #################
def test_mkdir_basic(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("mkdir a", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 1
    assert shell_empty.fs.current.items[0].name == "a"

    CmdResult = cl.enter_command("mkdir a", shell_empty)
    assert CmdResult.stderr == ["mkdir: Filename 'a' already exists"]
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 1
    assert shell_empty.fs.current.items[0].name == "a"


def test_mkdir_none(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("mkdir", shell_empty)
    assert CmdResult.stderr == ["mkdir: at least one argument should be given"]
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 0


def test_mkdir_verbose(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("mkdir -v a", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["mkdir: sucessfully created a"]
    assert len(shell_empty.fs.current.items) == 1
    assert shell_empty.fs.current.items[0].name == "a"


def test_mkdir_error(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("mkdir a/b", shell_empty)
    assert CmdResult.stderr == ["mkdir: No directory named a"]
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 0

    CmdResult = cl.enter_command("mkdir -p", shell_empty)
    assert CmdResult.stderr == ["mkdir: no name given for new directory"]
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 0


def test_mkdir_permissions(cl, shell_empty: ShellState):
    perm_str = "".join([str(random.randint(1, 7)) for _ in range(0, 3)])
    perm = determine_perms_fromstr(perm_str)
    CmdResult = cl.enter_command(f"mkdir -m a={perm_str} a", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 1
    fn = shell_empty.fs.current.items[0]
    assert fn.name == "a"
    assert perm == fn.inode.permissions

    CmdResult = cl.enter_command("mkdir -m a=00 a", shell_empty)
    assert CmdResult.stderr == [
        "chmod: value given for permissions which is not of length of 3"
    ]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("mkdir -m randomstuff a", shell_empty)
    assert CmdResult.stderr == ["mkdir: option given to -m or --mode is not correct"]
    assert CmdResult.stdout == []


def test_mkdir_parents(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("mkdir -p a/b/c", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 1
    fn = shell_empty.fs.current.items[0]
    assert fn.name == "a"
    assert len(fn.items) == 1
    fn2 = fn.items[0]
    assert fn2.name == "b"
    assert len(fn2.items) == 1
    fn3 = fn2.items[0]
    assert fn3.name == "c"


####### CD ####################
def test_cd_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("cd d1", shell_basic)
    assert CmdResult.stderr == []
    assert len(shell_basic.fs.current.items) == 2


def test_cd_missing(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("cd missing", shell_empty)
    assert CmdResult.stderr == ["cd:No directory named missing"]
    assert CmdResult.stdout == []


def test_cd_empty(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("cd", shell_empty)
    assert CmdResult.stderr == ["cd: must give argument"]
    assert CmdResult.stdout == []


########### REDIRECTION ##########
def test_redirection_writes_file(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("echo hi > d1/f3.txt", shell_basic)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == []
    CmdResult = cl.enter_command("cat d1/f3.txt", shell_basic)
    assert CmdResult.stdout == ["hi"]
    assert CmdResult.stderr == []


def test_redirection_path_error(cl, shell_basic: ShellState, fs_basic):
    CmdResult = cl.enter_command("echo hi > not/f3.txt", shell_basic)
    assert CmdResult.stderr == ["No directory named not"]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("echo hi >> not/f3.txt", shell_basic)
    assert CmdResult.stderr == ["No directory named not"]
    assert CmdResult.stdout == []


def test_redirection_rewrites_file(cl, shell_basic: ShellState, fs_basic: FileSystem):
    cl.enter_command("echo hi >> f1.txt", shell_basic)
    fs_basic.search("f1.txt")
    fnode = fs_basic.current
    assert fnode.get_data() == ["ERROR no", "INFO hey", "ERROR no2", "error 1", "hi"]


def test_redirection_writes_newfile(cl, shell_basic: ShellState, fs_basic: FileSystem):
    cl.enter_command("echo hi >> f3.txt", shell_basic)
    fs_basic.search("f3.txt")
    fnode = fs_basic.current
    assert fnode.get_data() == ["hi"]


######### CAT ##############
def test_cat_nonexistent_file(cl, shell_empty):
    # reading missing file returns error
    CmdResult = cl.enter_command("cat missing.txt", shell_empty)
    # cat sets CmdResult.stderr in CmdResult.stdout list per your implementation
    assert len(CmdResult.stderr) == 1


def test_cat_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("cat f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR no", "INFO hey", "ERROR no2", "error 1"]


######## HEAD ##############
def test_head_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("head f2.txt", shell_basic)
    assert CmdResult.stderr == []
    for i, line in enumerate(CmdResult.stdout):
        assert line == str(i)


def test_head_count(cl, shell_basic: ShellState):
    r = random.randint(1, 20)
    CmdResult = cl.enter_command(f"head -n {r} f2.txt", shell_basic)
    assert CmdResult.stderr == []
    for i in range(r):
        assert CmdResult.stdout[i] == str(i)
    CmdResult = cl.enter_command(f"head --lines={r} f2.txt", shell_basic)
    assert CmdResult.stderr == []
    for i in range(r):
        assert CmdResult.stdout[i] == str(i)
    CmdResult = cl.enter_command(f"head --lines=-{r} f2.txt", shell_basic)
    assert CmdResult.stderr == []
    for i in range(r, 0):
        assert CmdResult.stdout[-i] == str(i)


def test_head_bytes(cl, shell_basic: ShellState):
    r = random.randint(5, 20)
    CmdResult = cl.enter_command(f"head -c {r} f2.txt", shell_basic)
    assert CmdResult.stderr == []
    expected_lines = math.ceil(r / 2)
    assert len(CmdResult.stdout) == expected_lines
    for i, line in enumerate(CmdResult.stdout):
        assert line == str(i)

    CmdResult = cl.enter_command(f"head --bytes={r} f2.txt", shell_basic)
    assert CmdResult.stderr == []
    expected_lines = math.ceil(r / 2)
    assert len(CmdResult.stdout) == expected_lines
    for i, line in enumerate(CmdResult.stdout):
        assert line == str(i)


######### TOUCH ############
def test_touch_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("touch --no-create f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)

    CmdResult = cl.enter_command("touch f3.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("touch -c f4.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert not isinstance(shell_basic.fs.get_file("f4.txt"), FileNode)

    CmdResult = cl.enter_command("touch -x", shell_basic)
    assert CmdResult.stderr == ["touch: unknown argument given"]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("touch -a --date=2025-01-01 f2.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    assert fn.inode.atime != fn.inode.mtime

    CmdResult = cl.enter_command("touch -m --date=2025-02-01 f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    fn = shell_basic.fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    assert fn.inode.atime != fn.inode.mtime


def test_touch_error(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("touch", shell_basic)
    assert CmdResult.stderr == ["touch: must give atleast one argument"]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("touch a/f1.txt", shell_basic)
    assert CmdResult.stderr == ["No directory named a"]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("touch -a", shell_basic)
    assert CmdResult.stderr == ["touch: no file given"]
    assert CmdResult.stdout == []


######## GREP ##############
def test_grep_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("grep ERROR f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR no", "ERROR no2"]


def test_grep_count(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("grep -c ERROR f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["2"]


def test_grep_error(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("grep -c", shell_basic)
    assert CmdResult.stderr == ["grep: pattern not given"]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("grep -a", shell_basic)
    assert CmdResult.stderr == ["grep: unknown argument given"]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("grep text notexist.txt", shell_basic)
    assert CmdResult.stderr == ["grep: notexist.txt can not be found"]
    assert CmdResult.stdout == []


def test_grep_matchline(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command('grep -x "ERROR no" f1.txt', shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR no"]


def test_grep_matchwhole(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("grep -i ERROR f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR no", "ERROR no2", "error 1"]


def test_grep_dir(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("grep -r ERROR .", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR 1", "ERROR 2", "ERROR 3", "ERROR 4"]


def test_grep_dir2(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("grep -r ERROR .", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR no", "ERROR no2", "ERROR 1", "ERROR 2"]


def test_grep_dir3(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("grep ERROR .", shell_basic)
    assert CmdResult.stderr == ["Can't recursivly search directory without -r option"]
    assert CmdResult.stdout == []


####### CHMOD #############
def test_chmod_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("chmod 000 f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    fn = shell_basic.fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    assert shell_basic.fs.current.get_permission_str(fn) == "----------"
    CmdResult = cl.enter_command("chmod 777 f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    fn = shell_basic.fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    assert shell_basic.fs.current.get_permission_str(fn) == "-rwxrwxrwx"
    CmdResult = cl.enter_command("chmod -Rv 000 d1", shell_basic)
    assert CmdResult.stdout == [
        "Updated permissions of d1 with d---------",
        "Updated permissions of f3.txt with ----------",
        "Updated permissions of f4.txt with ----------",
    ]
    assert CmdResult.stderr == []
    fn = shell_basic.fs.get_file("d1")
    assert isinstance(fn, FileNode)
    assert shell_basic.fs.current.get_permission_str(fn) == "d---------"
    assert isinstance(fn.items[0], FileNode)
    assert fn.get_permission_str(fn.items[0]) == "----------"


def test_chmod_errors(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("chmod -y 888 not_exist.txt", shell_basic)
    assert CmdResult.stderr == ["chmod: Unknown output given"]
    assert CmdResult.stdout == []
    CmdResult = cl.enter_command("chmod 777 not_exist.txt", shell_basic)
    assert CmdResult.stderr == ["chmod: No directory named not_exist.txt"]
    assert CmdResult.stdout == []
    CmdResult = cl.enter_command("chmod 888 f1.txt", shell_basic)
    assert CmdResult.stderr == ["chmod: value given which is higher then needed"]
    assert CmdResult.stdout == []
    CmdResult = cl.enter_command("chmod f1.txt", shell_basic)
    assert CmdResult.stderr == ["chmod: expected at least two arguments"]
    assert CmdResult.stdout == []
    CmdResult = cl.enter_command("chmod 21 f1.txt", shell_basic)
    assert CmdResult.stderr == [
        "chmod: value given for permissions which is not of length of 3"
    ]
    assert CmdResult.stdout == []
    CmdResult = cl.enter_command("chmod 6a5 f1.txt", shell_basic)
    assert CmdResult.stderr == [
        "chmod: value other then given integer given for permissions"
    ]
    assert CmdResult.stdout == []


######## AND OR ################
def test_andor(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("cd d1 && ls", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f3.txt", "f4.txt"]


def test_and_failure(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("cd d3 && ls", shell_basic)
    assert CmdResult.stderr == ["cd:No directory named d3"]
    assert CmdResult.stdout == []


######## LN ###################
def test_ln_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("ln f1.txt s1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    f1, f2 = shell_basic.fs.get_file("f1.txt"), shell_basic.fs.get_file("s1.txt")
    assert isinstance(f1, FileNode)
    assert isinstance(f2, FileNode)
    assert f1.get_data() == f2.get_data()
    CmdResult = cl.enter_command('echo "Example" >> f1.txt', shell_basic)
    f1, f2 = shell_basic.fs.get_file("f1.txt"), shell_basic.fs.get_file("s1.txt")
    assert isinstance(f1, FileNode)
    assert isinstance(f2, FileNode)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert f1.get_data() == f2.get_data()
    CmdResult = cl.enter_command('echo "Example2" >> s1.txt', shell_basic)
    f1, f2 = shell_basic.fs.get_file("f1.txt"), shell_basic.fs.get_file("s1.txt")
    assert isinstance(f1, FileNode)
    assert isinstance(f2, FileNode)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert f1.get_data() == f2.get_data()


######### MV ##################
def test_mv_rename(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("mv f1.txt", shell_basic)
    assert CmdResult.stderr == ["cp: expected at least two arguments"]
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


########## SUBSHELL #################
def test_subshell_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("(cd d1 && ls)", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f3.txt", "f4.txt"]
    CmdResult = cl.enter_command("ls", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f1.txt", "f2.txt", "d1"]


def test_semicolon_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("cd d1; ls", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f3.txt", "f4.txt"]


########## VAR #####################
def test_var_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("X=5", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert shell_basic.vars["X"] == "5"

    CmdResult = cl.enter_command("echo $X", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["5"]


def test_var_error(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("echo $X", shell_basic)
    assert CmdResult.stderr == ["Var Used which is unassigned: X"]
    assert CmdResult.stdout == []


######## SORT ######################
def setup_names(s: ShellState, name: str) -> list[str]:
    amount = random.randint(5, 25)
    names = []
    r = RandomWord()
    for _ in range(0, amount):
        names.append(r.word())
    s.fs.search(name)
    s.fs.current.set_data(names)
    s.fs.current = s.fs.filehead
    names.sort()
    return names


def test_sort_basic(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    CmdResult = cl.enter_command("sort f2.txt", shell_basic)
    assert CmdResult.stderr == []
    for i in range(0, len(names)):
        assert CmdResult.stdout[i] == names[i]


def test_sort_random(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    name = random.choice(names)
    names.append(name)
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    fn.append_data([name])
    CmdResult = cl.enter_command("sort -R f2.txt", shell_basic)
    assert CmdResult.stderr == []
    for i in range(0, len(names) - 1):
        if CmdResult.stdout[i] == name:
            assert CmdResult.stdout[i + 1] == name
            return
    assert False


def test_sort_dups(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    name = random.choice(names)
    names = names.copy()
    print(f"Extra name is {name}")
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    fn.append_data([name])
    print(fn.get_data())
    CmdResult = cl.enter_command("sort -u f2.txt", shell_basic)
    assert CmdResult.stderr == []
    # assert len(CmdResult.stdout) == len(names)
    print(CmdResult.stdout)
    print(names)
    for i in range(0, len(names)):
        assert CmdResult.stdout[i] == names[i]


def test_sort_output(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    CmdResult = cl.enter_command("sort -o f1.txt f2.txt", shell_basic)
    shell_basic.fs.search("f1.txt")
    data = shell_basic.fs.current.get_data()
    shell_basic.fs.current = shell_basic.fs.filehead
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    for i in range(0, len(names)):
        assert data[i] == names[i]


def test_sort_sorted(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    CmdResult = cl.enter_command("sort -o s1.txt f2.txt", shell_basic)
    shell_basic.fs.search("s1.txt")
    data = shell_basic.fs.current.get_data()
    shell_basic.fs.current = shell_basic.fs.filehead
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    for i in range(0, len(names)):
        assert data[i] == names[i]
    CmdResult = cl.enter_command("sort -C s1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert shell_basic.ls == 0
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    data_copy = fn.get_data().copy()
    random.shuffle(data_copy)
    fn.set_data(data_copy)
    CmdResult = cl.enter_command("sort -C f2.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert shell_basic.ls == 0
    CmdResult = cl.enter_command("sort -c f2.txt", shell_basic)
    assert len(CmdResult.stderr)
    assert CmdResult.stderr[0].startswith("sort:")
    assert CmdResult.stdout == []
    assert shell_basic.ls == 0


######### PIPES #################
def test_pipes_lsgrep(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("ls | grep f", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f1.txt", "f2.txt"]


def test_pipes_lshead(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("ls | head --lines=2", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f1.txt", "f2.txt"]


def test_pipes_lshead2(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("ls | head", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_pipes_sortuniq(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    name = random.choice(names)
    names = names.copy()
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    fn.append_data([name])
    CmdResult = cl.enter_command("sort f2.txt | uniq", shell_basic)
    assert CmdResult.stderr == []
    assert len(CmdResult.stdout) == len(names)
    for i in range(0, len(names)):
        assert CmdResult.stdout[i] == names[i]


def test_pipes_lsgrep_inverse(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("ls | grep -v f1", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f2.txt", "d1"]


def test_pipes_lssort(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("ls | sort", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == sorted(CmdResult.stdout)


def test_pipes_ls_tail(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("ls | tail --lines=2", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f3.txt", "f4.txt"]


def test_pipes_catgrep(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | grep cat", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat wolf cat", "hi cat"]


def test_pipes_catgrephead(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | grep cat | head --lines=1", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat wolf cat"]


def test_pipes_catgreptail(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | grep cat | tail --lines=1", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hi cat"]


def test_pipes_catwc_lines(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | wc -l", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["2"]


def test_pipes_catwc_words(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | wc -w", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["5"]


def test_pipes_cat_sort(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | sort", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == sorted(CmdResult.stdout)


def test_pipes_catuniq(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f2.txt | uniq", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat CaT Cat"]


def test_pipes_grep_wc(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | grep cat | wc -l", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["2"]


def test_pipes_lsgrepwc(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("ls | grep txt | wc -l", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["2"]


def test_pipes_multiple_grep(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | grep cat | grep wolf", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat wolf cat"]


def test_pipes_head_tail_combo(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command(
        "ls | head --lines=3 | tail --lines=1", shell_fouritems
    )
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f3.txt"]


def test_pipes_ls_grep_no_match(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("ls | grep xyz", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_pipes_empty_chain(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("ls | grep f | wc -l", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["0"]


def test_pipes_long_chain(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command(
        "cat f1.txt | grep cat | sort | head --lines=1 | wc -w", shell_sed
    )
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["3"]


def test_pipes_cat_grep_ignorecase(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f2.txt | grep -i cat", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat CaT Cat"]


def test_pipes_ls_head_wc(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("ls | head --lines=3 | wc -l", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["3"]


def test_pipes_sort_tail(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("ls | sort | tail --lines=1", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f4.txt"]


######### CP ###################
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
