import os
import random
import time
from datetime import datetime

import pytest
from game.filenode import FileNode
from game.filesystem import FileSystem
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_success
from tests.cmd_tests.path_helpers import tree_state
from tests.command_helpers import assert_help

LS_FILES = [
    "xms.bin",
    "silly.c",
    "sigma.dat",
    "crap.js",
    "sheet.xsl",
    "nope.csv",
    "nothing.log",
    "cool.png",
    "record.ods",
    "stuff.sql",
    "annoying.java",
    "yikes.py",
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
    CmdResult = cl.enter_command("ls", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_ls_error(cl, shell_empty):
    CmdResult = cl.enter_command("ls -y", shell_empty)
    assert CmdResult.stderr == ["ls: unknown argument given"]
    assert CmdResult.stdout == []


def test_ls_target(cl, shell_basic):
    CmdResult = cl.enter_command("ls d1", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f3.txt", "f4.txt"]


def test_ls_basic(cl, shell_fouritems):
    CmdResult = cl.enter_command("ls", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f1.txt", "f2.txt", "f3.txt", "f4.txt"]


def test_ls_reverse(cl, shell_fouritems):
    CmdResult = cl.enter_command("ls -r", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f4.txt", "f3.txt", "f2.txt", "f1.txt"]


def test_ls_deep(cl, shell_basic):
    CmdResult = cl.enter_command("ls -R", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f1.txt", "f2.txt", "d1", "/d1/f3.txt", "/d1/f4.txt"]


def test_ls_organisation(cl, shell_ls: ShellState):
    CmdResult = cl.enter_command("ls -X", shell_ls)
    files = LS_FILES.copy()
    print(files)
    assert CmdResult.stderr == []
    sorted_files = sorted(files, key=lambda f: os.path.splitext(f)[1])
    assert CmdResult.stdout == sorted_files

    CmdResult = cl.enter_command("ls -S", shell_ls)
    assert CmdResult.stderr == []
    for i in range(0, 5):
        assert CmdResult.stdout[i] == sizes[i]

    CmdResult = cl.enter_command("ls -t", shell_ls)
    times = sizes.copy()
    times.reverse()
    assert CmdResult.stderr == []
    for i in range(0, 5):
        assert CmdResult.stdout[i] == times[i]

    CmdResult = cl.enter_command("ls -u", shell_ls)
    atimes.reverse()
    assert CmdResult.stderr == []
    for i in range(0, 5):
        assert CmdResult.stdout[i] == atimes[i]

    CmdResult = cl.enter_command("ls -c", shell_ls)
    assert CmdResult.stderr == []
    for i in range(0, 5):
        assert CmdResult.stdout[i] == LS_FILES[-(i + 1)]


def test_ls_help(cl, shell_empty):
    assert_help(cl, shell_empty, "ls")


@pytest.mark.parametrize("options", ["", "-a", "-A", "-la", "-iA", "-Ra"])
def test_ls_dot_paths_leave_tree_unchanged(
    run_dot_command, dot_shell, dot_directory, options
):
    operand, _ = dot_directory
    before = tree_state(dot_shell)
    # The shared check runs after each listing, before a cycle could reach the
    # next recursive command or serialization.
    for _ in range(2):
        result = run_dot_command(f"ls {options} {operand}")
        assert result.status == 0
        assert result.stderr == []
    assert tree_state(dot_shell) == before


@pytest.mark.parametrize("option", ["-a", "-A"])
def test_ls_dot_paths_show_virtual_entries(run_dot_command, dot_directory, option):
    operand, target = dot_directory
    expected = {item.name for item in target.items}
    if option == "-a":
        expected.update((".", ".."))
    result = run_dot_command(f"ls {option} {operand}")
    assert result.status == 0
    assert result.stderr == []
    assert set(result.stdout) == expected
    assert len(result.stdout) == len(expected)


def test_ls_dot_paths_regular_file(run_dot_command, dot_prefix):
    path = f"{dot_prefix}data.txt"
    assert_success(run_dot_command(f"ls {path}"), [path])


def test_ls_one_directory_entry_is_not_an_error(run_dot_command):
    assert_success(run_dot_command("ls branch"), ["leaf.txt"])


def test_ls_missing_path_reports_failure(run_dot_command):
    result = run_dot_command("ls missing")
    assert result.status != 0
    assert result.stdout == []
    assert any("missing" in message for message in result.stderr)


def test_ls_file_operand_uses_its_own_metadata(run_dot_command, dot_shell):
    file = dot_shell.fs.current.access("data.txt")
    file.inode.mtime = datetime(2001, 1, 2)

    result = run_dot_command("ls -li ./data.txt")

    assert_success(
        result,
        [
            f"{file.inode.id} {file.get_permission_str(file)} 1 user user "
            f"{file.get_size()} Jan 2 2001 ./data.txt"
        ],
    )
