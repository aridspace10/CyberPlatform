from fastapi import APIRouter
from network.SessionManger import session_manager

router = APIRouter(prefix="/api")

@router.get("/sessions")
def list_sessions():
    return {
        "sessions": [
            {
                "id": sid,
                "players": len(session.players)
            }
            for sid, session in session_manager.sessions.items()
        ]
    }