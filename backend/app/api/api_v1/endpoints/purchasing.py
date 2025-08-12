from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc, func
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from app.core.database import get_db, get_current_claims, require_role
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.models.supplier import Supplier
from app.models.product import Product
from app.schemas import purchasing as schemas
from app.schemas import reorder as reorder_schemas
from app.services.reorder import compute_reorder_suggestions, explain_reorder_suggestion

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


# ===== REORDER SUGGESTIONS ENDPOINTS =====

@router.get("/reorder-suggestions", response_model=reorder_schemas.ReorderSuggestionsResponse)
def get_reorder_suggestions(
    location_id: Optional[str] = Query(None),
    strategy: str = Query("latest", regex="^(latest|conservative)$"),
    horizon_days_override: Optional[int] = Query(None, gt=0, le=365),
    include_zero_velocity: bool = Query(False),
    min_days_cover: Optional[int] = Query(None, gt=0),
    max_days_cover: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """
    Get reorder suggestions based on velocity, lead times, MOQ, and safety stock.
    Implements the W5 purchase suggestions algorithm.
    """
    
    org_id_str = claims.get("org")
    if not org_id_str:
        raise HTTPException(status_code=401, detail="Organization ID required")
    
    org_id = uuid.UUID(org_id_str)
    location_uuid = uuid.UUID(location_id) if location_id else None
    
    # Validate horizon override
    if horizon_days_override and (horizon_days_override < 1 or horizon_days_override > 365):
        raise HTTPException(status_code=400, detail="Horizon override must be between 1 and 365 days")
    
    try:
        # Compute suggestions using the reorder service
        suggestions = compute_reorder_suggestions(
            org_id=org_id,
            location_id=location_uuid,
            strategy=strategy,  # type: ignore
            horizon_days_override=horizon_days_override
        )
        
        # Apply additional filters
        filtered_suggestions = []
        for suggestion in suggestions:
            # Skip zero velocity products unless explicitly included
            if not include_zero_velocity and (suggestion.chosen_velocity is None or suggestion.chosen_velocity == 0):
                continue
            
            # Apply coverage filters
            if min_days_cover and suggestion.days_cover_current and suggestion.days_cover_current < min_days_cover:
                continue
            if max_days_cover and suggestion.days_cover_current and suggestion.days_cover_current > max_days_cover:
                continue
            
            filtered_suggestions.append(suggestion)
        
        # Convert to response format
        suggestion_responses = []
        for suggestion in filtered_suggestions:
            suggestion_responses.append(reorder_schemas.ReorderSuggestionResponse(
                product_id=suggestion.product_id,
                sku=suggestion.sku,
                name=suggestion.name,
                supplier_id=suggestion.supplier_id,
                supplier_name=suggestion.supplier_name,
                on_hand=suggestion.on_hand,
                incoming=suggestion.incoming,
                days_cover_current=suggestion.days_cover_current,
                days_cover_after=suggestion.days_cover_after,
                recommended_quantity=suggestion.recommended_quantity,
                chosen_velocity=suggestion.chosen_velocity,
                velocity_source=suggestion.velocity_source,
                horizon_days=suggestion.horizon_days,
                demand_forecast_units=suggestion.demand_forecast_units,
                reasons=suggestion.reasons,
                adjustments=suggestion.adjustments
            ))
        
        # Create summary statistics
        total_suggestions = len(suggestion_responses)
        total_recommended_quantity = sum(s.recommended_quantity for s in suggestion_responses)
        suppliers_involved = len(set(s.supplier_id for s in suggestion_responses if s.supplier_id))
        
        # Reason breakdown
        all_reasons = []
        for s in suggestion_responses:
            all_reasons.extend(s.reasons)
        reason_counts = {}
        for reason in set(all_reasons):
            reason_counts[reason] = all_reasons.count(reason)
        
        summary = {
            "total_suggestions": total_suggestions,
            "total_recommended_quantity": total_recommended_quantity,
            "suppliers_involved": suppliers_involved,
            "reason_breakdown": reason_counts,
            "strategy_used": strategy,
            "filters_applied": {
                "include_zero_velocity": include_zero_velocity,
                "min_days_cover": min_days_cover,
                "max_days_cover": max_days_cover,
                "horizon_days_override": horizon_days_override
            }
        }
        
        # Build request object for response
        request_params = reorder_schemas.ReorderSuggestionsRequest(
            location_id=location_uuid,
            strategy=strategy,  # type: ignore
            horizon_days_override=horizon_days_override,
            include_zero_velocity=include_zero_velocity,
            min_days_cover=min_days_cover,
            max_days_cover=max_days_cover
        )
        
        return reorder_schemas.ReorderSuggestionsResponse(
            suggestions=suggestion_responses,
            summary=summary,
            generated_at=datetime.utcnow(),
            parameters=request_params
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing reorder suggestions: {str(e)}")


@router.get("/reorder-suggestions/explain/{product_id}", response_model=reorder_schemas.ReorderExplanationResponse)
def explain_reorder_suggestion_endpoint(
    product_id: str,
    strategy: str = Query("latest", regex="^(latest|conservative)$"),
    horizon_days_override: Optional[int] = Query(None, gt=0, le=365),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """
    Get detailed explanation for a single product's reorder calculation.
    Shows intermediate values and logic path for transparency.
    """
    
    org_id_str = claims.get("org")
    if not org_id_str:
        raise HTTPException(status_code=401, detail="Organization ID required")
    
    try:
        org_id = uuid.UUID(org_id_str)
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    try:
        explanation = explain_reorder_suggestion(
            org_id=org_id,
            product_id=product_uuid,
            strategy=strategy,  # type: ignore
            horizon_days_override=horizon_days_override
        )
        
        if not explanation:
            raise HTTPException(status_code=404, detail="Product not found or no data available")
        
        return reorder_schemas.ReorderExplanationResponse(**explanation)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error explaining reorder suggestion: {str(e)}")


@router.post("/reorder-suggestions/draft-po", response_model=reorder_schemas.DraftPOResponse)
def create_draft_purchase_orders(
    request: reorder_schemas.DraftPORequest,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin")),
):
    """
    Create draft purchase orders from selected reorder suggestions.
    Groups by supplier and applies MOQ/pack rounding adjustments.
    """
    
    org_id_str = claims.get("org")
    if not org_id_str:
        raise HTTPException(status_code=401, detail="Organization ID required")
    
    org_id = uuid.UUID(org_id_str)
    
    if not request.product_ids:
        raise HTTPException(status_code=400, detail="No products selected")
    
    try:
        # Get suggestions for selected products
        all_suggestions = compute_reorder_suggestions(
            org_id=org_id,
            location_id=None,  # TODO: Support location filtering
            strategy=request.strategy,
            horizon_days_override=request.horizon_days_override
        )
        
        # Filter to only selected products
        selected_suggestions = [
            s for s in all_suggestions 
            if s.product_id in request.product_ids and s.recommended_quantity > 0
        ]
        
        if not selected_suggestions:
            raise HTTPException(status_code=400, detail="No valid suggestions found for selected products")
        
        # Group by supplier
        supplier_groups = {}
        for suggestion in selected_suggestions:
            supplier_id = suggestion.supplier_id
            if not supplier_id:
                continue  # Skip products without suppliers
            
            if supplier_id not in supplier_groups:
                supplier_groups[supplier_id] = []
            supplier_groups[supplier_id].append(suggestion)
        
        if not supplier_groups:
            raise HTTPException(status_code=400, detail="No suppliers found for selected products")
        
        # Create draft POs
        draft_pos = []
        po_counter = 1
        
        for supplier_id, suggestions in supplier_groups.items():
            # Get supplier details
            supplier = db.query(Supplier).filter(
                Supplier.id == supplier_id,
                Supplier.org_id == org_id
            ).first()
            
            if not supplier:
                continue  # Skip if supplier not found
            
            # Generate PO number
            if request.auto_number:
                base_po_number = generate_po_number(db, org_id_str)
                if len(supplier_groups) > 1:
                    po_number = f"{base_po_number}-{po_counter:02d}"
                    po_counter += 1
                else:
                    po_number = base_po_number
            else:
                po_number = f"DRAFT-{datetime.utcnow().strftime('%Y%m%d')}-{po_counter:02d}"
                po_counter += 1
            
            # Create items
            draft_items = []
            total_quantity = 0
            estimated_total = Decimal('0.00')
            
            for suggestion in suggestions:
                # Get product details for costing
                product = db.query(Product).filter(
                    Product.id == suggestion.product_id,
                    Product.org_id == org_id
                ).first()
                
                unit_cost = product.cost if product and product.cost else None
                line_total = None
                if unit_cost:
                    line_total = unit_cost * suggestion.recommended_quantity
                    estimated_total += line_total
                
                draft_item = reorder_schemas.DraftPOItem(
                    product_id=suggestion.product_id,
                    sku=suggestion.sku,
                    product_name=suggestion.name,
                    quantity=suggestion.recommended_quantity,
                    unit_cost=unit_cost,
                    line_total=line_total,
                    on_hand=suggestion.on_hand,
                    recommended_quantity=suggestion.recommended_quantity,
                    reasons=suggestion.reasons,
                    adjustments=suggestion.adjustments
                )
                draft_items.append(draft_item)
                total_quantity += suggestion.recommended_quantity
            
            # Calculate expected delivery
            expected_delivery = None
            if supplier.lead_time_days:
                expected_delivery = datetime.utcnow() + timedelta(days=supplier.lead_time_days)
            
            draft_po = reorder_schemas.DraftPO(
                supplier_id=supplier_id,
                supplier_name=supplier.name,
                po_number=po_number,
                items=draft_items,
                total_items=len(draft_items),
                total_quantity=total_quantity,
                estimated_total=estimated_total if estimated_total > 0 else None,
                lead_time_days=supplier.lead_time_days,
                minimum_order_quantity=supplier.minimum_order_quantity,
                payment_terms=supplier.payment_terms,
                created_at=datetime.utcnow(),
                expected_delivery=expected_delivery
            )
            
            draft_pos.append(draft_po)
        
        # Create summary
        total_draft_pos = len(draft_pos)
        total_items = sum(po.total_items for po in draft_pos)
        total_quantity_all = sum(po.total_quantity for po in draft_pos)
        total_estimated = sum(po.estimated_total for po in draft_pos if po.estimated_total)
        
        summary = {
            "total_draft_pos": total_draft_pos,
            "total_items": total_items,
            "total_quantity": total_quantity_all,
            "total_estimated_value": total_estimated if total_estimated > 0 else None,
            "suppliers": [po.supplier_name for po in draft_pos]
        }
        
        return reorder_schemas.DraftPOResponse(
            draft_pos=draft_pos,
            summary=summary,
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating draft purchase orders: {str(e)}")