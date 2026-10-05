from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure
from tests.cmd_tests.path_helpers import descendants


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

    CmdResult = cl.enter_command("find -h", shell_basic)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == ["find: starting locaiton needs to be given"]


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


# def test_find_delete(cl, shell_basic: ShellState):
#     CmdResult = cl.enter_command('find . -type f -name f3.txt -delete', shell_basic)
#     assert CmdResult.stdout == []
#     assert CmdResult.stderr == []
