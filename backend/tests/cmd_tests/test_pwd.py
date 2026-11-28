from game.GameManager import GameManager
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_success
from tests.cmd_tests.path_helpers import canonical_path, tree_state
from tests.command_helpers import assert_help


def test_pwd_help_documents_no_logical_or_physical_flags(cl, shell_empty):
    assert_help(cl, shell_empty, "pwd")
    help_text = "".join(cl.enter_command("pwd --help", shell_empty).stdout)
    assert "No -L/-P flags" in help_text


def test_pwd_dot_paths_report_canonical_directory(run_dot_command, dot_shell):
    expected = canonical_path(dot_shell.fs.current)
    assert_success(run_dot_command("pwd"), [expected])


def test_pwd_dot_paths_after_navigation(run_dot_command, dot_shell, dot_directory):
    operand, target = dot_directory
    # Navigation has its own assertions in test_cd.py. This test additionally
    # ensures pwd agrees with the directory reached through a dotted path.
    run_dot_command(f"cd {operand}", navigates_to=target)
    expected = canonical_path(target)
    assert_success(run_dot_command("pwd"), [expected])


def test_pwd_rejects_unexpected_operands_without_mutation(cl, shell_basic):
    before = tree_state(shell_basic)
    result = cl.enter_command("pwd --bad", shell_basic)
    assert result.status != 0
    assert result.stderr == ["pwd: unexpected operand '--bad'"]
    assert tree_state(shell_basic) == before


def pwd_round(commands, *, question_count=1):
    manager = GameManager()
    manager.set_config(
        {
            "name": "pwd practice",
            "gameType": "MiniGames",
            "playType": "SinglePlayer",
            "commands": {
                command: {"selected": True, "options": []} for command in commands
            },
            "options": {"rounds": 1, "questionCount": question_count, "seed": 58},
        }
    )
    manager.start_round(["1"])
    return manager


def test_pwd_minigame_requires_the_target_directory_and_real_pwd_execution(cl):
    manager = pwd_round(["pwd"])
    question = manager.questions[0]
    goal = manager._challenge_engine.challenges[question["id"]].goal
    target = goal.expected_stdout[0]
    assert question["command"] == "pwd"
    assert target in question["prompt"]
    assert question["example"] != goal.solution
    assert target not in question["example"]

    player = ShellState()
    player.fs.from_dict(manager.get_shell()["fs"])

    wrong_path = cl.enter_command("pwd", player)
    assert wrong_path.stdout == ["/"]
    assert not manager.record_attempt("1", player, wrong_path.stdout)

    unrelated = cl.enter_command(f"echo {target}", player)
    assert unrelated.stdout == [target]
    assert not manager.record_attempt("1", player, unrelated.stdout)

    assert cl.enter_command(f"cd {target}", player).status == 0
    correct = cl.enter_command("pwd", player)
    assert correct.status == 0
    assert correct.stdout == [target]
    assert manager.record_attempt("1", player, correct.stdout)
    assert manager.get_game_data(player_id="1")["progress"]["completed"] == 1


def test_pwd_minigame_rotates_distinct_navigation_scenarios(cl):
    manager = pwd_round(["pwd"], question_count=3)
    challenges = list(manager._challenge_engine.challenges.values())
    assert {challenge.variant for challenge in challenges} == {
        "incident", "release", "team"
    }
    assert len({challenge.goal.expected_stdout for challenge in challenges}) == 3
    player = ShellState()
    player.fs.from_dict(manager.get_shell()["fs"])
    for challenge in challenges:
        target = challenge.goal.expected_stdout[0]
        assert cl.enter_command(f"cd {target}", player).status == 0
        result = cl.enter_command("pwd", player)
        assert manager.record_attempt("1", player, result.stdout)


def test_pwd_question_is_solvable_in_a_mixed_command_pool(cl):
    manager = pwd_round(["pwd", "grep"], question_count=2)
    assert {question["command"] for question in manager.questions} == {"pwd", "grep"}
    pwd_question = next(
        question for question in manager.questions if question["command"] == "pwd"
    )
    goal = manager._challenge_engine.challenges[pwd_question["id"]].goal
    player = ShellState()
    player.fs.from_dict(manager.get_shell()["fs"])
    assert cl.enter_command(f"cd {goal.expected_stdout[0]}", player).status == 0
    result = cl.enter_command("pwd", player)
    assert manager.record_attempt("1", player, result.stdout)
