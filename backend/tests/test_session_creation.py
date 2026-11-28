import asyncio
from types import SimpleNamespace

import pytest
from api.sessions import router
from db.authentication import create_access_token
from db.modals import (
    Base,
    Friendship,
    GameSession,
    Scenario,
    ScenarioToSession,
    SessionShell,
    User,
)
from db.session import get_db
from fastapi import FastAPI
from fastapi.testclient import TestClient
from game.GameManager import GameManager
from network.SessionManger import GameSession as RuntimeGameSession
from network.SessionManger import Player, session_manager
from network.WebsocketServer import router as websocket_router
from routers.users import get_db as get_users_db
from routers.users import router as users_router
from services.game_state import transition_and_persist
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect


def make_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    db.add(User(id=42, username="creator", email="creator@example.com", password="x"))
    db.add(User(id=43, username="guest", email="guest@example.com", password="x"))
    db.add(Scenario(id=7, name="MiniGames", config={"name": "MiniGames"}))
    db.add(Scenario(id=8, name="Tutorial", config='{"name": "Tutorial"}'))
    db.commit()
    db.close()

    def override_get_db():
        database = testing_session()
        try:
            yield database
        finally:
            database.close()

    app = FastAPI()
    app.include_router(router)
    app.include_router(websocket_router)
    app.include_router(users_router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_users_db] = override_get_db
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer " + create_access_token(
        {"sub": 42, "username": "creator"}
    )
    return client, testing_session


def creation_payload(play_type: str) -> dict:
    return {
        "config": {
            "name": f"{play_type} session",
            "playType": play_type,
            "visibility": "public",
            "gameType": "MiniGames",
            "creatorID": 42,
            "commands": {
                "grep": {
                    "selected": True,
                    "options": ["Case Insensitive", "Show Line Number"],
                },
                "sed": {"selected": False, "options": []},
            },
            "options": {
                "allowPipes": True,
                "rounds": 8,
                "questionCount": 6,
                "timeLimitSeconds": 300,
            },
        }
    }


def authorization(user_id: int, username: str) -> dict:
    return {
        "Authorization": "Bearer "
        + create_access_token({"sub": user_id, "username": username})
    }


def test_create_session_hands_complete_config_to_game_manager():
    client, testing_session = make_client()

    with client:
        response = client.post("/api/session_create", json=creation_payload("Versus"))

        assert response.status_code == 201
        result = response.json()
        assert result["state"] == "waiting"

        runtime = session_manager.get_session(str(result["session_id"]))
        assert runtime != "404"
        assert runtime.state == "waiting"
        assert runtime.game_manager.init_config == creation_payload("Versus")["config"]
        assert runtime.game_manager.commands == ["grep"]
        assert runtime.game_manager.allow_pipes is True
        assert runtime.game_manager.num_rounds == 8
        assert runtime.game_manager.question_count == 6
        game_data = runtime.game_manager.get_game_data(runtime.name)
        assert game_data["questions"] == []
        assert game_data["round"] == 0
        assert game_data["progress"] == {"completed": 0, "total": 6}

        db = testing_session()
        scenario = db.query(ScenarioToSession).one()
        shell = db.query(SessionShell).one()
        assert scenario.config == creation_payload("Versus")["config"]
        assert shell.shell["cmds"] == ["grep"]
        db.close()

        client.portal.call(
            session_manager.remove_session, str(response.json()["session_id"])
        )


def test_single_player_session_starts_running():
    client, _testing_session = make_client()

    with client:
        response = client.post(
            "/api/session_create", json=creation_payload("SinglePlayer")
        )

        assert response.status_code == 201
        result = response.json()
        assert result["state"] == "running"

        runtime = session_manager.get_session(str(result["session_id"]))
        assert runtime != "404"
        assert runtime.state == "running"

        session_response = client.get(f"/api/session/{result['session_id']}")
        assert session_response.status_code == 200
        assert session_response.json()["gameData"]["sessionName"] == (
            "SinglePlayer session"
        )
        assert session_response.json()["gameData"]["progress"] == {
            "completed": 0,
            "total": 6,
        }
        assert len(session_response.json()["gameData"]["questions"]) == 6

        client.portal.call(session_manager.remove_session, str(result["session_id"]))


