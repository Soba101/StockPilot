from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.core.database import Base
from .base import BaseModel

class Organization(Base, BaseModel):
    """Organization model using portable UUID from BaseModel.

    Inherits BaseModel to avoid dialect-specific UUID issues in tests (SQLite) while
    still using native UUID in Postgres. Previous implementation forced Postgres UUID
    type causing CompileError under SQLite in unit tests.
    """
    __tablename__ = "organizations"

    name = Column(String(255), nullable=False)
    
    # Relationships
    locations = relationship("Location", back_populates="organization", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="organization", cascade="all, delete-orphan")
    suppliers = relationship("Supplier", back_populates="organization", cascade="all, delete-orphan")
    purchase_orders = relationship("PurchaseOrder", back_populates="organization", cascade="all, delete-orphan")