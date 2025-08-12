from __future__ import annotations
import httpx
from typing import Dict, Any, Optional, List
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

    def _build_endpoint_matrix(self, mode: str) -> List[str]:
        """Construct prioritized list of endpoint URLs for a given mode ('chat' or 'completions').

        We purposely DO NOT mix payload types with mismatched endpoints (previously caused 'prompt field required')."""
        base = self.base_url.rstrip('/')
        roots = [base]
        if not base.endswith('/v1'):
            roots.append(base + '/v1')
        else:
            roots.append(base[:-3])  # allow unversioned fallback
        # Deduplicate roots
        cleaned: List[str] = []
        seen_r = set()
        for r in roots:
            r2 = r.rstrip('/')
            if r2 not in seen_r:
                seen_r.add(r2)
                cleaned.append(r2)
        endpoints: List[str] = []
        for r in cleaned:
            has_v1 = r.endswith('/v1')
            base_no_v1 = r[:-3] if has_v1 else r
            vroot = r if has_v1 else base_no_v1 + '/v1'
            if mode == 'chat':
                endpoints.append(vroot + '/chat/completions')
                if not has_v1:
                    endpoints.append(base_no_v1 + '/chat/completions')
            else:  # completions
                endpoints.append(vroot + '/completions')
                if not has_v1:
                    endpoints.append(base_no_v1 + '/completions')
        # Dedupe preserve order
        dedup: List[str] = []
        seen = set()
        for e in endpoints:
            if e not in seen:
                seen.add(e)
                dedup.append(e)
        return dedup

    def _parse_chat_or_completion(self, data: Dict[str, Any]) -> Optional[str]:
        try:
            return data['choices'][0]['message']['content']
        except Exception:
            try:
                return data['choices'][0].get('text')
            except Exception:
                return None

    async def _post_with_fallback(self, payload: Dict[str, Any], mode: str = 'chat') -> str:
        endpoints = self._build_endpoint_matrix(mode)
        last_error: Any = None
        effective_timeout = self.timeout if self.timeout and self.timeout >= 10 else 30
        async with httpx.AsyncClient(timeout=effective_timeout) as client:
            for url in endpoints:
                try:
                    resp = await client.post(url, json=payload, headers={"Authorization": f"Bearer {self.api_key}"})
                    text_body = resp.text
                    try:
                        data = resp.json()
                    except Exception:
                        if 'Unexpected endpoint' in text_body:
                            last_error = f"warning:{text_body[:120]}"; continue
                        if text_body.strip():
                            return text_body.strip()
                        last_error = 'empty-nonjson'; continue
                    if 'Unexpected endpoint' in str(data):
                        last_error = 'unexpected-endpoint'; continue
                    content = self._parse_chat_or_completion(data)
                    if content:
                        return content
                    last_error = 'no-content'
                except Exception as e:
                    last_error = e
                    continue
        raise RuntimeError(f"All LLM endpoints failed: {last_error}")

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
            content = await self._post_with_fallback(payload, mode='chat')
            # Detect placeholder / template artifacts and fallback to classic completion
            if not content or content.strip() in {"<|assistant|>", "<|channel|>", "<|assistant|"} or content.strip().startswith('<|'):
                comp_prompt = []
                for m in payload['messages']:
                    role = m['role']
                    comp_prompt.append(f"{role.upper()}: {m['content']}")
                comp_payload = {"model": self.model, "prompt": "\n".join(comp_prompt) + "\nASSISTANT:", "max_tokens": 400, "temperature": payload.get('temperature',0)}
                try:
                    content = await self._post_with_fallback(comp_payload, mode='completions')
                except Exception:
                    pass
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

BUSINESS CONTEXT (snapshot):
{business_context}

Instructions:
- Use the business context above to ground answers in actual numbers when referenced.
- If a user asks who or what you are, state you are an AI assistant running model '{self.model}' accessed locally via an OpenAI-compatible API.
- Be concise, insightful, and proactively surface one relevant metric when helpful.
- Offer specific analytic intents if they would answer the question better (top_skus_by_margin, stockout_risk, week_in_review, reorder_suggestions).
- If data required isn't in context, be transparent and say what additional data is needed.
- Avoid hallucinating metrics not present; prefer ranges or 'unknown'.
"""

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
            content = await self._post_with_fallback(payload, mode='chat')
            if not content or content.strip() in {"<|assistant|>", "<|channel|>", "<|assistant|"} or content.strip().startswith('<|'):
                # Classic completion fallback
                comp_prompt = []
                for m in payload['messages']:
                    comp_prompt.append(f"{m['role'].upper()}: {m['content']}")
                comp_payload = {"model": self.model, "prompt": "\n".join(comp_prompt) + "\nASSISTANT:", "max_tokens": 500, "temperature": payload.get('temperature',0.7)}
                try:
                    content = await self._post_with_fallback(comp_payload, mode='completions')
                except Exception:
                    pass
            return content.strip()
        except Exception as e:
            return f"I'm sorry, I encountered an error contacting the model endpoints: {e}"

llm_intent_resolver = LLMIntentResolver()
