import pytest

from game.filesystem import FileSystem
from game.ShellState import ShellState
from game.filenode import FileNode
from game.commandline import CommandLine

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

# def test_find_delete(cl, shell_basic: ShellState):
#     stderr, stdout = cl.enter_command('find . -type f -name f3.txt -delete', shell_basic)
#     assert stdout == []
#     assert stderr == []