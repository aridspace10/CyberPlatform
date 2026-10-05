import random

from game.filenode import FileNode
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error, tree_state
from tests.command_helpers import assert_help, setup_names


def test_sort_basic(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    CmdResult = cl.enter_command("sort f2.txt", shell_basic)
    assert CmdResult.stderr == []
    for i in range(0, len(names)):
        assert CmdResult.stdout[i] == names[i]


def test_sort_random(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    name = random.choice(names)
    names.append(name)
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    fn.append_data([name])
    CmdResult = cl.enter_command("sort -R f2.txt", shell_basic)
    assert CmdResult.stderr == []
    for i in range(0, len(names) - 1):
        if CmdResult.stdout[i] == name:
            assert CmdResult.stdout[i + 1] == name
            return
    raise AssertionError()


def test_sort_dups(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    name = random.choice(names)
    names = names.copy()
    print(f"Extra name is {name}")
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    fn.append_data([name])
    print(fn.get_data())
    CmdResult = cl.enter_command("sort -u f2.txt", shell_basic)
    assert CmdResult.stderr == []
    # assert len(CmdResult.stdout) == len(names)
    print(CmdResult.stdout)
    print(names)
    for i in range(0, len(names)):
        assert CmdResult.stdout[i] == names[i]


def test_sort_output(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    CmdResult = cl.enter_command("sort -o f1.txt f2.txt", shell_basic)
    shell_basic.fs.search("f1.txt")
    data = shell_basic.fs.current.get_data()
    shell_basic.fs.current = shell_basic.fs.filehead
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    for i in range(0, len(names)):
        assert data[i] == names[i]


def test_sort_output_requires_a_path_without_mutation(cl, shell_basic):
    before = tree_state(shell_basic)
    for command in ("sort -o", 'sort -o "" f2.txt'):
        result = cl.enter_command(command, shell_basic)
        assert_failure(result)
        assert result.stderr
        assert tree_state(shell_basic) == before


def test_sort_sorted(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    CmdResult = cl.enter_command("sort -o s1.txt f2.txt", shell_basic)
    shell_basic.fs.search("s1.txt")
    data = shell_basic.fs.current.get_data()
    shell_basic.fs.current = shell_basic.fs.filehead
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    for i in range(0, len(names)):
        assert data[i] == names[i]
    CmdResult = cl.enter_command("sort -C s1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert shell_basic.ls == 0
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    data_copy = fn.get_data().copy()
    random.shuffle(data_copy)
    fn.set_data(data_copy)
    CmdResult = cl.enter_command("sort -C f2.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert shell_basic.ls == 0
    CmdResult = cl.enter_command("sort -c f2.txt", shell_basic)
    assert len(CmdResult.stderr)
    assert CmdResult.stderr[0].startswith("sort:")
    assert CmdResult.stdout == []
    assert shell_basic.ls == 0


def test_sort_help(cl, shell_empty):
    assert_help(cl, shell_empty, "sort")


def test_sort_dot_paths_read_file(run_dot_command, dot_prefix):
    result = run_dot_command(f"sort {dot_prefix}data.txt")
    assert_success(result, ["alpha:1", "alpha:1", "beta:2"])


def test_sort_dot_paths_reject_directory(run_dot_command, dot_directory):
    operand, _ = dot_directory
    result = run_dot_command(f"sort {operand}")
    assert_directory_error(result)
    assert result.stderr == [f"sort: {operand}: Is a directory"]


def test_sort_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    result = run_dot_command(f"sort {invalid_dot_path}")
    assert_failure(result)


def test_sort_dot_paths_preserve_literal_dot_names(run_dot_command):
    result = run_dot_command("sort ./..backup")
    assert_success(result, ["literal:5"])


def test_sort_dot_paths_output_file(run_dot_command, dot_shell, dot_prefix):
    current = dot_shell.fs.current
    source = current.access("data.txt")
    result = run_dot_command(
        f"sort -o {dot_prefix}sorted.txt ./data.txt", unchanged=False
    )
    output = current.access("sorted.txt")
    assert output is not None
    assert output.inode.data == ["alpha:1", "alpha:1", "beta:2"]
    assert source.inode.data == ["beta:2", "alpha:1", "alpha:1"]
    assert_success(result)


def test_sort_dot_paths_reject_directory_output(run_dot_command, dot_directory):
    operand, _ = dot_directory
    result = run_dot_command(f"sort -o {operand} ./data.txt")
    assert_failure(result)
    assert result.stderr == [f"sort: {operand}: Is a directory"]


def test_sort_dot_paths_reject_invalid_output(run_dot_command, invalid_dot_path):
    assert_failure(run_dot_command(f"sort -o {invalid_dot_path} ./data.txt"))


def test_sort_dot_paths_read_parent_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    parent = current.parent if current.parent is not None else current
    lines = list(parent.access("data.txt").inode.data)
    result = run_dot_command("sort ../data.txt")
    assert_success(result, sorted(lines))
