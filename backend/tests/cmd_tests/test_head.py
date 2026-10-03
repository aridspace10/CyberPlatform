import math
import random

from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error
from tests.command_helpers import assert_help


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


def test_head_error(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("head d1", shell_basic)
    assert CmdResult.stderr == ["head: d1 is a directory"]


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


def test_head_help(cl, shell_empty):
    assert_help(cl, shell_empty, "head")


def test_head_dot_paths_read_file(run_dot_command, dot_prefix):
    result = run_dot_command(f"head -n 1 {dot_prefix}data.txt")
    assert_success(result, ["beta:2"])


def test_head_dot_paths_reject_directory(run_dot_command, dot_directory):
    operand, _ = dot_directory
    result = run_dot_command(f"head -n 1 {operand}")
    assert_directory_error(result)


def test_head_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    result = run_dot_command(f"head -n 1 {invalid_dot_path}")
    assert_failure(result)


def test_head_dot_paths_preserve_literal_dot_names(run_dot_command):
    result = run_dot_command("head -n 1 ./..backup")
    assert_success(result, ["literal:5"])


def test_head_dot_paths_read_parent_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    parent = current.parent if current.parent is not None else current
    lines = list(parent.access("data.txt").inode.data)
    result = run_dot_command("head -n 1 ../data.txt")
    assert_success(result, lines[:1])
