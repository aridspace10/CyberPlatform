from api.sessions import router
from db.modals import Base, Scenario, ScenarioToSession, SessionShell, User
from db.session import get_db
from fastapi import FastAPI
from fastapi.testclient import TestClient
from network.SessionManger import session_manager
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
