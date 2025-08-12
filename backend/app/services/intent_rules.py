from __future__ import annotations
from typing import Dict, Any, Callable, List, Tuple, cast
import re
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.schemas.chat import (
    IntentResolution,
    TopSkusByMarginParams,
    StockoutRiskParams,
    WeekInReviewParams,
    ReorderSuggestionsParams,
    SlowMoversParams,
    ProductDetailParams,
)

HandlerFn = Callable[[Dict[str, Any], Session, str], Dict[str, Any]]

# ---------------- Intent Resolution (rule based) -----------------

INTENT_KEYWORDS = {
    'top_skus_by_margin': ['top', 'margin', 'sku', 'skus', 'profit'],
    'stockout_risk': ['stockout', 'run out', 'risk'],
    'week_in_review': ['week in review', 'last week', 'summary', 'review'],
    'reorder_suggestions': ['reorder', 'suggestion', 'po draft', 'purchase'],
    'slow_movers': ['slow', 'not selling', "can't move", 'cant move', 'stuck', 'dead stock', 'dead inventory'],
    'product_detail': ['detail', 'tell me about', 'units sold', 'sales for', 'inventory for', 'stock for']
}

# Mapping needed by chat endpoint to validate params
INTENT_PARAM_MODELS = {
    'top_skus_by_margin': TopSkusByMarginParams,
    'stockout_risk': StockoutRiskParams,
    'week_in_review': WeekInReviewParams,
    'reorder_suggestions': ReorderSuggestionsParams,
    'slow_movers': SlowMoversParams,
    'product_detail': ProductDetailParams,
}

PARAM_NORMALIZERS = [
    (re.compile(r'last week|past week', re.I), 'period', lambda _: '7d'),
    (re.compile(r'last month|past 30 days', re.I), 'period', lambda _: '30d'),
    (re.compile(r'(?P<n>top ?(\d{1,2}))', re.I), 'n', lambda m: int(re.findall(r'\d+', m.group('n'))[0])),
    (re.compile(r'(?P<hd>(7|14|30)) ?day', re.I), 'horizon_days', lambda m: int(m.group('hd'))),
]

def resolve_intent_rules(prompt: str) -> IntentResolution:
    p_lower = prompt.lower()
    scores: List[Tuple[str, int]] = []
    for intent, kws in INTENT_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in p_lower)
        if hits:
            scores.append((intent, hits))
    if not scores:
        return IntentResolution(intent=None, params={}, confidence=0.0, reasons=['no keyword match'])
    scores.sort(key=lambda x: x[1], reverse=True)
    best_intent, best_score = scores[0]
    params: Dict[str, Any] = {}
    for pattern, key, fn in PARAM_NORMALIZERS:
        m = pattern.search(prompt)
        if m:
            try:
                params[key] = fn(m)
            except Exception:
                pass
    # Cast best_intent (str) to IntentName type for pydantic model
    return IntentResolution(intent=cast(Any, best_intent), params=params, confidence=min(1.0, 0.4 + 0.2 * best_score), reasons=['keyword match'])

# ---------------- Handlers -----------------

