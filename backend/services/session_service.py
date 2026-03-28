from sqlalchemy.orm import Session
from db.modals import GameSession, ScenarioToSession, Scenario

def get_sandbox_session(db: Session, user_id: int):
    return db.query(GameSession).filter(
        GameSession.name == "Sandbox",
        GameSession.creatorID == user_id
    ).first()

def add_session(db: Session, user_id: int, name: str) -> int:
    ses = GameSession(name=name, creatorID=user_id)
    db.add(ses)
    db.commit()
    db.refresh(ses)
    return int(ses.id)

def get_scenario_byname(db: Session, name: str) -> Scenario | None:
    return db.query(Scenario).filter(Scenario.name == name).first()

def add_session_scenario(db: Session, sesID: int, scID: int, config: dict) -> None:
    ses = ScenarioToSession(scenarioID=scID,sessionID=sesID,config=config)
    db.add(ses)
    db.commit()
    db.refresh(ses)
    return None