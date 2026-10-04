"""Tests for cut's field selection, input handling, and argument validation.

Most cases call cut(CommandContext) directly to separate handler defects from
shell parsing. Integration tests cover command dispatch, pipes, and redirection.
Ranges, long options, and byte/character modes are outside this command's scope.

Invalid arguments return errors in CommandResult. Output tests retain one-based
field numbering and stdout items without appended newlines.
"""

import pytest
from game.Context import CommandContext, SystemContext
from game.filenode import FileNode
from game.inode import Inode, NodeType
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error


@pytest.fixture
def cut_shell(shell_empty):
    # Short names isolate field handling from the separate filename tests.
    files = {
        "a": ["alice:admin:42", "bob:guest:7"],
        "b": ["carol:reader:9"],
        "e": [],
        "m": ["a::c", ":b:c", "a:b:"],
        "p": ["alice.admin.42", "bob.guest.7"],
        "r": ["alice:admin,active"],
        "n": ["plain", ""],
        "t": ["alice\tadmin\t42", "bob\tguest\t7"],
        "s": ["alice:admin", "plain", "", "charlie:"],
        "nul": ["alice\0admin", "bob\0guest"],
        "users.txt": ["dana:owner"],
        "with spaces.txt": ["erin:reader"],
        "-users.txt": ["frank:operator"],
    }
    for filename, lines in files.items():
        assert shell_empty.fs.add_file(filename) == ""
        node = shell_empty.fs.get_file(filename)
        assert isinstance(node, FileNode)
        node.set_data(lines.copy())
    assert shell_empty.fs.add_directory("folder") == ""
    return shell_empty


@pytest.fixture
def cut_context(cut_shell, process_manager, network_manager):
    def make_context(*args):
        return CommandContext(
            system=SystemContext(
                fs=cut_shell.fs,
                pm=process_manager,
                nm=network_manager,
                shell=cut_shell,
            ),
            command="cut",
            args=list(args),
            stdin=FileNode(None, "stdin", Inode(NodeType.FILE)),
            stdout=None,
        )

    return make_context


def assert_output(result, expected):
    assert result.stderr == []
    assert result.status == 0
    assert result.stdout == expected


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        pytest.param("1", ["alice", "bob"], id="first-field"),
        pytest.param("2", ["admin", "guest"], id="middle-field"),
        pytest.param("3", ["42", "7"], id="last-field"),
        pytest.param("1,3", ["alice:42", "bob:7"], id="comma-separated-fields"),
        pytest.param("3,1,3", ["alice:42", "bob:7"], id="ordered-unique-fields"),
    ],
)
def test_cut_selects_one_based_fields(cl, cut_context, selection, expected):
    result = cl.cut(cut_context("-d", ":", "-f", selection, "a"))
    assert_output(result, expected)


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        pytest.param("4", ["", ""], id="only-missing-field"),
        pytest.param("1,4", ["alice", "bob"], id="present-and-missing-fields"),
    ],
)
def test_cut_ignores_fields_beyond_line_end(cl, cut_context, selection, expected):
    result = cl.cut(cut_context("-d", ":", "-f", selection, "a"))
    assert_output(result, expected)


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        ("1", ["a", "", "a"]),
        ("2", ["", "b", "b"]),
        ("3", ["c", "c", ""]),
    ],
)
def test_cut_preserves_empty_fields(cl, cut_context, selection, expected):
    result = cl.cut(cut_context("-d", ":", "-f", selection, "m"))
    assert_output(result, expected)


def test_cut_preserves_lines_without_delimiter(cl, cut_context):
    result = cl.cut(cut_context("-d", ":", "-f", "2", "n"))
    assert_output(result, ["plain", ""])


def test_cut_delimiter_is_literal(cl, cut_context):
    result = cl.cut(cut_context("-d", ".", "-f", "2", "p"))
    assert_output(result, ["admin", "guest"])


