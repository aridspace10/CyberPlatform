from typing import Dict
from fastapi import WebSocket
from game.ShellState import ShellState

from game.filesystem import FileSystem
from game.commandline import CommandLine

class Player:
    def __init__(self, websocket: WebSocket, username: str):
        self.websocket = websocket
        self.username = username
        self.shell = ShellState()
        self.shell.fs = FileSystem()


class GameSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = "waiting"
        self.name = "Test"
        self.players: Dict[WebSocket, Player] = {}
        self.cmd = CommandLine()

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

    async def connect(self, websocket: WebSocket, username: str):
        self.players[websocket] = Player(websocket, username)

        await self.broadcast({
            "type": "system",
            "message": f"{username} joined session"
        })

        await self.broadcast(self.lobby_state())

    async def disconnect(self, websocket: WebSocket):
        player = self.players.get(websocket)
        if player:
            del self.players[websocket]

            await self.broadcast({
                "type": "system",
                "message": f"{player.username} left session"
            })

            await self.broadcast(self.lobby_state())

    async def broadcast(self, message: dict):
        for player in self.players.values():
            await player.websocket.send_json(message)

    async def send_to(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}

    def get_session(self, session_id: str) -> GameSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = GameSession(session_id)
        return self.sessions[session_id]
    
    async def set_session_state(self, session_id: str, new_state: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False

        await session.set_state(new_state)
        return True

session_manager = SessionManager()
