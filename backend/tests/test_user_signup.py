from db import seed
from db.authentication import create_access_token, hash_password, verify_password
from db.modals import Base, User
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import users
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def test_signup_creates_account_without_exposing_password():
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

        with Session(engine) as db:
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

        with Session(engine) as db:
            assert db.query(User).filter_by(username="jack2").count() == 1

        user_id = response.json()["id"]
        authorization = {
            "Authorization": f"Bearer {create_access_token({'sub': user_id})}"
        }
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

    engine.dispose()


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
