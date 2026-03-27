from sqlalchemy.orm import Session
from db.modals import GameSession

def get_sandbox_session(db: Session, user_id: int):
    return db.query(GameSession).filter(
        GameSession.name == "Sandbox",
        GameSession.creatorID == user_id
    ).first()