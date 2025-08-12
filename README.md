# StockPilot

Inventory, purchasing & sales analytics with an event‑sourced inventory core and AI chat that turns operational data into decisions.

## Quick Start

1. Prerequisites
   - Node.js 18+
   - Python 3.11+
   - Docker & Docker Compose

2. Start services & apps

   ```bash
   # Infra (Postgres + Redis, seeds DB via init.sql)
   docker-compose up -d

   # Backend API
   cd backend
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000

   # (Optional) dbt analytics build
   cd dbt
   dbt run && dbt test

   # Frontend
   cd ../../frontend
   npm install
   npm run dev
   ```

3. Access

   - Frontend: <http://localhost:3000>
   - API: <http://localhost:8000>
   - Docs (OpenAPI): <http://localhost:8000/docs>

## Architecture & Data Flow

User actions / imports → FastAPI CRUD → PostgreSQL core tables → append‑only `inventory_movements` (event sourcing) → dbt staging & marts (`sales_daily`, etc.) → Analytics & Reports endpoints → React/Next.js (App Router) + React Query → Chat assistant surfaces metrics.

### Key Components

| Layer | Purpose | Notables |
|-------|---------|----------|
| FastAPI | Multi‑tenant CRUD + analytics | Org scoping via JWT `org` claim; role via `role` |
| Event Sourcing | Derive on‑hand from summed movements | Never store static stock quantity |
| dbt | Transform + precompute metrics | `sales_daily` supplies velocity + margin + rolling avgs |
| Analytics Endpoints | `/analytics`, `/analytics/sales`, `/analytics/stockout-risk`, `/reports/week-in-review` | Mart‑first with graceful fallback |
| Frontend | Next.js (App Router) | Hooks isolate data fetching; dynamic API base in `src/lib/api.ts` |
| Chat | Lightweight intent routing | Reuses existing hooks; keyword branching |

## Multi‑Tenancy & Security

All core tables include `org_id`. Every endpoint injects claims via `get_current_claims`; always filter queries (`Model.org_id == claims['org']`). Use `require_role("admin")` (see purchasing endpoints) for privileged mutations. Tokens created with `create_access_token(sub, org_id, role)`.

## Analytics & Metrics

`sales_daily` mart columns used in code: `units_sold`, `gross_revenue`, `gross_margin`, `margin_percent`, `orders_count`, `units_7day_avg`, `units_30day_avg`.

Features:

- Sales KPIs & revenue trend (`/analytics`)
- Detailed sales breakdown & channel performance (`/analytics/sales`)
- Stockout risk (live on‑hand + rolling velocity, risk tiers ≤7/≤14/≤30 days) (`/analytics/stockout-risk`)
- Week in Review consolidated report (`/reports/week-in-review` + CSV export)

If mart query fails (dbt not yet run), endpoints fall back to base tables—retain this pattern for new analytics.

## Development Patterns

Backend routers: register in `backend/app/api/api_v1/api.py` (`/api/v1` prefix). Schemas live in `backend/app/schemas`. Inventory changes: always insert new movement rows (types: in | out | adjust | transfer); never mutate an aggregated stock column.

Frontend: Add new REST call in `frontend/src/lib/api.ts`, then a React Query hook `frontend/src/hooks/use-<feature>.ts`, then a page/component under `src/app/<feature>/`. Avoid calling axios directly in components.

## Testing & DB Reset

Run all tests:

```bash
cd backend
pytest
```

Integration tests hit a live server (ensure `uvicorn` running); they mint JWTs with `create_access_token`.

Reset database (drops volumes & reseeds):

```bash
docker-compose down -v && docker-compose up -d
```

## Adding a Feature (Checklist)

1. SQLAlchemy model (`backend/app/models`) incl. `org_id`, timestamps.
2. Pydantic schemas.
3. Endpoint module (org scoping + optional role restriction) + register router.
4. (Analytics) Extend / add dbt model & columns (snake_case); expose via mart‑first fallback.
5. Frontend: API method + hook + UI.
6. Add/extend integration test.

## Project Structure (Condensed)

```text
backend/
  app/api/api_v1/endpoints/   # CRUD + analytics + reports
  app/models/                 # SQLAlchemy models (all with org_id)
  app/schemas/                # Pydantic schemas
  app/core/                   # config, database, security
  dbt/models/{staging,marts}  # Transformation + marts (sales_daily)
frontend/
  src/lib/api.ts              # Axios base + token refresh
  src/hooks/                  # React Query hooks
  src/app/                    # Routes (App Router)
```

## Common Issues & Tips

- 401s: Ensure tokens exist; refresh handled automatically in interceptor.
- Empty analytics: Run dbt (`dbt run`) or allow fallback logic; then refresh page.
- Wrong/incomplete data: Confirm Postgres port 5432 unused locally; if conflict, stop local Postgres.
- Adding inventory logic: never add a static stock column—derive from movements.

## License / Deployment

Local dev via Docker; deploy backend & dbt on managed Postgres (Railway noted). Provide environment variables mirroring those in `app/core/config.py` plus `JWT_SECRET` & OpenAI key for chat.

---

Concise docs intentionally; see code & tests for authoritative patterns.
