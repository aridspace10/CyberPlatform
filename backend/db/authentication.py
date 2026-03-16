from jose import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext

### JWT handling ###
SECRET_KEY = "ccf447dfd8df5287991ef5ceb9a2f26c452bbf25eeb63d25c4e951783e5e2cf4"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=12)

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])