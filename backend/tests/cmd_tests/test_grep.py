from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error, descendants
from tests.command_helpers import assert_help


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


def test_grep_help(cl, shell_empty):
    assert_help(cl, shell_empty, "grep")


def test_grep_dot_paths_read_file(run_dot_command, dot_prefix):
    result = run_dot_command(f"grep : {dot_prefix}data.txt")
    assert_success(result, ["beta:2", "alpha:1", "alpha:1"])


def test_grep_dot_paths_reject_directory(run_dot_command, dot_directory):
    operand, _ = dot_directory
    result = run_dot_command(f"grep : {operand}")
    assert_directory_error(result)


def test_grep_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    result = run_dot_command(f"grep : {invalid_dot_path}")
    assert_failure(result)


def test_grep_dot_paths_preserve_literal_dot_names(run_dot_command):
    result = run_dot_command("grep : ./..backup")
    assert_success(result, ["literal:5"])


def test_grep_dot_paths_recursive_search(run_dot_command, dot_directory):
    operand, target = dot_directory
    expected = [line for node in descendants(target) for line in node.inode.data]
    result = run_dot_command(f"grep -r : {operand}")
    assert result.status == 0
    assert result.stderr == []
    assert sorted(result.stdout) == sorted(expected)


def test_grep_dot_paths_read_parent_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    parent = current.parent if current.parent is not None else current
    lines = list(parent.access("data.txt").inode.data)
    result = run_dot_command("grep : ../data.txt")
    assert_success(result, lines)
