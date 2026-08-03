import time


def test_command_output_contains_echo(session):
    session.send_command("echo hello")
    # Skip any intermediate messages, find the output one
    output_msg = session.receive_until(lambda m: m.get("type") == "command_output")
    assert "hello" in output_msg["stdout"]


def test_rm_command(session):
    files = ["alpha.txt", "bravo.txt", "charlie.txt"]
    session.send_command(f"touch {' '.join(files)}")
    session.receive_until(lambda m: m.get("type") == "command_output")

    session.send_command(f"rm -i {' '.join(files)}")
    response = session.receive()
    assert response["type"] == "command_output"
    assert response["interaction"]["mode"] == "foreground"
    assert response["interaction"]["prompt"] == "rm: remove regular file 'alpha.txt'?"
    session.send_command("y")
    response = session.receive()
    assert response["type"] == "command_output"
    assert response["interaction"]["mode"] == "foreground"
    assert response["interaction"]["prompt"] == "rm: remove regular file 'bravo.txt'?"
    session.send_command("n")
    response = session.receive()
    assert response["type"] == "command_output"
    assert response["interaction"]["mode"] == "foreground"
    assert response["interaction"]["prompt"] == "rm: remove regular file 'charlie.txt'?"
    session.send_command("y")
    response = session.receive()
    assert response["type"] == "command_output"
    assert response["interaction"] is None
    session.send_command("ls")
    response = session.receive()
    assert response["type"] == "command_output"
    assert response["stdout"] == ["bravo.txt"]


def test_rm_waiting_for_input_does_not_stop_scheduler(session):
    session.send_command("touch delayed.txt")
    session.receive_until(lambda m: m.get("type") == "command_output")

    session.send_command("rm -i delayed.txt")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"]["mode"] == "foreground"

    time.sleep(1.2)
    assert session.game_session.scheduler_task is not None
    assert not session.game_session.scheduler_task.done()

    session.send_command("n")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"] is None


def test_heredoc_executes_captured_input(session):
    session.send_command("cat << EOF")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"] == {"mode": "foreground", "prompt": ">"}

    session.send_command("hello from heredoc")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stdout"] == []
    assert response["interaction"] == {"mode": "foreground", "prompt": ">"}

    session.send_command("EOF")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stdout"] == ["hello from heredoc"]
    assert response["stderr"] == []
    assert response["interaction"] is None
