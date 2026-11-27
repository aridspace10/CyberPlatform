import pytest
from db import seed
from db.authentication import create_access_token, hash_password, verify_password
from db.modals import Base, User
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import users
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

USERNAME_MESSAGE = "Username must be 4–32 characters with no spaces"
PASSWORD_MESSAGE = (
    "Password must be 8–100 characters with uppercase and lowercase letters, "
    "a number, and a symbol (no spaces)"
)


@pytest.fixture
def signup_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def get_test_db():
        with session_factory() as db:
            yield db

    app = FastAPI()
    app.include_router(users.router)
    app.dependency_overrides[users.get_db] = get_test_db
    with TestClient(app) as client:
        yield client, session_factory
    engine.dispose()


@pytest.mark.parametrize(
    ("changes", "field", "message"),
    [
        ({"email": "not-an-email"}, "email", "Email given is not valid"),
        ({"email": "user@"}, "email", "Email given is not valid"),
        ({"username": "   "}, "username", USERNAME_MESSAGE),
        ({"username": "abc"}, "username", USERNAME_MESSAGE),
        ({"username": "two names"}, "username", USERNAME_MESSAGE),
        ({"username": "x" * 33}, "username", USERNAME_MESSAGE),
        ({"password": "Short1!"}, "password", PASSWORD_MESSAGE),
        ({"password": "lowercase1!"}, "password", PASSWORD_MESSAGE),
        ({"password": "UPPERCASE1!"}, "password", PASSWORD_MESSAGE),
        ({"password": "NoNumber!"}, "password", PASSWORD_MESSAGE),
        ({"password": "NoSymbol1"}, "password", PASSWORD_MESSAGE),
        ({"password": "Has Space1!"}, "password", PASSWORD_MESSAGE),
        ({"password": "ValidPass1!" * 10}, "password", PASSWORD_MESSAGE),
    ],
)
def test_signup_rejects_invalid_fields(signup_client, changes, field, message):
    client, session_factory = signup_client
    payload = {
        "username": "validuser",
        "email": "valid@example.com",
        "password": "ValidPass1!",
        **changes,
    }

    response = client.post("/users/", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]
    assert response.json()["detail"][0]["msg"] == message
    with session_factory() as db:
        assert db.query(User).count() == 0


def test_signup_normalizes_names_and_email(signup_client):
    client, session_factory = signup_client
    response = client.post(
        "/users/",
        json={
            "username": "  ValidUser  ",
            "email": "  Valid@Example.COM  ",
            "password": "ValidPass1!",
        },
    )

    assert response.status_code == 201
    assert response.json()["username"] == "ValidUser"
    assert response.json()["email"] == "valid@example.com"
    with session_factory() as db:
        saved_user = db.query(User).one()
        assert saved_user.username == "ValidUser"
        assert saved_user.email == "valid@example.com"
        assert verify_password("ValidPass1!", saved_user.password)

    duplicate = client.post(
        "/users/",
        json={
            "username": "ValidUser ",
            "email": "other@example.com",
            "password": "ValidPass1!",
        },
    )
    assert duplicate.status_code == 409


def test_signup_creates_account_without_exposing_password(signup_client):
    client, session_factory = signup_client
    response = client.post(
        "/users/",
        json={
            "username": "jack2",
            "email": "jack@example.com",
            "password": "ValidPass1!",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],
        "username": "jack2",
        "email": "jack@example.com",
    }

    with session_factory() as db:
        saved_user = db.query(User).filter_by(username="jack2").one()
        assert verify_password("ValidPass1!", saved_user.password)

    duplicate = client.post(
        "/users/",
        json={
            "username": "jack2",
            "email": "other@example.com",
            "password": "ValidPass1!",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Username is already taken"}

    with session_factory() as db:
        assert db.query(User).filter_by(username="jack2").count() == 1

    user_id = response.json()["id"]
    authorization = {"Authorization": f"Bearer {create_access_token({'sub': user_id})}"}
    assert client.get("/users/").status_code == 401
    assert client.get(f"/users/{user_id}").status_code == 401
    assert client.get("/users/", headers=authorization).status_code == 410
    assert client.get(f"/users/{user_id}", headers=authorization).status_code == 410
    assert client.get("/users/999", headers=authorization).status_code == 410

    updated = client.put(
        f"/users/{user_id}?username=jack3&email=new@example.com",
        headers=authorization,
    )
    assert updated.status_code == 200
    assert updated.json() == {
        "id": user_id,
        "username": "jack3",
        "email": "new@example.com",
    }


def test_startup_retires_legacy_demo_password_without_creating_new_user(
    tmp_path, monkeypatch
):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(seed, "CONFIG_FOLDER", str(tmp_path))

    with Session(engine) as db:
        seed.seed_db(db)
        assert db.query(User).count() == 0

        legacy_user = User(
            username="jack", email="jackovand27", password=hash_password("1234")
        )
        db.add(legacy_user)
        db.commit()
        user_id = legacy_user.id

        seed.seed_db(db)
        db.refresh(legacy_user)
        assert legacy_user.id == user_id
        assert not verify_password("1234", legacy_user.password)
        retired_hash = legacy_user.password

        seed.seed_db(db)
        db.refresh(legacy_user)
        assert legacy_user.password == retired_hash

    engine.dispose()


def test_local_dev_seed_enables_quick_login_only_when_requested(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(seed, "CONFIG_FOLDER", str(tmp_path))

    with Session(engine) as db:
        seed.seed_db(db, local_dev_login=True)
        developer = db.query(User).filter_by(username="jack").one()
        developer_id = developer.id
        assert verify_password("1234", developer.password)

        seed.seed_db(db)
        db.refresh(developer)
        assert developer.id == developer_id
        assert not verify_password("1234", developer.password)

        seed.seed_db(db, local_dev_login=True)
        db.refresh(developer)
        assert developer.id == developer_id
        assert verify_password("1234", developer.password)

    engine.dispose()
