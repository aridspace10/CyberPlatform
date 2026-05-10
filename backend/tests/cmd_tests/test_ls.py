import pytest

from game.filesystem import FileSystem
from game.ShellState import ShellState
from game.filenode import FileNode
from game.commandline import CommandLine
import random
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

@pytest.fixture
def shell_ls(fs_ls):
    s = ShellState()
    s.fs = fs_ls
    s.cwd = "/"
    return s

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
    print (files)
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
    assert stderr == []
    for i in range(0, 5):
        assert stdout[i] == LS_FILES[-(i+1)]