import pytest
from game.command_contract import COMMAND_CONTRACTS
from game.GameManager import GameManager
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_success


@pytest.mark.parametrize(("options", "mode"), [([], "basic"), (["Phrase"], "phrase")])
def test_echo_minigame_requires_exact_text_from_echo(cl, options, mode):
    manager = GameManager()
    manager.set_config({
        "name": "Message practice", "gameType": "MiniGames",
        "playType": "SinglePlayer",
        "commands": {"echo": {"selected": True, "options": options}},
        "options": {"rounds": 1, "questionCount": 1, "seed": 64},
    })
    manager.start_round(["1"])
    question = manager.questions[0]
    goal = manager._challenge_engine.challenges[question["id"]].goal
    assert question["mode"] == mode
    assert question["example"] != goal.solution
    assert goal.expected_stdout[0] in question["prompt"]
    assert goal.expected_stdout[0] not in question["example"]

    player = ShellState()
    player.fs.from_dict(manager.get_shell()["fs"])
    player.fs.add_file("/messages/decoy.txt")
    player.fs.resolve("/messages/decoy.txt").set_data([goal.expected_stdout[0]])
    unrelated = cl.enter_command("cat /messages/decoy.txt", player)
    assert unrelated.status == 0
    assert tuple(unrelated.stdout) == goal.expected_stdout
    assert not manager.record_attempt("1", player, unrelated.stdout)
    wrong = cl.enter_command("echo wrong message", player)
    assert wrong.status == 0
    assert not manager.record_attempt("1", player, wrong.stdout)

    correct = cl.enter_command(goal.solution, player)
    assert correct.status == 0
    assert tuple(correct.stdout) == goal.expected_stdout
    assert manager.record_attempt("1", player, correct.stdout)
    assert manager.get_game_data(player_id="1")["progress"]["completed"] == 1


def test_echo_minigame_mixed_pool_uses_distinct_messages():
    manager = GameManager()
    manager.set_config({
        "name": "Mixed messages", "gameType": "MiniGames",
        "commands": {
            "echo": {"selected": True, "options": ["Phrase"]},
            "ls": {"selected": True, "options": []},
        },
        "options": {"rounds": 1, "questionCount": 4, "seed": 64},
    })
    manager.start_round(["1"])
    questions = [q for q in manager.questions if q["command"] == "echo"]
    assert len(questions) == 2
    goals = [manager._challenge_engine.challenges[q["id"]].goal for q in questions]
    assert len({goal.expected_stdout for goal in goals}) == 2


def test_echo_dot_paths_are_literal_text(run_dot_command):
    assert_success(run_dot_command("echo . .. ./ branch/.."), [". .. ./ branch/.."])


def test_echo_basic(cl, shell_empty):
    # echo should return CmdResult.stdout containing the args joined
    CmdResult = cl.enter_command("echo hello world", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hello world"]


def test_echo_help_argument_is_literal(cl, shell_empty):
    assert_success(cl.enter_command("echo --help", shell_empty), ["--help"])


def test_echo_expands_star_question_and_character_classes(cl, shell_basic):
    assert_success(cl.enter_command("echo f*.txt", shell_basic), ["f1.txt f2.txt"])
    assert_success(cl.enter_command("echo f?.txt", shell_basic), ["f1.txt f2.txt"])
    assert_success(cl.enter_command("echo f[12].txt", shell_basic), ["f1.txt f2.txt"])


def test_echo_expands_relative_and_absolute_path_components(cl, shell_basic):
    assert_success(
        cl.enter_command("echo ./d?/f*.txt /d?/f?.txt", shell_basic),
        ["./d1/f3.txt ./d1/f4.txt /d1/f3.txt /d1/f4.txt"],
    )


def test_echo_preserves_quoted_and_escaped_globs(cl, shell_basic):
    assert_success(
        cl.enter_command(r'''echo '*.txt' "f?.txt" \*.txt "f"*.txt''', shell_basic),
        ["*.txt f?.txt *.txt f1.txt f2.txt"],
    )


def test_echo_mixes_literal_brackets_with_wildcards(cl, shell_empty):
    shell_empty.fs.add_file("item[1].txt")
    shell_empty.fs.add_file("itema.txt")
    assert_success(
        cl.enter_command(r"echo item\[1\]*", shell_empty),
        ["item[1].txt"],
    )


def test_echo_expands_unquoted_variable_patterns(cl, shell_basic):
    assert_success(
        cl.enter_command('PAT="f?.txt"; echo $PAT "$PAT" "f*$PAT"', shell_basic),
        ["f1.txt f2.txt f?.txt f*f?.txt"],
    )


def test_echo_keeps_unmatched_patterns_and_excludes_hidden_files(cl, shell_empty):
    shell_empty.fs.add_file("visible.txt")
    shell_empty.fs.add_file(".secret.txt")
    assert_success(
        cl.enter_command("echo *.txt .* missing*.txt", shell_empty),
        ["visible.txt .secret.txt missing*.txt"],
    )


def test_echo_glob_respects_directory_permissions(cl, shell_basic):
    shell_basic.fs.resolve("d1").inode.permissions["user"]["r"] = False
    assert_success(cl.enter_command("echo d1/*", shell_basic), ["d1/*"])


def test_registry_has_truthful_contract_for_every_command(cl):
    assert set(cl.commands) == set(COMMAND_CONTRACTS)
