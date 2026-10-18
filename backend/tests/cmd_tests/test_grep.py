import pytest
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error, descendants
from tests.command_helpers import assert_help


@pytest.mark.parametrize(
    ("lines", "expected"),
    [([], []), (["cat", "", "wolf", "cat dog"], ["cat", "cat dog"])],
)
def test_grep_buffered_input(run_buffered_command, lines, expected):
    result = run_buffered_command("grep cat", lines)
    assert result.stdout == expected
    assert result.stderr == []


@pytest.mark.parametrize("input_prefix", ["", "echo cat | "])
def test_grep_stdin_filename_uses_a_display_label(cl, shell_basic, input_prefix):
    suffix = " < f1.txt" if not input_prefix else ""
    pattern = "ERROR" if not input_prefix else "cat"
    result = cl.enter_command(f"{input_prefix}grep -l {pattern}{suffix}", shell_basic)
    assert_success(result, ["(standard input)"])


def test_grep_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("grep ERROR f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR no", "ERROR no2"]


def test_grep_count(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("grep -c ERROR f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["2"]
    assert CmdResult.status == 0


def test_grep_error(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("grep -c", shell_basic)
    assert CmdResult.stderr == ["grep: pattern not given"]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("grep -a", shell_basic)
    assert CmdResult.stderr == ["grep: unsupported option '-a'"]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("grep text notexist.txt", shell_basic)
    assert CmdResult.stderr == ["grep: notexist.txt can not be found"]
    assert CmdResult.stdout == []


def test_grep_matchline(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command('grep -x "ERROR no" f1.txt', shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR no"]


def test_grep_matchwhole(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("grep -i ERROR f1.txt", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["ERROR no", "ERROR no2", "error 1"]


def test_grep_dir(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("grep -r ERROR .", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "./f1.txt:ERROR 1",
        "./f1.txt:ERROR 2",
        "./f2.txt:ERROR 3",
        "./f2.txt:ERROR 4",
    ]


def test_grep_dir2(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("grep -r ERROR .", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "./f1.txt:ERROR no",
        "./f1.txt:ERROR no2",
        "./d1/f4.txt:ERROR 1",
        "./d1/f4.txt:ERROR 2",
    ]


def test_grep_dir3(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("grep ERROR .", shell_basic)
    assert CmdResult.stderr == ["Can't recursively search directory without -r option"]
    assert CmdResult.stdout == []
    assert CmdResult.status == 2


def test_grep_regex_anchors_and_distinct_no_match_status(cl, shell_empty):
    shell_empty.fs.add_file("a.txt")
    shell_empty.fs.current.access("a.txt").set_data(["xalpha", "alpha beta"])

    matched = cl.enter_command("grep '^alpha' a.txt", shell_empty)
    unmatched = cl.enter_command("grep NOMATCH a.txt", shell_empty)

    assert matched.status == 0
    assert matched.stdout == ["alpha beta"]
    assert unmatched.status == 1
    assert unmatched.stdout == []


def test_grep_empty_pattern_matches_every_line(cl, shell_empty):
    shell_empty.fs.add_file("a.txt")
    shell_empty.fs.current.access("a.txt").set_data(["alpha", "", "beta"])

    result = cl.enter_command("grep -e '' a.txt", shell_empty)

    assert result.status == 0
    assert result.stdout == ["alpha", "", "beta"]


def test_grep_reports_invalid_regex_as_an_error(cl, shell_empty):
    result = cl.enter_command("grep '['", shell_empty)

    assert result.status == 2
    assert result.stdout == []
    assert result.stderr


def test_grep_end_of_options_reads_dash_prefixed_file(cl, shell_empty):
    shell_empty.fs.add_file("-dash.txt")
    shell_empty.fs.current.access("-dash.txt").set_data(["alpha"])

    result = cl.enter_command("grep alpha -- -dash.txt", shell_empty)

    assert result.status == 0
    assert result.stdout == ["alpha"]


def test_grep_word_matching_uses_punctuation_boundaries(cl, shell_empty):
    shell_empty.fs.add_file("punct.txt")
    shell_empty.fs.current.access("punct.txt").set_data(
        ["alpha-beta", "xalpha", "alpha!"]
    )

    result = cl.enter_command("grep -w alpha punct.txt", shell_empty)

    assert result.status == 0
    assert result.stdout == ["alpha-beta", "alpha!"]


def test_grep_only_matching_emits_all_original_case_occurrences(cl, shell_empty):
    shell_empty.fs.add_file("word.txt")
    shell_empty.fs.current.access("word.txt").set_data(["xALPHAx Alpha"])

    result = cl.enter_command("grep -ion alpha word.txt", shell_empty)

    assert result.status == 0
    assert result.stdout == ["1:ALPHA", "1:Alpha"]


def test_grep_line_and_invert_filters_are_consistent(cl, shell_empty):
    shell_empty.fs.add_file("lines.txt")
    shell_empty.fs.current.access("lines.txt").set_data(["alpha", "alpha beta", "beta"])

    exact = cl.enter_command("grep -x alpha lines.txt", shell_empty)
    inverted = cl.enter_command("grep -v alpha lines.txt", shell_empty)

    assert exact.status == 0
    assert exact.stdout == ["alpha"]
    assert inverted.status == 0
    assert inverted.stdout == ["beta"]


def test_grep_count_is_per_file_and_retains_missing_file_error(cl, shell_empty):
    shell_empty.fs.add_file("first.txt")
    shell_empty.fs.current.access("first.txt").set_data(["alpha", "alpha"])
    shell_empty.fs.add_file("second.txt")
    shell_empty.fs.current.access("second.txt").set_data(["beta"])

    result = cl.enter_command("grep -c alpha first.txt missing.txt second.txt", shell_empty)

    assert result.status == 2
    assert result.stdout == ["first.txt:2", "second.txt:0"]
    assert result.stderr == ["grep: missing.txt can not be found"]

    no_matches = cl.enter_command("grep -c NOMATCH first.txt", shell_empty)
    assert no_matches.status == 1
    assert no_matches.stdout == ["0"]
    assert no_matches.stderr == []


def test_grep_matching_multiple_files_prefixes_each_filename(cl, shell_empty):
    shell_empty.fs.add_file("first.txt")
    shell_empty.fs.current.access("first.txt").set_data(["alpha"])
    shell_empty.fs.add_file("second.txt")
    shell_empty.fs.current.access("second.txt").set_data(["alpha"])

    result = cl.enter_command("grep alpha first.txt second.txt", shell_empty)

    assert result.status == 0
    assert result.stdout == ["first.txt:alpha", "second.txt:alpha"]


def test_grep_recursive_matching_prefixes_each_filename(cl, shell_empty):
    shell_empty.fs.add_directory("search")
    shell_empty.fs.add_file("search/first.txt")
    shell_empty.fs.current.access("search").access("first.txt").set_data(["alpha"])
    shell_empty.fs.add_file("search/second.txt")
    shell_empty.fs.current.access("search").access("second.txt").set_data(["alpha"])

    result = cl.enter_command("grep -r alpha search", shell_empty)

    assert result.status == 0
    assert result.stdout == ["search/first.txt:alpha", "search/second.txt:alpha"]


def test_grep_recursion_applies_include_exclude_and_directory_filters(
    cl, shell_empty
):
    fs = shell_empty.fs
    fs.add_directory("search")
    fs.add_file("search/keep.zzz")
    fs.current.access("search").access("keep.zzz").set_data(["alpha"])
    fs.add_file("search/skip.txt")
    fs.current.access("search").access("skip.txt").set_data(["alpha"])
    fs.add_directory("search/ignored")
    fs.add_file("search/ignored/inside.zzz")
    fs.current.access("search").access("ignored").access("inside.zzz").set_data(
        ["alpha"]
    )

    result = cl.enter_command(
        "grep -r --include=*.zzz --exclude-dir=ignored alpha search", shell_empty
    )

    assert result.status == 0
    assert result.stdout == ["alpha"]
    assert result.stderr == []

    excluded = cl.enter_command("grep -r --exclude=keep.zzz alpha search", shell_empty)
    assert excluded.status == 0
    assert excluded.stdout == ["search/skip.txt:alpha", "search/ignored/inside.zzz:alpha"]
    assert excluded.stderr == []


@pytest.mark.parametrize(
    ("command", "expected_status", "expected_stdout"),
    [("grep ERROR f1.txt", 0, ["ERROR no", "ERROR no2"]),
     ("grep NOMATCH f1.txt", 1, [])],
)
def test_grep_match_and_no_match_statuses(cl, shell_basic, command, expected_status, expected_stdout):
    result = cl.enter_command(command, shell_basic)

    assert result.status == expected_status
    assert result.stdout == expected_stdout


def test_grep_help(cl, shell_empty):
    assert_help(cl, shell_empty, "grep")


def test_grep_dot_paths_read_file(run_dot_command, dot_prefix):
    result = run_dot_command(f"grep : {dot_prefix}data.txt")
    assert_success(result, ["beta:2", "alpha:1", "alpha:1"])


def test_grep_dot_paths_reject_directory(run_dot_command, dot_directory):
    operand, _ = dot_directory
    result = run_dot_command(f"grep : {operand}")
    assert_directory_error(result)


def test_grep_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    result = run_dot_command(f"grep : {invalid_dot_path}")
    assert_failure(result)


def test_grep_dot_paths_preserve_literal_dot_names(run_dot_command):
    result = run_dot_command("grep : ./..backup")
    assert_success(result, ["literal:5"])


def test_grep_dot_paths_recursive_search(run_dot_command, dot_directory):
    operand, target = dot_directory
    expected = [line for node in descendants(target) for line in node.inode.data]
    result = run_dot_command(f"grep -r : {operand}")
    assert result.status == 0
    assert result.stderr == []
    actual = [next(item for item in expected if output.endswith(item)) for output in result.stdout]
    assert sorted(actual) == sorted(expected)


def test_grep_dot_paths_read_parent_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    parent = current.parent if current.parent is not None else current
    lines = list(parent.access("data.txt").inode.data)
    result = run_dot_command("grep : ../data.txt")
    assert_success(result, lines)
