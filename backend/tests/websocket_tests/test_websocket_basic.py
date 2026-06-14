def test_rm_command(session):
    session.send_command("rm -i .")
    response = session.receive()
    assert response is not None


def test_command_output_contains_echo(session):
    session.send_command("echo hello")
    # Skip any intermediate messages, find the output one
    output_msg = session.receive_until(lambda m: m.get("type") == "command_output")
    assert "hello" in output_msg["stdout"]
