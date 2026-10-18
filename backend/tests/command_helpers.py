import random

from game.command_contract import COMMAND_CONTRACTS, format_command_help
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
    assert result.stderr == []
    assert result.stdout == format_command_help(command)
    assert set(cl.commands) == set(COMMAND_CONTRACTS)


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
