from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.modals import User
from pydantic import BaseModel

class SessionCreate(BaseModel):
    username: str
    email: str

router = APIRouter(prefix="/sessions", tags=["sessions"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CREATE USER
@router.post("/")
def create_session(ses_data: SessionCreate, db: Session = Depends(get_db)):
    pass

# GET USERS
@router.get("/")
def get_session(db: Session = Depends(get_db)):
    return db.query(User).all()

# UPDATE USER
@router.put("/{session_id}")
def update_ses(db: Session = Depends(get_db)):
    pass