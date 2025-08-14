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


def compose_bi(result: Dict[str, Any], summary: str, intent: str, confidence: float) -> Dict[str, Any]:
    payload = _base()
    payload.update({
        "route": "BI",
        "answer": summary,
        "cards": [{"type": "table", "data": result.get("rows", [])[:20]}],
        "provenance": {"data": {"tables": result.get("tables", ["analytics_marts.sales_daily"]), "query_id": f"q_{uuid.uuid4().hex[:8]}", "refreshed_at": result.get("refreshed_at") or ISO(datetime.now(timezone.utc))}, "docs": []},
        "confidence": round(confidence, 3),
        "follow_ups": FOLLOW_UP_SUGGESTIONS.get(intent, [])
    })
    validate_output(payload)
    return payload


def compose_rag(snippets: List[Dict[str, Any]], answer: str, confidence: float) -> Dict[str, Any]:
    payload = _base()
    if not snippets:
        return compose_no_answer("No supporting documents found", ["Try rephrasing", "Ask a BI question like top margin SKUs"])
    payload.update({
        "route": "RAG",
        "answer": answer,
        "cards": [{"type": "citations", "data": snippets[:10]}],
        "provenance": {"data": {"tables": []}, "docs": snippets},
        "confidence": round(confidence, 3),
        "follow_ups": ["Ask for BI metrics", "Refine the policy question"]
    })
    validate_output(payload)
    return payload


def compose_mixed(bi_result: Dict[str, Any], rag_snippets: List[Dict[str, Any]], synthesis: str, confidence: float, intent: str) -> Dict[str, Any]:
    if not bi_result.get('rows') and not rag_snippets:
        return compose_no_answer("Neither data nor docs available", ["Load documents", "Add sales data"])
    payload = _base()
    payload.update({
        "route": "MIXED",
        "answer": synthesis,
        "cards": [
            {"type": "table", "data": bi_result.get('rows', [])[:15]},
            {"type": "citations", "data": rag_snippets[:8]}
        ],
        "provenance": {"data": {"tables": bi_result.get("tables", []) or ["analytics_marts.sales_daily"], "query_id": f"q_{uuid.uuid4().hex[:8]}", "refreshed_at": bi_result.get("refreshed_at") or ISO(datetime.now(timezone.utc))}, "docs": rag_snippets},
        "confidence": round(confidence, 3),
        "follow_ups": FOLLOW_UP_SUGGESTIONS.get(intent, []) + ["Deep dive policy detail"]
    })
    validate_output(payload)
    return payload


def compose_open(answer: str) -> Dict[str, Any]:
    payload = _base()
    payload.update({
        "route": "OPEN",
        "answer": answer,
        "confidence": 0.6,
        "follow_ups": ["Ask for top margin SKUs", "Check stockout risk"]
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
