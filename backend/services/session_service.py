from sqlalchemy.orm import Session
from typing import List 
from db.modals import GameSession, ScenarioToSession, Scenario, SessionShell


############# GETTERS #############
def get_sandbox_session(db: Session, user_id: int):
    return db.query(GameSession).filter(
        GameSession.name == "Sandbox",
        GameSession.creatorID == user_id
    ).first()

def get_session(db: Session, sesID: int):
    return db.query(GameSession).filter(
        GameSession.id == sesID
    ).first()

def get_scenario_byname(db: Session, name: str) -> Scenario | None:
    return db.query(Scenario).filter(Scenario.name == name).first()

def get_session_shell(db: Session, sesID: str, userID: str) -> SessionShell | None:
    return db.query(SessionShell).filter(SessionShell.SessionID == sesID, SessionShell.UserID == userID).first()

def get_session_shells(db: Session, sesID: str) -> List[SessionShell] | None:
    return db.query(SessionShell).filter(SessionShell.SessionID == sesID).all()

############# ADDERS #############
def add_session(db: Session, user_id: int, name: str, state: str) -> int:
    ses = GameSession(name=name, creatorID=user_id, state=state)
    db.add(ses)
    db.commit()
    db.refresh(ses)
    return int(ses.id)

def add_session_scenario(db: Session, sesID: int, scID: int, config: dict) -> None:
    ses = ScenarioToSession(scenarioID=scID,sessionID=sesID,config=config)
    db.add(ses)
    db.commit()
    db.refresh(ses)
    return None

def add_session_shell(db: Session, sesID: int, userID: int, shell: dict) -> None:
    ses = SessionShell(SessionID=sesID,UserID=userID,shell=shell)
    db.add(ses)
    db.commit()
    db.refresh(ses)
    return None

############## UPDATERS ###############
def update_session_shell(db: Session, sesID: int, userID: int, shell: dict) -> None:
    ses = db.query(SessionShell).filter(SessionShell.SessionID == sesID,  SessionShell.UserID == userID).first()

    ses.shell = shell

    db.commit()
    db.refresh(ses)

############# DELETE ###############
def delete_session_shell(db: Session, sesID: int) -> None:
    db.query(SessionShell).filter(SessionShell.SessionID == sesID).delete()
    db.query(ScenarioToSession).filter(ScenarioToSession.sessionID == sesID).delete()
    db.query(GameSession).filter(GameSession.id == sesID).delete()
    db.commit()
    return None

def wipe_session_db(db: Session) -> None:
    db.query(SessionShell).delete()
    db.query(ScenarioToSession).delete()
    db.query(GameSession).delete()
    db.commit()
    return None