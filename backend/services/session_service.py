import json
from datetime import datetime
from typing import List

from db.modals import (
    GameSession,
    JoinRequest,
    Scenario,
    ScenarioToSession,
    SessionShell,
)
from sqlalchemy.orm import Session


############# GETTERS #############
def get_sandbox_session(db: Session, user_id: int):
    return (
        db.query(GameSession)
        .join(ScenarioToSession, ScenarioToSession.sessionID == GameSession.id)
        .join(Scenario, Scenario.id == ScenarioToSession.scenarioID)
        .filter(GameSession.creatorID == user_id, Scenario.name == "Tutorial")
        .first()
    )


def is_sandbox_session(db: Session, session_id: int) -> bool:
    return (
        db.query(ScenarioToSession)
        .join(Scenario, Scenario.id == ScenarioToSession.scenarioID)
        .filter(ScenarioToSession.sessionID == session_id, Scenario.name == "Tutorial")
        .first()
        is not None
    )


def restore_game_state(db: Session, session, session_id: int) -> bool:
    """Restore config; replace an interrupted MiniGames round with a playable one."""
    scenario = (
        db.query(ScenarioToSession)
        .filter(ScenarioToSession.sessionID == session_id)
        .first()
    )
    if scenario is None or not scenario.config:
        return False
    config = scenario.config
    if isinstance(config, str):
        config = json.loads(config)
    session.game_manager.set_config(config)
    if session.state == "running" and session.game_manager.game_type == "MiniGames":
        shells = (
            db.query(SessionShell).filter(SessionShell.SessionID == session_id).all()
        )
        participants = [str(shell.UserID) for shell in shells]
        if not participants:
            return False
        shell_data = session.game_manager.start_round(participants)
        for shell in shells:
            shell.shell = shell_data
        db.commit()
    elif session.state == "finished":
        session.game_manager.finished = True
    return True


def get_session(db: Session, sesID: int):
    return db.query(GameSession).filter(GameSession.id == sesID).first()


def get_scenario_byname(db: Session, name: str) -> Scenario | None:
    return db.query(Scenario).filter(Scenario.name == name).first()


def get_session_shell(db: Session, sesID: str, userID: str) -> SessionShell | None:
    return (
        db.query(SessionShell)
        .filter(SessionShell.SessionID == sesID, SessionShell.UserID == userID)
        .first()
    )


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
    ses = ScenarioToSession(scenarioID=scID, sessionID=sesID, config=config)
    db.add(ses)
    db.commit()
    db.refresh(ses)
    return None


def add_session_shell(db: Session, sesID: int, userID: int, shell: dict) -> None:
    ses = SessionShell(SessionID=sesID, UserID=userID, shell=shell)
    db.add(ses)
    db.commit()
    db.refresh(ses)
    return None

def add_join_request(db: Session, sesID: int, userID: int) -> None:
    now = datetime.now()
    req = JoinRequest(SessionID=sesID, UserID=userID, date=now)
    db.add(req)
    db.commit()
    db.refresh(req)
    return None

############## UPDATERS ###############
def update_session_shell(db: Session, sesID: int, userID: int, shell: dict) -> None:
    ses = (
        db.query(SessionShell)
        .filter(SessionShell.SessionID == sesID, SessionShell.UserID == userID)
        .first()
    )

    ses.shell = shell

    db.commit()
    db.refresh(ses)
