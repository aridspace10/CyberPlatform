from game.command_contract import COMMAND_CONTRACTS
from tests.cmd_tests.creation_helpers import assert_success


def test_echo_dot_paths_are_literal_text(run_dot_command):
    assert_success(run_dot_command("echo . .. ./ branch/.."), [". .. ./ branch/.."])


def test_echo_basic(cl, shell_empty):
    # echo should return CmdResult.stdout containing the args joined
    CmdResult = cl.enter_command("echo hello world", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hello world"]


def test_echo_help_argument_is_literal(cl, shell_empty):
    assert_success(cl.enter_command("echo --help", shell_empty), ["--help"])


def test_registry_has_truthful_contract_for_every_command(cl):
    assert set(cl.commands) == set(COMMAND_CONTRACTS)
