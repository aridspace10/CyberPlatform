import asyncio
from typing import Dict, Literal, Set

from fastapi import WebSocket
from game.commandline import CommandLine
from game.Events import ProcessTerminatedEvent
from game.filesystem import FileSystem
from game.GameManager import GameManager
from game.NetworkManager import NetworkManager
from game.ProcessManager import ProcessManager
from game.Scheduler import Scheduler
from game.ShellState import ShellState

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
            "fs": self.shell.fs.to_dict(),
        }


class GameSession:
    def __init__(self, session_id: str):
        # Basic Info
        self.session_id = session_id
        self.state = "waiting"
        self.name = "Test"

        # Player and Connecitons
        self.players: Dict[Username, Player] = {}
        self.connections: Dict[WebSocket, Username] = {}

        # Setup machine
        self.process_manager = ProcessManager()
        self.process_manager.boot()
        self.game_manager = GameManager()
        # Keep the old misspelled attribute working while callers migrate.
        self.game_manger = self.game_manager

        self.scheduler = Scheduler(self.process_manager)
        self.scheduler_task: asyncio.Task[None] | None = None

        self.network_manager = NetworkManager()

        self.commandline = CommandLine(self.process_manager, self.network_manager)

        self.requests: Set[Username] = set()

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
            "name": self.name,
            "gameData": self.game_manager.get_game_data(self.name),
        }

    async def scheduler_loop(self):
        while True:
            self.scheduler.tick()

            while self.process_manager.events:
                event = self.process_manager.events.pop(0)
                if isinstance(event, ProcessTerminatedEvent):
                    for player in self.players.values():
                        if player.shell.foreground_pid == event.process.pid:
                            player.shell.foreground_pid = None

                            if player.websocket:
                                await self.send_to(
                                    player.websocket,
                                    {
                                        "type": "terminal_state",
                                        "busy": False,
                                        "mode": None,
                                        "prompt": None,
                                    },
                                )

            await asyncio.sleep(1)

    def ensure_scheduler(self) -> asyncio.Task[None]:
        if self.scheduler_task is None or self.scheduler_task.done():
            self.scheduler_task = asyncio.create_task(self.scheduler_loop())
        return self.scheduler_task

    async def stop_scheduler(self) -> None:
        task = self.scheduler_task
        if task is None:
            return

        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.scheduler_task = None

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

        await self.broadcast(
            {"type": "system", "message": f"{username} joined session"}
        )

        await self.broadcast(self.lobby_state())

    async def disconnect(self, websocket: WebSocket):
        username = self.connections.pop(websocket, None)
        if not username:
            return

        player = self.players.get(username)
        if player and player.websocket is websocket:
            player.websocket = None

        await self.broadcast({"type": "system", "message": f"{username} disconnected"})

    async def broadcast(self, message: dict):
        dead = []

        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.connections.pop(ws, None)

    async def send_to(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}

    def get_session(self, session_id: str) -> GameSession | Literal["404"]:
        if session_id not in self.sessions:
            return "404"
        return self.sessions[session_id]

    def add_session(self, session_id: str, name: str):
        new_session = GameSession(session_id)
        new_session.name = name
        new_session.ensure_scheduler()
        self.sessions[session_id] = new_session
        return self.sessions[session_id]

    async def remove_session(self, session_id: str) -> bool:
        session = self.sessions.pop(session_id, None)
        if session is None:
            return False
        await session.stop_scheduler()
        return True

    async def set_session_state(self, session_id: str, new_state: str) -> bool:
        session = self.get_session(session_id)
        if not session or session == "404":
            return False

        await session.set_state(new_state)
        return True


session_manager = SessionManager()
