from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error
from tests.command_helpers import assert_help


def test_cat_nonexistent_file(cl, shell_empty):
    # reading missing file returns error
    CmdResult = cl.enter_command("cat missing.txt", shell_empty)
    # cat sets CmdResult.stderr in CmdResult.stdout list per your implementation
    assert len(CmdResult.stderr) == 1


def test_cat_error(cl, shell_empty):
    cmd = cl.enter_command("cat -x missing.txt", shell_empty)
    assert cmd.stderr == ["cat: Unknown Argument Given (x)"]


def test_cat_numbering(cl, shell_basic):
    CmdResult = cl.enter_command("cat -n f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["1 ERROR no", "2 INFO hey", "3 ERROR no2", "4 error 1"]


def test_cat_stdin(cl, shell_basic):
    CmdResult = cl.enter_command("cat - < f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR no", "INFO hey", "ERROR no2", "error 1"]


def test_cat_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("cat f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR no", "INFO hey", "ERROR no2", "error 1"]


def test_cat_help(cl, shell_empty):
    assert_help(cl, shell_empty, "cat")


def test_cat_dot_paths_read_file(run_dot_command, dot_prefix):
    result = run_dot_command(f"cat {dot_prefix}data.txt")
    assert_success(result, ["beta:2", "alpha:1", "alpha:1"])


def test_cat_dot_paths_reject_directory(run_dot_command, dot_directory):
    operand, _ = dot_directory
    result = run_dot_command(f"cat {operand}")
    assert_directory_error(result)


def test_cat_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    result = run_dot_command(f"cat {invalid_dot_path}")
    assert_failure(result)


def test_cat_dot_paths_preserve_literal_dot_names(run_dot_command):
    result = run_dot_command("cat ./..backup")
    assert_success(result, ["literal:5"])


def test_cat_dot_paths_read_parent_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    parent = current.parent if current.parent is not None else current
    lines = list(parent.access("data.txt").inode.data)
    result = run_dot_command("cat ../data.txt")
    assert_success(result, lines)
