from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Literal, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from app.core.config import settings

VelocityStrategy = Literal["latest", "conservative"]

@dataclass
class StockoutItem:
    product_id: str
    sku: str
    name: str
    on_hand: float
    reorder_point: Optional[int]
    velocity_7d: Optional[float]
    velocity_30d: Optional[float]
    velocity_56d: Optional[float]
    chosen_velocity: Optional[float]
    velocity_source: str
    days_to_stockout: Optional[float]
    risk_level: str

@dataclass
class DailyDigest:
    org_id: str
    run_date: date
    strategy: VelocityStrategy
    high: List[StockoutItem]
    medium: List[StockoutItem]
    counts: Dict[str, int]
    top_soonest: List[StockoutItem]

# In-memory idempotency fallback (process scope)
_idempotent_keys: set[str] = set()

def _idempotency_key(org_id: str, run_date: date) -> str:
    return f"alerts:daily:{org_id}:{run_date.strftime('%Y%m%d')}"

def check_and_set_idempotent(org_id: str, run_date: date) -> bool:
    """Return True if already executed; else mark and return False.
    TODO: Replace with Redis implementation when connection available.
    """
    key = _idempotency_key(org_id, run_date)
    if key in _idempotent_keys:
        return True
    _idempotent_keys.add(key)
    return False

def generate_daily_stockout_digest(db: Session, org_id: UUID, strategy: VelocityStrategy = "latest") -> DailyDigest:
    # Pull on-hand & velocities using sales_daily mart (aggregated averages) + inventory movements.
    # On hand
    stock_sql = text("""
        SELECT p.id as product_id, p.sku, p.name, p.reorder_point,
               COALESCE(SUM(CASE 
                 WHEN im.movement_type IN ('in','adjust') THEN im.quantity
                 WHEN im.movement_type = 'out' THEN -im.quantity
                 WHEN im.movement_type = 'transfer' THEN 0
                 ELSE 0 END), 0) as on_hand
        FROM products p
        LEFT JOIN inventory_movements im ON im.product_id = p.id
        WHERE p.org_id = :org_id
        GROUP BY p.id, p.sku, p.name, p.reorder_point
    """)
    stock_rows = db.execute(stock_sql, {"org_id": org_id}).fetchall()
    stock_map = {str(r.product_id): r for r in stock_rows}

    vel_sql = text("""
        SELECT sd.sku,
               AVG(sd.units_7day_avg) as v7,
               AVG(sd.units_30day_avg) as v30,
               AVG(sd.units_56day_avg) as v56
        FROM analytics_marts.sales_daily sd
        WHERE sd.org_id = :org_id
          AND sd.sales_date >= (current_date - interval '60 days')
        GROUP BY sd.sku
    """)
    col_check = db.execute(text("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema='analytics_marts' AND table_name='sales_daily' AND column_name='units_56day_avg'
    """
    )).fetchone()
    if col_check:
        try:
            vel_rows = db.execute(vel_sql, {"org_id": org_id}).fetchall()
        except ProgrammingError:
            db.rollback()
            vel_rows = []
    else:
        fallback = text("""
            SELECT sd.sku,
                   AVG(sd.units_7day_avg) as v7,
                   AVG(sd.units_30day_avg) as v30,
                   NULL::numeric as v56
            FROM analytics_marts.sales_daily sd
            WHERE sd.org_id = :org_id
              AND sd.sales_date >= (current_date - interval '60 days')
            GROUP BY sd.sku
        """)
        vel_rows = db.execute(fallback, {"org_id": org_id}).fetchall()
    vel_map = {r.sku: r for r in vel_rows}

    epsilon = 1e-6
    high: List[StockoutItem] = []
    medium: List[StockoutItem] = []
    all_items: List[StockoutItem] = []

    for pid, srow in stock_map.items():
        vrow = vel_map.get(srow.sku)
        v7 = float(vrow.v7) if vrow and vrow.v7 is not None else None
        v30 = float(vrow.v30) if vrow and vrow.v30 is not None else None
        v56 = float(vrow.v56) if vrow and vrow.v56 is not None else None

        candidates = [v for v in [v7, v30, v56] if v and v > 0]
        chosen_velocity: Optional[float] = None
        velocity_source = "none"
        if strategy == "latest":
            # Priority 7d > 30d > 56d
            for val, src in [(v7, "7d"), (v30, "30d"), (v56, "56d")]:
                if val and val > 0:
                    chosen_velocity = val
                    velocity_source = src
                    break
        else:  # conservative
            if candidates:
                chosen_velocity = min(candidates)
                if chosen_velocity == v7:
                    velocity_source = "7d"
                elif chosen_velocity == v30:
                    velocity_source = "30d"
                elif chosen_velocity == v56:
                    velocity_source = "56d"

        days_to_stockout: Optional[float] = None
        if chosen_velocity and chosen_velocity > 0:
            days_to_stockout = float(srow.on_hand) / max(chosen_velocity, epsilon)

        risk_level = "none"
        if days_to_stockout is not None:
            if days_to_stockout <= 7:
                risk_level = "high"
            elif days_to_stockout <= 14:
                risk_level = "medium"
            elif days_to_stockout <= 30:
                risk_level = "low"

        # Reorder point bump
        if srow.reorder_point is not None and float(srow.on_hand) <= float(srow.reorder_point or 0):
            if risk_level in ("none", "low"):
                risk_level = "medium" if risk_level == "none" else risk_level

        item = StockoutItem(
            product_id=pid,
            sku=srow.sku,
            name=srow.name,
            on_hand=float(srow.on_hand),
            reorder_point=int(srow.reorder_point) if srow.reorder_point is not None else None,
            velocity_7d=v7,
            velocity_30d=v30,
            velocity_56d=v56,
            chosen_velocity=chosen_velocity,
            velocity_source=velocity_source,
            days_to_stockout=round(days_to_stockout,1) if days_to_stockout is not None else None,
            risk_level=risk_level
        )
        all_items.append(item)
        if risk_level == "high":
            high.append(item)
        elif risk_level == "medium" and (days_to_stockout is not None and days_to_stockout <= 14):
            medium.append(item)

    # Sort lists
    high.sort(key=lambda x: x.days_to_stockout or 9999)
    medium.sort(key=lambda x: x.days_to_stockout or 9999)

    # Top 5 soonest across both high + medium
    combined = sorted(high + medium, key=lambda x: x.days_to_stockout or 9999)[:5]

    digest = DailyDigest(
        org_id=str(org_id),
        run_date=date.today(),
        strategy=strategy,
        high=high,
        medium=medium,
        counts={"high": len(high), "medium": len(medium)},
        top_soonest=combined
    )
    return digest

__all__ = [
    "VelocityStrategy",
    "StockoutItem",
    "DailyDigest",
    "generate_daily_stockout_digest",
    "check_and_set_idempotent"
]
