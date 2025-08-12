## StockPilot – AI Agent Quick Operating Guide
Concise, project‑specific rules so agents can act safely & productively. Show diffs only (no full file dumps) and preserve multi‑tenant + event‑sourcing guarantees.

### 1. Architecture (Big Picture)
Flow: FastAPI backend (`backend/app`) ←→ Postgres (core + append‑only `inventory_movements`) + Redis → dbt models (`backend/dbt`) → Analytics/Reports endpoints (`/api/v1/analytics/*`, `/api/v1/reports/*`) → Next.js App Router UI (React Query hooks) → Optional chat intent endpoint `/api/v1/chat/query`.
Inventory is event‑sourced: on‑hand is derived (NEVER persist a running total). Every business row carries `org_id`; JWT (see `app/core/security.py`) injects `org` + `role`.

### 2. Multi‑Tenancy & Auth
ALWAYS scope DB queries with `Model.org_id == claims.get("org")` (ignore client‑supplied org). Use `Depends(get_current_claims)` for reads; `Depends(require_role("admin"))` for privileged mutations. Never expose IDs from other orgs in responses or errors.

### 3. Data & Models
Unified GUID Type: `models/base.py` (`GUID` TypeDecorator). All PKs & FKs use `BaseModel.UUIDType` not raw dialect UUID types.
Timestamps: `BaseModel` provides `created_at` + `updated_at`; do not redeclare them (e.g. `InventoryMovement` now inherits both).
Schema Evolution: No Alembic yet. Add columns by (a) updating `backend/init.sql`, (b) adding an idempotent SQL file under `backend/migrations/`, or (c) a one‑off manual `ALTER TABLE` (document it). Keep changes additive.

### 4. Inventory Logic
Insert a new `InventoryMovement` for every change (`movement_type`: in | out | adjust | transfer). Never update historical quantity or store a consolidated stock count. Summary endpoints aggregate on demand with signed quantities (see inventory endpoint code using `case`).

### 5. Analytics Pattern
Always attempt mart table first (e.g. `analytics_marts.sales_daily`). On failure (missing mart / dbt not run) fallback to base tables with equivalent field names. Only ADD new response fields—do not rename existing ones to avoid frontend breakage. Stockout risk: aggregate velocity + classify (<=7 high, <=14 medium, <=30 low, else none).

### 6. Chat Layer
`/api/v1/chat/query`: apply deterministic intent rules first (`services/intent_rules.py`) then, only if enabled by env (`CHAT_ENABLED`, `CHAT_LLM_FALLBACK_ENABLED`), call the LLM client (`services/llm_client.py`). Return confidence + freshness metadata; prefer expanding rules over relying on LLM.

### 7. Frontend Conventions
HTTP wrapper: `frontend/src/lib/api.ts` handles base URL + token refresh. Add a typed function there, then a React Query hook in `frontend/src/hooks/`. Pages stay thin; no direct fetch logic. Compose chat responses via existing hooks mapped from intents.

### 8. Tests & Local Dev
Quick run: `cd backend && DATABASE_URL=sqlite:///./test.db pytest` (SQLite auto‑creates tables). For Postgres: `docker-compose up -d` then run API with uvicorn. Integration tests mint JWTs via `create_access_token`; follow that pattern. Reset Postgres data: `docker-compose down -v && docker-compose up -d` (replays `init.sql`).

### 9. Adding a Feature (Minimal Steps)
1. Model: subclass `Base` + `BaseModel`; add `org_id` & domain fields (no duplicate timestamps).
2. Schema: Pydantic (`from_attributes = True`); accept blank server‑generated fields.
3. Router: new file under `api/api_v1/endpoints`; include in `api/api_v1/api.py`; enforce auth + org filter.
4. (If analytics) Extend mart + fallback logic—add fields only.
5. Frontend: api.ts function → hook → page/component.
6. Tests: CRUD + integration; use GUID fixtures or create objects inside test.

### 10. Guardrails
Never: persist computed stock, skip org filter, broad `except` hiding root causes, expose other org IDs, redefine BaseModel timestamps.
Prefer: additive SQL changes, explicit column lists in analytics responses, `model_dump()` (modernize legacy `dict()` usages gradually), small focused diffs.

### 11. Key Paths
Routers: `backend/app/api/api_v1/endpoints/`
Models: `backend/app/models/`
Schemas: `backend/app/schemas/`
Analytics dbt marts: `backend/dbt/models/marts/`
Chat: `backend/app/api/api_v1/endpoints/chat.py` + `services/intent_*`
Migrations (ad hoc): `backend/migrations/`
Tests: `backend/tests/`

### 12. Example Snippets
Org‑scoped query pattern:
```python
products = db.query(Product).filter(Product.org_id == claims.get("org")).all()
```
Add movement (event sourcing):
```python
db.add(InventoryMovement(product_id=pid, location_id=lid, quantity=delta, movement_type='adjust', timestamp=now))
```

Return only changed lines in patches. Maintain multi‑tenant safety & analytics fallback consistency.
