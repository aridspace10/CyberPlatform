import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_websocket_sleep(client):
    return
    with client.websocket_connect("/ws/1") as ws:

        ws.send_json({"username": "jackson", "userID": "1"})
        # consume join messages
        ws.receive_json()
        ws.receive_json()
        ws.send_json({"type": "command", "input": "sleep 2"})
        for i in range(10):
            msg = ws.receive_json()
            print(f"MSG {i}: {msg}")

        # response = ws.receive_json()
        # assert response["type"] == "command_output"
        # assert response["interaction"]
        # assert response["interaction"]["mode"] == "foreground"
        # response = ws.receive_json()
        # assert response["type"] == "terminal_state"
        # assert response["busy"] == False
