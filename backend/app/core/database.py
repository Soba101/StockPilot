from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.security import decode_token

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Simple auth dependency (extract org and role)
bearer_scheme = HTTPBearer(auto_error=False)

def get_current_claims(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not creds:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    try:
        claims = decode_token(creds.credentials)
        return claims
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(*roles):
    def _inner(claims = Depends(get_current_claims)):
        if roles and claims.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return claims
    return _inner