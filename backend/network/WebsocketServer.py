from uuid import uuid4

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


def execute_terminal_input(session, player: Player, raw: str):
    """Run one new command or foreground response and build its wire payload."""
    if player.shell.foreground_pid:
        proc = session.process_manager.get_process(player.shell.foreground_pid)
        if proc and proc.program:
            stdout, stderr = proc.program.receive_input(raw)
            if proc.status == ProcessState.TERMINATED:
                player.shell.foreground_pid = None
                interaction = None
            else:
                interaction = {
                    "mode": "foreground",
                    "prompt": proc.program.prompt,
                }
            status = 1 if stderr else 0
        else:
            player.shell.foreground_pid = None
            stdout = []
            stderr = ["Foreground process is no longer available"]
            interaction = None
            status = 1
        input_kind = "foreground_input"
    else:
        result = session.commandline.enter_command(raw, player.shell)
        stdout, stderr = result.stdout, result.stderr
        status = result.status
        input_kind = "command"
        interaction = (
            None
            if not result.interaction
            else {
                "mode": result.interaction.mode,
                "prompt": result.interaction.prompt,
            }
        )

    return (
        {
            "type": "command_output",
            "stdout": stdout,
            "stderr": stderr,
            "cwd": get_current_path(player),
            "interaction": interaction,
        },
        status,
        input_kind,
    )


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
    username = "anonymous"
    user_id = "0"
    request_id = str(uuid4())
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
        session.logger.record_session_event(
            event="user_connected", user_id=user_id, username=username
        )

        while True:
            request_id = str(uuid4())
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                raise
            except Exception as error:
                session.logger.record_error(
                    request_id=request_id,
                    user_id=user_id,
                    username=username,
                    input_kind="websocket_message",
                    input_text="",
                    error=error,
                )
                session.logger.record_activity(
                    request_id=request_id,
                    user_id=user_id,
                    username=username,
                    input_kind="websocket_message",
                    input_text="",
                    cwd="/",
                    status=1,
                    interaction=None,
                    outcome="exception",
                    error_type=type(error).__name__,
                )
                await session.send_to(
                    websocket,
                    {
                        "type": "command_output",
                        "stdout": [],
                        "stderr": [
                            "Request failed unexpectedly. The error was "
                            "logged for this session."
                        ],
                        "cwd": "/",
                        "interaction": None,
                    },
                )
                continue

            if not isinstance(data, dict):
                session.logger.record_activity(
                    request_id=request_id,
                    user_id=user_id,
                    username=username,
                    input_kind="websocket_message",
                    input_text=repr(data),
                    cwd="/",
                    status=1,
                    interaction=None,
                    outcome="invalid_request",
                )
                await session.send_to(
                    websocket,
                    {
                        "type": "command_output",
                        "stdout": [],
                        "stderr": ["Invalid request"],
                        "cwd": "/",
                        "interaction": None,
                    },
                )
                continue

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
                input_text = raw if isinstance(raw, str) else repr(raw)
                input_kind = (
                    "foreground_input" if player.shell.foreground_pid else "command"
                )
                try:
                    response, status, input_kind = execute_terminal_input(
                        session, player, input_text
                    )
                except Exception as error:
                    session.logger.record_error(
                        request_id=request_id,
                        user_id=user_id,
                        username=username,
                        input_kind=input_kind,
                        input_text=input_text,
                        error=error,
                    )
                    session.logger.record_activity(
                        request_id=request_id,
                        user_id=user_id,
                        username=username,
                        input_kind=input_kind,
                        input_text=input_text,
                        cwd=player.shell.cwd or "/",
                        status=1,
                        interaction=None,
                        outcome="exception",
                        error_type=type(error).__name__,
                    )
                    if player.shell.foreground_pid:
                        proc = session.process_manager.get_process(
                            player.shell.foreground_pid
                        )
                        if proc:
                            proc.status = ProcessState.TERMINATED
                        player.shell.foreground_pid = None
                    response = {
                        "type": "command_output",
                        "stdout": [],
                        "stderr": [
                            "Command failed unexpectedly. The error was "
                            "logged for this session."
                        ],
                        "cwd": player.shell.cwd or "/",
                        "interaction": None,
                    }
                else:
                    session.logger.record_activity(
                        request_id=request_id,
                        user_id=user_id,
                        username=username,
                        input_kind=input_kind,
                        input_text=input_text,
                        cwd=response["cwd"],
                        status=status,
                        interaction=response["interaction"],
                    )
                await session.send_to(websocket, response)

    except WebSocketDisconnect:
        session.logger.record_session_event(
            event="user_disconnected", user_id=user_id, username=username
        )
        await session.disconnect(websocket)
    except Exception as error:
        session.logger.record_error(
            request_id=request_id,
            user_id=user_id,
            username=username,
            input_kind="websocket_request",
            input_text="",
            error=error,
        )
        session.logger.record_activity(
            request_id=request_id,
            user_id=user_id,
            username=username,
            input_kind="websocket_request",
            input_text="",
            cwd="/",
            status=1,
            interaction=None,
            outcome="exception",
            error_type=type(error).__name__,
        )
        try:
            await session.send_to(
                websocket,
                {
                    "type": "command_output",
                    "stdout": [],
                    "stderr": [
                        "Request failed unexpectedly. The error was "
                        "logged for this session."
                    ],
                    "cwd": "/",
                    "interaction": None,
                },
            )
        except Exception:
            pass
        await session.disconnect(websocket)
