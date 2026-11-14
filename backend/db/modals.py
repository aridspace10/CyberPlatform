from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Scenario(Base):
    __tablename__ = "scenario"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String)
    config: Mapped[dict] = mapped_column(JSON)


class GameSession(Base):
    __tablename__ = "session"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String)
    creatorID: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    state: Mapped[Optional[str]] = mapped_column(String)
    visibility: Mapped[str] = mapped_column(
        String, nullable=False, default="public", server_default=text("'public'")
    )


class SessionShell(Base):
    __tablename__ = "Session_Shell"
    SessionID: Mapped[int] = mapped_column(ForeignKey("session.id"), primary_key=True)
    UserID: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    shell: Mapped[Optional[dict]] = mapped_column(JSON)


class ScenarioToSession(Base):
    __tablename__ = "scenariosToGame"
    scenarioID: Mapped[int] = mapped_column(ForeignKey("scenario.id"), primary_key=True)
    sessionID: Mapped[int] = mapped_column(ForeignKey("session.id"), primary_key=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String, unique=True)
    email: Mapped[Optional[str]] = mapped_column(String)
    password: Mapped[Optional[str]] = mapped_column(String)


class Friendship(Base):
    """A request becomes a friendship when its recipient accepts it."""

    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint(
            "requester_id", "recipient_id", name="uq_friendship_direction"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")


class JoinRequest(Base):
    __tablename__ = "joinRequest"
    SessionID: Mapped[int] = mapped_column(ForeignKey("session.id"), primary_key=True)
    UserID: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    date: Mapped[DateTime] = mapped_column(DateTime)
