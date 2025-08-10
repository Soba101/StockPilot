from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    movement_type = Column(String(20), nullable=False)  # 'in', 'out', 'adjust', 'transfer'
    reference = Column(String(255))
    notes = Column(Text)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_by = Column(UUID(as_uuid=True))  # Will reference users when auth is implemented
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="inventory_movements")
    location = relationship("Location", back_populates="inventory_movements")