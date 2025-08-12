from __future__ import annotations
from typing import Dict, Any, Callable, List, Tuple
import re
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.schemas.chat import (
    IntentResolution,
    TopSkusByMarginParams,
    StockoutRiskParams,
    WeekInReviewParams,
    ReorderSuggestionsParams,
    SlowMoversParams,
    IntentName,
)
from typing import cast

HandlerFn = Callable[[Dict[str, Any], Session, str], Dict[str, Any]]  # params, db, org_id -> structured data dict

INTENT_KEYWORDS = {
    'top_skus_by_margin': ['top', 'margin', 'sku', 'skus', 'profit'],
    'stockout_risk': ['stockout', 'run out', 'risk'],
    'week_in_review': ['week in review', 'last week', 'summary', 'review'],
    'reorder_suggestions': ['reorder', 'suggestion', 'po draft', 'purchase'],
    'slow_movers': ['slow', 'not selling', "can't move", 'cant move', 'stuck', 'dead stock', 'dead inventory']
}

PARAM_NORMALIZERS = [
    # (pattern, key, value_fn)
    (re.compile(r'last week|past week', re.I), 'period', lambda _: '7d'),
    (re.compile(r'last month|past 30 days', re.I), 'period', lambda _: '30d'),
    (re.compile(r'(?P<n>top ?(\d{1,2}))', re.I), 'n', lambda m: int(re.findall(r'\d+', m.group('n'))[0])),
    (re.compile(r'(?P<hd>(7|14|30)) ?day', re.I), 'horizon_days', lambda m: int(m.group('hd'))),
]

INTENT_PARAM_MODELS = {
    'top_skus_by_margin': TopSkusByMarginParams,
    'stockout_risk': StockoutRiskParams,
    'week_in_review': WeekInReviewParams,
    'reorder_suggestions': ReorderSuggestionsParams,
    'slow_movers': SlowMoversParams,
}


def resolve_intent_rules(prompt: str) -> IntentResolution:
    p_lower = prompt.lower()
    scores: List[Tuple[str, int]] = []
    for intent, keywords in INTENT_KEYWORDS.items():
        hit = sum(1 for kw in keywords if kw in p_lower)
        if hit:
            scores.append((intent, hit))
    if not scores:
        return IntentResolution(intent=None, params={}, confidence=0.0, reasons=['no keyword match'])
    # pick highest score; tie-break by length of first keyword occurrence index
    scores.sort(key=lambda x: x[1], reverse=True)
    best_intent, best_score = scores[0]

    params: Dict[str, Any] = {}
    for pattern, key, val_fn in PARAM_NORMALIZERS:
        m = pattern.search(prompt)
        if m:
            try:
                params[key] = val_fn(m)
            except Exception:
                pass

    # heuristic confidence
    max_keywords = len(INTENT_KEYWORDS[best_intent])
    confidence = 0.3 + 0.7 * (best_score / max_keywords)

    return IntentResolution(intent=cast(IntentName, best_intent), params=params, confidence=confidence, reasons=[f"score={best_score}"])

# ========== Handlers ==============

def handler_top_skus_by_margin(params: Dict[str, Any], db: Session, org_id: str) -> Dict[str, Any]:
    p = TopSkusByMarginParams(**params)
    # Use sales_daily mart
    sql = text("""
        SELECT product_name, sku, sum(gross_margin) as gross_margin, sum(gross_revenue) as revenue, sum(units_sold) as units
        FROM analytics_marts.sales_daily
        WHERE org_id=:org_id AND sales_date >= (current_date - (:days::int))
        GROUP BY product_name, sku
        ORDER BY gross_margin DESC
        LIMIT :limit
    """)
    days = 7 if p.period == '7d' else 30
    rows = db.execute(sql, {"org_id": org_id, "days": days, "limit": p.n}).fetchall()
    data_rows = [
        {
            "product_name": r.product_name,
            "sku": r.sku,
            "gross_margin": float(r.gross_margin or 0),
            "revenue": float(r.revenue or 0),
            "units": int(r.units or 0)
        } for r in rows
    ]
    return {
        "columns": [
            {"name": "product_name", "type": "string"},
            {"name": "sku", "type": "string"},
            {"name": "gross_margin", "type": "number"},
            {"name": "revenue", "type": "number"},
            {"name": "units", "type": "number"},
        ],
        "rows": data_rows,
        "sql": sql.text.replace('\n', ' '),
        "definition": "Top SKUs ranked by total gross margin over the selected period.",
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
                   COALESCE(SUM(CASE WHEN sd.sales_date >= (current_date - :days::int) THEN sd.units_sold ELSE 0 END),0) as units_sold_period
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

INTENT_HANDLERS: Dict[str, HandlerFn] = {
    'top_skus_by_margin': handler_top_skus_by_margin,
    'stockout_risk': handler_stockout_risk,
    'week_in_review': handler_week_in_review,
    'reorder_suggestions': handler_reorder_suggestions,
    'slow_movers': handler_slow_movers,
}

