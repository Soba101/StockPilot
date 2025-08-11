from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class InventoryMovementBase(BaseModel):
    product_id: UUID
    location_id: UUID
    quantity: int
    movement_type: str = Field(..., pattern="^(in|out|adjust|transfer)$")
    reference: Optional[str] = None
    notes: Optional[str] = None
    timestamp: datetime


class InventoryMovementCreate(InventoryMovementBase):
    pass


class InventoryMovementUpdate(BaseModel):
    reference: Optional[str] = None
    notes: Optional[str] = None


class InventoryMovement(InventoryMovementBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InventoryMovementWithDetails(InventoryMovement):
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    location_name: Optional[str] = None


class StockSummary(BaseModel):
    product_id: UUID
    product_name: str
    product_sku: str
    location_id: UUID
    location_name: str
    on_hand_quantity: int
    allocated_quantity: int = 0
    available_quantity: int
    reorder_point: Optional[int] = None
    is_low_stock: bool = False
    is_out_of_stock: bool = False
    last_movement_date: Optional[datetime] = None


class LocationStockSummary(BaseModel):
    location_id: UUID
    location_name: str
    total_products: int
    low_stock_count: int
    out_of_stock_count: int
    total_stock_value: float
    products: List[StockSummary]


class InventorySummaryResponse(BaseModel):
    total_products: int
    total_locations: int
    low_stock_count: int
    out_of_stock_count: int
    total_stock_value: float
    locations: List[LocationStockSummary]


class StockAdjustment(BaseModel):
    product_id: UUID
    location_id: UUID
    new_quantity: int
    reason: str
    notes: Optional[str] = None


class BulkStockAdjustment(BaseModel):
    adjustments: List[StockAdjustment]


class StockTransfer(BaseModel):
    product_id: UUID
    from_location_id: UUID
    to_location_id: UUID
    quantity: int
    reference: Optional[str] = None
    notes: Optional[str] = None