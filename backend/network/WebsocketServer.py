from db.session import get_db
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from game.ProcessManager import ProcessState
from network.SessionManger import Player, session_manager
from services.session_service import get_session, get_session_shell
from sqlalchemy.orm import Session

router = APIRouter()


def get_current_path(player: Player) -> str:
    """Return the player's current filesystem path for the terminal prompt."""
    parts: list[str] = []
    node = player.shell.fs.current
    while node is not None:
        if node.name:
            parts.append(node.name)
        node = node.parent
    return "/" + "/".join(reversed(parts))


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket, session_id: str, db: Session = Depends(get_db)
):
    await websocket.accept()
    session = session_manager.get_session(session_id)
    if session == "404":
        ses_db = get_session(db, int(session_id))
        if ses_db is None:
            await websocket.close()
            return
        session = session_manager.add_session(
            session_id, ses_db.name if ses_db.name else ""
        )
    try:
        session.ensure_scheduler()
        # Expect join packet first
        join_data = await websocket.receive_json()
        username = join_data.get("username", "anonymous")
        user_id = join_data.get("userID", "0")

        if username not in session.players:
            shell_db = get_session_shell(db, session_id, user_id)
            if shell_db and shell_db.shell:
                player = Player(websocket, username, user_id)
                shell = shell_db.shell
                player.shell.commands = shell["cmds"]
                player.shell.vars = shell["vars"]
                player.shell.fs.from_dict(shell["fs"])
                session.players[username] = player
            else:
                pass
                # IMPLEMENT JOIN REQUEST FUTURE JACKSON
        await session.connect(websocket, username, user_id)

        while True:
            data = await websocket.receive_json()

            msg_type = data.get("type")
            if msg_type == "chat":
                await session.broadcast(
                    {
                        "type": "chat",
                        "user": username,
                        "message": data.get("message", ""),
                    }
                )

            elif msg_type == "command":

                player = session.players.get(username)

                if not player:
                    continue

                raw = data.get("input", "")

                if player.shell.foreground_pid:
                    proc = session.process_manager.get_process(
                        player.shell.foreground_pid
                    )

                    if proc and proc.program:
                        stdout, stderr = proc.program.receive_input(raw)
                        if proc.status == ProcessState.TERMINATED:
                            player.shell.foreground_pid = None
                            await session.send_to(
                                websocket,
                                {
                                    "type": "command_output",
                                    "stdout": stdout,
                                    "stderr": stderr,
                                    "cwd": get_current_path(player),
                                    "interaction": None,
                                },
                            )
                        else:
                            await session.send_to(
                                websocket,
                                {
                                    "type": "command_output",
                                    "stdout": stdout,
                                    "stderr": stderr,
                                    "cwd": get_current_path(player),
                                    "interaction": {
                                        "mode": "foreground",
                                        "prompt": proc.program.prompt,
                                    },
                                },
                            )
                    else:
                        player.shell.foreground_pid = None
                        await session.send_to(
                            websocket,
                            {
                                "type": "command_output",
                                "stdout": [],
                                "stderr": ["Foreground process is no longer available"],
                                "cwd": get_current_path(player),
                                "interaction": None,
                            },
                        )
                else:
                    cmd = session.commandline.enter_command(raw, player.shell)

                    await session.send_to(
                        websocket,
                        {
                            "type": "command_output",
                            "stdout": cmd.stdout,
                            "stderr": cmd.stderr,
                            "cwd": get_current_path(player),
                            "interaction": (
                                None
                                if not cmd.interaction
                                else {
                                    "mode": cmd.interaction.mode,
                                    "prompt": cmd.interaction.prompt,
                                }
                            ),
                        },
                    )

    except WebSocketDisconnect:
        await session.disconnect(websocket)
