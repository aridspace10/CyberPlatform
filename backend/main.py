from fastapi import FastAPI
from network.WebsocketServer import router as websocket_router
from api.sessions import router as sessions_router
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from db.session import engine, Base
from routers import users
from db.seed import seed_db
from db.session import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):

    # startup
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_db(db)  # ✅ run once on startup
    finally:
        db.close()

    yield

    # shutdown
    pass


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket_router)
app.include_router(sessions_router)
app.include_router(users.router)


@app.get("/")
def root():
    return {"status": "CyberPlatform backend running"}
