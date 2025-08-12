from sqlalchemy import Column, String, DateTime, func, ForeignKey
from app.core.database import Base
from .base import BaseModel


class User(Base, BaseModel):
    __tablename__ = "users"

    # id inherited from BaseModel
    org_id = Column(BaseModel.UUIDType, ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="admin")  # admin|viewer|purchaser
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


