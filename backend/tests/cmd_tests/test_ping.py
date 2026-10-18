import pytest
from tests.command_helpers import assert_command_error_without_mutation, assert_help


@pytest.mark.parametrize("destination", [".", "..", "127.0.0.1"])
def test_ping_dot_paths_do_not_resolve_filesystem(run_dot_command, destination):
    # Network destinations are not filesystem paths. Leave their validity to
    # ping's network contract; enforce that even dot-like names leave FS intact.
    run_dot_command(f"ping {destination}")


def test_ping_help(cl, shell_empty):
    assert_help(cl, shell_empty, "ping")


@pytest.mark.parametrize("command", ["ping", "ping -i", "ping -i nope host", 'ping ""'])
def test_ping_invalid_input_is_a_command_error_without_mutation(
    cl, shell_empty, command
):
    assert_command_error_without_mutation(cl, shell_empty, command)


def test_ping_online_simulated_gateway(cl, shell_empty):
    result = cl.enter_command("ping gateway -c 2", shell_empty)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == [
        "PING gateway (192.0.2.1): 56 data bytes",
        "64 bytes from 192.0.2.1: icmp_seq=1 ttl=64 time=10.0 ms",
        "64 bytes from 192.0.2.1: icmp_seq=2 ttl=64 time=10.0 ms",
        "--- gateway ping statistics ---",
        "2 packets transmitted, 2 received, 0% packet loss",
    ]
    assert shell_empty.foreground_pid is None
    assert cl.process_manager.processes == {}


def test_ping_resolves_simulated_ip_address(cl, shell_empty):
    result = cl.enter_command("ping 192.0.2.1 -c 1", shell_empty)

    assert result.status == 0
    assert "64 bytes from 192.0.2.1: icmp_seq=1" in result.stdout[1]
    assert result.stdout[-1] == "1 packets transmitted, 1 received, 0% packet loss"


def test_ping_offline_destination_reports_unreachable(cl, shell_empty):
    result = cl.enter_command("ping offline-host -c 2", shell_empty)

    assert result.status == 1
    assert result.stdout[1:3] == [
        "From 192.0.2.2 icmp_seq=1 Destination Host Unreachable",
        "From 192.0.2.2 icmp_seq=2 Destination Host Unreachable",
    ]
    assert result.stdout[-1] == "2 packets transmitted, 0 received, 100% packet loss"


def test_ping_unknown_destination_returns_error_status(cl, shell_empty):
    result = cl.enter_command("ping missing-host", shell_empty)

    assert result.status == 2
    assert result.stderr == ["ping: unknown simulated destination 'missing-host'"]
    assert result.stdout == []


def test_ping_timeout_can_reject_online_simulated_responses(cl, shell_empty):
    result = cl.enter_command("ping -W 0.005 gateway -c 1", shell_empty)

    assert result.status == 1
    assert result.stdout[1] == "Request timeout for icmp_seq=1"
    assert result.stdout[-1] == "1 packets transmitted, 0 received, 100% packet loss"


@pytest.mark.parametrize(
    "command",
    [
        "ping -c 0 gateway",
        "ping -c 11 gateway",
        "ping -c many gateway",
        "ping -c gateway",
        "ping -W nope gateway",
        "ping -W 0 gateway",
        "ping -W 61 gateway",
        "ping -W gateway",
        "ping -i 1 gateway",
        "ping gateway second-host",
    ],
)
def test_ping_rejects_invalid_options_and_arguments(cl, shell_empty, command):
    result = assert_command_error_without_mutation(cl, shell_empty, command)
    assert result.status != 0


def test_ping_count_one_terminates_with_one_reply(cl, shell_empty):
    result = cl.enter_command("ping -c 1 gateway", shell_empty)

    assert result.status == 0
    assert sum("icmp_seq=" in line for line in result.stdout) == 1
    assert result.stdout[-1] == "1 packets transmitted, 1 received, 0% packet loss"
