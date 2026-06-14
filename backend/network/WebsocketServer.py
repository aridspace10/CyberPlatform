from db.session import get_db
from faker import Faker
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from game.filesystem import FileNode
from game.inode import Inode, NodeType
from network.SessionManger import Player, session_manager
from services.session_service import get_session, get_session_shell
from sqlalchemy.orm import Session

fake = Faker()

router = APIRouter()


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
        print("Scheduler ensured")
        # Expect join packet first
        join_data = await websocket.receive_json()
        username = join_data.get("username", "anonymous")
        user_id = join_data.get("userID", "0")

        if username not in session.players:
            shell_db = get_session_shell(db, session_id, user_id)
            if shell_db and shell_db.shell:
                player = Player(websocket, username, user_id)
                shell = shell_db.shell
                print(shell)
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
            print(f"Received message: {data}")

            msg_type = data.get("type")
            if msg_type == "chat":
                await session.broadcast(
                    {
                        "type": "chat",
                        "user": username,
                        "message": data.get("message", ""),
                    }
                )

            elif msg_type == "add_random_file":
                # Used for testing
                player = session.players.get(username)
                inode = Inode(NodeType.FILE)
                inode.data = fake.paragraph().split("\n")
                fn = FileNode(
                    session.players[username].shell.fs.current, fake.word(), inode
                )
                session.players[username].shell.fs.add_file(".", fn)

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
                        proc.program.receive_input(raw)

                else:
                    print("before enter_command")

                    cmd = session.commandline.enter_command(raw, player.shell)

                    print("after enter_command")

                    await session.send_to(
                        websocket,
                        {
                            "type": "command_output",
                            "stdout": cmd.stdout,
                            "stderr": cmd.stderr,
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
