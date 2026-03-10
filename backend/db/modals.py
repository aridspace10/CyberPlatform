from sqlalchemy import Column, DateTime, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase
import datetime

class Base(DeclarativeBase):
    pass

class Scenario(Base):
    __tablename__ = "Scenario"
    name = Column(String)
    description = Column(String)
    config = Column(JSON)

class Session(Base):
    __tablename__ = "SessionID"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    creatorID = Column(Integer, ForeignKey("users.id"))

class scenario_to_session(Base):
    __tablename__ = "scenariosToGame"
    scenarioID = Column(Integer, ForeignKey("scenarios.id"), primary_key=True)
    sessionID = Column(Integer, ForeignKey("game.id"), primary_key=True)
    config = Column(JSON)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String)