from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./cubersim.db"

engine = create_async_engine(DATABASE_URL, echo=False)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

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

class ScenarioToGame(Base):
    __tablename__ = "scenariosToGame"
    scenarioID = Column(Integer, foreign_key=True)
    gameID = Column(Integer, game_key=True)
    config = Column(JSON)