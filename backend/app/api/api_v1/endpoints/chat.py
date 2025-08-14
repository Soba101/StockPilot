from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
from app.core.database import get_db, get_current_claims
from app.core.config import settings
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse, ConfidenceMeta, FreshnessMeta, QueryExplainer
from app.schemas.chat import IntentName, IntentResolution
from app.services.intent_resolver import resolve_intent
from app.services.intent_rules import INTENT_HANDLERS, INTENT_PARAM_MODELS
from app.services.llm_client import llm_intent_resolver
from app.services.business_context import get_business_context
import re

router = APIRouter()

async def _compute_freshness(db: Session, org_id: str):
    # inventory_movements has no org_id and the column is named timestamp, not ts
    inv_ts = db.execute(text(
        """
        SELECT max(im.timestamp) as m
        FROM inventory_movements im
        JOIN products p ON p.id = im.product_id
        WHERE p.org_id = :org
        """
    ), {"org": org_id}).fetchone()
    order_ts = db.execute(text("SELECT max(ordered_at) as m FROM orders WHERE org_id=:org"), {"org": org_id}).fetchone()
    candidates = [r.m for r in [inv_ts, order_ts] if r and r.m]
    if candidates:
        latest = max(candidates)
        # Normalize: make both sides timezone-aware UTC
        now_utc = datetime.now(timezone.utc)
        if getattr(latest, 'tzinfo', None) is None:
            latest_aware = latest.replace(tzinfo=timezone.utc)
        else:
            latest_aware = latest.astimezone(timezone.utc)
        lag = (now_utc - latest_aware).total_seconds()
        return latest_aware.isoformat().replace('+00:00','Z'), int(lag)
    return None, None

@router.post("/query", response_model=ChatQueryResponse)
async def chat_query(req: ChatQueryRequest, db: Session = Depends(get_db), claims = Depends(get_current_claims)):
    if not settings.CHAT_ENABLED:
        raise HTTPException(status_code=403, detail="Chat disabled")
    org_id = claims.get("org")

    # Resolve intent
    resolution: IntentResolution
    if req.intent:
        resolution = IntentResolution(intent=req.intent, params=req.params, confidence=1.0, source='rules', reasons=['explicit'])
    else:
        resolution = await resolve_intent(req.prompt)
    
    # If no specific intent is resolved and LLM is enabled, use general chat
    if not resolution.intent and settings.CHAT_LLM_FALLBACK_ENABLED:
        try:
            # Get comprehensive business context
            business_context = get_business_context(db, org_id)
            answer = await llm_intent_resolver.general_chat(req.prompt, business_context)
            answer = _sanitize_answer(answer)
            now_iso = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
            
            return ChatQueryResponse(
                intent=None,
                title="StockPilot Assistant",
                answer_summary=answer,
                data={"columns": [], "rows": []},
                query_explainer=QueryExplainer(definition="Business-aware conversation", sql=None, sources=[]),
                freshness=FreshnessMeta(generated_at=now_iso, data_fresh_at=None, max_lag_seconds=None),
                confidence=ConfidenceMeta(level='high', reasons=['business_context_aware']),
                source='llm',
                warnings=[]
            )
        except Exception as e:
            # Graceful degradation (avoid 500 for frontend): return structured fallback
            now_iso = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
            return ChatQueryResponse(
                intent=None,
                title="StockPilot Assistant",
                answer_summary="LLM temporarily unavailable. You can still run analytic intents (e.g. 'top margin skus last week').",
                data={"columns": [], "rows": []},
                query_explainer=QueryExplainer(definition="Business-aware conversation fallback", sql=None, sources=[]),
                freshness=FreshnessMeta(generated_at=now_iso, data_fresh_at=None, max_lag_seconds=None),
                confidence=ConfidenceMeta(level='low', reasons=[f"llm_error:{e}"]),
                source='llm',
                warnings=["llm_unavailable"]
            )
    
    if not resolution.intent:
        raise HTTPException(status_code=400, detail={"error":"intent_unresolved","reasons":resolution.reasons})

    # Validate params
    param_model = INTENT_PARAM_MODELS[resolution.intent]
    try:
        validated_params = param_model(**{**resolution.params, **req.params}).model_dump(by_alias=True)
    except Exception as e:
        raise HTTPException(status_code=422, detail={"error":"param_validation_failed","message":str(e)})

    # Execute handler
    handler = INTENT_HANDLERS[resolution.intent]
    data_payload = handler(validated_params, db, org_id)

    latest_ts, lag = await _compute_freshness(db, org_id)
    now_iso = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

    # Confidence heuristic mapping
    level = 'high' if resolution.confidence >= 0.75 else 'medium' if resolution.confidence >= 0.55 else 'low'

    explainer = QueryExplainer(definition=data_payload.get('definition',''), sql=data_payload.get('sql'), sources=[])
    freshness = FreshnessMeta(generated_at=now_iso, data_fresh_at=latest_ts, max_lag_seconds=lag)
    confidence = ConfidenceMeta(level=level, reasons=resolution.reasons)

    title_map = {
        'top_skus_by_margin': 'Top SKUs by Margin',
        'stockout_risk': 'Stockout Risk Analysis',
        'week_in_review': 'Week in Review',
        'reorder_suggestions': 'Reorder Suggestions',
        'slow_movers': 'Slow Moving Inventory',
        'product_detail': 'Product Detail',
        'quarterly_forecast': 'Quarterly Forecast',
        'annual_breakdown': 'Annual Business Performance'
    }
    
    # Enhanced summary with business context awareness
    summary = _summarize_with_context(resolution.intent, data_payload, db, org_id)

    return ChatQueryResponse(
        intent=resolution.intent, title=title_map[resolution.intent], answer_summary=summary,
        data={"columns": data_payload['columns'], "rows": data_payload['rows']},
        query_explainer=explainer, freshness=freshness, confidence=confidence, source=resolution.source,
        warnings=[]
    )


