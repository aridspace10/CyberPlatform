from sqlalchemy.orm import Session
from db.modals import GameSession, ScenarioToSession

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
