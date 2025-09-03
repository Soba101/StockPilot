from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core import router as hybrid_router
from app.core import composer
from app.core.llm_lmstudio import lmstudio_client
import logging
from app.core.contracts import validate_output
from app.core.database import get_db, get_current_claims
from sqlalchemy.orm import Session
from app.tools.rag.retriever import get_rag_retriever
import asyncio
from sqlalchemy import text
from datetime import datetime, timedelta, date

router = APIRouter()

class UnifiedChatRequest(BaseModel):
    message: str
    options: Dict[str, Any] = {}

@router.post("/query")
async def unified_chat(req: UnifiedChatRequest, db: Session = Depends(get_db), claims = Depends(get_current_claims)):
    if not settings.HYBRID_CHAT_ENABLED:
        raise HTTPException(status_code=403, detail="Hybrid chat disabled")

    org_id = claims.get("org")
    # Route the message
    decision = await hybrid_router.route(req.message)

    # Only support RAG and OPEN routes (BI removed)
    if decision.route == "RAG":
        try:
            retriever = get_rag_retriever()
            # Enforce org scoping on RAG lookups
            rag_snippets = await retriever.search(req.message, top_k=6, filters={"org_id": org_id})
            if not rag_snippets:
                return composer.compose_no_answer(
                    "No relevant documents found. Please add documents to the knowledge base or try a different question.",
                    ["Ask a simpler question", "Contact support for document ingestion"]
                )
            answer = await retriever.generate_answer(req.message, rag_snippets)
            return composer.compose_rag(rag_snippets, answer, decision.confidence)
        except Exception as e:
            logging.warning(f"RAG system error: {e}")
            return composer.compose_no_answer(
                "Document search system temporarily unavailable",
                ["Try again later"]
            )
    if decision.route == "BI":
        # Minimal BI: total revenue, total orders, total units, AOV for a simple period
        try:
            # Parse a very small set of time hints
            msg = (req.message or "").lower()
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            tables = ["analytics_marts.sales_daily"]
            # year detection like 2025
            import re
            # Optional filters parsed from message
            sku_filter: Optional[str] = None
            category_filter: Optional[str] = None
            msku = re.search(r"\bsku\s+([A-Za-z0-9._-]+)\b", msg)
            if msku:
                sku_filter = msku.group(1)
            mcat = re.search(r"\b(?:in|by|for)\s+category\s+([A-Za-z0-9 &_/-]{2,})\b", msg)
            if mcat:
                category_filter = mcat.group(1).strip()
            m = re.search(r"\b(20\d{2})\b", msg)
            if m:
                year = int(m.group(1))
                start_date = datetime(year, 1, 1).date()
                end_date = datetime(year, 12, 31).date()
            elif "today" in msg:
                start_date = end_date
            elif "yesterday" in msg:
                start_date = end_date - timedelta(days=1)
                end_date = start_date
            elif "this week" in msg:
                # ISO week: Monday=0
                start_date = end_date - timedelta(days=end_date.weekday())
            elif "last week" in msg:
                # previous week Monday..Sunday
                this_mon = end_date - timedelta(days=end_date.weekday())
                start_date = this_mon - timedelta(days=7)
                end_date = start_date + timedelta(days=6)
            elif "last 7" in msg:
                start_date = end_date - timedelta(days=7)
            elif "last 30" in msg or "30 days" in msg:
                start_date = end_date - timedelta(days=30)
            elif "last month" in msg:
                first_of_this_month = end_date.replace(day=1)
                last_month_end = first_of_this_month - timedelta(days=1)
                start_date = last_month_end.replace(day=1)
                end_date = last_month_end
            elif "this month" in msg or "mtd" in msg:
                start_date = end_date.replace(day=1)
            elif "this quarter" in msg or "qtd" in msg:
                # calendar quarters; adjust if fiscal later
                q = (end_date.month - 1) // 3 + 1
                if q == 1:
                    start_date = end_date.replace(month=1, day=1)
                elif q == 2:
                    start_date = end_date.replace(month=4, day=1)
                elif q == 3:
                    start_date = end_date.replace(month=7, day=1)
                else:
                    start_date = end_date.replace(month=10, day=1)
            elif "this year" in msg or "ytd" in msg or "year to date" in msg:
                start_date = end_date.replace(month=1, day=1)

            # Specific date detection (YYYY-MM-DD) e.g. "on 2025-08-12" → set exact day window
            mdate = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])\b", msg)
            if mdate:
                y, mo, d = int(mdate.group(1)), int(mdate.group(2)), int(mdate.group(3))
                try:
                    specific = datetime(y, mo, d).date()
                    start_date = specific
                    end_date = specific
                except Exception:
                    pass

            # Special intents within BI
            # synonyms for intents
            wants_top_products = (
                ("top" in msg or "best" in msg or "winner" in msg or "top seller" in msg or "best seller" in msg or "top sellers" in msg or "best sellers" in msg)
                and ("product" in msg or "sku" in msg or "item" in msg)
            )
            wants_daily = (
                "by day" in msg or "per day" in msg or "daily" in msg or "each day" in msg or "day by day" in msg or "day-by-day" in msg or "daily breakdown" in msg
            )
            # Quarter detection and comparison intent
            q_matches = re.findall(r"\bq([1-4])\b", msg)
            wants_quarter = bool(q_matches)
            wants_vs = (" vs " in msg or "versus" in msg or "compare" in msg)
            wants_profit = ("profit" in msg or "margin" in msg or "gross profit" in msg or "margin%" in msg or "gross margin" in msg)
            wants_category_breakdown = ("by category" in msg or "category breakdown" in msg or "sales by category" in msg)
            wants_inventory = (("on hand" in msg or "inventory" in msg or "stock on hand" in msg) and (sku_filter is not None))

            # Generic 2-period comparison parsing (years, months, weeks, specific dates, rolling windows)
            MONTHS = {
                "jan": 1, "january": 1,
                "feb": 2, "february": 2,
                "mar": 3, "march": 3,
                "apr": 4, "april": 4,
                "may": 5,
                "jun": 6, "june": 6,
                "jul": 7, "july": 7,
                "aug": 8, "august": 8,
                "sep": 9, "sept": 9, "september": 9,
                "oct": 10, "october": 10,
                "nov": 11, "november": 11,
                "dec": 12, "december": 12,
            }

            def month_range(y: int, m: int) -> tuple[date, date]:
                from calendar import monthrange
                last_day = monthrange(y, m)[1]
                return datetime(y, m, 1).date(), datetime(y, m, last_day).date()

            def week_range_for(d: date) -> tuple[date, date]:
                # ISO week Monday..Sunday
                start = d - timedelta(days=d.weekday())
                return start, start + timedelta(days=6)

            def summary_for_range(s: date, e: date):
                nonlocal tables
                base_sql = (
                    "SELECT COALESCE(sum(gross_revenue),0) as total_revenue, "
                    "COALESCE(sum(orders_count),0) as total_orders, COALESCE(sum(units_sold),0) as total_units "
                    "FROM analytics_marts.sales_daily WHERE org_id = :org_id "
                    "AND sales_date BETWEEN :start_date AND :end_date"
                )
                params = {"org_id": org_id, "start_date": s, "end_date": e}
                if sku_filter:
                    base_sql += " AND sku = :sku"
                    params["sku"] = sku_filter
                if category_filter:
                    base_sql += " AND (LOWER(COALESCE(category,'uncategorized')) LIKE :cat_like)"
                    params["cat_like"] = f"%{category_filter.lower()}%"
                r = db.execute(text(base_sql), params).fetchone()
                tr = float(r.total_revenue) if r and r.total_revenue is not None else 0.0
                to = int(r.total_orders) if r and r.total_orders is not None else 0
                tu = int(r.total_units) if r and r.total_units is not None else 0
                if (not r) or (tr == 0 and to == 0 and tu == 0):
                    tables = ["orders", "order_items", "products"]
                    fb_sql = (
                        "SELECT COALESCE(SUM(oi.unit_price * oi.quantity - oi.discount),0) as total_revenue, "
                        "COUNT(DISTINCT o.id) as total_orders, COALESCE(SUM(oi.quantity),0) as total_units "
                        "FROM orders o JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id "
                        "WHERE o.org_id = :org_id AND o.status IN ('fulfilled','completed','shipped') "
                        "AND o.ordered_at::date BETWEEN :start_date AND :end_date"
                    )
                    fb_params = {"org_id": org_id, "start_date": s, "end_date": e}
                    if sku_filter:
                        fb_sql += " AND p.sku = :sku"
                        fb_params["sku"] = sku_filter
                    if category_filter:
                        fb_sql += " AND (LOWER(COALESCE(p.category,'uncategorized')) LIKE :cat_like)"
                        fb_params["cat_like"] = f"%{category_filter.lower()}%"
                    fr = db.execute(text(fb_sql), fb_params).fetchone()
                    tr = float(fr.total_revenue) if fr and fr.total_revenue is not None else 0.0
                    to = int(fr.total_orders) if fr and fr.total_orders is not None else 0
                    tu = int(fr.total_units) if fr and fr.total_units is not None else 0
                aov = (tr / to) if to > 0 else 0.0
                return tr, to, tu, aov

            def try_parse_two_periods() -> Optional[tuple[str, date, date, str, date, date]]:
                # 1) two explicit years
                years = re.findall(r"\b(20\d{2})\b", msg)
                if len(years) >= 2:
                    y1, y2 = int(years[0]), int(years[1])
                    s1, e1 = datetime(y1, 1, 1).date(), datetime(y1, 12, 31).date()
                    s2, e2 = datetime(y2, 1, 1).date(), datetime(y2, 12, 31).date()
                    return (str(y1), s1, e1, str(y2), s2, e2)

                # 2) this year vs last year
                if ("this year" in msg or "ytd" in msg or "year to date" in msg) and ("last year" in msg or "prior year" in msg or "previous year" in msg):
                    y = end_date.year
                    s1, e1 = end_date.replace(month=1, day=1), end_date
                    s2, e2 = datetime(y-1, 1, 1).date(), datetime(y-1, 12, 31).date()
                    return (f"YTD {y}", s1, e1, f"Year {y-1}", s2, e2)

                # 3) two explicit dates (YYYY-MM-DD)
                d_matches = re.findall(r"\b(20\d{2})-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])\b", msg)
                if len(d_matches) >= 2:
                    y1, m1, d1 = map(int, d_matches[0])
                    y2, m2, d2 = map(int, d_matches[1])
                    s1 = e1 = datetime(y1, m1, d1).date()
                    s2 = e2 = datetime(y2, m2, d2).date()
                    return (f"{s1}", s1, e1, f"{s2}", s2, e2)

                # 4) this month vs last month
                if ("this month" in msg or "mtd" in msg) and ("last month" in msg or "previous month" in msg or "prior month" in msg):
                    first_of_this = end_date.replace(day=1)
                    last_month_end = first_of_this - timedelta(days=1)
                    s1, e1 = first_of_this, end_date  # MTD
                    s2, e2 = last_month_end.replace(day=1), last_month_end
                    return (f"MTD {end_date.strftime('%b %Y')}", s1, e1, f"{last_month_end.strftime('%b %Y')}", s2, e2)

                # 5) two months (optionally with years)
                # capture month tokens possibly followed by a year
                m_tokens = list(re.finditer(r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b(?:\s+(20\d{2}))?", msg))
                if len(m_tokens) >= 2:
                    m1 = m_tokens[0].group(1); y1 = int(m_tokens[0].group(2)) if m_tokens[0].group(2) else end_date.year
                    m2 = m_tokens[1].group(1); y2 = int(m_tokens[1].group(2)) if m_tokens[1].group(2) else end_date.year
                    s1, e1 = month_range(y1, MONTHS[m1])
                    s2, e2 = month_range(y2, MONTHS[m2])
                    return (f"{m1.title()} {y1}", s1, e1, f"{m2.title()} {y2}", s2, e2)

                # 6) this week vs last week
                if ("this week" in msg) and ("last week" in msg or "previous week" in msg or "prior week" in msg):
                    s1, e1 = week_range_for(end_date)
                    this_mon = s1
                    s2, e2 = this_mon - timedelta(days=7), this_mon - timedelta(days=1)
                    return ("This week", s1, e1, "Last week", s2, e2)

                # 7) last N days vs previous/prior N days
                mwin = re.search(r"last\s+(\d{1,3})\s+days\s+(?:vs|versus|compared\s+to)\s+(?:previous|prior)\s+\1\s+days", msg)
                if mwin:
                    n = int(mwin.group(1))
                    s1, e1 = end_date - timedelta(days=n-1), end_date
                    s2, e2 = s1 - timedelta(days=n), s1 - timedelta(days=1)
                    return (f"Last {n} days", s1, e1, f"Prior {n} days", s2, e2)

                # 8) MTD vs prior MTD
                if re.search(r"\b(mtd|month[-\s]?to[-\s]?date)\b", msg) and re.search(r"\b(prior|previous|last)\s+(mtd|month)\b", msg):
                    first_this = end_date.replace(day=1)
                    s1, e1 = first_this, end_date
                    # prior month
                    last_month_end = first_this - timedelta(days=1)
                    s2 = last_month_end.replace(day=1)
                    # same elapsed days
                    elapsed = (e1 - s1).days
                    e2_candidate = s2 + timedelta(days=elapsed)
                    # cap to end of prior month
                    _, last_day = __import__('calendar').monthrange(s2.year, s2.month)
                    e2 = min(e2_candidate, datetime(s2.year, s2.month, last_day).date())
                    return (f"MTD {end_date.strftime('%b %Y')}", s1, e1, f"Prior MTD {last_month_end.strftime('%b %Y')}", s2, e2)

                # 9) QTD vs prior QTD or "this quarter vs last quarter"
                if (re.search(r"\b(qtd|quarter[-\s]?to[-\s]?date)\b", msg) and re.search(r"\b(prior|previous|last)\s+qtd\b", msg)) or ("this quarter" in msg and ("last quarter" in msg or "previous quarter" in msg or "prior quarter" in msg)):
                    # current quarter start
                    q = (end_date.month - 1) // 3 + 1
                    if q == 1:
                        s1 = end_date.replace(month=1, day=1)
                    elif q == 2:
                        s1 = end_date.replace(month=4, day=1)
                    elif q == 3:
                        s1 = end_date.replace(month=7, day=1)
                    else:
                        s1 = end_date.replace(month=10, day=1)
                    e1 = end_date
                    # previous quarter start
                    py, pq = (end_date.year - 1, 4) if q == 1 else (end_date.year, q - 1)
                    if pq == 1:
                        ps2 = datetime(py, 1, 1).date()
                    elif pq == 2:
                        ps2 = datetime(py, 4, 1).date()
                    elif pq == 3:
                        ps2 = datetime(py, 7, 1).date()
                    else:
                        ps2 = datetime(py, 10, 1).date()
                    elapsed = (e1 - s1).days
                    e2 = ps2 + timedelta(days=elapsed)
                    # ensure not beyond prior quarter end
                    pq_end = (datetime(py, 3, 31).date() if pq == 1 else datetime(py, 6, 30).date() if pq == 2 else datetime(py, 9, 30).date() if pq == 3 else datetime(py, 12, 31).date())
                    if e2 > pq_end:
                        e2 = pq_end
                    return (f"QTD Q{q} {end_date.year}", s1, e1, f"Prior QTD Q{pq} {py}", ps2, e2)

                # 10) YTD vs prior YTD
                if re.search(r"\b(ytd|year[-\s]?to[-\s]?date)\b", msg) and re.search(r"\b(prior|previous|last)\s+(ytd|year)\b", msg):
                    s1 = end_date.replace(month=1, day=1)
                    e1 = end_date
                    py = end_date.year - 1
                    s2 = datetime(py, 1, 1).date()
                    elapsed = (e1 - s1).days
                    e2_candidate = s2 + timedelta(days=elapsed)
                    # cap to 31 Dec previous year
                    e2 = min(e2_candidate, datetime(py, 12, 31).date())
                    return (f"YTD {end_date.year}", s1, e1, f"Prior YTD {py}", s2, e2)

                return None

            # General compare handler (non-quarter, non-top-products, non-daily)
            if wants_vs and not wants_quarter and not wants_top_products and not wants_daily:
                parsed = try_parse_two_periods()
                if parsed:
                    lblA, sA, eA, lblB, sB, eB = parsed
                    trA, toA, tuA, aovA = summary_for_range(sA, eA)
                    trB, toB, tuB, aovB = summary_for_range(sB, eB)

                    def pct(chg_num, base):
                        return ((chg_num - base) / base * 100.0) if base else 0.0

                    dr = pct(trB, trA)
                    do = pct(toB, toA)
                    du = pct(tuB, tuA)
                    da = pct(aovB, aovA)
                    header = f"{lblA} vs {lblB}"
                    lines = [
                        f"- {lblA}: revenue ${trA:,.2f}, orders {toA}, units {tuA}, AOV ${aovA:,.2f}",
                        f"- {lblB}: revenue ${trB:,.2f}, orders {toB}, units {tuB}, AOV ${aovB:,.2f}",
                        f"- Change ({lblB} vs {lblA}): revenue {dr:+.1f}%, orders {do:+.1f}%, units {du:+.1f}%, AOV {da:+.1f}%",
                    ]
                    try:
                        sys = (
                            "You are StockPilot. Using ONLY these metrics, write a 1-2 sentence neutral comparison."
                            " Do not invent numbers."
                        )
                        content = (
                            f"User question: {req.message}\n"
                            f"Metrics JSON: {{'{lblA}': {{'revenue': {trA}, 'orders': {toA}, 'units': {tuA}, 'aov': {aovA}}},"
                            f" '{lblB}': {{'revenue': {trB}, 'orders': {toB}, 'units': {tuB}, 'aov': {aovB}}},"
                            f" 'delta_pct': {{'revenue': {dr}, 'orders': {do}, 'units': {du}, 'aov': {da}}}}}"
                        )
                        narrative = await lmstudio_client.get_chat_response([
                            {"role": "system", "content": sys},
                            {"role": "user", "content": content}
                        ], temperature=0.2, max_tokens=120)
                    except Exception:
                        narrative = ""
                    answer = header + ("\n\n" + narrative.strip() if narrative else "") + "\n\n" + "\n".join(lines)
                    metrics = {
                        "comparison": {
                            "lhs": {"label": lblA, "revenue": trA, "orders": toA, "units": tuA, "aov": aovA},
                            "rhs": {"label": lblB, "revenue": trB, "orders": toB, "units": tuB, "aov": aovB},
                            "delta_pct": {"revenue": dr, "orders": do, "units": du, "aov": da}
                        }
                    }
                    return composer.compose_bi(answer, decision.confidence, metrics=metrics, tables=tables)

            # Helper to compute headline metrics
            def compute_headline():
                nonlocal tables
                base_sql = (
                    "SELECT COALESCE(sum(gross_revenue),0) as total_revenue, "
                    "COALESCE(sum(orders_count),0) as total_orders, COALESCE(sum(units_sold),0) as total_units "
                    "FROM analytics_marts.sales_daily "
                    "WHERE org_id = :org_id AND sales_date BETWEEN :start_date AND :end_date"
                )
                params = {"org_id": org_id, "start_date": start_date, "end_date": end_date}
                if sku_filter:
                    base_sql += " AND sku = :sku"
                    params["sku"] = sku_filter
                if category_filter:
                    base_sql += " AND (LOWER(COALESCE(category,'uncategorized')) LIKE :cat_like)"
                    params["cat_like"] = f"%{category_filter.lower()}%"
                q = text(base_sql)
                res = db.execute(q, params).fetchone()
                tr = float(res.total_revenue) if res and res.total_revenue is not None else 0.0
                to = int(res.total_orders) if res and res.total_orders is not None else 0
                tu = int(res.total_units) if res and res.total_units is not None else 0
                if (not res) or (tr == 0 and to == 0 and tu == 0):
                    # Fallback: compute from raw tables
                    tables = ["orders", "order_items", "products"]
                    fb_sql = (
                        "SELECT COALESCE(SUM(oi.unit_price * oi.quantity - oi.discount),0) as total_revenue, "
                        "COUNT(DISTINCT o.id) as total_orders, COALESCE(SUM(oi.quantity),0) as total_units "
                        "FROM orders o JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id "
                        "WHERE o.org_id = :org_id AND o.status IN ('fulfilled','completed','shipped') "
                        "AND o.ordered_at::date BETWEEN :start_date AND :end_date"
                    )
                    fb_params = {"org_id": org_id, "start_date": start_date, "end_date": end_date}
                    if sku_filter:
                        fb_sql += " AND p.sku = :sku"
                        fb_params["sku"] = sku_filter
                    if category_filter:
                        fb_sql += " AND (LOWER(COALESCE(p.category,'uncategorized')) LIKE :cat_like)"
                        fb_params["cat_like"] = f"%{category_filter.lower()}%"
                    fq = text(fb_sql)
                    fres = db.execute(fq, fb_params).fetchone()
                    tr = float(fres.total_revenue) if fres and fres.total_revenue is not None else 0.0
                    to = int(fres.total_orders) if fres and fres.total_orders is not None else 0
                    tu = int(fres.total_units) if fres and fres.total_units is not None else 0
                return tr, to, tu

            # Profit headline computation (gross profit = revenue - cost)
            def compute_profit_headline():
                nonlocal tables
                try:
                    base_sql = (
                        "SELECT COALESCE(sum(gross_revenue),0) as total_revenue, "
                        "COALESCE(sum(orders_count),0) as total_orders, COALESCE(sum(units_sold),0) as total_units, "
                        "COALESCE(sum(gross_profit),0) as total_profit "
                        "FROM analytics_marts.sales_daily "
                        "WHERE org_id = :org_id AND sales_date BETWEEN :start_date AND :end_date"
                    )
                    params = {"org_id": org_id, "start_date": start_date, "end_date": end_date}
                    if sku_filter:
                        base_sql += " AND sku = :sku"
                        params["sku"] = sku_filter
                    if category_filter:
                        base_sql += " AND (LOWER(COALESCE(category,'uncategorized')) LIKE :cat_like)"
                        params["cat_like"] = f"%{category_filter.lower()}%"
                    r = db.execute(text(base_sql), params).fetchone()
                    tr = float(getattr(r, 'total_revenue', 0) or 0)
                    to = int(getattr(r, 'total_orders', 0) or 0)
                    tu = int(getattr(r, 'total_units', 0) or 0)
                    tp = float(getattr(r, 'total_profit', 0) or 0)
                    if tr == 0 and to == 0 and tu == 0 and tp == 0:
                        raise Exception("empty_mart")
                except Exception:
                    db.rollback()
                    tables = ["orders", "order_items", "products"]
                    fb_sql = (
                        "SELECT COALESCE(SUM(oi.unit_price * oi.quantity - oi.discount),0) as total_revenue, "
                        "COUNT(DISTINCT o.id) as total_orders, COALESCE(SUM(oi.quantity),0) as total_units, "
                        "COALESCE(SUM((oi.unit_price * oi.quantity - oi.discount) - (COALESCE(p.cost,0) * oi.quantity)),0) as total_profit "
                        "FROM orders o JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id "
                        "WHERE o.org_id = :org_id AND o.status IN ('fulfilled','completed','shipped') "
                        "AND o.ordered_at::date BETWEEN :start_date AND :end_date"
                    )
                    fb_params = {"org_id": org_id, "start_date": start_date, "end_date": end_date}
                    if sku_filter:
                        fb_sql += " AND p.sku = :sku"
                        fb_params["sku"] = sku_filter
                    if category_filter:
                        fb_sql += " AND (LOWER(COALESCE(p.category,'uncategorized')) LIKE :cat_like)"
                        fb_params["cat_like"] = f"%{category_filter.lower()}%"
                    r = db.execute(text(fb_sql), fb_params).fetchone()
                    tr = float(getattr(r, 'total_revenue', 0) or 0)
                    to = int(getattr(r, 'total_orders', 0) or 0)
                    tu = int(getattr(r, 'total_units', 0) or 0)
                    tp = float(getattr(r, 'total_profit', 0) or 0)
                margin_pct = (tp / tr * 100.0) if tr else 0.0
                aov = (tr / to) if to > 0 else 0.0
                return tr, to, tu, aov, tp, margin_pct

            # Top products intent
            if wants_top_products:
                limit = 5
                mlim = re.search(r"top\s+(\d{1,2})", msg)
                if mlim:
                    try:
                        limit = max(1, min(20, int(mlim.group(1))))
                    except Exception:
                        pass
                # Mart-first: aggregate by product (allow profit ordering)
                select_profit = ", SUM(gross_profit) as total_profit" if wants_profit else ""
                order_metric = "total_profit" if wants_profit else "total_revenue"
                where_extra = ""
                params = {"org_id": org_id, "start_date": start_date, "end_date": end_date}
                if sku_filter:
                    where_extra += " AND sku = :sku"
                    params["sku"] = sku_filter
                if category_filter:
                    where_extra += " AND (LOWER(COALESCE(category,'uncategorized')) LIKE :cat_like)"
                    params["cat_like"] = f"%{category_filter.lower()}%"
                qtp = text(
                    f"""
                    SELECT product_name, sku, COALESCE(category, 'Uncategorized') as category,
                           SUM(gross_revenue) as total_revenue, SUM(units_sold) as total_units{select_profit}
                    FROM analytics_marts.sales_daily
                    WHERE org_id = :org_id AND sales_date BETWEEN :start_date AND :end_date{where_extra}
                    GROUP BY product_name, sku, category
                    ORDER BY {order_metric} DESC
                    LIMIT {limit}
                    """
                )
                rows = []
                try:
                    rows = db.execute(qtp, params).fetchall()
                    if not rows:
                        raise Exception("no_mart_rows")
                except Exception:
                    db.rollback()
                    tables = ["orders", "order_items", "products"]
                    fb_sql = (
                        "SELECT p.name as product_name, p.sku as sku, COALESCE(p.category, 'Uncategorized') as category, "
                        "SUM(oi.unit_price * oi.quantity - oi.discount) as total_revenue, SUM(oi.quantity) as total_units"
                        + (", COALESCE(SUM((oi.unit_price * oi.quantity - oi.discount) - (COALESCE(p.cost,0) * oi.quantity)),0) as total_profit" if wants_profit else "") +
                        " FROM orders o JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id "
                        "WHERE o.org_id = :org_id AND o.ordered_at::date BETWEEN :start_date AND :end_date "
                        "AND o.status IN ('fulfilled','completed','shipped')"
                    )
                    fb_params = {"org_id": org_id, "start_date": start_date, "end_date": end_date}
                    if sku_filter:
                        fb_sql += " AND p.sku = :sku"
                        fb_params["sku"] = sku_filter
                    if category_filter:
                        fb_sql += " AND (LOWER(COALESCE(p.category,'uncategorized')) LIKE :cat_like)"
                        fb_params["cat_like"] = f"%{category_filter.lower()}%"
                    order_clause = " ORDER BY total_profit DESC" if wants_profit else " ORDER BY total_revenue DESC"
                    fb_sql += " GROUP BY p.name, p.sku, COALESCE(p.category, 'Uncategorized')" + order_clause + f" LIMIT {limit}"
                    rows = db.execute(text(fb_sql), fb_params).fetchall()

                top_lines = []
                rank = 1
                for r in rows:
                    try:
                        if wants_profit and hasattr(r, 'total_profit'):
                            top_lines.append(f"{rank}. {r.sku} – {r.product_name} • ${float(r.total_revenue or 0):,.0f} rev, ${float(getattr(r,'total_profit',0) or 0):,.0f} profit, {int(r.total_units or 0)} units")
                        else:
                            top_lines.append(f"{rank}. {r.sku} – {r.product_name} • ${float(r.total_revenue or 0):,.0f} revenue, {int(r.total_units or 0)} units")
                    except Exception:
                        # SQLite Row access fallback by index
                        if wants_profit and len(r) >= 6:
                            top_lines.append(f"{rank}. {r[1]} – {r[0]} • ${float(r[3] or 0):,.0f} rev, ${float(r[5] or 0):,.0f} profit, {int(r[4] or 0)} units")
                        else:
                            top_lines.append(f"{rank}. {r[1]} – {r[0]} • ${float(r[3] or 0):,.0f} revenue, {int(r[4] or 0)} units")
                    rank += 1

                tr, to, tu = compute_headline()
                aov = (tr / to) if to > 0 else 0.0
                period_label = f"{start_date.isoformat()} to {end_date.isoformat()}"

                narrative = "Top products" + (f" (top {limit})" if limit else "") + f" for {period_label}:\n" + ("\n".join(top_lines) if top_lines else "No sales recorded.")
                # Keep narrative concise; still include headline metrics block
                answer = (
                    f"{narrative}\n\n"
                    f"Headline metrics for {period_label}:\n"
                    f"- Total revenue: ${tr:,.2f}\n- Total orders: {to}\n- Total units: {tu}\n- Average order value: ${aov:,.2f}"
                )
                metrics = {"period": period_label, "total_revenue": tr, "total_orders": to, "total_units": tu, "aov": aov}
                return composer.compose_bi(answer, decision.confidence, metrics=metrics, tables=tables)

            # Category breakdown intent (top 5 categories)
            if wants_category_breakdown:
                where_extra = ""
                params = {"org_id": org_id, "start_date": start_date, "end_date": end_date}
                if sku_filter:
                    where_extra += " AND sku = :sku"
                    params["sku"] = sku_filter
                qcat = text(
                    f"""
                    SELECT COALESCE(category,'Uncategorized') as category, 
                           SUM(gross_revenue) as revenue, SUM(units_sold) as units
                    FROM analytics_marts.sales_daily
                    WHERE org_id = :org_id AND sales_date BETWEEN :start_date AND :end_date{where_extra}
                    GROUP BY COALESCE(category,'Uncategorized')
                    ORDER BY revenue DESC
                    LIMIT 5
                    """
                )
                rows = []
                try:
                    rows = db.execute(qcat, params).fetchall()
                    if not rows:
                        raise Exception("no_mart_rows")
                except Exception:
                    db.rollback()
                    tables = ["orders", "order_items", "products"]
                    fb_sql = (
                        "SELECT COALESCE(p.category,'Uncategorized') as category, "
                        "SUM(oi.unit_price * oi.quantity - oi.discount) as revenue, SUM(oi.quantity) as units "
                        "FROM orders o JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id "
                        "WHERE o.org_id = :org_id AND o.status IN ('fulfilled','completed','shipped') "
                        "AND o.ordered_at::date BETWEEN :start_date AND :end_date"
                    )
                    fb_params = {"org_id": org_id, "start_date": start_date, "end_date": end_date}
                    if sku_filter:
                        fb_sql += " AND p.sku = :sku"
                        fb_params["sku"] = sku_filter
                    fb_sql += " GROUP BY COALESCE(p.category,'Uncategorized') ORDER BY revenue DESC LIMIT 5"
                    rows = db.execute(text(fb_sql), fb_params).fetchall()

                lines = []
                for r in rows:
                    try:
                        lines.append(f"- {r.category}: ${float(r.revenue or 0):,.0f} • {int(r.units or 0)} units")
                    except Exception:
                        lines.append(f"- {r[0]}: ${float(r[1] or 0):,.0f} • {int(r[2] or 0)} units")

                tr, to, tu = compute_headline()
                aov = (tr / to) if to > 0 else 0.0
                period_label = f"{start_date.isoformat()} to {end_date.isoformat()}"
                answer = (
                    f"Top categories for {period_label} (max 5):\n" + ("\n".join(lines) if lines else "No sales recorded.") +
                    f"\n\nHeadline metrics for {period_label}:\n- Total revenue: ${tr:,.2f}\n- Total orders: {to}\n- Total units: {tu}\n- AOV: ${aov:,.2f}"
                )
                metrics = {"period": period_label, "total_revenue": tr, "total_orders": to, "total_units": tu, "aov": aov}
                return composer.compose_bi(answer, decision.confidence, metrics=metrics, tables=tables)

            # Inventory snapshot by SKU (sum movements per location)
            if wants_inventory and sku_filter:
                try:
                    inv_sql = text(
                        """
                        SELECT l.name as location_name, COALESCE(SUM(m.quantity),0) as on_hand
                        FROM inventory_movements m
                        JOIN products p ON p.id = m.product_id
                        JOIN locations l ON l.id = m.location_id
                        WHERE p.org_id = :org_id AND p.sku = :sku
                        GROUP BY l.name
                        ORDER BY l.name
                        """
                    )
                    rows = db.execute(inv_sql, {"org_id": org_id, "sku": sku_filter}).fetchall()
                    per_loc = []
                    total = 0
                    for r in rows:
                        try:
                            per_loc.append(f"- {r.location_name}: {int(r.on_hand or 0)} units")
                            total += int(r.on_hand or 0)
                        except Exception:
                            per_loc.append(f"- {r[0]}: {int(r[1] or 0)} units")
                            total += int(r[1] or 0)
                    answer = f"On-hand inventory for SKU {sku_filter}: {total} units\n" + ("\n".join(per_loc) if per_loc else "No inventory movements found.")
                    metrics = {"sku": sku_filter, "on_hand_total": total}
                    return composer.compose_bi(answer, decision.confidence, metrics=metrics, tables=["inventory_movements"])
                except Exception as e:
                    logging.warning(f"Inventory snapshot error: {e}")
                    # fall through to default BI summary

            # Daily time series intent
            if wants_daily:
                # Mart-first daily rollup
                base_sql = (
                    "SELECT sales_date::date as d, COALESCE(sum(gross_revenue),0) as revenue, "
                    "COALESCE(sum(orders_count),0) as orders, COALESCE(sum(units_sold),0) as units "
                    "FROM analytics_marts.sales_daily WHERE org_id = :org_id "
                    "AND sales_date BETWEEN :start_date AND :end_date"
                )
                params = {"org_id": org_id, "start_date": start_date, "end_date": end_date}
                if sku_filter:
                    base_sql += " AND sku = :sku"
                    params["sku"] = sku_filter
                if category_filter:
                    base_sql += " AND (LOWER(COALESCE(category,'uncategorized')) LIKE :cat_like)"
                    params["cat_like"] = f"%{category_filter.lower()}%"
                base_sql += " GROUP BY sales_date::date ORDER BY sales_date::date"
                qd = text(base_sql)
                rows = []
                try:
                    rows = db.execute(qd, params).fetchall()
                    if not rows:
                        raise Exception("no_mart_rows")
                except Exception:
                    db.rollback()
                    tables = ["orders", "order_items"]
                    fb_sql = (
                        "SELECT o.ordered_at::date as d, COALESCE(SUM(oi.unit_price * oi.quantity - oi.discount),0) as revenue, "
                        "COUNT(DISTINCT o.id) as orders, COALESCE(SUM(oi.quantity),0) as units "
                        "FROM orders o JOIN order_items oi ON oi.order_id = o.id "
                        "WHERE o.org_id = :org_id AND o.status IN ('fulfilled','completed','shipped') "
                        "AND o.ordered_at::date BETWEEN :start_date AND :end_date"
                    )
                    fb_params = {"org_id": org_id, "start_date": start_date, "end_date": end_date}
                    if sku_filter:
                        fb_sql += " AND oi.product_id IN (SELECT id FROM products WHERE sku = :sku)"
                        fb_params["sku"] = sku_filter
                    if category_filter:
                        fb_sql += " AND oi.product_id IN (SELECT id FROM products WHERE LOWER(COALESCE(category,'uncategorized')) LIKE :cat_like)"
                        fb_params["cat_like"] = f"%{category_filter.lower()}%"
                    fb_sql += " GROUP BY o.ordered_at::date ORDER BY o.ordered_at::date"
                    rows = db.execute(text(fb_sql), fb_params).fetchall()

                # Build concise answer: show up to last 10 rows
                series_lines = []
                for r in rows[-10:]:  # show last 10 days to keep concise
                    try:
                        series_lines.append(f"{r.d}: ${float(r.revenue or 0):,.0f} • {int(r.orders or 0)} orders • {int(r.units or 0)} units")
                    except Exception:
                        series_lines.append(f"{r[0]}: ${float(r[1] or 0):,.0f} • {int(r[2] or 0)} orders • {int(r[3] or 0)} units")

                tr, to, tu = compute_headline()
                aov = (tr / to) if to > 0 else 0.0
                period_label = f"{start_date.isoformat()} to {end_date.isoformat()}"
                answer = (
                    f"Daily sales for {period_label} (showing last {min(10, len(rows))} days):\n" +
                    ("\n".join(series_lines) if series_lines else "No daily sales recorded.") +
                    f"\n\nHeadline metrics for {period_label}:\n- Total revenue: ${tr:,.2f}\n- Total orders: {to}\n- Total units: {tu}\n- Average order value: ${aov:,.2f}"
                )
                metrics = {"period": period_label, "total_revenue": tr, "total_orders": to, "total_units": tu, "aov": aov}
                return composer.compose_bi(answer, decision.confidence, metrics=metrics, tables=tables)

            # Quarter summary or comparison intent
            if wants_quarter:
                # Helper: quarter start/end
                def quarter_range(y: int, q: int):
                    if q == 1:
                        return datetime(y, 1, 1).date(), datetime(y, 3, 31).date()
                    if q == 2:
                        return datetime(y, 4, 1).date(), datetime(y, 6, 30).date()
                    if q == 3:
                        return datetime(y, 7, 1).date(), datetime(y, 9, 30).date()
                    return datetime(y, 10, 1).date(), datetime(y, 12, 31).date()

                def prev_quarter(y: int, q: int) -> tuple[int, int]:
                    if q == 1:
                        return (y - 1, 4)
                    return (y, q - 1)

                def summary_for_range(s: date, e: date):
                    nonlocal tables
                    base_sql = (
                        "SELECT COALESCE(sum(gross_revenue),0) as total_revenue, "
                        "COALESCE(sum(orders_count),0) as total_orders, COALESCE(sum(units_sold),0) as total_units "
                        "FROM analytics_marts.sales_daily WHERE org_id = :org_id "
                        "AND sales_date BETWEEN :start_date AND :end_date"
                    )
                    params = {"org_id": org_id, "start_date": s, "end_date": e}
                    if sku_filter:
                        base_sql += " AND sku = :sku"
                        params["sku"] = sku_filter
                    if category_filter:
                        base_sql += " AND (LOWER(COALESCE(category,'uncategorized')) LIKE :cat_like)"
                        params["cat_like"] = f"%{category_filter.lower()}%"
                    r = db.execute(text(base_sql), params).fetchone()
                    tr = float(r.total_revenue) if r and r.total_revenue is not None else 0.0
                    to = int(r.total_orders) if r and r.total_orders is not None else 0
                    tu = int(r.total_units) if r and r.total_units is not None else 0
                    if (not r) or (tr == 0 and to == 0 and tu == 0):
                        tables = ["orders", "order_items", "products"]
                        fb_sql = (
                            "SELECT COALESCE(SUM(oi.unit_price * oi.quantity - oi.discount),0) as total_revenue, "
                            "COUNT(DISTINCT o.id) as total_orders, COALESCE(SUM(oi.quantity),0) as total_units "
                            "FROM orders o JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id "
                            "WHERE o.org_id = :org_id AND o.status IN ('fulfilled','completed','shipped') "
                            "AND o.ordered_at::date BETWEEN :start_date AND :end_date"
                        )
                        fb_params = {"org_id": org_id, "start_date": s, "end_date": e}
                        if sku_filter:
                            fb_sql += " AND p.sku = :sku"
                            fb_params["sku"] = sku_filter
                        if category_filter:
                            fb_sql += " AND (LOWER(COALESCE(p.category,'uncategorized')) LIKE :cat_like)"
                            fb_params["cat_like"] = f"%{category_filter.lower()}%"
                        fr = db.execute(text(fb_sql), fb_params).fetchone()
                        tr = float(fr.total_revenue) if fr and fr.total_revenue is not None else 0.0
                        to = int(fr.total_orders) if fr and fr.total_orders is not None else 0
                        tu = int(fr.total_units) if fr and fr.total_units is not None else 0
                    aov = (tr / to) if to > 0 else 0.0
                    return tr, to, tu, aov

                # Parse up to two quarter tokens, each may include an explicit year (e.g., Q1 2024 vs Q1 2025)
                q_tokens = list(re.finditer(r"\bq([1-4])\b(?:\s*(20\d{2}))?", msg))
                # Fallback: original q_matches with a single global year context
                year_match = re.search(r"\b(20\d{2})\b", msg)
                default_year = int(year_match.group(1)) if year_match else datetime.now().year
                if len(q_tokens) == 0 and len(q_matches) > 0:
                    q_tokens = [re.search(r"\bq([1-4])\b", msg)] * len(q_matches)

                # Determine comparison type
                if wants_vs and len(q_tokens) >= 2:
                    qA = int(q_tokens[0].group(1)) if q_tokens[0] else int(q_matches[0])
                    yA = int(q_tokens[0].group(2)) if (q_tokens[0] and q_tokens[0].lastindex == 2 and q_tokens[0].group(2)) else default_year
                    qB = int(q_tokens[1].group(1)) if q_tokens[1] else int(q_matches[1])
                    yB = int(q_tokens[1].group(2)) if (q_tokens[1] and q_tokens[1].lastindex == 2 and q_tokens[1].group(2)) else default_year
                    sA, eA = quarter_range(yA, qA)
                    sB, eB = quarter_range(yB, qB)
                    trA, toA, tuA, aovA = summary_for_range(sA, eA)
                    trB, toB, tuB, aovB = summary_for_range(sB, eB)

                    def pct(chg_num, base):
                        return ((chg_num - base) / base * 100.0) if base else 0.0

                    dr = pct(trB, trA)
                    do = pct(toB, toA)
                    du = pct(tuB, tuA)
                    da = pct(aovB, aovA)
                    header = f"Q{qA} {yA} vs Q{qB} {yB}"
                    lines = [
                        f"- Q{qA} {yA}: revenue ${trA:,.2f}, orders {toA}, units {tuA}, AOV ${aovA:,.2f}",
                        f"- Q{qB} {yB}: revenue ${trB:,.2f}, orders {toB}, units {tuB}, AOV ${aovB:,.2f}",
                        f"- Change (Q{qB} {yB} vs Q{qA} {yA}): revenue {dr:+.1f}%, orders {do:+.1f}%, units {du:+.1f}%, AOV {da:+.1f}%",
                    ]
                    # Optional concise LLM narrative constrained to metrics
                    try:
                        sys = (
                            "You are StockPilot. Using ONLY these metrics, write a 1-2 sentence neutral comparison."
                            " Do not invent numbers."
                        )
                        content = (
                            f"User question: {req.message}\n" 
                            f"Metrics JSON: {{'Q{qA} {yA}': {{'revenue': {trA}, 'orders': {toA}, 'units': {tuA}, 'aov': {aovA}}},"
                            f" 'Q{qB} {yB}': {{'revenue': {trB}, 'orders': {toB}, 'units': {tuB}, 'aov': {aovB}}},"
                            f" 'delta_pct': {{'revenue': {dr}, 'orders': {do}, 'units': {du}, 'aov': {da}}}}}"
                        )
                        narrative = await lmstudio_client.get_chat_response([
                            {"role": "system", "content": sys},
                            {"role": "user", "content": content}
                        ], temperature=0.2, max_tokens=120)
                    except Exception:
                        narrative = ""
                    answer = header + ("\n\n" + narrative.strip() if narrative else "") + "\n\n" + "\n".join(lines)
                    metrics = {
                        "comparison": {
                "lhs": {"label": f"Q{qA} {yA}", "revenue": trA, "orders": toA, "units": tuA, "aov": aovA},
                "rhs": {"label": f"Q{qB} {yB}", "revenue": trB, "orders": toB, "units": tuB, "aov": aovB},
                            "delta_pct": {"revenue": dr, "orders": do, "units": du, "aov": da}
                        }
                    }
                    return composer.compose_bi(answer, decision.confidence, metrics=metrics, tables=tables)
                else:
                    # Single quarter summary
                    # Prefer explicit token with optional year; else fallback
                    qN = int(q_matches[0])
                    year_match = re.search(r"\b(20\d{2})\b", msg)
                    q_year = int(year_match.group(1)) if year_match else datetime.now().year
                    sQ, eQ = quarter_range(q_year, qN)
                    trQ, toQ, tuQ, aovQ = summary_for_range(sQ, eQ)
                    period_label = f"Q{qN} {q_year}"
                    answer = (
                        f"Sales summary for {period_label}:\n"
                        f"- Total revenue: ${trQ:,.2f}\n- Total orders: {toQ}\n- Total units: {tuQ}\n- Average order value: ${aovQ:,.2f}"
                    )
                    metrics = {"period": period_label, "total_revenue": trQ, "total_orders": toQ, "total_units": tuQ, "aov": aovQ}
                    return composer.compose_bi(answer, decision.confidence, metrics=metrics, tables=tables)

            # Profit headline (when asked directly and not other specific intents)
            if wants_profit and not wants_top_products and not wants_daily and not wants_vs and not wants_category_breakdown and not wants_quarter:
                tr2 = to2 = tu2 = aov2 = tp = margin_pct = 0.0
                try:
                    rtr, rto, rtu, raov, rtp, rmp = compute_profit_headline()
                    tr2, to2, tu2, aov2, tp, margin_pct = rtr, rto, rtu, raov, rtp, rmp
                except Exception as e:
                    logging.warning(f"Profit headline error: {e}")
                period_label = f"{start_date.isoformat()} to {end_date.isoformat()}"
                answer = (
                    f"Profit summary for {period_label}:\n"
                    f"- Revenue: ${tr2:,.2f}\n- Orders: {int(to2)}\n- Units: {int(tu2)}\n- AOV: ${aov2:,.2f}\n- Gross profit: ${tp:,.2f}\n- Margin: {margin_pct:.1f}%"
                )
                metrics = {"period": period_label, "revenue": tr2, "orders": int(to2), "units": int(tu2), "aov": aov2, "gross_profit": tp, "margin_pct": margin_pct}
                return composer.compose_bi(answer, decision.confidence, metrics=metrics, tables=tables)

            # Default: headline summary
            # Mart-first query for headline metrics
            tr, to, tu = compute_headline()

            aov = (tr / to) if to > 0 else 0.0
            period_label = f"{start_date.isoformat()} to {end_date.isoformat()}"
            # Compose a concise narrative using LLM (no new numbers)
            try:
                sys = (
                    "You are StockPilot. Write a concise, neutral summary using ONLY the provided metrics.\n"
                    "Do not invent new numbers. Keep it 2-3 sentences max."
                )
                content = (
                    f"User question: {req.message}\n"
                    f"Period: {period_label}\n"
                    f"Metrics JSON: {{'total_revenue': {tr}, 'total_orders': {to}, 'total_units': {tu}, 'aov': {aov}}}"
                )
                narrative = await lmstudio_client.get_chat_response([
                    {"role": "system", "content": sys},
                    {"role": "user", "content": content}
                ], temperature=0.2, max_tokens=160)
            except Exception:
                narrative = ""
            answer = (narrative.strip() + ("\n\n" if narrative else "") +
                f"Sales summary for {period_label}:\n"
                f"- Total revenue: ${tr:,.2f}\n"
                f"- Total orders: {to}\n"
                f"- Total units: {tu}\n"
                f"- Average order value: ${aov:,.2f}")
            metrics = {
                "period": period_label,
                "total_revenue": tr,
                "total_orders": to,
                "total_units": tu,
                "aov": aov,
            }
            return composer.compose_bi(answer, decision.confidence, metrics=metrics, tables=tables)
        except Exception as e:
            logging.warning(f"BI path error: {e}")
            return composer.compose_no_answer("Analytics temporarily unavailable", ["Try again later", "Open Analytics page"])

    if decision.route == "OPEN":
        try:
            # Simple assistant answer (no BI/data fetching)
            system_prompt = (
                "You are StockPilot assistant.\n"
                "- Do not invent company-specific numbers.\n"
                "- If the user asks for sales/revenue/metrics, explain you don't have direct access via chat and suggest using the Analytics pages or scheduled Reports.\n"
                "- Offer concrete next steps inside StockPilot (e.g., view Analytics, run Week-in-Review report).\n"
                "- Keep responses concise and actionable."
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message}
            ]
            response = await lmstudio_client.get_chat_response(messages, temperature=0.3)
            if not response:
                raise ValueError("empty_llm_response")
            follow_ups = [
                "Open Analytics → Sales overview",
                "Generate Week-in-Review report",
                "Ask a policy/document question"
            ]
            return composer.compose_open(response, follow_ups)
        except Exception as e:
            logging.warning(f"LM Studio chat error: {e}")
            return composer.compose_no_answer("Assistant temporarily unavailable", ["Retry in a moment"])
    return composer.compose_no_answer("Unable to determine an answer path", ["Ask a simpler question"])
