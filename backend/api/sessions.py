import json
from datetime import datetime
from typing import Dict, Literal

from db.authentication import decode_token, get_current_user
from db.modals import GameSession as DatabaseGameSession
from db.modals import JoinRequest, Scenario, ScenarioToSession, SessionShell
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from game.GameManager import QUESTION_MODES
from jose import JWTError
from network.SessionManger import session_manager
from pydantic import BaseModel, ConfigDict, Field
from services.session_logging import SessionLogger
from services.session_service import (
    add_session,
    add_session_scenario,
    add_session_shell,
    get_sandbox_session,
    get_scenario_byname,
    get_session,
    update_session_shell,
)
from services.user_service import get_user_by_id, is_friend
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api")


def friend_scope_allows(db: Session, session: DatabaseGameSession, user_id: int):
    return (
        session.visibility != "friends_only"
        or user_id == session.creatorID
        or is_friend(db, user_id, session.creatorID)
    )


def require_session_member(db: Session, session_id: int, user_id: int):
    """Return the session only while this user may access its saved state."""
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if db.get(SessionShell, (session_id, user_id)) is None or not friend_scope_allows(
        db, session, user_id
    ):
        raise HTTPException(
            status_code=403, detail="You are not a member of this session"
        )
    return session


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
    questionCount: int = Field(default=10, ge=1, le=50)
    timeLimitSeconds: int = Field(default=300, ge=30, le=3600)


class SessionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    playType: Literal["SinglePlayer", "Versus"]
    gameType: str = Field(min_length=1)
    visibility: Literal["public", "private", "friends_only"] = "public"
    creatorID: int | None = None
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
def list_sessions(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db),
):
    user_id = None
    if credentials is not None:
        try:
            user_id = int(decode_token(credentials.credentials)["sub"])
        except (JWTError, KeyError, TypeError, ValueError):
            pass
    sessions = []
    for sid, runtime in session_manager.sessions.items():
        if runtime.is_sandbox or not sid.isdecimal():
            continue
        saved = get_session(db, int(sid))
        if saved is None:
            continue
        member = (
            user_id is not None
            and db.get(SessionShell, (saved.id, user_id)) is not None
        )
        if not member and (
            runtime.game_manager.play_type != "Versus"
            or runtime.state != "waiting"
            or db.query(SessionShell).filter_by(SessionID=saved.id).count() >= 2
        ):
            continue
        if saved.visibility == "private" and not member:
            continue
        if saved.visibility == "friends_only" and (
            user_id is None or not friend_scope_allows(db, saved, user_id)
        ):
            continue
        sessions.append(
            {
                "id": sid,
                "name": saved.name,
                "players": len(runtime.connected_players()),
                "state": runtime.state,
                "visibility": saved.visibility,
            }
        )
    return {"sessions": sessions}


