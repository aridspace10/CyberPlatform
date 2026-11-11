import json
import time

from network.SessionManger import session_manager
from services.session_logging import SessionLogger


def test_command_output_contains_echo(session):
    session.send_command("echo hello")
    # Skip any intermediate messages, find the output one
    output_msg = session.receive_until(lambda m: m.get("type") == "command_output")
    assert "hello" in output_msg["stdout"]
    assert output_msg["status"] == 0


def test_grep_no_match_reports_exit_status_without_output(session):
    player = session.game_session.players["jackson"]
    player.shell.fs.add_file("/sample.txt")
    player.shell.fs.resolve("/sample.txt").set_data(["present"])

    session.send_command("grep absent /sample.txt")
    output = session.receive_until(
        lambda message: message.get("type") == "command_output"
    )
    assert output["status"] == 1
    assert output["stdout"] == []
    assert output["stderr"] == []


def test_grep_question_progress_is_sent_to_player(session):
    game = session.game_session
    game.game_manager.set_config({
        "name": "Grep game", "gameType": "MiniGames", "playType": "SinglePlayer",
        "commands": {"grep": {"selected": True}}, "options": {"rounds": 1},
    })
    shell = game.game_manager.start_round(["1"])
    player = game.players["jackson"]
    player.shell.commands = shell["cmds"]
    player.shell.fs.from_dict(shell["fs"])
    game.state = "running"

    words = game.game_manager.questions[0]["prompt"].split()
    marker, path = words[-3], words[-1]
    session.send_command(f"grep {marker} {path}")
    output = session.receive_until(
        lambda message: message.get("type") == "command_output"
    )
    assert marker in output["stdout"][0]
    update = session.receive_until(
        lambda message: message.get("type") == "lobby_update"
    )
    assert update["gameData"]["progress"] == {"completed": 1, "total": 10}
    assert update["gameData"]["questions"][0]["status"] == "completed"


def test_versus_round_starts_for_both_players_and_expires(session, client):
    game = session.game_session
    game.game_manager.set_config({
        "name": "Versus grep", "gameType": "MiniGames", "playType": "Versus",
        "creatorID": 1,
        "commands": {"grep": {"selected": True}},
        "options": {"rounds": 1, "timeLimitSeconds": 60},
    })
    with client.websocket_connect(f"/ws/{game.session_id}") as opponent:
        opponent.send_json({"username": "opponent", "userID": "2"})
        opponent.receive_json()
        opponent.receive_json()
        session.ws.send_json({"type": "start_game"})
        started = session.receive_until(
            lambda message: message.get("type") == "lobby_update"
            and message.get("state") == "running"
        )
        assert len(started["gameData"]["questions"]) == 10
        assert started["gameData"]["deadline"] is not None
        assert game.players["jackson"].shell.fs.to_dict()["nodes"]["items"]
        assert game.players["opponent"].shell.fs.to_dict()["nodes"]["items"]

        game.game_manager.deadline = 0
        client.portal.call(game.finish_round_if_ready)
        ended = session.receive_until(
            lambda message: message.get("type") == "lobby_update"
            and message.get("state") == "finished"
        )
        assert ended["gameData"]["finished"] is True


def test_ten_grep_answers_advance_to_fresh_round(session):
    game = session.game_session
    game.game_manager.set_config({
        "name": "Grep rounds", "gameType": "MiniGames", "playType": "SinglePlayer",
        "commands": {"grep": {"selected": True}}, "options": {"rounds": 2},
    })
    shell = game.game_manager.start_round(["1"])
    player = game.players["jackson"]
    player.shell.commands = shell["cmds"]
    player.shell.fs.from_dict(shell["fs"])
    game.state = "running"
    first_prompts = [question["prompt"] for question in game.game_manager.questions]

    for index, prompt in enumerate(first_prompts, start=1):
        marker, path = prompt.split()[-3], prompt.split()[-1]
        session.send_command(f"grep {marker} {path}")
        session.receive_until(lambda message: message.get("type") == "command_output")
        update = session.receive_until(
            lambda message, expected=index: message.get("type") == "lobby_update"
            and message["gameData"]["progress"]["completed"] == expected
        )
        assert update["gameData"]["round"] == 1

    next_round = session.receive_until(
        lambda message: message.get("type") == "lobby_update"
        and message["gameData"]["round"] == 2
    )
    assert next_round["gameData"]["progress"] == {"completed": 0, "total": 10}
    assert next_round["gameData"]["leaderboard"][0]["completed"] == 10
    next_prompts = [
        question["prompt"] for question in next_round["gameData"]["questions"]
    ]
    assert next_prompts != first_prompts


