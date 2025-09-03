## StockPilot – AI Agent Guide
Event-sourced inventory management with analytics marts, hybrid AI chat, and multi-tenant architecture. Focus: protect multi-tenancy + event-sourced inventory; keep analytics mart-first with safe fallbacks; produce small focused diffs.

### Core Architecture & Data Flow
FastAPI (`backend/app`) → Postgres (append-only `inventory_movements` + core tables) + Redis → dbt marts (`backend/dbt/models/marts/`) → Analytics/Reports endpoints → Next.js (React Query + Radix UI) → Hybrid Chat (rules/embeddings + LLM tiebreaker). 

**Critical**: On-hand stock is ALWAYS derived (sum movements); never a mutable column. Use event sourcing pattern for all inventory changes.

### Multi-Tenancy & Auth (Mandatory)
Every model has `org_id`; ignore any client-supplied org. Always: `Model.org_id == claims['org']`. Use `Depends(get_current_claims)`; wrap privileged ops with `require_role("admin")`. Never leak foreign org IDs (even in error text).

```python
# Always filter by org in endpoints
items = db.query(Product).filter(Product.org_id == claims['org']).all()
```

### Inventory Event Sourcing (Core Pattern)
All changes insert an `InventoryMovement` (types: in | out | adjust | transfer). Do not update or delete past movements; derive current quantity via aggregation in queries/analytics. Multi-tenancy enforced through Product/Location relationships (no direct `org_id` on movements).

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
Single fetch layer: `frontend/src/lib/api.ts` (auth + dynamic base URL + LAN IP support) → React Query hook (`src/hooks/use-*.ts`) → component (`src/app/`). Components must not call fetch/axios directly. Uses Radix UI components + Tailwind CSS. API client auto-detects localhost vs LAN access via Next.js rewrites.

```typescript
// Hooks follow this pattern: use-*.ts files with React Query
export function useProducts() {
  return useQuery<Product[], Error>({
    queryKey: ['products'],
    queryFn: () => productsApi.list().then(res => res.data),
  });
}
```

### Chat & Hybrid Routing
Legacy `/api/v1/chat/query` (rules → LLM). Hybrid `/api/v1/chat2/query` uses `app/core/{router,composer,contracts,params,llm_lmstudio}.py` with semantic scoring + embeddings under feature flags `HYBRID_CHAT_ENABLED`, `HYBRID_ROUTER_*`. BI exemplars stored in `app/core/exemplars/bi/`. Prefer deterministic BI intents over LLM; compose responses via `composer.compose_bi(...)`.

```python
# Hybrid router decision flow: rules → embeddings → LLM tiebreaker
@dataclass
class RouteDecision:
    route: str  # RAG | OPEN | NO_ANSWER
    intent: str | None
    confidence: float
    reason: str
```
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
- Use `GUID()` type for all IDs (cross-platform: UUID in Postgres, CHAR(36) in SQLite) 
- All models inherit from `BaseModel` (auto-timestamps, UUID primary keys, shared UUIDType)
- Migrations in `backend/migrations/*.sql` (additive only)
- dbt marts in `backend/dbt/models/marts/` for analytics (materialized as tables)
- SQLAlchemy ORM with declarative models extending `Base, BaseModel`

```python
# Standard model pattern
class Product(Base, BaseModel):
    __tablename__ = "products"
    org_id = Column(BaseModel.UUIDType, ForeignKey("organizations.id"), nullable=False)
    sku = Column(String(100), nullable=False)
    # id, created_at, updated_at inherited from BaseModel
```

### Testing Patterns
- Integration tests in `backend/tests/test_api_integration.py` use real JWT tokens via `create_access_token()`
- Skip integration tests if API server not running: `pytest.skip("API server is not running")`
- Use `TEST_ORG_ID` and `TEST_USER_ID` constants for consistent test data
- Quick tests (SQLite): `DATABASE_URL=sqlite:///./test.db pytest -q`
- Full suite requires containers running: `docker-compose up -d && pytest`

```python
# Standard test pattern
@pytest.fixture(scope="session")
def auth_headers():
    token = create_access_token(sub=TEST_USER_ID, org_id=TEST_ORG_ID, role="admin")
    return {"Authorization": f"Bearer {token}"}
```

### Guardrails (NEVER / ALWAYS)
**NEVER**: persist computed on-hand; skip org filter; broad bare `except`; rename existing JSON keys; leak other org IDs; reformat entire files; commit large dumps.

**ALWAYS**: additive SQL + migrations; explicit column lists; derive stock via aggregation; small focused diffs; include 3-5 lines of context in edits.

### Key File Patterns
- Endpoints: `backend/app/api/api_v1/endpoints/` (register in `api.py`)
- Models: `backend/app/models/` (all inherit `Base, BaseModel` with `org_id`)
- Schemas: `backend/app/schemas/` (Pydantic validation/serialization)
- Frontend API: `frontend/src/lib/api.ts` (single source, auth + LAN-aware URLs)
- Hooks: `frontend/src/hooks/use-*.ts` (React Query wrappers, kebab-case naming)
- dbt marts: `backend/dbt/models/marts/` (analytics tables + schema.yml)
- Tests: `backend/tests/test_*.py` (integration + unit patterns)
- Config: `backend/app/core/config.py` (settings with env fallbacks)
- Chat: `backend/app/core/{router,composer,llm_lmstudio}.py` (hybrid architecture)

### Error Handling & Debugging
- Frontend uses React Query for error states, retries, and optimistic updates
- Backend analytics: mart-first with graceful fallback to raw queries (try/except pattern)
- Auth errors: check token expiration, org filtering (`claims['org']`), and role requirements
- Integration tests require running containers (`docker-compose up -d`)
- LAN access: Next.js rewrites proxy `/api/*` to `localhost:8000/api/v1/*` automatically
- Multi-tenant violations: always filter by `org_id` in queries, never leak foreign org data

```python
# Standard mart-first error handling
try: 
    rows = db.execute(mart_sql).fetchall()
    logger.info("Using analytics mart")
except Exception as e: 
    logger.warning(f"Mart failed: {e}, falling back to raw tables")
    rows = db.execute(fallback_sql).fetchall()
```
