from fastapi import FastAPI
from network.WebsocketServer import router as websocket_router
from api.sessions import router as sessions_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket_router)
app.include_router(sessions_router)

@app.get("/")
def root():
    return {"status": "CyberPlatform backend running"}