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
    route: str  # RAG | OPEN | NO_ANSWER
    intent: str | None
    confidence: float
    reason: str

DOC_KEYWORDS = ["policy", "return", "returns", "markdown", "sop", "procedure", "guide", "documentation", "manual", "rule", "rules", "process"]

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


async def _llm_tiebreaker(prompt: str, scores: Dict[str, float]) -> RouteDecision:
    """Use LLM to make final routing decision when rules + embeddings are unclear."""
    if not settings.HYBRID_ROUTER_LLM_TIEBREAKER_ENABLED:
        return RouteDecision(route="OPEN", intent=None, confidence=0.3, reason="llm_tiebreaker_disabled")
    
    try:
        # Build context for LLM
        context = f"Query: {prompt}\n"
        if scores:
            context += f"Similarity scores: {scores}\n"
        
        system_prompt = (
            "You are a strict router. Output only valid JSON.\n"
            "Pick route: \"RAG\" (documents/policies) or \"OPEN\".\n"
            "Return {\"route\":\"...\",\"intent\":null,\"reason\":\"...\"}."
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
            if route not in ["RAG", "OPEN"]:
                route = "OPEN"
            
            # RAG route doesn't need intent validation anymore
            return RouteDecision(route=route, intent=None, confidence=0.65, reason=f"llm_{reason}")
            
        except json.JSONDecodeError:
            return RouteDecision(route="OPEN", intent=None, confidence=0.3, reason="llm_parse_error")
    
    except Exception as e:
        print(f"Warning: LLM tiebreaker failed: {e}")
        return RouteDecision(route="OPEN", intent=None, confidence=0.3, reason="llm_error")


# Removed BI-related functions: _is_business_query, _best_bi_intent

async def route(prompt: str) -> RouteDecision:
    """Route to either RAG (documents) or OPEN (general assistant)."""
    # Rule-based scoring for documents
    doc_score = _rule_score(prompt, DOC_KEYWORDS)
    
    # Embedding-based scoring (if enabled)
    embedding_scores = await _compute_embedding_scores(prompt)
    
    # Combine scores
    rule_doc_score = doc_score
    embedding_doc_score = embedding_scores.get("doc_qna", 0.0)
    rag_confidence = 0.6 * rule_doc_score + 0.4 * embedding_doc_score
    
    open_embedding = embedding_scores.get("open_chat", 0.0)
    open_confidence = 0.4 * open_embedding
    
    # Decision logic: prefer RAG if document keywords are detected
    if rag_confidence >= 0.25:
        return RouteDecision(route="RAG", intent=None, confidence=rag_confidence, reason="high_conf_rag")
    elif open_confidence >= 0.2:
        return RouteDecision(route="OPEN", intent=None, confidence=open_confidence, reason="high_conf_open")
    else:
        # Default to OPEN for general assistant chat
        return RouteDecision(route="OPEN", intent=None, confidence=0.3, reason="open_fallback")
