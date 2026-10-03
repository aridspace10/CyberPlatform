"""mkdir tests, including the CYB-24 regression contract and legacy cases.

Run from backend with:
    python -m pytest tests/cmd_tests/test_mkdir.py -o addopts= -p no:cacheprovider

Required mode syntax: three octal digits (-m/--mode/--mode=).
Regressions remain ordinary failures until fixed.
Shared helpers inspect children directly to avoid lookup and cwd side effects.
"""

from copy import deepcopy

import pytest
from game.inode import NodeType
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import (
    assert_created,
    assert_failure,
    assert_success,
    node_at,
)


@pytest.mark.parametrize("command,node_type", [("mkdir", NodeType.DIRECTORY)])
@pytest.mark.parametrize(
    "operand,expected_path",
    [
        ("new", "work/new"),
        ("parent/new", "work/parent/new"),
        ("./parent/new", "work/parent/new"),
        ("../other/new", "other/new"),
        ("../../new", "new"),
        ("/other/new", "other/new"),
    ],
)
def test_mkdir_creation_places_basename_under_correct_parent(
    run_creation, creation_shell, command, node_type, operand, expected_path
):
    result = run_creation(f"{command} {operand}")

    node = assert_created(creation_shell, expected_path, node_type)
    assert node.inode.data == []
    assert node.items == []
    assert_success(result)


@pytest.mark.parametrize("command,node_type", [("mkdir", NodeType.DIRECTORY)])
def test_mkdir_creation_processes_every_operand(
    run_creation, creation_shell, command, node_type
):
    result = run_creation(f"{command} first parent/second third")

    for path in ("work/first", "work/parent/second", "work/third"):
        assert_created(creation_shell, path, node_type)
    assert node_at(creation_shell, "work/parent/third") is None
    assert_success(result)


@pytest.mark.parametrize("command,node_type", [("mkdir", NodeType.DIRECTORY)])
@pytest.mark.parametrize(
    "operands",
    [
        "parent/missing/child blocker/child first second",
        "first parent/missing/child blocker/child second",
        "first second parent/missing/child blocker/child",
    ],
    ids=["failures-first", "failures-middle", "failures-last"],
)
def test_mkdir_creation_reports_each_failure_and_keeps_processing(
    run_creation, creation_shell, command, node_type, operands
):
    blocker = node_at(creation_shell, "work/blocker")
    original_blocker = deepcopy(blocker.to_dict())

    result = run_creation(f"{command} {operands}")

    assert_created(creation_shell, "work/first", node_type)
    assert_created(creation_shell, "work/second", node_type)
    assert node_at(creation_shell, "work/parent/missing") is None
    assert node_at(creation_shell, "work/parent/first") is None
    assert node_at(creation_shell, "work/parent/second") is None
    assert blocker.to_dict() == original_blocker
    assert_failure(result)
    assert any("missing" in message for message in result.stderr)
    assert any("blocker" in message for message in result.stderr)


@pytest.mark.parametrize("option", ["-p", "--parents"])
def test_mkdir_parents_creates_all_components_and_is_idempotent(
    run_creation, creation_shell, option
):
    first = run_creation(f"mkdir {option} parent/one/two")

    one = assert_created(creation_shell, "work/parent/one", NodeType.DIRECTORY)
    two = assert_created(creation_shell, "work/parent/one/two", NodeType.DIRECTORY)
    assert_success(first)
    original = deepcopy(two.to_dict())

    second = run_creation(f"mkdir {option} parent/one/two")

    assert node_at(creation_shell, "work/parent/one") is one
    assert node_at(creation_shell, "work/parent/one/two") is two
    assert two.to_dict() == original
    assert_success(second)


@pytest.mark.parametrize("operand", ["parent", ".", "..", "../..", "/"])
def test_mkdir_parents_accepts_existing_directories_without_changes(
    run_creation, creation_shell, operand
):
    before = deepcopy(creation_shell.fs.filehead.to_dict())

    result = run_creation(f"mkdir -p {operand}")

    assert creation_shell.fs.filehead.to_dict() == before
    assert_success(result)


