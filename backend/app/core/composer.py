"""Answer composer to normalize outputs into unified contract."""
from __future__ import annotations
from typing import List, Dict, Any
from .contracts import validate_output
import uuid
from datetime import datetime, timezone

ISO = lambda dt: dt.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

FOLLOW_UP_SUGGESTIONS = {
    'top_skus_by_margin': ["Show stockout risks", "Any slow movers?"],
    'stockout_risk': ["Which need reorder?", "Top margin SKUs"],
}

def _base() -> Dict[str, Any]:
    return {
        "route": "NO_ANSWER",
        "answer": "",
        "cards": [],
        "provenance": {"data": {"tables": []}, "docs": []},
        "confidence": 0.0,
        "follow_ups": []
    }


def compose_rag(snippets: List[Dict[str, Any]], answer: str, confidence: float) -> Dict[str, Any]:
    payload = _base()
    if not snippets:
        return compose_no_answer("No supporting documents found", ["Try rephrasing", "Ask a general question"])
    payload.update({
        "route": "RAG",
        "answer": answer,
        "cards": [{"type": "citations", "data": snippets[:10]}],
        "provenance": {"data": {"tables": []}, "docs": snippets},
        "confidence": round(confidence, 3),
        "follow_ups": ["Ask another question", "Refine the policy question"]
    })
    validate_output(payload)
    return payload


def compose_open(answer: str) -> Dict[str, Any]:
    payload = _base()
    payload.update({
        "route": "OPEN",
        "answer": answer,
        "confidence": 0.6,
        "follow_ups": ["Ask about inventory", "How can I help?"]
    })
    validate_output(payload)
    return payload


def compose_no_answer(reason: str, follow_ups: List[str]) -> Dict[str, Any]:
    payload = _base()
    payload.update({
        "route": "NO_ANSWER",
        "answer": reason,
        "confidence": 0.0,
        "follow_ups": follow_ups
    })
    validate_output(payload)
    return payload
