# Hybrid Chat System Implementation Plan

## Overview

This document outlines the implementation plan for creating a unified chat system that intelligently routes queries to BI (database), RAG (in-process documents), MIXED (both), or OPEN chat modes using only LM Studio for all LLM operations.

## Architecture

```
LM Studio (localhost:1234) → Unified Backend App
├─ Smart Router (rules + embeddings + LM Studio tiebreaker)
├─ Parameter Extractor (SGT time, SKU aliases, units)
├─ BI Tool (existing SQL + enhanced provenance)
├─ RAG Tool (in-process: Chroma/pgvector + hybrid retrieval)
└─ Answer Composer (unified JSON schema)
```

## Environment Configuration

```bash
# LM Studio Configuration
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
LMSTUDIO_CHAT_MODEL=openai/gpt-oss-20b
LMSTUDIO_EMBED_MODEL=text-embedding-minilm  # Use a dedicated embedding model for retrieval/routing
LMSTUDIO_TIMEOUT=120

# Application Configuration
DB_DSN=postgresql+psycopg://user:pass@localhost:5432/stockpilot
APP_TZ=Asia/Singapore
FISCAL_CALENDAR_START_MONTH=4           # e.g., 4 = April fiscal year start; adjust as needed

# RAG Configuration
RAG_STORE=chroma                    # "chroma" or "pgvector"
RAG_PERSIST_DIR=./chroma_store      # if chroma (Chroma uses a persist directory, not a DB URL)
# RAG_PG_DSN=postgresql://...       # if pgvector
```

## Implementation Steps

### 1. LM Studio Client (`backend/app/core/llm_lmstudio.py`)

**Purpose**: Single provider for all LLM operations, replacing OpenAI dependencies.

**Key Methods**:
- `chat(messages, temperature, max_tokens, **kwargs)` → dict
- `embed(texts)` → list[list[float]]
- `get_chat_response(messages, **kwargs)` → str
- `health_check()` → dict

**Features**:
- Connects to LM Studio's OpenAI-compatible endpoints
- Handles `/chat/completions` and `/embeddings`
- Comprehensive error handling and timeout management
- Health check for both chat and embeddings endpoints

### 2. JSON Contracts (`backend/app/core/contracts.py`)

**Purpose**: Define and validate all input/output schemas.

**Key Schemas**:
```python
from jsonschema import Draft7Validator

UNIFIED_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "route": {"type": "string", "enum": ["BI", "RAG", "MIXED", "OPEN", "NO_ANSWER"]},
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

BI_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": ["top_skus_by_margin","stockout_risk","week_in_review","reorder_suggestions","slow_movers","product_detail","quarterly_forecast"]},
        "time_start": {"type": "string", "format": "date-time"},
        "time_end": {"type": "string", "format": "date-time"},
        "skus": {"type": "array", "items": {"type": "string"}},
        "options": {"type": "object"}
    },
    "required": ["intent", "time_start", "time_end"]
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
```

**Functions**:
- `validate_output(payload)` using jsonschema
- Schema constants for all tool inputs/outputs

### 3. Parameter Extractor (`backend/app/core/params.py`)

**Purpose**: Parse natural language into structured parameters with Singapore timezone.

**Key Functions**:
- `normalize_time(nl_text, tz="Asia/Singapore")` → (start_iso, end_iso)
- `parse_numbers_units(nl_text)` → {"percent": 0.2, "qty": 300, ...}
- `resolve_skus(nl_text)` → list[str]

**Time Parsing Examples**:
- "today" → SGT date range for current day
- "last week" → SGT date range for previous 7 days  
- "Q4" → date range for fiscal or calendar Q4 based on FISCAL_CALENDAR_START_MONTH
- "this month" → SGT date range for current month

**SKU Resolution**:
- Uses `backend/app/core/glossary_map.json` for alias mapping
- "iPhone" → ["APPL-IPH-001"] 
- "MacBook" → ["APPL-MBP-001", "APPL-MBA-001"]

