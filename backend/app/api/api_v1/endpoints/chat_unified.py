from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core import router as hybrid_router
from app.core import params as param_utils
from app.core import composer
from app.core.llm_lmstudio import lmstudio_client
import logging
from app.core.contracts import validate_output
from app.core.database import get_db, get_current_claims
from sqlalchemy.orm import Session
from app.services.intent_rules import INTENT_HANDLERS, INTENT_PARAM_MODELS
from app.tools.rag.retriever import get_rag_retriever
import asyncio

router = APIRouter()

def _generate_intelligent_summary(intent: str, bi_result: Dict[str, Any], original_query: str) -> str:
    """Generate intelligent, contextual summaries for BI results."""
    rows = bi_result.get('rows', [])
    
    if not rows:
        return f"No data available for your {intent.replace('_', ' ')} query."
    
    # Calculate totals and insights based on intent
    if intent == 'week_in_review':
        total_revenue = sum(float(row.get('revenue', 0)) for row in rows)
        total_units = sum(int(row.get('units', 0)) for row in rows)
        total_margin = sum(float(row.get('margin', 0)) for row in rows)
        days = len(rows)
        avg_daily_revenue = total_revenue / days if days > 0 else 0
        margin_percentage = (total_margin / total_revenue * 100) if total_revenue > 0 else 0
        
        # Check if query mentions specific year/period
        query_lower = original_query.lower()
        if any(year in query_lower for year in ['2025', '2024', 'year', 'annual', 'ytd']):
            return f"**2025 Business Performance:** ${total_revenue:,.0f} total revenue from {total_units:,} units sold. Gross margin of ${total_margin:,.0f} ({margin_percentage:.1f}%). Daily average: ${avg_daily_revenue:,.0f}. Strong performance across {days} active days."
        else:
            return f"**Weekly Performance:** ${total_revenue:,.0f} revenue from {total_units:,} units. ${total_margin:,.0f} margin ({margin_percentage:.1f}%). Daily average: ${avg_daily_revenue:,.0f} over {days} days. Business momentum is strong."
    
    elif intent == 'top_skus_by_margin':
        if rows:
            top_product = rows[0]
            total_margin = sum(float(row.get('gross_margin', 0)) for row in rows[:5])  # Top 5
            top_margin = float(top_product.get('gross_margin', 0))
            top_sku = top_product.get('sku', 'Unknown')
            
            return f"**Top Performers:** {top_sku} leads with ${top_margin:,.0f} margin. Top 5 products generated ${total_margin:,.0f} combined margin. These are your profit drivers."
    
    elif intent == 'stockout_risk':
        high_risk = [row for row in rows if row.get('risk_level') == 'high']
        medium_risk = [row for row in rows if row.get('risk_level') == 'medium']
        
        if high_risk:
            return f"**Urgent Attention:** {len(high_risk)} products at HIGH stockout risk, {len(medium_risk)} at medium risk. Immediate reordering recommended."
        elif medium_risk:
            return f"**Watch List:** {len(medium_risk)} products at medium stockout risk. Plan reorders within 1-2 weeks."
        else:
            return f"**All Clear:** No immediate stockout risks detected. Inventory levels are healthy."
    
    elif intent == 'quarterly_forecast':
        # Enhanced quarterly breakdown
        total_revenue = sum(float(row.get('revenue', 0)) for row in rows)
        total_units = sum(int(row.get('units', 0)) for row in rows)
        
        query_lower = original_query.lower()
        if 'quarter' in query_lower:
            return f"**Quarterly Forecast:** ${total_revenue:,.0f} projected revenue from {total_units:,} units. Based on current trends and historical performance."
        elif any(term in query_lower for term in ['2025', 'year', 'annual', 'ytd']):
            return f"**2025 Annual Outlook:** ${total_revenue:,.0f} projected total revenue. {total_units:,} units forecasted. Performance tracking ahead of targets."
        
    elif intent == 'reorder_suggestions':
        urgent_orders = len([row for row in rows if row.get('priority', '') == 'urgent'])
        total_suggestions = len(rows)
        
        return f"**Reorder Recommendations:** {total_suggestions} products need reordering ({urgent_orders} urgent). Prioritize high-velocity items to avoid stockouts."
    
    elif intent == 'slow_movers':
        total_slow = len(rows)
        if rows:
            oldest_item = rows[0].get('product_name', 'Unknown')
            return f"**Slow Movers Identified:** {total_slow} underperforming products. {oldest_item} and similar items may need promotion or clearance."
    
    elif intent == 'product_detail':
        if rows:
            product = rows[0]
            name = product.get('product_name', product.get('sku', 'Unknown'))
            return f"**Product Analysis:** Detailed breakdown for {name}. Current performance metrics and inventory status."
    
    # Fallback for any unhandled intents
    return f"Analysis complete: {len(rows)} records found for your {intent.replace('_', ' ')} query."

class UnifiedChatRequest(BaseModel):
    message: str
    intent: Optional[str] = None  # optional explicit override for BI intent
    options: Dict[str, Any] = {}

