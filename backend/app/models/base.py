from sqlalchemy import Column, DateTime, func, String
try:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    USE_NATIVE_UUID = True
except ImportError:  # pragma: no cover
    PG_UUID = None  # type: ignore
    USE_NATIVE_UUID = False
import uuid

class BaseModel:
    __abstract__ = True
    
    # Backend‑agnostic UUID primary key (UUID type where available, else String)
    if USE_NATIVE_UUID and PG_UUID is not None:
        UUIDType = PG_UUID
        id = Column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    else:
        # Provide a pseudo UUID type for SQLite as simple CHAR(36)
        from sqlalchemy import CHAR
        UUIDType = CHAR  # type: ignore
        id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())