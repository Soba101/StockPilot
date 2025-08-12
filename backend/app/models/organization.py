from sqlalchemy import Column, String, DateTime, func, CHAR
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base
from .base import BaseModel

class Organization(Base):
    __tablename__ = "organizations"
    
    try:
        from sqlalchemy.dialects.postgresql import UUID as _PGUUID  # type: ignore
        id = Column(_PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    except Exception:  # SQLite fallback
        id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    locations = relationship("Location", back_populates="organization", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="organization", cascade="all, delete-orphan")
    suppliers = relationship("Supplier", back_populates="organization", cascade="all, delete-orphan")
    purchase_orders = relationship("PurchaseOrder", back_populates="organization", cascade="all, delete-orphan")