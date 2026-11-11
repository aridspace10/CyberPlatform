import os
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import jwt
from passlib.context import CryptContext

### Schemas ####
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str


### JWT handling ###
SECRET_KEY = os.environ.get("CYBERPLATFORM_JWT_SECRET") or secrets.token_urlsafe(32)
ALGORITHM = "HS256"


def create_access_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=12)
    payload["sub"] = str(payload["sub"])
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


def get_current_user(token=Depends(security)):
    try:
        payload = decode_token(token.credentials)
        return int(payload["sub"])  # <-- convert back to int for DB query
    except Exception as e:
        print(f"Token error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token") from e
