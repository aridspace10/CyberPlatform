from sqlalchemy import Column, DateTime, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase
import datetime

class Base(DeclarativeBase):
    pass

class Scenario(Base):
    __tablename__ = "scenario"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    config = Column(JSON)

class GameSession(Base):
    __tablename__ = "session"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    creatorID = Column(Integer, ForeignKey("users.id"))

class SessionShell(Base):
    __tablename__ = "Session_Shell"
    SessionID = Column(Integer, ForeignKey("scenario.id"), primary_key=True)
    UserID = Column(Integer, ForeignKey("users.id"), primary_key=True)
    shell = Column(JSON)

class ScenarioToSession(Base):
    __tablename__ = "scenariosToGame"
    scenarioID = Column(Integer, ForeignKey("scenario.id"), primary_key=True)
    sessionID = Column(Integer, ForeignKey("session.id"), primary_key=True)
    config = Column(JSON)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String)
    password = Column(String)