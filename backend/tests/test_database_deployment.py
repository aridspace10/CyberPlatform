"""Fresh deployment, redeployment, and SQLite recovery coverage."""

import pytest
from db.configuration import (
    BACKEND_DIR,
    check_database_storage,
    database_path,
    database_url,
)
from db.maintenance import copy_database
from db.modals import GameSession, SessionShell, User
from db.session import upgrade_schema
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session


def test_production_requires_a_persistent_absolute_database_path(tmp_path):
    with pytest.raises(RuntimeError, match="CYBERPLATFORM_DATABASE_PATH"):
        database_path({"CYBERPLATFORM_ENV": "production"})
    with pytest.raises(RuntimeError, match="absolute"):
        database_path(
            {"CYBERPLATFORM_ENV": "production", "CYBERPLATFORM_DATABASE_PATH": "app.db"}
        )
    with pytest.raises(RuntimeError, match="outside the source checkout"):
        database_path(
            {
                "CYBERPLATFORM_ENV": "production",
                "CYBERPLATFORM_DATABASE_PATH": str(BACKEND_DIR / "public.db"),
            }
        )
    assert (
        database_path(
            {
                "CYBERPLATFORM_ENV": "production",
                "CYBERPLATFORM_DATABASE_PATH": str(tmp_path / "live.db"),
            }
        )
        == tmp_path / "live.db"
    )


def test_database_location_does_not_depend_on_cwd(monkeypatch, tmp_path):
    first = database_path({})
    monkeypatch.chdir(tmp_path)
    assert database_path({}) == first


def test_missing_database_mount_fails_before_creating_data(tmp_path):
    path = tmp_path / "missing-mount" / "live.db"
    with pytest.raises(RuntimeError, match="does not exist"):
        check_database_storage(path)
    assert not path.exists()


def test_upgrade_existing_session_schema_and_reject_future_version(tmp_path):
    engine = create_engine(database_url(tmp_path / "legacy.db"))
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE session (id INTEGER PRIMARY KEY, name VARCHAR, "
                "creatorID INTEGER, state VARCHAR)"
            )
        )
    upgrade_schema(engine)
    assert "visibility" in {
        column["name"] for column in inspect(engine).get_columns("session")
    }
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA user_version")).scalar_one() == 1
    upgrade_schema(engine)
    with engine.begin() as connection:
        connection.execute(text("PRAGMA user_version = 999"))
    with pytest.raises(RuntimeError, match="newer"):
        upgrade_schema(engine)
    engine.dispose()


def test_fresh_deploy_redeploy_and_backup_restore_preserve_account_and_sandbox(
    tmp_path,
):
    live = tmp_path / "live.db"
    backup = tmp_path / "backup.db"
    engine = create_engine(database_url(live))
    check_database_storage(live)
    upgrade_schema(engine)
    assert "users" in inspect(engine).get_table_names()

    with Session(engine) as db:
        assert db.query(User).count() == 0
        user = User(username="public_test", email="test@example.com", password="hash")
        db.add(user)
        db.flush()
        game = GameSession(name="Test Sandbox", creatorID=user.id, state="running")
        db.add(game)
        db.flush()
        db.add(SessionShell(SessionID=game.id, UserID=user.id, shell={"cwd": "/lab"}))
        db.commit()
    engine.dispose()

    # A redeploy opens the same volume and safely reruns schema upgrades.
    engine = create_engine(database_url(live))
    upgrade_schema(engine)
    with Session(engine) as db:
        assert (
            db.query(User).filter_by(username="public_test").one().email
            == "test@example.com"
        )
        assert db.query(SessionShell).one().shell == {"cwd": "/lab"}
    engine.dispose()

    copy_database(live, backup)
    restored = tmp_path / "restored.db"
    copy_database(backup, restored)
    restored_engine = create_engine(database_url(restored))
    with Session(restored_engine) as db:
        assert db.query(User).filter_by(username="public_test").count() == 1
        assert db.query(SessionShell).one().shell == {"cwd": "/lab"}
    restored_engine.dispose()


def test_restore_requires_explicit_replace_and_leaves_existing_data_intact(tmp_path):
    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    source.write_bytes(b"source")
    target.write_bytes(b"target")
    with pytest.raises(FileExistsError):
        copy_database(source, target)
    assert target.read_bytes() == b"target"
    with pytest.raises(ValueError, match="differ"):
        copy_database(source, source)
