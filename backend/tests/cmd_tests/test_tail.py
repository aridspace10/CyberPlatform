import pytest

from game.filesystem import FileSystem
from game.ShellState import ShellState
from game.filenode import FileNode
from game.commandline import CommandLine

@pytest.fixture
def cl():
    return CommandLine()

# =========================================================
# Fixtures
# =========================================================

@pytest.fixture
def shell_tail():
    fs = FileSystem()

    fs.add_file("f1.txt")
    fn = fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    fn.set_data([
        "1", "2", "3", "4", "5", "6",
        "7", "8", "9", "10", "11", "12"
    ])

    fs.add_file("small.txt")
    fn = fs.get_file("small.txt")
    assert isinstance(fn, FileNode)
    fn.set_data(["a", "b", "c"])

    fs.add_file("empty.txt")
    fn = fs.get_file("empty.txt")
    assert isinstance(fn, FileNode)
    fn.set_data([])

    fs.add_file("single.txt")
    fn = fs.get_file("single.txt")
    assert isinstance(fn, FileNode)
    fn.set_data(["hello"])

    fs.add_file("newline.txt")
    fn = fs.get_file("newline.txt")
    assert isinstance(fn, FileNode)
    fn.set_data(["a", "b", "c"])

    fs.add_file("mixed.txt")
    fn = fs.get_file("mixed.txt")
    assert isinstance(fn, FileNode)
    fn.set_data([
        "apple", "banana", "carrot",
        "dog", "elephant", "frog", "grape"
    ])

    s = ShellState()
    s.fs = fs
    s.cwd = "/"

    return s


@pytest.fixture
def shell_one_line_no_newline():
    fs = FileSystem()

    fs.add_file("f1.txt")
    fn = fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    fn.set_data(["hello"])

    s = ShellState()
    s.fs = fs
    s.cwd = "/"

    return s

# =========================================================
# Basic Behaviour
# =========================================================

def test_tail_default(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "3", "4", "5", "6", "7",
        "8", "9", "10", "11", "12"
    ]


def test_tail_small_file(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail small.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "a", "b", "c"
    ]


def test_tail_single_line(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail single.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "hello"
    ]


