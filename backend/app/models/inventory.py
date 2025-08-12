from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from .base import BaseModel

class InventoryMovement(Base, BaseModel):
    __tablename__ = "inventory_movements"
    
    # id inherited from BaseModel
    product_id = Column(BaseModel.UUIDType, ForeignKey("products.id"), nullable=False)
    location_id = Column(BaseModel.UUIDType, ForeignKey("locations.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    movement_type = Column(String(20), nullable=False)  # 'in', 'out', 'adjust', 'transfer'
    reference = Column(String(255))
    notes = Column(Text)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_by = Column(BaseModel.UUIDType)  # Will reference users when auth is implemented
    # created_at / updated_at inherited from BaseModel; avoid redefining to keep schema consistent
    
    # Relationships
    product = relationship("Product", back_populates="inventory_movements")
    location = relationship("Location", back_populates="inventory_movements")