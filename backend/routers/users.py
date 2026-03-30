from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.modals import User
from pydantic import BaseModel
from db.authentication import create_access_token
from db.authentication import verify_password
from db.authentication import LoginRequest
from db.authentication import get_current_user, hash_password

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

router = APIRouter(prefix="/users", tags=["users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/me")
def get_me(user_id=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return

    return {
        "id": user.id,
        "username": user.username
    }


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id})

    return {"access_token": token}

# CREATE USER
@router.post("/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    hpassword = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, password=hpassword)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

# GET USERS
@router.get("/")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    return db.query(User).filter(User.id == user_id).first()

# UPDATE USER
@router.put("/{user_id}")
def update_user(user_id: int, username: str, email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    user.username = username
    user.email = email

    db.commit()
    db.refresh(user)

    return user

# DELETE USER
@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    db.delete(user)
    db.commit()

    return {"message": "deleted"}