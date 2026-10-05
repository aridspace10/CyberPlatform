from tests.command_helpers import assert_command_error_without_mutation, assert_help


def test_ps_dot_paths_do_not_change_filesystem(run_dot_command):
    # ps has no path operands. Its filesystem contract is cwd/tree preservation.
    result = run_dot_command("ps")
    assert result.status == 0
    assert result.stderr == []


def test_ps_help(cl, shell_empty):
    assert_help(cl, shell_empty, "ps")


def test_ps_missing_option_value_returns_command_error(cl, shell_empty):
    result = assert_command_error_without_mutation(cl, shell_empty, "ps -C")
    assert result.stderr == ["ps: argument required for -C"]