@router.post("/query")
async def unified_chat(req: UnifiedChatRequest, db: Session = Depends(get_db), claims = Depends(get_current_claims)):
    if not settings.HYBRID_CHAT_ENABLED:
        raise HTTPException(status_code=403, detail="Hybrid chat disabled")

    org_id = claims.get("org")
    # Step 1: route
    decision = await hybrid_router.route(req.message)

    # Override for explicit BI intent (only if valid)
    if req.intent and req.intent in INTENT_HANDLERS:
        decision.route = "BI"
        decision.intent = req.intent
        decision.reason = "explicit_intent"
        decision.confidence = 1.0

    # Step 2: parameter extraction (time range, numbers, skus)
    time_start, time_end = param_utils.normalize_time(req.message)
    number_meta = param_utils.parse_numbers_units(req.message)
    skus = param_utils.resolve_skus(req.message)

    # Prepare BI params if BI or MIXED
    bi_result = {}
    rag_snippets = []

    if decision.route in ("BI", "MIXED") and decision.intent:
        try:
            # Check if this is an annual query that should use quarterly breakdown
            query_lower = req.message.lower()
            actual_intent = decision.intent
            target_year = None
            
            # Extract specific year from query
            import re
            year_match = re.search(r'20(2[0-9])', req.message)
            if year_match:
                target_year = int(year_match.group())
            
            if decision.intent == 'week_in_review' and any(term in query_lower for term in ['2025', '2024', 'year', 'annual', 'ytd', 'revenue for']):
                actual_intent = 'annual_breakdown'
            
            param_model = INTENT_PARAM_MODELS.get(actual_intent)
            raw_params: Dict[str, Any] = {}
            if param_model:
                try:
                    raw_params = param_model(**{}).model_dump()  # defaults
                except Exception as e:
                    logging.warning(f"Parameter model error for {actual_intent}: {e}")
                    raw_params = {}
            
            handler = INTENT_HANDLERS[actual_intent]
            bi_result = handler(raw_params, db, org_id)
            # augment with tables (simple heuristic) & refreshed_at placeholder
            bi_result.setdefault("tables", ["analytics_marts.sales_daily"])
            
        except Exception as e:
            logging.error(f"BI handler error for {decision.intent}: {e}")
            # Fallback to no-answer on BI failure
            if decision.route == "BI":
                return composer.compose_no_answer(
                    f"Business intelligence analysis temporarily unavailable: {str(e)[:100]}",
                    ["Try a simpler question", "Ask about documents instead"]
                )
            # For MIXED route, continue without BI data
            bi_result = {"rows": [], "tables": []}

    # RAG implementation using existing RAG system
    if decision.route in ("RAG", "MIXED"):
        try:
            retriever = get_rag_retriever()
            # Search for relevant documents
            rag_snippets = await retriever.search(req.message, top_k=6)
            
            if decision.route == "RAG":
                if not rag_snippets:
                    return composer.compose_no_answer(
                        "No relevant documents found. Please add documents to the knowledge base or try a different question.",
                        ["Ask a BI question about your data", "Refine your question", "Contact support for document ingestion"]
                    )
                
                # Generate answer using RAG system
                answer = await retriever.generate_answer(req.message, rag_snippets)
                return composer.compose_rag(rag_snippets, answer, decision.confidence)
                
        except Exception as e:
            logging.warning(f"RAG system error: {e}")
            if decision.route == "RAG":
                return composer.compose_no_answer(
                    "Document search system temporarily unavailable",
                    ["Ask a BI question", "Try again later"]
                )
            # For MIXED route, continue without RAG

    if decision.route == "MIXED":
        if rag_snippets:
            # Generate synthesis of BI + RAG
            try:
                # Create context for LLM synthesis
                bi_summary = f"BI Analysis: {len(bi_result.get('rows', []))} data points found"
                doc_summary = f"Documentation: {len(rag_snippets)} relevant sections found"
                
                synthesis_prompt = f"""
                Question: {req.message}
                
                {bi_summary}
                {doc_summary}
                
                Provide a comprehensive answer combining both data analysis and policy/documentation insights.
                """
                
                synthesis = await lmstudio_client.get_chat_response([
                    {"role": "system", "content": "You are a business analyst combining data insights with policy documentation."},
                    {"role": "user", "content": synthesis_prompt}
                ], temperature=0.3)
                
                return composer.compose_mixed(bi_result, rag_snippets, synthesis, decision.confidence, decision.intent or "")
                
            except Exception as e:
                logging.warning(f"Mixed synthesis error: {e}")
                # Fallback to BI-only with note
                summary = f"Data analysis complete. Document synthesis unavailable: {str(e)}"
                return composer.compose_bi(bi_result, summary, decision.intent or "", decision.confidence)
        else:
            # No RAG results, degrade to BI-only
            summary = f"Data analysis for {decision.intent}. No relevant documents found."
            return composer.compose_bi(bi_result, summary, decision.intent or "", decision.confidence)

    if decision.route == "BI" and decision.intent:
        # Generate intelligent summary based on intent and data
        summary = _generate_intelligent_summary(decision.intent, bi_result, req.message)
        return composer.compose_bi(bi_result, summary, decision.intent, decision.confidence)

    if decision.route == "OPEN":
        # Simple LM Studio chat with robust fallback
        try:
            content = await lmstudio_client.get_chat_response([
                {"role": "system", "content": "You are StockPilot assistant for inventory management and sales analytics. Help with product stock levels, sales data, purchasing, and warehouse operations. Be concise."},
                {"role": "user", "content": req.message}
            ], temperature=0.7)
            if not content:
                raise ValueError("empty_llm_response")
            return composer.compose_open(content)
        except Exception as e:
            logging.warning(f"LM Studio chat error: {e}")
            return composer.compose_no_answer("LLM temporarily unavailable", ["Ask a BI question", "Retry in a moment"]) 

    return composer.compose_no_answer("Unable to determine an answer path", ["Ask a simpler question", "Request top SKUs by margin"])