def test_running_minigame_reopens_with_a_fresh_playable_round():
    client, testing_session = make_client()
    with client:
        response = client.post(
            "/api/session_create", json=creation_payload("SinglePlayer")
        )
        assert response.status_code == 201
        session_id = str(response.json()["session_id"])
        original = session_manager.get_session(session_id)
        old_prompts = [
            question["prompt"] for question in original.game_manager.questions
        ]
        client.portal.call(session_manager.remove_session, session_id)

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.send_json(
                {
                    "userID": "999",
                    "username": "forged",
                    "token": create_access_token({"sub": 42, "username": "creator"}),
                }
            )
            websocket.receive_json()
            lobby = websocket.receive_json()
            assert lobby["state"] == "running"
            assert lobby["players"] == ["creator"]
            assert lobby["gameData"]["creatorID"] == 42
            assert len(lobby["gameData"]["questions"]) == 6
            assert [q["prompt"] for q in lobby["gameData"]["questions"]] != old_prompts
            assert (
                session_manager.get_session(session_id).players["creator"].user_id
                == "42"
            )

            prompt = next(
                q["prompt"]
                for q in lobby["gameData"]["questions"]
                if q["mode"] == "basic"
            )
            marker, path = prompt.split()[-3], prompt.split()[-1]
            websocket.send_json({"type": "command", "input": f"grep {marker} {path}"})
            output = websocket.receive_json()
            assert output["type"] == "command_output"
            assert output["status"] == 0
            assert marker in output["stdout"][0]

        db = testing_session()
        saved = db.query(SessionShell).one()
        assert (
            saved.shell["fs"]
            == session_manager.get_session(session_id).game_manager.get_shell()["fs"]
        )
        db.close()
        client.portal.call(session_manager.remove_session, session_id)


def test_waiting_versus_reopens_with_saved_host_config():
    client, _testing_session = make_client()
    with client:
        response = client.post("/api/session_create", json=creation_payload("Versus"))
        assert response.status_code == 201
        session_id = str(response.json()["session_id"])
        client.portal.call(session_manager.remove_session, session_id)

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.send_json(
                {
                    "token": create_access_token({"sub": 42, "username": "creator"}),
                }
            )
            websocket.receive_json()
            lobby = websocket.receive_json()
            assert lobby["state"] == "waiting"
            assert lobby["gameData"]["creatorID"] == 42
            assert lobby["gameData"]["progress"] == {"completed": 0, "total": 6}
            websocket.send_json({"type": "start_game"})
            warning = websocket.receive_json()
            assert warning["type"] == "system"
            assert "Two players" in warning["message"]

        client.portal.call(session_manager.remove_session, session_id)


def test_single_player_tutorial_creation_does_not_generate_minigame_round():
    client, _testing_session = make_client()
    payload = creation_payload("SinglePlayer")
    payload["config"]["gameType"] = "Tutorial"
    payload["config"]["commands"] = {}
    with client:
        response = client.post("/api/session_create", json=payload)
        assert response.status_code == 201
        session_id = str(response.json()["session_id"])
        runtime = session_manager.get_session(session_id)
        assert runtime.state == "running"
        assert runtime.game_manager.questions == []
        client.portal.call(session_manager.remove_session, session_id)


def test_selected_sed_configuration_generates_sed_questions():
    client, _testing_session = make_client()
    payload = creation_payload("SinglePlayer")
    payload["config"]["commands"] = {
        "grep": {"selected": False, "options": []},
        "sed": {"selected": True, "options": ["Save a backup", "Case Insensitive"]},
    }
    payload["config"]["options"]["questionCount"] = 3

    with client:
        response = client.post("/api/session_create", json=payload)
        assert response.status_code == 201
        runtime = session_manager.get_session(str(response.json()["session_id"]))
        assert runtime != "404"
        assert len(runtime.game_manager.questions) == 3
        assert {question["command"] for question in runtime.game_manager.questions} == {
            "sed"
        }
        assert {question["mode"] for question in runtime.game_manager.questions} == {
            "basic",
            "backup",
            "ignore_case",
        }
        assert runtime.game_manager.get_shell()["cmds"] == ["sed"]

        client.portal.call(
            session_manager.remove_session, str(response.json()["session_id"])
        )


def test_selected_commands_share_configured_question_count():
    client, _testing_session = make_client()
    payload = creation_payload("SinglePlayer")
    payload["config"]["commands"]["sed"] = {
        "selected": True,
        "options": ["Save a backup"],
    }
    payload["config"]["options"]["questionCount"] = 5

    with client:
        response = client.post("/api/session_create", json=payload)
        assert response.status_code == 201
        runtime = session_manager.get_session(str(response.json()["session_id"]))
        assert runtime != "404"
        questions = runtime.game_manager.questions
        assert len(questions) == 5
        assert sum(question["command"] == "grep" for question in questions) == 3
        assert sum(question["command"] == "sed" for question in questions) == 2
        assert runtime.game_manager.get_shell()["cmds"] == ["grep", "sed"]
        client.portal.call(
            session_manager.remove_session, str(response.json()["session_id"])
        )


def test_round_planner_rotates_commands_and_replays_seeded_sessions():
    config = {
        "name": "Varied session", "gameType": "MiniGames",
        "commands": {
            command: {"selected": True, "options": []}
            for command in ("ls", "cat", "wc", "grep", "sed")
        },
        "options": {"rounds": 3, "questionCount": 2, "seed": 1107},
    }

    def play_rounds():
        manager = GameManager()
        manager.set_config(config)
        rounds = []
        for _ in range(3):
            manager.start_round(["1"])
            rounds.append(list(manager.questions))
        return rounds

    first = play_rounds()
    assert first == play_rounds()
    assert {question["command"] for round_questions in first
            for question in round_questions} == set(config["commands"])
    assert all("solution" not in question for round_questions in first
               for question in round_questions)


