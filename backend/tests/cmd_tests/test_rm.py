import pytest
from game.GameManager import GameManager
from game.Process import ProcessState
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import tree_state
from tests.command_helpers import assert_help


@pytest.mark.parametrize(
    ("options", "mode"),
    [([], "basic"), (["Remove Tree"], "recursive")],
)
def test_rm_minigame_requires_target_deletion_and_preserves_guard(cl, options, mode):
    manager = GameManager()
    manager.set_config({
        "name": "Cleanup practice", "gameType": "MiniGames",
        "playType": "SinglePlayer",
        "commands": {"rm": {"selected": True, "options": options}},
        "options": {"rounds": 1, "questionCount": 1, "seed": 59},
    })
    manager.start_round(["1"])
    question = manager.questions[0]
    goal = manager._challenge_engine.challenges[question["id"]].goal
    assert question["mode"] == mode
    assert question["example"] != goal.solution
    assert goal.target_path not in question["example"]

    player = ShellState()
    player.fs.from_dict(manager.get_shell()["fs"])
    player.fs.add_file("/cleanup/unrelated.txt")
    unrelated = cl.enter_command("rm /cleanup/unrelated.txt", player)
    assert unrelated.status == 0
    assert not manager.record_attempt("1", player, unrelated.stdout)
    echo = cl.enter_command("echo removed", player)
    assert echo.status == 0
    assert not manager.record_attempt("1", player, echo.stdout)

    if mode == "recursive":
        no_flag = cl.enter_command(f"rm {goal.target_path}", player)
        assert no_flag.status != 0
        assert not manager.record_attempt("1", player, no_flag.stdout)

    correct = cl.enter_command(goal.solution, player)
    assert correct.status == 0
    assert manager.record_attempt("1", player, correct.stdout)
    assert isinstance(player.fs.resolve(goal.target_path), str)
    assert manager.get_game_data(player_id="1")["progress"]["completed"] == 1

    damaged = ShellState()
    damaged.fs.from_dict(manager.get_shell()["fs"])
    option = "-r " if mode == "recursive" else ""
    both = cl.enter_command(
        f"rm {option}{goal.target_path} {goal.guard_path}", damaged
    )
    assert both.status == 0
    assert not manager.record_attempt("2", damaged, both.stdout)


def test_rm_minigame_mixed_pool_uses_distinct_disposable_targets():
    manager = GameManager()
    manager.set_config({
        "name": "Mixed cleanup practice", "gameType": "MiniGames",
        "commands": {
            "rm": {"selected": True, "options": ["Remove Tree"]},
            "ls": {"selected": True, "options": []},
        },
        "options": {"rounds": 1, "questionCount": 4, "seed": 59},
    })
    manager.start_round(["1"])
    questions = [
        question for question in manager.questions if question["command"] == "rm"
    ]
    assert len(questions) == 2
    goals = [manager._challenge_engine.challenges[q["id"]].goal for q in questions]
    assert len({goal.target_path for goal in goals}) == 2


def test_rm_dot_paths_remove_only_requested_file(
    run_dot_command, dot_shell, dot_prefix
):
    current = dot_shell.fs.current
    source = current.access("data.txt")
    before = tree_state(dot_shell)
    result = run_dot_command(f"rm {dot_prefix}data.txt", unchanged=False)
    assert current.access("data.txt") is None
    assert len(tree_state(dot_shell)) == len(before) - 1
    assert all(row[0] != id(source) for row in tree_state(dot_shell))
    assert_success(result)


def test_rm_dot_paths_recursive_child(run_dot_command, dot_shell, dot_prefix):
    current = dot_shell.fs.current
    data = current.access("data.txt")
    result = run_dot_command(f"rm -r {dot_prefix}branch", unchanged=False)
    assert current.access("branch") is None
    assert current.access("data.txt") is data
    assert_success(result)


@pytest.mark.parametrize("option", ["", "-r", "-ri"])
@pytest.mark.parametrize(
    "operand", [".", "..", "./.", "branch/..", "branch/../..", "/.."]
)
def test_rm_dot_paths_refuse_dot_and_parent(
    run_dot_command, dot_shell, operand, option
):
    result = run_dot_command(f"rm {option} {operand}")
    assert result.interaction is None
    assert dot_shell.foreground_pid is None
    assert_failure(result)


def test_rm_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    assert_failure(run_dot_command(f"rm {invalid_dot_path}"))


