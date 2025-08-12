"""
Business Intelligence Context Service

Provides comprehensive business context for LLM interactions by gathering
key metrics, inventory status, sales data, and business insights.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class BusinessContext:
    """Gathers and formats business intelligence data for LLM context."""
    
    def __init__(self, db: Session, org_id: str):
        self.db = db
        self.org_id = org_id
        self._context_cache: Optional[Dict[str, Any]] = None
    
    def get_comprehensive_context(self) -> str:
        """Returns a comprehensive business context summary for LLM."""
        try:
            context = self._gather_business_metrics()
            return self._format_context_for_llm(context)
        except Exception as e:
            logger.error(f"Error gathering business context: {e}")
            return "StockPilot inventory management system (context temporarily unavailable)"
    
    def _gather_business_metrics(self) -> Dict[str, Any]:
        """Gather key business metrics from the database."""
        context = {}
        
        # Company overview
        context['company'] = self._get_company_overview()
        
        # Inventory metrics
        context['inventory'] = self._get_inventory_metrics()
        
        # Sales performance
        context['sales'] = self._get_sales_metrics()
        
        # Top performers
        context['top_products'] = self._get_top_products()
        
        # Alerts and risks
        context['risks'] = self._get_business_risks()
        
        # Recent activity
        context['recent_activity'] = self._get_recent_activity()
        
        return context
    
    def _get_company_overview(self) -> Dict[str, Any]:
        """Get basic company metrics."""
        try:
            # Total products
            product_count = self.db.execute(
                text("SELECT COUNT(*) as count FROM products WHERE org_id = :org_id"),
                {"org_id": self.org_id}
            ).fetchone()
            
            # Total locations
            location_count = self.db.execute(
                text("SELECT COUNT(*) as count FROM locations WHERE org_id = :org_id"),
                {"org_id": self.org_id}
            ).fetchone()
            
            return {
                "total_products": product_count.count if product_count else 0,
                "total_locations": location_count.count if location_count else 0,
                "org_id": self.org_id
            }
        except Exception as e:
            logger.error(f"Error getting company overview: {e}")
            return {"total_products": 0, "total_locations": 0, "org_id": self.org_id}
    
    def _get_inventory_metrics(self) -> Dict[str, Any]:
        """Get current inventory status."""
        try:
            # Current inventory levels
            inventory_sql = text("""
                WITH per_product AS (
                    SELECT p.id,
                           COALESCE(SUM(CASE 
                                WHEN im.movement_type IN ('in','adjust') THEN im.quantity 
                                WHEN im.movement_type='out' THEN -im.quantity 
                                ELSE 0 END),0) as on_hand
                    FROM products p
                    LEFT JOIN inventory_movements im ON im.product_id = p.id
                    WHERE p.org_id = :org_id
                    GROUP BY p.id
                )
                SELECT COUNT(*) as total_skus,
                       COUNT(CASE WHEN on_hand <= 0 THEN 1 END) as out_of_stock_count,
                       COUNT(CASE WHEN on_hand BETWEEN 1 AND 10 THEN 1 END) as low_stock_count,
                       SUM(on_hand) as total_units
                FROM per_product
            """)

            result = self.db.execute(inventory_sql, {"org_id": self.org_id}).fetchone()
            
            return {
                "total_skus": result.total_skus if result else 0,
                "out_of_stock": result.out_of_stock_count if result else 0,
                "low_stock": result.low_stock_count if result else 0,
                "total_units": int(result.total_units) if result and result.total_units else 0
            }
        except Exception as e:
            logger.error(f"Error getting inventory metrics: {e}")
            return {"total_skus": 0, "out_of_stock": 0, "low_stock": 0, "total_units": 0}
    
    def _get_sales_metrics(self) -> Dict[str, Any]:
        """Get recent sales performance."""
        try:
            # Try analytics mart first, fallback to base tables
            sales_sql = text("""
                SELECT 
                    SUM(gross_revenue) as revenue_7d,
                    SUM(units_sold) as units_7d,
                    SUM(gross_margin) as margin_7d,
                    AVG(gross_revenue) as avg_daily_revenue
                FROM analytics_marts.sales_daily
                WHERE org_id = :org_id AND sales_date >= (current_date - 7)
            """)
            
            result = self.db.execute(sales_sql, {"org_id": self.org_id}).fetchone()
            
            if result and result.revenue_7d:
                return {
                    "revenue_7d": float(result.revenue_7d),
                    "units_7d": int(result.units_7d or 0),
                    "margin_7d": float(result.margin_7d or 0),
                    "avg_daily_revenue": float(result.avg_daily_revenue or 0)
                }
            else:
                # Fallback: basic order data
                fallback_sql = text("""
                    SELECT COUNT(*) as order_count_7d
                    FROM orders 
                    WHERE org_id = :org_id AND ordered_at >= (current_date - 7)
                """)
                fallback = self.db.execute(fallback_sql, {"org_id": self.org_id}).fetchone()
                return {
                    "order_count_7d": fallback.order_count_7d if fallback else 0,
                    "revenue_7d": 0,
                    "units_7d": 0,
                    "margin_7d": 0
                }
        except Exception as e:
            logger.error(f"Error getting sales metrics: {e}")
            return {"revenue_7d": 0, "units_7d": 0, "margin_7d": 0, "order_count_7d": 0}
    
    def _get_top_products(self) -> Dict[str, Any]:
        """Get top performing products."""
        try:
            top_products_sql = text("""
                SELECT product_name, sku, 
                       SUM(gross_margin) as margin,
                       SUM(units_sold) as units
                FROM analytics_marts.sales_daily
                WHERE org_id = :org_id AND sales_date >= (current_date - 30)
                GROUP BY product_name, sku
                ORDER BY margin DESC
                LIMIT 3
            """)
            
            results = self.db.execute(top_products_sql, {"org_id": self.org_id}).fetchall()
            
            return {
                "top_by_margin": [
                    {
                        "name": r.product_name,
                        "sku": r.sku,
                        "margin": float(r.margin or 0),
                        "units": int(r.units or 0)
                    } for r in results
                ]
            }
        except Exception as e:
            logger.error(f"Error getting top products: {e}")
            return {"top_by_margin": []}
    
    def _get_business_risks(self) -> Dict[str, Any]:
        """Get current business risks and alerts."""
        try:
            # Stockout risk
            stockout_sql = text("""
                SELECT COUNT(*) as high_risk_count
                FROM (
                    SELECT p.sku,
                           COALESCE(SUM(CASE WHEN im.movement_type IN ('in','adjust') THEN im.quantity WHEN im.movement_type='out' THEN -im.quantity ELSE 0 END),0) as on_hand,
                           COALESCE(AVG(sd.units_30day_avg), 0) as velocity
                    FROM products p
                    LEFT JOIN inventory_movements im ON im.product_id = p.id
                    LEFT JOIN analytics_marts.sales_daily sd ON sd.sku = p.sku AND sd.org_id = p.org_id
                    WHERE p.org_id = :org_id
                    GROUP BY p.id, p.sku
                ) stock_analysis
                WHERE velocity > 0 AND (on_hand / velocity) <= 7
            """)
            
            result = self.db.execute(stockout_sql, {"org_id": self.org_id}).fetchone()
            
            return {
                "high_stockout_risk": result.high_risk_count if result else 0,
                "needs_immediate_attention": result.high_risk_count > 5 if result else False
            }
        except Exception as e:
            logger.error(f"Error getting business risks: {e}")
            return {"high_stockout_risk": 0, "needs_immediate_attention": False}
    
    def _get_recent_activity(self) -> Dict[str, Any]:
        """Get recent business activity."""
        try:
            # Recent inventory movements
            movements_sql = text("""
                SELECT COUNT(*) as movements_today
                FROM inventory_movements im
                JOIN products p ON p.id = im.product_id
                WHERE p.org_id = :org_id AND DATE(im."timestamp") = current_date
            """)

            movements = self.db.execute(movements_sql, {"org_id": self.org_id}).fetchone()
            
            return {
                "inventory_movements_today": movements.movements_today if movements else 0,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return {"inventory_movements_today": 0, "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")}
    
    def _format_context_for_llm(self, context: Dict[str, Any]) -> str:
        """Format the business context into a concise summary for LLM."""
        company = context.get('company', {})
        inventory = context.get('inventory', {})
        sales = context.get('sales', {})
        top_products = context.get('top_products', {})
        risks = context.get('risks', {})
        activity = context.get('recent_activity', {})
        
        # Build context summary
        context_parts = [
            "STOCKPILOT BUSINESS CONTEXT:",
            f"• Organization: {company.get('org_id', 'Unknown')}",
            f"• Product Catalog: {company.get('total_products', 0)} products across {company.get('total_locations', 0)} locations",
            "",
            "INVENTORY STATUS:",
            f"• Total SKUs: {inventory.get('total_skus', 0)}",
            f"• Total Units: {inventory.get('total_units', 0):,}",
            f"• Out of Stock: {inventory.get('out_of_stock', 0)} items",
            f"• Low Stock: {inventory.get('low_stock', 0)} items",
            "",
            "RECENT PERFORMANCE (Last 7 Days):",
            f"• Revenue: ${sales.get('revenue_7d', 0):,.2f}",
            f"• Units Sold: {sales.get('units_7d', 0):,}",
            f"• Gross Margin: ${sales.get('margin_7d', 0):,.2f}",
        ]
        
        # Add top products if available
        top_by_margin = top_products.get('top_by_margin', [])
        if top_by_margin:
            context_parts.extend([
                "",
                "TOP PERFORMERS (Last 30 Days):",
            ])
            for i, product in enumerate(top_by_margin[:3], 1):
                context_parts.append(f"• #{i}: {product['name']} (SKU: {product['sku']}) - ${product['margin']:,.2f} margin")
        
        # Add risks if any
        if risks.get('high_stockout_risk', 0) > 0:
            context_parts.extend([
                "",
                "BUSINESS ALERTS:",
                f"• {risks['high_stockout_risk']} products at high stockout risk (≤7 days inventory)",
            ])
            if risks.get('needs_immediate_attention'):
                context_parts.append("• ⚠️ URGENT: Multiple stockouts need immediate attention")
        
        # Add recent activity
        context_parts.extend([
            "",
            f"RECENT ACTIVITY: {activity.get('inventory_movements_today', 0)} inventory movements today",
            f"Data as of: {activity.get('last_updated', 'Unknown')}"
        ])
        
        return "\n".join(context_parts)

def get_business_context(db: Session, org_id: str) -> str:
    """Get comprehensive business context for LLM interactions."""
    business_context = BusinessContext(db, org_id)
    return business_context.get_comprehensive_context()
