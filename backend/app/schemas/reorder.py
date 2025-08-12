"""
Pydantic schemas for reorder suggestions and purchase order drafting.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from decimal import Decimal
import uuid


class ReorderSuggestionResponse(BaseModel):
    """Single reorder suggestion response."""
    
    # Product identification
    product_id: uuid.UUID
    sku: str
    name: str
    
    # Supplier information
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    
    # Current state
    on_hand: int
    incoming: int
    
    # Coverage calculations
    days_cover_current: Optional[float] = None
    days_cover_after: Optional[float] = None
    
    # Recommendation
    recommended_quantity: int
    
    # Velocity information
    chosen_velocity: Optional[float] = None
    velocity_source: str
    
    # Algorithm inputs
    horizon_days: int
    demand_forecast_units: float
    
    # Decision reasoning
    reasons: List[str]
    adjustments: List[str]
    
    class Config:
        from_attributes = True


class ReorderSuggestionsRequest(BaseModel):
    """Request parameters for reorder suggestions."""
    
    location_id: Optional[uuid.UUID] = None
    strategy: Literal["latest", "conservative"] = "latest"
    horizon_days_override: Optional[int] = None
    include_zero_velocity: bool = False
    min_days_cover: Optional[int] = None
    max_days_cover: Optional[int] = None


class ReorderSuggestionsResponse(BaseModel):
    """Response containing list of reorder suggestions."""
    
    suggestions: List[ReorderSuggestionResponse]
    summary: Dict[str, Any]
    generated_at: datetime
    parameters: ReorderSuggestionsRequest
    
    class Config:
        from_attributes = True


class ReorderExplanationResponse(BaseModel):
    """Detailed explanation for a single product's reorder calculation."""
    
    product_id: uuid.UUID
    sku: str
    name: str
    skipped: bool = False
    skip_reason: Optional[str] = None
    
    recommendation: Optional[Dict[str, Any]] = None
    explanation: Optional[Dict[str, Any]] = None
    reasons: List[str] = []
    adjustments: List[str] = []
    coverage: Optional[Dict[str, Any]] = None
    velocity: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class DraftPOItem(BaseModel):
    """Single item in a draft purchase order."""
    
    product_id: uuid.UUID
    sku: str
    product_name: str
    quantity: int
    unit_cost: Optional[Decimal] = None
    line_total: Optional[Decimal] = None
    
    # Reorder context
    on_hand: int
    recommended_quantity: int
    reasons: List[str]
    adjustments: List[str]


class DraftPO(BaseModel):
    """Draft purchase order grouped by supplier."""
    
    supplier_id: uuid.UUID
    supplier_name: str
    po_number: str  # Sequential number
    
    items: List[DraftPOItem]
    
    # PO totals
    total_items: int
    total_quantity: int
    estimated_total: Optional[Decimal] = None
    
    # Supplier details
    lead_time_days: int
    minimum_order_quantity: int
    payment_terms: Optional[str] = None
    
    # Metadata
    created_at: datetime
    expected_delivery: Optional[datetime] = None


class DraftPORequest(BaseModel):
    """Request to create draft purchase orders."""
    
    product_ids: List[uuid.UUID]
    strategy: Literal["latest", "conservative"] = "latest"
    horizon_days_override: Optional[int] = None
    auto_number: bool = True  # Auto-generate PO numbers


class DraftPOResponse(BaseModel):
    """Response containing draft purchase orders."""
    
    draft_pos: List[DraftPO]
    summary: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True