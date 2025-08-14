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
from app.tools.database_tools import DatabaseTools, get_database_tools_schema
import asyncio
import json

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

    # Only support RAG and OPEN routes
    if decision.route == "RAG":
        try:
            retriever = get_rag_retriever()
            rag_snippets = await retriever.search(req.message, top_k=6)
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
    if decision.route == "OPEN":
        try:
            # Initialize database tools for this user's org
            db_tools = DatabaseTools(db, org_id)
            
            # Prepare function-calling system prompt
            system_prompt = f"""You are StockPilot assistant for inventory management and sales analytics. 
You have access to real-time database information. When users ask about data, provide accurate information.

Available data you can access:
- Total sales, revenue, and order counts
- Top performing products by revenue
- Current inventory levels and low stock alerts
- Products needing reorder

Answer directly with current data. Don't use function calling syntax - I'll get the data for you automatically."""

            # Check if the user is asking for specific data and get it
            data_context = ""
            year_match = None
            
            # Extract year from query if present
            import re
            year_pattern = r'\b(20\d{2})\b'
            year_matches = re.findall(year_pattern, req.message)
            if year_matches:
                year_match = year_matches[0]
            
            # Determine what data to fetch based on the question
            needs_sales_data = any(word in req.message.lower() for word in ['sales', 'revenue', 'total'])
            needs_top_products = any(word in req.message.lower() for word in ['top', 'best', 'performing', 'products'])
            needs_inventory = any(word in req.message.lower() for word in ['inventory', 'stock', 'levels'])
            needs_reorder = any(word in req.message.lower() for word in ['reorder', 'repurchasing', 'need'])
            
            # Fetch the requested data
            if needs_sales_data:
                if year_match:
                    start_date = f"{year_match}-01-01"
                    end_date = f"{year_match}-12-31"
                    sales_data = db_tools.get_total_sales(start_date, end_date)
                    data_context += f"\n{year_match} Sales Data: {json.dumps(sales_data, indent=2)}"
                else:
                    sales_data = db_tools.get_total_sales()
                    data_context += f"\nTotal Sales Data: {json.dumps(sales_data, indent=2)}"
            
            if needs_top_products:
                top_products = db_tools.get_top_products_by_revenue(limit=5)
                data_context += f"\nTop Products: {json.dumps(top_products, indent=2)}"
            
            if needs_inventory:
                inventory_data = db_tools.get_current_inventory_levels()
                data_context += f"\nInventory Levels: {json.dumps(inventory_data, indent=2)}"
            
            if needs_reorder:
                reorder_data = db_tools.get_products_needing_reorder()
                data_context += f"\nReorder Suggestions: {json.dumps(reorder_data, indent=2)}"
            
            # Create the enhanced prompt with actual data
            if data_context:
                enhanced_prompt = f"""Question: {req.message}

Current data from your database:{data_context}

Provide a clear, helpful answer based on this real data. Be specific with numbers and insights."""
            else:
                enhanced_prompt = req.message
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": enhanced_prompt}
            ]
            
            response = await lmstudio_client.get_chat_response(messages, temperature=0.3)
            
            if not response:
                raise ValueError("empty_llm_response")
            
            return composer.compose_open(response)
            
        except Exception as e:
            logging.warning(f"LM Studio chat error: {e}")
            return composer.compose_no_answer("Assistant temporarily unavailable", ["Retry in a moment"])
    return composer.compose_no_answer("Unable to determine an answer path", ["Ask a simpler question"])
