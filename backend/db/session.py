from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from .modals import Base

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base.metadata.create_all(bind=engine)
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
