"""Smart hybrid router (rules + embeddings + LLM tiebreaker).
Enhanced version with semantic similarity scoring.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from app.services.intent_rules import INTENT_KEYWORDS, BUSINESS_QUERY_INDICATORS
from app.core.config import settings
from app.core.llm_lmstudio import lmstudio_client
from dataclasses import dataclass
import math
import asyncio
import os
from pathlib import Path

@dataclass
class RouteDecision:
    route: str  # BI | RAG | MIXED | OPEN | NO_ANSWER
    intent: str | None
    confidence: float
    reason: str

BI_INTENTS = list(INTENT_KEYWORDS.keys())

DOC_KEYWORDS = ["policy", "return", "returns", "markdown", "sop", "procedure", "guide", "documentation", "manual", "rule", "rules", "process"]

MIXED_HINTS = ["forecast", "if I", "and confirm", "policy", "impact", "effect"]

OPEN_FALLBACK_THRESHOLD = 0.1

# Embedding cache to avoid recomputing embeddings for exemplars
_embeddings_cache = {}
_embedder = None


def _rule_score(prompt: str, words: list[str]) -> float:
    pl = prompt.lower()
    hits = sum(1 for w in words if w in pl)
    if not words:
        return 0.0
    return hits / len(words)


async def _get_embedder():
    """Get sentence transformer embedder (lazy loading)."""
    global _embedder
    if _embedder is None and settings.HYBRID_ROUTER_EMBEDDINGS_ENABLED:
        try:
            from sentence_transformers import SentenceTransformer
            embeddings_model = os.getenv("EMBEDDINGS_MODEL", "BAAI/bge-small-en-v1.5")
            _embedder = SentenceTransformer(embeddings_model)
        except ImportError:
            print("Warning: sentence-transformers not installed. Embeddings routing disabled.")
    return _embedder


async def _load_exemplars() -> Dict[str, List[str]]:
    """Load exemplar phrases from files."""
    exemplars = {}
    exemplars_dir = Path(__file__).parent / "exemplars"
    
    if not exemplars_dir.exists():
        return exemplars
    
    # BI exemplars
    bi_dir = exemplars_dir / "bi"
    if bi_dir.exists():
        for intent in BI_INTENTS:
            file_path = bi_dir / f"{intent}.txt"
            if file_path.exists():
                try:
                    exemplars[f"bi_{intent}"] = file_path.read_text().strip().split('\n')
                except Exception:
                    pass
    
    # Document QnA exemplars
    doc_file = exemplars_dir / "doc_qna.txt"
    if doc_file.exists():
        try:
            exemplars["doc_qna"] = doc_file.read_text().strip().split('\n')
        except Exception:
            pass
    
    # Open chat exemplars
    open_file = exemplars_dir / "open_chat.txt"
    if open_file.exists():
        try:
            exemplars["open_chat"] = open_file.read_text().strip().split('\n')
        except Exception:
            pass
    
    return exemplars


async def _compute_embedding_scores(prompt: str) -> Dict[str, float]:
    """Compute semantic similarity scores against exemplars."""
    if not settings.HYBRID_ROUTER_EMBEDDINGS_ENABLED:
        return {}
    
    embedder = await _get_embedder()
    if embedder is None:
        return {}
    
    try:
        exemplars = await _load_exemplars()
        if not exemplars:
            return {}
        
        # Generate embedding for prompt
        prompt_embedding = embedder.encode([prompt], normalize_embeddings=True)[0]
        
        scores = {}
        
        for category, phrases in exemplars.items():
            if not phrases:
                continue
            
            # Get or compute exemplar embeddings
            cache_key = f"{category}_{hash(tuple(phrases))}"
            if cache_key not in _embeddings_cache:
                exemplar_embeddings = embedder.encode(phrases, normalize_embeddings=True)
                _embeddings_cache[cache_key] = exemplar_embeddings
            else:
                exemplar_embeddings = _embeddings_cache[cache_key]
            
            # Compute cosine similarities
            similarities = []
            for exemplar_emb in exemplar_embeddings:
                similarity = float(prompt_embedding @ exemplar_emb)  # Cosine similarity (normalized vectors)
                similarities.append(similarity)
            
            # Take max similarity as category score
            scores[category] = max(similarities) if similarities else 0.0
        
        return scores
    
    except Exception as e:
        print(f"Warning: Embedding scoring failed: {e}")
        return {}


async def _llm_tiebreaker(prompt: str, bi_intent: Optional[str], scores: Dict[str, float]) -> RouteDecision:
    """Use LLM to make final routing decision when rules + embeddings are unclear."""
    if not settings.HYBRID_ROUTER_LLM_TIEBREAKER_ENABLED:
        return RouteDecision(route="OPEN", intent=None, confidence=0.3, reason="llm_tiebreaker_disabled")
    
    try:
        # Build context for LLM
        context = f"Query: {prompt}\n"
        if bi_intent:
            context += f"Possible BI intent: {bi_intent}\n"
        if scores:
            context += f"Similarity scores: {scores}\n"
        
        system_prompt = (
            "You are a strict router. Output only valid JSON.\n"
            "Pick route: \"BI\" (database analytics), \"RAG\" (documents/policies), \"MIXED\" (both), or \"OPEN\".\n"
            "If BI, include one intent from: [\"top_skus_by_margin\", \"stockout_risk\", \"week_in_review\", \"reorder_suggestions\", \"slow_movers\", \"product_detail\", \"quarterly_forecast\"].\n"
            "Return {\"route\":\"...\",\"intent\":null|\"...\",\"reason\":\"...\"}."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        
        response = await lmstudio_client.get_chat_response(messages, temperature=0.1, max_tokens=100)
        
        # Parse JSON response
        import json
        try:
            data = json.loads(response.strip())
            route = data.get("route", "OPEN")
            intent = data.get("intent")
            reason = data.get("reason", "llm_decision")
            
            # Validate route
            if route not in ["BI", "RAG", "MIXED", "OPEN"]:
                route = "OPEN"
            
            # Validate intent if BI route
            if route == "BI" and intent not in BI_INTENTS:
                intent = bi_intent  # Fall back to rule-based intent
            
            return RouteDecision(route=route, intent=intent, confidence=0.65, reason=f"llm_{reason}")
            
        except json.JSONDecodeError:
            return RouteDecision(route="OPEN", intent=None, confidence=0.3, reason="llm_parse_error")
    
    except Exception as e:
        print(f"Warning: LLM tiebreaker failed: {e}")
        return RouteDecision(route="OPEN", intent=None, confidence=0.3, reason="llm_error")


def _is_business_query(prompt: str) -> bool:
    """Check if query contains business indicators that should trigger BI analysis."""
    pl = prompt.lower()
    return any(indicator in pl for indicator in BUSINESS_QUERY_INDICATORS)

def _best_bi_intent(prompt: str):
    pl = prompt.lower()
    best = None
    best_hits = 0
    for intent, kws in INTENT_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in pl)
        if hits > best_hits:
            best_hits = hits
            best = intent
    
    # If no specific intent but it's a business query, default to week_in_review
    if not best and _is_business_query(prompt):
        best = 'week_in_review'
        best_hits = 1
    
    if not best:
        return None, 0.0
    confidence = min(1.0, 0.4 + 0.05 * best_hits)
    
    # Boost confidence for business queries to ensure BI routing
    if _is_business_query(prompt):
        confidence = max(confidence, 0.6)
    
    return best, confidence

async def route(prompt: str) -> RouteDecision:
    # Step 1: Rule-based scoring
    bi_intent, bi_conf = _best_bi_intent(prompt)
    doc_score = _rule_score(prompt, DOC_KEYWORDS)
    mixed_hint = any(h in prompt.lower() for h in MIXED_HINTS)
    
    # Step 2: Embedding-based scoring (if enabled)
    embedding_scores = await _compute_embedding_scores(prompt)
    
    # Step 3: Combine scores (0.6 rules + 0.4 embeddings as per plan)
    combined_scores = {}
    
    # BI intent scoring
    if bi_intent:
        rule_score = bi_conf
        embedding_score = embedding_scores.get(f"bi_{bi_intent}", 0.0)
        combined_scores["bi"] = 0.6 * rule_score + 0.4 * embedding_score
    else:
        combined_scores["bi"] = 0.0
    
    # RAG/Doc scoring  
    rule_doc_score = doc_score
    embedding_doc_score = embedding_scores.get("doc_qna", 0.0)
    combined_scores["rag"] = 0.6 * rule_doc_score + 0.4 * embedding_doc_score
    
    # Open chat scoring
    open_embedding = embedding_scores.get("open_chat", 0.0)
    combined_scores["open"] = 0.4 * open_embedding  # Only embedding-based for open
    
    # Step 4: Decision logic based on thresholds from plan
    max_score = max(combined_scores.values()) if combined_scores else 0.0
    
    # High confidence threshold (≥0.25): Direct route selection  
    if max_score >= 0.25:
        if combined_scores.get("bi", 0) == max_score and bi_intent:
            if mixed_hint or combined_scores.get("rag", 0) >= 0.2:
                return RouteDecision(route="MIXED", intent=bi_intent, confidence=max_score, reason="high_conf_mixed")
            return RouteDecision(route="BI", intent=bi_intent, confidence=max_score, reason="high_conf_bi")
        elif combined_scores.get("rag", 0) == max_score:
            return RouteDecision(route="RAG", intent=None, confidence=max_score, reason="high_conf_rag")
        elif combined_scores.get("open", 0) == max_score:
            return RouteDecision(route="OPEN", intent=None, confidence=max_score, reason="high_conf_open")
    
    # Medium confidence threshold (0.2-0.3): LLM tiebreaker
    elif max_score >= 0.2:
        if settings.HYBRID_ROUTER_LLM_TIEBREAKER_ENABLED:
            return await _llm_tiebreaker(prompt, bi_intent, embedding_scores)
        else:
            # Fallback to rule-based when LLM disabled
            if combined_scores.get("bi", 0) == max_score and bi_intent:
                return RouteDecision(route="BI", intent=bi_intent, confidence=max_score, reason="medium_conf_bi_fallback")
            elif combined_scores.get("rag", 0) == max_score:
                return RouteDecision(route="RAG", intent=None, confidence=max_score, reason="medium_conf_rag_fallback")
            else:
                return RouteDecision(route="OPEN", intent=None, confidence=max_score, reason="medium_conf_open_fallback")
    
    # Low confidence: Check if it's a business query that should go to BI
    else:
        if _is_business_query(prompt):
            # Business queries should always get BI analytics, not general chat
            fallback_intent = "week_in_review"  # Default intent for general business questions
            return RouteDecision(route="BI", intent=fallback_intent, confidence=0.4, reason="business_query_fallback")
        else:
            # For non-business queries, use OPEN route as general chat fallback
            return RouteDecision(route="OPEN", intent=None, confidence=0.2, reason="open_fallback")
    
    # This should never be reached, but added for type safety
    return RouteDecision(route="NO_ANSWER", intent=None, confidence=0.0, reason="fallback")
