import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_websocket_connect(client):

    with client.websocket_connect("/ws/1") as ws:

        ws.send_json({"username": "jackson", "userID": "1"})

        response = ws.receive_json()

        assert response["type"] == "system"


def test_pwd_command(client):

    with client.websocket_connect("/ws/1") as ws:

        ws.send_json({"username": "jackson", "userID": "1"})

        # consume join messages
        ws.receive_json()
        ws.receive_json()

        ws.send_json({"type": "command", "input": "pwd"})

        response = ws.receive_json()

        assert response["type"] == "command_output"
