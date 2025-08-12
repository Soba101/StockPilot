from __future__ import annotations
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.schemas.chat import IntentResolution, IntentName
import json

SYSTEM_PROMPT = """You are a strict intent mapper for an inventory & sales analytics system. Allowed intents: top_skus_by_margin, stockout_risk, week_in_review, reorder_suggestions. Output MUST be valid JSON with keys: intent (string or null), params (object), confidence (0-1 float), reasons (array). If user asks something outside allowed intents, set intent=null and give short reason. Don't invent parameters. Map 'last week' to period=7d, 'last month' to period=30d. horizon_days must be one of 7,14,30."""

USER_SCHEMA_EXAMPLE = {"intent": "top_skus_by_margin", "params": {"period": "7d", "n": 10}, "confidence": 0.9, "reasons": ["keywords: top, margin"]}

class LLMIntentResolver:
    def __init__(self):
        self.base_url = settings.LLM_BASE_URL.rstrip('/')
        self.model = settings.LLM_MODEL_ID
        self.timeout = settings.LLM_TIMEOUT_SECONDS
        self.api_key = settings.OPENAI_API_KEY or "sk-no-key"  # some servers require a token header

    async def resolve(self, prompt: str) -> IntentResolution:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers={"Authorization": f"Bearer {self.api_key}"})
                resp.raise_for_status()
                data = resp.json()
                content = data['choices'][0]['message']['content']
                parsed = json.loads(content)
                intent = parsed.get('intent')
                if intent is None:
                    return IntentResolution(intent=None, params={}, confidence=float(parsed.get('confidence',0)), source='llm', reasons=parsed.get('reasons',[]))
                if intent not in ['top_skus_by_margin','stockout_risk','week_in_review','reorder_suggestions']:
                    return IntentResolution(intent=None, params={}, confidence=0.0, source='llm', reasons=['invalid intent'])
                return IntentResolution(intent=intent, params=parsed.get('params',{}), confidence=float(parsed.get('confidence',0)), source='llm', reasons=parsed.get('reasons',[]))
        except Exception as e:
            return IntentResolution(intent=None, params={}, confidence=0.0, source='llm', reasons=[f"llm_error: {e}"])

    async def general_chat(self, prompt: str, business_context: str = "") -> str:
        """Handle general conversational queries with full business context."""
        system_prompt = f"""You are an intelligent business assistant for StockPilot, an inventory management system. 
        You have full knowledge of the business data and should respond as someone who understands the company intimately.

{business_context}

Instructions:
- When answering questions, use the business context above to provide relevant, data-driven responses
- For general questions, feel free to be conversational but maintain business awareness
- You can make recommendations based on the data you see
- If someone asks about specific metrics, refer to the actual numbers from the context
- Be helpful, insightful, and demonstrate your understanding of the business
- When appropriate, proactively mention relevant insights from the data
- For jokes or casual conversation, you can incorporate business themes/context

Available specific analytics you can suggest:
- "show me top products by margin" - detailed product performance
- "stockout risk analysis" - inventory risk assessment  
- "week in review" - detailed daily performance
- "reorder suggestions" - purchase recommendations"""
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers={"Authorization": f"Bearer {self.api_key}"})
                resp.raise_for_status()
                data = resp.json()
                return data['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"I'm sorry, I encountered an error processing your request: {str(e)}"

llm_intent_resolver = LLMIntentResolver()