@router.post("/session_create", status_code=201)
async def session_create(
    body: SessionCreate,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persist a session and register its complete config with GameManager."""
    config = body.config

    if get_user_by_id(db, user_id) is None:
        raise HTTPException(status_code=404, detail="Creator not found")

    scenario = get_scenario_byname(db, config.gameType)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Game type not found")
    selected_commands = {
        name for name, selection in config.commands.items() if selection.selected
    }
    if config.gameType == "MiniGames" and not selected_commands:
        raise HTTPException(status_code=422, detail="Select grep or sed for MiniGames")
    if config.gameType == "MiniGames" and selected_commands - {"grep", "sed"}:
        raise HTTPException(
            status_code=422,
            detail="Only grep and sed questions are available",
        )
    if config.gameType == "MiniGames" and config.options.questionCount < len(
        selected_commands
    ):
        raise HTTPException(
            status_code=422,
            detail="Questions per round must cover each selected command",
        )
    for command in selected_commands & set(QUESTION_MODES):
        unknown_options = set(config.commands[command].options) - set(
            QUESTION_MODES[command]
        )
        if unknown_options:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported {command} option: {sorted(unknown_options)[0]}",
            )

    initial_state = "running" if config.playType == "SinglePlayer" else "waiting"
    config_data = config.model_dump()
    config_data["creatorID"] = user_id
    runtime_session = None

    try:
        database_session = DatabaseGameSession(
            name=config.name,
            creatorID=user_id,
            state=initial_state,
            visibility=config.visibility,
        )
        db.add(database_session)
        db.flush()

        runtime_session = session_manager.add_session(
            str(database_session.id), config.name
        )
        runtime_session.state = initial_state
        runtime_session.game_manager.set_config(config_data)
        if config.playType == "SinglePlayer" and config.gameType == "MiniGames":
            runtime_session.game_manager.start_round([str(user_id)])

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
                UserID=user_id,
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
        "visibility": config.visibility,
    }


@router.post("/session/{session_id}/requests", status_code=201)
def request_session_join(
    session_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.visibility != "private":
        raise HTTPException(
            status_code=400, detail="This session does not need approval"
        )
    scenario = db.query(ScenarioToSession).filter_by(sessionID=session_id).first()
    config = scenario.config if scenario else {}
    if isinstance(config, str):
        config = json.loads(config)
    if config.get("playType") != "Versus":
        raise HTTPException(
            status_code=403, detail="Single-player sessions cannot be joined"
        )
    if db.get(SessionShell, (session_id, user_id)) is not None:
        return {"status": "approved"}
    active = session_manager.get_session(str(session_id))
    state = active.state if active != "404" else session.state
    if (
        state != "waiting"
        or db.query(SessionShell).filter_by(SessionID=session_id).count() >= 2
    ):
        raise HTTPException(
            status_code=409, detail="Session is full or already started"
        )
    request = db.get(JoinRequest, (session_id, user_id))
    if request is None:
        db.add(
            JoinRequest(SessionID=session_id, UserID=user_id, date=datetime.utcnow())
        )
        db.commit()
    return {"status": "pending"}


@router.get("/session/{session_id}/access")
def session_access(
    session_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    scenario = db.query(ScenarioToSession).filter_by(sessionID=session_id).first()
    config = scenario.config if scenario else {}
    if isinstance(config, str):
        config = json.loads(config)
    member = db.get(SessionShell, (session_id, user_id)) is not None
    pending = db.get(JoinRequest, (session_id, user_id)) is not None
    runtime = session_manager.get_session(str(session_id))
    state = runtime.state if runtime != "404" else session.state
    member_count = db.query(SessionShell).filter_by(SessionID=session_id).count()
    if (
        session.visibility == "friends_only"
        and user_id != session.creatorID
        and not is_friend(db, user_id, session.creatorID)
    ):
        status = "denied"
    elif member:
        status = "member"
    elif (
        config.get("playType") == "SinglePlayer"
        or state != "waiting"
        or member_count >= 2
    ):
        status = "denied"
    elif session.visibility == "private":
        status = "pending" if pending else "requestable"
    else:
        status = "joinable"
    return {
        "name": session.name,
        "visibility": session.visibility,
        "status": status,
        "is_host": session.creatorID == user_id,
    }


@router.get("/session/{session_id}/requests")
def list_session_requests(
    session_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.creatorID != user_id:
        raise HTTPException(status_code=403, detail="Only the host can view requests")
    requests = db.query(JoinRequest).filter(JoinRequest.SessionID == session_id).all()
    return {
        "requests": [
            {"user_id": request.UserID, "username": user.username}
            for request in requests
            if (user := get_user_by_id(db, request.UserID)) is not None
        ]
    }


@router.post("/session/{session_id}/requests/{requester_id}/accept")
def accept_session_request(
    session_id: int,
    requester_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.creatorID != user_id:
        raise HTTPException(status_code=403, detail="Only the host can accept requests")
    request = db.get(JoinRequest, (session_id, requester_id))
    if request is None:
        raise HTTPException(status_code=404, detail="Join request not found")
    active = session_manager.get_session(str(session_id))
    state = active.state if active != "404" else session.state
    if (
        state != "waiting"
        or db.query(SessionShell).filter_by(SessionID=session_id).count() >= 2
    ):
        raise HTTPException(
            status_code=409, detail="Session is full or already started"
        )
    scenario = db.query(ScenarioToSession).filter_by(sessionID=session_id).first()
    if scenario is None:
        raise HTTPException(status_code=409, detail="Session configuration unavailable")
    runtime = session_manager.get_session(str(session_id))
    if runtime == "404":
        runtime = session_manager.add_session(str(session_id), session.name or "")
        runtime.state = session.state or "waiting"
        runtime.game_manager.set_config(scenario.config)
    db.add(
        SessionShell(
            SessionID=session_id,
            UserID=requester_id,
            shell=runtime.game_manager.get_shell(),
        )
    )
    db.delete(request)
    db.commit()
    return {"status": "approved"}


@router.post("/session/{session_id}/requests/{requester_id}/decline")
def decline_session_request(
    session_id: int,
    requester_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.creatorID != user_id:
        raise HTTPException(
            status_code=403, detail="Only the host can decline requests"
        )
    request = db.get(JoinRequest, (session_id, requester_id))
    if request is None:
        raise HTTPException(status_code=404, detail="Join request not found")
    db.delete(request)
    db.commit()
    return {"status": "declined"}


@router.post("/sandbox/{user_id}")
async def get_sandbox(
    user_id: str,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if str(current_user_id) != user_id:
        raise HTTPException(
            status_code=403, detail="You cannot create another user's sandbox"
        )
    # get sandbox from db if exist
    tut = get_sandbox_session(db, int(user_id))
    if tut is None:
        # Create a tutorial session
        sessionID = add_session(db, int(user_id), "Sandbox", "running")
        session = session_manager.add_session(str(sessionID), "Sandbox")
        session.is_sandbox = True
        session.state = "running"
        # Generate tutorial config
        scenario = get_scenario_byname(db, "Tutorial")
        if scenario is None:
            return {"error": "No tutorial config"}
        config = scenario.config or {}
        if isinstance(config, str):
            config = json.loads(config)
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
            session.is_sandbox = True
        else:
            session_manager.get_session(str(tut.id)).is_sandbox = True
        return {"session_id": tut.id}


@router.get("/shells")
async def get_shells(
    user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    shells = db.query(SessionShell).filter_by(UserID=user_id).all()
    return {
        "shells": [
            shell
            for shell in shells
            if (session := get_session(db, shell.SessionID)) is not None
            and friend_scope_allows(db, session, user_id)
        ]
    }


@router.post("/sessions/{session_id}/state")
async def update_session_state(
    session_id: str,
    body: StateUpdate,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    database_session = get_session(db, int(session_id))
    if database_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if database_session.creatorID != user_id:
        raise HTTPException(
            status_code=403, detail="Only the host can change session state"
        )
    success = await session_manager.set_session_state(session_id, body.state)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid session or state")

    return {"session_id": session_id, "state": body.state}


@router.post("/sessions/{session_id}/save")
async def save_session_state(
    session_id: str,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_session_member(db, int(session_id), user_id)
    ses = session_manager.get_session(session_id)
    if ses == "404":
        raise HTTPException(status_code=404, detail="Session not found")
    player = next(
        (player for player in ses.players.values() if int(player.user_id) == user_id),
        None,
    )
    if player is not None:
        update_session_shell(db, int(session_id), user_id, player.serialize())
    return {"status": "saved"}


@router.get("/scenarios")
async def get_scenarios(db: Session = Depends(get_db)):
    return {"scenarios": db.query(Scenario).all()}


@router.get("/session/{session_id}")
def get_session_data(
    session_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_session_member(db, session_id, user_id)
    session = session_manager.get_session(str(session_id))
    if session == "404":
        raise HTTPException(status_code=404, detail="Session not found")

    game_data = session.game_manager.get_game_data(session.name, str(user_id))
    game_data["isSandbox"] = session.is_sandbox
    return {
        "details": "Found",
        "name": session.name,
        "state": session.state,
        "gameData": game_data,
    }


@router.get("/session/{session_id}/diagnostics")
def download_session_diagnostics(
    session_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_session_member(db, session_id, user_id)

    runtime_session = session_manager.get_session(str(session_id))
    logger = (
        runtime_session.logger
        if runtime_session != "404"
        else SessionLogger(str(session_id))
    )
    archive = logger.export_user_archive(str(user_id))
    return Response(
        content=archive,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="session-{session_id}-diagnostics.zip"'
            )
        },
    )


@router.get("/db/session/{session_id}")
def debug_session(
    session_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. Get session
    session = require_session_member(db, session_id, user_id)

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
    own_shell = db.get(SessionShell, (session_id, user_id))

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
        "players": [{"userID": own_shell.UserID, "shell": own_shell.shell}],
    }
