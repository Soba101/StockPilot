"""
Reorder suggestions service implementing the W5 purchase suggestions algorithm.
Computes reorder recommendations based on velocity, lead times, MOQ, pack sizes, and safety stock.
"""

from typing import List, Optional, Dict, Any, Literal
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
from decimal import Decimal
import math

from app.core.database import engine


class ReorderSuggestion:
    """Reorder suggestion data structure matching the algorithm contract."""
    
    def __init__(self, **kwargs):
        # Product identification
        self.product_id: uuid.UUID = kwargs['product_id']
        self.sku: str = kwargs['sku']
        self.name: str = kwargs['name']
        
        # Supplier information
        self.supplier_id: Optional[uuid.UUID] = kwargs.get('supplier_id')
        self.supplier_name: Optional[str] = kwargs.get('supplier_name')
        
        # Current state
        self.on_hand: int = kwargs['on_hand']
        self.incoming: int = kwargs['incoming']
        
        # Coverage calculations
        self.days_cover_current: Optional[float] = kwargs.get('days_cover_current')
        self.days_cover_after: Optional[float] = kwargs.get('days_cover_after')
        
        # Recommendation
        self.recommended_quantity: int = kwargs['recommended_quantity']
        
        # Velocity information
        self.chosen_velocity: Optional[float] = kwargs.get('chosen_velocity')
        self.velocity_source: str = kwargs.get('velocity_source', 'none')
        
        # Algorithm inputs
        self.horizon_days: int = kwargs['horizon_days']
        self.demand_forecast_units: float = kwargs.get('demand_forecast_units', 0.0)
        
        # Decision reasoning
        self.reasons: List[str] = kwargs.get('reasons', [])
        self.adjustments: List[str] = kwargs.get('adjustments', [])
        
        # Optional detailed explanation
        self.explanation: Optional[Dict[str, Any]] = kwargs.get('explanation')


