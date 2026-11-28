"""Keep process-local game runtimes on one backend worker per deployment."""

import os
from contextlib import contextmanager
from pathlib import Path

from db.session import engine


def _runtime_lock_path() -> Path:
    configured = os.environ.get("CYBERPLATFORM_RUNTIME_LOCK_FILE")
    if configured:
        return Path(configured).resolve()
    if engine.dialect.name == "sqlite" and engine.url.database:
        return Path(engine.url.database).resolve().with_suffix(".runtime.lock")
    raise RuntimeError(
        "Set CYBERPLATFORM_RUNTIME_LOCK_FILE on shared persistent storage "
        "to enforce the single-worker game runtime."
    )


def _reject_worker_settings() -> None:
    for name in ("WEB_CONCURRENCY", "UVICORN_WORKERS"):
        value = os.environ.get(name)
        if value is None:
            continue
        try:
            count = int(value)
        except ValueError as exc:
            raise RuntimeError(f"{name} must be set to 1") from exc
        if count != 1:
            raise RuntimeError(f"{name}={value} is unsupported: run one backend worker")


@contextmanager
def single_game_worker():
    """Hold a process lock for the full ASGI lifespan."""
    _reject_worker_settings()
    path = _runtime_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as lock_file:
        lock_file.seek(0)
        lock_file.write(b"\0")
        lock_file.flush()
        lock_file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(
                f"Another backend worker owns the game runtime lock at {path}. "
                "Run exactly one worker and one backend instance."
            ) from exc
        try:
            yield
        finally:
            if os.name == "nt":
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
