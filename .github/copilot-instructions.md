# Copilot Instructions for StockPilot

Concise guidance for AI coding agents to be productive quickly in this repo.

## Core Architecture (Big Picture)
Backend (FastAPI + SQLAlchemy + PostgreSQL) provides CRUD + analytics + reporting APIs. Data flows: raw domain tables -> event-sourced inventory movements -> dbt transformations (`backend/dbt`) -> analytics marts (`sales_daily`) -> enriched API endpoints (`/analytics`, `/analytics/sales`, `/reports/week-in-review`) -> Next.js frontend (App Router) using React Query hooks.

Multi‑tenant boundary: every core table carries `org_id`; API access expects JWT with `org` claim (created via `app.core.security.create_access_token`).

## Key Backend Patterns
- Routers registered in `backend/app/api/api_v1/api.py`; prefix `/api/v1` from `settings.API_V1_STR` (see `app/core/config.py`). Add new endpoints by creating a module in `endpoints/` and including router.
- DB session + claims injection via `Depends(get_db)` and `Depends(get_current_claims)` from `app.core.database` (ensure to require org scoping in queries).
- Pydantic schemas live in `app/schemas/*`; keep response models explicit for FastAPI docs.
- Analytics endpoints: `analytics.py` (general KPIs + fallback logic if mart absent) and `reports.py` (Week in Review assembling multiple queries).
- Purchasing workflow consolidated in `purchasing.py` (PO number generation, status transitions, permission check via `require_role("admin")`). Use that pattern for future role‑restricted actions.
- Inventory integrity: no direct stock quantity fields—derive from `inventory_movements` (movement_type in|out|adjust|transfer). When adding stock logic, append new movement rows instead of mutating totals.
- Graceful degradation: analytics endpoints try mart (`analytics_marts.sales_daily`) then fallback to base tables. Preserve this try/except pattern for new analytics.

## dbt Data Layer
- Located in `backend/dbt/` with `models/staging` and `models/marts`. `sales_daily` mart powers velocity (`units_7day_avg`, `units_30day_avg`), margin %, channel performance, and trending detection.
- Run locally (inside Python venv or container) from `backend/dbt`: `dbt run`, `dbt test`. Keep tests (unique/not_null) for new marts.

## Frontend Conventions
- App Router under `frontend/src/app/*` (folders = routes). Each feature folder has a `page.tsx` plus subcomponents.
- Data fetching encapsulated in hooks: `frontend/src/hooks/use-*.ts` (e.g. `use-products`, `use-inventory`, `use-analytics`, `use-purchasing`). New endpoints => create parallel hook returning typed data + loading/error state.
- UI components use shadcn/ui pattern (see `components/ui/`). Follow existing Tailwind class style and minimal custom CSS.
- Auth context at `contexts/auth-context.tsx`; ensure API calls include token via centralized Axios (check `lib/api.ts` if present—add new base paths there).
- Chat page (`app/chat/page.tsx`) performs lightweight intent parsing over real inventory data; extend by importing additional hooks (e.g. analytics) and adding keyword branches.

## Testing & Workflows
- Integration tests in `backend/tests/test_api_integration.py` hit a running local server at `http://localhost:8000` using real DB (Docker). When adding endpoints, mirror patterns: acquire auth token via `create_access_token`, call REST with `requests`, assert shape + status.
- Run tests: `cd backend && pytest` (Pytest config in `backend/pytest.ini`). Keep tests idempotent—use timestamp/UUID SKUs for product creation.
- Spin services: `docker-compose up -d` (Postgres + Redis). Backend: `uvicorn app.main:app --reload --port 8000`. Frontend: `npm run dev`.
- DB reset for clean slate: `docker-compose down -v && docker-compose up -d` (replays `init.sql` + sample data).

## Security & Multi-Tenancy
- Always filter queries by `org_id = claims.get("org")` (see purchasing & reports examples). DO NOT return cross‑org aggregate data.
- Role checks: use `Depends(require_role("admin"))` for mutation endpoints that should be restricted.

## Adding a New Feature (Concrete Checklist)
1. Define SQLAlchemy model (`app/models/`) with `org_id` FK + timestamps.
2. Create Pydantic schemas (`app/schemas/`).
3. Implement endpoint module in `app/api/api_v1/endpoints/` using dependency injection & org scoping; include router in `api.py`.
4. If analytical: add/extend dbt models; expose new fields through endpoint with mart fallback.
5. Frontend: add types, hook (`use-newthing.ts`), page or component under `app/feature/`.
6. Add integration test hitting real server (pattern in existing test file).

## Performance & Future Enhancements
- Days-to-stockout placeholder: compute from current derived stock / max(velocity, epsilon); integrate into reports & dashboard once implemented.
- Keep analytics additions incremental—extend `sales_daily` or add parallel mart; maintain existing naming (snake_case columns) and include rolling averages where trend detection needed.

## Pitfalls to Avoid
- Don’t store derived inventory totals; always recompute via movements or summary queries.
- Don’t bypass org scoping or role requirements. Copy patterns from existing endpoints.
- Avoid coupling frontend components directly to raw fetch calls—always route through hooks for caching & invalidation.
- When updating analytics, preserve fallback logic to keep app resilient if dbt pipeline not yet run.

## Quick Reference Paths
- Endpoints: `backend/app/api/api_v1/endpoints/*.py`
- Models: `backend/app/models/*.py`
- Schemas: `backend/app/schemas/*.py`
- Config: `backend/app/core/config.py`
- dbt marts: `backend/dbt/models/marts/`
- Frontend hooks: `frontend/src/hooks/`
- Integration tests: `backend/tests/`

Provide concise diffs for file edits and follow established patterns above.
