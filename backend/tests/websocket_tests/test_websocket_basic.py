import json
import time

from services.session_logging import SessionLogger


def test_command_output_contains_echo(session):
    session.send_command("echo hello")
    # Skip any intermediate messages, find the output one
    output_msg = session.receive_until(lambda m: m.get("type") == "command_output")
    assert "hello" in output_msg["stdout"]


def test_bad_input_and_unexpected_command_error_keep_websocket_usable(
    session, monkeypatch, tmp_path
):
    monkeypatch.setenv("CYBERPLATFORM_LOG_DIR", str(tmp_path / "logs"))
    logger = SessionLogger(session.game_session.session_id)
    session.game_session.logger = logger

    original_enter_command = session.game_session.commandline.enter_command

    def fail_one_command(raw, shell):
        if raw == "explode":
            raise RuntimeError("diagnostic-only failure")
        return original_enter_command(raw, shell)

    monkeypatch.setattr(
        session.game_session.commandline, "enter_command", fail_one_command
    )

    session.send_command("head -n")
    bad_input = session.receive_until(
        lambda message: message.get("type") == "command_output"
    )
    assert bad_input["stderr"] == ["head: argument required for -n"]

    session.send_command("explode")
    unexpected_error = session.receive_until(
        lambda message: message.get("type") == "command_output"
    )
    assert "diagnostic-only failure" not in " ".join(unexpected_error["stderr"])
    assert "logged" in " ".join(unexpected_error["stderr"])

    session.send_command("echo recovered")
    recovered = session.receive_until(
        lambda message: message.get("type") == "command_output"
    )
    assert recovered["stdout"] == ["recovered"]

    errors = [json.loads(line) for line in logger.error_path.read_text().splitlines()]
    assert len(errors) == 1
    assert errors[0]["exception_type"] == "RuntimeError"
    assert "diagnostic-only failure" in errors[0]["traceback"]

    activities = [
        json.loads(line) for line in logger.activity_path.read_text().splitlines()
    ]
    terminal_inputs = [
        record for record in activities if record["event"] == "terminal_input"
    ]
    assert [record["input"] for record in terminal_inputs] == [
        "head -n",
        "explode",
        "echo recovered",
    ]
    assert terminal_inputs[0]["outcome"] == "completed"
    assert terminal_inputs[1]["outcome"] == "exception"
    assert terminal_inputs[1]["request_id"] == errors[0]["request_id"]


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
