import math
import random
from pathlib import Path

import pytest
from game.command_contract import format_command_help
from game.GameManager import GameManager
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error, tree_state
from tests.command_helpers import assert_help


@pytest.mark.parametrize(
    ("options", "mode"),
    [([], "basic"), (["First Lines"], "lines"), (["First Bytes"], "bytes")],
)
def test_head_minigame_requires_source_count_and_output(cl, options, mode):
    manager = GameManager()
    manager.set_config({
        "name": "Head practice", "gameType": "MiniGames",
        "playType": "SinglePlayer",
        "commands": {"head": {"selected": True, "options": options}},
        "options": {"rounds": 1, "questionCount": 1, "seed": 62},
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
        wrong_count_command = f"head -n 9 {source_path}"
    else:
        flag = "-c" if mode == "bytes" else "-n"
        wrong_count_command = f"head {flag} {goal.count - 1} {source_path}"
    wrong_count = cl.enter_command(wrong_count_command, player)
    assert wrong_count.status == 0
    assert not manager.record_attempt("1", player, wrong_count.stdout)

    correct = cl.enter_command(goal.solution, player)
    assert correct.status == 0
    assert tuple(correct.stdout) == goal.expected_stdout
    assert manager.record_attempt("1", player, correct.stdout)
    assert manager.get_game_data(player_id="1")["progress"]["completed"] == 1


def test_head_minigame_mixed_pool_has_distinct_sources():
    manager = GameManager()
    manager.set_config({
        "name": "Mixed report practice", "gameType": "MiniGames",
        "commands": {
            "head": {"selected": True, "options": ["First Lines", "First Bytes"]},
            "ls": {"selected": True, "options": []},
        },
        "options": {"rounds": 1, "questionCount": 4, "seed": 62},
    })
    manager.start_round(["1"])
    questions = [q for q in manager.questions if q["command"] == "head"]
    assert len(questions) == 2
    goals = [manager._challenge_engine.challenges[q["id"]].goal for q in questions]
    assert len({goal.solution.split()[-1] for goal in goals}) == 2


@pytest.mark.parametrize("lines", [[], ["cat", "", "wolf"]])
def test_head_buffered_input(run_buffered_command, lines):
    assert_success(run_buffered_command("head -n 2", lines), lines[:2])


def test_head_help_loading_does_not_depend_on_process_cwd(
    cl, shell_empty, monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    assert_help(cl, shell_empty, "head")


def test_head_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("head f2.txt", shell_basic)
    assert CmdResult.stderr == []
    for i, line in enumerate(CmdResult.stdout):
        assert line == str(i)


def test_head_rejects_unreadable_input(cl, shell_basic):
    source = shell_basic.fs.filehead.access("f2.txt")
    source.inode.permissions["user"]["r"] = False

    result = cl.enter_command("head f2.txt", shell_basic)

    assert result.status == 1
    assert result.stdout == []
    assert result.stderr and "Permission denied" in result.stderr[0]


def test_head_count(cl, shell_basic: ShellState):
    r = random.randint(1, 20)
    CmdResult = cl.enter_command(f"head -n {r} f2.txt", shell_basic)
    assert CmdResult.stderr == []
    for i in range(r):
        assert CmdResult.stdout[i] == str(i)
    CmdResult = cl.enter_command(f"head --lines={r} f2.txt", shell_basic)
    assert CmdResult.stderr == []
    for i in range(r):
        assert CmdResult.stdout[i] == str(i)
    CmdResult = cl.enter_command(f"head --lines=-{r} f2.txt", shell_basic)
    assert CmdResult.stderr == []
    for i in range(r, 0):
        assert CmdResult.stdout[-i] == str(i)


def test_head_zero_negative_and_positive_line_counts(cl, shell_empty):
    shell_empty.fs.add_file("lines.txt")
    node = shell_empty.fs.get_file("lines.txt")
    node.set_data(["one", "two", "three"])

    assert cl.enter_command("head -n 0 lines.txt", shell_empty).stdout == []
    expected_without_final = [
        "one",
        "two",
    ]
    assert (
        cl.enter_command("head --lines=-1 lines.txt", shell_empty).stdout
        == expected_without_final
    )
    assert (
        cl.enter_command("head -n -1 lines.txt", shell_empty).stdout
        == expected_without_final
    )
    assert cl.enter_command("head -n +2 lines.txt", shell_empty).stdout == [
        "two",
        "three",
    ]


def test_head_byte_budget_resets_for_each_file_and_partial_utf8_is_replaced(
    cl, shell_empty
):
    shell_empty.fs.add_file("a.txt")
    shell_empty.fs.get_file("a.txt").set_data(["abc"])
    shell_empty.fs.add_file("b.txt")
    shell_empty.fs.get_file("b.txt").set_data(["éclair"])

    result = cl.enter_command("head -c 1 a.txt b.txt", shell_empty)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == ["==> a.txt <==", "a", "==> b.txt <==", "�"]


def test_head_error(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("head d1", shell_basic)
    assert CmdResult.stderr == ["head: d1 is a directory"]


def test_head_missing_path_sets_failure_status(cl, shell_basic):
    result = cl.enter_command("head d1/missing", shell_basic)
    assert result.status != 0
    assert result.stderr


@pytest.mark.parametrize(
    "command", ["head -n", "head -n nope", "head -n ++2", "head -c", "head --bytes="]
)
def test_head_invalid_count_is_a_command_error_without_mutation(
    cl, shell_basic, command
):
    before = tree_state(shell_basic)
    result = cl.enter_command(command, shell_basic)
    assert_failure(result)
    assert result.stderr
    assert tree_state(shell_basic) == before


def test_head_bytes(cl, shell_basic: ShellState):
    r = random.randint(5, 20)
    CmdResult = cl.enter_command(f"head -c {r} f2.txt", shell_basic)
    assert CmdResult.stderr == []
    expected_lines = math.ceil(r / 2)
    assert len(CmdResult.stdout) == expected_lines
    for i, line in enumerate(CmdResult.stdout):
        assert line == str(i)

    CmdResult = cl.enter_command(f"head --bytes={r} f2.txt", shell_basic)
    assert CmdResult.stderr == []
    expected_lines = math.ceil(r / 2)
    assert len(CmdResult.stdout) == expected_lines
    for i, line in enumerate(CmdResult.stdout):
        assert line == str(i)


def test_head_help(cl, shell_empty):
    assert_help(cl, shell_empty, "head")


def test_help_does_not_depend_on_working_directory_resources(
    cl, shell_empty, monkeypatch
):
    def unavailable_help_resources(_path, *args, **kwargs):
        raise OSError("simulated missing help resource")

    monkeypatch.setattr(Path, "read_text", unavailable_help_resources)
    result = cl.enter_command("head --help", shell_empty)
    assert result.status == 0
    assert result.stdout == format_command_help("head")
    assert result.stderr == []


def test_head_dot_paths_read_file(run_dot_command, dot_prefix):
    result = run_dot_command(f"head -n 1 {dot_prefix}data.txt")
    assert_success(result, ["beta:2"])


def test_head_dot_paths_reject_directory(run_dot_command, dot_directory):
    operand, _ = dot_directory
    result = run_dot_command(f"head -n 1 {operand}")
    assert_directory_error(result)


def test_head_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    result = run_dot_command(f"head -n 1 {invalid_dot_path}")
    assert_failure(result)


def test_head_dot_paths_preserve_literal_dot_names(run_dot_command):
    result = run_dot_command("head -n 1 ./..backup")
    assert_success(result, ["literal:5"])


def test_head_dot_paths_read_parent_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    parent = current.parent if current.parent is not None else current
    lines = list(parent.access("data.txt").inode.data)
    result = run_dot_command("head -n 1 ../data.txt")
    assert_success(result, lines[:1])
