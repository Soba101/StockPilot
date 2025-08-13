"""Generate one year of synthetic operational data ending at a supplied end date (default: today).

Creates realistic:
- Inventory movements (purchase receipts, sales shipments, adjustments)
- Sales orders + order items
- Purchase orders + items (with receipt movements) 

Constraints / Principles:
- Event sourced inventory: only insert rows into inventory_movements; never persist running totals
- Multi‑tenant: only touches the demo org (first organizations row) unless ORG_ID env override provided
- Deterministic-ish but with randomness: seeding allows reproducibility

Usage (from repo root):
  python -m backend.scripts.generate_year_data --end 2025-08-13 --days 365

SQLite dev quick run:
  DATABASE_URL=sqlite:///./test.db python -m backend.scripts.generate_year_data --reset-sqlite

Safe re-run: Will not delete existing facts unless --purge is passed. It will skip days that already have movements/orders tagged by a synthetic reference marker.
"""
from __future__ import annotations
import argparse
import os
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete

from app.core.database import SessionLocal, engine
from app.models.product import Product
from app.models.inventory import InventoryMovement
from app.models.order import Order, OrderItem
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.models.organization import Organization
from app.models.location import Location
from app.models.supplier import Supplier

REF_PREFIX = "SYNTH-YEAR"
RANDOM_SEED = int(os.getenv("SYNTH_SEED", "42"))
random.seed(RANDOM_SEED)

# --- Helpers -----------------------------------------------------------------

def pick(seq):
    return random.choice(list(seq))

# Daily demand profile (weekday higher than weekend)
BASE_DEMAND_BY_DOW = { # 0=Mon
    0: 1.15,
    1: 1.10,
    2: 1.05,
    3: 1.00,
    4: 1.05,
    5: 0.7,
    6: 0.6,
}

# Introduce mild seasonality over the year (sinusoidal)
import math

def seasonal_multiplier(day_index: int, total_days: int) -> float:
    # one full sine cycle across the year, range ~0.85 - 1.15
    angle = 2 * math.pi * (day_index / total_days)
    return 1 + 0.15 * math.sin(angle - math.pi/6)

# --- Core generation ----------------------------------------------------------

def ensure_demo_entities(db: Session, org_id: str | None) -> tuple[str, list[Product], Location, list[Supplier]]:
    if org_id:
        org = db.scalar(select(Organization).where(Organization.id == org_id))
        if not org:
            raise SystemExit(f"Provided ORG_ID {org_id} not found")
    else:
        org = db.scalar(select(Organization).order_by(Organization.created_at.asc()))
        if not org:
            raise SystemExit("No organizations present; run init.sql first")
    products = list(db.scalars(select(Product).where(Product.org_id == org.id)))
    if not products:
        raise SystemExit("No products found for org; seed products first")
    # pick a default warehouse (first location) or create one if absent (should exist via init.sql)
    location = db.scalar(select(Location).where(Location.org_id == org.id).order_by(Location.created_at.asc()))
    if not location:
        raise SystemExit("No location found; seed locations first")
    suppliers = list(db.scalars(select(Supplier).where(Supplier.org_id == org.id)))
    if not suppliers:
        raise SystemExit("No suppliers found; seed suppliers first")
    return org.id, products, location, suppliers


def purge_existing(db: Session, org_id: str):
    # Only purge synthetic data (by reference prefix) to retain manual test data
    inv_q = delete(InventoryMovement).where(InventoryMovement.reference.like(f"{REF_PREFIX}%"))
    ord_ids = [oid for (oid,) in db.execute(select(Order.id).where(Order.order_number.like(f"{REF_PREFIX}%")))]
    if ord_ids:
        db.execute(delete(OrderItem).where(OrderItem.order_id.in_(ord_ids)))
        db.execute(delete(Order).where(Order.id.in_(ord_ids)))
    po_ids = [pid for (pid,) in db.execute(select(PurchaseOrder.id).where(PurchaseOrder.po_number.like(f"{REF_PREFIX}%")))]
    if po_ids:
        db.execute(delete(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id.in_(po_ids)))
        db.execute(delete(PurchaseOrder).where(PurchaseOrder.id.in_(po_ids)))
    db.commit()


def day_already_generated(db: Session, day_start: datetime, day_end: datetime) -> bool:
    # check any inventory movement with our reference and timestamp inside day
    exists = db.scalar(
        select(func.count()).select_from(InventoryMovement)
        .where(InventoryMovement.reference.like(f"{REF_PREFIX}%"))
        .where(InventoryMovement.timestamp >= day_start)
        .where(InventoryMovement.timestamp < day_end)
    )
    return bool(exists)


