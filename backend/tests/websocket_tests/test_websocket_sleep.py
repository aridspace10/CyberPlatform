def test_websocket_sleep(session):
    session.send_command("sleep 2")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"]
    assert response["interaction"]["mode"] == "foreground"

    response = session.receive_until(lambda m: m.get("type") == "terminal_state")
    assert not response["busy"]
