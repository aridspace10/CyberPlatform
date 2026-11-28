import os
from contextlib import asynccontextmanager

from api.sessions import router as sessions_router
from db.seed import seed_db
from db.session import Base, SessionLocal, engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from network.WebsocketServer import router as websocket_router
from routers import contact, users
from services.single_worker import single_game_worker


@asynccontextmanager
async def lifespan(app: FastAPI):

    # startup
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_db(db, local_dev_login=getattr(app.state, "local_dev_login", False))
    finally:
        db.close()

    yield

    # shutdown
    pass


@asynccontextmanager
async def single_worker_lifespan(app: FastAPI):
    with single_game_worker():
        async with lifespan(app):
            yield


app = FastAPI(lifespan=single_worker_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get(
            "CYBERPLATFORM_CORS_ORIGINS", "http://localhost:5173"
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket_router)
app.include_router(sessions_router)
app.include_router(users.router)
app.include_router(contact.router)


@app.get("/")
def root():
    return {"status": "CyberPlatform backend running"}