def test_mkdir_without_parents_rejects_existing_directory_and_continues(
    run_creation, creation_shell
):
    parent = node_at(creation_shell, "work/parent")
    before = deepcopy(parent.to_dict())

    result = run_creation("mkdir first parent last")

    assert node_at(creation_shell, "work/parent") is parent
    assert parent.to_dict() == before
    assert_created(creation_shell, "work/first", NodeType.DIRECTORY)
    assert_created(creation_shell, "work/last", NodeType.DIRECTORY)
    assert_failure(result)
    assert any("parent" in message for message in result.stderr)


@pytest.mark.parametrize("command", ["mkdir", "mkdir -p"])
@pytest.mark.parametrize("operand", ["blocker/child", "blocker/child/grandchild"])
def test_mkdir_creation_rejects_non_directory_components_without_mutation(
    run_creation, creation_shell, command, operand
):
    before = deepcopy(creation_shell.fs.filehead.to_dict())

    result = run_creation(f"{command} {operand}")

    assert creation_shell.fs.filehead.to_dict() == before
    assert_failure(result)
    assert any("blocker" in message for message in result.stderr)


def test_mkdir_parents_rejects_existing_file_as_final_component(
    run_creation, creation_shell
):
    before = deepcopy(creation_shell.fs.filehead.to_dict())

    result = run_creation("mkdir -p blocker")

    assert creation_shell.fs.filehead.to_dict() == before
    assert_failure(result)


@pytest.mark.parametrize("option", ["-v", "--verbose"])
def test_mkdir_verbose_reports_every_created_directory(
    run_creation, creation_shell, option
):
    result = run_creation(f"mkdir {option} first parent/second")

    assert_created(creation_shell, "work/first", NodeType.DIRECTORY)
    assert_created(creation_shell, "work/parent/second", NodeType.DIRECTORY)
    assert result.status == 0
    assert result.stderr == []
    assert len(result.stdout) == 2
    assert "first" in result.stdout[0]
    assert "parent/second" in result.stdout[1]


def test_mkdir_verbose_reports_only_created_operands(run_creation, creation_shell):
    result = run_creation("mkdir -v first parent last")

    assert_created(creation_shell, "work/first", NodeType.DIRECTORY)
    assert_created(creation_shell, "work/last", NodeType.DIRECTORY)
    assert node_at(creation_shell, "work/parent") is not None
    assert result.status == 1
    assert result.stderr
    assert result.stdout == [
        "mkdir: sucessfully created first",
        "mkdir: sucessfully created last",
    ]


@pytest.mark.parametrize(
    "mode_option", ["-m 755", "--mode 755", "--mode=755", "-m 700", "-m 000"]
)
def test_mkdir_accepts_octal_mode_for_every_operand(
    run_creation, creation_shell, mode_option
):
    expected = {
        "755": {
            "user": {"r": True, "w": True, "x": True},
            "group": {"r": True, "w": False, "x": True},
            "public": {"r": True, "w": False, "x": True},
        },
        "700": {
            "user": {"r": True, "w": True, "x": True},
            "group": {"r": False, "w": False, "x": False},
            "public": {"r": False, "w": False, "x": False},
        },
        "000": {
            "user": {"r": False, "w": False, "x": False},
            "group": {"r": False, "w": False, "x": False},
            "public": {"r": False, "w": False, "x": False},
        },
    }[mode_option[-3:]]

    result = run_creation(f"mkdir {mode_option} first parent/second")

    for path in ("work/first", "work/parent/second"):
        node = assert_created(creation_shell, path, NodeType.DIRECTORY)
        assert node.inode.permissions == expected
    assert_success(result)


