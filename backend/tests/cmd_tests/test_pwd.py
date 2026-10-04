from tests.cmd_tests.creation_helpers import assert_success
from tests.cmd_tests.path_helpers import canonical_path


def test_pwd_dot_paths_report_canonical_directory(run_dot_command, dot_shell):
    # Retain the simulator's displayed root name while checking a normalized path.
    expected = dot_shell.fs.filehead.name + canonical_path(dot_shell.fs.current).rstrip(
        "/"
    )
    assert_success(run_dot_command("pwd"), [expected])


def test_pwd_dot_paths_after_navigation(run_dot_command, dot_shell, dot_directory):
    operand, target = dot_directory
    # Navigation has its own assertions in test_cd.py. This test additionally
    # ensures pwd agrees with the directory reached through a dotted path.
    run_dot_command(f"cd {operand}", navigates_to=target)
    expected = dot_shell.fs.filehead.name + canonical_path(target).rstrip("/")
    assert_success(run_dot_command("pwd"), [expected])
