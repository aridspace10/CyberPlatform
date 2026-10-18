import pytest

from game.ShellState import ShellState
from game.filenode import FileNode
from game.inode import Inode, NodeType
from tests.cmd_tests.creation_helpers import assert_failure
from tests.cmd_tests.path_helpers import descendants
from tests.command_helpers import assert_help
def test_find_help(cl, shell_empty):
    assert_help(cl, shell_empty, "find")


def test_find_dot_paths_visit_each_file_once(run_dot_command, dot_directory):
    operand, target = dot_directory
    expected = [
        node.name
        for node in descendants(target)
        if not node.items and node.inode.type.value == "file"
    ]
    result = run_dot_command(f"find {operand} -type f")
    assert result.status == 0
    assert result.stderr == []
    assert sorted(path.rsplit("/", 1)[-1] for path in result.stdout) == sorted(expected)
    assert len(result.stdout) == len(set(result.stdout))


def test_find_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    assert_failure(run_dot_command(f"find {invalid_dot_path}"))


def test_find_invalid_type_predicate_returns_command_error_without_mutation(
    run_dot_command,
):
    result = run_dot_command("find . -type invalid")
    assert_failure(result)
    assert result.stderr


################# FIND ##################
def test_find_error(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("find", shell_basic)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == ["find: atleast one argument needs to be given"]

    CmdResult = cl.enter_command("find \( -type f -o -type d", shell_basic)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == ["find: Missing )"]

    CmdResult = cl.enter_command("find . -type", shell_basic)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == ["find: No value for given for: -type"]

    CmdResult = cl.enter_command("find . -exec cat {}", shell_basic)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == ["find: Expected ; or +"]

    CmdResult = cl.enter_command("find not_exist.jsx -type f", shell_basic)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == ["No directory named not_exist.jsx"]
    assert CmdResult.status != 0

    CmdResult = cl.enter_command("find -h", shell_basic)
    assert CmdResult.status == 0
    assert CmdResult.stderr == []


def test_find_help_documents_supported_predicates_and_actions(cl, shell_empty):
    assert_help(cl, shell_empty, "find")


def test_find_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("find .", shell_basic)
    assert CmdResult.stdout == [
        ".",
        "./f1.txt",
        "./f2.txt",
        "./d1",
        "./d1/f3.txt",
        "./d1/f4.txt",
    ]
    assert CmdResult.stderr == []


def test_find_file(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("find . -type f", shell_basic)
    assert CmdResult.stdout == ["./f1.txt", "./f2.txt", "./d1/f3.txt", "./d1/f4.txt"]
    assert CmdResult.stderr == []


def test_find_or(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("find . -type f -o -type d", shell_basic)
    assert CmdResult.stdout == [
        ".",
        "./f1.txt",
        "./f2.txt",
        "./d1",
        "./d1/f3.txt",
        "./d1/f4.txt",
    ]
    assert CmdResult.stderr == []


def test_find_name(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command('find . -name "f*.txt"', shell_basic)
    assert CmdResult.stdout == ["./f1.txt", "./f2.txt", "./d1/f3.txt", "./d1/f4.txt"]
    assert CmdResult.stderr == []

    CmdResult = cl.enter_command("find . -name f4.txt", shell_basic)
    assert CmdResult.stdout == ["./d1/f4.txt"]
    assert CmdResult.stderr == []


def test_find_not(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command('find . ! -name "f*.txt"', shell_basic)
    assert CmdResult.stdout == [".", "./d1"]
    assert CmdResult.stderr == []


def test_find_and(cl, shell_basic: ShellState):
    shell_basic.fs.add_file("f3.txt")
    CmdResult = cl.enter_command("find . -type d -name f3.txt", shell_basic)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == []


def test_find_false_empty_and_parenthesized_boolean_expressions(cl, shell_basic):
    shell_basic.fs.add_file("empty.txt")
    shell_basic.fs.add_file("blank.txt")
    shell_basic.fs.get_file("blank.txt").set_data([""])

    result = cl.enter_command("find . -false", shell_basic)
    assert result.status == 0
    assert result.stdout == []

    result = cl.enter_command("find . -empty", shell_basic)
    assert result.status == 0
    assert result.stdout == ["./d1/f3.txt", "./empty.txt"]

    result = cl.enter_command(
        "find . \\( -type f -o -type d \\) ! -name f1.txt", shell_basic
    )
    assert result.status == 0
    assert result.stdout == [
        ".",
        "./f2.txt",
        "./d1",
        "./d1/f3.txt",
        "./d1/f4.txt",
        "./empty.txt",
        "./blank.txt",
    ]


def test_find_multiple_roots_are_independent_and_preserve_cwd(cl, shell_basic):
    shell_basic.fs.add_directory("d1/sub")
    assert cl.enter_command("cd d1", shell_basic).status == 0
    current = shell_basic.fs.current
    fs_cwd = shell_basic.fs.cwd
    shell_cwd = shell_basic.cwd

    result = cl.enter_command("find . .. -type d", shell_basic)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == [".", "./sub", "..", "../d1", "../d1/sub"]
    assert shell_basic.fs.current is current
    assert shell_basic.fs.cwd == fs_cwd
    assert shell_basic.cwd == shell_cwd


def test_find_reports_symlinks_without_following_them(cl, shell_basic):
    assert cl.enter_command("ln -s d1 link", shell_basic).status == 0

    result = cl.enter_command("find . -type l", shell_basic)
    assert result.status == 0
    assert result.stdout == ["./link"]

    result = cl.enter_command("find link -type l", shell_basic)
    assert result.status == 0
    assert result.stdout == ["link"]


def test_find_absolute_start_preserves_operand_and_child_paths(cl, shell_basic):
    shell_basic.fs.add_directory("d1/sub")
    result = cl.enter_command("find /d1 -type d", shell_basic)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == ["/d1", "/d1/sub"]


@pytest.mark.parametrize(
    "expression",
    [
        r"find . -exec echo {} \;",
        "find . -exec echo {} +",
        "find . -delete",
        "find . -exec echo {} invalid",
        "find missing -delete",
    ],
)
def test_find_rejects_actions_before_traversal(cl, shell_basic, expression):
    before = shell_basic.fs.filehead.to_dict()
    current = shell_basic.fs.current

    result = cl.enter_command(expression, shell_basic)

    assert result.status != 0
    assert result.stderr
    assert (
        "actions are not supported" in result.stderr[0]
        or "Expected ; or +" in result.stderr[0]
    )
    assert shell_basic.fs.filehead.to_dict() == before
    assert shell_basic.fs.current is current


def test_find_detects_filesystem_cycles(cl, shell_empty):
    root = shell_empty.fs.filehead
    root.items.append(root)
    try:
        result = cl.enter_command("find .", shell_empty)
    finally:
        root.items.pop()
    assert result.status != 0
    assert "cycle" in result.stderr[0]


def test_find_limits_traversal_depth(cl, shell_empty):
    parent = shell_empty.fs.filehead
    for index in range(514):
        child = FileNode(parent, f"d{index}", Inode(NodeType.DIRECTORY))
        parent.items.append(child)
        parent = child

    result = cl.enter_command("find .", shell_empty)

    assert result.status != 0
    assert "maximum traversal depth" in result.stderr[0]


# def test_find_delete(cl, shell_basic: ShellState):
#     CmdResult = cl.enter_command('find . -type f -name f3.txt -delete', shell_basic)
#     assert CmdResult.stdout == []
#     assert CmdResult.stderr == []