### 4. Smart Hybrid Router (`backend/app/core/router.py`)

**Purpose**: Intelligently route queries using rules + embeddings + LLM tiebreaker.

**Routing Logic**:
1. **Rule Matching**: Score against 8 BI intent keywords
2. **Embedding Similarity**: Compare against exemplar phrases
3. **Combined Score**: 0.6 × rules + 0.4 × embeddings
4. **Decision Thresholds**:
   - ≥0.75: Direct route selection
   - 0.55-0.75: LM Studio tiebreaker call
   - <0.55: OPEN or NO_ANSWER

**Exemplar Files** (`backend/app/core/exemplars/`):
> Populate each file with **10–20 diverse phrasings** to ensure robust semantic routing.
```
bi/top_skus_by_margin.txt
bi/stockout_risk.txt  
bi/week_in_review.txt
bi/reorder_suggestions.txt
bi/slow_movers.txt
bi/product_detail.txt
bi/quarterly_forecast.txt
doc_qna.txt
open_chat.txt
```

**LM Studio Router Prompt**:
```
You are a strict router. Output only valid JSON.
Pick route: "BI" (database analytics), "RAG" (documents/policies), "MIXED" (both), or "OPEN".
If BI, include one intent from: ["top_skus_by_margin", "stockout_risk", "week_in_review", "reorder_suggestions", "slow_movers", "product_detail", "quarterly_forecast"].
Return {"route":"...","intent":null|"...","reason":"..."}.
```

### 5. In-Process RAG System (`backend/app/tools/rag/`)

**Purpose**: Document search and retrieval with citations, fully in-process.

#### 5.1. Vector Store (`backend/app/tools/rag/store.py`)

**Store Options**:
- **Chroma**: SQLite-based with `persist_directory` (set via `RAG_PERSIST_DIR`), simple setup
- **pgvector**: PostgreSQL extension, reuses existing DB

**Key Methods**:
- `upsert(docs)` → store documents with metadata
- `search(query, top_k, filters)` → retrieve candidates
- `delete(doc_ids)` → remove documents

**Document Metadata**:
```python
{
    "title": "Returns Policy",
    "url": "/policies/returns.pdf",
    "doc_type": "policy",
    "owner": "ops",
    "effective_date": "2025-08-01",
    "version": "1.2",
    "department": "operations"
}
```

#### 5.2. Document Ingestion (`backend/app/tools/rag/ingest.py`)

**CLI Usage**:
```bash
python -m backend.app.tools.rag.ingest \
    --path docs/ \
    --doc-type policy \
    --owner ops \
    --effective-date 2025-08-01
```

**Features**:
- Supports .txt, .md, .pdf, .csv files (use PyMuPDF or pdfminer for robust text; store page numbers for `url#page` anchors)
- 500-1000 token chunks with 100-150 overlap
- Automatic metadata extraction from file paths
- Batch processing with progress tracking

**Document Types to Ingest**:
- Returns/Exchanges policies
- Markdown/Discount policies  
- Supplier SLAs
- Standard Operating Procedures (SOPs)
- Data Dictionary/Glossary
- Forecast methodology notes

#### 5.3. Hybrid Retriever (`backend/app/tools/rag/retriever.py`)

**Retrieval Strategy**:
- **RBAC/Filters**: apply `department`, `owner`, and user/role filters at search time to restrict snippets.
1. **Keyword Search**: BM25 or PostgreSQL `pg_trgm` LIKE matching
2. **Vector Search**: Cosine similarity using LM Studio embeddings
3. **Hybrid Scoring**: Combine keyword + vector scores
4. **LLM Reranking**: Use LM Studio to reorder top ~12 candidates

**Return Format**:
```python
[{
    "title": "Returns Policy Section 3.2",
    "url": "/policies/returns.pdf#section-3.2", 
    "quote": "Markdown items eligible for exchange within 14 days...",
    "score": 0.89,
    "effective_date": "2025-08-01"
}]
```

