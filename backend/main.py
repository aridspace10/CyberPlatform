from fastapi import FastAPI
from game.filesystem import FileSystem

app = FastAPI()

@app.get("/")
def health():
    return {"status": "ok"}