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
            wants_vs = (" vs " in msg or "versus" in msg)

            # Helper to compute headline metrics
            def compute_headline():
                nonlocal tables
                q = text(
                    """
                    SELECT 
                        COALESCE(sum(gross_revenue),0) as total_revenue,
                        COALESCE(sum(orders_count),0) as total_orders,
                        COALESCE(sum(units_sold),0) as total_units
                    FROM analytics_marts.sales_daily
                    WHERE org_id = :org_id
                      AND sales_date BETWEEN :start_date AND :end_date
                    """
                )
                res = db.execute(q, {"org_id": org_id, "start_date": start_date, "end_date": end_date}).fetchone()
                tr = float(res.total_revenue) if res and res.total_revenue is not None else 0.0
                to = int(res.total_orders) if res and res.total_orders is not None else 0
                tu = int(res.total_units) if res and res.total_units is not None else 0
                if (not res) or (tr == 0 and to == 0 and tu == 0):
                    # Fallback: compute from raw tables
                    tables = ["orders", "order_items", "products"]
                    fq = text(
                        """
                        SELECT 
                            COALESCE(SUM(oi.quantity * oi.unit_price),0) as total_revenue,
                            COUNT(DISTINCT o.id) as total_orders,
                            COALESCE(SUM(oi.quantity),0) as total_units
                        FROM orders o
                        JOIN order_items oi ON oi.order_id = o.id
                        JOIN products p ON p.id = oi.product_id
                        WHERE o.org_id = :org_id
                          AND o.status IN ('fulfilled','completed','shipped')
                          AND o.ordered_at::date BETWEEN :start_date AND :end_date
                        """
                    )
                    fres = db.execute(fq, {"org_id": org_id, "start_date": start_date, "end_date": end_date}).fetchone()
                    tr = float(fres.total_revenue) if fres and fres.total_revenue is not None else 0.0
                    to = int(fres.total_orders) if fres and fres.total_orders is not None else 0
                    tu = int(fres.total_units) if fres and fres.total_units is not None else 0
                return tr, to, tu

            # Top products intent
            if wants_top_products:
                limit = 5
                mlim = re.search(r"top\s+(\d{1,2})", msg)
                if mlim:
                    try:
                        limit = max(1, min(20, int(mlim.group(1))))
                    except Exception:
                        pass
                # Mart-first: aggregate by product
                qtp = text(
                    f"""
                    SELECT 
                        product_name,
                        sku,
                        COALESCE(category, 'Uncategorized') as category,
                        SUM(gross_revenue) as total_revenue,
                        SUM(units_sold) as total_units
                    FROM analytics_marts.sales_daily
                    WHERE org_id = :org_id
                      AND sales_date BETWEEN :start_date AND :end_date
                    GROUP BY product_name, sku, category
                    ORDER BY total_revenue DESC
                    LIMIT {limit}
                    """
                )
                rows = []
                try:
                    rows = db.execute(qtp, {"org_id": org_id, "start_date": start_date, "end_date": end_date}).fetchall()
                    if not rows:
                        raise Exception("no_mart_rows")
                except Exception:
                    db.rollback()
                    tables = ["orders", "order_items", "products"]
                    qtp_fb = text(
                        f"""
                        SELECT 
                            p.name as product_name,
                            p.sku as sku,
                            COALESCE(p.category, 'Uncategorized') as category,
                            SUM(oi.unit_price * oi.quantity - oi.discount) as total_revenue,
                            SUM(oi.quantity) as total_units
                        FROM orders o
                        JOIN order_items oi ON o.id = oi.order_id
                        JOIN products p ON oi.product_id = p.id
                        WHERE o.org_id = :org_id
                          AND o.ordered_at::date BETWEEN :start_date AND :end_date
                          AND o.status IN ('fulfilled','completed','shipped')
                        GROUP BY p.name, p.sku, COALESCE(p.category, 'Uncategorized')
                        ORDER BY total_revenue DESC
                        LIMIT {limit}
                        """
                    )
                    rows = db.execute(qtp_fb, {"org_id": org_id, "start_date": start_date, "end_date": end_date}).fetchall()

                top_lines = []
                rank = 1
                for r in rows:
                    try:
                        top_lines.append(f"{rank}. {r.sku} – {r.product_name} • ${float(r.total_revenue or 0):,.0f} revenue, {int(r.total_units or 0)} units")
                    except Exception:
                        # SQLite Row access fallback by index
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

            # Daily time series intent
            if wants_daily:
                # Mart-first daily rollup
                qd = text(
                    """
                    SELECT sales_date::date as d, 
                           COALESCE(sum(gross_revenue),0) as revenue,
                           COALESCE(sum(orders_count),0) as orders,
                           COALESCE(sum(units_sold),0) as units
                    FROM analytics_marts.sales_daily
                    WHERE org_id = :org_id
                      AND sales_date BETWEEN :start_date AND :end_date
                    GROUP BY sales_date::date
                    ORDER BY sales_date::date
                    """
                )
                rows = []
                try:
                    rows = db.execute(qd, {"org_id": org_id, "start_date": start_date, "end_date": end_date}).fetchall()
                    if not rows:
                        raise Exception("no_mart_rows")
                except Exception:
                    db.rollback()
                    tables = ["orders", "order_items"]
                    qd_fb = text(
                        """
                        SELECT o.ordered_at::date as d,
                               COALESCE(SUM(oi.unit_price * oi.quantity - oi.discount),0) as revenue,
                               COUNT(DISTINCT o.id) as orders,
                               COALESCE(SUM(oi.quantity),0) as units
                        FROM orders o
                        JOIN order_items oi ON oi.order_id = o.id
                        WHERE o.org_id = :org_id
                          AND o.status IN ('fulfilled','completed','shipped')
                          AND o.ordered_at::date BETWEEN :start_date AND :end_date
                        GROUP BY o.ordered_at::date
                        ORDER BY o.ordered_at::date
                        """
                    )
                    rows = db.execute(qd_fb, {"org_id": org_id, "start_date": start_date, "end_date": end_date}).fetchall()

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
                # Resolve year: explicit in text else current year
                year_match = re.search(r"\b(20\d{2})\b", msg)
                q_year = int(year_match.group(1)) if year_match else datetime.now().year

                def quarter_range(y: int, q: int):
                    if q == 1:
                        return datetime(y, 1, 1).date(), datetime(y, 3, 31).date()
                    if q == 2:
                        return datetime(y, 4, 1).date(), datetime(y, 6, 30).date()
                    if q == 3:
                        return datetime(y, 7, 1).date(), datetime(y, 9, 30).date()
                    return datetime(y, 10, 1).date(), datetime(y, 12, 31).date()

                def summary_for_range(s: date, e: date):
                    nonlocal tables
                    q = text(
                        """
                        SELECT 
                            COALESCE(sum(gross_revenue),0) as total_revenue,
                            COALESCE(sum(orders_count),0) as total_orders,
                            COALESCE(sum(units_sold),0) as total_units
                        FROM analytics_marts.sales_daily
                        WHERE org_id = :org_id
                          AND sales_date BETWEEN :start_date AND :end_date
                        """
                    )
                    r = db.execute(q, {"org_id": org_id, "start_date": s, "end_date": e}).fetchone()
                    tr = float(r.total_revenue) if r and r.total_revenue is not None else 0.0
                    to = int(r.total_orders) if r and r.total_orders is not None else 0
                    tu = int(r.total_units) if r and r.total_units is not None else 0
                    if (not r) or (tr == 0 and to == 0 and tu == 0):
                        tables = ["orders", "order_items", "products"]
                        fq = text(
                            """
                            SELECT 
                                COALESCE(SUM(oi.quantity * oi.unit_price),0) as total_revenue,
                                COUNT(DISTINCT o.id) as total_orders,
                                COALESCE(SUM(oi.quantity),0) as total_units
                            FROM orders o
                            JOIN order_items oi ON oi.order_id = o.id
                            JOIN products p ON p.id = oi.product_id
                            WHERE o.org_id = :org_id
                              AND o.status IN ('fulfilled','completed','shipped')
                              AND o.ordered_at::date BETWEEN :start_date AND :end_date
                            """
                        )
                        fr = db.execute(fq, {"org_id": org_id, "start_date": s, "end_date": e}).fetchone()
                        tr = float(fr.total_revenue) if fr and fr.total_revenue is not None else 0.0
                        to = int(fr.total_orders) if fr and fr.total_orders is not None else 0
                        tu = int(fr.total_units) if fr and fr.total_units is not None else 0
                    aov = (tr / to) if to > 0 else 0.0
                    return tr, to, tu, aov

                q_list = [int(q_matches[0])] if len(q_matches) == 1 else [int(q_matches[0]), int(q_matches[1])]
                q_list = q_list[:2]
                # If user implied comparison or provided two quarters, do compare
                if wants_vs or len(q_list) == 2:
                    qA, qB = (q_list + q_list)[0], (q_list + q_list)[1]  # ensure two values
                    sA, eA = quarter_range(q_year, qA)
                    sB, eB = quarter_range(q_year, qB)
                    trA, toA, tuA, aovA = summary_for_range(sA, eA)
                    trB, toB, tuB, aovB = summary_for_range(sB, eB)

                    def pct(chg_num, base):
                        return ((chg_num - base) / base * 100.0) if base else 0.0

                    dr = pct(trB, trA)
                    do = pct(toB, toA)
                    du = pct(tuB, tuA)
                    da = pct(aovB, aovA)
                    header = f"Q{qA} {q_year} vs Q{qB} {q_year}"
                    lines = [
                        f"- Q{qA}: revenue ${trA:,.2f}, orders {toA}, units {tuA}, AOV ${aovA:,.2f}",
                        f"- Q{qB}: revenue ${trB:,.2f}, orders {toB}, units {tuB}, AOV ${aovB:,.2f}",
                        f"- Change (Q{qB} vs Q{qA}): revenue {dr:+.1f}%, orders {do:+.1f}%, units {du:+.1f}%, AOV {da:+.1f}%",
                    ]
                    # Optional concise LLM narrative constrained to metrics
                    try:
                        sys = (
                            "You are StockPilot. Using ONLY these metrics, write a 1-2 sentence neutral comparison."
                            " Do not invent numbers."
                        )
                        content = (
                            f"User question: {req.message}\n" 
                            f"Metrics JSON: {{'Q{qA}': {{'revenue': {trA}, 'orders': {toA}, 'units': {tuA}, 'aov': {aovA}}},"
                            f" 'Q{qB}': {{'revenue': {trB}, 'orders': {toB}, 'units': {tuB}, 'aov': {aovB}}},"
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
                            "lhs": {"label": f"Q{qA} {q_year}", "revenue": trA, "orders": toA, "units": tuA, "aov": aovA},
                            "rhs": {"label": f"Q{qB} {q_year}", "revenue": trB, "orders": toB, "units": tuB, "aov": aovB},
                            "delta_pct": {"revenue": dr, "orders": do, "units": du, "aov": da}
                        }
                    }
                    return composer.compose_bi(answer, decision.confidence, metrics=metrics, tables=tables)
                else:
                    # Single quarter summary
                    qN = q_list[0]
                    sQ, eQ = quarter_range(q_year, qN)
                    trQ, toQ, tuQ, aovQ = summary_for_range(sQ, eQ)
                    period_label = f"Q{qN} {q_year}"
                    answer = (
                        f"Sales summary for {period_label}:\n"
                        f"- Total revenue: ${trQ:,.2f}\n- Total orders: {toQ}\n- Total units: {tuQ}\n- Average order value: ${aovQ:,.2f}"
                    )
                    metrics = {"period": period_label, "total_revenue": trQ, "total_orders": toQ, "total_units": tuQ, "aov": aovQ}
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
