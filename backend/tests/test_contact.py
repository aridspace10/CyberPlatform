import smtplib

from db.modals import Base
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import contact
from services import auth_rate_limit
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

REPORT = {
    "name": "Alex",
    "email": "alex@example.com",
    "category": "bug",
    "subject": "Sandbox does not open",
    "description": "The sandbox stays on its loading screen.",
    "steps": "Sign in, then open the Sandbox.",
    "expected": "The terminal appears.",
    "actual": "Loading screen remains.",
    "page": "/game/123",
    "device": "Windows, Chrome",
}


def make_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    def get_test_db():
        with factory() as db:
            yield db

    app = FastAPI()
    app.include_router(contact.router)
    app.dependency_overrides[contact.get_db] = get_test_db
    return TestClient(app), engine


def test_contact_email_is_structured_and_replyable(monkeypatch):
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("smtp.example.com", 587, 10)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def starttls(self, context):
            assert context is not None

        def login(self, username, password):
            assert (username, password) == ("mailer", "secret")

        def send_message(self, message):
            sent.append(message)

    monkeypatch.setattr("services.contact_email.smtplib.SMTP", FakeSMTP)
    monkeypatch.setenv("CYBERPLATFORM_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("CYBERPLATFORM_CONTACT_FROM", "support@example.com")
    monkeypatch.setenv("CYBERPLATFORM_CONTACT_TO", "issues@example.com")
    monkeypatch.setenv("CYBERPLATFORM_SMTP_USERNAME", "mailer")
    monkeypatch.setenv("CYBERPLATFORM_SMTP_PASSWORD", "secret")

    client, engine = make_client()
    with client:
        response = client.post("/api/contact", json=REPORT)
    engine.dispose()

    assert response.status_code == 201
    reference = response.json()["reference"]
    assert reference.startswith("CP-")
    assert len(sent) == 1
    message = sent[0]
    assert message["From"] == "support@example.com"
    assert message["To"] == "issues@example.com"
    assert message["Reply-To"] == REPORT["email"]
    assert message["Subject"] == (
        f"[CyberPlatform][bug] {REPORT['subject']} ({reference})"
    )
    assert message["X-CyberPlatform-Category"] == "bug"
    assert message["X-CyberPlatform-Reference"] == reference
    body = message.get_content()
    for detail in (
        "WHAT HAPPENED",
        REPORT["description"],
        "STEPS TO REPRODUCE",
        REPORT["steps"],
        REPORT["expected"],
        REPORT["actual"],
        REPORT["page"],
        REPORT["device"],
    ):
        assert detail in body


def test_contact_requires_configuration_and_does_not_claim_success(monkeypatch):
    for key in (
        "CYBERPLATFORM_SMTP_HOST",
        "CYBERPLATFORM_CONTACT_FROM",
        "CYBERPLATFORM_CONTACT_TO",
    ):
        monkeypatch.delenv(key, raising=False)
    client, engine = make_client()
    with client:
        response = client.post("/api/contact", json=REPORT)
    engine.dispose()
    assert response.status_code == 503
    assert "reference" not in response.json()


def test_contact_delivery_failure_returns_retryable_error(monkeypatch):
    def fail_delivery(report):
        raise smtplib.SMTPException("down")

    monkeypatch.setattr(contact, "send_contact_report", fail_delivery)
    client, engine = make_client()
    with client:
        response = client.post("/api/contact", json=REPORT)
    engine.dispose()
    assert response.status_code == 503
    assert "could not be sent" in response.json()["detail"]


def test_contact_rejects_invalid_and_header_injection(monkeypatch):
    monkeypatch.setattr(contact, "send_contact_report", lambda report: "unexpected")
    client, engine = make_client()
    with client:
        for changes in (
            {"email": "alex@example.com\r\nBcc: victim@example.com"},
            {"subject": "Issue\nBcc: victim@example.com"},
            {"description": "   "},
            {"description": "         x"},
            {"subject": "  x  "},
            {"category": "urgent"},
        ):
            response = client.post("/api/contact", json={**REPORT, **changes})
            assert response.status_code == 422
    engine.dispose()


def test_contact_rate_limit(monkeypatch):
    monkeypatch.setattr(contact, "send_contact_report", lambda report: "CP-123")
    monkeypatch.setattr(auth_rate_limit.time, "time", lambda: 1000.0)
    client, engine = make_client()
    with client:
        for _ in range(auth_rate_limit.CONTACT_CLIENT_LIMIT):
            assert client.post("/api/contact", json=REPORT).status_code == 201
        assert client.post("/api/contact", json=REPORT).status_code == 429
    engine.dispose()