def test_session_allows_fewer_questions_than_selected_commands():
    client, _testing_session = make_client()
    payload = creation_payload("SinglePlayer")
    payload["config"]["commands"] = {
        command: {"selected": True, "options": []}
        for command in ("ls", "cat", "wc", "grep", "sed")
    }
    payload["config"]["options"].update({
        "rounds": 3, "questionCount": 2, "seed": 1107,
    })

    with client:
        response = client.post("/api/session_create", json=payload)
        assert response.status_code == 201
        session_id = str(response.json()["session_id"])
        runtime = session_manager.get_session(session_id)
        assert len(runtime.game_manager.questions) == 2
        client.portal.call(session_manager.remove_session, session_id)


def test_new_commands_generate_a_mixed_round_and_score_over_websocket():
    client, _testing_session = make_client()
    payload = creation_payload("SinglePlayer")
    options_by_command = {
        "grep": ["Case Insensitive"], "sed": ["Save a backup"],
        "ls": ["Show Hidden"], "cat": ["Number Lines"],
        "wc": ["Count Bytes"],
    }
    payload["config"]["commands"] = {
        command: {"selected": True, "options": options}
        for command, options in options_by_command.items()
    }
    payload["config"]["options"].update({"rounds": 1, "questionCount": 5})

    with client:
        response = client.post("/api/session_create", json=payload)
        assert response.status_code == 201
        session_id = str(response.json()["session_id"])
        runtime = session_manager.get_session(session_id)
        assert {q["command"] for q in runtime.game_manager.questions} == set(
            payload["config"]["commands"]
        )
        assert {q["command"]: q["mode"] for q in runtime.game_manager.questions} == {
            "grep": "ignore_case", "sed": "backup", "ls": "hidden",
            "cat": "numbered", "wc": "bytes",
        }
        question = next(
            q for q in runtime.game_manager.questions if q["command"] == "wc"
        )
        solution = runtime.game_manager._challenge_engine.challenges[
            question["id"]
        ].goal.solution

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.send_json({
                "token": create_access_token({"sub": 42, "username": "creator"}),
            })
            websocket.receive_json()
            lobby = websocket.receive_json()
            assert lobby["state"] == "running"
            websocket.send_json({"type": "command", "input": solution})
            output = websocket.receive_json()
            assert output["type"] == "command_output"
            assert output["status"] == 0
            update = websocket.receive_json()
            assert update["gameData"]["progress"] == {"completed": 1, "total": 5}

        client.portal.call(session_manager.remove_session, session_id)


def test_minigames_rejects_commands_without_questions():
    client, _testing_session = make_client()
    payload = creation_payload("SinglePlayer")
    payload["config"]["commands"] = {
        "unknown": {"selected": True, "options": []},
    }
    with client:
        response = client.post("/api/session_create", json=payload)
        assert response.status_code == 422
        assert "no MiniGames questions" in response.json()["detail"]


def test_question_count_can_be_less_than_selected_commands():
    client, _testing_session = make_client()
    payload = creation_payload("SinglePlayer")
    payload["config"]["commands"]["sed"]["selected"] = True
    payload["config"]["options"]["questionCount"] = 1
    with client:
        response = client.post("/api/session_create", json=payload)
        assert response.status_code == 201
        session_id = str(response.json()["session_id"])
        runtime = session_manager.get_session(session_id)
        assert len(runtime.game_manager.questions) == 1
        client.portal.call(session_manager.remove_session, session_id)


def test_sandbox_is_marked_and_excluded_from_active_sessions():
    client, testing_session = make_client()

    with client:
        response = client.post("/api/sandbox/42")
        assert response.status_code == 200
        sandbox_id = str(response.json()["session_id"])
        sandbox = session_manager.get_session(sandbox_id)
        assert sandbox.is_sandbox is True
        assert sandbox.game_manager.game_type == "Tutorial"
        db = testing_session()
        assert db.get(GameSession, int(sandbox_id)) is not None
        assert db.query(ScenarioToSession).filter_by(sessionID=int(sandbox_id)).count() == 1
        assert db.query(SessionShell).filter_by(SessionID=int(sandbox_id)).count() == 1
        db.close()

        game_data = client.get(f"/api/session/{sandbox_id}").json()["gameData"]
        assert game_data["isSandbox"] is True
        assert sandbox.lobby_state("42")["gameData"]["isSandbox"] is True
        assert sandbox_id not in {
            item["id"] for item in client.get("/api/sessions").json()["sessions"]
        }

        client.portal.call(session_manager.remove_session, sandbox_id)
        with client.websocket_connect(f"/ws/{sandbox_id}") as websocket:
            websocket.send_json(
                {
                    "username": "creator",
                    "userID": "42",
                    "token": create_access_token({"sub": 42, "username": "creator"}),
                }
            )
            websocket.receive_json()
            assert session_manager.get_session(sandbox_id).is_sandbox is True
            assert sandbox_id not in {
                item["id"] for item in client.get("/api/sessions").json()["sessions"]
            }

        client.portal.call(session_manager.remove_session, sandbox_id)
        payload = creation_payload("Versus")
        payload["config"]["name"] = "Sandbox"
        normal_id = str(
            client.post("/api/session_create", json=payload).json()["session_id"]
        )
        assert normal_id in {
            item["id"] for item in client.get("/api/sessions").json()["sessions"]
        }
        client.portal.call(session_manager.remove_session, normal_id)
        reopened = client.post("/api/sandbox/42")
        assert str(reopened.json()["session_id"]) == sandbox_id
        assert session_manager.get_session(sandbox_id).is_sandbox is True
        assert sandbox_id not in {
            item["id"] for item in client.get("/api/sessions").json()["sessions"]
        }

        client.portal.call(session_manager.remove_session, sandbox_id)


