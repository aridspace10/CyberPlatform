from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.modals import GameSession, ScenarioToSession, SessionShell
from pydantic import BaseModel
from typing import Dict, Any

class SessionCreate(BaseModel):
    creatorID: int
    name: str
    scenarioID: str
    config: Dict[str, Any]

class SessionJoin(BaseModel):
    userID: int
    sessionID: int
    shell: Dict[str, Any]

router = APIRouter(prefix="/sessions", tags=["sessions"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CREATE USER
@router.post("/")
def create_session(ses_data: SessionCreate, db: Session = Depends(get_db)):
    ses = GameSession(name=ses_data.name, creatorID=ses_data.creatorID)
    db.add(ses)
    db.commit()
    db.refresh(ses)
    ss = ScenarioToSession(scenarioID=ses_data.scenarioID, sessionID= ses.id, config= ses_data.config)
    db.add(ss)
    db.commit()
    db.refresh(ss)
    return (ses, ss)

@router.post("/sessions/{session_id}")
def join_session(ses_data: SessionJoin, db: Session = Depends(get_db)):
    ses = SessionShell(SessionID=ses_data.sessionID,UserID=ses_data.userID,shell=ses_data.shell)
    db.add(ses)
    db.commit()
    db.refresh(ses)
    return ses

# GET USERS
@router.get("/")
def get_sessions(db: Session = Depends(get_db)):
    return db.query(GameSession).all()

@router.get("/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    return db.query(GameSession).filter(GameSession.id == session_id).first()

@router.get("/sandbox/{user_id}")
def get_sandbox_session(user_id: int, db: Session = Depends(get_db)):
    return db.query(GameSession).filter(GameSession.name == "Sandbox" and GameSession.creatorID == user_id).first()

# UPDATE USER
@router.put("/{session_id}")
def update_session(db: Session = Depends(get_db)):
    pass