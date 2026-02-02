from fastapi import FastAPI
from game.filesystem import FileSystem
from fastapi.middleware.cors import CORSMiddleware
from game.commandline import CommandLine
from game.ShellState import ShellState

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

cmd = CommandLine()
shell = ShellState()
shell.fs = FileSystem()
shell.fs.setup_system("filesystems/example.txt")
print(cmd.enter_command("cd d1 && ls", shell))

@app.get("/")
def health():
    return {"status": "ok"}