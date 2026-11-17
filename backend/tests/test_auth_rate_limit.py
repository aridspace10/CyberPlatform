from db.modals import Base
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import users
from services import auth_rate_limit
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


def make_client(engine, *, proxy=False, client_host="testclient"):
    factory = sessionmaker(bind=engine)

    def get_test_db():
        with factory() as db:
            yield db

    app = FastAPI()
    app.include_router(users.router)
    app.dependency_overrides[users.get_db] = get_test_db
    if proxy:
        app = ProxyHeadersMiddleware(app, trusted_hosts=[client_host])
    return TestClient(app, client=(client_host, 50000))


def memory_engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return engine


def login(client, username="alice", headers=None):
    return client.post(
        "/users/login",
        json={"username": username, "password": "incorrect"},
        headers=headers,
    )


def test_login_limit_and_reset_window(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(auth_rate_limit.time, "time", lambda: now[0])
    engine = memory_engine()
    with make_client(engine) as client:
        for _ in range(auth_rate_limit.LOGIN_ACCOUNT_CLIENT_LIMIT):
            assert login(client).status_code == 401

        limited = login(client)
        assert limited.status_code == 429
        assert limited.json() == {
            "detail": "Too many attempts. Please try again later."
        }
        assert limited.headers["Retry-After"] == "200"
        assert login(client, "other-account").status_code == 401

        now[0] = 1200.0
        assert login(client).status_code == 401
    engine.dispose()


def test_signup_limit_and_reset_window(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(auth_rate_limit.time, "time", lambda: now[0])
    engine = memory_engine()
    signup = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "ValidPass1!",
    }
    with make_client(engine) as client:
        assert client.post("/users/", json=signup).status_code == 201
        for _ in range(auth_rate_limit.SIGNUP_CLIENT_LIMIT - 1):
            assert client.post("/users/", json=signup).status_code == 409
        assert client.post("/users/", json=signup).status_code == 429

        now[0] = 1200.0
        assert client.post("/users/", json=signup).status_code == 409
    engine.dispose()


def test_limits_are_shared_by_separate_app_instances(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_rate_limit.time, "time", lambda: 1000.0)
    database_url = f"sqlite:///{tmp_path / 'accounts.db'}"
    first_engine = create_engine(
        database_url, connect_args={"check_same_thread": False}
    )
    second_engine = create_engine(
        database_url, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(first_engine)
    with make_client(first_engine) as first, make_client(second_engine) as second:
        for _ in range(auth_rate_limit.LOGIN_ACCOUNT_CLIENT_LIMIT):
            assert login(first).status_code == 401
        assert login(second).status_code == 429
    first_engine.dispose()
    second_engine.dispose()


def test_forwarded_address_is_used_only_for_trusted_proxy(monkeypatch):
    monkeypatch.setattr(auth_rate_limit.time, "time", lambda: 1000.0)
    engine = memory_engine()
    with make_client(engine) as direct:
        for index in range(auth_rate_limit.LOGIN_ACCOUNT_CLIENT_LIMIT):
            assert (
                login(
                    direct, headers={"X-Forwarded-For": f"198.51.100.{index + 1}"}
                ).status_code
                == 401
            )
        assert (
            login(direct, headers={"X-Forwarded-For": "198.51.100.99"}).status_code
            == 429
        )
    engine.dispose()

    engine = memory_engine()
    with make_client(engine, proxy=True) as proxied:
        for _ in range(auth_rate_limit.LOGIN_ACCOUNT_CLIENT_LIMIT):
            assert (
                login(proxied, headers={"X-Forwarded-For": "198.51.100.1"}).status_code
                == 401
            )
        assert (
            login(proxied, headers={"X-Forwarded-For": "198.51.100.1"}).status_code
            == 429
        )
        assert (
            login(proxied, headers={"X-Forwarded-For": "198.51.100.2"}).status_code
            == 401
        )
    engine.dispose()


def test_account_limit_spans_clients(monkeypatch):
    monkeypatch.setattr(auth_rate_limit.time, "time", lambda: 1000.0)
    engine = memory_engine()
    for index in range(auth_rate_limit.LOGIN_ACCOUNT_LIMIT):
        with make_client(engine, client_host=f"198.51.100.{index + 1}") as client:
            assert login(client).status_code == 401
    with make_client(engine, client_host="198.51.100.99") as client:
        assert login(client).status_code == 429
    engine.dispose()


def test_client_limit_spans_accounts(monkeypatch):
    monkeypatch.setattr(auth_rate_limit.time, "time", lambda: 1000.0)
    engine = memory_engine()
    with make_client(engine) as client:
        for index in range(auth_rate_limit.LOGIN_CLIENT_LIMIT):
            assert login(client, f"account-{index}").status_code == 401
        assert login(client, "another-account").status_code == 429
    engine.dispose()