def test_saved_sessions_remain_browsable_with_member_and_public_scope():
    client, _testing_session = make_client()
    with client:
        versus_id = str(
            client.post("/api/session_create", json=creation_payload("Versus"))
            .json()["session_id"]
        )
        solo_id = str(
            client.post("/api/session_create", json=creation_payload("SinglePlayer"))
            .json()["session_id"]
        )
        private_payload = creation_payload("Versus")
        private_payload["config"]["visibility"] = "private"
        private_id = str(
            client.post("/api/session_create", json=private_payload)
            .json()["session_id"]
        )
        client.portal.call(session_manager.remove_session, versus_id)
        client.portal.call(session_manager.remove_session, solo_id)
        client.portal.call(session_manager.remove_session, private_id)

        own = {
            item["id"]: item for item in client.get("/api/sessions").json()["sessions"]
        }
        assert own[versus_id]["member"] is True
        assert own[solo_id]["member"] is True
        assert own[private_id]["member"] is True
        assert own[versus_id]["connected_players"] == 0
        assert own[versus_id]["joined_players"] == 1
        assert own[versus_id]["play_type"] == "Versus"

        guest = {
            item["id"]: item
            for item in client.get(
                "/api/sessions", headers=authorization(43, "guest")
            ).json()["sessions"]
        }
        assert guest[versus_id]["member"] is False
        assert solo_id not in guest
        assert private_id not in guest


def test_session_list_tracks_connected_and_joined_players_across_reconnects():
    client, _testing_session = make_client()
    with client:
        response = client.post("/api/session_create", json=creation_payload("Versus"))
        assert response.status_code == 201
        session_id = str(response.json()["session_id"])
        runtime = session_manager.get_session(session_id)
        creator_token = authorization(42, "creator")["Authorization"].split(" ", 1)[1]
        guest_token = authorization(43, "guest")["Authorization"].split(" ", 1)[1]

        def counts():
            entries = client.get("/api/sessions").json()["sessions"]
            entry = next(item for item in entries if item["id"] == session_id)
            return entry["connected_players"], entry["joined_players"]

        assert counts() == (0, 1)
        with client.websocket_connect(f"/ws/{session_id}") as creator:
            creator.send_json({"token": creator_token})
            creator.receive_json()
            creator.receive_json()
            assert counts() == (1, 1)

            with client.websocket_connect(f"/ws/{session_id}") as guest:
                guest.send_json({"token": guest_token})
                guest.receive_json()
                guest.receive_json()
                assert counts() == (2, 2)

            assert len(runtime.players) == 2  # retained for reconnect
            assert counts() == (1, 2)

        assert counts() == (0, 2)
        with client.websocket_connect(f"/ws/{session_id}") as guest:
            guest.send_json({"token": guest_token})
            guest.receive_json()
            guest.receive_json()
            assert counts() == (1, 2)

        assert counts() == (0, 2)
        client.portal.call(session_manager.remove_session, session_id)


