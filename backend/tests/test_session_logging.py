"""Privacy and retention behavior for terminal diagnostics."""

import io
import json
import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zipfile import ZipFile

import pytest
from services import session_logging


def _activity(logger, text="echo secret-token", cwd="/", interaction=None):
    logger.record_activity(
        request_id="request-1",
        user_id="42",
        username="player",
        input_kind="command",
        input_text=text,
        cwd=cwd,
        status=0,
        interaction=interaction,
    )


def test_diagnostics_redact_input_and_exception_text(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERPLATFORM_LOG_DIR", str(tmp_path))
    logger = session_logging.SessionLogger("session-1")
    secret = "secret-token"
    _activity(
        logger,
        f"echo {secret}",
        cwd=f"/private/{secret}",
        interaction={"mode": "foreground", "prompt": f"remove {secret}?"},
    )

    try:
        raise ValueError(secret)
    except ValueError as error:
        logger.record_error(
            request_id="request-1",
            user_id="42",
            username="player",
            input_kind="command",
            input_text=f"echo {secret}",
            error=error,
        )

    activity = json.loads(logger.activity_path.read_text(encoding="utf-8"))
    failure = json.loads(logger.error_path.read_text(encoding="utf-8"))
    assert activity["input"] == failure["input"] == "[redacted]"
    assert activity["cwd"] == "[redacted]"
    assert activity["interaction"] == {"mode": "foreground"}
    assert activity["input_length"] == failure["input_length"] == len(f"echo {secret}")
    assert failure["exception_type"] == "ValueError"
    assert "test_diagnostics_redact_input_and_exception_text" in failure["traceback"]
    assert "exception_message" not in failure
    assert secret not in logger.activity_path.read_text(encoding="utf-8")
    assert secret not in logger.error_path.read_text(encoding="utf-8")


def test_archive_removes_expired_records_and_filters_users(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERPLATFORM_LOG_DIR", str(tmp_path))
    logger = session_logging.SessionLogger("session-2")
    _activity(logger)
    fresh = json.loads(logger.activity_path.read_text(encoding="utf-8"))
    old = {
        **fresh,
        "timestamp": (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
    }
    other = {**fresh, "user_id": "99"}
    with logger.activity_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(old) + "\n")
        stream.write(json.dumps(other) + "\n")

    with ZipFile(io.BytesIO(logger.export_user_archive("42"))) as archive:
        records = [
            json.loads(line)
            for line in archive.read("activity.jsonl").decode("utf-8").splitlines()
        ]
    assert records == [fresh]
    assert len(logger.activity_path.read_text(encoding="utf-8").splitlines()) == 2


def test_configured_retention_shortens_export_window(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERPLATFORM_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(
        session_logging,
        "settings",
        replace(session_logging.settings, log_retention_days=7),
    )
    logger = session_logging.SessionLogger("short-retention")
    _activity(logger)
    fresh = json.loads(logger.activity_path.read_text(encoding="utf-8"))
    expired = {
        **fresh,
        "timestamp": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
    }
    with logger.activity_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(expired) + "\n")

    with ZipFile(io.BytesIO(logger.export_user_archive("42"))) as archive:
        records = [
            json.loads(line)
            for line in archive.read("activity.jsonl").decode("utf-8").splitlines()
        ]
    assert records == [fresh]


def test_old_session_logs_are_pruned_without_touching_unrelated_paths(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("CYBERPLATFORM_LOG_DIR", str(tmp_path))
    logger = session_logging.SessionLogger("old-session")
    _activity(logger)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (unrelated / "keep.txt").write_text("keep", encoding="utf-8")
    future = datetime.now(timezone.utc) + timedelta(days=32)

    session_logging._prune_expired_directories(tmp_path.resolve(), future)

    assert not logger.directory.exists()
    assert (unrelated / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_log_pruning_does_not_follow_a_session_named_symlink(tmp_path):
    root = tmp_path / "logs"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    link = root / ("session-" + "a" * 64)
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are unavailable")

    session_logging._prune_expired_directories(
        root.resolve(), datetime.now(timezone.utc) + timedelta(days=32)
    )

    assert link.is_symlink()
    assert (outside / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_diagnostic_file_size_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERPLATFORM_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(
        session_logging,
        "settings",
        replace(session_logging.settings, max_log_file_bytes=1024),
    )
    logger = session_logging.SessionLogger("session-3")

    for index in range(40):
        logger.record_activity(
            request_id=str(index),
            user_id="42",
            username="player",
            input_kind="command",
            input_text="echo hello",
            cwd="/",
            status=0,
            interaction=None,
        )

    assert logger.activity_path.stat().st_size <= 1024
    assert (
        json.loads(logger.activity_path.read_text(encoding="utf-8").splitlines()[-1])[
            "request_id"
        ]
        == "39"
    )


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
def test_log_files_are_private_on_posix(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERPLATFORM_LOG_DIR", str(tmp_path))
    logger = session_logging.SessionLogger("private-session")
    _activity(logger)

    assert logger.directory.stat().st_mode & 0o777 == 0o700
    assert logger.activity_path.stat().st_mode & 0o777 == 0o600
