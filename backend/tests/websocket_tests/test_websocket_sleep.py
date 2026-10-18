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