### 6. Enhanced BI Tool (`backend/app/tools/bi_tool.py`)

**Purpose**: Execute parameterized SQL queries with rich provenance.

**Key Features**:
- Parameterized SQL templates for all 8 intents
- Row-level security/RBAC filters applied via `actor_id`/tenant in WHERE clauses
- Freshness checking against analytics marts
- Automatic fallback to transactional tables if stale
- Rich provenance metadata

**Return Format**:
```python
{
    "data": [...],                    # Query results
    "insights": [...],                # Business insights
    "provenance": {
        "tables": ["analytics_marts.sales_daily"],
        "query_id": "q_abc123",
        "refreshed_at": "2025-08-13T10:05:00+08:00"
    },
    "banner": "Fell back to transactional on stale mart"  # if applicable
}
```

**Supported Intents**:
1. `top_skus_by_margin`
2. `stockout_risk` 
3. `week_in_review`
4. `reorder_suggestions`
5. `slow_movers`
6. `product_detail`
7. `quarterly_forecast`

### 7. Unified Answer Composer (`backend/app/core/composer.py`)

**Purpose**: Transform tool outputs into consistent response format.

**Composition Methods**:
- `compose_bi(result)` → BI response with cards + provenance
- `compose_rag(snippets)` → RAG response with citations (≥1 required)
- `compose_mixed(bi_result, rag_snippets)` → Coherent blend of both
- `compose_open(llm_response)` → Open chat with guardrails
- `compose_no_answer(reason, follow_ups)` → Helpful fallback

**Guardrails**:
- BI responses: Must include provenance or return NO_ANSWER
- RAG responses: Must include ≥1 citation or return NO_ANSWER  
- No fabricated numbers without SQL backing
- All responses validate against unified schema

### 8. Orchestration Layer (`backend/app/api/endpoints/chat.py`)

**Purpose**: Wire together all components into unified chat endpoint.

**Request Flow**:
1. **Route Decision**: `router.route(user_text)` → {route, intent, confidence}
2. **Parameter Extraction**: Extract time ranges, SKUs, units in SGT
3. **Tool Execution**:
   - **BI**: `bi_tool.run(intent, time_start, time_end, skus, options)`
   - **RAG**: `rag.retriever.search(question, top_k, filters)`
   - **MIXED**: Execute both tools (parallel if possible)
   - **OPEN**: LM Studio chat with fact-checking via tools
4. **Response Composition**: Transform to unified JSON format
5. **Validation**: Ensure response passes schema validation

**Error Handling**:
- Tool failures → NO_ANSWER with helpful follow_ups
- Schema validation failures → Error logging + fallback response
- LM Studio unavailable → Graceful degradation message

## Example Query Flows

### 1. Pure BI Query
**Input**: "what is today's best selling item?"

**Flow**:
1. Router: Rules match "best selling" → BI/top_skus_by_margin (score: 0.95)
2. Params: "today" → SGT date range for current day
3. BI Tool: Execute top_skus_by_margin SQL with today's date filter
4. Composer: Build response with data table + provenance
5. Output: Cards with top products, query metadata, high confidence

### 2. Pure RAG Query  
**Input**: "what is our returns policy for markdowns?"

**Flow**:
1. Router: Rules + embeddings → RAG (score: 0.82)
2. RAG Tool: Hybrid search for "returns policy markdowns"
3. Results: Find policy document section with relevant quote
4. Composer: Build response with citation (≥1 required)
5. Output: Policy text with document reference, medium confidence

### 3. Mixed Query
**Input**: "forecast Q4 margin if I markdown slow movers by 20% and confirm the policy"

**Flow**:
1. Router: Complex query → MIXED route via LM Studio tiebreaker
2. Params: "Q4" → SGT Q4 date range, "20%" → {"percent": 0.2}
3. BI Tool: Execute quarterly_forecast + slow_movers SQL
4. RAG Tool: Search for markdown policies  
5. Composer: Merge SQL forecast with policy constraints
6. Output: Financial projection + policy compliance, structured format

