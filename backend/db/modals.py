from sqlalchemy import Column, DateTime, Integer, String, JSON, ForeignKey
from .modals import Base
from sqlalchemy.orm import DeclarativeBase
import datetime

class Base(DeclarativeBase):
    pass

class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    created_at = Column(DateTime)
    snapshot = Column(JSON)

class ScenarioInfo(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)

class Game(Base):
    __tablename__ = "game"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    date = Column(String)

class scenario_to_game(Base):
    __tablename__ = "scenariosToGame"
    scenarioID = Column(Integer, ForeignKey("scenarios.id"))
    gameID = Column(Integer, ForeignKey("game.id"))
    config = Column(JSON)

class SessionModel(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    name = Column(String)
    state = Column(String)

    # Entire serialized game state
    data = Column(JSON)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)