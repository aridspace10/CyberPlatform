"""touch tests, including the CYB-24 regression contract and legacy cases.

Run from backend with:
    python -m pytest tests/cmd_tests/test_touch.py -o addopts= -p no:cacheprovider

Required date syntax: YYYY-MM-DD (-d/--date/--date=) and YYYYMMDDhhmm (-t).
This is a minimum supported subset, not GNU's full date language. Regressions
remain ordinary failures until fixed. Shared helpers inspect children directly
to avoid lookup and cwd side effects; data assertions do not update atime.
"""

from copy import deepcopy
from datetime import datetime

import pytest
from game.filenode import FileNode
from game.inode import NodeType
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import (
    OLD_ATIME,
    OLD_MTIME,
    REQUESTED_TIME,
    assert_created,
    assert_failure,
    assert_success,
    node_at,
)


@pytest.mark.parametrize("command,node_type", [("touch", NodeType.FILE)])
@pytest.mark.parametrize(
    "operand,expected_path",
    [
        ("new", "work/new"),
        ("parent/new", "work/parent/new"),
        ("./parent/new", "work/parent/new"),
        ("../other/new", "other/new"),
        ("/other/new", "other/new"),
    ],
)
def test_touch_creation_places_basename_under_correct_parent(
    run_creation, creation_shell, command, node_type, operand, expected_path
):
    result = run_creation(f"{command} {operand}")

    node = assert_created(creation_shell, expected_path, node_type)
    assert node.inode.data == []
    assert node.items == []
    assert_success(result)


@pytest.mark.parametrize("command,node_type", [("touch", NodeType.FILE)])
def test_touch_creation_processes_every_operand(
    run_creation, creation_shell, command, node_type
):
    result = run_creation(f"{command} first parent/second third")

    for path in ("work/first", "work/parent/second", "work/third"):
        assert_created(creation_shell, path, node_type)
    assert node_at(creation_shell, "work/parent/third") is None
    assert_success(result)


