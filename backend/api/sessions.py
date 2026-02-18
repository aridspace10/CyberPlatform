from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from network.SessionManger import session_manager

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


@router.post("/sessions/{session_id}/state")
async def update_session_state(session_id: str, body: StateUpdate):
    success = await session_manager.set_session_state(session_id, body.state)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid session or state")

    return {
        "session_id": session_id,
        "state": body.state
    }