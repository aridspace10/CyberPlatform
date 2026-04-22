from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from network.SessionManger import session_manager
from fastapi import Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.modals import Scenario, ScenarioToSession, SessionShell
from services.session_service import (
    get_session,
    get_sandbox_session,
    add_session,
    get_scenario_byname,
    add_session_scenario,
    add_session_shell,
    update_session_shell,
)

router = APIRouter(prefix="/api")


class StateUpdate(BaseModel):
    state: str


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


@router.post("/sandbox/{user_id}")
def get_sandbox(user_id: str, db: Session = Depends(get_db)):
    # get sandbox from db if exist
    tut = get_sandbox_session(db, int(user_id))
    if tut == None:
        # Create a tutorial session
        sessionID = add_session(db, int(user_id), "Sandbox", "running")
        session = session_manager.add_session(str(sessionID), "Sandbox")
        # Generate tutorial config
        scenario = get_scenario_byname(db, "Tutorial")
        if scenario == None:
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
    for username, player in ses.players.items():
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
