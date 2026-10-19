import pytest


def test_websocket_sleep(session):
    session.send_command("sleep 2")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"]
    assert response["interaction"]["mode"] == "foreground"

    response = session.receive_until(lambda m: m.get("type") == "terminal_state")
    assert not response["busy"]


def test_sleep_conditional_runs_only_after_scheduler_completion(session):
    session.send_command("sleep 1 && echo done")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stdout"] == []
    assert response["interaction"]["mode"] == "foreground"

    response = session.receive_until(
        lambda m: m.get("type") == "command_output" and m.get("stdout") == ["done"]
    )
    assert response["stderr"] == []
    assert response["interaction"] is None


@pytest.mark.parametrize(
    "command",
    [
        "echo before; sleep 1; echo after",
        "echo before && sleep 1 && echo after",
    ],
)
def test_sleep_composed_commands_emit_each_line_once_and_keep_final_status(
    session, command
):
    session.send_command(command)
    initial = session.receive_until(lambda message: message.get("type") == "command_output")
    assert initial["interaction"]["mode"] == "foreground"

    resumed = session.receive_until(
        lambda message: message.get("type") == "command_output"
        and message.get("interaction") is None
    )

    all_output = initial["stdout"] + resumed["stdout"]
    assert all_output == ["before", "after"]
    assert initial["stdout"].count("before") + resumed["stdout"].count("before") == 1
    assert initial["stdout"].count("after") + resumed["stdout"].count("after") == 1
    assert session.game_session.players["jackson"].shell.last_status == 0


def test_sleep_continuation_chains_or_then_and_operators(session):
    session.send_command("missing-command || sleep 1 && echo resumed")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stderr"] == ["Unknown command given"]
    assert response["interaction"]["mode"] == "foreground"

    response = session.receive_until(
        lambda m: m.get("type") == "command_output"
        and m.get("stdout") == ["resumed"]
    )
    assert response["stderr"] == []
    assert response["interaction"] is None


def test_sleep_rejects_input_without_calling_program_input_handler(session):
    session.send_command("sleep 2")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"]["mode"] == "foreground"

    session.send_command("unexpected input")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stderr"] == ["Foreground process is not accepting input"]
    assert response["interaction"]["mode"] == "foreground"


def test_cancelling_sleep_resumes_failure_conditional(session):
    session.send_command("sleep 10 || echo cancelled")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"]["mode"] == "foreground"

    session.send_command("\x03")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stdout"] == ["cancelled"]
    assert response["interaction"] is None
