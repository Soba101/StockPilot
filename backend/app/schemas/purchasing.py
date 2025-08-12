from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from app.models.purchase_order import PurchaseOrderStatus


class PurchaseOrderItemBase(BaseModel):
    product_id: str
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")
    unit_cost: float = Field(ge=0, description="Unit cost must be non-negative")


class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass


class PurchaseOrderItem(PurchaseOrderItemBase):
    id: str
    purchase_order_id: str
    total_cost: float
    received_quantity: int = 0
    created_at: datetime
    updated_at: datetime
    
    # Product details (joined)
    product_name: Optional[str] = None
    product_sku: Optional[str] = None

    class Config:
        from_attributes = True


class PurchaseOrderBase(BaseModel):
    supplier_id: str
    po_number: str = Field(min_length=1, max_length=50)
    expected_date: Optional[datetime] = None
    notes: Optional[str] = None


class PurchaseOrderCreate(PurchaseOrderBase):
    items: List[PurchaseOrderItemCreate] = Field(min_items=1, description="At least one item is required")


class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[str] = None
    expected_date: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[PurchaseOrderStatus] = None


class PurchaseOrder(PurchaseOrderBase):
    id: str
    org_id: str
    status: PurchaseOrderStatus
    order_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    total_amount: float
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    
    # Supplier details (joined)
    supplier_name: Optional[str] = None
    
    # Items
    items: List[PurchaseOrderItem] = []

    class Config:
        from_attributes = True


class PurchaseOrderSummary(BaseModel):
    """Lightweight summary for lists"""
    id: str
    po_number: str
    supplier_name: str
    status: PurchaseOrderStatus
    total_amount: float
    order_date: Optional[datetime] = None
    expected_date: Optional[datetime] = None
    item_count: int

    class Config:
        from_attributes = True


class PurchaseOrderStatusUpdate(BaseModel):
    status: PurchaseOrderStatus
    notes: Optional[str] = None
    received_date: Optional[datetime] = None