@pytest.mark.parametrize("command,node_type", [("touch", NodeType.FILE)])
@pytest.mark.parametrize(
    "operands",
    [
        "parent/missing/child blocker/child first second",
        "first parent/missing/child blocker/child second",
        "first second parent/missing/child blocker/child",
    ],
    ids=["failures-first", "failures-middle", "failures-last"],
)
def test_touch_creation_reports_each_failure_and_keeps_processing(
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


@pytest.mark.parametrize("command", ["touch"])
@pytest.mark.parametrize("operand", ["blocker/child", "blocker/child/grandchild"])
def test_touch_creation_rejects_non_directory_components_without_mutation(
    run_creation, creation_shell, command, operand
):
    before = deepcopy(creation_shell.fs.filehead.to_dict())

    result = run_creation(f"{command} {operand}")

    assert creation_shell.fs.filehead.to_dict() == before
    assert_failure(result)
    assert any("blocker" in message for message in result.stderr)


@pytest.mark.parametrize(
    "command",
    [
        "touch",
        "touch -a",
        "touch -c",
        "touch -d",
        "touch --date",
        "touch -t",
        "touch -d 2024-02-29",
        "touch -t 202402291230",
        "touch -d not-a-date existing.txt new",
        "touch -d 2024-02-30 existing.txt new",
        "touch --date=2024-13-01 existing.txt new",
        'touch -d "" existing.txt new',
        "touch --date= existing.txt new",
        "touch -t nonsense existing.txt new",
        "touch -t 202402301230 existing.txt new",
        "touch -t 202402292530 existing.txt new",
        "touch --unknown existing.txt new",
        "touch --unknown=value existing.txt new",
        "touch -z existing.txt new",
    ],
)
def test_touch_invalid_arguments_return_failure_without_mutating_tree(
    run_creation, creation_shell, command
):
    before = deepcopy(creation_shell.fs.filehead.to_dict())

    # Uncaught ValueError/IndexError must fail the test, not count as validation.
    result = run_creation(command)

    assert creation_shell.fs.filehead.to_dict() == before
    assert_failure(result)


@pytest.mark.parametrize(
    "date_option,expected",
    [
        ("-d 2024-02-29", REQUESTED_TIME),
        ("--date 2024-02-29", REQUESTED_TIME),
        ("--date=2024-02-29", REQUESTED_TIME),
        ("-t 202402291230", datetime(2024, 2, 29, 12, 30)),
    ],
)
def test_touch_supported_dates_apply_to_existing_and_new_files(
    run_creation, creation_shell, date_option, expected
):
    original = node_at(creation_shell, "work/existing.txt")
    inode = original.inode
    data = list(inode.data)
    birth = inode.btime

    result = run_creation(f"touch {date_option} existing.txt new.txt")

    new = assert_created(creation_shell, "work/new.txt", NodeType.FILE)
    assert new.inode.data == []
    assert node_at(creation_shell, "work/existing.txt") is original
    assert original.inode is inode
    assert inode.data == data
    assert inode.btime == birth
    for node in (original, new):
        assert node.inode.atime == expected
        assert node.inode.mtime == expected
    assert_success(result)


@pytest.mark.parametrize(
    "selection,change_access,change_modified",
    [
        ("", True, True),
        ("-a", True, False),
        ("-m", False, True),
        ("-am", True, True),
        ("-ma", True, True),
        ("-a -m", True, True),
        ("-m -a", True, True),
    ],
)
def test_touch_updates_selected_timestamps_and_preserves_content(
    run_creation, creation_shell, selection, change_access, change_modified
):
    node = node_at(creation_shell, "work/existing.txt")
    inode = node.inode
    parent = node.parent
    data = list(inode.data)
    birth = inode.btime

    result = run_creation(f"touch {selection} -d 2024-02-29 existing.txt")

    assert node_at(creation_shell, "work/existing.txt") is node
    assert node.inode is inode
    assert node.parent is parent
    assert inode.atime == (REQUESTED_TIME if change_access else OLD_ATIME)
    assert inode.mtime == (REQUESTED_TIME if change_modified else OLD_MTIME)
    assert inode.data == data  # get_data() would itself update atime.
    assert inode.btime == birth
    assert_success(result)


def test_touch_default_uses_current_time_for_both_timestamps(
    run_creation, creation_shell
):
    before = datetime.now()
    result = run_creation("touch existing.txt new.txt")
    after = datetime.now()

    for path in ("work/existing.txt", "work/new.txt"):
        node = assert_created(creation_shell, path, NodeType.FILE)
        assert before <= node.inode.atime <= after
        assert before <= node.inode.mtime <= after
    assert node_at(creation_shell, "work/existing.txt").inode.data == [
        "keep existing content"
    ]
    assert node_at(creation_shell, "work/new.txt").inode.data == []
    assert_success(result)


def test_touch_existing_directory_updates_metadata_without_replacing_it(
    run_creation, creation_shell
):
    parent = node_at(creation_shell, "work/parent")
    inode = parent.inode
    keep = node_at(creation_shell, "work/parent/keep.txt")
    before_child = deepcopy(keep.to_dict())

    result = run_creation("touch -d 2024-02-29 parent")

    assert node_at(creation_shell, "work/parent") is parent
    assert parent.inode is inode
    assert inode.type == NodeType.DIRECTORY
    assert parent.parent is node_at(creation_shell, "work")
    assert node_at(creation_shell, "work/parent/keep.txt") is keep
    assert keep.to_dict() == before_child
    assert inode.atime == REQUESTED_TIME
    assert inode.mtime == REQUESTED_TIME
    assert_success(result)


@pytest.mark.parametrize(
    "options,change_access,change_modified",
    [
        ("-c", True, True),
        ("--no-create", True, True),
        ("-ca", True, False),
        ("-cm", False, True),
        ("-cam", True, True),
    ],
)
def test_touch_no_create_skips_missing_paths_and_updates_existing_operand(
    run_creation, creation_shell, options, change_access, change_modified
):
    existing = node_at(creation_shell, "work/existing.txt")

    result = run_creation(
        f"touch {options} -d 2024-02-29 absent parent/absent "
        "parent/missing/absent existing.txt"
    )

    for path in ("work/absent", "work/parent/absent", "work/parent/missing"):
        assert node_at(creation_shell, path) is None
    assert node_at(creation_shell, "work/existing.txt") is existing
    assert existing.inode.atime == (REQUESTED_TIME if change_access else OLD_ATIME)
    assert existing.inode.mtime == (REQUESTED_TIME if change_modified else OLD_MTIME)
    assert existing.inode.data == ["keep existing content"]
    assert_success(result)


@pytest.mark.integration
@pytest.mark.parametrize(
    "command,created_path,node_type",
    [
        ("touch parent/new.txt", "work/parent/new.txt", NodeType.FILE),
        ("touch -c absent", None, None),
    ],
)
def test_touch_successful_creation_allows_and_followup(
    run_creation, creation_shell, command, created_path, node_type
):
    result = run_creation(f"{command} && echo created")

    if created_path:
        assert_created(creation_shell, created_path, node_type)
    assert_success(result, ["created"])


@pytest.mark.integration
@pytest.mark.parametrize(
    "command", ["touch parent/missing/child", "touch first parent/missing/child"]
)
def test_touch_failed_creation_blocks_and_followup(
    run_creation, creation_shell, command
):
    result = run_creation(f"{command} && echo should-not-run")

    assert_failure(result)
    assert node_at(creation_shell, "work/parent/missing") is None
    if "first" in command.split():
        node_type = NodeType.DIRECTORY if command.startswith("mkdir") else NodeType.FILE
        assert_created(creation_shell, "work/first", node_type)


def test_touch_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("touch --no-create f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert isinstance(shell_basic.fs.get_file("f1.txt"), FileNode)

    CmdResult = cl.enter_command("touch f3.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("touch -c f4.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert not isinstance(shell_basic.fs.get_file("f4.txt"), FileNode)

    CmdResult = cl.enter_command("touch -x", shell_basic)
    assert CmdResult.stderr == ["touch: unknown argument given"]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("touch -a --date=2025-01-01 f2.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    assert fn.inode.atime != fn.inode.mtime

    CmdResult = cl.enter_command("touch -m --date=2025-02-01 f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    fn = shell_basic.fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    assert fn.inode.atime != fn.inode.mtime


def test_touch_error(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("touch", shell_basic)
    assert CmdResult.stderr == ["touch: must give atleast one argument"]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("touch a/f1.txt", shell_basic)
    assert CmdResult.stderr == ["No directory named a"]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("touch -a", shell_basic)
    assert CmdResult.stderr == ["touch: no file given"]
    assert CmdResult.stdout == []


def test_touch_help(cl, shell_empty):
    result = cl.enter_command("touch --help", shell_empty)
    with open("../static/help/touch.txt") as help_file:
        assert result.stderr == []
        assert result.stdout == help_file.readlines()