def test_mkdir_parents_mode_preserves_existing_directory_permissions(
    run_creation, creation_shell
):
    parent = node_at(creation_shell, "work/parent")
    before = deepcopy(parent.inode.permissions)

    result = run_creation("mkdir -p -m 700 parent parent/new")

    assert node_at(creation_shell, "work/parent") is parent
    assert parent.inode.permissions == before
    new = assert_created(creation_shell, "work/parent/new", NodeType.DIRECTORY)
    assert new.inode.permissions == {
        "user": {"r": True, "w": True, "x": True},
        "group": {"r": False, "w": False, "x": False},
        "public": {"r": False, "w": False, "x": False},
    }
    assert_success(result)


@pytest.mark.parametrize(
    "command",
    [
        "mkdir",
        "mkdir -p",
        "mkdir -m",
        "mkdir --mode",
        "mkdir -m 755",
        "mkdir -m 888 new",
        "mkdir -m banana new",
        'mkdir -m "" new',
        "mkdir --mode= new",
        "mkdir --unknown new",
        "mkdir -z new",
    ],
)
def test_mkdir_invalid_arguments_return_failure_without_mutating_tree(
    run_creation, creation_shell, command
):
    before = deepcopy(creation_shell.fs.filehead.to_dict())

    # Uncaught ValueError/IndexError must fail the test, not count as validation.
    result = run_creation(command)

    assert creation_shell.fs.filehead.to_dict() == before
    assert_failure(result)


@pytest.mark.integration
@pytest.mark.parametrize(
    "command,created_path,node_type",
    [("mkdir new", "work/new", NodeType.DIRECTORY), ("mkdir -p parent", None, None)],
)
def test_mkdir_successful_creation_allows_and_followup(
    run_creation, creation_shell, command, created_path, node_type
):
    result = run_creation(f"{command} && echo created")

    if created_path:
        assert_created(creation_shell, created_path, node_type)
    assert_success(result, ["created"])


@pytest.mark.integration
@pytest.mark.parametrize(
    "command",
    ["mkdir", "mkdir parent/missing/child", "mkdir first parent/missing/child"],
)
def test_mkdir_failed_creation_blocks_and_followup(
    run_creation, creation_shell, command
):
    result = run_creation(f"{command} && echo should-not-run")

    assert_failure(result)
    assert node_at(creation_shell, "work/parent/missing") is None
    if "first" in command.split():
        node_type = NodeType.DIRECTORY if command.startswith("mkdir") else NodeType.FILE
        assert_created(creation_shell, "work/first", node_type)


def test_mkdir_basic(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("mkdir a", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 1
    assert shell_empty.fs.current.items[0].name == "a"

    CmdResult = cl.enter_command("mkdir a", shell_empty)
    assert CmdResult.stderr == ["mkdir: Filename 'a' already exists"]
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 1
    assert shell_empty.fs.current.items[0].name == "a"


def test_mkdir_none(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("mkdir", shell_empty)
    assert CmdResult.stderr == ["mkdir: at least one argument should be given"]
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 0


def test_mkdir_verbose(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("mkdir -v a", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["mkdir: sucessfully created a"]
    assert len(shell_empty.fs.current.items) == 1
    assert shell_empty.fs.current.items[0].name == "a"


def test_mkdir_error(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("mkdir a/b", shell_empty)
    assert CmdResult.stderr == ["mkdir: No directory named a"]
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 0

    CmdResult = cl.enter_command("mkdir -p", shell_empty)
    assert CmdResult.stderr == ["mkdir: no name given for new directory"]
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 0


def test_mkdir_parents(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("mkdir -p a/b/c", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert len(shell_empty.fs.current.items) == 1
    fn = shell_empty.fs.current.items[0]
    assert fn.name == "a"
    assert len(fn.items) == 1
    fn2 = fn.items[0]
    assert fn2.name == "b"
    assert len(fn2.items) == 1
    fn3 = fn2.items[0]
    assert fn3.name == "c"


def test_mkdir_help(cl, shell_empty):
    result = cl.enter_command("mkdir --help", shell_empty)
    with open("../static/help/mkdir.txt") as help_file:
        assert result.stderr == []
        assert result.stdout == help_file.readlines()
