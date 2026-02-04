from fastapi import FastAPI
from network.WebsocketServer import router as websocket_router
from api.sessions import router as sessions_router

app = FastAPI()

app.include_router(websocket_router)
app.include_router(sessions_router)

@app.get("/")
def root():
    return {"status": "CyberPlatform backend running"}