from tests.cmd_tests.creation_helpers import assert_success
from tests.cmd_tests.path_helpers import canonical_path, tree_state
from tests.command_helpers import assert_help


def test_pwd_help_documents_no_logical_or_physical_flags(cl, shell_empty):
    assert_help(cl, shell_empty, "pwd")
    help_text = "".join(cl.enter_command("pwd --help", shell_empty).stdout)
    assert "No -L/-P flags" in help_text


def test_pwd_dot_paths_report_canonical_directory(run_dot_command, dot_shell):
    expected = canonical_path(dot_shell.fs.current)
    assert_success(run_dot_command("pwd"), [expected])


def test_pwd_dot_paths_after_navigation(run_dot_command, dot_shell, dot_directory):
    operand, target = dot_directory
    # Navigation has its own assertions in test_cd.py. This test additionally
    # ensures pwd agrees with the directory reached through a dotted path.
    run_dot_command(f"cd {operand}", navigates_to=target)
    expected = canonical_path(target)
    assert_success(run_dot_command("pwd"), [expected])


def test_pwd_rejects_unexpected_operands_without_mutation(cl, shell_basic):
    before = tree_state(shell_basic)
    result = cl.enter_command("pwd --bad", shell_basic)
    assert result.status != 0
    assert result.stderr == ["pwd: unexpected operand '--bad'"]
    assert tree_state(shell_basic) == before
