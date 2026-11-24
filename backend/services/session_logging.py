"""Small append-only JSONL logs for reconstructing terminal session failures."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import threading
import traceback
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

_locks_guard = threading.Lock()
_session_locks: dict[Path, threading.Lock] = {}
_prune_guard = threading.Lock()
_last_root_prune: dict[Path, datetime] = {}
_last_file_prune: dict[Path, datetime] = {}

LOG_RETENTION = timedelta(days=30)
PRUNE_INTERVAL = timedelta(days=1)
MAX_LOG_FILE_BYTES = 5 * 1024 * 1024
MAX_LOG_RECORD_BYTES = 32 * 1024
REDACTED_INPUT = "[redacted]"
_SESSION_DIRECTORY = re.compile(r"[A-Za-z0-9_.-]+-[0-9a-f]{64}\Z")


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
        resolved_root = root.resolve()
        _prune_expired_directories(resolved_root)
        self.directory = resolved_root / f"{readable_id}-{suffix}"
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
                "input": REDACTED_INPUT,
                "input_length": len(input_text),
                "cwd": REDACTED_INPUT,
                "outcome": outcome,
                "status": status,
                "interaction": (
                    None if interaction is None else {"mode": interaction.get("mode")}
                ),
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
                "input": REDACTED_INPUT,
                "input_length": len(input_text),
                "exception_type": type(error).__name__,
                "traceback": _stack_locations(error),
            },
        )

    def export_user_archive(self, user_id: str) -> bytes:
        """Return only this user's activity and errors as a downloadable ZIP."""
        archive_buffer = io.BytesIO()
        with self._lock:
            with ZipFile(archive_buffer, mode="w", compression=ZIP_DEFLATED) as archive:
                for path in (self.activity_path, self.error_path):
                    try:
                        _prune_file(
                            path, datetime.now(timezone.utc), MAX_LOG_FILE_BYTES
                        )
                    except OSError:
                        # A read-only log may still be safe to export after filtering.
                        pass
                    records = self._read_user_records(path, str(user_id))
                    archive.writestr(path.name, records)
        return archive_buffer.getvalue()

    @staticmethod
    def _read_user_records(path: Path, user_id: str) -> str:
        try:
            cutoff = datetime.now(timezone.utc) - LOG_RETENTION
            with path.open("r", encoding="utf-8") as log_file:
                records = []
                for line in log_file:
                    try:
                        record = json.loads(line)
                        stamp = datetime.fromisoformat(record["timestamp"])
                    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                        continue
                    if stamp.tzinfo is None:
                        stamp = stamp.replace(tzinfo=timezone.utc)
                    belongs_to_user = (
                        isinstance(record, dict)
                        and str(record.get("user_id")) == user_id
                    )
                    if belongs_to_user and stamp >= cutoff:
                        records.append(line)
                return "".join(records)
        except OSError:
            return ""

    def _append(self, path: Path, record: dict[str, Any]) -> None:
        try:
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            encoded = (line + "\n").encode("utf-8")
            if len(encoded) > MAX_LOG_RECORD_BYTES:
                return
            with self._lock:
                path.parent.mkdir(parents=True, exist_ok=True)
                _restrict_permissions(path.parent, 0o700)
                now = datetime.now(timezone.utc)
                last_prune = _last_file_prune.get(path)
                over_limit = (
                    path.exists()
                    and path.stat().st_size + len(encoded) > MAX_LOG_FILE_BYTES
                )
                if (
                    last_prune is None
                    or now - last_prune >= PRUNE_INTERVAL
                    or over_limit
                ):
                    # Leave headroom after rotation so a full log does not
                    # need a complete rewrite for every following input.
                    keep_bytes = (
                        MAX_LOG_FILE_BYTES // 2
                        if over_limit
                        else MAX_LOG_FILE_BYTES - len(encoded)
                    )
                    _prune_file(path, now, keep_bytes)
                    _last_file_prune[path] = now
                flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
                flags |= getattr(os, "O_NOFOLLOW", 0)
                with os.fdopen(
                    os.open(path, flags, 0o600), "a", encoding="utf-8", newline="\n"
                ) as log_file:
                    _restrict_permissions(path, 0o600)
                    log_file.write(line + "\n")
                    log_file.flush()
        except (OSError, TypeError, ValueError):
            # Diagnostics must never turn a failed command into a disconnected session.
            return


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stack_locations(error: Exception) -> str:
    """Keep useful frame locations without exception text or source lines."""
    return "".join(
        f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}\n'
        for frame in traceback.extract_tb(error.__traceback__)
    )


def _restrict_permissions(path: Path, mode: int) -> None:
    if os.name == "posix":
        os.chmod(path, mode)


def _prune_expired_directories(root: Path, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    with _prune_guard:
        last_prune = _last_root_prune.get(root)
        if last_prune is not None and now - last_prune < PRUNE_INTERVAL:
            return
        try:
            children = list(root.iterdir())
        except OSError:
            return
        cutoff = (now - LOG_RETENTION).timestamp()
        for child in children:
            if not _SESSION_DIRECTORY.fullmatch(child.name):
                continue
            try:
                with _lock_for(child):
                    if child.is_symlink() or child.is_junction() or not child.is_dir():
                        continue
                    resolved_child = child.resolve(strict=True)
                    if resolved_child.parent != root:
                        continue
                    files = [child / "activity.jsonl", child / "errors.jsonl"]
                    last_modified = max(
                        [child.stat().st_mtime]
                        + [path.stat().st_mtime for path in files if path.is_file()]
                    )
                    if last_modified < cutoff:
                        shutil.rmtree(resolved_child)
            except OSError:
                continue
        _last_root_prune[root] = now


def _prune_file(path: Path, now: datetime, max_bytes: int) -> None:
    """Keep only recent valid records, capped by the most recent bytes."""
    if not path.is_file():
        return
    cutoff = now - LOG_RETENTION
    records: deque[bytes] = deque()
    total = 0
    with path.open("rb") as source:
        for line in source:
            if len(line) > MAX_LOG_RECORD_BYTES:
                continue
            try:
                stamp = datetime.fromisoformat(json.loads(line)["timestamp"])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            if stamp < cutoff:
                continue
            records.append(line)
            total += len(line)
            while total > max_bytes:
                total -= len(records.popleft())
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, delete=False
        ) as out:
            temporary = Path(out.name)
            _restrict_permissions(temporary, 0o600)
            out.writelines(records)
        os.replace(temporary, path)
        _restrict_permissions(path, 0o600)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
