import pytest
import datetime
import random
from game.ShellState import ShellState
from game.filesystem import FileSystem
from game.commandline import CommandLine
from game.filenode import FileNode, Inode, NodeType
import time

LS_FILES = ["xms.bin", "silly.c", "sigma.dat", "crap.js", 
             "sheet.xsl", "nope.csv", "nothing.log", "cool.png",
             "record.ods", "stuff.sql", "annoying.java", "yikes.py"
        ]

random.shuffle(LS_FILES)

f = random.sample(LS_FILES, 10)
sizes = f[0:5]
atimes = f[5:]

@pytest.fixture
def cl():
    return CommandLine()

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
    inode.set_data(["ERROR 1", "ERROR 2", "INFO 1"])
    fn = FileNode(None, "f1.txt", inode)
    fs.add_file("f1.txt", fn)
    inode = Inode(NodeType.FILE)
    inode.set_data(["ERROR 3", "ERROR 4", "INFO 2"])
    fn = FileNode(None, "f2.txt", inode)
    fs.add_file("f2.txt", fn)
    fs.add_file("f3.txt")
    fs.add_file("f4.txt")
    return fs

@pytest.fixture
def fs_basic():
    fs = FileSystem()
    fs.add_file("f1.txt")
    fs.current.items[0].set_data(["ERROR no", "INFO hey", "ERROR no2", "error 1"])
    fs.add_file("f2.txt")
    fs.current.items[1].set_data([str(i) for i in range(25)])
    fs.add_directory("d1")
    fs.add_file("d1/f3.txt")
    inode = Inode(NodeType.FILE)
    inode.set_data(["ERROR 1", "ERROR 2", "INFO 1"])
    fn = FileNode(None, "f4.txt", inode)
    fs.add_file("d1/f4.txt", fn)
    return fs

@pytest.fixture
def fs_sed():
    fs = FileSystem()
    fs.add_file("f1.txt")
    fs.current.items[0].set_data(["cat wolf cat", "hi cat"])
    fs.add_file("f2.txt")
    fs.current.items[1].set_data(["cat CaT Cat"])
    fs.add_file("f3.txt")
    fs.current.items[2].set_data(["cat wolf cat", "hi cat", " whats up", " the cat", " test cat here"])
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
    for file in LS_FILES:
        time.sleep(0.1)
        fs.add_file(file)
    time.sleep(0.5)
    fn = fs.get_file(sizes[0])
    assert isinstance(fn, FileNode)
    fn.set_data(["123456789" * 1000])
    fn = fs.get_file(atimes[0])
    assert isinstance(fn, FileNode)
    fn.get_data()
    time.sleep(0.1)
    fn = fs.get_file(sizes[1])
    assert isinstance(fn, FileNode)
    fn.set_data(["123456789" * 100])
    fn = fs.get_file(atimes[1])
    assert isinstance(fn, FileNode)
    fn.get_data()
    time.sleep(0.1)
    fn = fs.get_file(sizes[2])
    assert isinstance(fn, FileNode)
    fn.set_data(["123456789" * 50])
    fn = fs.get_file(atimes[2])
    assert isinstance(fn, FileNode)
    fn.get_data()
    time.sleep(0.1)
    fn = fs.get_file(sizes[3])
    assert isinstance(fn, FileNode)
    fn.set_data(["123456789" * 10])
    fn = fs.get_file(atimes[3])
    assert isinstance(fn, FileNode)
    fn.get_data()
    time.sleep(0.1)
    fn = fs.get_file(sizes[4])
    assert isinstance(fn, FileNode)
    fn.set_data(["123456789" * 1])
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
    fn.set_data([])
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
    fn.set_data(["hello"])
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
    fn.set_data(["hello"])
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
    fn.set_data(["", "", ""])
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
    fn.set_data(["", "", "", ""])
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
    fn.set_data(["   ", "\t", "hello"])
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
    fn.set_data(["a", "b"])

    fs.add_file("f2.txt")
    fn = fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    fn.set_data(["1", "2", "3"])

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
    fn.set_data([])

    fs.add_file("b.txt")
    fn = fs.get_file("b.txt")
    assert isinstance(fn, FileNode)
    fn.set_data(["1", "2", "3", "4"])

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
    fn.set_data([str(i) for i in range(1000)])

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
    fn.set_data(["a", "b"])

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
    fn.set_data(["a", "b"])

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