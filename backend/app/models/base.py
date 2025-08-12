from sqlalchemy import Column, DateTime, func
from sqlalchemy.types import TypeDecorator, CHAR
import uuid

class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type.

    Uses PostgreSQL's native UUID type when available; otherwise stores
    as CHAR(36) string. Always returns/accepts uuid.UUID objects in Python
    code, avoiding binding errors under SQLite.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):  # pragma: no cover - simple branching
        if dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID  # type: ignore
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            # Attempt to coerce
            value = uuid.UUID(str(value))
        if dialect.name == 'postgresql':
            return value
        # Store as string for non-Postgres
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class BaseModel:
    __abstract__ = True

    # Unified UUID type for FK references
    UUIDType = GUID
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())