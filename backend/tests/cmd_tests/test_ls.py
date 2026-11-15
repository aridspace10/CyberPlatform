import os
import random
import time
from datetime import datetime

import pytest
from game.filenode import FileNode
from game.filesystem import FileSystem
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_success
from tests.cmd_tests.path_helpers import tree_state
from tests.command_helpers import assert_help


@pytest.mark.parametrize(
    ("options", "mode"),
    [([], "basic"), (["Show Hidden"], "hidden"), (["Long Listing"], "long")],
)
def test_ls_minigame_question_uses_the_requested_directory(cl, options, mode):
    from game.GameManager import GameManager

    manager = GameManager()
    manager.set_config({
        "name": "ls game", "gameType": "MiniGames", "playType": "SinglePlayer",
        "commands": {"ls": {"selected": True, "options": options}},
        "options": {"rounds": 1, "questionCount": 1},
    })
    manager.start_round(["1"])
    question = manager.questions[0]
    goal = manager._challenge_engine.challenges[question["id"]].goal
    assert question["mode"] == mode
    assert question["example"] != goal.solution
    player = ShellState()
    player.fs.from_dict(manager.get_shell()["fs"])

    directory = goal.solution.split()[-1]
    original = player.fs.resolve(directory)
    decoy_dir = "/inventory/other"
    player.fs.add_directory(decoy_dir)
    for child in original.items:
        player.fs.add_file(f"{decoy_dir}/{child.name}")
    flag = " ".join(goal.solution.split()[1:-1])
    wrong = cl.enter_command(f"ls {flag} {decoy_dir}", player)
    assert wrong.status == 0
    assert tuple(wrong.stdout) == goal.expected_stdout
    assert not manager.record_command_runs("1", player.command_runs, wrong.stdout)

    correct = cl.enter_command(goal.solution, player)
    assert correct.status == 0
    assert tuple(correct.stdout) == goal.expected_stdout
    assert manager.record_command_runs("1", player.command_runs, correct.stdout)
    assert manager.get_game_data(player_id="1")["progress"]["completed"] == 1

def test_ls_round_uses_distinct_directory_scenarios(cl):
    from game.GameManager import GameManager

    manager = GameManager()
    manager.set_config({
        "name": "Varied ls", "gameType": "MiniGames",
        "commands": {"ls": {"selected": True, "options": []}},
        "options": {"rounds": 1, "questionCount": 3, "seed": 41},
    })
    manager.start_round(["1"])
    player = ShellState()
    player.fs.from_dict(manager.get_shell()["fs"])
    challenges = manager._challenge_engine.challenges.values()
    assert len({challenge.variant for challenge in challenges}) == 3
    assert len({challenge.prompt.split(".")[0] for challenge in challenges}) == 3
    assert sorted(
        len(player.fs.resolve(challenge.goal.solution.split()[-1]).items)
        for challenge in challenges
    ) == [2, 4, 6]
    for challenge in challenges:
        result = cl.enter_command(challenge.goal.solution, player)
        assert result.status == 0
        assert manager.record_command_runs("1", player.command_runs, result.stdout)


LS_FILES = [
    "xms.bin",
    "silly.c",
    "sigma.dat",
    "crap.js",
    "sheet.xsl",
    "nope.csv",
    "nothing.log",
    "cool.png",
    "record.ods",
    "stuff.sql",
    "annoying.java",
    "yikes.py",
]

random.shuffle(LS_FILES)

f = random.sample(LS_FILES, 10)
sizes = f[0:5]
atimes = f[5:]


def test_ls_recursive_requires_directory_read_and_search_permission(cl, shell_basic):
    directory = shell_basic.fs.filehead.access("d1")
    directory.inode.permissions["user"]["r"] = False
    assert cl.enter_command("ls -R d1", shell_basic).status != 0


@pytest.fixture
def fs_ls():
    fs = FileSystem()
    for file in LS_FILES:
        time.sleep(0.1)
        fs.add_file(file)
    time.sleep(0.5)
    fn = fs.get_file(sizes[0])
    assert isinstance(fn, FileNode)
    fn.set_data(["123456789" * 1000])
    fn = fs.get_file(atimes[0])
    assert isinstance(fn, FileNode)
    fn.get_data()
    time.sleep(0.1)
    fn = fs.get_file(sizes[1])
    assert isinstance(fn, FileNode)
    fn.set_data(["123456789" * 100])
    fn = fs.get_file(atimes[1])
    assert isinstance(fn, FileNode)
    fn.get_data()
    time.sleep(0.1)
    fn = fs.get_file(sizes[2])
    assert isinstance(fn, FileNode)
    fn.set_data(["123456789" * 50])
    fn = fs.get_file(atimes[2])
    assert isinstance(fn, FileNode)
    fn.get_data()
    time.sleep(0.1)
    fn = fs.get_file(sizes[3])
    assert isinstance(fn, FileNode)
    fn.set_data(["123456789" * 10])
    fn = fs.get_file(atimes[3])
    assert isinstance(fn, FileNode)
    fn.get_data()
    time.sleep(0.1)
    fn = fs.get_file(sizes[4])
    assert isinstance(fn, FileNode)
    fn.set_data(["123456789" * 1])
    fn = fs.get_file(atimes[4])
    assert isinstance(fn, FileNode)
    fn.get_data()
    return fs


