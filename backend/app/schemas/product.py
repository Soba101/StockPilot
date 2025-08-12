from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal
import uuid

class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    cost: Optional[Decimal] = None
    price: Optional[Decimal] = None
    uom: str = "each"
    reorder_point: int = 0
    safety_stock_days: int = 3
    preferred_supplier_id: Optional[uuid.UUID] = None
    pack_size: int = 1
    max_stock_days: Optional[int] = None

class ProductCreate(ProductBase):
    org_id: uuid.UUID

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    cost: Optional[Decimal] = None
    price: Optional[Decimal] = None
    uom: Optional[str] = None
    reorder_point: Optional[int] = None
    safety_stock_days: Optional[int] = None
    preferred_supplier_id: Optional[uuid.UUID] = None
    pack_size: Optional[int] = None
    max_stock_days: Optional[int] = None

class Product(ProductBase):
    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True