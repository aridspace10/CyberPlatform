import random
from pathlib import Path

from game.ShellState import ShellState
from tests.cmd_tests.path_helpers import tree_state
from wonderwords import RandomWord


def setup_names(s: ShellState, name: str) -> list[str]:
    amount = random.randint(5, 25)
    names = []
    r = RandomWord()
    for _ in range(0, amount):
        names.append(r.word())
    s.fs.search(name)
    s.fs.current.set_data(names)
    s.fs.current = s.fs.filehead
    names.sort()
    return names


def assert_help(cl, shell, command):
    result = cl.enter_command(f"{command} --help", shell)
    help_path = (
        Path(__file__).resolve().parents[2] / "static" / "help" / f"{command}.txt"
    )
    assert result.stderr == []
    assert result.stdout == help_path.read_text().splitlines(keepends=True)


def assert_command_error_without_mutation(cl, shell, command):
    before = tree_state(shell)
    current = shell.fs.current
    fs_cwd = shell.fs.cwd
    shell_cwd = shell.cwd

    result = cl.enter_command(command, shell)

    assert result.status != 0, f"{command!r} should fail as invalid input"
    assert result.stderr, f"{command!r} should explain the input error"
    assert tree_state(shell) == before, f"{command!r} changed filesystem state"
    assert shell.fs.current is current
    assert shell.fs.cwd == fs_cwd
    assert shell.cwd == shell_cwd
    return result
