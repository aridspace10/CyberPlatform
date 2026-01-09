from fastapi import APIRouter
from pydantic import BaseModel
from game.commandline import CommandLine
from game.filesystem import FileSystem

router = APIRouter()

# TEMP: single filesystem (we’ll make this per-user later)
fs = FileSystem()
cl = CommandLine()

class CommandRequest(BaseModel):
    command: str

@router.post("/command")
def execute_command(req: CommandRequest):
    stdout, stderr = cl.enter_command(req.command, fs)
    return {
        "stdout": stdout,
        "stderr": stderr
    }
