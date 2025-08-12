# Copilot Instructions – StockPilot

Fast orientation for AI agents; focus on project‑specific patterns (keep answers concrete, show diffs only for changed lines/files).

## 1. Big Picture Flow
Inbound data / user actions → FastAPI CRUD + event‑sourced inventory (`inventory_movements`) → dbt transforms (`backend/dbt`, marts under `analytics_marts.*`) → analytics/report endpoints (`/analytics`, `/analytics/sales`, `/analytics/stockout-risk`, `/reports/week-in-review`) → Next.js App Router UI using React Query hooks.
Multi‑tenant: every core table has `org_id`; JWT (created via `app.core.security.create_access_token`) supplies `org` + `role`. Never return cross‑org rows.

## 2. Backend Conventions
Routers: register in `api/api_v1/api.py` with prefix `/api/v1` (from settings). New endpoint: create `endpoints/<feature>.py`, add `api_router.include_router` entry.
Dependencies: always include `claims = Depends(get_current_claims)` then scope queries `Model.org_id == claims.get("org")`.
Role restriction: `claims = Depends(require_role("admin"))` (see `purchasing.py`).
Inventory: never store on‑hand; compute via summed movements (see stockout risk + reports queries). New stock logic → append movement rows.
Analytics fallback: try mart query (`analytics_marts.sales_daily`) inside try/except; on failure, fall back to base tables (pattern in `analytics.get_analytics` revenue + trend sections).
Stockout risk: combines live on‑hand (aggregate movements) + rolling averages (`units_7day_avg` / `units_30day_avg`) from mart; risk tiers: <=7 high, <=14 medium, <=30 low, else none.

## 3. dbt Layer
Location: `backend/dbt/models/{staging,marts}`. Core mart referenced in code: `sales_daily` providing: `units_sold`, `gross_revenue`, `gross_margin`, `margin_percent`, `orders_count`, rolling averages (`units_7day_avg`, `units_30day_avg`). Run & test: `cd backend/dbt && dbt run && dbt test`.
When adding metrics: extend mart with snake_case columns; preserve existing column names used by API to avoid breaking serializers.

## 4. Frontend Patterns
API base resolution & auth handled in `frontend/src/lib/api.ts` (dynamic base + token refresh on 401). Always add endpoints there, then wrap with a React Query hook in `src/hooks/use-*.ts` returning typed data + `loading` / `error`.
Pages live under `src/app/<feature>/page.tsx`; keep data fetching out of components—import hooks.
Chat page extends by matching keywords and calling existing hooks (see `app/chat/`).

## 5. Testing & Workflows
Spin infra: `docker-compose up -d` (Postgres + Redis). Backend: `uvicorn app.main:app --reload --port 8000`. Frontend: `npm run dev`.
Integration tests (`backend/tests/test_api_integration.py`) call live server using tokens from `create_access_token`; copy pattern for new endpoints (assert shape + status, use time/UUID for uniqueness). Run: `cd backend && pytest`.
Reset DB (wipe & reseed sample data): `docker-compose down -v && docker-compose up -d`.

## 6. Adding a Feature (Concrete Steps)
1. Model (`app/models/*`), include `org_id`, timestamps. 2. Schemas (`app/schemas/*`). 3. Endpoint module with scoped queries + router registration. 4. (Analytics) add/modify dbt model; expose with mart‑first fallback. 5. Frontend: add API method + typed hook + page/component. 6. Integration test.

## 7. Analytics/Mart Query Pattern (Example Skeleton)
```python
try:
	rows = db.execute(text("""SELECT ... FROM analytics_marts.sales_daily WHERE org_id=:org AND ..."""), {"org": org_id}).fetchall()
	# use mart rows
except Exception:
	# fallback: derive from base tables (join Orders/OrderItems/Products)
```

## 8. Pitfalls / Guardrails
Do NOT: store derived stock, omit org filters, bypass `require_role` on admin actions, or couple React components directly to axios (always via hook).
Keep new analytics resilient: preserve fallback, avoid breaking existing response models, prefer additive columns.

## 9. Key Paths
Endpoints: `backend/app/api/api_v1/endpoints/` | Models: `backend/app/models/` | Schemas: `backend/app/schemas/` | dbt marts: `backend/dbt/models/marts/` | Frontend hooks: `frontend/src/hooks/` | Tests: `backend/tests/`.

Return diffs only (no full file dumps) when editing; follow above patterns.
