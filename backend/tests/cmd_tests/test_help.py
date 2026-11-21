from game.command_contract import COMMAND_CONTRACTS, format_command_help
from tests.cmd_tests.path_helpers import tree_state


def test_help_lists_every_registered_command_with_descriptions(cl, shell_empty):
    result = cl.enter_command("help", shell_empty)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout[0] == "Available commands:"
    assert result.stdout[-1] == "Run 'help COMMAND' for details."
    assert set(cl.commands) == set(COMMAND_CONTRACTS)
    listing = result.stdout[1:-1]
    assert [line.split()[0] for line in listing] == sorted(cl.commands)
    for line, command in zip(listing, sorted(cl.commands)):
        assert COMMAND_CONTRACTS[command][0] in line


def test_help_shows_existing_command_details(cl, shell_empty):
    result = cl.enter_command("help ls", shell_empty)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == format_command_help("ls")


def test_help_documents_itself(cl, shell_empty):
    result = cl.enter_command("help --help", shell_empty)

    assert result.status == 0
    assert result.stdout == format_command_help("help")


def test_help_rejects_unknown_command_and_extra_operands(cl, shell_empty):
    before = tree_state(shell_empty)

    unknown = cl.enter_command("help nonexistent", shell_empty)
    extra = cl.enter_command("help ls pwd", shell_empty)

    assert unknown.status == 1
    assert unknown.stderr == ["help: unknown command 'nonexistent'"]
    assert extra.status == 1
    assert extra.stderr == ["help: expected one command name"]
    assert tree_state(shell_empty) == before
