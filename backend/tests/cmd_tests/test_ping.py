import pytest
from tests.command_helpers import assert_help


@pytest.mark.parametrize("destination", [".", "..", "127.0.0.1"])
def test_ping_dot_paths_do_not_resolve_filesystem(run_dot_command, destination):
    # Network destinations are not filesystem paths. Leave their validity to
    # ping's network contract; enforce that even dot-like names leave FS intact.
    run_dot_command(f"ping {destination}")


def test_ping_help(cl, shell_empty):
    assert_help(cl, shell_empty, "ping")
