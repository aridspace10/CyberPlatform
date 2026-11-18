from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from db.authentication import create_access_token
from db.modals import Base, Friendship, User
from db.session import migrate_friendships
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.users import get_db, router
from services.user_service import is_friend
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def make_client(engine=None):
    if engine is None:
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
            == 409
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
        assert (
            client.post(
                "/users/me/friend-requests", json={"user_id": 2}, headers=auth(1)
            ).status_code
            == 409
        )


def test_search_and_friend_request_limits_and_legacy_user_routes():
    client, _ = make_client()
    with client:
        assert client.get("/users/").status_code == 410
        assert client.get("/users/2").status_code == 410
        assert client.get("/users/search?query=%25", headers=auth(1)).status_code == 400
        assert client.get("/users/search?query=%25%25", headers=auth(1)).json() == []
        for _ in range(28):
            assert (
                client.get("/users/search?query=bo", headers=auth(1)).status_code == 200
            )
        limited = client.get("/users/search?query=bo", headers=auth(1))
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) > 0

        assert (
            client.post(
                "/users/me/friend-requests", json={"user_id": 2}, headers=auth(1)
            ).status_code
            == 201
        )
        for _ in range(9):
            assert (
                client.post(
                    "/users/me/friend-requests", json={"user_id": 2}, headers=auth(1)
                ).status_code
                == 409
            )
        limited = client.post(
            "/users/me/friend-requests", json={"user_id": 2}, headers=auth(1)
        )
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) > 0


def test_block_removes_pending_request_and_rejects_direct_api_calls():
    client, _ = make_client()
    with client:
        sent = client.post(
            "/users/me/friend-requests", json={"user_id": 2}, headers=auth(1)
        )
        assert sent.status_code == 201
        request_id = sent.json()["id"]
        assert (
            client.post(
                "/users/me/blocks", json={"user_id": 1}, headers=auth(2)
            ).status_code
            == 200
        )
        assert (
            client.get("/users/me/friend-requests", headers=auth(2)).json()["incoming"]
            == []
        )
        assert (
            client.post(
                f"/users/me/friend-requests/{request_id}/accept", headers=auth(2)
            ).status_code
            == 404
        )
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
        assert client.get("/users/search?query=al", headers=auth(2)).json() == []
        assert client.get("/users/me/blocks", headers=auth(2)).json() == [
            {"id": 1, "username": "Alice"}
        ]
        assert client.delete("/users/me/blocks/1", headers=auth(2)).status_code == 200
        assert client.get("/users/me/blocks", headers=auth(2)).json() == []


def test_decline_cooldown_expires_and_block_removes_accepted_friend():
    client, factory = make_client()
    with client:
        sent = client.post(
            "/users/me/friend-requests", json={"user_id": 2}, headers=auth(1)
        )
        request_id = sent.json()["id"]
        assert (
            client.delete(
                f"/users/me/friend-requests/{request_id}", headers=auth(2)
            ).status_code
            == 200
        )
        with factory() as db:
            request = db.get(Friendship, request_id)
            request.declined_at = datetime.now(timezone.utc).replace(
                tzinfo=None
            ) - timedelta(hours=25)
            db.commit()
        assert (
            client.post(
                "/users/me/friend-requests", json={"user_id": 2}, headers=auth(1)
            ).status_code
            == 201
        )
        assert (
            client.post(
                f"/users/me/friend-requests/{request_id}/accept", headers=auth(2)
            ).status_code
            == 200
        )
        assert client.get("/users/me/friends", headers=auth(1)).json() == [
            {"id": 2, "username": "Bob"}
        ]
        assert (
            client.post(
                "/users/me/blocks", json={"user_id": 1}, headers=auth(2)
            ).status_code
            == 200
        )
        assert client.get("/users/me/friends", headers=auth(1)).json() == []


def test_friendship_pair_is_unique_in_either_direction():
    _, factory = make_client()
    with factory() as db:
        db.add(Friendship(requester_id=1, recipient_id=2))
        db.commit()
        db.add(Friendship(requester_id=2, recipient_id=1))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_opposite_direction_requests_concurrently_create_one_relationship(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'race.db'}",
        connect_args={"check_same_thread": False},
    )
    client, factory = make_client(engine)
    start = Barrier(2)

    def send(sender, recipient):
        start.wait()
        return client.post(
            "/users/me/friend-requests",
            json={"user_id": recipient},
            headers=auth(sender),
        ).status_code

    with client, ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(send, 1, 2)
        second = pool.submit(send, 2, 1)
        assert sorted((first.result(), second.result())) == [201, 409]
        with factory() as db:
            assert db.query(Friendship).count() == 1


def test_legacy_friendships_migrate_to_one_row_per_pair(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as db:
        db.execute(
            text(
                "CREATE TABLE friendships (id INTEGER PRIMARY KEY, "
                "requester_id INTEGER, recipient_id INTEGER, status VARCHAR)"
            )
        )
        db.execute(
            text(
                "INSERT INTO friendships VALUES (1, 1, 2, 'pending'), "
                "(2, 2, 1, 'accepted')"
            )
        )
    migrate_friendships(engine)
    migrate_friendships(engine)
    with engine.connect() as db:
        rows = db.execute(text("SELECT id, status, pair_key FROM friendships")).all()
    assert rows == [(2, "accepted", "1:2")]


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
