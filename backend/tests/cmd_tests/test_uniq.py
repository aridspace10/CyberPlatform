from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error
from tests.command_helpers import assert_help


def test_uniq_help(cl, shell_empty):
    assert_help(cl, shell_empty, "uniq")


def test_uniq_dot_paths_read_file(run_dot_command, dot_prefix):
    result = run_dot_command(f"uniq {dot_prefix}data.txt")
    assert_success(result, ["beta:2", "alpha:1"])


def test_uniq_dot_paths_reject_directory(run_dot_command, dot_directory):
    operand, _ = dot_directory
    result = run_dot_command(f"uniq {operand}")
    assert_directory_error(result)


def test_uniq_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    result = run_dot_command(f"uniq {invalid_dot_path}")
    assert_failure(result)


def test_uniq_dot_paths_preserve_literal_dot_names(run_dot_command):
    result = run_dot_command("uniq ./..backup")
    assert_success(result, ["literal:5"])


def test_uniq_dot_paths_read_parent_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    parent = current.parent if current.parent is not None else current
    lines = list(parent.access("data.txt").inode.data)
    result = run_dot_command("uniq ../data.txt")
    assert_success(
        result, [line for i, line in enumerate(lines) if i == 0 or line != lines[i - 1]]
    )
