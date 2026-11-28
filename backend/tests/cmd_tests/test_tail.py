import pytest
from game.filenode import FileNode
from game.filesystem import FileSystem
from game.GameManager import GameManager
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error
from tests.command_helpers import assert_help


@pytest.mark.parametrize(
    ("options", "mode"),
    [([], "basic"), (["Last Lines"], "lines"), (["Last Bytes"], "bytes")],
)
def test_tail_minigame_requires_source_count_and_output(cl, options, mode):
    manager = GameManager()
    manager.set_config({
        "name": "Tail practice", "gameType": "MiniGames",
        "playType": "SinglePlayer",
        "commands": {"tail": {"selected": True, "options": options}},
        "options": {"rounds": 1, "questionCount": 1, "seed": 63},
    })
    manager.start_round(["1"])
    question = manager.questions[0]
    goal = manager._challenge_engine.challenges[question["id"]].goal
    assert question["mode"] == mode
    assert question["example"] != goal.solution
    source_path = goal.solution.split()[-1]
    assert source_path in question["prompt"]
    assert source_path not in question["example"]

    player = ShellState()
    player.fs.from_dict(manager.get_shell()["fs"])
    source = player.fs.resolve(source_path)
    decoy = "/reports/other.txt"
    player.fs.add_file(decoy)
    player.fs.resolve(decoy).set_data(source.get_data())
    wrong_source = cl.enter_command(goal.solution.replace(source_path, decoy), player)
    assert wrong_source.status == 0
    assert tuple(wrong_source.stdout) == goal.expected_stdout
    assert not manager.record_attempt("1", player, wrong_source.stdout)

    if mode == "basic":
        wrong_count_command = f"tail -n 9 {source_path}"
    else:
        flag = "-c" if mode == "bytes" else "-n"
        wrong_count_command = f"tail {flag} {goal.count - 1} {source_path}"
    wrong_count = cl.enter_command(wrong_count_command, player)
    assert wrong_count.status == 0
    assert not manager.record_attempt("1", player, wrong_count.stdout)

    correct = cl.enter_command(goal.solution, player)
    assert correct.status == 0
    assert tuple(correct.stdout) == goal.expected_stdout
    assert manager.record_attempt("1", player, correct.stdout)
    assert manager.get_game_data(player_id="1")["progress"]["completed"] == 1


def test_tail_minigame_mixed_pool_has_distinct_sources():
    manager = GameManager()
    manager.set_config({
        "name": "Mixed report practice", "gameType": "MiniGames",
        "commands": {
            "tail": {"selected": True, "options": ["Last Lines", "Last Bytes"]},
            "ls": {"selected": True, "options": []},
        },
        "options": {"rounds": 1, "questionCount": 4, "seed": 63},
    })
    manager.start_round(["1"])
    questions = [q for q in manager.questions if q["command"] == "tail"]
    assert len(questions) == 2
    goals = [manager._challenge_engine.challenges[q["id"]].goal for q in questions]
    assert len({goal.solution.split()[-1] for goal in goals}) == 2


@pytest.mark.parametrize("lines", [[], ["cat", "", "wolf"]])
def test_tail_buffered_input(run_buffered_command, lines):
    assert_success(run_buffered_command("tail -n 2", lines), lines[-2:])


# =========================================================
# Fixtures
# =========================================================