def test_sandbox_reset_restores_fresh_live_and_saved_shell():
    client, testing_session = make_client()

    with client:
        sandbox_id = str(client.post("/api/sandbox/42").json()["session_id"])
        db = testing_session()
        try:
            original_shell = db.get(SessionShell, (int(sandbox_id), 42)).shell
        finally:
            db.close()

        with client.websocket_connect(f"/ws/{sandbox_id}") as websocket:
            websocket.send_json({
                "token": create_access_token({"sub": 42, "username": "creator"}),
            })
            websocket.receive_json()  # join notice
            websocket.receive_json()  # lobby state

            websocket.send_json({"type": "command", "input": "mkdir scratch"})
            assert websocket.receive_json()["status"] == 0
            websocket.send_json({"type": "command", "input": "cd scratch"})
            assert websocket.receive_json()["cwd"] == "/scratch"
            assert client.post(f"/api/sessions/{sandbox_id}/save").status_code == 200

            websocket.send_json({"type": "reset_sandbox"})
            assert websocket.receive_json() == {"type": "sandbox_reset", "cwd": "/"}
            websocket.send_json({"type": "command", "input": "ls /"})
            assert "scratch" not in websocket.receive_json()["stdout"]

            db = testing_session()
            try:
                assert db.get(SessionShell, (int(sandbox_id), 42)).shell == original_shell
            finally:
                db.close()

        client.portal.call(session_manager.remove_session, sandbox_id)
        with client.websocket_connect(f"/ws/{sandbox_id}") as websocket:
            websocket.send_json({
                "token": create_access_token({"sub": 42, "username": "creator"}),
            })
            websocket.receive_json()
            assert websocket.receive_json()["cwd"] == "/"
            websocket.send_json({"type": "command", "input": "ls /"})
            assert "scratch" not in websocket.receive_json()["stdout"]
        client.portal.call(session_manager.remove_session, sandbox_id)


def assert_no_sandbox_state(testing_session, original_runtimes):
    db = testing_session()
    try:
        assert db.query(GameSession).count() == 0
        assert db.query(ScenarioToSession).count() == 0
        assert db.query(SessionShell).count() == 0
    finally:
        db.close()
    assert set(session_manager.sessions) == original_runtimes


def test_sandbox_missing_scenario_returns_error_without_partial_state():
    client, testing_session = make_client()
    db = testing_session()
    db.delete(db.query(Scenario).filter_by(name="Tutorial").one())
    db.commit()
    db.close()
    original_runtimes = set(session_manager.sessions)

    with client:
        response = client.post("/api/sandbox/42")
        assert response.status_code == 503
        assert response.json() == {
            "detail": "Sandbox is unavailable: Tutorial configuration is missing"
        }
        assert_no_sandbox_state(testing_session, original_runtimes)


@pytest.mark.parametrize("config", ["{bad json", {"name": "Tutorial", "options": {"rounds": "bad"}}])
def test_sandbox_malformed_scenario_returns_error_without_partial_state(config):
    client, testing_session = make_client()
    db = testing_session()
    db.query(Scenario).filter_by(name="Tutorial").one().config = config
    db.commit()
    db.close()
    original_runtimes = set(session_manager.sessions)

    with client:
        response = client.post("/api/sandbox/42")
        assert response.status_code == 503
        assert response.json() == {
            "detail": "Sandbox is unavailable: Tutorial configuration is invalid"
        }
        assert_no_sandbox_state(testing_session, original_runtimes)


def test_sandbox_storage_failure_rolls_back_database_and_runtime(monkeypatch):
    client, testing_session = make_client()
    original_runtimes = set(session_manager.sessions)

    with client:
        with monkeypatch.context() as patch:
            def fail_commit(_session):
                raise RuntimeError("Storage unavailable")

            patch.setattr(testing_session.class_, "commit", fail_commit)
            response = client.post("/api/sandbox/42")

        assert response.status_code == 500
        assert response.json() == {
            "detail": "Could not create Sandbox. Please try again"
        }
        assert_no_sandbox_state(testing_session, original_runtimes)


def test_session_creation_uses_authenticated_creator_and_rejects_anonymous():
    client, testing_session = make_client()
    payload = creation_payload("Versus")
    payload["config"]["creatorID"] = 43
    with client:
        anonymous = client.post(
            "/api/session_create", json=payload, headers={"Authorization": ""}
        )
        assert anonymous.status_code in (401, 403)
        response = client.post("/api/session_create", json=payload)
        assert response.status_code == 201
        session_id = response.json()["session_id"]
        db = testing_session()
        saved = db.get(GameSession, session_id)
        assert saved.creatorID == 42
        assert db.query(ScenarioToSession).one().config["creatorID"] == 42
        db.close()
        client.portal.call(session_manager.remove_session, str(session_id))


