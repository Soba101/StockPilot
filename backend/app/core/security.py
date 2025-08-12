import os
import datetime as dt
from typing import Optional, Any
from jose import jwt
from passlib.context import CryptContext

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-change-me")
JWT_ALG = "HS256"
ACCESS_MINUTES = int(os.getenv("ACCESS_MINUTES", "15"))
REFRESH_DAYS = int(os.getenv("REFRESH_DAYS", "7"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def create_access_token(sub: Optional[str] = None, org_id: Optional[str] = None, role: str = "user", **kwargs: Any) -> str:
    """Create an access JWT.

    Backwards compatibility: some tests call with user_id= instead of sub=.
    We accept either and normalize to JWT 'sub'. If org_id missing, raise ValueError.
    """
    # Accept alias user_id
    if sub is None:
        sub = kwargs.get("user_id")
    if sub is None:
        raise ValueError("sub (or user_id) is required")
    if org_id is None:
        org_id = kwargs.get("org_id")
    if org_id is None:
        raise ValueError("org_id is required")
    now = dt.datetime.utcnow()
    payload = {
        "sub": sub,
        "org": org_id,
        "role": role,
        "iat": now,
        "exp": now + dt.timedelta(minutes=ACCESS_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def create_refresh_token(sub: str) -> str:
    now = dt.datetime.utcnow()
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + dt.timedelta(days=REFRESH_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])