@pytest.fixture
def shell_tail():
    fs = FileSystem()

    fs.add_file("f1.txt")
    fn = fs.get_file("f1.txt")
    assert isinstance(fn, FileNode)
    fn.set_data(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])

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
    fn.set_data(["apple", "banana", "carrot", "dog", "elephant", "frog", "grape"])

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
    CmdResult = cl.enter_command("tail f1.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]


def test_tail_small_file(cl, shell_tail):
    CmdResult = cl.enter_command("tail small.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["a", "b", "c"]


def test_tail_single_line(cl, shell_tail):
    CmdResult = cl.enter_command("tail single.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hello"]


def test_tail_empty_file(cl, shell_tail):
    CmdResult = cl.enter_command("tail empty.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_tail_one_line_no_newline(cl, shell_one_line_no_newline):
    CmdResult = cl.enter_command("tail f1.txt", shell_one_line_no_newline)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hello"]


def test_tail_error(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("tail -c", shell_basic)
    assert CmdResult.stderr == ["tail: argument required for -c"]


def test_tail_error2(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("tail d1", shell_basic)
    assert CmdResult.stderr == ["tail: d1 is a directory"]


# =========================================================
# -n Tests
# =========================================================


def test_tail_n_1(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n 1 f1.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["12"]


def test_tail_n_3(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n 3 f1.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["10", "11", "12"]


def test_tail_n_equal_file_size(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n 12 f1.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
    ]


def test_tail_n_larger_than_file(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n 999 f1.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
    ]


def test_tail_n_zero(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n 0 f1.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_tail_byte_count_slices_bytes_including_final_newline(cl, shell_tail):
    node = shell_tail.fs.get_file("single.txt")
    node.set_data(["abc"])
    node.inode.has_trailing_newline = True

    result = cl.enter_command("tail -c 2 single.txt", shell_tail)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == ["c"]

    node.set_data(["é"])
    node.inode.has_trailing_newline = False
    result = cl.enter_command("tail -c 1 single.txt", shell_tail)
    assert result.stdout == ["�"]


def test_tail_explicit_stdin_and_plus_byte_count(cl, shell_tail):
    result = cl.enter_command("cat single.txt | tail -n 1 -", shell_tail)
    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == ["hello"]

    result = cl.enter_command("tail -c +2 single.txt", shell_tail)
    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == ["ello"]


# =========================================================
# Short Numeric Form
# =========================================================


def test_tail_short_numeric(cl, shell_tail):
    CmdResult = cl.enter_command("tail -3 f1.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["10", "11", "12"]


def test_tail_short_numeric_one(cl, shell_tail):
    CmdResult = cl.enter_command("tail -1 f1.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["12"]


# =========================================================
# +N Behaviour
# =========================================================


def test_tail_plus_mode(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n +3 f1.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]


def test_tail_plus_one(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n +1 f1.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
    ]


def test_tail_plus_last_line(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n +12 f1.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["12"]


def test_tail_plus_past_end(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n +20 f1.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


# =========================================================
# Newline Edge Cases
# =========================================================


def test_tail_file_with_trailing_newline(cl, shell_tail):
    CmdResult = cl.enter_command("tail newline.txt", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["a", "b", "c"]


def test_tail_preserves_no_trailing_newline(cl, shell_one_line_no_newline):
    CmdResult = cl.enter_command("tail -n 1 f1.txt", shell_one_line_no_newline)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hello"]


# =========================================================
# Error Handling
# =========================================================


def test_tail_missing_file(cl, shell_tail):
    CmdResult = cl.enter_command("tail missing.txt", shell_tail)

    assert CmdResult.stdout == []
    assert len(CmdResult.stderr) == 1
    assert CmdResult.status != 0


def test_tail_invalid_n_alpha(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n abc f1.txt", shell_tail)

    assert CmdResult.stdout == []
    assert len(CmdResult.stderr) == 1


def test_tail_invalid_n_float(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n 1.5 f1.txt", shell_tail)

    assert CmdResult.stdout == []
    assert len(CmdResult.stderr) == 1


def test_tail_missing_n_value(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n", shell_tail)

    assert CmdResult.stdout == []
    assert len(CmdResult.stderr) == 1


@pytest.mark.parametrize(
    "command",
    [
        "tail -n -1 f1.txt",
        "tail -c -1 f1.txt",
        "tail -n +0 f1.txt",
        "tail -n ++2 f1.txt",
    ],
)
def test_tail_rejects_unsupported_negative_and_zero_start_counts(
    cl, shell_tail, command
):
    result = cl.enter_command(command, shell_tail)
    assert result.status != 0
    assert result.stderr


# =========================================================
# Pipe Tests
# =========================================================


def test_tail_pipe_cat(cl, shell_tail):
    CmdResult = cl.enter_command("cat f1.txt | tail -n 2", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["11", "12"]


def test_tail_pipe_grep(cl, shell_tail):
    CmdResult = cl.enter_command("grep 1 f1.txt | tail -n 2", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["11", "12"]


def test_tail_pipe_wc_chain(cl, shell_tail):
    CmdResult = cl.enter_command("cat f1.txt | tail -n 3 | wc -l", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["3"]


def test_tail_pipe_only(cl, shell_tail):
    CmdResult = cl.enter_command("echo 'a\nb\nc\nd' | tail -n 2", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["c", "d"]


# =========================================================
# Multiple Files
# =========================================================


def test_tail_multiple_files(cl, shell_tail):
    CmdResult = cl.enter_command("tail small.txt f1.txt", shell_tail)

    assert CmdResult.stderr == []


def test_tail_multiple_files_with_n(cl, shell_tail):
    CmdResult = cl.enter_command("tail -n 1 small.txt f1.txt", shell_tail)

    assert CmdResult.stderr == []


# =========================================================
# Realistic Usage Tests
# =========================================================


def test_tail_log_style_usage(cl, shell_tail):
    CmdResult = cl.enter_command("grep 1 f1.txt | tail -1", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["12"]


def test_tail_after_grep(cl, shell_tail):
    CmdResult = cl.enter_command("grep apple mixed.txt | tail -1", shell_tail)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["apple"]


def test_tail_help(cl, shell_empty):
    assert_help(cl, shell_empty, "tail")


def test_tail_dot_paths_read_file(run_dot_command, dot_prefix):
    result = run_dot_command(f"tail -n 1 {dot_prefix}data.txt")
    assert_success(result, ["alpha:1"])


def test_tail_dot_paths_reject_directory(run_dot_command, dot_directory):
    operand, _ = dot_directory
    result = run_dot_command(f"tail -n 1 {operand}")
    assert_directory_error(result)


def test_tail_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    result = run_dot_command(f"tail -n 1 {invalid_dot_path}")
    assert_failure(result)


def test_tail_dot_paths_preserve_literal_dot_names(run_dot_command):
    result = run_dot_command("tail -n 1 ./..backup")
    assert_success(result, ["literal:5"])


def test_tail_dot_paths_read_parent_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    parent = current.parent if current.parent is not None else current
    lines = list(parent.access("data.txt").inode.data)
    result = run_dot_command("tail -n 1 ../data.txt")
    assert_success(result, lines[-1:])
