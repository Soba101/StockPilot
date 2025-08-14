## StockPilot – AI Agent Operating Guide
Concise, repo‑specific rules so agents act safely & productively. Output only diffs for edits; never dump whole files. Preserve multi‑tenant + event‑sourcing invariants.

### 1. Architecture
FastAPI backend (`backend/app`) ←→ Postgres (core tables + append‑only `inventory_movements`) + Redis → dbt marts (`backend/dbt`) → Analytics & Reports endpoints → Next.js App Router UI (hooks) → Chat layer (rule intents + LLM fallback + emerging hybrid router `/chat2`). On‑hand inventory is ALWAYS derived (sum movements); never stored as a mutable column.

### 2. Multi‑Tenancy & Auth
Every business row has `org_id`. Always filter queries: `Model.org_id == claims['org']`. Ignore client‑supplied org IDs. Use `Depends(get_current_claims)`; for privileged ops wrap with `require_role("admin")`. Never leak another org's IDs (even in errors).

### 3. Data & Models
GUID TypeDecorator in `models/base.py` (use provided types, not raw UUID). `BaseModel` already gives `created_at`,`updated_at`. Additive schema changes only: update `backend/init.sql` + drop an idempotent SQL file in `backend/migrations/`. No Alembic yet.

### 4. Inventory Event Sourcing
Mutations insert `InventoryMovement` (types: in|out|adjust|transfer); never edit past movements. Derive stock via signed aggregation at query time (see inventory & stockout risk handlers). Avoid caching on‑hand totals in DB.

### 5. Analytics Pattern
Mart‑first (e.g. `analytics_marts.sales_daily`); fallback to raw tables if mart missing or query fails. When adding fields only APPEND—do not rename existing response keys (frontend stability). Stockout risk tiers: ≤7 high, ≤14 medium, ≤30 low, else none.

### 6. Chat & Hybrid Layer
Legacy endpoint `/api/v1/chat/query` uses deterministic intent rules (`services/intent_rules.py`) → optional LLM fallback (`services/llm_client.py`). New hybrid scaffold: `/api/v1/chat2/query` with router + composer in `app/core/` (`router.py`, `composer.py`, `llm_lmstudio.py`, `contracts.py`, `params.py`). Feature flags: `HYBRID_CHAT_ENABLED`, `HYBRID_ROUTER_*`. LM Studio only: extend fallback endpoints and long timeouts; prefer BI rule answers over LLM.

### 7. Frontend Conventions
All HTTP calls go through `frontend/src/lib/api.ts` (token refresh, base URL). Add: api function → React Query hook (`src/hooks/`) → page/component (`src/app/`). Components must not call fetch/axios directly. Chat UI should migrate to `/chat2` when hybrid flags enabled.

### 8. Testing & Local Dev
Fast unit run (SQLite): `cd backend && DATABASE_URL=sqlite:///./test.db pytest -q`. Postgres + dbt: `docker-compose up -d`, then run uvicorn. Reset DB: `docker-compose down -v && docker-compose up -d` (replays `init.sql`). JWTs minted via `create_access_token` in tests. New hybrid tests live under `backend/tests/` (e.g. `test_hybrid_router.py`).

### 9. Adding Features
1. Model (`app/models`) inherit `Base` + `BaseModel`; include `org_id`. 2. Pydantic schema (allow server fields blank). 3. Endpoint under `api/api_v1/endpoints`, register in `api/api_v1/api.py`, enforce org filter. 4. (Analytics) Add mart + fallback logic; append fields only. 5. Frontend: api.ts → hook → UI. 6. Tests: CRUD + integration; avoid global state hacks.

### 10. Guardrails & Anti‑Patterns
Never: persist computed on‑hand; skip org filters; broad bare `except`; leak foreign org IDs; duplicate timestamp columns; rename existing response keys; commit large file dumps in patches. Prefer: explicit column lists, additive SQL, `model_dump()`, small focused diffs, schema validation before returning chat responses.

### 11. Key Paths
Endpoints: `backend/app/api/api_v1/endpoints/`
Models: `backend/app/models/`
Schemas: `backend/app/schemas/`
Hybrid Chat Core: `backend/app/core/{router,composer,contracts,llm_lmstudio,params}.py`
Intent Rules: `backend/app/services/intent_rules.py`
DBT marts: `backend/dbt/models/marts/`
Migrations (ad hoc SQL): `backend/migrations/`
Frontend API wrapper: `frontend/src/lib/api.ts`
Tests: `backend/tests/`

### 12. Examples
Org‑scoped query:
```python
products = db.query(Product).filter(Product.org_id == claims['org']).all()
```
Insert movement:
```python
db.add(InventoryMovement(product_id=pid, location_id=lid, quantity=delta, movement_type='adjust', timestamp=now))
```
Hybrid chat BI compose (use composer):
```python
from app.core import composer
resp = composer.compose_bi(bi_result, summary, intent, confidence)
```

### 13. Patch Etiquette
Show ONLY changed lines (unified diff). Do not reformat unrelated code. Respect multi‑tenant filters & event sourcing. If uncertain about an analytics fallback, replicate existing pattern (mart try → fallback query) and comment briefly.

### 14. When Unsure
Prefer rule/SQL expansion over LLM prompts. Provide a minimal draft + TODO comments rather than stalling. Flag assumptions explicitly.
