"""Business Intelligence Context Service.

Provides concise, multi-section operational snapshot (inventory, sales,
top/bottom performers, risks, slow movers, reorder suggestions) to ground
LLM answers. All queries are org-scoped for multi-tenant safety.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BusinessContext:
    """Gather and format business intelligence data for LLM context."""

    def __init__(self, db: Session, org_id: str):
        self.db = db
        self.org_id = org_id
        self._context_cache: Optional[Dict[str, Any]] = None

    # -------- Public API --------
    def get_comprehensive_context(self) -> str:
        try:
            ctx = self._gather_business_metrics()
            return self._format_context_for_llm(ctx)
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error gathering business context: {e}")
            return "StockPilot inventory management system (context temporarily unavailable)"

    # -------- Gathering --------
    def _gather_business_metrics(self) -> Dict[str, Any]:
        ctx: Dict[str, Any] = {}
        ctx['company'] = self._get_company_overview()
        ctx['inventory'] = self._get_inventory_metrics()
        ctx['sales'] = self._get_sales_metrics()
        ctx['top_products'] = self._get_top_products()
        ctx['bottom_products'] = self._get_bottom_products()
        ctx['risks'] = self._get_business_risks()
        ctx['recent_activity'] = self._get_recent_activity()
        ctx['slow_movers'] = self._get_slow_movers()
        ctx['reorder_suggestions'] = self._get_reorder_suggestions()
        return ctx

    def _get_company_overview(self) -> Dict[str, Any]:
        try:
            product_count = self.db.execute(
                text("SELECT COUNT(*) as count FROM products WHERE org_id = :org_id"),
                {"org_id": self.org_id},
            ).fetchone()
            location_count = self.db.execute(
                text("SELECT COUNT(*) as count FROM locations WHERE org_id = :org_id"),
                {"org_id": self.org_id},
            ).fetchone()
            return {
                "total_products": product_count.count if product_count else 0,
                "total_locations": location_count.count if location_count else 0,
                "org_id": self.org_id,
            }
        except Exception as e:  # pragma: no cover
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

    def _get_bottom_products(self) -> Dict[str, Any]:
        try:
            sql = text("""
                SELECT p.name as product_name, p.sku,
                       SUM( (oi.unit_price - COALESCE(p.cost,0)) * oi.quantity ) AS margin,
                       SUM( oi.quantity ) AS units
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                JOIN products p ON p.id = oi.product_id
                WHERE p.org_id = :org_id AND o.ordered_at >= (current_date - 30)
                GROUP BY p.name, p.sku
                HAVING SUM(oi.quantity) > 0
                ORDER BY margin ASC
                LIMIT 3
            """)
            rows = self.db.execute(sql, {"org_id": self.org_id}).fetchall()
            return {"bottom_by_margin": [
                {"name": r.product_name, "sku": r.sku, "margin": float(r.margin or 0), "units": int(r.units or 0)} for r in rows
            ]}
        except Exception as e:
            logger.error(f"Error getting bottom products: {e}")
            return {"bottom_by_margin": []}
    
    def _get_business_risks(self) -> Dict[str, Any]:
        try:
            stockout_sql = text(
                """
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
                """
            )
            result = self.db.execute(stockout_sql, {"org_id": self.org_id}).fetchone()
            return {
                "high_stockout_risk": result.high_risk_count if result else 0,
                "needs_immediate_attention": bool(result.high_risk_count > 5) if result else False,
            }
        except Exception as e:  # pragma: no cover
            logger.error(f"Error getting business risks: {e}")
            return {"high_stockout_risk": 0, "needs_immediate_attention": False}

    def _get_slow_movers(self) -> Dict[str, Any]:
        try:
            sql = text("""
                SELECT p.name as product_name, p.sku,
                       COALESCE(SUM(CASE WHEN im.movement_type IN ('in','adjust') THEN im.quantity WHEN im.movement_type='out' THEN -im.quantity ELSE 0 END),0) as on_hand,
                       COALESCE(SUM(CASE WHEN sd.sales_date >= (current_date - 30) THEN sd.units_sold ELSE 0 END),0) as units_sold_30d
                FROM products p
                LEFT JOIN inventory_movements im ON im.product_id = p.id
                LEFT JOIN analytics_marts.sales_daily sd ON sd.sku = p.sku AND sd.org_id = p.org_id
                WHERE p.org_id = :org_id
                GROUP BY p.id, p.name, p.sku
                HAVING COALESCE(SUM(CASE WHEN im.movement_type IN ('in','adjust') THEN im.quantity WHEN im.movement_type='out' THEN -im.quantity ELSE 0 END),0) > 0
                ORDER BY units_sold_30d ASC, on_hand DESC
                LIMIT 3
            """)
            rows = self.db.execute(sql, {"org_id": self.org_id}).fetchall()
            return {"slow": [
                {"name": r.product_name, "sku": r.sku, "on_hand": float(r.on_hand or 0), "units_sold_30d": int(r.units_sold_30d or 0)} for r in rows
            ]}
        except Exception as e:
            logger.error(f"Error getting slow movers: {e}")
            return {"slow": []}

    def _get_reorder_suggestions(self) -> Dict[str, Any]:
        try:
            sql = text("""
                SELECT p.name as product_name, p.sku,
                       COALESCE(SUM(CASE WHEN im.movement_type IN ('in','adjust') THEN im.quantity WHEN im.movement_type='out' THEN -im.quantity ELSE 0 END),0) as on_hand,
                       COALESCE(AVG(sd.units_30day_avg),0) as v30
                FROM products p
                LEFT JOIN inventory_movements im ON im.product_id = p.id
                LEFT JOIN analytics_marts.sales_daily sd ON sd.sku = p.sku AND sd.org_id = p.org_id
                WHERE p.org_id = :org_id
                GROUP BY p.id, p.name, p.sku
            """)
            rows = self.db.execute(sql, {"org_id": self.org_id}).fetchall()
            suggestions = []
            for r in rows:
                vel = float(r.v30 or 0)
                if vel <= 0: continue
                needed = vel * 30 - float(r.on_hand or 0)
                if needed > 0:
                    suggestions.append({"name": r.product_name, "sku": r.sku, "suggested_qty": int(round(needed))})
            suggestions.sort(key=lambda x: x['suggested_qty'], reverse=True)
            return {"reorder": suggestions[:3]}
        except Exception as e:
            logger.error(f"Error getting reorder suggestions: {e}")
            return {"reorder": []}
    
    def _get_recent_activity(self) -> Dict[str, Any]:
        """Get recent business activity."""
        try:
            movements_sql = text(
                """
                SELECT COUNT(*) as movements_today
                FROM inventory_movements im
                JOIN products p ON p.id = im.product_id
                WHERE p.org_id = :org_id AND DATE(im."timestamp") = current_date
                """
            )
            movements = self.db.execute(movements_sql, {"org_id": self.org_id}).fetchone()
            return {
                "inventory_movements_today": movements.movements_today if movements else 0,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return {
                "inventory_movements_today": 0,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }

    # -------- Formatting --------
    def _format_context_for_llm(self, ctx: Dict[str, Any]) -> str:
        company = ctx.get('company', {})
        inventory = ctx.get('inventory', {})
        sales = ctx.get('sales', {})
        top_products = ctx.get('top_products', {})
        bottom_products = ctx.get('bottom_products', {})
        risks = ctx.get('risks', {})
        activity = ctx.get('recent_activity', {})
        slow = ctx.get('slow_movers', {})
        reorder = ctx.get('reorder_suggestions', {})

        parts = [
            "STOCKPILOT BUSINESS CONTEXT:",
            f"• Organization: {company.get('org_id','?')}",
            f"• Product Catalog: {company.get('total_products',0)} products across {company.get('total_locations',0)} locations",
            "",
            "INVENTORY STATUS:",
            f"• Total SKUs: {inventory.get('total_skus',0)} | Total Units: {inventory.get('total_units',0)}",
            f"• Out of Stock: {inventory.get('out_of_stock',0)} | Low Stock (≤10): {inventory.get('low_stock',0)}",
            "",
            "PERFORMANCE (Last 7 Days):",
            f"• Revenue ${sales.get('revenue_7d',0):,.2f} | Units {sales.get('units_7d',0)} | Gross Margin ${sales.get('margin_7d',0):,.2f}",
        ]

        top_list = top_products.get('top_by_margin', [])
        if top_list:
            parts.append("TOP MARGIN SKUs (30d):")
            for t in top_list:
                parts.append(f"  - {t['name']} (SKU {t['sku']}): margin ${t['margin']:.2f}, units {t['units']}")

        bottom_list = bottom_products.get('bottom_by_margin', [])
        if bottom_list:
            parts.append("BOTTOM MARGIN SKUs (30d):")
            for b in bottom_list:
                parts.append(f"  - {b['name']} (SKU {b['sku']}): margin ${b['margin']:.2f}, units {b['units']}")

        slow_list = slow.get('slow', [])
        if slow_list:
            parts.append("SLOW MOVERS (have stock, low 30d sales):")
            for s in slow_list:
                parts.append(f"  - {s['name']} (SKU {s['sku']}): on_hand {s['on_hand']}, sold_30d {s['units_sold_30d']}")

        reorder_list = reorder.get('reorder', [])
        if reorder_list:
            parts.append("REORDER SUGGESTIONS (target 30d cover):")
            for r in reorder_list:
                parts.append(f"  - {r['name']} (SKU {r['sku']}): suggested_qty {r['suggested_qty']}")

        parts.append("")
        parts.append(
            f"HIGH STOCKOUT RISK SKUs (≤7d cover): {risks.get('high_stockout_risk',0)} | Immediate Attention: {risks.get('needs_immediate_attention', False)}"
        )
        parts.append(
            f"RECENT ACTIVITY: {activity.get('inventory_movements_today',0)} inventory movements today (as of {activity.get('last_updated','?')})"
        )
        parts.append("")
        parts.append(
            "Guidelines: Answer only with data present. If missing, say it's not in snapshot and suggest analytic intent (top_skus_by_margin, stockout_risk, week_in_review, reorder_suggestions, slow_movers, product_detail). Be concise and factual."
        )
        return "\n".join(parts)


def get_business_context(db: Session, org_id: str) -> str:
    return BusinessContext(db, org_id).get_comprehensive_context()