def test_private_session_requires_request_and_host_approval():
    client, testing_session = make_client()
    payload = creation_payload("Versus")
    payload["config"]["visibility"] = "private"
    with client:
        response = client.post("/api/session_create", json=payload)
        assert response.status_code == 201
        session_id = response.json()["session_id"]
        guest_headers = authorization(43, "guest")
        assert (
            client.get(f"/api/session/{session_id}", headers=guest_headers).status_code
            == 403
        )
        assert client.get("/api/shells", headers=guest_headers).json() == {"shells": []}
        assert (
            client.get(
                f"/api/db/session/{session_id}", headers=guest_headers
            ).status_code
            == 403
        )
        assert (
            client.get(
                f"/api/session/{session_id}/diagnostics", headers=guest_headers
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/sessions/{session_id}/save", headers=guest_headers
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/sessions/{session_id}/state",
                json={"state": "running"},
                headers=guest_headers,
            ).status_code
            == 403
        )
        with client.websocket_connect(f"/ws/{session_id}") as ws:
            ws.send_json({"token": guest_headers["Authorization"].split(" ", 1)[1]})
            try:
                ws.receive_json()
            except WebSocketDisconnect as error:
                assert error.code == 4403
            else:
                raise AssertionError("Unapproved guest entered private session")

        request = client.post(
            f"/api/session/{session_id}/requests", headers=guest_headers
        )
        assert request.status_code == 201
        assert request.json()["status"] == "pending"
        assert (
            client.post(
                f"/api/session/{session_id}/requests/43/accept", headers=guest_headers
            ).status_code
            == 403
        )
        assert client.get(f"/api/session/{session_id}/requests").json()["requests"] == [
            {"user_id": 43, "username": "guest"}
        ]
        assert (
            client.post(f"/api/session/{session_id}/requests/43/accept").status_code
            == 200
        )
        assert (
            client.get(f"/api/session/{session_id}", headers=guest_headers).status_code
            == 200
        )
        guest_debug = client.get(
            f"/api/db/session/{session_id}", headers=guest_headers
        ).json()
        assert [player["userID"] for player in guest_debug["players"]] == [43]
        with client.websocket_connect(f"/ws/{session_id}") as ws:
            ws.send_json({"token": guest_headers["Authorization"].split(" ", 1)[1]})
            ws.receive_json()
            lobby = ws.receive_json()
            assert lobby["gameData"]["creatorID"] == 42
        db = testing_session()
        assert db.get(SessionShell, (session_id, 43)) is not None
        db.close()
        client.portal.call(session_manager.remove_session, str(session_id))


def test_public_versus_allows_authenticated_guest_and_hides_solo_session():
    client, testing_session = make_client()
    with client:
        public = client.post("/api/session_create", json=creation_payload("Versus"))
        solo = client.post("/api/session_create", json=creation_payload("SinglePlayer"))
        public_id = public.json()["session_id"]
        solo_id = solo.json()["session_id"]
        guest_headers = authorization(43, "guest")
        visible = client.get("/api/sessions", headers=guest_headers).json()["sessions"]
        assert {entry["id"] for entry in visible} == {str(public_id)}
        guest_token = guest_headers["Authorization"].split(" ", 1)[1]
        with client.websocket_connect(f"/ws/{public_id}") as ws:
            ws.send_json({"token": guest_token})
            ws.receive_json()
            assert ws.receive_json()["type"] == "lobby_update"
        db = testing_session()
        assert db.get(SessionShell, (public_id, 43)) is not None
        db.close()
        client.portal.call(session_manager.remove_session, str(public_id))
        client.portal.call(session_manager.remove_session, str(solo_id))


@pytest.mark.parametrize("play_type", ["SinglePlayer", "Versus"])
def test_same_user_cannot_join_one_session_from_two_tabs(play_type):
    client, _testing_session = make_client()
    with client:
        response = client.post("/api/session_create", json=creation_payload(play_type))
        assert response.status_code == 201
        session_id = str(response.json()["session_id"])
        runtime = session_manager.get_session(session_id)
        token = authorization(42, "creator")["Authorization"].split(" ", 1)[1]

        with client.websocket_connect(f"/ws/{session_id}") as first:
            first.send_json({"token": token})
            assert first.receive_json() == {
                "type": "system", "message": "creator joined session"
            }
            assert first.receive_json()["players"] == ["creator"]
            player = runtime.players["creator"]

            with client.websocket_connect(f"/ws/{session_id}") as second:
                second.send_json({"token": token})
                with pytest.raises(WebSocketDisconnect) as rejected:
                    second.receive_json()
                assert rejected.value.code == 4409

            assert runtime.connected_players() == [player]
            first.send_json({"type": "chat", "message": "first tab still works"})
            assert first.receive_json() == {
                "type": "chat", "user": "creator", "message": "first tab still works"
            }
            first.send_json({"type": "command", "input": "echo first-tab-command"})
            output = first.receive_json()
            assert output["type"] == "command_output"
            assert output["stdout"] == ["first-tab-command"]

        assert runtime.connected_players() == []
        with client.websocket_connect(f"/ws/{session_id}") as rejoined:
            rejoined.send_json({"token": token})
            assert rejoined.receive_json()["message"] == "creator joined session"
            assert rejoined.receive_json()["players"] == ["creator"]
            assert runtime.players["creator"] is player

        client.portal.call(session_manager.remove_session, session_id)