@pytest.mark.parametrize(
    ("first_delimiter", "last_delimiter", "expected"),
    [
        (":", ",", ["active"]),
        (",", ":", ["admin,active"]),
    ],
)
def test_cut_last_delimiter_wins(
    cl, cut_context, first_delimiter, last_delimiter, expected
):
    result = cl.cut(
        cut_context("-d", first_delimiter, "-d", last_delimiter, "-f", "2", "r")
    )
    assert_output(result, expected)


@pytest.mark.parametrize("args", [("-d", ":", "-f", "1"), ("-f", "1", "-d", ":")])
def test_cut_empty_file_and_option_order(cl, cut_context, args):
    result = cl.cut(cut_context(*args, "e"))
    assert_output(result, [])


def test_cut_stdout_items_have_no_appended_newline(cl, cut_context):
    result = cl.cut(cut_context("-d", ":", "-f", "1", "a"))
    assert result.stderr == []
    assert len(result.stdout) == 2
    assert all(not line.endswith("\n") for line in result.stdout)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("users.txt", ["dana"]), ("with spaces.txt", ["erin"])],
)
def test_cut_keeps_filename_as_one_operand(cl, cut_context, filename, expected):
    result = cl.cut(cut_context("-d", ":", "-f", "1", filename))
    assert_output(result, expected)


def test_cut_processes_each_file_once_in_argument_order(cl, cut_context):
    result = cl.cut(cut_context("-d", ":", "-f", "1", "a", "b"))
    assert result.stderr == []
    assert len(result.stdout) == 3, "Two lines from a, followed by one from b."
    assert_output(result, ["alice", "bob", "carol"])


def test_cut_reports_missing_file_and_failure_status(cl, cut_context):
    result = cl.cut(cut_context("-d", ":", "-f", "1", "z"))
    assert result.stdout == []
    assert result.stderr == ["cut: z does not exist"]
    assert result.status != 0


def test_cut_continues_to_valid_file_after_missing_file(cl, cut_context):
    result = cl.cut(cut_context("-d", ":", "-f", "1", "z", "a"))
    assert result.stderr == ["cut: z does not exist"]
    assert len(result.stdout) == 2, "The readable file should be processed once."
    assert result.stdout == ["alice", "bob"]
    assert result.status != 0


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("-d",), id="missing-delimiter"),
        pytest.param(("-f",), id="missing-fields"),
        pytest.param(("-d", ":", "-f"), id="missing-fields-after-delimiter"),
    ],
)
def test_cut_missing_option_value_returns_argument_error(cl, cut_context, args):
    result = cl.cut(cut_context(*args))
    assert result.status != 0
    assert result.stdout == []
    assert result.stderr == [f"cut: parameter expected for {args[-1]}"]


@pytest.mark.parametrize("selection", ["abc", "1,b", "1,,2", ""])
def test_cut_non_integer_field_list_returns_argument_error(cl, cut_context, selection):
    result = cl.cut(cut_context("-d", ":", "-f", selection, "a"))
    assert result.status != 0
    assert result.stdout == []
    assert result.stderr == ["cut: bad value given for -f"]


def test_cut_does_not_mutate_source_or_change_directory(cl, cut_context, cut_shell):
    source = cut_shell.fs.get_file("a")
    assert isinstance(source, FileNode)
    before = source.get_data().copy()
    current = cut_shell.fs.current
    cwd = cut_shell.cwd

    result = cl.cut(cut_context("-d", ":", "-f", "1", "a"))

    assert result.status == 0
    assert result.stderr == []
    assert len(result.stdout) == len(before)
    assert source.get_data() == before
    assert cut_shell.fs.current is current
    assert cut_shell.cwd == cwd


@pytest.mark.integration
def test_cut_is_registered_with_shell(cl, cut_shell):
    result = cl.enter_command('cut -d ":" -f 1 e', cut_shell)
    assert_output(result, [])


def test_cut_defaults_to_tab_delimiter(cl, cut_context):
    assert_output(cl.cut(cut_context("-f", "1,3", "t")), ["alice\t42", "bob\t7"])


