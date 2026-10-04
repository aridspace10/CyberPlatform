"""Small append-only JSONL logs for reconstructing terminal session failures."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_locks_guard = threading.Lock()
_session_locks: dict[Path, threading.Lock] = {}


def _lock_for(directory: Path) -> threading.Lock:
    with _locks_guard:
        return _session_locks.setdefault(directory, threading.Lock())


class SessionLogger:
    """Write a session's terminal activity and unexpected errors to separate files."""

    def __init__(self, session_id: str) -> None:
        self.session_id = str(session_id)
        configured_root = os.environ.get("CYBERPLATFORM_LOG_DIR")
        root = (
            Path(configured_root).expanduser()
            if configured_root
            else Path(__file__).resolve().parents[1] / "logs" / "sessions"
        )
        readable_id = re.sub(r"[^A-Za-z0-9_.-]", "_", self.session_id).strip(".")
        readable_id = readable_id[:48] or "session"
        suffix = hashlib.sha256(self.session_id.encode("utf-8")).hexdigest()
        self.directory = root.resolve() / f"{readable_id}-{suffix}"
        self.activity_path = self.directory / "activity.jsonl"
        self.error_path = self.directory / "errors.jsonl"
        self._lock = _lock_for(self.directory)

    def record_activity(
        self,
        *,
        request_id: str,
        user_id: str,
        username: str,
        input_kind: str,
        input_text: str,
        cwd: str,
        status: int,
        interaction: dict[str, str | None] | None,
        outcome: str = "completed",
        error_type: str | None = None,
    ) -> None:
        self._append(
            self.activity_path,
            {
                "timestamp": _timestamp(),
                "event": "terminal_input",
                "session_id": self.session_id,
                "request_id": request_id,
                "user_id": str(user_id),
                "username": username,
                "input_kind": input_kind,
                "input": input_text,
                "cwd": cwd,
                "outcome": outcome,
                "status": status,
                "interaction": interaction,
                "error_type": error_type,
            },
        )

    def record_session_event(self, *, event: str, user_id: str, username: str) -> None:
        self._append(
            self.activity_path,
            {
                "timestamp": _timestamp(),
                "event": event,
                "session_id": self.session_id,
                "user_id": str(user_id),
                "username": username,
            },
        )

    def record_error(
        self,
        *,
        request_id: str,
        user_id: str,
        username: str,
        input_kind: str,
        input_text: str,
        error: Exception,
    ) -> None:
        self._append(
            self.error_path,
            {
                "timestamp": _timestamp(),
                "event": "unexpected_terminal_exception",
                "session_id": self.session_id,
                "request_id": request_id,
                "user_id": str(user_id),
                "username": username,
                "input_kind": input_kind,
                "input": input_text,
                "exception_type": type(error).__name__,
                "exception_message": str(error),
                "traceback": "".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                ),
            },
        )

    def _append(self, path: Path, record: dict[str, Any]) -> None:
        try:
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            with self._lock:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8", newline="\n") as log_file:
                    log_file.write(line + "\n")
                    log_file.flush()
        except (OSError, TypeError, ValueError):
            # Diagnostics must never turn a failed command into a disconnected session.
            return


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
