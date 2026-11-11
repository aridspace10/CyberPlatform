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
from network.SessionManger import session_manager
from network.WebsocketServer import router as websocket_router
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
    app.dependency_overrides[get_db] = override_get_db
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
