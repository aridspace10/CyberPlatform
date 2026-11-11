import re

import pytest
from game.filenode import FileNode
from game.GameManager import GameManager
from game.inode import Inode, NodeType
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error, descendants
from tests.command_helpers import assert_help


def test_grep_questions_complete_from_real_terminal_matches(cl):
    manager = GameManager()
    manager.set_config({
        "name": "Grep round", "gameType": "MiniGames", "playType": "SinglePlayer",
        "commands": {"grep": {"selected": True, "options": []}},
        "options": {"rounds": 2},
    })
    manager.start_round(["1", "2"])
    assert len(manager.questions) == 10

    player = ShellState()
    player.fs.from_dict(manager.get_shell()["fs"])
    question = manager.questions[0]
    marker, path = question["prompt"].split()[-3], question["prompt"].split()[-1]

    cl.enter_command(f"echo {marker}", player)
    assert not manager.record_grep("1", player.grep_matches)
    result = cl.enter_command(f"grep {marker} {path}", player)
    assert result.status == 0
    assert marker in result.stdout[0]
    assert manager.record_grep("1", player.grep_matches)
    assert not manager.record_grep("1", player.grep_matches)
    assert manager.get_game_data(player_id="1")["progress"]["completed"] == 1
    assert manager.get_game_data(player_id="2")["progress"]["completed"] == 0

    for question in manager.questions[1:]:
        marker, path = question["prompt"].split()[-3], question["prompt"].split()[-1]
        result = cl.enter_command(f"grep {marker} {path}", player)
        assert result.status == 0
        assert manager.record_grep("1", player.grep_matches)

    assert manager.get_game_data(player_id="1")["progress"]["completed"] == 10
    first_prompts = [question["prompt"] for question in manager.questions]
    manager.start_round(["1", "2"])
    assert [question["prompt"] for question in manager.questions] != first_prompts
    assert manager.get_game_data(player_id="1")["progress"]["completed"] == 0
    assert manager.get_game_data()["leaderboard"][0]["completed"] == 10


def test_generated_grep_markers_avoid_ambiguous_characters(cl):
    manager = GameManager()
    manager.set_config({
        "name": "Readable grep markers",
        "gameType": "MiniGames",
        "playType": "SinglePlayer",
        "commands": {"grep": {"selected": True, "options": []}},
        "options": {"rounds": 1, "questionCount": 10},
    })
    manager.start_round(["1"])

    player = ShellState()
    player.fs.from_dict(manager.get_shell()["fs"])
    for question in manager.questions:
        marker = re.search(r"TRACE_([A-F0-9]{8})", question["prompt"])
        assert marker is not None
        assert not set(marker.group(1)) & set("018B")

        path = question["prompt"].split()[-1]
        result = cl.enter_command(f"grep {marker.group()} {path}", player)
        assert result.status == 0
        assert marker.group() in result.stdout[0]


@pytest.mark.parametrize(
    ("selected_options", "wrong_flag", "correct_flag"),
    [([], "-l", ""), (["Show Line Number"], "-ln", "-n")],
)
def test_filename_only_grep_does_not_complete_line_question(
    cl, selected_options, wrong_flag, correct_flag
):
    manager = GameManager()
    manager.set_config({
        "name": "Grep output type",
        "gameType": "MiniGames",
        "playType": "SinglePlayer",
        "commands": {"grep": {"selected": True, "options": selected_options}},
        "options": {"rounds": 1, "questionCount": 1},
    })
    manager.start_round(["1"])
    question = manager.questions[0]
    answer = manager._answers[question["id"]]
    marker = answer["pattern"]
    path = question["prompt"].split()[-1]
    player = ShellState()
    player.fs.from_dict(manager.get_shell()["fs"])

    wrong = cl.enter_command(f"grep {wrong_flag} {marker} {path}", player)
    assert wrong.status == 0
    assert wrong.stdout == [path]
    assert not manager.record_grep("1", player.grep_matches, wrong.stdout)

    correct = cl.enter_command(f"grep {correct_flag} {marker} {path}", player)
    assert correct.status == 0
    assert manager.record_grep("1", player.grep_matches, correct.stdout)


def test_selected_grep_options_generate_matching_questions(cl):
    manager = GameManager()
    manager.set_config({
        "name": "Grep options", "gameType": "MiniGames", "playType": "SinglePlayer",
        "commands": {"grep": {"selected": True, "options": [
            "Case Insensitive", "Find By Filename", "Match By Line",
            "Match By Word", "Show Line Number",
        ]}},
        "options": {"rounds": 1, "questionCount": 5},
    })
    manager.start_round(["1"])
    assert {question["mode"] for question in manager.questions} == {
        "ignore_case", "files_with_matches", "line_regexp",
        "word_regexp", "line_number",
    }
    player = ShellState()
    player.fs.from_dict(manager.get_shell()["fs"])

    for question in manager.questions:
        prompt = question["prompt"]
        mode = question["mode"]
        marker = re.search(r"TRACE_[A-F0-9]+", prompt).group()
        path = "/logs" if mode == "files_with_matches" else prompt.split()[-1]
        pattern = (
            re.search(r'"([^"]+)"', prompt).group(1)
            if mode == "line_regexp" else marker
        )
        plain_command = (
            f"grep -r {pattern} {path}"
            if mode == "files_with_matches" else f'grep "{pattern}" {path}'
        )
        plain = cl.enter_command(plain_command, player)
        assert not manager.record_grep("1", player.grep_matches, plain.stdout)

        flag = {
            "ignore_case": "-i", "files_with_matches": "-rl",
            "line_regexp": "-x", "word_regexp": "-w", "line_number": "-n",
        }[mode]
        result = cl.enter_command(f'grep {flag} "{pattern}" {path}', player)
        assert result.status == 0
        assert manager.record_grep("1", player.grep_matches, result.stdout)

    assert manager.get_game_data(player_id="1")["progress"] == {
        "completed": 5, "total": 5,
    }


