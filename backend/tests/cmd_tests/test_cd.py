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


def test_cd_requires_directory_search_permission(cl, shell_basic):
    directory = shell_basic.fs.filehead.access("d1")
    directory.inode.permissions["user"]["x"] = False
    assert_failure(cl.enter_command("cd d1", shell_basic))
    assert shell_basic.fs.current is shell_basic.fs.filehead


def test_cd_dot_paths_reject_file(run_dot_command, dot_prefix):
    assert_failure(run_dot_command(f"cd {dot_prefix}data.txt"))


def test_cd_restores_root_and_canonical_paths(cl, shell_basic):
    assert_success(cl.enter_command("cd d1", shell_basic))
    assert shell_basic.fs.cwd == "/d1"
    assert shell_basic.cwd == "/d1"
    assert_success(cl.enter_command("cd /", shell_basic))
    assert shell_basic.fs.current is shell_basic.fs.filehead
    assert shell_basic.fs.cwd == "/"
    assert shell_basic.cwd == "/"
    assert_success(cl.enter_command("pwd", shell_basic), ["/"])


def test_cd_failure_from_non_root_preserves_all_state(cl, shell_basic):
    assert_success(cl.enter_command("cd d1", shell_basic))
    current = shell_basic.fs.current
    fs_cwd = shell_basic.fs.cwd
    shell_cwd = shell_basic.cwd

    result = cl.enter_command("cd d1/missing", shell_basic)

    assert_failure(result)
    assert shell_basic.fs.current is current
    assert shell_basic.fs.cwd == fs_cwd
    assert shell_basic.cwd == shell_cwd


def test_cd_rejects_files_without_changing_state(cl, shell_basic):
    current = shell_basic.fs.current
    fs_cwd = shell_basic.fs.cwd
    shell_cwd = shell_basic.cwd

    result = cl.enter_command("cd f1.txt", shell_basic)

    assert_failure(result)
    assert result.stderr == ["cd: f1.txt is not a directory"]
    assert shell_basic.fs.current is current
    assert shell_basic.fs.cwd == fs_cwd
    assert shell_basic.cwd == shell_cwd


def test_cd_normalizes_repeated_and_trailing_slashes(cl, shell_basic):
    assert_success(cl.enter_command("cd d1///./", shell_basic))
    assert shell_basic.fs.cwd == "/d1"
    assert shell_basic.cwd == "/d1"


def test_cd_and_sequence(cl, shell_basic: ShellState):
    result = cl.enter_command("cd d1 && ls", shell_basic)
    assert result.stderr == []
    assert result.stdout == ["f3.txt", "f4.txt"]


def test_cd_subshell_keeps_parent_cwd(cl, shell_basic: ShellState):
    result = cl.enter_command("(cd d1 && ls)", shell_basic)
    assert result.stderr == []
    assert result.stdout == ["f3.txt", "f4.txt"]
    result = cl.enter_command("ls", shell_basic)
    assert result.stderr == []
    assert result.stdout == ["f1.txt", "f2.txt", "d1"]

def test_cd_semicolon_sequence(cl, shell_basic: ShellState):
    result = cl.enter_command("cd d1; ls", shell_basic)
    assert result.stderr == []
    assert result.stdout == ["f3.txt", "f4.txt"]


def test_cd_and_failure_stops_sequence(cl, shell_basic):
    result = cl.enter_command("cd d3 && ls", shell_basic)
    assert result.stderr == ["cd:No directory named d3"]
    assert result.stdout == []
