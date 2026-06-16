def test_command_output_contains_echo(session):
    session.send_command("echo hello")
    # Skip any intermediate messages, find the output one
    output_msg = session.receive_until(lambda m: m.get("type") == "command_output")
    assert "hello" in output_msg["stdout"]


def test_rm_command(session):
    a = session.add_random_file()
    b = session.add_random_file()
    c = session.add_random_file()
    session.send_command(f"rm -i {a} {b} {c}")
    response = session.receive()
    assert response["type"] == "command_output"
    assert response["interaction"]["mode"] == "foreground"
    assert response["interaction"]["prompt"] == f"rm: remove regular file '{a}'?"
    session.send_command("y")
    response = session.receive()
    assert response["type"] == "command_output"
    assert response["interaction"]["mode"] == "foreground"
    assert response["interaction"]["prompt"] == f"rm: remove regular file '{b}'?"
    session.send_command("n")
    response = session.receive()
    assert response["type"] == "command_output"
    assert response["interaction"]["mode"] == "foreground"
    assert response["interaction"]["prompt"] == f"rm: remove regular file '{c}'?"
    session.send_command("y")
    response = session.receive()
    assert response["type"] == "command_output"
    assert response["interaction"] is None
    raise AssertionError()
