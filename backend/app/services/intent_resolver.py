from __future__ import annotations
from typing import Dict, Any
from app.schemas.chat import IntentResolution
from app.services.intent_rules import resolve_intent_rules
from app.services.llm_client import llm_intent_resolver
from app.core.config import settings
import asyncio

LOW_CONFIDENCE_THRESHOLD = 0.55

async def resolve_intent(prompt: str) -> IntentResolution:
    rule_res = resolve_intent_rules(prompt)
    if not settings.CHAT_LLM_FALLBACK_ENABLED:
        return rule_res
    if rule_res.confidence >= LOW_CONFIDENCE_THRESHOLD:
        return rule_res
    # fallback to LLM
    llm_res = await llm_intent_resolver.resolve(prompt)
    # choose better resolution (higher confidence)
    if (llm_res.intent and llm_res.confidence > rule_res.confidence) or (not rule_res.intent and llm_res.intent):
        return llm_res
    return rule_res
