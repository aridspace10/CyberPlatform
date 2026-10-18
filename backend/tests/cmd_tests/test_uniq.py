import pytest
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error, tree_state
from tests.command_helpers import assert_help


@pytest.mark.parametrize(
    ("lines", "expected"),
    [([], []), (["Cat", "cat", "", "wolf"], ["Cat", "", "wolf"])],
)
def test_uniq_buffered_input(run_buffered_command, lines, expected):
    assert_success(run_buffered_command("uniq -i", lines), expected)


def test_uniq_help(cl, shell_empty):
    assert_help(cl, shell_empty, "uniq")


@pytest.mark.parametrize(
    ("option", "expected"),
    [
        ("", ["x", "y", "z"]),
        ("-d", ["x", "y"]),
        ("--repeated", ["x", "y"]),
        ("-u", ["z"]),
        ("--count", ["3 x", "2 y", "1 z"]),
        ("-cd", ["3 x", "2 y"]),
    ],
)
def test_uniq_adjacent_groups_and_representative_once(
    cl, shell_empty, option, expected
):
    lines = ["x", "x", "x", "y", "y", "z"]
    shell_empty.fs.add_file("groups.txt")
    shell_empty.fs.current.access("groups.txt").set_data(lines)
    command = f"uniq {option} groups.txt" if option else "uniq groups.txt"

    result = cl.enter_command(command, shell_empty)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == expected


def test_uniq_only_merges_adjacent_duplicates(cl, shell_empty):
    shell_empty.fs.add_file("input.txt")
    shell_empty.fs.current.access("input.txt").set_data(["x", "y", "x"])

    result = cl.enter_command("uniq input.txt", shell_empty)

    assert result.status == 0
    assert result.stdout == ["x", "y", "x"]

    repeated = cl.enter_command("uniq -d input.txt", shell_empty)
    assert repeated.status == 0
    assert repeated.stdout == []


def test_uniq_comparison_options_preserve_original_lines(cl, shell_empty):
    shell_empty.fs.add_file("input.txt")
    source_lines = ["Cat", "cat", "DOG"]
    shell_empty.fs.current.access("input.txt").set_data(source_lines)

    result = cl.enter_command("uniq -i input.txt", shell_empty)

    assert result.status == 0
    assert result.stdout == ["Cat", "DOG"]
    assert shell_empty.fs.current.access("input.txt").inode.data == source_lines


def test_uniq_skips_fields_before_characters(cl, shell_empty):
    shell_empty.fs.add_file("input.txt")
    shell_empty.fs.current.access("input.txt").set_data(
        ["a alpha Z", "b beta Z", "c charlie Z"]
    )

    result = cl.enter_command("uniq -f 1 -s 2 input.txt", shell_empty)

    assert result.status == 0
    assert result.stdout == ["a alpha Z", "b beta Z", "c charlie Z"]


def test_uniq_fields_treat_tabs_and_repeated_blanks_as_separators(cl, shell_empty):
    shell_empty.fs.add_file("input.txt")
    shell_empty.fs.current.access("input.txt").set_data(
        ["id1\talpha\tS", "id2  alpha\tS", "id3\talpha S"]
    )

    result = cl.enter_command("uniq --skip-fields=1 input.txt", shell_empty)

    assert result.status == 0
    assert result.stdout == ["id1\talpha\tS", "id3\talpha S"]


def test_uniq_preserves_whitespace_in_unskipped_text(cl, shell_empty):
    shell_empty.fs.add_file("input.txt")
    shell_empty.fs.current.access("input.txt").set_data(["a x  y", "a x y"])

    result = cl.enter_command("uniq -f 1 input.txt", shell_empty)

    assert result.status == 0
    assert result.stdout == ["a x  y", "a x y"]


def test_uniq_accepts_stdin_marker(cl, shell_basic):
    result = cl.enter_command("uniq - < f1.txt", shell_basic)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == ["ERROR no", "INFO hey", "ERROR no2", "error 1"]


def test_uniq_missing_file_fails_and_preserves_cwd(cl, shell_basic):
    current = shell_basic.fs.current
    fs_cwd, shell_cwd = shell_basic.fs.cwd, shell_basic.cwd

    result = cl.enter_command("uniq missing.txt", shell_basic)

    assert result.status != 0
    assert result.stdout == []
    assert result.stderr
    assert shell_basic.fs.current is current
    assert shell_basic.fs.cwd == fs_cwd
    assert shell_basic.cwd == shell_cwd


@pytest.mark.parametrize("command", ["uniq -z", "uniq --all-repeated", "uniq a b"])
def test_uniq_rejects_unsupported_options_and_extra_inputs(
    cl, shell_empty, command
):
    result = cl.enter_command(command, shell_empty)

    assert result.status != 0
    assert result.stderr


@pytest.mark.parametrize(
    "command", ["uniq -f", "uniq -f nope", "uniq -s", "uniq --skip-fields=x"]
)
def test_uniq_invalid_skip_value_is_a_command_error_without_mutation(
    cl, shell_basic, command
):
    before = tree_state(shell_basic)
    result = cl.enter_command(command, shell_basic)
    assert_failure(result)
    assert result.stderr
    assert tree_state(shell_basic) == before


def test_uniq_dot_paths_read_file(run_dot_command, dot_prefix):
    result = run_dot_command(f"uniq {dot_prefix}data.txt")
    assert_success(result, ["beta:2", "alpha:1"])


def test_uniq_dot_paths_reject_directory(run_dot_command, dot_directory):
    operand, _ = dot_directory
    result = run_dot_command(f"uniq {operand}")
    assert_directory_error(result)
    assert result.stderr == [f"uniq: {operand}: Is a directory"]


def test_uniq_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    result = run_dot_command(f"uniq {invalid_dot_path}")
    assert_failure(result)


def test_uniq_dot_paths_preserve_literal_dot_names(run_dot_command):
    result = run_dot_command("uniq ./..backup")
    assert_success(result, ["literal:5"])


def test_uniq_dot_paths_read_parent_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    parent = current.parent if current.parent is not None else current
    lines = list(parent.access("data.txt").inode.data)
    result = run_dot_command("uniq ../data.txt")
    assert_success(
        result, [line for i, line in enumerate(lines) if i == 0 or line != lines[i - 1]]
    )