def test_reused_username_cannot_inherit_another_players_runtime_shell():
    client, testing_session = make_client()
    with client:
        response = client.post("/api/session_create", json=creation_payload("Versus"))
        session_id = response.json()["session_id"]
        with client.websocket_connect(f"/ws/{session_id}") as host:
            host.send_json(
                {
                    "token": authorization(42, "creator")["Authorization"].split(
                        " ", 1
                    )[1]
                }
            )
            host.receive_json()
            host.receive_json()

        db = testing_session()
        db.get(User, 42).username = "renamed-creator"
        db.get(User, 43).username = "creator"
        db.commit()
        db.close()

        with client.websocket_connect(f"/ws/{session_id}") as guest:
            guest.send_json(
                {
                    "token": authorization(43, "creator")["Authorization"].split(
                        " ", 1
                    )[1]
                }
            )
            try:
                guest.receive_json()
            except WebSocketDisconnect as error:
                assert error.code == 4403
            else:
                raise AssertionError("Guest inherited the host's runtime player")
        runtime = session_manager.get_session(str(session_id))
        assert runtime.players["creator"].user_id == "42"

        with client.websocket_connect(f"/ws/{session_id}") as host:
            host.send_json(
                {
                    "token": authorization(42, "renamed-creator")[
                        "Authorization"
                    ].split(" ", 1)[1]
                }
            )
            host.receive_json()
            assert host.receive_json()["type"] == "lobby_update"
            assert len(runtime.players) == 1
        client.portal.call(session_manager.remove_session, str(session_id))


def test_friends_only_revocation_closes_socket_and_blocks_saved_state():
    client, testing_session = make_client()
    payload = creation_payload("Versus")
    payload["config"]["visibility"] = "friends_only"
    with client:
        session_id = client.post("/api/session_create", json=payload).json()[
            "session_id"
        ]
        db = testing_session()
        db.add(Friendship(requester_id=42, recipient_id=43, status="accepted"))
        db.commit()
        db.close()
        guest_headers = authorization(43, "guest")
        with client.websocket_connect(f"/ws/{session_id}") as guest:
            guest.send_json({"token": guest_headers["Authorization"].split(" ", 1)[1]})
            guest.receive_json()
            guest.receive_json()
            assert client.delete("/users/me/friends/43").status_code == 200
            try:
                guest.receive_json()
            except WebSocketDisconnect as error:
                assert error.code == 4403
            else:
                raise AssertionError("Former friend kept a live connection")

        db = testing_session()
        assert db.get(SessionShell, (session_id, 43)) is None
        db.close()
        assert "guest" not in session_manager.get_session(str(session_id)).players

        assert (
            client.get(f"/api/session/{session_id}", headers=guest_headers).status_code
            == 403
        )
        assert (
            client.get(
                f"/api/db/session/{session_id}", headers=guest_headers
            ).status_code
            == 403
        )
        assert (
            client.get(
                f"/api/session/{session_id}/diagnostics", headers=guest_headers
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/sessions/{session_id}/save", headers=guest_headers
            ).status_code
            == 403
        )
        assert client.get("/api/shells", headers=guest_headers).json() == {"shells": []}
        assert str(session_id) not in {
            item["id"]
            for item in client.get("/api/sessions", headers=guest_headers).json()[
                "sessions"
            ]
        }
        client.portal.call(session_manager.remove_session, str(session_id))


def test_friends_only_requires_accepted_friendship_and_single_player_stays_solo():
    client, testing_session = make_client()
    payload = creation_payload("Versus")
    payload["config"]["visibility"] = "friends_only"
    with client:
        response = client.post("/api/session_create", json=payload)
        assert response.status_code == 201
        session_id = response.json()["session_id"]
        guest_token = authorization(43, "guest")["Authorization"].split(" ", 1)[1]
        with client.websocket_connect(f"/ws/{session_id}") as ws:
            ws.send_json({"token": guest_token})
            try:
                ws.receive_json()
            except WebSocketDisconnect as error:
                assert error.code == 4403
            else:
                raise AssertionError("Nonfriend entered friends-only session")
        db = testing_session()
        friendship = Friendship(requester_id=42, recipient_id=43, status="accepted")
        db.add(friendship)
        db.commit()
        with client.websocket_connect(f"/ws/{session_id}") as ws:
            ws.send_json({"token": guest_token})
            ws.receive_json()
            assert ws.receive_json()["type"] == "lobby_update"
        db.delete(friendship)
        db.commit()
        db.close()
        with client.websocket_connect(f"/ws/{session_id}") as ws:
            ws.send_json({"token": guest_token})
            try:
                ws.receive_json()
            except WebSocketDisconnect as error:
                assert error.code == 4403
            else:
                raise AssertionError("Former friend reentered friends-only session")
        client.portal.call(session_manager.remove_session, str(session_id))

        solo = client.post("/api/session_create", json=creation_payload("SinglePlayer"))
        solo_id = solo.json()["session_id"]
        with client.websocket_connect(f"/ws/{solo_id}") as ws:
            ws.send_json({"token": guest_token})
            try:
                ws.receive_json()
            except WebSocketDisconnect as error:
                assert error.code == 4403
            else:
                raise AssertionError("Guest entered single-player session")
        client.portal.call(session_manager.remove_session, str(solo_id))


