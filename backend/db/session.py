from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from .modals import Base

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def migrate_friendships(database_engine):
    if (
        database_engine.dialect.name != "sqlite"
        or "friendships" not in inspect(database_engine).get_table_names()
    ):
        return
    friendship_columns = {
        column["name"] for column in inspect(database_engine).get_columns("friendships")
    }
    with database_engine.begin() as connection:
        if "pair_key" not in friendship_columns:
            connection.execute(
                text("ALTER TABLE friendships ADD COLUMN pair_key VARCHAR")
            )
        if "declined_at" not in friendship_columns:
            connection.execute(
                text("ALTER TABLE friendships ADD COLUMN declined_at DATETIME")
            )
        rows = connection.execute(
            text(
                "SELECT id, requester_id, recipient_id, status FROM friendships "
                "ORDER BY CASE WHEN status = 'accepted' THEN 0 ELSE 1 END, id"
            )
        ).all()
        seen = set()
        for row in rows:
            low = min(row.requester_id, row.recipient_id)
            high = max(row.requester_id, row.recipient_id)
            pair_key = f"{low}:{high}"
            if pair_key in seen:
                connection.execute(
                    text("DELETE FROM friendships WHERE id = :id"), {"id": row.id}
                )
            else:
                seen.add(pair_key)
                connection.execute(
                    text("UPDATE friendships SET pair_key = :pair_key WHERE id = :id"),
                    {"pair_key": pair_key, "id": row.id},
                )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_friendships_pair_key "
                "ON friendships (pair_key)"
            )
        )


Base.metadata.create_all(bind=engine)
migrate_friendships(engine)
if engine.dialect.name == "sqlite" and "session" in inspect(engine).get_table_names():
    session_columns = {
        column["name"] for column in inspect(engine).get_columns("session")
    }
    if "visibility" not in session_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE session ADD COLUMN visibility VARCHAR "
                    "NOT NULL DEFAULT 'public'"
                )
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
