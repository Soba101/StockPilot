## StockPilot – AI Agent Guide (Concise)
Focus: protect multi‑tenancy + event‑sourced inventory; keep analytics mart‑first with safe fallbacks; produce small diffs only.

### Core Architecture (Why)
FastAPI (`backend/app`) → Postgres (append‑only `inventory_movements` + core tables) + Redis → dbt marts (`backend/dbt`) → Analytics/Reports endpoints → Next.js (hooks) → Chat (rule intents + hybrid `/chat2`). On‑hand stock is ALWAYS derived (sum movements); never a mutable column.

### Multi‑Tenancy & Auth
Every model has `org_id`; ignore any client‑supplied org. Always: `Model.org_id == claims['org']`. Use `Depends(get_current_claims)`; wrap privileged ops with `require_role("admin")`. Never leak foreign org IDs (even in error text).

### Inventory Event Sourcing
All changes insert an `InventoryMovement` (types: in | out | adjust | transfer). Do not update or delete past movements; derive current quantity via aggregation in queries / analytics.

### Analytics Pattern
Attempt mart (e.g. `analytics_marts.sales_daily`) first; on failure/missing, fallback to raw tables with equivalent fields; append new response fields only (never rename). Stockout risk tiers: ≤7 high, ≤14 medium, ≤30 low, else none.

### Chat / Hybrid
Legacy `/api/v1/chat/query` (rules → LLM). Hybrid `/api/v1/chat2/query` uses `app/core/{router,composer,contracts,params,llm_lmstudio}.py` under feature flags `HYBRID_CHAT_ENABLED`, `HYBRID_ROUTER_*`. Prefer deterministic BI intents over LLM; compose responses via `composer.compose_bi(...)`.

### Frontend Conventions
Single fetch layer: `frontend/src/lib/api.ts` (auth + base URL) → React Query hook (`src/hooks/`) → component (`src/app/`). Components must not call fetch/axios directly. Chat UI should migrate to `/chat2` when flags enabled.

### Dev & Tests
Start infra: `docker-compose up -d`. Run backend: `uvicorn app.main:app --reload`. Quick tests (SQLite): `DATABASE_URL=sqlite:///./test.db pytest -q`. Full suite (Postgres): ensure containers running then `pytest`. Reset DB: `docker-compose down -v && docker-compose up -d` (replays `init.sql`).

### Adding Backend Feature (Happy Path)
1 Model in `app/models` (inherit `BaseModel`, include `org_id`, use `GUID`). 2 Pydantic schemas. 3 Endpoint under `api/api_v1/endpoints/` + register in `api/api_v1/api.py` (org filter!). 4 (If analytics) add/extend mart SQL + safe fallback query. 5 Frontend api.ts → hook → page. 6 Tests (CRUD + integration) mint JWT via `create_access_token`.

### Guardrails (NEVER / ALWAYS)
NEVER: persist computed on‑hand; skip org filter; broad bare `except`; rename existing JSON keys; leak other org IDs; reformat entire files; commit large dumps. ALWAYS: additive SQL + migrations (`backend/migrations/*.sql`); explicit column lists; derive stock; small focused diffs.

### Key Paths
Endpoints: `backend/app/api/api_v1/endpoints/` | Models: `backend/app/models/` | Schemas: `backend/app/schemas/` | Chat Core: `backend/app/core/` | Intent Rules: `backend/app/services/intent_rules.py` | dbt marts: `backend/dbt/models/marts/` | Frontend API: `frontend/src/lib/api.ts` | Tests: `backend/tests/`.

### Snippets
Org filter:
```python
items = db.query(Product).filter(Product.org_id == claims['org']).all()
```
Insert movement:
```python
db.add(InventoryMovement(product_id=pid, location_id=lid, quantity=delta, movement_type='adjust', timestamp=now))
```
Mart-first fallback (pattern):
```python
try: rows = db.execute(mart_sql).fetchall()
except Exception: rows = db.execute(fallback_sql).fetchall()
```

### Patch Etiquette & Uncertainty
Submit unified diff of changed lines only; do not mass‑reflow unrelated code. If unsure: copy an existing analytics handler pattern, add `# TODO clarify` comment, and proceed (prefer concrete draft over stalling).

### When Extending Chat
Add intent rule → implement handler using existing analytics/query logic → compose via `composer` → ensure structured JSON matches existing schema; do not invent new top‑level keys without appending.

Feedback welcome: highlight any unclear convention so we can refine this guide.
