from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from network.SessionManger import session_manager
from fastapi import Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.modals import GameSession, Scenario
from services.session_service import get_sandbox_session, add_session, get_scenario_byname, add_session_scenario, add_session_shell

router = APIRouter(prefix="/api")

class StateUpdate(BaseModel):
    state: str

@router.get("/sessions")
def list_sessions():
    return {
        "sessions": [
            {
                "id": sid,
                "players": len(session.players),
                "state": session.state
            }
            for sid, session in session_manager.sessions.items()
        ]
    }

@router.get("/session/{id}")
def get_session(id: str):
    session = session_manager.sessions.get(id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": id,
        "players": list(session.players.keys()),
        "state": session.state
    }

@router.post("/sandbox/{user_id}")
def get_sandbox(user_id: str, db: Session = Depends(get_db)):
    # get sandbox from db if exist
    tut = get_sandbox_session(db, int(user_id))
    if (tut == None):
        # Create a tutorial session
        sessionID = add_session(db, int(user_id), "Sandbox")
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
        if (session_manager.get_session(str(tut.id)) == "404"):
            session = session_manager.add_session(str(tut.id), "Sandbox")
        return {"session_id": tut.id}



@router.post("/sessions/{session_id}/state")
async def update_session_state(session_id: str, body: StateUpdate):
    success = await session_manager.set_session_state(session_id, body.state)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid session or state")

    return {
        "session_id": session_id,
        "state": body.state
    }

@router.get("/scenarios")
async def get_scenarios(db: Session = Depends(get_db)):
    return {
        "scenarios": db.query(Scenario).all()
    }