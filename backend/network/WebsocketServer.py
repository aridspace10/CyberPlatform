from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .SessionManger import session_manager

router = APIRouter()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()

    session = session_manager.get_session(session_id)

    try:
        # Expect join packet first
        join_data = await websocket.receive_json()
        username = join_data.get("username", "anonymous")

        await session.connect(websocket, username)

        while True:
            data = await websocket.receive_json()

            msg_type = data.get("type")
            if msg_type == "chat":
                await session.broadcast({
                    "type": "chat",
                    "user": username,
                    "message": data.get("message", "")
                })

            elif msg_type == "command":

                player = session.players.get(websocket)

                if not player:
                    continue

                raw = data.get("input", "")

                stdout, stderr = session.cmd.enter_command(
                    raw,
                    player.shell
                )

                await session.send_to(websocket, {
                    "type": "command_output",
                    "stdout": stdout,
                    "stderr": stderr
                })

    except WebSocketDisconnect:
        session.disconnect(websocket)
