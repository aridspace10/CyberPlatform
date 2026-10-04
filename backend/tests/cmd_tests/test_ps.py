from tests.command_helpers import assert_help


def test_ps_dot_paths_do_not_change_filesystem(run_dot_command):
    # ps has no path operands. Its filesystem contract is cwd/tree preservation.
    result = run_dot_command("ps")
    assert result.status == 0
    assert result.stderr == []


def test_ps_help(cl, shell_empty):
    assert_help(cl, shell_empty, "ps")
