from fastapi import APIRouter
from pydantic import BaseModel
from game.commandline import CommandLine
from game.filesystem import FileSystem
from game.ShellState import ShellState

router = APIRouter()

# TEMP: single filesystem (we’ll make this per-user later)
shell = ShellState()
shell.fs = FileSystem()
cl = CommandLine()

class CommandRequest(BaseModel):
    command: str

@router.post("/command")
def execute_command(req: CommandRequest):
    stdout, stderr = cl.enter_command(req.command, shell)
    return {
        "stdout": stdout,
        "stderr": stderr
    }
