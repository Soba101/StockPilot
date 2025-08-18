## StockPilot – AI Agent Guide
Event-sourced inventory management with analytics marts, hybrid AI chat, and multi-tenant architecture. Focus: protect multi-tenancy + event-sourced inventory; keep analytics mart-first with safe fallbacks; produce small focused diffs.

### Core Architecture & Data Flow
FastAPI (`backend/app`) → Postgres (append-only `inventory_movements` + core tables) + Redis → dbt marts (`backend/dbt`) → Analytics/Reports endpoints → Next.js (React Query hooks) → Chat (rule intents + hybrid `/chat2`). 

**Critical**: On-hand stock is ALWAYS derived (sum movements); never a mutable column. Use event sourcing pattern for all inventory changes.

### Multi-Tenancy & Auth (Mandatory)
Every model has `org_id`; ignore any client-supplied org. Always: `Model.org_id == claims['org']`. Use `Depends(get_current_claims)`; wrap privileged ops with `require_role("admin")`. Never leak foreign org IDs (even in error text).

```python
# Always filter by org in endpoints
items = db.query(Product).filter(Product.org_id == claims['org']).all()
```

### Inventory Event Sourcing (Core Pattern)
All changes insert an `InventoryMovement` (types: in | out | adjust | transfer). Do not update or delete past movements; derive current quantity via aggregation in queries/analytics.

```python
# Event sourcing pattern - insert movement, never update stock
db.add(InventoryMovement(product_id=pid, location_id=lid, quantity=delta, movement_type='adjust', timestamp=now))
```

### Analytics Mart-First Pattern
Attempt mart (e.g. `analytics_marts.sales_daily`) first; on failure/missing, fallback to raw tables with equivalent fields. Append new response fields only (never rename). Stockout risk tiers: ≤7 high, ≤14 medium, ≤30 low, else none.

```python
# Standard mart-first fallback pattern
try: 
    rows = db.execute(mart_sql).fetchall()
except Exception: 
    rows = db.execute(fallback_sql).fetchall()
```

### Frontend Architecture (Strict Layers)
Single fetch layer: `frontend/src/lib/api.ts` (auth + dynamic base URL) → React Query hook (`src/hooks/`) → component (`src/app/`). Components must not call fetch/axios directly. API client handles LAN IP detection automatically.

### Chat & Hybrid Routing
Legacy `/api/v1/chat/query` (rules → LLM). Hybrid `/api/v1/chat2/query` uses `app/core/{router,composer,contracts,params,llm_lmstudio}.py` under feature flags `HYBRID_CHAT_ENABLED`, `HYBRID_ROUTER_*`. Prefer deterministic BI intents over LLM; compose responses via `composer.compose_bi(...)`.

### Dev Workflow & Commands
```bash
# Start infrastructure (seeds DB via init.sql)
docker-compose up -d

# Backend development
cd backend && uvicorn app.main:app --reload

# Frontend development (supports LAN access)
cd frontend && npm run dev

# Tests: Quick (SQLite)
DATABASE_URL=sqlite:///./test.db pytest -q

# Tests: Full suite (requires containers)
pytest

# Analytics pipeline
cd backend/dbt && dbt run && dbt test

# Database reset (drops volumes, reseeds)
docker-compose down -v && docker-compose up -d
```

### Adding Backend Features (Standard Path)
1. Model in `app/models` (inherit `BaseModel`, include `org_id`, use `GUID`)
2. Pydantic schemas in `app/schemas`
3. Endpoint under `api/api_v1/endpoints/` + register in `api/api_v1/api.py` (org filter!)
4. (If analytics) add/extend mart SQL + safe fallback query
5. Frontend: api.ts → hook → page component
6. Tests (CRUD + integration) mint JWT via `create_access_token`

### Database & Types
- Use `GUID()` type for all IDs (works across SQLite/Postgres)
- All models inherit from `BaseModel` (auto-timestamps, UUID primary keys)
- Migrations in `backend/migrations/*.sql` (additive only)
- dbt marts in `backend/dbt/models/marts/` for analytics

### Testing Patterns
- Integration tests in `backend/tests/test_api_integration.py` use real JWT tokens
- Skip integration tests if API server not running: `pytest.skip("API server is not running")`
- Use `TEST_ORG_ID` and `TEST_USER_ID` constants for consistent test data

### Guardrails (NEVER / ALWAYS)
**NEVER**: persist computed on-hand; skip org filter; broad bare `except`; rename existing JSON keys; leak other org IDs; reformat entire files; commit large dumps.

**ALWAYS**: additive SQL + migrations; explicit column lists; derive stock via aggregation; small focused diffs; include 3-5 lines of context in edits.

### Key File Patterns
- Endpoints: `backend/app/api/api_v1/endpoints/`
- Models: `backend/app/models/` (all inherit BaseModel)
- Schemas: `backend/app/schemas/` (Pydantic validation)
- Frontend API: `frontend/src/lib/api.ts` (single source, auth + dynamic URLs)
- Hooks: `frontend/src/hooks/` (React Query wrappers)
- dbt marts: `backend/dbt/models/marts/` (analytics layer)
- Tests: `backend/tests/` (integration + unit)

### Error Handling & Debugging
- Frontend uses React Query for error states and retries
- Backend analytics: mart-first with graceful fallback to raw queries
- Auth errors: check token expiration, org filtering, and role requirements
- Integration tests require running containers (`docker-compose up -d`)