def generate_year(db: Session, end_date: datetime, days: int, org_id: str, products: list[Product], location: Location, suppliers: list[Supplier], skip_existing: bool):
    start_date = end_date - timedelta(days=days-1)
    total_days = days

    # Roughly derive baseline daily demand per product from reorder_point or default
    base_daily = {}
    for p in products:
        # Extract scalar ints (SQLAlchemy attributes can be InstrumentedAttribute for type checkers)
        rp = getattr(p, "reorder_point", None)
        ss = getattr(p, "safety_stock_days", None)
        try:
            rp_val = int(rp) if rp is not None else 0
        except Exception:
            rp_val = 0
        try:
            ss_val = int(ss) if ss is not None else 3
        except Exception:
            ss_val = 3
        if rp_val > 0 and ss_val > 0:
            est = max(1, rp_val / max(ss_val, 1))
        else:
            est = 3
        base_daily[p.id] = est

    current_stock = defaultdict(int)

    # initial stocking purchase order for each product
    po_counter = 0

    for day_idx in range(total_days):
        day = start_date + timedelta(days=day_idx)
        day_start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        if skip_existing and day_already_generated(db, day_start, day_end):
            continue

        dow_mult = BASE_DEMAND_BY_DOW[day.weekday()]
        season_mult = seasonal_multiplier(day_idx, total_days)

        # Simulate sales orders for the day
        # number of orders ~ normal variation scaled by demand
        order_factor = (dow_mult * season_mult)
        num_orders = max(0, int(random.gauss(3 * order_factor, 1)))
        for oi in range(num_orders):
            order_ts = day_start + timedelta(hours=random.randint(9, 18), minutes=random.randint(0,59))
            order_number = f"{REF_PREFIX}-SO-{day.strftime('%Y%m%d')}-{oi:03d}"
            order = Order(org_id=org_id, order_number=order_number, channel=pick(["online","pos"]), status="fulfilled", ordered_at=order_ts, fulfilled_at=order_ts)
            db.add(order)
            db.flush()  # get order.id

            # choose 1-3 items
            items_in_order = random.randint(1,3)
            chosen_products = random.sample(products, min(items_in_order, len(products)))
            for prod in chosen_products:
                demand_base = base_daily[prod.id]
                qty = max(1, int(random.gauss(demand_base * order_factor, 0.75)))
                # create order item
                price = prod.price or Decimal("10.00")
                item = OrderItem(order_id=order.id, product_id=prod.id, quantity=qty, unit_price=price, discount=Decimal("0"))
                db.add(item)
                # inventory movement (out)
                mv = InventoryMovement(product_id=prod.id, location_id=location.id, quantity=-qty, movement_type='out', reference=f"{REF_PREFIX}-SO-{order_number}", timestamp=order_ts)
                db.add(mv)
                current_stock[prod.id] -= qty

        # Replenishment logic: if projected stock below threshold, create a purchase order (received same day or later)
        # We'll trigger a PO roughly weekly or when stock < reorder_point
        if day.weekday() == 0:  # Mondays evaluate reorder
            for prod in products:
                rp = getattr(prod, "reorder_point", None)
                threshold = int(rp) if (rp is not None and isinstance(rp, (int, float))) else 10
                if current_stock[prod.id] < int(threshold):
                    po_counter += 1
                    supplier = pick(suppliers)
                    po_number = f"{REF_PREFIX}-PO-{day.strftime('%Y%m%d')}-{po_counter:03d}"
                    qty = int(threshold) * 2 + random.randint(0, int(threshold))  # order enough for ~2 weeks
                    raw_cost = getattr(prod, "cost", None)
                    try:
                        cost = float(raw_cost) if raw_cost is not None else 5.0
                    except Exception:
                        cost = 5.0
                    lt_raw = getattr(supplier, "lead_time_days", None)
                    try:
                        lt_days = int(lt_raw) if lt_raw is not None else 7
                    except Exception:
                        lt_days = 7
                    po = PurchaseOrder(org_id=org_id, supplier_id=supplier.id, po_number=po_number, status=PurchaseOrderStatus.received, order_date=day_start, expected_date=day_start + timedelta(days= lt_days), received_date=day_start)
                    db.add(po)
                    db.flush()
                    poi = PurchaseOrderItem(purchase_order_id=po.id, product_id=prod.id, quantity=qty, unit_cost=cost, total_cost=qty * cost, received_quantity=qty)
                    db.add(poi)
                    mv_in = InventoryMovement(product_id=prod.id, location_id=location.id, quantity=qty, movement_type='in', reference=f"{REF_PREFIX}-PO-{po_number}", timestamp=day_start + timedelta(hours=8))
                    db.add(mv_in)
                    current_stock[prod.id] += qty

        # Occasional adjustments (inventory counts)
        if random.random() < 0.05:
            prod = pick(products)
            adjust_qty = random.choice([-2,-1,1,2])
            mv_adj = InventoryMovement(product_id=prod.id, location_id=location.id, quantity=adjust_qty, movement_type='adjust', reference=f"{REF_PREFIX}-ADJ-{day.strftime('%Y%m%d')}", timestamp=day_start + timedelta(hours=19))
            db.add(mv_adj)
            current_stock[prod.id] += adjust_qty

        if day_idx % 14 == 0:
            db.commit()  # periodic flush

    db.commit()


# --- Main --------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic year of data")
    parser.add_argument("--end", help="End date YYYY-MM-DD (inclusive)", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--days", type=int, default=365, help="Number of days (default 365)")
    parser.add_argument("--purge", action="store_true", help="Purge previously generated synthetic data first")
    parser.add_argument("--org-id", help="Target org UUID (defaults to first org)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip days already containing synthetic data")
    parser.add_argument("--reset-sqlite", action="store_true", help="(Dev) If using sqlite file test.db, delete it first for clean slate")
    args = parser.parse_args()

    if args.reset_sqlite and "sqlite" in os.getenv("DATABASE_URL", ""):
        path = os.getenv("DATABASE_URL", "").split("///")[-1]
        if path and os.path.exists(path):
            os.remove(path)

    end_date = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)

    with SessionLocal() as db:
        org_id, products, location, suppliers = ensure_demo_entities(db, args.org_id)
        if args.purge:
            purge_existing(db, org_id)
        generate_year(db, end_date, args.days, org_id, products, location, suppliers, skip_existing=args.skip_existing)
    print(f"Synthetic data generated for {args.days} days ending {end_date.date()}.")

if __name__ == "__main__":
    main()
