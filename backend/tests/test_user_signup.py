from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from db.authentication import verify_password
from db.modals import Base, User
from routers import users


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
            json={"username": "jack2", "email": "jack@example.com", "password": "ValidPass1!"},
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
            json={"username": "jack2", "email": "other@example.com", "password": "ValidPass1!"},
        )
        assert duplicate.status_code == 409
        assert duplicate.json() == {"detail": "Username is already taken"}

        with Session(engine) as db:
            assert db.query(User).filter_by(username="jack2").count() == 1

    engine.dispose()