def test_tail_empty_file(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail empty.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_tail_one_line_no_newline(cl, shell_one_line_no_newline):
    CmdResult = cl.enter_command(
        "tail f1.txt",
        shell_one_line_no_newline
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hello"]


# =========================================================
# -n Tests
# =========================================================

def test_tail_n_1(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n 1 f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "12"
    ]


def test_tail_n_3(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n 3 f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "10", "11", "12"
    ]


def test_tail_n_equal_file_size(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n 12 f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "1", "2", "3", "4", "5", "6",
        "7", "8", "9", "10", "11", "12"
    ]


def test_tail_n_larger_than_file(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n 999 f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "1", "2", "3", "4", "5", "6",
        "7", "8", "9", "10", "11", "12"
    ]


def test_tail_n_zero(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n 0 f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == []

# =========================================================
# -c / Bytes Tests
# =========================================================

def test_tail_c_1(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c 1 f1.txt",
        shell_tail
    )

    assert CommandResult.CommandResult.stderr == []

    # Raw stream ends with "...11\n12"
    # Last byte is "2"
    assert CommandResult.stdout == ["2"]


def test_tail_c_2(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c 2 f1.txt",
        shell_tail
    )

    assert CommandResult.stderr == []

    # Last two bytes are "12"
    assert CommandResult.stdout == ["12"]


def test_tail_c_5(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c 5 f1.txt",
        shell_tail
    )

    assert CommandResult.stderr == []
    assert CommandResult.stdout == ["11", "12"]


def test_tail_c_equal_file_size(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c 26 f1.txt",
        shell_tail
    )

    assert CommandResult.stderr == []

    # Entire file stream
    assert CommandResult.stdout == [
        "1", "2", "3", "4", "5", "6",
        "7", "8", "9", "10", "11", "12"
    ]


def test_tail_c_larger_than_file(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c 999 f1.txt",
        shell_tail
    )

    assert CommandResult.stderr == []

    assert CommandResult.stdout == [
        "1", "2", "3", "4", "5", "6",
        "7", "8", "9", "10", "11", "12"
    ]


def test_tail_c_zero(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c 0 f1.txt",
        shell_tail
    )

    assert CommandResult.stderr == []

    # Real tail -c 0 outputs nothing
    assert CommandResult.stdout == []


def test_tail_c_small_file(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c 2 small.txt",
        shell_tail
    )

    assert CommandResult.stderr == []

    # "a\nb\nc" -> last 2 bytes = "\nc"
    assert CommandResult.stdout == ["", "c"]


def test_tail_c_single_line(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c 1 single.txt",
        shell_tail
    )

    assert CommandResult.stderr == []

    # "hello" -> "o"
    assert CommandResult.stdout == ["o"]


def test_tail_c_empty_file(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c 5 empty.txt",
        shell_tail
    )

    assert CommandResult.stderr == []
    assert CommandResult.stdout == []


def test_tail_c_mixed_file(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c 3 mixed.txt",
        shell_tail
    )

    assert CommandResult.stderr == []

    # Stream ends with "...frog\ngrape"
    # Last 3 bytes are "ape"
    assert CommandResult.stdout == ["ape"]


def test_tail_c_missing_argument(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c",
        shell_tail
    )

    assert CommandResult.stderr != []
    assert CommandResult.stdout == []


def test_tail_c_invalid_number(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c abc f1.txt",
        shell_tail
    )

    assert CommandResult.stderr != []
    assert CommandResult.stdout == []


def test_tail_c_negative_number(cl, shell_tail):
    CommandResult = cl.enter_command(
        "tail -c -5 f1.txt",
        shell_tail
    )

    # GNU tail rejects negative byte counts
    assert CommandResult.stderr == ["tail: invalid number of bytes"]
    assert CommandResult.stdout == []


def test_tail_c_with_pipe_input(cl, shell_tail):
    CommandResult = cl.enter_command(
        'cat f1.txt | tail -c 3',
        shell_tail
    )

    assert CommandResult.stderr == []

    # Last 3 bytes are "\n12"
    assert CommandResult.stdout == ["", "12"]


# =========================================================
# Short Numeric Form
# =========================================================

def test_tail_short_numeric(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -3 f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "10", "11", "12"
    ]


def test_tail_short_numeric_one(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -1 f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "12"
    ]


# =========================================================
# +N Behaviour
# =========================================================

def test_tail_plus_mode(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n +3 f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "3", "4", "5", "6", "7", "8",
        "9", "10", "11", "12"
    ]


def test_tail_plus_one(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n +1 f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "1", "2", "3", "4", "5", "6",
        "7", "8", "9", "10", "11", "12"
    ]


def test_tail_plus_last_line(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n +12 f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "12"
    ]


def test_tail_plus_past_end(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n +20 f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


# =========================================================
# Newline Edge Cases
# =========================================================

def test_tail_file_with_trailing_newline(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail newline.txt",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "a", "b", "c"
    ]


def test_tail_preserves_no_trailing_newline(cl, shell_one_line_no_newline):
    CmdResult = cl.enter_command(
        "tail -n 1 f1.txt",
        shell_one_line_no_newline
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hello"]


# =========================================================
# Error Handling
# =========================================================

def test_tail_missing_file(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail missing.txt",
        shell_tail
    )

    assert CmdResult.stdout == []
    assert len(CmdResult.stderr) == 1


def test_tail_invalid_n_alpha(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n abc f1.txt",
        shell_tail
    )

    assert CmdResult.stdout == []
    assert len(CmdResult.stderr) == 1


def test_tail_invalid_n_float(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n 1.5 f1.txt",
        shell_tail
    )

    assert CmdResult.stdout == []
    assert len(CmdResult.stderr) == 1


def test_tail_missing_n_value(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n",
        shell_tail
    )

    assert CmdResult.stdout == []
    assert len(CmdResult.stderr) == 1


# =========================================================
# Pipe Tests
# =========================================================

def test_tail_pipe_cat(cl, shell_tail):
    CmdResult = cl.enter_command(
        "cat f1.txt | tail -n 2",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "11", "12"
    ]


def test_tail_pipe_grep(cl, shell_tail):
    CmdResult = cl.enter_command(
        "grep 1 f1.txt | tail -n 2",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "11", "12"
    ]


def test_tail_pipe_wc_chain(cl, shell_tail):
    CmdResult = cl.enter_command(
        "cat f1.txt | tail -n 3 | wc -l",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "3"
    ]


def test_tail_pipe_only(cl, shell_tail):
    CmdResult = cl.enter_command(
        "echo 'a\nb\nc\nd' | tail -n 2",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "c", "d"
    ]


# =========================================================
# Multiple Files
# =========================================================

def test_tail_multiple_files(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail small.txt f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []


def test_tail_multiple_files_with_n(cl, shell_tail):
    CmdResult = cl.enter_command(
        "tail -n 1 small.txt f1.txt",
        shell_tail
    )

    assert CmdResult.stderr == []


# =========================================================
# Realistic Usage Tests
# =========================================================

def test_tail_log_style_usage(cl, shell_tail):
    CmdResult = cl.enter_command(
        "grep 1 f1.txt | tail -1",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "12"
    ]


def test_tail_after_grep(cl, shell_tail):
    CmdResult = cl.enter_command(
        "grep apple mixed.txt | tail -1",
        shell_tail
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "apple"
    ]