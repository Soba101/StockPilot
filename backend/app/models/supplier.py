from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from app.core.database import Base
from .base import BaseModel


class Supplier(Base, BaseModel):
    __tablename__ = "suppliers"

    # id inherited from BaseModel
    org_id = Column(BaseModel.UUIDType, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    contact_person = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    lead_time_days = Column(Integer, nullable=False, default=7)
    minimum_order_quantity = Column(Integer, nullable=False, default=1)
    payment_terms = Column(String(100), nullable=True)
    is_active = Column(String(10), nullable=False, default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="suppliers")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")