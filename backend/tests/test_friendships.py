from db.authentication import create_access_token
from db.modals import Base, User
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.users import get_db, router
from services.user_service import is_friend
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def make_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with factory() as db:
        db.add_all(
            [
                User(
                    id=1, username="Alice", email="alice@example.com", password="secret"
                ),
                User(id=2, username="Bob", email="bob@example.com", password="secret"),
                User(
                    id=3, username="Carol", email="carol@example.com", password="secret"
                ),
            ]
        )
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_db
    return TestClient(app), factory


def auth(user_id):
    return {"Authorization": f"Bearer {create_access_token({'sub': user_id})}"}


def test_friend_request_lifecycle_and_public_responses():
    client, factory = make_client()
    with client:
        assert client.get("/users/search?query=bo").status_code == 401
        assert client.get("/users/search?query=bo", headers=auth(1)).json() == [
            {"id": 2, "username": "Bob"}
        ]
        assert client.get("/users/search?query=al", headers=auth(1)).json() == []

        sent = client.post(
            "/users/me/friend-requests", json={"user_id": 2}, headers=auth(1)
        )
        assert sent.status_code == 201
        request_id = sent.json()["id"]
        assert sent.json() == {
            "id": request_id,
            "user": {"id": 2, "username": "Bob"},
            "status": "pending",
        }
        assert client.get("/users/me/friend-requests", headers=auth(2)).json() == {
            "incoming": [{"id": request_id, "user": {"id": 1, "username": "Alice"}}],
            "outgoing": [],
        }
        with factory() as db:
            assert not is_friend(db, 1, 2)

        assert (
            client.post(
                f"/users/me/friend-requests/{request_id}/accept", headers=auth(3)
            ).status_code
            == 403
        )
        accepted = client.post(
            f"/users/me/friend-requests/{request_id}/accept", headers=auth(2)
        )
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "accepted"
        assert client.get("/users/me/friends", headers=auth(1)).json() == [
            {"id": 2, "username": "Bob"}
        ]
        assert client.get("/users/me/friends", headers=auth(2)).json() == [
            {"id": 1, "username": "Alice"}
        ]
        with factory() as db:
            assert is_friend(db, 1, 2)
            assert is_friend(db, 2, 1)
            assert not is_friend(db, 1, 3)

        assert client.delete("/users/me/friends/2", headers=auth(3)).status_code == 404
        assert client.delete("/users/me/friends/2", headers=auth(1)).status_code == 200
        assert client.get("/users/me/friends", headers=auth(2)).json() == []


def test_friend_request_conflicts_and_recipient_can_decline():
    client, _ = make_client()
    with client:
        assert (
            client.post(
                "/users/me/friend-requests", json={"user_id": 1}, headers=auth(1)
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/users/me/friend-requests", json={"user_id": 999}, headers=auth(1)
            ).status_code
            == 404
        )
        first = client.post(
            "/users/me/friend-requests", json={"user_id": 2}, headers=auth(1)
        )
        request_id = first.json()["id"]
        assert (
            client.post(
                "/users/me/friend-requests", json={"user_id": 2}, headers=auth(1)
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/users/me/friend-requests", json={"user_id": 1}, headers=auth(2)
            ).status_code
            == 409
        )
        assert (
            client.delete(
                f"/users/me/friend-requests/{request_id}", headers=auth(3)
            ).status_code
            == 403
        )
        assert (
            client.delete(
                f"/users/me/friend-requests/{request_id}", headers=auth(2)
            ).status_code
            == 200
        )
        assert client.get("/users/me/friend-requests", headers=auth(1)).json() == {
            "incoming": [],
            "outgoing": [],
        }


def test_account_mutations_require_the_account_owner():
    client, factory = make_client()
    with client:
        update = "/users/2?username=stolen&email=stolen@example.com"
        assert client.put(update).status_code == 401
        assert client.put(update, headers=auth(1)).status_code == 403
        assert client.delete("/users/2").status_code == 401
        assert client.delete("/users/2", headers=auth(1)).status_code == 403
        assert (
            client.put(
                "/users/2?username=Alice&email=bob@example.com", headers=auth(2)
            ).status_code
            == 409
        )
        assert (
            client.put(
                "/users/2?username=Robert&email=bob@example.com", headers=auth(2)
            ).status_code
            == 200
        )
        with factory() as db:
            assert db.get(User, 2).username == "Robert"