def _sanitize_answer(text: str) -> str:
    """Convert markdown-ish output to plain text for UI without markdown rendering.

    Rules:
    - Strip **bold** markers
    - Convert simple markdown tables to 'Header: value' lines
    - Collapse multiple blank lines
    - Trim whitespace
    """
    if not text:
        return text
    # Strip bold markers
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    # Detect tables (lines starting with |)
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('|') and '|' in line[1:]:
            # collect contiguous table lines
            table_block = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_block.append(lines[i]); i += 1
            # parse table
            if len(table_block) >= 2:
                # first line headers, second maybe separator
                header_line = table_block[0]
                # skip separator line(s)
                data_rows = [r for r in table_block[1:] if not set(r.replace('|','').strip()) <= {'-',' '}]
                headers = [h.strip() for h in header_line.strip('|').split('|')]
                for dr in data_rows:
                    cells = [c.strip() for c in dr.strip('|').split('|')]
                    if len(cells) == len(headers):
                        for h, c in zip(headers, cells):
                            if h.lower() != 'metric' or (h.lower() == 'metric' and c):
                                out.append(f"{h.strip()}: {c}")
                    else:
                        out.append(dr)
                continue
        else:
            out.append(line)
            i += 1
    # Collapse blank lines
    cleaned = []
    prev_blank = False
    for l in out:
        blank = not l.strip()
        if blank and prev_blank:
            continue
        cleaned.append(l)
        prev_blank = blank
    return '\n'.join(cleaned).strip()


def _summarize_with_context(intent: IntentName, payload: dict, db: Session, org_id: str) -> str:
    """Enhanced summarize with business context awareness."""
    rows = payload.get('rows', [])
    if not rows:
        return 'No data found for your query. This might indicate you need to add inventory data or the specified filters returned no results.'
    
    # Base summary
    base_summary = _summarize(intent, payload)
    
    # Add contextual insights
    if intent == 'top_skus_by_margin':
        total_margin = sum(r.get('gross_margin', 0) for r in rows)
        return f"{base_summary} Total margin from top performers: ${total_margin:,.2f}. These products are driving your profitability."
    
    elif intent == 'stockout_risk':
        high_risk = [r for r in rows if r.get('risk_level') == 'high']
        if high_risk:
            return f"{base_summary} Immediate action needed on {len(high_risk)} high-risk items to prevent lost sales."
        else:
            return f"{base_summary} Your inventory levels look healthy with good stock coverage."
    
    elif intent == 'week_in_review':
        if len(rows) >= 2:
            # Compare recent days
            latest_rev = rows[0].get('revenue', 0)
            prev_rev = rows[1].get('revenue', 0)
            trend = "up" if latest_rev > prev_rev else "down" if latest_rev < prev_rev else "stable"
            return f"{base_summary} Daily revenue trend is {trend} compared to previous day."
        return base_summary
    
    elif intent == 'reorder_suggestions':
        urgent_count = len([r for r in rows if r.get('suggested_order_qty', 0) > 50])
        if urgent_count > 0:
            return f"{base_summary} {urgent_count} items need large reorder quantities (>50 units) - consider bulk purchasing."
        return f"{base_summary} Regular restocking levels suggested."
    elif intent == 'product_detail':
        r = rows[0]
        return (f"Product {r.get('product_name')} (SKU {r.get('sku')}) has on-hand {r.get('on_hand')} units. "
                f"Sold {r.get('units_sold_7d')} units in last 7d and {r.get('units_sold_30d')} in last 30d. "
                f"30d revenue ${r.get('revenue_30d'):.2f} margin ${r.get('margin_30d'):.2f}.")
    
    return base_summary


def _summarize(intent: IntentName, payload: dict) -> str:
    rows = payload.get('rows', [])
    if not rows:
        return 'No data found for selection.'
    if intent == 'top_skus_by_margin':
        top = rows[0]
        return f"Top SKU {top['sku']} with margin ${top['gross_margin']:.2f}."
    if intent == 'stockout_risk':
        high = [r for r in rows if r.get('risk_level') == 'high']
        return f"{len(high)} high-risk SKUs; {len(rows)} at-risk within horizon." if rows else 'No stockout risks.'
    if intent == 'week_in_review':
        total_rev = sum(r['revenue'] for r in rows)
        return f"Week revenue ${total_rev:.2f} across {len(rows)} days." 
    if intent == 'reorder_suggestions':
        return f"{len(rows)} SKUs need reorder; top suggestion qty {rows[0]['suggested_order_qty']}" if rows else 'No reorder needs.'
    if intent == 'slow_movers':
        zero_sold = [r for r in rows if r.get('units_sold_period', 0) == 0]
        return f"{len(rows)} slow movers (including {len(zero_sold)} with zero sales). Top stuck SKU {rows[0]['sku']} with {rows[0]['on_hand']} on hand." if rows else 'No slow movers found.'
    if intent == 'annual_breakdown':
        total_revenue = sum(r.get('revenue', 0) for r in rows)
        total_units = sum(r.get('units', 0) for r in rows)
        year = rows[0]['year'] if rows else 'Current'
        return f"{year} Business Performance: ${total_revenue:,.2f} total revenue from {total_units:,} units sold. Strong performance across {len(rows)} active {'quarters' if len(rows) > 1 else 'quarter'}."
    return f"Data with {len(rows)} results."
    return 'Summary unavailable.'
