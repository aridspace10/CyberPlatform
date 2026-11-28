import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from main import app
from services.single_worker import single_game_worker


@pytest.mark.parametrize("value", ["2", "0", "many"])
def test_startup_rejects_unsupported_worker_count(monkeypatch, value):
    monkeypatch.setenv("WEB_CONCURRENCY", value)
    with pytest.raises(RuntimeError, match="WEB_CONCURRENCY"):
        with TestClient(app):
            pass


def test_another_process_cannot_own_the_same_game_runtime(monkeypatch, tmp_path):
    lock_path = tmp_path / "game.runtime.lock"
    monkeypatch.setenv("CYBERPLATFORM_RUNTIME_LOCK_FILE", str(lock_path))
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    env.pop("WEB_CONCURRENCY", None)
    env.pop("UVICORN_WORKERS", None)
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "from services.single_worker import single_game_worker\n"
            "with single_game_worker():\n"
            "    print('ready', flush=True)\n"
            "    input()\n",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        assert child.stdout.readline().strip() == "ready"
        with pytest.raises(RuntimeError, match="Another backend worker"):
            with single_game_worker():
                pass
    finally:
        child.stdin.close()
        child.wait(timeout=10)
    with single_game_worker():
        pass