def test_rm_basic(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("rm f2.txt", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert len(shell_fouritems.fs.current.items) == 3


def test_rm_force_ignores_missing_files_and_removes_existing_files(cl, shell_fouritems):
    result = cl.enter_command("rm -f missing.txt f2.txt", shell_fouritems)

    assert result.status == 0
    assert result.stdout == []
    assert result.stderr == []
    assert shell_fouritems.fs.get_file("f2.txt") is None


def test_rm_long_force_ignores_missing_files(cl, shell_empty):
    result = cl.enter_command("rm --force missing.txt", shell_empty)

    assert result.status == 0
    assert result.stdout == []
    assert result.stderr == []


def test_rm_requires_parent_write_permission(cl, shell_basic):
    root = shell_basic.fs.filehead
    root.inode.permissions["user"]["w"] = False
    assert_failure(cl.enter_command("rm f1.txt", shell_basic))
    assert root.access("f1.txt") is not None


def test_rm_recursive_permission_denied_preserves_child(cl, shell_basic):
    assert_success(cl.enter_command("chmod -R 000 d1", shell_basic))
    directory = shell_basic.fs.filehead.access("d1")
    assert_failure(cl.enter_command("rm d1/f3.txt", shell_basic))
    assert directory.access("f3.txt") is not None


def test_rm_dir(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("rm d1", shell_basic)
    assert len(shell_basic.fs.current.items) == 3
    assert CmdResult.stderr == ["rm: cannot remove 'd1': Is a directory"]
    assert CmdResult.stdout == []
    CmdResult = cl.enter_command("rm -r d1", shell_basic)
    assert len(shell_basic.fs.current.items) == 2
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_rm_interactive_recursive_expands_nested_targets(cl, shell_basic: ShellState):
    result = cl.enter_command("rm -ri d1", shell_basic)
    assert result.stderr == []
    assert result.interaction is not None
    assert result.interaction.prompt == "rm: remove regular file 'd1/f3.txt'?"

    pid = shell_basic.foreground_pid
    assert pid is not None
    process = cl.process_manager.get_process(pid)
    assert process is not None
    assert process.program is not None

    expected_prompts = [
        "rm: remove regular file 'd1/f4.txt'?",
        "rm: remove directory 'd1'?",
    ]
    for prompt in expected_prompts:
        stdout, stderr = process.program.receive_input("yes")
        assert stdout == []
        assert stderr == []
        assert process.program.prompt == prompt

    stdout, stderr = process.program.receive_input("yes")
    assert stdout == []
    assert stderr == []
    assert process.status == ProcessState.TERMINATED
    assert shell_basic.fs.get_file("d1") is None


def test_rm_interactive_missing_file_finishes_without_blocking(cl, shell_empty):
    result = cl.enter_command("rm -i missing.txt", shell_empty)
    assert result.status == 1
    assert result.interaction is None
    assert shell_empty.foreground_pid is None
    assert result.stderr == ["rm: cannot remove 'missing.txt': No such file"]


def test_rm_interactive_rejected_child_preserves_directory(cl, shell_basic):
    result = cl.enter_command("rm -ri d1", shell_basic)
    assert result.interaction is not None

    pid = shell_basic.foreground_pid
    assert pid is not None
    process = cl.process_manager.get_process(pid)
    assert process is not None
    assert process.program is not None

    process.program.receive_input("no")
    process.program.receive_input("yes")
    _stdout, stderr = process.program.receive_input("yes")

    assert stderr == ["rm: cannot remove 'd1': Directory not empty"]
    directory = shell_basic.fs.get_file("d1")
    assert directory is not None
    assert not isinstance(directory, str)
    assert [item.name for item in directory.items] == ["f3.txt"]


def test_rm_nested_delete_restores_filesystem_pointer(cl, shell_basic: ShellState):
    directory = shell_basic.fs.resolve("d1")
    assert not isinstance(directory, str)
    shell_basic.fs.current = directory
    shell_basic.fs.cwd = shell_basic.fs.display_path(directory)
    shell_basic.cwd = shell_basic.fs.cwd

    result = cl.enter_command("rm f3.txt", shell_basic)

    assert result.stderr == []
    assert shell_basic.fs.current is directory
    assert shell_basic.fs.get_file("f3.txt") is None


def test_recursive_rm_requires_directory_traversal_before_mutating(cl, shell_basic):
    directory = shell_basic.fs.filehead.access("d1")
    directory.inode.permissions["user"]["x"] = False
    before = [child.name for child in directory.items]

    result = cl.enter_command("rm -r d1", shell_basic)

    assert_failure(result)
    assert [child.name for child in directory.items] == before
    assert shell_basic.fs.filehead.access("d1") is directory


def test_rm_help(cl, shell_empty):
    assert_help(cl, shell_empty, "rm")
