import math
import random
from pathlib import Path

import pytest
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error, tree_state
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


@pytest.mark.parametrize(
    "command", ["head -n", "head -n nope", "head -c", "head --bytes="]
)
def test_head_invalid_count_is_a_command_error_without_mutation(
    cl, shell_basic, command
):
    before = tree_state(shell_basic)
    result = cl.enter_command(command, shell_basic)
    assert_failure(result)
    assert result.stderr
    assert tree_state(shell_basic) == before


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


def test_missing_help_resource_returns_safe_command_output(
    cl, shell_empty, monkeypatch
):
    original_read_text = Path.read_text

    def missing_help(path, *args, **kwargs):
        if path.name == "head.txt":
            raise OSError("simulated missing help resource")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", missing_help)
    result = cl.enter_command("head --help", shell_empty)
    assert result.status == 0
    assert result.stdout == ["head: help is unavailable"]
    assert result.stderr == []


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
