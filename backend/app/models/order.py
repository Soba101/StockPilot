from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from .base import BaseModel


class Order(Base, BaseModel):
    __tablename__ = "orders"

    # id inherited from BaseModel
    org_id = Column(BaseModel.UUIDType, ForeignKey("organizations.id"), nullable=False)
    order_number = Column(String(100), nullable=False)
    channel = Column(String(50))  # 'online', 'pos', 'phone', etc.
    status = Column(String(20), default='pending')
    ordered_at = Column(DateTime(timezone=True), default=func.now())
    fulfilled_at = Column(DateTime(timezone=True))
    location_id = Column(BaseModel.UUIDType, ForeignKey("locations.id"))
    total_amount = Column(DECIMAL(10, 2))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization")
    location = relationship("Location")
    order_items = relationship("OrderItem", back_populates="order")


class OrderItem(Base, BaseModel):
    __tablename__ = "order_items"

    # id inherited from BaseModel
    order_id = Column(BaseModel.UUIDType, ForeignKey("orders.id"), nullable=False)
    product_id = Column(BaseModel.UUIDType, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    discount = Column(DECIMAL(10, 2), default=0)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product")