def test_game_pipe_setting_controls_terminal_pipeline(cl):
    manager = GameManager()
    manager.set_config({
        "name": "Pipe setting", "gameType": "MiniGames", "playType": "SinglePlayer",
        "commands": {"grep": {"selected": True, "options": []}},
        "options": {"rounds": 1, "questionCount": 1, "allowPipes": False},
    })
    manager.start_round(["1"])
    player = ShellState()
    shell_data = manager.get_shell()
    player.fs.from_dict(shell_data["fs"])
    player.allow_pipes = shell_data["allowPipes"]
    words = manager.questions[0]["prompt"].split()
    marker, path = words[-3], words[-1]
    command = f"grep {marker} {path} | grep {marker}"
    blocked = cl.enter_command(command, player)
    assert blocked.status != 0
    assert blocked.stderr == ["Pipes are disabled for this game"]
    assert not player.grep_matches

    player.allow_pipes = True
    allowed = cl.enter_command(command, player)
    assert allowed.status == 0
    assert manager.record_grep("1", player.grep_matches, allowed.stdout)


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


def test_grep_help_describes_regex_and_status_contract(cl, shell_empty):
    result = cl.enter_command("grep --help", shell_empty)

    assert result.status == 0
    assert any("Python regular expression" in line for line in result.stdout)
    assert any(
        "Status 0 means at least one line matched" in line for line in result.stdout
    )
    assert any("--regexp=PATTERN" in line for line in result.stdout)


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

    result = cl.enter_command(
        "grep -c alpha first.txt missing.txt second.txt", shell_empty
    )

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
    assert excluded.stdout == [
        "search/skip.txt:alpha", "search/ignored/inside.zzz:alpha"
    ]
    assert excluded.stderr == []


def test_grep_recursive_filters_keep_equals_and_match_basenames(cl, shell_empty):
    fs = shell_empty.fs
    fs.add_directory("search")
    for name in ("match=one.txt", "match=two.log", "skip=three.txt"):
        fs.add_file(f"search/{name}")
        fs.current.access("search").access(name).set_data(["alpha"])

    result = cl.enter_command(
        "grep -r --include=match=*.txt --include=match=*.log "
        "--exclude=skip=*.txt alpha search",
        shell_empty,
    )

    assert result.status == 0
    assert result.stdout == [
        "search/match=one.txt:alpha",
        "search/match=two.log:alpha",
    ]
    assert result.stderr == []


def test_grep_recursive_search_does_not_follow_directory_symlinks(cl, shell_empty):
    fs = shell_empty.fs
    fs.add_directory("search")
    fs.add_file("search/inside.txt")
    fs.current.access("search").access("inside.txt").set_data(["alpha"])
    fs.add_file("search/other.txt")
    fs.current.access("search").access("other.txt").set_data(["beta"])
    assert_success(cl.enter_command("ln -s . search/loop", shell_empty))

    result = cl.enter_command("grep -r alpha search", shell_empty)

    assert result.status == 0
    assert result.stdout == ["search/inside.txt:alpha"]
    assert result.stderr == []


def test_grep_recursive_search_handles_deep_directory_trees(cl, shell_empty):
    shell_empty.fs.add_directory("search")
    directory = shell_empty.fs.resolve("search")
    assert not isinstance(directory, str)
    parent = directory
    for index in range(1100):
        child = FileNode(parent, f"nested-{index}", Inode(NodeType.DIRECTORY))
        parent.items.append(child)
        parent = child
    file_node = FileNode(parent, "match.txt", Inode(NodeType.FILE))
    file_node.set_data(["alpha"])
    parent.items.append(file_node)

    result = cl.enter_command("grep -r alpha search", shell_empty)

    assert result.status == 0
    assert result.stdout == ["alpha"]
    assert result.stderr == []


@pytest.mark.parametrize(
    ("command", "expected_status", "expected_stdout"),
    [("grep ERROR f1.txt", 0, ["ERROR no", "ERROR no2"]),
     ("grep NOMATCH f1.txt", 1, [])],
)
def test_grep_match_and_no_match_statuses(
    cl, shell_basic, command, expected_status, expected_stdout
):
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
    actual = [
        next(item for item in expected if output.endswith(item))
        for output in result.stdout
    ]
    assert sorted(actual) == sorted(expected)


def test_grep_dot_paths_read_parent_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    parent = current.parent if current.parent is not None else current
    lines = list(parent.access("data.txt").inode.data)
    result = run_dot_command("grep : ../data.txt")
    assert_success(result, lines)
