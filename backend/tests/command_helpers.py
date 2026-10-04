import random
from pathlib import Path

from game.ShellState import ShellState
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
