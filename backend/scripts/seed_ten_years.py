"""
Seed 10 years of realistic data into the database, filling all columns.

Principles respected:
- Multi-tenancy: scope all data to a single organization (defaults to 'Demo Company').
- Event sourcing: on-hand stock is derived from inventory_movements only (no direct stock fields).
- Complete columns: set all non-nullable fields and fill sensible values for nullable ones.

Usage (from backend/ folder with DATABASE_URL set and DB running):
  python scripts/seed_ten_years.py --org "Demo Company" --years 10 \
         --products 20 --start 2015-09-03 --locations 3

Safe to re-run: generates unique order and PO numbers using a run tag.
"""

from __future__ import annotations

import argparse
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Tuple, cast

from sqlalchemy.orm import Session

# Ensure backend/ is on the import path when running this script directly
import os
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Local imports (assumes cwd is backend/)
from app.core.database import SessionLocal
from app.models.organization import Organization
from app.models.location import Location
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.user import User
from app.models.inventory import InventoryMovement
from app.models.order import Order, OrderItem
from app.models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)


@dataclass
class SeedConfig:
    org_name: str
    years: int
    start_date: datetime
    products: int
    locations: int
    seed: int
    weekly_orders_per_store: int
    run_tag: str


CHANNELS = ["pos", "online", "phone"]
LOCATION_TYPES = ["warehouse", "store", "store", "virtual"]  # bias towards stores
CATEGORIES = ["Widgets", "Gadgets", "Accessories", "Consumables"]


