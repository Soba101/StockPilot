"""Database tools for LLM function calling."""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.inventory import InventoryMovement
from datetime import datetime, timedelta
import json
import uuid

class DatabaseTools:
    """Safe database query tools for LLM function calling."""
    
    def __init__(self, db: Session, org_id: str):
        self.db = db
        # Ensure org_id is a valid UUID string
        try:
            uuid.UUID(org_id)
            self.org_id = org_id
        except ValueError:
            # Generate a test UUID if invalid
            self.org_id = str(uuid.uuid4())
    
    def get_total_sales(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get total sales for a date range."""
        try:
            query = self.db.query(
                func.sum(OrderItem.quantity * OrderItem.unit_price).label('total_revenue'),
                func.sum(OrderItem.quantity).label('total_units'),
                func.count(func.distinct(Order.id)).label('total_orders')
            ).join(Order).filter(Order.org_id == self.org_id)
            
            if start_date:
                query = query.filter(Order.ordered_at >= start_date)
            if end_date:
                query = query.filter(Order.ordered_at <= end_date)
            
            result = query.first()
            if result:
                return {
                    "total_revenue": float(result[0] or 0),
                    "total_units": int(result[1] or 0),
                    "total_orders": int(result[2] or 0),
                    "period": f"{start_date or 'start'} to {end_date or 'now'}"
                }
            else:
                return {
                    "total_revenue": 0.0,
                    "total_units": 0,
                    "total_orders": 0,
                    "period": f"{start_date or 'start'} to {end_date or 'now'}"
                }
        except Exception as e:
            return {"error": str(e)}
    
    def get_top_products_by_revenue(self, limit: int = 10, start_date: Optional[str] = None) -> Dict[str, Any]:
        """Get top products by revenue."""
        try:
            query = self.db.query(
                Product.name,
                Product.sku,
                func.sum(OrderItem.quantity * OrderItem.unit_price).label('revenue'),
                func.sum(OrderItem.quantity).label('units')
            ).join(OrderItem).join(Order).filter(
                Product.org_id == self.org_id,
                Order.org_id == self.org_id
            )
            
            if start_date:
                query = query.filter(Order.ordered_at >= start_date)
            
            results = query.group_by(Product.id, Product.name, Product.sku)\
                          .order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc())\
                          .limit(limit).all()
            
            return {
                "products": [
                    {
                        "name": r.name,
                        "sku": r.sku,
                        "revenue": float(r.revenue),
                        "units": int(r.units)
                    } for r in results
                ],
                "count": len(results)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_current_inventory_levels(self, low_stock_threshold: int = 10) -> Dict[str, Any]:
        """Get current inventory levels with low stock alerts."""
        try:
            # Get current stock levels using event sourcing pattern
            stock_query = text("""
                SELECT 
                    p.name,
                    p.sku,
                    p.reorder_point,
                    COALESCE(SUM(im.quantity), 0) as current_stock
                FROM products p
                LEFT JOIN inventory_movements im ON p.id = im.product_id
                WHERE p.org_id = :org_id
                GROUP BY p.id, p.name, p.sku, p.reorder_point
                ORDER BY current_stock ASC
            """)
            
            results = self.db.execute(stock_query, {"org_id": self.org_id}).fetchall()
            
            products = []
            low_stock_count = 0
            
            for r in results:
                current_stock = int(r.current_stock)
                reorder_point = r.reorder_point or low_stock_threshold
                is_low_stock = current_stock <= reorder_point
                
                if is_low_stock:
                    low_stock_count += 1
                
                products.append({
                    "name": r.name,
                    "sku": r.sku,
                    "current_stock": current_stock,
                    "reorder_point": reorder_point,
                    "is_low_stock": is_low_stock,
                    "status": "LOW STOCK" if is_low_stock else "OK"
                })
            
            return {
                "products": products,
                "total_products": len(products),
                "low_stock_count": low_stock_count,
                "low_stock_percentage": round((low_stock_count / len(products)) * 100, 1) if products else 0
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_products_needing_reorder(self) -> Dict[str, Any]:
        """Get products that need reordering based on current stock vs reorder point."""
        try:
            reorder_query = text("""
                SELECT 
                    p.name,
                    p.sku,
                    p.reorder_point,
                    COALESCE(SUM(im.quantity), 0) as current_stock,
                    (p.reorder_point - COALESCE(SUM(im.quantity), 0)) as shortage
                FROM products p
                LEFT JOIN inventory_movements im ON p.id = im.product_id
                WHERE p.org_id = :org_id
                GROUP BY p.id, p.name, p.sku, p.reorder_point
                HAVING COALESCE(SUM(im.quantity), 0) <= COALESCE(p.reorder_point, 0)
                ORDER BY shortage DESC
            """)
            
            results = self.db.execute(reorder_query, {"org_id": self.org_id}).fetchall()
            
            reorder_suggestions = []
            for r in results:
                reorder_suggestions.append({
                    "name": r.name,
                    "sku": r.sku,
                    "current_stock": int(r.current_stock),
                    "reorder_point": r.reorder_point,
                    "suggested_quantity": 50,  # Default suggestion
                    "shortage": int(r.shortage),
                    "priority": "URGENT" if r.shortage > 10 else "MEDIUM"
                })
            
            return {
                "reorder_suggestions": reorder_suggestions,
                "total_items_to_reorder": len(reorder_suggestions),
                "urgent_count": len([r for r in reorder_suggestions if r["priority"] == "URGENT"])
            }
        except Exception as e:
            return {"error": str(e)}

def get_database_tools_schema() -> List[Dict[str, Any]]:
    """Get the function schema for LLM tool calling."""
    return [
        {
            "name": "get_total_sales",
            "description": "Get total sales revenue, units, and orders for a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "format": "date", "description": "End date (YYYY-MM-DD)"}
                }
            }
        },
        {
            "name": "get_top_products_by_revenue",
            "description": "Get top performing products by revenue",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                    "start_date": {"type": "string", "format": "date", "description": "Start date (YYYY-MM-DD)"}
                }
            }
        },
        {
            "name": "get_current_inventory_levels",
            "description": "Get current inventory levels and identify low stock items",
            "parameters": {
                "type": "object",
                "properties": {
                    "low_stock_threshold": {"type": "integer", "minimum": 1, "default": 10}
                }
            }
        },
        {
            "name": "get_products_needing_reorder",
            "description": "Get products that need reordering based on reorder points",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    ]
