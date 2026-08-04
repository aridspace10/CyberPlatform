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
            "options": {"allowPipes": True, "rounds": 8},
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

        db = testing_session()
        scenario = db.query(ScenarioToSession).one()
        shell = db.query(SessionShell).one()
        assert scenario.config == creation_payload("Versus")["config"]
        assert shell.shell["cmds"] == ["grep"]
        db.close()

        client.portal.call(session_manager.remove_session, str(result["session_id"]))


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

        client.portal.call(session_manager.remove_session, str(result["session_id"]))
