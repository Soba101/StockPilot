from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc, func
from datetime import datetime
from app.core.database import get_db, get_current_claims, require_role
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.models.supplier import Supplier
from app.models.product import Product
from app.schemas import purchasing as schemas

router = APIRouter()


def generate_po_number(db: Session, org_id: str) -> str:
    """Generate next PO number for organization"""
    # Get last PO number for this org
    last_po = db.query(PurchaseOrder).filter(
        PurchaseOrder.org_id == org_id
    ).order_by(desc(PurchaseOrder.created_at)).first()
    
    if last_po and last_po.po_number.startswith('PO-'):
        try:
            last_num = int(last_po.po_number.split('-')[1])
            return f"PO-{last_num + 1:04d}"
        except (IndexError, ValueError):
            pass
    
    # Default starting number
    return "PO-1001"


@router.get("/purchase-orders", response_model=List[schemas.PurchaseOrderSummary])
def get_purchase_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[PurchaseOrderStatus] = Query(None),
    supplier_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """Get purchase orders with filtering"""
    
    org_id = claims.get("org")
    
    query = db.query(PurchaseOrder).join(Supplier).filter(
        PurchaseOrder.org_id == org_id
    )
    
    if status:
        query = query.filter(PurchaseOrder.status == status)
    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)
    
    purchase_orders = query.order_by(desc(PurchaseOrder.created_at)).offset(skip).limit(limit).all()
    
    # Transform to summary format
    result = []
    for po in purchase_orders:
        item_count = db.query(func.count(PurchaseOrderItem.id)).filter(
            PurchaseOrderItem.purchase_order_id == po.id
        ).scalar() or 0
        
        summary = schemas.PurchaseOrderSummary(
            id=str(po.id),
            po_number=po.po_number,
            supplier_name=po.supplier.name,
            status=po.status,
            total_amount=po.total_amount,
            order_date=po.order_date,
            expected_date=po.expected_date,
            item_count=item_count
        )
        result.append(summary)
    
    return result


@router.get("/purchase-orders/{po_id}", response_model=schemas.PurchaseOrder)
def get_purchase_order(
    po_id: str,
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """Get specific purchase order details"""
    
    org_id = claims.get("org")
    
    po = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.supplier),
        joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product)
    ).filter(
        PurchaseOrder.id == po_id,
        PurchaseOrder.org_id == org_id
    ).first()
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    # Transform the data
    items = []
    for item in po.items:
        item_data = schemas.PurchaseOrderItem(
            id=str(item.id),
            purchase_order_id=str(item.purchase_order_id),
            product_id=str(item.product_id),
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            total_cost=item.total_cost,
            received_quantity=item.received_quantity,
            created_at=item.created_at,
            updated_at=item.updated_at,
            product_name=item.product.name if item.product else None,
            product_sku=item.product.sku if item.product else None
        )
        items.append(item_data)
    
    result = schemas.PurchaseOrder(
        id=str(po.id),
        org_id=str(po.org_id),
        supplier_id=str(po.supplier_id),
        po_number=po.po_number,
        status=po.status,
        order_date=po.order_date,
        expected_date=po.expected_date,
        received_date=po.received_date,
        total_amount=po.total_amount,
        notes=po.notes,
        created_at=po.created_at,
        updated_at=po.updated_at,
        created_by=str(po.created_by) if po.created_by else None,
        supplier_name=po.supplier.name,
        items=items
    )
    
    return result


@router.post("/purchase-orders", response_model=schemas.PurchaseOrder)
def create_purchase_order(
    po_data: schemas.PurchaseOrderCreate,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin")),
):
    """Create a new purchase order"""
    
    org_id = claims.get("org")
    user_id = claims.get("sub")
    
    # Verify supplier belongs to org
    supplier = db.query(Supplier).filter(
        Supplier.id == po_data.supplier_id,
        Supplier.org_id == org_id
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Verify all products belong to org
    product_ids = [item.product_id for item in po_data.items]
    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.org_id == org_id
    ).all()
    if len(products) != len(product_ids):
        raise HTTPException(status_code=404, detail="One or more products not found")
    
    # Generate PO number if not provided
    po_number = po_data.po_number
    if not po_number or po_number.strip() == "":
        po_number = generate_po_number(db, org_id)
    
    # Calculate total amount
    total_amount = sum(item.quantity * item.unit_cost for item in po_data.items)
    
    # Create purchase order
    db_po = PurchaseOrder(
        org_id=org_id,
        supplier_id=po_data.supplier_id,
        po_number=po_number,
        expected_date=po_data.expected_date,
        notes=po_data.notes,
        total_amount=total_amount,
        created_by=user_id
    )
    db.add(db_po)
    db.flush()  # Get the ID
    
    # Create purchase order items
    for item_data in po_data.items:
        total_cost = item_data.quantity * item_data.unit_cost
        db_item = PurchaseOrderItem(
            purchase_order_id=db_po.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit_cost=item_data.unit_cost,
            total_cost=total_cost
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_po)
    
    # Return the created PO
    return get_purchase_order(str(db_po.id), db, claims)


@router.put("/purchase-orders/{po_id}/status", response_model=schemas.PurchaseOrder)
def update_purchase_order_status(
    po_id: str,
    status_update: schemas.PurchaseOrderStatusUpdate,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin")),
):
    """Update purchase order status"""
    
    org_id = claims.get("org")
    
    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.id == po_id,
        PurchaseOrder.org_id == org_id
    ).first()
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    # Update status
    po.status = status_update.status
    
    if status_update.notes:
        po.notes = status_update.notes
    
    # Set order date when status changes to ordered
    if status_update.status == PurchaseOrderStatus.ordered and not po.order_date:
        po.order_date = datetime.utcnow()
    
    # Set received date when status changes to received
    if status_update.status == PurchaseOrderStatus.received:
        if status_update.received_date:
            po.received_date = status_update.received_date
        elif not po.received_date:
            po.received_date = datetime.utcnow()
    
    db.commit()
    db.refresh(po)
    
    return get_purchase_order(po_id, db, claims)


@router.delete("/purchase-orders/{po_id}")
def delete_purchase_order(
    po_id: str,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin")),
):
    """Delete a purchase order (only if draft status)"""
    
    org_id = claims.get("org")
    
    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.id == po_id,
        PurchaseOrder.org_id == org_id
    ).first()
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    if po.status != PurchaseOrderStatus.draft:
        raise HTTPException(
            status_code=400, 
            detail="Can only delete purchase orders in draft status"
        )
    
    db.delete(po)
    db.commit()
    
    return {"message": "Purchase order deleted successfully"}