def compute_reorder_suggestions(
    org_id: uuid.UUID,
    location_id: Optional[uuid.UUID] = None,
    strategy: Literal["latest", "conservative"] = "latest",
    horizon_days_override: Optional[int] = None
) -> List[ReorderSuggestion]:
    """
    Compute reorder suggestions for an organization using the W5 algorithm.
    
    Args:
        org_id: Organization identifier
        location_id: Optional location filter (not implemented yet - reserved)
        strategy: Velocity selection strategy ("latest" or "conservative")
        horizon_days_override: Override the computed horizon (lead_time + safety_stock)
        
    Returns:
        List of reorder suggestions with recommendations and explanations
    """
    
    # Query the reorder_inputs mart for all required data
    query = text("""
        SELECT 
            product_id,
            sku,
            product_name,
            supplier_id,
            supplier_name,
            on_hand,
            reorder_point,
            safety_stock_days,
            pack_size,
            max_stock_days,
            lead_time_days,
            moq,
            chosen_velocity_latest,
            chosen_velocity_conservative,
            velocity_source_latest,
            velocity_source_conservative,
            incoming_units_30d,
            incoming_units_60d,
            horizon_days,
            missing_supplier,
            no_velocity_data
        FROM analytics_marts.reorder_inputs 
        WHERE org_id = :org_id
        -- Note: Temporarily allowing products without active suppliers for demo purposes
        ORDER BY product_name
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"org_id": str(org_id)})
        rows = result.fetchall()
    
    suggestions = []
    
    for row in rows:
        suggestion = _compute_single_product_suggestion(row, strategy, horizon_days_override)
        if suggestion:
            suggestions.append(suggestion)
    
    return suggestions


def _compute_single_product_suggestion(
    row: Any, 
    strategy: str, 
    horizon_days_override: Optional[int]
) -> Optional[ReorderSuggestion]:
    """
    Compute reorder suggestion for a single product following the W5 algorithm contract.
    
    Algorithm steps:
    1. Select velocity based on strategy
    2. Compute horizon (lead_time + safety_stock, min 7, or override)
    3. Calculate demand forecast = chosen_velocity * horizon_days
    4. Determine incoming units within horizon
    5. Compute raw shortfall = demand_forecast - (on_hand + incoming)
    6. Apply adjustments: reorder bump, MOQ, pack rounding, max stock cap
    7. Apply guardrails: zero velocity skip, minimum quantity filter
    """
    
    # Extract row data
    product_id = row.product_id if isinstance(row.product_id, uuid.UUID) else uuid.UUID(row.product_id)
    sku = row.sku
    name = row.product_name
    supplier_id = row.supplier_id if isinstance(row.supplier_id, uuid.UUID) else (uuid.UUID(row.supplier_id) if row.supplier_id else None)
    supplier_name = row.supplier_name
    on_hand = int(row.on_hand or 0)
    reorder_point = int(row.reorder_point or 0)
    safety_stock_days = int(row.safety_stock_days or 3)
    pack_size = max(1, int(row.pack_size or 1))
    max_stock_days = int(row.max_stock_days) if row.max_stock_days else None
    lead_time_days = int(row.lead_time_days or 7)
    moq = max(1, int(row.moq or 1))
    
    # Step 1: Select velocity based on strategy
    if strategy == "conservative":
        chosen_velocity = float(row.chosen_velocity_conservative or 0.0)
        velocity_source = row.velocity_source_conservative or 'none'
    else:  # "latest"
        chosen_velocity = float(row.chosen_velocity_latest or 0.0)
        velocity_source = row.velocity_source_latest or 'none'
    
    # Step 2: Compute horizon
    if horizon_days_override:
        horizon_days = max(7, horizon_days_override)
    else:
        horizon_days = max(7, lead_time_days + safety_stock_days)
    
    # Step 3: Calculate demand forecast
    demand_forecast_units = chosen_velocity * horizon_days
    
    # Step 4: Determine incoming units within horizon
    # Use appropriate incoming quantity based on horizon
    if horizon_days <= 30:
        incoming_units_within_horizon = int(row.incoming_units_30d or 0)
    else:
        incoming_units_within_horizon = int(row.incoming_units_60d or 0)
    
    # Step 5: Compute base shortfall
    net_available_after_incoming = on_hand + incoming_units_within_horizon
    raw_shortfall = demand_forecast_units - net_available_after_incoming
    recommended_base = max(0, raw_shortfall)
    
    # Initialize tracking variables
    reasons = []
    adjustments = []
    final_quantity = recommended_base
    
    # Step 6: Apply adjustments in order
    
    # 6a. Reorder bump (ensure at least reorder_point - on_hand if below)
    if on_hand < reorder_point:
        reorder_bump = max(0, reorder_point - on_hand)
        if reorder_bump > final_quantity:
            final_quantity = reorder_bump
            adjustments.append(f"Bumped to reorder point: {reorder_bump} units")
            reasons.append("BELOW_REORDER_POINT")
    
    # Add base reasoning
    if raw_shortfall > 0:
        reasons.append("LEAD_TIME_RISK")
    if incoming_units_within_horizon > 0:
        reasons.append("INCOMING_COVERAGE")
    
    # 6b. MOQ enforcement (raise to MOQ if >0 and < MOQ)
    if final_quantity > 0 and final_quantity < moq:
        final_quantity = moq
        adjustments.append(f"Raised to MOQ: {moq} units")
        reasons.append("MOQ_ENFORCED")
    
    # 6c. Pack rounding (ceil to multiple of pack_size)
    if final_quantity > 0 and pack_size > 1:
        original_qty = final_quantity
        final_quantity = math.ceil(final_quantity / pack_size) * pack_size
        if final_quantity != original_qty:
            adjustments.append(f"Rounded to pack size {pack_size}: {original_qty} → {final_quantity}")
            reasons.append("PACK_ROUNDED")
    
    # 6d. Cap by max_stock_days (limit coverage ≤ max)
    if max_stock_days and chosen_velocity > 0:
        max_units = chosen_velocity * max_stock_days
        total_after_order = net_available_after_incoming + final_quantity
        if total_after_order > max_units:
            capped_quantity = max(0, max_units - net_available_after_incoming)
            if capped_quantity != final_quantity:
                adjustments.append(f"Capped by max stock days {max_stock_days}: {final_quantity} → {capped_quantity}")
                final_quantity = capped_quantity
                reasons.append("CAPPED_BY_MAX_DAYS")
    
    # Step 7: Apply guardrails
    
    # 7a. Zero velocity skip unless below reorder point
    if chosen_velocity == 0:
        if on_hand >= reorder_point:
            reasons.append("ZERO_VELOCITY_SKIPPED")
            return None  # Skip this product
        else:
            reasons.append("NO_VELOCITY")
    
    # 7b. Drop if <1 after adjustments (unless MOQ was enforced)
    if final_quantity < 1 and "MOQ_ENFORCED" not in reasons:
        return None  # Skip this product
    
    # Calculate coverage metrics
    days_cover_current = (on_hand / chosen_velocity) if chosen_velocity > 0 else None
    days_cover_after = ((net_available_after_incoming + final_quantity) / chosen_velocity) if chosen_velocity > 0 else None
    
    # Build explanation for transparency
    explanation = {
        "inputs": {
            "on_hand": on_hand,
            "incoming_units_within_horizon": incoming_units_within_horizon,
            "chosen_velocity": chosen_velocity,
            "lead_time_days": lead_time_days,
            "safety_stock_days": safety_stock_days,
            "horizon_days": horizon_days,
            "reorder_point": reorder_point,
            "moq": moq,
            "pack_size": pack_size,
            "max_stock_days": max_stock_days
        },
        "calculations": {
            "demand_forecast_units": demand_forecast_units,
            "net_available_after_incoming": net_available_after_incoming,
            "raw_shortfall": raw_shortfall,
            "recommended_base": recommended_base,
            "final_quantity": int(final_quantity)
        },
        "logic_path": adjustments
    }
    
    return ReorderSuggestion(
        product_id=product_id,
        sku=sku,
        name=name,
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        on_hand=on_hand,
        incoming=incoming_units_within_horizon,
        days_cover_current=days_cover_current,
        days_cover_after=days_cover_after,
        recommended_quantity=int(final_quantity),
        chosen_velocity=chosen_velocity if chosen_velocity > 0 else None,
        velocity_source=velocity_source,
        horizon_days=horizon_days,
        demand_forecast_units=demand_forecast_units,
        reasons=reasons,
        adjustments=adjustments,
        explanation=explanation
    )


def explain_reorder_suggestion(
    org_id: uuid.UUID,
    product_id: uuid.UUID,
    strategy: Literal["latest", "conservative"] = "latest",
    horizon_days_override: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Get detailed explanation for a single product's reorder calculation.
    
    Returns the full explanation object with intermediate values and logic path.
    """
    
    # Query single product from reorder_inputs
    query = text("""
        SELECT * FROM reorder_inputs 
        WHERE org_id = :org_id AND product_id = :product_id
        LIMIT 1
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"org_id": str(org_id), "product_id": str(product_id)})
        row = result.fetchone()
    
    if not row:
        return None
    
    suggestion = _compute_single_product_suggestion(row, strategy, horizon_days_override)
    
    if not suggestion:
        # Return explanation even for skipped products
        return {
            "product_id": str(product_id),
            "sku": row.sku,
            "name": row.product_name,
            "skipped": True,
            "skip_reason": "Zero velocity and above reorder point, or final quantity < 1"
        }
    
    return {
        "product_id": str(suggestion.product_id),
        "sku": suggestion.sku,
        "name": suggestion.name,
        "recommendation": {
            "quantity": suggestion.recommended_quantity,
            "supplier_id": str(suggestion.supplier_id) if suggestion.supplier_id else None,
            "supplier_name": suggestion.supplier_name
        },
        "explanation": suggestion.explanation,
        "reasons": suggestion.reasons,
        "adjustments": suggestion.adjustments,
        "coverage": {
            "days_cover_current": suggestion.days_cover_current,
            "days_cover_after": suggestion.days_cover_after
        },
        "velocity": {
            "chosen_velocity": suggestion.chosen_velocity,
            "source": suggestion.velocity_source
        }
    }