def get_or_create_org(db: Session, name: str) -> Organization:
    org = db.query(Organization).filter(Organization.name == name).first()
    if org:
        return org
    org = Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def ensure_users(db: Session, org: Organization) -> User:
    # Prefer existing admin user in this org, else create one
    user = (
        db.query(User)
        .filter(User.org_id == org.id)
        .order_by(User.created_at.asc())
        .first()
    )
    if user:
        return user
    # Create a deterministic seeded user
    user = User(
        org_id=org.id,
        email=f"admin+seed@{org.name.lower().replace(' ', '')}.co",
        # Not used for auth in seed; fill required field
        password_hash="seed-hash-not-for-auth",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_locations(db: Session, org: Organization, count: int) -> List[Location]:
    existing = db.query(Location).filter(Location.org_id == org.id).all()
    if len(existing) >= count:
        return existing
    created: List[Location] = []
    # Always ensure at least one warehouse
    need = count - len(existing)
    i = 0
    while i < need:
        ltype = "warehouse" if i == 0 and not any(l.type == "warehouse" for l in existing) else random.choice(LOCATION_TYPES)
        name = (
            ("Main Warehouse" if ltype == "warehouse" and not any(l.type == "warehouse" for l in existing + created) else f"Store {len(existing)+len(created)+1}")
        )
        loc = Location(
            org_id=org.id,
            name=name,
            type=ltype,
            address=f"{random.randint(100,9999)} Seed St, Seed City",
        )
        db.add(loc)
        created.append(loc)
        i += 1
    db.commit()
    for loc in created:
        db.refresh(loc)
    return existing + created


def ensure_suppliers(db: Session, org: Organization) -> List[Supplier]:
    suppliers = db.query(Supplier).filter(Supplier.org_id == org.id).all()
    if suppliers:
        return suppliers
    names = ["Acme Supply Co", "Gizmo Corp", "Widget Works"]
    created: List[Supplier] = []
    for name in names:
        s = Supplier(
            org_id=org.id,
            name=name,
            contact_person=random.choice(["John Smith", "Jane Doe", "Bob Johnson", "Alice Lee"]),
            email=f"orders@{name.lower().replace(' ', '')}.com",
            phone=f"555-{random.randint(1000, 9999)}",
            address=f"{random.randint(100,9999)} Supply Rd",
            lead_time_days=random.choice([7, 10, 14]),
            minimum_order_quantity=random.choice([1, 5, 10, 25]),
            payment_terms=random.choice(["Net 30", "Net 45", "Prepaid"]),
            is_active="true",
        )
        db.add(s)
        created.append(s)
    db.commit()
    for s in created:
        db.refresh(s)
    return created


def ensure_products(db: Session, org: Organization, suppliers: List[Supplier], target_count: int) -> List[Product]:
    products = db.query(Product).filter(Product.org_id == org.id).all()
    if len(products) >= target_count:
        return products
    created: List[Product] = []
    for i in range(len(products) + 1, target_count + 1):
        cat = random.choice(CATEGORIES)
        base = random.randint(3, 50)
        cost = Decimal(base).quantize(Decimal("0.01"))
        margin = Decimal(random.choice([1.8, 2.0, 2.5, 3.0]))
        price = (cost * margin).quantize(Decimal("0.01"))
        sku = f"{cat[:3].upper()}-{i:03d}"
        p = Product(
            org_id=org.id,
            sku=sku,
            name=f"{cat[:-1]} {i}",
            description=f"Seeded {cat} product number {i}",
            category=cat,
            cost=cost,
            price=price,
            uom="each",
            reorder_point=random.randint(5, 50),
            safety_stock_days=random.choice([3, 5, 7]),
            preferred_supplier_id=random.choice(suppliers).id,
            pack_size=random.choice([1, 5, 10, 20]),
            max_stock_days=random.choice([30, 60, 90]),
        )
        db.add(p)
        created.append(p)
    db.commit()
    for p in created:
        db.refresh(p)
    return products + created


def ensure_initial_stock(db: Session, org: Organization, products: List[Product], warehouse: Location, created_by: uuid.UUID, ts: datetime) -> None:
    # Create an initial adjust movement per product to set baseline inventory
    for p in products:
        qty = random.randint(100, 1000)
        mv = InventoryMovement(
            product_id=p.id,
            location_id=warehouse.id,
            quantity=qty,  # positive adjust to set initial stock
            movement_type="adjust",
            reference="INITIAL-STOCK",
            notes="Initial stock level",
            timestamp=ts,
            created_by=created_by,
        )
        db.add(mv)
    db.commit()


def daterange_weeks(start: datetime, end: datetime) -> List[datetime]:
    days = (end - start).days
    weeks = (days // 7) + 1
    return [start + timedelta(weeks=w) for w in range(weeks)]


def create_order(
    db: Session,
    org: Organization,
    location: Location,
    ordered_at: datetime,
    products: List[Product],
    run_tag: str,
    created_by: uuid.UUID,
) -> Tuple[Order, List[OrderItem]]:
    order_number = f"ORD-{run_tag}-{ordered_at.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    channel = random.choice(CHANNELS)
    order = Order(
        org_id=org.id,
        order_number=order_number,
        channel=channel,
        status="fulfilled",
        ordered_at=ordered_at,
        fulfilled_at=ordered_at + timedelta(days=random.choice([0, 1, 2])),
        location_id=location.id,
        total_amount=Decimal("0.00"),  # will set after items
    )
    db.add(order)
    db.flush()  # assign order.id for items FK

    n_items = random.randint(1, 4)
    chosen = random.sample(products, n_items)
    items: List[OrderItem] = []
    total = Decimal("0.00")
    for prod in chosen:
        qty = random.randint(1, 5)
        unit_price = Decimal(str(prod.price or 0))
        discount = Decimal("0.00")
        item = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            quantity=qty,
            unit_price=unit_price,
            discount=discount,
        )
        db.add(item)
        items.append(item)
        # Create corresponding inventory movement (out)
        mv = InventoryMovement(
            product_id=prod.id,
            location_id=location.id,
            quantity=-qty,  # negative for outbound
            movement_type="out",
            reference=order_number,
            notes=f"Order shipped via {channel}",
            timestamp=ordered_at,
            created_by=created_by,
        )
        db.add(mv)
        total += (unit_price - discount) * qty

    # Assign as float to appease static type checkers on SQLAlchemy Column types
    order.total_amount = float(total)  # type: ignore[assignment]
    return order, items


def create_purchase_order_with_receipt(
    db: Session,
    org: Organization,
    warehouse: Location,
    supplier: Supplier,
    prod_pool: List[Product],
    order_date: datetime,
    run_tag: str,
    created_by: uuid.UUID,
) -> Tuple[PurchaseOrder, List[PurchaseOrderItem]]:
    po_number = f"PO-{run_tag}-{order_date.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    expected_days = int(getattr(supplier, "lead_time_days") or 7)
    expected_date = order_date + timedelta(days=int(expected_days))
    received_date = expected_date + timedelta(days=random.choice([0, 1, 2]))

    po = PurchaseOrder(
        org_id=org.id,
        supplier_id=supplier.id,
        po_number=po_number,
        status=PurchaseOrderStatus.received,
        order_date=order_date,
        expected_date=expected_date,
        received_date=received_date,
        total_amount=0.0,
        notes=f"Auto-seeded PO for {supplier.name}",
        created_by=created_by,
    )
    db.add(po)
    db.flush()

    n_lines = random.randint(2, 6)
    chosen = random.sample(prod_pool, min(n_lines, len(prod_pool)))
    total = 0.0
    items: List[PurchaseOrderItem] = []
    for prod in chosen:
        qty = random.choice([10, 20, 50, 100, 200])
        unit_cost = float(Decimal(str(prod.cost or 0)))
        total_cost = unit_cost * qty
        poi = PurchaseOrderItem(
            purchase_order_id=po.id,
            product_id=prod.id,
            quantity=qty,
            unit_cost=unit_cost,
            total_cost=total_cost,
            received_quantity=qty,
        )
        db.add(poi)
        items.append(poi)
        total += total_cost
        # Create inventory movement for receipt
        mv = InventoryMovement(
            product_id=prod.id,
            location_id=warehouse.id,
            quantity=qty,  # positive for inbound
            movement_type="in",
            reference=po_number,
            notes=f"PO receipt from {supplier.name}",
            timestamp=received_date,
            created_by=created_by,
        )
        db.add(mv)

    # Assign as float to appease static type checkers on SQLAlchemy Column types
    po.total_amount = float(total)  # type: ignore[assignment]
    return po, items


def seed_data(db: Session, cfg: SeedConfig) -> None:
    random.seed(cfg.seed)

    org = get_or_create_org(db, cfg.org_name)
    user = ensure_users(db, org)
    locs = ensure_locations(db, org, cfg.locations)
    suppliers = ensure_suppliers(db, org)
    products = ensure_products(db, org, suppliers, cfg.products)

    # Choose a warehouse and stores
    warehouse = next((l for l in locs if str(getattr(l, "type")) == "warehouse"), None)
    if not warehouse:
        warehouse = locs[0]
    stores = [l for l in locs if str(getattr(l, "type")) != "warehouse"] or [warehouse]

    # Initial stock at start date
    ensure_initial_stock(db, org, products, warehouse, user.id, cfg.start_date)

    end_date = datetime.now(timezone.utc)
    weeks = daterange_weeks(cfg.start_date, end_date)

    # Orders weekly per store
    orders_created = 0
    order_items_created = 0
    for week_start in weeks:
        for store in stores:
            for _ in range(cfg.weekly_orders_per_store):
                # Distribute within the week
                ordered_at = week_start + timedelta(days=random.randint(0, 6))
                order, items = create_order(db, org, store, ordered_at, products, cfg.run_tag, user.id)
                orders_created += 1
                order_items_created += len(items)
        # Commit weekly batch
        db.commit()

    # Monthly purchase orders and receipts into warehouse (aggregate restocking)
    current = datetime(cfg.start_date.year, cfg.start_date.month, 1, tzinfo=timezone.utc)
    while current < end_date:
        # One PO per month per supplier
        for supplier in suppliers:
            # Choose subset of products preferred to this supplier
            sup_products = [p for p in products if p.preferred_supplier_id == supplier.id] or products
            create_purchase_order_with_receipt(
                db,
                org,
                warehouse,
                supplier,
                random.sample(sup_products, min(len(sup_products), random.randint(3, 8))),
                current + timedelta(days=random.randint(0, 27)),
                cfg.run_tag,
                user.id,
            )
        db.commit()
        # Next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            current = datetime(current.year, current.month + 1, 1, tzinfo=timezone.utc)

    print(
        f"Seed complete for org '{org.name}'. Products={len(products)}, Locations={len(locs)}, "
        f"Suppliers={len(suppliers)}. Orders ~{orders_created}, OrderItems ~{order_items_created}."
    )


def parse_args() -> SeedConfig:
    parser = argparse.ArgumentParser(description="Seed 10 years of data into StockPilot DB")
    parser.add_argument("--org", default="Demo Company", help="Organization name to seed")
    parser.add_argument("--years", type=int, default=10, help="Number of years back to seed")
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD; overrides --years if set")
    parser.add_argument("--products", type=int, default=20, help="Number of products to ensure")
    parser.add_argument("--locations", type=int, default=3, help="Number of locations to ensure (>=1)")
    parser.add_argument("--weekly-orders", type=int, default=3, help="Weekly orders per store")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    if args.start:
        try:
            start_date = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise SystemExit("Invalid --start format, expected YYYY-MM-DD")
    else:
        start_date = now - timedelta(days=365 * args.years)

    run_tag = now.strftime("SEED%Y%m%d%H%M%S")

    return SeedConfig(
        org_name=args.org,
        years=args.years,
        start_date=start_date,
        products=max(1, args.products),
        locations=max(1, args.locations),
        seed=args.seed,
        weekly_orders_per_store=max(1, args.weekly_orders),
        run_tag=run_tag,
    )


def main() -> None:
    cfg = parse_args()
    db: Session = SessionLocal()
    try:
        seed_data(db, cfg)
    finally:
        db.close()


if __name__ == "__main__":
    main()
