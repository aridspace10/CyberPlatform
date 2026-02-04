from fastapi import FastAPI
from network.WebsocketServer import router as websocket_router

app = FastAPI()

app.include_router(websocket_router)

@app.get("/")
def root():
    return {"status": "CyberPlatform backend running"}