def test_cut_only_delimited_keeps_empty_selected_fields(cl, cut_context):
    result = cl.cut(cut_context("-d", ":", "-f", "2", "-s", "s"))
    assert_output(result, ["admin", ""])


def test_cut_empty_delimiter_uses_nul(cl, cut_context):
    result = cl.cut(cut_context("-d", "", "-f", "2", "nul"))
    assert_output(result, ["admin", "guest"])


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("-d", ":", "a"),
        ("-d", ":", "-f", "0", "a"),
        ("-d", ":", "-f", "-1", "a"),
        ("-d", ":", "-f", "1", "-f", "2", "a"),
        ("-d", ":,", "-f", "1", "a"),
        ("-dog", ":", "-f", "1", "a"),
        ("-d", ":", "-fool", "1", "a"),
        ("-d", ":", "-f", "1", "-silly", "a"),
        ("-d", ":", "-f", "1", "--unknown", "a"),
        ("-d", ":", "-f", "1", ""),
        ("-d", ":", "-f", "1", "folder"),
        ("-d", ":", "-f", "1", "missing/child.txt"),
    ],
)
def test_cut_invalid_arguments_and_paths_do_not_crash(cl, cut_context, args):
    result = cl.cut(cut_context(*args))
    assert result.status != 0
    assert result.stdout == []
    assert result.stderr
    assert all(message.startswith("cut:") for message in result.stderr)


@pytest.mark.parametrize(
    "command",
    [
        'cut -d ":" -f 1 users.txt',
        'cat users.txt | cut -d ":" -f 1',
        'cat users.txt | cut -d ":" -f 1 -',
        'cut -d ":" -f 1 < users.txt',
        'cut -d ":" -f 1 users.txt | cat',
        'cat a | cut -d ":" -f 1 users.txt',
    ],
)
@pytest.mark.integration
def test_cut_file_pipe_and_redirected_input(cl, cut_shell, command):
    assert_output(cl.enter_command(command, cut_shell), ["dana"])


@pytest.mark.integration
def test_cut_output_redirection(cl, cut_shell):
    result = cl.enter_command('cut -d ":" -f 1 a > names.txt', cut_shell)
    assert_output(result, [])
    assert_output(cl.enter_command("cat names.txt", cut_shell), ["alice", "bob"])


@pytest.mark.parametrize(
    "command",
    [
        'cut -d ":" -f 1',
        'cut -d ":" -f 1 -',
        'cat e | cut -d ":" -f 1',
    ],
)
@pytest.mark.integration
def test_cut_empty_stdin(cl, cut_shell, command):
    assert_output(cl.enter_command(command, cut_shell), [])


@pytest.mark.integration
def test_cut_end_of_options_allows_dash_prefixed_filename(cl, cut_shell):
    result = cl.enter_command('cut -d ":" -f 1 -- -users.txt', cut_shell)
    assert_output(result, ["frank"])


def test_cut_dot_paths_read_file(run_dot_command, dot_prefix):
    result = run_dot_command(f"cut -d : -f 1 {dot_prefix}data.txt")
    assert_success(result, ["beta", "alpha", "alpha"])


def test_cut_dot_paths_reject_directory(run_dot_command, dot_directory):
    operand, _ = dot_directory
    result = run_dot_command(f"cut -d : -f 1 {operand}")
    assert_directory_error(result)


def test_cut_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    result = run_dot_command(f"cut -d : -f 1 {invalid_dot_path}")
    assert_failure(result)


def test_cut_dot_paths_preserve_literal_dot_names(run_dot_command):
    result = run_dot_command("cut -d : -f 1 ./..backup")
    assert_success(result, ["literal"])


def test_cut_dot_paths_read_parent_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    parent = current.parent if current.parent is not None else current
    lines = list(parent.access("data.txt").inode.data)
    result = run_dot_command("cut -d : -f 1 ../data.txt")
    assert_success(result, [line.split(":")[0] for line in lines])
