"""Answer composer to normalize outputs into unified contract."""
from __future__ import annotations
from typing import List, Dict, Any
from .contracts import validate_output

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


def compose_open(answer: str, follow_ups: List[str] | None = None) -> Dict[str, Any]:
    payload = _base()
    payload.update({
        "route": "OPEN",
        "answer": answer,
    "confidence": 0.6,
    "follow_ups": follow_ups if follow_ups is not None else ["Ask about inventory", "How can I help?"]
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


def compose_bi(answer: str, confidence: float, metrics: Dict[str, Any] | None = None, tables: List[str] | None = None) -> Dict[str, Any]:
    payload = _base()
    payload.update({
        "route": "BI",
        "answer": answer,
        "cards": ([{"type": "metrics", "data": metrics}] if metrics else []),
        "provenance": {"data": {"tables": tables or []}, "docs": []},
        "confidence": round(confidence, 3),
        "follow_ups": ["Open Analytics → Sales overview", "Download Week-in-Review PDF"]
    })
    validate_output(payload)
    return payload
