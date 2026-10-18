from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.command_helpers import assert_help
from tests.filesystem_helpers import restored_filesystem


def test_cd_help(cl, shell_empty):
    assert_help(cl, shell_empty, "cd")


def test_cd_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("cd d1", shell_basic)
    assert CmdResult.stderr == []
    assert len(shell_basic.fs.current.items) == 2


def test_cd_parent_after_filesystem_restore(cl, shell_basic: ShellState):
    shell_basic.fs = restored_filesystem(shell_basic.fs)

    assert_success(cl.enter_command("cd d1", shell_basic))
    assert shell_basic.fs.current.parent is shell_basic.fs.filehead
    assert_success(cl.enter_command("cd ..", shell_basic))
    assert shell_basic.fs.current is shell_basic.fs.filehead


def test_cd_missing(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("cd missing", shell_empty)
    assert CmdResult.stderr == ["cd:No directory named missing"]
    assert CmdResult.stdout == []


def test_cd_empty(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("cd", shell_empty)
    assert CmdResult.stderr == ["cd: must give argument"]
    assert CmdResult.stdout == []


def test_cd_dot_paths_keep_state_canonical(run_dot_command, dot_directory):
    operand, target = dot_directory
    assert_success(run_dot_command(f"cd {operand}", navigates_to=target))


def test_cd_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    assert_failure(run_dot_command(f"cd {invalid_dot_path}"))


def test_cd_dot_paths_reject_file(run_dot_command, dot_prefix):
    assert_failure(run_dot_command(f"cd {dot_prefix}data.txt"))
