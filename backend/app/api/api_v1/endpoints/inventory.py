from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, desc, case
from datetime import datetime, date
from app.core.database import get_db, get_current_claims, require_role
from app.models.inventory import InventoryMovement
from app.models.product import Product
from app.models.location import Location
from app.schemas import inventory as schemas

router = APIRouter()


@router.post("/movements", response_model=schemas.InventoryMovement)
def create_movement(
    movement: schemas.InventoryMovementCreate,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin")),
):
    """Record a new inventory movement"""
    
    # Verify product and location belong to user's org
    org_id = claims.get("org")
    user_id = claims.get("sub")
    
    product = db.query(Product).filter(
        Product.id == movement.product_id,
        Product.org_id == org_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    location = db.query(Location).filter(
        Location.id == movement.location_id,
        Location.org_id == org_id
    ).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Create movement
    db_movement = InventoryMovement(
        **movement.dict(),
        created_by=user_id
    )
    db.add(db_movement)
    db.commit()
    db.refresh(db_movement)
    return db_movement


@router.get("/movements", response_model=List[schemas.InventoryMovementWithDetails])
def get_movements(
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    movement_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """Get inventory movements with filtering"""
    
    org_id = claims.get("org")
    
    # Base query with joins for product and location names
    query = db.query(InventoryMovement).join(Product).join(Location).filter(
        Product.org_id == org_id,
        Location.org_id == org_id
    )
    
    # Apply filters
    if product_id:
        query = query.filter(InventoryMovement.product_id == product_id)
    if location_id:
        query = query.filter(InventoryMovement.location_id == location_id)
    if movement_type:
        query = query.filter(InventoryMovement.movement_type == movement_type)
    if start_date:
        query = query.filter(InventoryMovement.timestamp >= start_date)
    if end_date:
        query = query.filter(InventoryMovement.timestamp <= end_date)
    
    movements = query.order_by(desc(InventoryMovement.timestamp)).offset(skip).limit(limit).all()
    
    # Transform to include product and location details
    result = []
    for movement in movements:
        movement_dict = {
            "id": movement.id,
            "product_id": movement.product_id,
            "location_id": movement.location_id,
            "quantity": movement.quantity,
            "movement_type": movement.movement_type,
            "reference": movement.reference,
            "notes": movement.notes,
            "timestamp": movement.timestamp,
            "created_by": movement.created_by,
            "created_at": movement.created_at,
            "product_name": movement.product.name,
            "product_sku": movement.product.sku,
            "location_name": movement.location.name,
        }
        result.append(schemas.InventoryMovementWithDetails(**movement_dict))
    
    return result


@router.get("/movements/{movement_id}", response_model=schemas.InventoryMovementWithDetails)
def get_movement(
    movement_id: str,
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """Get specific movement details"""
    
    org_id = claims.get("org")
    
    movement = db.query(InventoryMovement).join(Product).join(Location).filter(
        InventoryMovement.id == movement_id,
        Product.org_id == org_id,
        Location.org_id == org_id
    ).first()
    
    if not movement:
        raise HTTPException(status_code=404, detail="Movement not found")
    
    movement_dict = {
        "id": movement.id,
        "product_id": movement.product_id,
        "location_id": movement.location_id,
        "quantity": movement.quantity,
        "movement_type": movement.movement_type,
        "reference": movement.reference,
        "notes": movement.notes,
        "timestamp": movement.timestamp,
        "created_by": movement.created_by,
        "created_at": movement.created_at,
        "product_name": movement.product.name,
        "product_sku": movement.product.sku,
        "location_name": movement.location.name,
    }
    
    return schemas.InventoryMovementWithDetails(**movement_dict)


@router.get("/summary", response_model=schemas.InventorySummaryResponse)
def get_inventory_summary(
    location_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """Get current inventory summary with stock levels"""
    
    org_id = claims.get("org")
    
    # Calculate current stock levels by aggregating movements
    stock_query = db.query(
        InventoryMovement.product_id,
        InventoryMovement.location_id,
        func.sum(
            case(
                (InventoryMovement.movement_type.in_(['in', 'adjust']), InventoryMovement.quantity),
                else_=-InventoryMovement.quantity
            )
        ).label('on_hand_quantity'),
        func.max(InventoryMovement.timestamp).label('last_movement_date')
    ).join(Product).join(Location).filter(
        Product.org_id == org_id,
        Location.org_id == org_id
    ).group_by(
        InventoryMovement.product_id,
        InventoryMovement.location_id
    )
    
    if location_id:
        stock_query = stock_query.filter(InventoryMovement.location_id == location_id)
    
    stock_results = stock_query.all()
    
    # Get product and location details
    stock_summaries = []
    location_summaries = {}
    
    for stock in stock_results:
        if stock.on_hand_quantity <= 0:
            continue
            
        product = db.query(Product).filter(Product.id == stock.product_id).first()
        location = db.query(Location).filter(Location.id == stock.location_id).first()
        
        available_quantity = max(stock.on_hand_quantity, 0)  # Simple calculation for now
        is_low_stock = product.reorder_point and available_quantity <= product.reorder_point
        is_out_of_stock = available_quantity == 0
        
        stock_summary = schemas.StockSummary(
            product_id=stock.product_id,
            product_name=product.name,
            product_sku=product.sku,
            location_id=stock.location_id,
            location_name=location.name,
            on_hand_quantity=stock.on_hand_quantity,
            available_quantity=available_quantity,
            reorder_point=product.reorder_point,
            is_low_stock=is_low_stock,
            is_out_of_stock=is_out_of_stock,
            last_movement_date=stock.last_movement_date
        )
        
        stock_summaries.append(stock_summary)
        
        # Group by location
        if stock.location_id not in location_summaries:
            location_summaries[stock.location_id] = {
                'location_id': stock.location_id,
                'location_name': location.name,
                'products': [],
                'low_stock_count': 0,
                'out_of_stock_count': 0,
                'total_stock_value': 0.0
            }
        
        location_summaries[stock.location_id]['products'].append(stock_summary)
        if is_low_stock:
            location_summaries[stock.location_id]['low_stock_count'] += 1
        if is_out_of_stock:
            location_summaries[stock.location_id]['out_of_stock_count'] += 1
        
        stock_value = stock.on_hand_quantity * (product.cost or 0)
        location_summaries[stock.location_id]['total_stock_value'] += stock_value
    
    # Build location summaries
    locations = []
    for loc_data in location_summaries.values():
        locations.append(schemas.LocationStockSummary(
            location_id=loc_data['location_id'],
            location_name=loc_data['location_name'],
            total_products=len(loc_data['products']),
            low_stock_count=loc_data['low_stock_count'],
            out_of_stock_count=loc_data['out_of_stock_count'],
            total_stock_value=loc_data['total_stock_value'],
            products=loc_data['products']
        ))
    
    # Calculate totals
    total_products = len(stock_summaries)
    total_low_stock = sum(1 for s in stock_summaries if s.is_low_stock)
    total_out_of_stock = sum(1 for s in stock_summaries if s.is_out_of_stock)
    total_stock_value = sum(loc.total_stock_value for loc in locations)
    
    return schemas.InventorySummaryResponse(
        total_products=total_products,
        total_locations=len(locations),
        low_stock_count=total_low_stock,
        out_of_stock_count=total_out_of_stock,
        total_stock_value=total_stock_value,
        locations=locations
    )


@router.post("/adjust", response_model=List[schemas.InventoryMovement])
def adjust_stock(
    adjustment: schemas.BulkStockAdjustment,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin")),
):
    """Perform bulk stock adjustments"""
    
    org_id = claims.get("org")
    user_id = claims.get("sub")
    created_movements = []
    
    for adj in adjustment.adjustments:
        # Verify product and location
        product = db.query(Product).filter(
            Product.id == adj.product_id,
            Product.org_id == org_id
        ).first()
        if not product:
            continue
            
        location = db.query(Location).filter(
            Location.id == adj.location_id,
            Location.org_id == org_id
        ).first()
        if not location:
            continue
        
        # Calculate current stock
        current_stock = db.query(
            func.sum(
                func.case(
                    (InventoryMovement.movement_type.in_(['in', 'adjust']), InventoryMovement.quantity),
                    else_=-InventoryMovement.quantity
                )
            )
        ).filter(
            InventoryMovement.product_id == adj.product_id,
            InventoryMovement.location_id == adj.location_id
        ).scalar() or 0
        
        # Calculate adjustment needed
        adjustment_qty = adj.new_quantity - current_stock
        
        if adjustment_qty != 0:
            movement = InventoryMovement(
                product_id=adj.product_id,
                location_id=adj.location_id,
                quantity=abs(adjustment_qty),
                movement_type='adjust',
                reference=f"Stock adjustment: {adj.reason}",
                notes=adj.notes,
                timestamp=datetime.utcnow(),
                created_by=user_id
            )
            
            # If adjustment is negative, record as 'out' movement
            if adjustment_qty < 0:
                movement.movement_type = 'out'
                movement.reference = f"Stock reduction: {adj.reason}"
            
            db.add(movement)
            created_movements.append(movement)
    
    db.commit()
    for movement in created_movements:
        db.refresh(movement)
    
    return created_movements


@router.post("/transfer", response_model=List[schemas.InventoryMovement])
def transfer_stock(
    transfer: schemas.StockTransfer,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin")),
):
    """Transfer stock between locations"""
    
    org_id = claims.get("org")
    user_id = claims.get("sub")
    
    # Verify product and locations
    product = db.query(Product).filter(
        Product.id == transfer.product_id,
        Product.org_id == org_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    from_location = db.query(Location).filter(
        Location.id == transfer.from_location_id,
        Location.org_id == org_id
    ).first()
    if not from_location:
        raise HTTPException(status_code=404, detail="From location not found")
    
    to_location = db.query(Location).filter(
        Location.id == transfer.to_location_id,
        Location.org_id == org_id
    ).first()
    if not to_location:
        raise HTTPException(status_code=404, detail="To location not found")
    
    # Check available stock
    available_stock = db.query(
        func.sum(
            case(
                (InventoryMovement.movement_type.in_(['in', 'adjust']), InventoryMovement.quantity),
                else_=-InventoryMovement.quantity
            )
        )
    ).filter(
        InventoryMovement.product_id == transfer.product_id,
        InventoryMovement.location_id == transfer.from_location_id
    ).scalar() or 0
    
    if available_stock < transfer.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Available: {available_stock}, Requested: {transfer.quantity}"
        )
    
    # Create transfer movements
    reference = transfer.reference or f"Transfer {from_location.name} → {to_location.name}"
    timestamp = datetime.utcnow()
    
    # Out movement from source location
    out_movement = InventoryMovement(
        product_id=transfer.product_id,
        location_id=transfer.from_location_id,
        quantity=transfer.quantity,
        movement_type='transfer',
        reference=reference,
        notes=transfer.notes,
        timestamp=timestamp,
        created_by=user_id
    )
    
    # In movement to destination location
    in_movement = InventoryMovement(
        product_id=transfer.product_id,
        location_id=transfer.to_location_id,
        quantity=transfer.quantity,
        movement_type='in',
        reference=reference,
        notes=f"Transfer from {from_location.name}. {transfer.notes or ''}".strip(),
        timestamp=timestamp,
        created_by=user_id
    )
    
    db.add(out_movement)
    db.add(in_movement)
    db.commit()
    
    db.refresh(out_movement)
    db.refresh(in_movement)
    
    return [out_movement, in_movement]