def handler_top_skus_by_margin(params: Dict[str, Any], db: Session, org_id: str) -> Dict[str, Any]:
    p = TopSkusByMarginParams(**params)
    days = 7 if p.period == '7d' else 30
    limit = p.n
    mart_sql = text("""
        SELECT product_name, sku, sum(gross_margin) AS gross_margin, sum(gross_revenue) AS revenue, sum(units_sold) AS units
        FROM analytics_marts.sales_daily
        WHERE org_id = :org_id AND sales_date >= current_date - make_interval(days => :days)
        GROUP BY product_name, sku
        ORDER BY gross_margin DESC
        LIMIT :limit
    """)
    executed_sql = mart_sql
    fallback_used = False
    try:
        rows = db.execute(mart_sql, {"org_id": org_id, "days": days, "limit": limit}).fetchall()
    except Exception:
        # Fallback derive from order_items
        fallback_sql = text("""
            SELECT p.name AS product_name, p.sku,
                   SUM( (oi.unit_price - COALESCE(p.cost,0)) * oi.quantity ) AS gross_margin,
                   SUM( oi.unit_price * oi.quantity ) AS revenue,
                   SUM( oi.quantity ) AS units
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            JOIN products p ON p.id = oi.product_id
            WHERE p.org_id = :org_id AND o.ordered_at >= current_date - make_interval(days => :days)
            GROUP BY p.name, p.sku
            ORDER BY gross_margin DESC
            LIMIT :limit
        """)
        rows = db.execute(fallback_sql, {"org_id": org_id, "days": days, "limit": limit}).fetchall()
        executed_sql = fallback_sql
        fallback_used = True
    data_rows = [{
        "product_name": r.product_name,
        "sku": r.sku,
        "gross_margin": float(r.gross_margin or 0),
        "revenue": float(r.revenue or 0),
        "units": int(r.units or 0),
    } for r in rows]
    return {
        "columns": [
            {"name": "product_name", "type": "string"},
            {"name": "sku", "type": "string"},
            {"name": "gross_margin", "type": "number"},
            {"name": "revenue", "type": "number"},
            {"name": "units", "type": "number"},
        ],
        "rows": data_rows,
        "sql": executed_sql.text.replace('\n',' '),
        "definition": "Top SKUs ranked by total gross margin over the selected period." + (" (fallback approximation)" if fallback_used else ""),
    }

def handler_stockout_risk(params: Dict[str, Any], db: Session, org_id: str) -> Dict[str, Any]:
    p = StockoutRiskParams(**params)
    horizon = p.horizon_days
    # Reuse logic similar to analytics stockout risk but narrower
    sql = text("""
        SELECT p.id as product_id, p.name as product_name, p.sku,
               COALESCE(SUM(CASE WHEN im.movement_type IN ('in','adjust') THEN im.quantity WHEN im.movement_type='out' THEN -im.quantity ELSE 0 END),0) as on_hand,
               AVG(sd.units_7day_avg) as v7, AVG(sd.units_30day_avg) as v30
        FROM products p
        LEFT JOIN inventory_movements im ON im.product_id = p.id
        LEFT JOIN analytics_marts.sales_daily sd ON sd.sku = p.sku AND sd.org_id = p.org_id
        WHERE p.org_id = :org_id
        GROUP BY p.id, p.name, p.sku
    """)
    rows = db.execute(sql, {"org_id": org_id}).fetchall()
    result = []
    for r in rows:
        v = float(r.v7 or r.v30 or 0)
        days_to = (float(r.on_hand) / v) if v > 0 else None
        risk = 'none'
        if days_to is not None:
            if days_to <= 7: risk='high'
            elif days_to <= 14: risk='medium'
            elif days_to <= 30: risk='low'
        if days_to is not None and days_to <= horizon:
            result.append({
                "product_name": r.product_name,
                "sku": r.sku,
                "on_hand": float(r.on_hand),
                "days_to_stockout": round(days_to,1) if days_to is not None else None,
                "risk_level": risk
            })
    # sort by highest risk then soonest
    rank = {'high':0,'medium':1,'low':2,'none':3}
    result.sort(key=lambda x: (rank.get(x['risk_level'],4), x.get('days_to_stockout') or 9999))
    return {
        "columns": [
            {"name": "product_name", "type": "string"},
            {"name": "sku", "type": "string"},
            {"name": "on_hand", "type": "number"},
            {"name": "days_to_stockout", "type": "number"},
            {"name": "risk_level", "type": "string"},
        ],
        "rows": result,
        "sql": sql.text.replace('\n', ' '),
        "definition": "Products at risk of stocking out within the specified horizon based on recent velocity.",
    }

def handler_week_in_review(params: Dict[str, Any], db: Session, org_id: str) -> Dict[str, Any]:
    _ = WeekInReviewParams(**params)  # currently no extra params
    sql = text("""
        SELECT sales_date, sum(gross_revenue) as revenue, sum(units_sold) as units, sum(gross_margin) as margin
        FROM analytics_marts.sales_daily
        WHERE org_id=:org_id AND sales_date >= (current_date - 7)
        GROUP BY sales_date
        ORDER BY sales_date DESC
    """)
    rows = db.execute(sql, {"org_id": org_id}).fetchall()
    data_rows = [{
        "date": r.sales_date.isoformat(),
        "revenue": float(r.revenue or 0),
        "units": int(r.units or 0),
        "margin": float(r.margin or 0)
    } for r in rows]
    return {
        "columns": [
            {"name": "date", "type": "date"},
            {"name": "revenue", "type": "number"},
            {"name": "units", "type": "number"},
            {"name": "margin", "type": "number"},
        ],
        "rows": data_rows,
        "sql": sql.text.replace('\n',' '),
        "definition": "Daily revenue, units, and margin for the last 7 days.",
    }

