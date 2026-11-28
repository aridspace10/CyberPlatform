import json
from datetime import datetime
from typing import List

from db.modals import (
    GameSession,
    JoinRequest,
    RoundState,
    Scenario,
    ScenarioToSession,
    SessionShell,
)
from network.SessionManger import Player
from services.user_service import get_user_by_id
from sqlalchemy.orm import Session


def restore_game_state(db: Session, session, session_id: int) -> bool:
    """Restore exact private round state and saved shells for all participants."""
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
    if session.game_manager.game_type == "MiniGames":
        saved_round = db.get(RoundState, session_id)
        if saved_round is None:
            # Old running games have no answers or scores to recover safely.
            return False
        session.game_manager.import_state(saved_round.state)
    elif session.state == "finished":
        session.game_manager.finished = True
    shells = db.query(SessionShell).filter(SessionShell.SessionID == session_id).all()
    if not shells:
        return False
    for saved_shell in shells:
        user = get_user_by_id(db, saved_shell.UserID)
        if user is None or not user.username or not saved_shell.shell:
            return False
        player = Player(None, user.username, str(user.id))
        player.load_shell(saved_shell.shell)
        session.players[user.username] = player
    return True


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
