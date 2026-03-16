from jose import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

### Schemas ####
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str

### JWT handling ###
SECRET_KEY = "ccf447dfd8df5287991ef5ceb9a2f26c452bbf25eeb63d25c4e951783e5e2cf4"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=12)

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

#### Password handling
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

### route protections
security = HTTPBearer()

def get_current_user(token = Depends(security)):
    try:
        payload = decode_token(token.credentials)
        return payload["sub"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")