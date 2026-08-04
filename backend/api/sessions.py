from typing import Dict, Literal

from db.modals import GameSession as DatabaseGameSession
from db.modals import Scenario, ScenarioToSession, SessionShell
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from network.SessionManger import session_manager
from pydantic import BaseModel, ConfigDict, Field
from services.session_service import (
    add_session,
    add_session_scenario,
    add_session_shell,
    get_sandbox_session,
    get_scenario_byname,
    get_session,
    update_session_shell,
)
from services.user_service import get_user_by_id
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api")


class StateUpdate(BaseModel):
    state: str


class CommandSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected: bool = False
    options: list[str] = Field(default_factory=list)


class GameOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowPipes: bool = False
    rounds: int = Field(default=5, ge=1, le=20)


class SessionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    playType: Literal["SinglePlayer", "Versus"]
    gameType: str = Field(min_length=1)
    creatorID: int
    commands: Dict[str, CommandSelection] = Field(default_factory=dict)
    options: GameOptions


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config: SessionConfig


# ################### HELPERS ###################
# def populate_session_from_db(session_id: int, db: Session = Depends(get_db)):
#     ses_db = get_session(db, session_id)
#     if ses_db == None:
#         return {
#             "details": "Session does not exist"
#         }
#     ses = GameSession(str(session_id))
#     shells = get_session_shells(db, str(session_id))
#     for shell in shells:
#         p = Player()


################### ROUTERS ###################
@router.get("/sessions")
def list_sessions():
    return {
        "sessions": [
            {"id": sid, "players": len(session.players), "state": session.state}
            for sid, session in session_manager.sessions.items()
        ]
    }

@router.post("/session_create", status_code=201)
async def session_create(body: SessionCreate, db: Session = Depends(get_db)):
    """Persist a session and register its complete config with GameManager."""
    config = body.config

    if get_user_by_id(db, config.creatorID) is None:
        raise HTTPException(status_code=404, detail="Creator not found")

    scenario = get_scenario_byname(db, config.gameType)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Game type not found")

    initial_state = "running" if config.playType == "SinglePlayer" else "waiting"
    config_data = config.model_dump()
    runtime_session = None

    try:
        database_session = DatabaseGameSession(
            name=config.name,
            creatorID=config.creatorID,
            state=initial_state,
        )
        db.add(database_session)
        db.flush()

        runtime_session = session_manager.add_session(
            str(database_session.id), config.name
        )
        runtime_session.state = initial_state
        runtime_session.game_manager.set_config(config_data)

        db.add(
            ScenarioToSession(
                scenarioID=scenario.id,
                sessionID=database_session.id,
                config=runtime_session.game_manager.gen_config,
            )
        )
        db.add(
            SessionShell(
                SessionID=database_session.id,
                UserID=config.creatorID,
                shell=runtime_session.game_manager.get_shell(),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        if runtime_session is not None:
            await session_manager.remove_session(runtime_session.session_id)
        raise

    return {
        "session_id": database_session.id,
        "state": initial_state,
        "play_type": config.playType,
    }


@router.get("/session/{session_id}/join/{user_id}")
def session_join(session_id: str, user_id: str, db: Session = Depends(get_db)):
    session = session_manager.get_session(session_id)
    if (session == "404"):
        return {
            "details": "Session not found"
        }
    user = get_user_by_id(db, int(user_id))
    if (user is None or user.username is None):
        return {
            "details": "User not found"
        }
    session.requests.add(user.username)
    return None

@router.get("/session/{session_id}/accept/{user_id}")
def session_accept(session_id: str, user_id: str, db: Session = Depends(get_db)):
    # Get Session and User Data
    session = session_manager.get_session(session_id)
    if (session == "404"):
        return {
            "details": "Session not found"
        }
    user = get_user_by_id(db, int(user_id))
    if (user is None or user.username is None):
        return {
            "details": "User not found"
        }
    # Remove Request
    session.requests.remove(user.username)
    return None

@router.get("/session/{session_id}/decline/{user_id}")
def session_decline(session_id: str, user_id: str, db: Session = Depends(get_db)):
    session = session_manager.get_session(session_id)
    if (session == "404"):
        return {
            "details": "Session not found"
        }
    user = get_user_by_id(db, int(user_id))
    if (user is None or user.username is None):
        return {
            "details": "User not found"
        }
    session.requests.remove(user.username)
    return None

@router.post("/sandbox/{user_id}")
async def get_sandbox(user_id: str, db: Session = Depends(get_db)):
    # get sandbox from db if exist
    tut = get_sandbox_session(db, int(user_id))
    if tut is None:
        # Create a tutorial session
        sessionID = add_session(db, int(user_id), "Sandbox", "running")
        session = session_manager.add_session(str(sessionID), "Sandbox")
        # Generate tutorial config
        scenario = get_scenario_byname(db, "Tutorial")
        if scenario is None:
            return {"error": "No tutorial config"}
        config: dict = scenario.config or {}
        session.game_manger.set_config(config)
        # Add tutorial config to db
        add_session_scenario(db, sessionID, scenario.id, session.game_manger.gen_config)
        # Add user to tutorial session with shell gained from tutorial config to db
        add_session_shell(db, sessionID, int(user_id), session.game_manger.get_shell())
        return {"session_id": sessionID}
    else:
        # Tutorial Exists in db, bring to session manger if needed (add please)
        if session_manager.get_session(str(tut.id)) == "404":
            session = session_manager.add_session(str(tut.id), "Sandbox")
            session.state = "running"
        return {"session_id": tut.id}


@router.get("/shells")
async def get_shells(db: Session = Depends(get_db)):
    return {"shells": db.query(SessionShell).all()}


@router.post("/sessions/{session_id}/state")
async def update_session_state(session_id: str, body: StateUpdate):
    success = await session_manager.set_session_state(session_id, body.state)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid session or state")

    return {"session_id": session_id, "state": body.state}


@router.post("/sessions/{session_id}/save")
async def save_session_state(session_id: str, db: Session = Depends(get_db)):
    ses = session_manager.get_session(session_id)
    if ses == "404":
        return {"message": "sessionID does not exist"}
    for _username, player in ses.players.items():
        update_session_shell(
            db, int(session_id), int(player.user_id), player.serialize()
        )


@router.get("/scenarios")
async def get_scenarios(db: Session = Depends(get_db)):
    return {"scenarios": db.query(Scenario).all()}


@router.get("/session/{session_id}")
def get_session_data(session_id: int, db: Session = Depends(get_db)):
    session = session_manager.get_session(str(session_id))
    print(session)
    if session == "404":
        return {"details": "Not Found"}

    return {"details": "Found", "name": session.name, "state": session.state}


@router.get("/db/session/{session_id}")
def debug_session(session_id: int, db: Session = Depends(get_db)):
    # 1. Get session
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Get scenario mapping
    scenario_link = (
        db.query(ScenarioToSession)
        .filter(ScenarioToSession.sessionID == session_id)
        .first()
    )

    scenario = None
    if scenario_link:
        scenario = (
            db.query(Scenario).filter(Scenario.id == scenario_link.scenarioID).first()
        )

    # 3. Get all shells (players in session)
    shells = db.query(SessionShell).filter(SessionShell.SessionID == session_id).all()

    # 4. Build response
    return {
        "session": {
            "id": session.id,
            "name": session.name,
            "creatorID": session.creatorID,
            "state": session.state,
        },
        "scenario": {
            "id": scenario.id if scenario else None,
            "config": scenario_link.config if scenario_link else None,
            "base": scenario.config if scenario else None,
        },
        "players": [{"userID": s.UserID, "shell": s.shell} for s in shells],
    }
