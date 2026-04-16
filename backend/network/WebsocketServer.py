from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .SessionManger import session_manager, GameSession, Player
from services.session_service import get_session, get_session_shell
from sqlalchemy.orm import Session
from fastapi import Depends
from db.session import get_db
from game.ShellState import CommandHistory

router = APIRouter()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, db: Session = Depends(get_db)):
    await websocket.accept()
    session = session_manager.get_session(session_id)
    if session == "404":
        ses_db = get_session(db, int(session_id))
        if (ses_db == None):
            await websocket.close()
            return
        session = GameSession(str(session_id))
        session.name = ses_db.name if ses_db.name is not None else ""
        session.state = ses_db.state if ses_db.state is not None else ""
        print (session.state)
    try:
        # Expect join packet first
        join_data = await websocket.receive_json()
        username = join_data.get("username", "anonymous")
        user_id = join_data.get("userID", "0")

        if username not in session.players:
            shell_db = get_session_shell(db, session_id, user_id)
            if shell_db and shell_db.shell:
                player = Player(websocket, username, user_id)
                shell = shell_db.shell
                ch = CommandHistory()
                ch.commands = shell["cmds"]
                player.shell.commands = CommandHistory()
                player.shell.vars = shell["vars"]
                player.shell.fs.from_dict(shell["fs"])
                session.players[username] = player
            else:
                pass
                # IMPLEMENT JOIN REQUEST FUTURE JACKSON
        await session.connect(websocket, username, user_id)

        while True:
            data = await websocket.receive_json()
            print(f"Received message: {data}")

            msg_type = data.get("type")
            if msg_type == "chat":
                await session.broadcast({
                    "type": "chat",
                    "user": username,
                    "message": data.get("message", "")
                })

            elif msg_type == "command":
                
                player = session.players.get(username)
                if not player:
                    continue

                raw = data.get("input", "")
                player.shell.commands.add(raw)

                stdout, stderr = session.cmd.enter_command(
                    raw,
                    player.shell
                )

                if (player.shell.ls == -1): # Interactive command
                    await session.send_to(websocket, {
                        "type": "command_output",
                        "return_type": 1,
                        "stdout": stdout,
                        "stderr": stderr
                    })
                else:
                    await session.send_to(websocket, {
                        "type": "command_output",
                        "return_type": 0,
                        "stdout": stdout,
                        "stderr": stderr
                    })

    except WebSocketDisconnect:
        session.disconnect(websocket)