## Testing Strategy

### Unit Tests (`backend/app/tests/`)

**test_router.py**:
- Rule matching accuracy
- Embedding similarity scoring
- LM Studio tiebreaker logic
- Edge cases and thresholds

**test_params.py**:
- Singapore timezone conversion
- Natural language time parsing
- SKU alias resolution
- Number/unit extraction

**test_bi_tool.py**:
- SQL template rendering
- Provenance metadata
- Freshness checking
- Fallback mechanisms

**test_rag_tool.py**:
- Document indexing
- Hybrid retrieval accuracy
- Citation requirements
- Metadata filtering

**test_composer.py**:
- Schema validation
- Response consistency
- Guardrail enforcement
- NO_ANSWER handling

### Integration Tests

**End-to-End Scenarios**:
- Pure BI queries with various intents
- Pure RAG queries with different document types
- Mixed queries requiring both systems
- Error handling and fallback behaviors

**Mock Strategy**:
- Mock LM Studio HTTP endpoints for deterministic testing
- Mock database with known test data
- Mock vector store with controlled document set

## Deployment Considerations

### LM Studio Setup
1. Install LM Studio with the `openai/gpt-oss-20b` model loaded
2. Ensure OpenAI-compatible API is enabled and running at 127.0.0.1:1234
3. Configure model: `openai/gpt-oss-20b` (handles both chat and embeddings)
4. Verify both `/chat/completions` and `/embeddings` endpoints work

### Document Preparation
1. Collect key business documents (policies, SOPs, glossaries)
2. Organize in structured directory with clear naming
3. Run ingestion CLI to populate vector store
4. Verify search functionality with sample queries

### Monitoring & Observability

### Caching & Performance
- BI result cache keyed by (intent, params, snapshot) with TTL.
- Semantic cache for recent natural-language prompts.
- Parallelize BI and RAG in MIXED route.
- Consider a smaller instruct model if latency exceeds target; keep embeddings stable.
- Health check endpoint for LM Studio connectivity
- Request/response logging for debugging
- Performance metrics for route distribution
- Error tracking for failed queries

## Success Criteria

### Functional Requirements
- ✅ `/chat` endpoint returns unified JSON for all route types
- ✅ LM Studio is the only LLM provider (no OpenAI dependencies)
- ✅ BI responses include query provenance and freshness metadata
- ✅ RAG responses include document citations with quotes
- ✅ Mixed queries execute both systems and merge coherently
- ✅ Singapore timezone handling for all time references
- ✅ NO_ANSWER path with helpful follow-up suggestions

### Non-Functional Requirements  
- ✅ Response time <3 seconds for typical queries
- ✅ Schema validation for all outputs
- ✅ Comprehensive test coverage (>90%)
- ✅ Clear error messages and graceful degradation
- ✅ README instructions for LM Studio setup

### Example Validations
```bash
# Test BI route
curl -s localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message":"what is today's best selling item?"}' | jq '.route'
# Expected: "BI"

# Test RAG route  
curl -s localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message":"what is our returns policy for markdowns?"}' | jq '.route'
# Expected: "RAG"

# Test MIXED route
curl -s localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message":"forecast Q4 margin if I markdown slow movers by 20% and confirm policy"}' | jq '.route'
# Expected: "MIXED"
```

## Implementation Timeline

### Phase 1: Foundation (Days 1-3)
- LM Studio client
- JSON contracts  
- Parameter extractor
- Basic router (rules only)

### Phase 2: Core Systems (Days 4-7)
- Enhanced BI tool with provenance
- In-process RAG system (store, ingest, retriever)
- Embedding-based router improvements
- Answer composer

### Phase 3: Integration (Days 8-10)
- Wire orchestration into chat endpoint
- LM Studio tiebreaker logic
- Mixed query handling
- Error handling and guardrails

### Phase 4: Testing & Polish (Days 11-14)
- Comprehensive test suite
- Documentation updates
- Performance optimization
- Production readiness review