def test_mixed_grep_and_sed_round_finishes_from_terminal_commands(session):
    game = session.game_session
    game.game_manager.set_config({
        "name": "Mixed round", "gameType": "MiniGames", "playType": "SinglePlayer",
        "commands": {
            "grep": {"selected": True, "options": []},
            "sed": {"selected": True, "options": []},
        },
        "options": {"rounds": 1, "questionCount": 2},
    })
    shell = game.game_manager.start_round(["1"])
    player = game.players["jackson"]
    player.shell.commands = shell["cmds"]
    player.shell.fs.from_dict(shell["fs"])
    game.state = "running"
    assert {question["command"] for question in game.game_manager.questions} == {
        "grep", "sed",
    }

    for expected, question in enumerate(game.game_manager.questions, start=1):
        answer = game.game_manager._answers[question["id"]]
        if question["command"] == "grep":
            words = question["prompt"].split()
            command = f"grep {words[-3]} {words[-1]}"
        else:
            source = answer["before"][1].split()[0]
            replacement = answer["after"][1].split()[0]
            command = f"sed 's/{source}/{replacement}/' {answer['path']}"
        session.send_command(command)
        session.receive_until(
            lambda message: message.get("type") == "command_output"
        )
        update = session.receive_until(
            lambda message, count=expected: message.get("type") == "lobby_update"
            and message["gameData"]["progress"]["completed"] == count
        )
        assert update["gameData"]["progress"]["total"] == 2

    finished = session.receive_until(
        lambda message: message.get("type") == "lobby_update"
        and message["state"] == "finished"
    )
    assert finished["gameData"]["leaderboard"][0]["completed"] == 2


def test_background_job_keeps_prompt_available_and_streams_completion(session):
    session.send_command("echo background & echo foreground")
    response = session.receive_until(
        lambda message: message.get("type") == "command_output"
    )

    assert response["stdout"][0].startswith("[job ")
    assert response["stdout"][-1] == "foreground"
    assert response["interaction"] is None
    assert session.game_session.players["jackson"].shell.foreground_pid is None

    completion = session.receive_until(
        lambda message: message.get("type") == "background_job_complete"
    )
    assert completion["stdout"] == ["background"]
    assert completion["stderr"] == []
    assert completion["status"] == 0


def test_removed_session_rejects_commands_on_existing_websocket(session, client):
    game_session = session.game_session
    client.portal.call(
        session_manager.remove_session, game_session.session_id
    )

    session.send_command("sleep 5 &")
    response = session.receive_until(
        lambda message: message.get("type") == "command_output"
    )

    assert response["stderr"] == ["Session is closed"]
    assert game_session.players["jackson"].shell.background_jobs == {}
    assert not any(
        process.command.startswith("sleep ")
        for process in game_session.process_manager.processes.values()
    )


def test_background_job_cancellation_stops_its_child(session):
    session.send_command("sleep 30 &")
    response = session.receive_until(
        lambda message: message.get("type") == "command_output"
    )
    job_id = int(response["stdout"][0].split()[1].rstrip("]"))
    session.ws.send_json(
        {"type": "cancel_background_job", "job_id": job_id}
    )
    cancelled = session.receive_until(
        lambda message: message.get("type") == "background_job_cancelled"
    )
    assert cancelled["cancelled"] is True
    completion = session.receive_until(
        lambda message: message.get("type") == "background_job_complete"
    )
    assert completion["job_id"] == job_id
    assert completion["status"] == 130
    assert "background job cancelled" in completion["stderr"]


def test_background_job_uses_launch_directory_without_changing_foreground(session):
    session.send_command("mkdir launch-dir && cd launch-dir && pwd")
    session.receive_until(lambda message: message.get("type") == "command_output")
    session.send_command("cd / && pwd & pwd")
    response = session.receive_until(
        lambda message: message.get("type") == "command_output"
    )

    assert response["stdout"][-1] == "/launch-dir"
    completion = session.receive_until(
        lambda message: message.get("type") == "background_job_complete"
    )
    assert completion["stdout"] == ["/"]
    assert completion["status"] == 0
    assert session.game_session.players["jackson"].shell.cwd == "/launch-dir"


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


def test_heredoc_pipeline_resumes_after_delimiter(session):
    session.send_command("cat << EOF | cut -d : -f 1")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"] == {"mode": "foreground", "prompt": ">"}

    session.send_command("alice:admin")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stdout"] == []
    assert response["interaction"] == {"mode": "foreground", "prompt": ">"}

    session.send_command("EOF")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stdout"] == ["alice"]
    assert response["stderr"] == []
    assert response["interaction"] is None


def test_heredoc_redirection_resumes_following_list_command(session):
    session.send_command("cat << EOF > input.txt; echo saved")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"] == {"mode": "foreground", "prompt": ">"}
    session.send_command("contents")
    session.receive_until(lambda m: m.get("type") == "command_output")
    session.send_command("EOF")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stdout"] == ["saved"]
    assert response["interaction"] is None

    session.send_command("cat input.txt")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stdout"] == ["contents"]


def test_rm_interactive_completion_resumes_conditional(session):
    session.send_command("touch remove-me.txt")
    session.receive_until(lambda m: m.get("type") == "command_output")
    session.send_command("rm -i remove-me.txt && echo removed")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"]["prompt"].startswith("rm: remove regular file")

    session.send_command("y")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stdout"] == ["removed"]
    assert response["interaction"] is None
    session.send_command("ls remove-me.txt")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stderr"]


def test_sequential_foreground_programs_each_receive_input(session):
    session.send_command("touch next.txt")
    session.receive_until(lambda m: m.get("type") == "command_output")
    session.send_command("cat << EOF; rm -i next.txt")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"] == {"mode": "foreground", "prompt": ">"}

    session.send_command("captured")
    session.receive_until(lambda m: m.get("type") == "command_output")
    session.send_command("EOF")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"]["prompt"].startswith("rm: remove regular file")

    session.send_command("y")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["interaction"] is None
    session.send_command("ls next.txt")
    response = session.receive_until(lambda m: m.get("type") == "command_output")
    assert response["stderr"]