def _next_lobby_state(websocket, expected_state):
    for _ in range(6):
        message = websocket.receive_json()
        if (
            message.get("type") == "lobby_update"
            and message.get("state") == expected_state
        ):
            return message
    raise AssertionError(f"No {expected_state} lobby update received")


def test_host_state_api_rejects_invalid_and_premature_transitions():
    client, testing_session = make_client()
    payload = creation_payload("Versus")
    payload["config"]["options"]["rounds"] = 1
    with client:
        response = client.post("/api/session_create", json=payload)
        assert response.status_code == 201
        session_id = response.json()["session_id"]
        state_path = f"/api/sessions/{session_id}/state"
        runtime = session_manager.get_session(str(session_id))

        assert client.post(state_path, json={"state": "broken"}).status_code == 422
        assert client.post(state_path, json={"state": "finished"}).status_code == 409
        assert client.post(state_path, json={"state": "running"}).status_code == 409
        assert runtime.state == "waiting"
        assert runtime.game_manager.round_number == 0

        creator_token = authorization(42, "creator")["Authorization"].split()[1]
        guest_token = authorization(43, "guest")["Authorization"].split()[1]
        with client.websocket_connect(f"/ws/{session_id}") as host:
            host.send_json({"token": creator_token})
            _next_lobby_state(host, "waiting")
            with client.websocket_connect(f"/ws/{session_id}") as guest:
                guest.send_json({"token": guest_token})
                _next_lobby_state(guest, "waiting")
                started = client.post(state_path, json={"state": "running"})
                assert started.status_code == 200
                lobby = _next_lobby_state(host, "running")
                assert lobby["gameData"]["round"] == 1
                assert runtime.game_manager.round_number == 1
                assert runtime.game_manager.questions
                db = testing_session()
                assert db.get(GameSession, session_id).state == "running"
                db.close()

                assert (
                    client.post(state_path, json={"state": "running"}).status_code
                    == 409
                )
                assert (
                    client.post(state_path, json={"state": "finished"}).status_code
                    == 409
                )
                assert runtime.state == "running"
                assert runtime.game_manager.finished is False

                question_ids = {item["id"] for item in runtime.game_manager.questions}
                runtime.game_manager._completed = {
                    "42": question_ids.copy(), "43": question_ids.copy()
                }
                finished = client.post(state_path, json={"state": "finished"})
                assert finished.status_code == 200
                assert _next_lobby_state(host, "finished")["gameData"]["finished"]
                assert runtime.state == "finished"
                assert runtime.game_manager.finished is True
                db = testing_session()
                assert db.get(GameSession, session_id).state == "finished"
                db.close()
                assert (
                    client.post(state_path, json={"state": "running"}).status_code
                    == 409
                )

        client.portal.call(session_manager.remove_session, str(session_id))


def test_websocket_start_uses_same_transition_and_persists_state():
    client, testing_session = make_client()
    with client:
        response = client.post("/api/session_create", json=creation_payload("Versus"))
        session_id = response.json()["session_id"]
        creator_token = authorization(42, "creator")["Authorization"].split()[1]
        guest_token = authorization(43, "guest")["Authorization"].split()[1]
        with client.websocket_connect(f"/ws/{session_id}") as host:
            host.send_json({"token": creator_token})
            _next_lobby_state(host, "waiting")
            with client.websocket_connect(f"/ws/{session_id}") as guest:
                guest.send_json({"token": guest_token})
                _next_lobby_state(guest, "waiting")
                host.send_json({"type": "start_game"})
                lobby = _next_lobby_state(host, "running")
                assert lobby["gameData"]["round"] == 1
                runtime = session_manager.get_session(str(session_id))
                assert runtime.game_manager.round_number == 1
                db = testing_session()
                assert db.get(GameSession, session_id).state == "running"
                db.close()
        client.portal.call(session_manager.remove_session, str(session_id))


def test_failed_state_commit_restores_runtime_round_and_player_shells():
    runtime = RuntimeGameSession("rollback")
    runtime.game_manager.set_config(creation_payload("Versus")["config"])
    for name, user_id in (("creator", "42"), ("guest", "43")):
        socket = object()
        runtime.players[name] = Player(socket, name, user_id)
        runtime.connections[socket] = name
    original_shells = {
        name: player.serialize() for name, player in runtime.players.items()
    }
    saved = SimpleNamespace(state="waiting")

    class FailingDatabase:
        rolled_back = False

        def commit(self):
            raise RuntimeError("database unavailable")

        def rollback(self):
            self.rolled_back = True

    db = FailingDatabase()
    with pytest.raises(RuntimeError, match="database unavailable"):
        asyncio.run(transition_and_persist(db, saved, runtime, "running"))

    assert db.rolled_back
    assert saved.state == "waiting"
    assert runtime.state == "waiting"
    assert runtime.game_manager.round_number == 0
    assert runtime.game_manager.questions == []
    restored_shells = {
        name: player.serialize() for name, player in runtime.players.items()
    }
    assert restored_shells == original_shells