def handler_reorder_suggestions(params: Dict[str, Any], db: Session, org_id: str) -> Dict[str, Any]:
    _ = ReorderSuggestionsParams(**params)
    # Simplified reorder suggestion using velocity vs on hand (placeholder)
    sql = text("""
        SELECT p.name as product_name, p.sku,
               COALESCE(SUM(CASE WHEN im.movement_type IN ('in','adjust') THEN im.quantity WHEN im.movement_type='out' THEN -im.quantity ELSE 0 END),0) as on_hand,
               AVG(sd.units_30day_avg) as v30
        FROM products p
        LEFT JOIN inventory_movements im ON im.product_id = p.id
        LEFT JOIN analytics_marts.sales_daily sd ON sd.sku = p.sku AND sd.org_id = p.org_id
        WHERE p.org_id = :org_id
        GROUP BY p.id, p.name, p.sku
    """)
    rows = db.execute(sql, {"org_id": org_id}).fetchall()
    suggestions = []
    for r in rows:
        vel = float(r.v30 or 0)
        if vel <= 0: continue
        target_cover_days = 30
        needed = vel * target_cover_days - float(r.on_hand)
        if needed > 0:
            suggestions.append({
                "product_name": r.product_name,
                "sku": r.sku,
                "on_hand": float(r.on_hand),
                "avg_30d_units": vel,
                "suggested_order_qty": int(round(needed))
            })
    suggestions.sort(key=lambda x: x['suggested_order_qty'], reverse=True)
    return {
        "columns": [
            {"name": "product_name", "type": "string"},
            {"name": "sku", "type": "string"},
            {"name": "on_hand", "type": "number"},
            {"name": "avg_30d_units", "type": "number"},
            {"name": "suggested_order_qty", "type": "number"},
        ],
        "rows": suggestions,
        "sql": sql.text.replace('\n',' '),
        "definition": "Suggested replenishment quantities to cover 30 days based on 30-day average velocity.",
    }

def handler_slow_movers(params: Dict[str, Any], db: Session, org_id: str) -> Dict[str, Any]:
    p = SlowMoversParams(**params)
    days = 30 if p.period == '30d' else 7
    # Use sales_daily if available for velocity; fallback to movement aggregation
    sql = text("""
        WITH per_product AS (
            SELECT p.id, p.name as product_name, p.sku,
                   COALESCE(SUM(CASE WHEN im.movement_type IN ('in','adjust') THEN im.quantity 
                        WHEN im.movement_type='out' THEN -im.quantity ELSE 0 END),0) as on_hand,
                   COALESCE(SUM(CASE WHEN sd.sales_date >= current_date - make_interval(days => :days) THEN sd.units_sold ELSE 0 END),0) as units_sold_period
            FROM products p
            LEFT JOIN inventory_movements im ON im.product_id = p.id
            LEFT JOIN analytics_marts.sales_daily sd ON sd.sku = p.sku AND sd.org_id = p.org_id
            WHERE p.org_id = :org_id
            GROUP BY p.id, p.name, p.sku
        )
        SELECT product_name, sku, on_hand, units_sold_period
        FROM per_product
        WHERE on_hand > 0
        ORDER BY units_sold_period ASC, on_hand DESC
        LIMIT :limit
    """)
    rows = db.execute(sql, {"org_id": org_id, "days": days, "limit": p.n}).fetchall()
    data_rows = [
        {"product_name": r.product_name, "sku": r.sku, "on_hand": float(r.on_hand), "units_sold_period": int(r.units_sold_period)}
        for r in rows
    ]
    return {
        "columns": [
            {"name": "product_name", "type": "string"},
            {"name": "sku", "type": "string"},
            {"name": "on_hand", "type": "number"},
            {"name": "units_sold_period", "type": "number"},
        ],
        "rows": data_rows,
        "sql": sql.text.replace('\n',' '),
        "definition": f"Products with on-hand inventory but low sales in last {days} days (potential dead stock).",
    }

