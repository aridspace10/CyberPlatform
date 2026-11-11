from api.sessions import router
from db.authentication import create_access_token
from db.modals import Base, Scenario, ScenarioToSession, SessionShell, User
from db.session import get_db
from fastapi import FastAPI
from fastapi.testclient import TestClient
from network.SessionManger import session_manager
from network.WebsocketServer import router as websocket_router
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


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
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session


def creation_payload(play_type: str) -> dict:
    return {
        "config": {
            "name": f"{play_type} session",
            "playType": play_type,
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
        old_prompts = [question["prompt"] for question in original.game_manager.questions]
        client.portal.call(session_manager.remove_session, session_id)

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.send_json({
                "userID": "999",
                "username": "forged",
                "token": create_access_token({"sub": 42, "username": "creator"}),
            })
            websocket.receive_json()
            lobby = websocket.receive_json()
            assert lobby["state"] == "running"
            assert lobby["players"] == ["creator"]
            assert lobby["gameData"]["creatorID"] == 42
            assert len(lobby["gameData"]["questions"]) == 6
            assert [q["prompt"] for q in lobby["gameData"]["questions"]] != old_prompts
            assert session_manager.get_session(session_id).players["creator"].user_id == "42"

            prompt = next(
                q["prompt"] for q in lobby["gameData"]["questions"]
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
        assert saved.shell["fs"] == session_manager.get_session(session_id).game_manager.get_shell()["fs"]
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
            websocket.send_json({
                "token": create_access_token({"sub": 42, "username": "creator"}),
            })
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
        assert {
            question["command"] for question in runtime.game_manager.questions
        } == {"sed"}
        assert {question["mode"] for question in runtime.game_manager.questions} == {
            "basic", "backup", "ignore_case"
        }
        assert runtime.game_manager.get_shell()["cmds"] == ["sed"]

        client.portal.call(
            session_manager.remove_session, str(response.json()["session_id"])
        )


def test_selected_commands_share_configured_question_count():
    client, _testing_session = make_client()
    payload = creation_payload("SinglePlayer")
    payload["config"]["commands"]["sed"] = {
        "selected": True, "options": ["Save a backup"],
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


def test_question_count_must_cover_selected_commands():
    client, _testing_session = make_client()
    payload = creation_payload("SinglePlayer")
    payload["config"]["commands"]["sed"]["selected"] = True
    payload["config"]["options"]["questionCount"] = 1
    with client:
        response = client.post("/api/session_create", json=payload)
        assert response.status_code == 422
        assert "each selected command" in response.json()["detail"]


def test_sandbox_is_marked_and_excluded_from_active_sessions():
    client, _testing_session = make_client()

    with client:
        response = client.post("/api/sandbox/42")
        assert response.status_code == 200
        sandbox_id = str(response.json()["session_id"])
        sandbox = session_manager.get_session(sandbox_id)
        assert sandbox.is_sandbox is True
        assert sandbox.game_manager.game_type == "Tutorial"

        game_data = client.get(f"/api/session/{sandbox_id}").json()["gameData"]
        assert game_data["isSandbox"] is True
        assert sandbox.lobby_state("42")["gameData"]["isSandbox"] is True
        assert sandbox_id not in {
            item["id"] for item in client.get("/api/sessions").json()["sessions"]
        }

        client.portal.call(session_manager.remove_session, sandbox_id)
        with client.websocket_connect(f"/ws/{sandbox_id}") as websocket:
            websocket.send_json({
                "username": "creator",
                "userID": "42",
                "token": create_access_token({"sub": 42, "username": "creator"}),
            })
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
