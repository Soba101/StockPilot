# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (FastAPI + Python)
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Testing
pytest                          # Run all tests
pytest tests/test_integration.py  # Integration tests only  
pytest -m unit                  # Unit tests only
pytest -m crud                  # CRUD tests only
```

### Frontend (Next.js + TypeScript)
```bash
cd frontend
npm install
npm run dev       # Development server
npm run build     # Production build
npm run lint      # ESLint check
```

### dbt Analytics Pipeline
```bash
cd backend/dbt
dbt run           # Build marts from staging models
dbt test          # Run data quality tests
```

### Infrastructure
```bash
# Start services (Postgres + Redis)
docker-compose up -d

# Reset database (drops volumes, reseeds from init.sql)
docker-compose down -v && docker-compose up -d
```

## Architecture Overview

**StockPilot** is a multi-tenant inventory management system with event-sourced inventory tracking and AI-powered analytics chat.

### Core Architecture Pattern
```
User Actions → FastAPI CRUD → PostgreSQL → Event-sourced inventory_movements → 
dbt staging/marts → Analytics endpoints → React/Next.js + React Query → Chat assistant
```

### Key Architectural Principles

1. **Event Sourcing for Inventory**: Never store static stock quantities. All inventory changes create new `inventory_movements` records with movement types: `in`, `out`, `adjust`, `transfer`. Current stock is derived by summing movements.

2. **Multi-Tenancy**: Every model includes `org_id`. All endpoints filter by JWT `org` claim via `get_current_claims()`. Use `require_role("admin")` for privileged operations.

3. **Analytics-First with Fallbacks**: Analytics endpoints attempt mart queries first (`analytics_marts.sales_daily`), then fallback to base tables if marts aren't built. This pattern maintains functionality when dbt hasn't run.

### Data Flow Layers

| Layer | Purpose | Key Files |
|-------|---------|-----------|
| FastAPI API | Multi-tenant CRUD + analytics | `backend/app/api/api_v1/endpoints/` |
| Event Store | Append-only inventory movements | `backend/app/models/inventory.py` |
| dbt Transforms | Stage raw data → business metrics | `backend/dbt/models/marts/sales_daily.sql` |
| Analytics | Mart-first queries with fallbacks | `backend/app/api/api_v1/endpoints/analytics.py` |
| Frontend | React Query hooks + Next.js App Router | `frontend/src/hooks/`, `frontend/src/app/` |
| Chat System | Intent resolution → existing hooks | `backend/app/services/intent_rules.py` |

## Chat & Intent System

The chat system uses deterministic keyword matching in `backend/app/services/intent_rules.py` before falling back to LLM. Available intents:

- `top_skus_by_margin` - Top performing products by gross margin
- `stockout_risk` - Products at risk of stocking out  
- `week_in_review` - Daily metrics for past 7 days
- `reorder_suggestions` - AI-powered purchase recommendations
- `slow_movers` - Products with low velocity but high inventory
- `product_detail` - Detailed metrics for specific product

Each intent handler follows the mart-first/fallback pattern and returns structured data consumed by existing React Query hooks.

## Development Patterns

### Adding New Features

1. **Backend Model**: Extend `BaseModel` (includes `org_id`, timestamps). Use `GUID` type from `models/base.py`.
2. **Pydantic Schemas**: Add request/response schemas in `schemas/`
3. **Router**: Create endpoint in `api/api_v1/endpoints/`, register in `api/api_v1/api.py`
4. **Frontend**: Add API method to `lib/api.ts` → React Query hook in `hooks/` → UI components
5. **Tests**: Add integration tests following existing patterns with JWT minting

### Inventory Operations
```python
# NEVER store static quantities - always create movements
db.add(InventoryMovement(
    product_id=product_id,
    location_id=location_id, 
    quantity=delta,  # positive for in/adjust, negative for out
    movement_type='adjust',
    timestamp=datetime.utcnow()
))
```

### Multi-tenant Query Pattern
```python
# Always filter by org_id from JWT claims
products = db.query(Product).filter(
    Product.org_id == claims.get("org")
).all()
```

### Analytics with Fallback Pattern
```python
try:
    # Attempt mart query first
    result = db.execute(mart_sql, params).fetchall()
except Exception:
    # Fallback to base tables  
    result = db.execute(fallback_sql, params).fetchall()
    # Mark fallback was used for debugging
```

## Key Business Logic

### Reorder Algorithm (W5)
The purchase suggestions system uses velocity forecasting with supplier constraints:

1. Calculate `horizon_days = max(7, lead_time + safety_stock_days)`
2. Forecast demand using latest available velocity (7d → 30d → 56d priority)
3. Compute shortfall vs current inventory + incoming stock
4. Apply MOQ enforcement, pack rounding, max stock capping
5. Strategies: "latest" (recent velocity priority) vs "conservative" (minimum velocity)

### Stockout Risk Classification
- **High**: ≤7 days of stock remaining
- **Medium**: 8-14 days  
- **Low**: 15-30 days
- **None**: >30 days or no velocity data

## Environment Variables

Key backend environment variables in `.env`:

```env
DATABASE_URL=postgresql://stockpilot:stockpilot_dev@localhost:5432/stockpilot
SECRET_KEY=your-jwt-secret
OPENAI_API_KEY=your-openai-key
CHAT_ENABLED=1
ALERT_CRON_TOKEN=dev-cron-token
```

## Testing Strategy

- **Unit Tests**: Business logic, calculations (`-m unit`)
- **CRUD Tests**: Database operations (`-m crud`) 
- **Integration Tests**: Full API workflows with JWT auth (`-m integration`)

Integration tests require running backend server and use `create_access_token()` for authentication.

## Project Structure

```
backend/
├── app/
│   ├── api/api_v1/endpoints/     # REST endpoints by domain
│   ├── models/                   # SQLAlchemy models (all include org_id)  
│   ├── schemas/                  # Pydantic request/response schemas
│   ├── services/                 # Business logic (intent_rules, reorder, etc.)
│   └── core/                     # Config, database, security
├── dbt/models/
│   ├── staging/                  # Raw table transformations
│   └── marts/                    # Business metrics (sales_daily, etc.)
└── tests/                        # Test suite

frontend/
├── src/
│   ├── app/                      # Next.js App Router pages
│   ├── hooks/                    # React Query data fetching hooks
│   ├── lib/api.ts               # Axios instance + token refresh
│   └── components/               # Reusable UI components
```

## Common Gotchas

1. **Never store computed inventory totals** - always derive from movements
2. **Always apply org_id filters** - multi-tenancy security requirement  
3. **Prefer mart queries with fallbacks** - maintains functionality when dbt isn't built
4. **Use existing hooks in chat responses** - avoid duplicating data fetching logic
5. **Test with integration tests** - they catch multi-tenancy and auth issues