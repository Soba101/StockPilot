from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base
from .base import BaseModel


class PurchaseOrderStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    ordered = "ordered"
    received = "received"
    cancelled = "cancelled"


class PurchaseOrder(Base, BaseModel):
    __tablename__ = "purchase_orders"

    # id inherited from BaseModel
    org_id = Column(BaseModel.UUIDType, ForeignKey("organizations.id"), nullable=False)
    supplier_id = Column(BaseModel.UUIDType, ForeignKey("suppliers.id"), nullable=False)
    po_number = Column(String(50), nullable=False, unique=True)
    status = Column(Enum(PurchaseOrderStatus), default=PurchaseOrderStatus.draft, nullable=False)
    order_date = Column(DateTime(timezone=True), nullable=True)
    expected_date = Column(DateTime(timezone=True), nullable=True)
    received_date = Column(DateTime(timezone=True), nullable=True)
    total_amount = Column(Float, nullable=False, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(BaseModel.UUIDType, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="purchase_orders")
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base, BaseModel):
    __tablename__ = "purchase_order_items"

    # id inherited from BaseModel
    purchase_order_id = Column(BaseModel.UUIDType, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(BaseModel.UUIDType, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    received_quantity = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")