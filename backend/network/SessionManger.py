from typing import Dict, Literal
from fastapi import WebSocket
from game.ShellState import ShellState
from game.GameManager import GameManager
from game.filesystem import FileSystem
from game.commandline import CommandLine

Username = str

class Player:
    def __init__(self, websocket: WebSocket | None, username: str, user_id: str):
        self.websocket = websocket
        self.username = username
        self.user_id = user_id
        self.shell = ShellState()
        self.shell.fs = FileSystem()

    def serialize(self) -> dict:
        return {
            "vars": self.shell.vars,
            "cmds": self.shell.commands,
            "fs": self.shell.fs.to_dict()
        }

class GameSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = "waiting"
        self.name = "Test"

        self.players: Dict[Username, Player] = {}
        self.connections: Dict[WebSocket, Username] = {}
        self.cmd = CommandLine()
        self.game_manger: GameManager = GameManager()
    
    def __str__(self) -> str:
        return f"SessionID: {self.session_id}, name: {self.name}, state: {self.state}"

    def get_player(self, websocket: WebSocket) -> Player | None:
        username = self.connections.get(websocket)
        if not username:
            return None
        return self.players.get(username)

    def lobby_state(self) -> dict:
        return {
            "type": "lobby_update",
            "players": [p.username for p in self.players.values()],
            "state": self.state,
            "session": self.session_id,
            "name": self.name
        }

    async def set_state(self, new_state: str):
        self.state = new_state
        await self.broadcast(self.lobby_state())

    async def connect(self, websocket: WebSocket, username: str, user_id: str):
        self.connections[websocket] = username

        if username not in self.players:
            # First time joining
            self.players[username] = Player(websocket, username, user_id)
        else:
            # Reconnecting
            self.players[username].websocket = websocket

        await self.broadcast({
            "type": "system",
            "message": f"{username} joined session"
        })

        await self.broadcast(self.lobby_state())

    async def disconnect(self, websocket: WebSocket):
        username = self.connections.pop(websocket, None)
        if not username:
            return 

        await self.broadcast({
            "type": "system",
            "message": f"{username} disconnected"
        })

    async def broadcast(self, message: dict):
        dead = []

        for ws in self.connections:
            try:
                await ws.send_json(message)
            except:
                dead.append(ws)

        for ws in dead:
            self.connections.pop(ws, None)

    async def send_to(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)

    async def handle_message(self, websocket: WebSocket, data: dict):
        player = self.players.get(websocket)
        if not player:
            return

        msg_type = data.get("type")

        if msg_type == "command":
            await self._handle_command(player, data.get("command", ""))

        elif msg_type == "chat":
            await self.broadcast({
                "type": "chat",
                "user": player.username,
                "message": data.get("message", "")
            })
    
    async def _handle_command(self, player: Player, command: str):
        stdout, stderr = self.cmd.enter_command(command, player.shell)

        await player.websocket.send_json({
            "type": "command_result",
            "stdout": stdout,
            "stderr": stderr,
            "cwd": player.shell.cwd
        })


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}

    def get_session(self, session_id: str) -> GameSession | Literal["404"]:
        if session_id not in self.sessions:
            return "404"
        return self.sessions[session_id]
    
    def add_session(self, session_id: str, name: str):
        # 1.Setup Session
        new_session = GameSession(session_id) 
        new_session.name = name
        # 2. Assign to session manger array
        self.sessions[session_id] = new_session
        return self.sessions[session_id]
    
    async def set_session_state(self, session_id: str, new_state: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False

        await session.set_state(new_state)
        return True

session_manager = SessionManager()