def handler_product_detail(params: Dict[str, Any], db: Session, org_id: str) -> Dict[str, Any]:
    p = ProductDetailParams(**params)
    # Accept lookup by sku or name (prefer sku)
    where = []
    binds: Dict[str, Any] = {"org_id": org_id}
    if p.sku:
        where.append("p.sku = :sku")
        binds['sku'] = p.sku
    if p.name:
        where.append("lower(p.name) = lower(:pname)")
        binds['pname'] = p.name
    if not where:
        return {"columns": [], "rows": [], "sql": None, "definition": "Provide sku or name for product detail."}
    filt = ' AND '.join(where)
    sql = text(f"""
        WITH sales AS (
            SELECT sku,
                   SUM(CASE WHEN sales_date >= (current_date - 7) THEN units_sold ELSE 0 END) AS units_7d,
                   SUM(CASE WHEN sales_date >= (current_date - 30) THEN units_sold ELSE 0 END) AS units_30d,
                   SUM(CASE WHEN sales_date >= (current_date - 30) THEN gross_margin ELSE 0 END) AS margin_30d,
                   SUM(CASE WHEN sales_date >= (current_date - 30) THEN gross_revenue ELSE 0 END) AS revenue_30d
            FROM analytics_marts.sales_daily
            WHERE org_id = :org_id
            GROUP BY sku
        ), inv AS (
            SELECT p.id, p.name, p.sku,
                   COALESCE(SUM(CASE WHEN im.movement_type IN ('in','adjust') THEN im.quantity WHEN im.movement_type='out' THEN -im.quantity ELSE 0 END),0) AS on_hand
            FROM products p
            LEFT JOIN inventory_movements im ON im.product_id = p.id
            WHERE p.org_id = :org_id
            GROUP BY p.id, p.name, p.sku
        )
        SELECT inv.name as product_name, inv.sku, inv.on_hand,
               COALESCE(s.units_7d,0) as units_sold_7d,
               COALESCE(s.units_30d,0) as units_sold_30d,
               COALESCE(s.margin_30d,0) as margin_30d,
               COALESCE(s.revenue_30d,0) as revenue_30d
        FROM inv
        LEFT JOIN sales s ON s.sku = inv.sku
        WHERE {filt}
        LIMIT 1
    """)
    row = db.execute(sql, binds).fetchone()
    if not row:
        return {"columns": [], "rows": [], "sql": sql.text.replace('\n',' '), "definition": "Product not found for given filters."}
    data_row = {
        "product_name": row.product_name,
        "sku": row.sku,
        "on_hand": float(row.on_hand or 0),
        "units_sold_7d": int(row.units_sold_7d or 0),
        "units_sold_30d": int(row.units_sold_30d or 0),
        "margin_30d": float(row.margin_30d or 0),
        "revenue_30d": float(row.revenue_30d or 0),
    }
    return {
        "columns": [
            {"name": "product_name", "type": "string"},
            {"name": "sku", "type": "string"},
            {"name": "on_hand", "type": "number"},
            {"name": "units_sold_7d", "type": "number"},
            {"name": "units_sold_30d", "type": "number"},
            {"name": "margin_30d", "type": "number"},
            {"name": "revenue_30d", "type": "number"},
        ],
        "rows": [data_row],
        "sql": sql.text.replace('\n',' '),
        "definition": "Detailed product snapshot: current on-hand, recent sales & economics.",
    }

INTENT_HANDLERS: Dict[str, HandlerFn] = {
    'top_skus_by_margin': handler_top_skus_by_margin,
    'stockout_risk': handler_stockout_risk,
    'week_in_review': handler_week_in_review,
    'reorder_suggestions': handler_reorder_suggestions,
    'slow_movers': handler_slow_movers,
    'product_detail': handler_product_detail,
}

INTENT_HANDLERS: Dict[str, HandlerFn] = {
    'top_skus_by_margin': handler_top_skus_by_margin,
    'stockout_risk': handler_stockout_risk,
    'week_in_review': handler_week_in_review,
    'reorder_suggestions': handler_reorder_suggestions,
    'slow_movers': handler_slow_movers,
    'product_detail': handler_product_detail,
}

