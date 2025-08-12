from sqlalchemy import Column, String, Text, DECIMAL, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from .base import BaseModel

class Product(Base, BaseModel):
    __tablename__ = "products"
    
    # id inherited from BaseModel
    org_id = Column(BaseModel.UUIDType, ForeignKey("organizations.id"), nullable=False)
    sku = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    cost = Column(DECIMAL(10, 2))
    price = Column(DECIMAL(10, 2))
    uom = Column(String(20), default="each")
    reorder_point = Column(Integer, default=0)
    safety_stock_days = Column(Integer, default=3)
    preferred_supplier_id = Column(BaseModel.UUIDType, ForeignKey("suppliers.id"), nullable=True)
    pack_size = Column(Integer, default=1)
    max_stock_days = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="products")
    inventory_movements = relationship("InventoryMovement", back_populates="product")
    preferred_supplier = relationship("Supplier", foreign_keys=[preferred_supplier_id])