@pytest.fixture
def shell_ls(fs_ls):
    s = ShellState()
    s.fs = fs_ls
    s.cwd = "/"
    return s


def test_ls_empty(cl, shell_empty):
    CmdResult = cl.enter_command("ls", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_ls_error(cl, shell_empty):
    CmdResult = cl.enter_command("ls -y", shell_empty)
    assert CmdResult.stderr == ["ls: unknown argument given"]
    assert CmdResult.stdout == []


def test_ls_empty_path_is_a_command_error_without_mutation(cl, shell_basic):
    before = tree_state(shell_basic)
    result = cl.enter_command('ls ""', shell_basic)
    assert result.status != 0
    assert result.stderr
    assert tree_state(shell_basic) == before


def test_ls_target(cl, shell_basic):
    CmdResult = cl.enter_command("ls d1", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f3.txt", "f4.txt"]


def test_ls_basic(cl, shell_fouritems):
    CmdResult = cl.enter_command("ls", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f1.txt", "f2.txt", "f3.txt", "f4.txt"]


def test_ls_reverse(cl, shell_fouritems):
    CmdResult = cl.enter_command("ls -r", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f4.txt", "f3.txt", "f2.txt", "f1.txt"]


def test_ls_deep(cl, shell_basic):
    CmdResult = cl.enter_command("ls -R", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f1.txt", "f2.txt", "d1", "/d1/f3.txt", "/d1/f4.txt"]


def test_ls_organisation(cl, shell_ls: ShellState):
    CmdResult = cl.enter_command("ls -X", shell_ls)
    files = LS_FILES.copy()
    print(files)
    assert CmdResult.stderr == []
    sorted_files = sorted(files, key=lambda f: os.path.splitext(f)[1])
    assert CmdResult.stdout == sorted_files

    CmdResult = cl.enter_command("ls -S", shell_ls)
    assert CmdResult.stderr == []
    for i in range(0, 5):
        assert CmdResult.stdout[i] == sizes[i]

    CmdResult = cl.enter_command("ls -t", shell_ls)
    times = sizes.copy()
    times.reverse()
    assert CmdResult.stderr == []
    for i in range(0, 5):
        assert CmdResult.stdout[i] == times[i]

    CmdResult = cl.enter_command("ls -u", shell_ls)
    atimes.reverse()
    assert CmdResult.stderr == []
    for i in range(0, 5):
        assert CmdResult.stdout[i] == atimes[i]

    CmdResult = cl.enter_command("ls -c", shell_ls)
    assert CmdResult.stderr == []
    for i in range(0, 5):
        assert CmdResult.stdout[i] == LS_FILES[-(i + 1)]


def test_ls_help(cl, shell_empty):
    assert_help(cl, shell_empty, "ls")


@pytest.mark.parametrize("options", ["", "-a", "-A", "-la", "-iA", "-Ra"])
def test_ls_dot_paths_leave_tree_unchanged(
    run_dot_command, dot_shell, dot_directory, options
):
    operand, _ = dot_directory
    before = tree_state(dot_shell)
    # The shared check runs after each listing, before a cycle could reach the
    # next recursive command or serialization.
    for _ in range(2):
        result = run_dot_command(f"ls {options} {operand}")
        assert result.status == 0
        assert result.stderr == []
    assert tree_state(dot_shell) == before


@pytest.mark.parametrize("option", ["-a", "-A"])
def test_ls_dot_paths_show_virtual_entries(run_dot_command, dot_directory, option):
    operand, target = dot_directory
    expected = {item.name for item in target.items}
    if option == "-a":
        expected.update((".", ".."))
    result = run_dot_command(f"ls {option} {operand}")
    assert result.status == 0
    assert result.stderr == []
    assert set(result.stdout) == expected
    assert len(result.stdout) == len(expected)


def test_ls_dot_paths_regular_file(run_dot_command, dot_prefix):
    path = f"{dot_prefix}data.txt"
    assert_success(run_dot_command(f"ls {path}"), [path])


def test_ls_one_directory_entry_is_not_an_error(run_dot_command):
    assert_success(run_dot_command("ls branch"), ["leaf.txt"])


def test_ls_missing_path_reports_failure(run_dot_command):
    result = run_dot_command("ls missing")
    assert result.status != 0
    assert result.stdout == []
    assert any("missing" in message for message in result.stderr)


def test_ls_file_operand_uses_its_own_metadata(run_dot_command, dot_shell):
    file = dot_shell.fs.current.access("data.txt")
    file.inode.mtime = datetime(2001, 1, 2)

    result = run_dot_command("ls -li ./data.txt")

    assert_success(
        result,
        [
            f"{file.inode.id} {file.get_permission_str(file)} 1 user user "
            f"{file.get_size()} Jan 2 2001 ./data.txt"
        ],
    )
