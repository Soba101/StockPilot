"""JSON schema contracts for unified hybrid chat responses (Phase 1)."""
from jsonschema import Draft7Validator, ValidationError

UNIFIED_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
    "route": {"type": "string", "enum": ["RAG", "OPEN", "BI", "NO_ANSWER"]},
        "answer": {"type": "string"},
        "cards": {"type": "array", "items": {"type": "object"}},
        "provenance": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "properties": {
                        "tables": {"type": "array", "items": {"type": "string"}},
                        "query_id": {"type": "string"},
                        "refreshed_at": {"type": "string"}
                    },
                    "required": ["tables"]
                },
                "docs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "quote": {"type": "string"}
                        },
                        "required": ["title", "url"]
                    }
                }
            }
        },
        "confidence": {"type": "number"},
        "follow_ups": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["route", "answer", "provenance", "confidence", "follow_ups"]
}

RAG_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 6},
        "filters": {"type": "object"}
    },
    "required": ["question"]
}

_unified_validator = Draft7Validator(UNIFIED_RESPONSE_SCHEMA)

class SchemaValidationError(Exception):
    pass

def validate_output(payload):
    errors = sorted(_unified_validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        messages = [f"{'/'.join([str(p) for p in e.path])}: {e.message}" for e in errors]
        raise SchemaValidationError("; ".join(messages))
    return True
