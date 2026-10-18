import pytest
from game.ShellState import ShellState
from game.identity import EffectiveIdentity
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error
from tests.command_helpers import assert_help


@pytest.mark.parametrize("lines", [[], ["cat", "", "wolf"]])
def test_cat_buffered_input(run_buffered_command, lines):
    assert_success(run_buffered_command("cat", lines), lines)


def test_cat_nonexistent_file(cl, shell_empty):
    result = cl.enter_command("cat missing.txt", shell_empty)
    assert result.status != 0
    assert result.stdout == []
    assert result.stderr == ["cat: missing.txt: No directory named missing.txt"]


def test_cat_error(cl, shell_empty):
    cmd = cl.enter_command("cat -x missing.txt", shell_empty)
    assert cmd.stderr == ["cat: Unknown Argument Given (x)"]


def test_cat_numbering(cl, shell_basic):
    CmdResult = cl.enter_command("cat -n f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["1 ERROR no", "2 INFO hey", "3 ERROR no2", "4 error 1"]


def test_cat_numbers_cumulatively_across_multiple_files(cl, shell_basic):
    result = cl.enter_command("cat -n f1.txt f2.txt", shell_basic)
    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == [
        "1 ERROR no", "2 INFO hey", "3 ERROR no2", "4 error 1",
        *[f"{number} {number - 5}" for number in range(5, 30)],
    ]


def test_cat_uses_owner_group_other_and_root_permissions(cl, shell_basic):
    node = shell_basic.fs.filehead.access("f1.txt")
    node.inode.owner = "owner"
    node.inode.group = "readers"
    node.inode.permissions = {
        "user": {"r": False, "w": False, "x": False},
        "group": {"r": True, "w": False, "x": False},
        "public": {"r": False, "w": False, "x": False},
    }

    shell_basic.identity = EffectiveIdentity("reader", "readers", frozenset({"readers"}))
    assert cl.enter_command("cat f1.txt", shell_basic).stdout == [
        "ERROR no",
        "INFO hey",
        "ERROR no2",
        "error 1",
    ]

    shell_basic.identity = EffectiveIdentity("visitor", "visitors", frozenset({"visitors"}))
    denied = cl.enter_command("cat f1.txt", shell_basic)
    assert denied.status != 0
    assert denied.stderr and "Permission denied" in denied.stderr[0]

    node.inode.permissions["public"]["r"] = True
    assert cl.enter_command("cat f1.txt", shell_basic).status == 0
    node.inode.permissions["public"]["r"] = False

    shell_basic.identity = EffectiveIdentity("root", "root", frozenset({"root"}), True)
    assert cl.enter_command("cat f1.txt", shell_basic).status == 0

def test_cat_stdin(cl, shell_basic):
    CmdResult = cl.enter_command("cat - < f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR no", "INFO hey", "ERROR no2", "error 1"]


def test_cat_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("cat f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR no", "INFO hey", "ERROR no2", "error 1"]


def test_cat_end_of_options_reads_dash_prefixed_file(cl, shell_basic):
    shell_basic.fs.add_file("-dash.txt")
    dash_file = shell_basic.fs.current.access("-dash.txt")
    dash_file.set_data(["dash content"])

    result = cl.enter_command("cat -- -dash.txt", shell_basic)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == ["dash content"]


def test_cat_end_of_options_allows_help_as_a_filename(cl, shell_basic):
    shell_basic.fs.add_file("--help")
    shell_basic.fs.current.access("--help").set_data(["literal filename"])

    result = cl.enter_command("cat -- --help", shell_basic)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == ["literal filename"]


def test_cat_mixed_operands_reports_errors_and_continues(cl, shell_basic):
    fs = shell_basic.fs
    before_cwd = (shell_basic.cwd, fs.cwd, fs.current)
    before_contents = {
        node.name: tuple(node.inode.data)
        for node in fs.current.items
        if node.inode.type.value == "file"
    }

    result = cl.enter_command("cat f1.txt missing.txt d1 f2.txt", shell_basic)

    assert result.status != 0
    assert result.stdout == [
        "ERROR no", "INFO hey", "ERROR no2", "error 1",
        *[str(number) for number in range(25)],
    ]
    assert len(result.stderr) == 2
    assert "missing.txt" in result.stderr[0]
    assert "d1" in result.stderr[1] and "director" in result.stderr[1].lower()
    assert (shell_basic.cwd, fs.cwd, fs.current) == before_cwd
    assert {
        node.name: tuple(node.inode.data)
        for node in fs.current.items
        if node.inode.type.value == "file"
    } == before_contents


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
