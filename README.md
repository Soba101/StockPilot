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

```mermaid
graph TB
    %% Frontend Layer
    subgraph "Frontend (Next.js)"
        UI[User Interface]
        RQ[React Query Hooks]
        API_CLIENT[API Client<br/>src/lib/api.ts]
        CHAT[AI Chat Interface]
    end

    %% API Layer
    subgraph "Backend (FastAPI)"
        ROUTER[API Router<br/>/api/v1/*]
        AUTH[JWT Auth<br/>Multi-tenant]
        CRUD[CRUD Endpoints]
        ANALYTICS[Analytics Endpoints]
        CHAT_SVC[Chat Service<br/>Intent Resolution]
    end

    %% Data Layer
    subgraph "Data Storage"
        PG[(PostgreSQL<br/>Core Tables)]
        REDIS[(Redis<br/>Cache)]
        EVENTS[(inventory_movements<br/>Event Sourcing)]
    end

    %% Analytics Layer
    subgraph "Analytics Pipeline"
        DBT[dbt Transformations]
        STAGING[Staging Models]
        MARTS[Business Marts<br/>sales_daily, etc.]
    end

    %% External Services
    OPENAI[OpenAI API<br/>Chat Fallback]

    %% Data Flow
    UI --> RQ
    RQ --> API_CLIENT
    API_CLIENT --> ROUTER
    CHAT --> CHAT_SVC

    ROUTER --> AUTH
    AUTH --> CRUD
    AUTH --> ANALYTICS
    AUTH --> CHAT_SVC

    CRUD --> PG
    CRUD --> EVENTS
    ANALYTICS --> REDIS
    ANALYTICS --> MARTS

    PG --> DBT
    EVENTS --> DBT
    DBT --> STAGING
    STAGING --> MARTS

    CHAT_SVC --> OPENAI
    CHAT_SVC --> ANALYTICS

    %% Styling
    classDef frontend fill:#e1f5fe
    classDef backend fill:#fff3e0
    classDef data fill:#f3e5f5
    classDef analytics fill:#e8f5e8
    classDef external fill:#ffebee

    class UI,RQ,API_CLIENT,CHAT frontend
    class ROUTER,AUTH,CRUD,ANALYTICS,CHAT_SVC backend
    class PG,REDIS,EVENTS data
    class DBT,STAGING,MARTS analytics
    class OPENAI external
```

### System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ User        │  │ React Query  │  │ AI Chat                 │ │
│  │ Interface   │  │ Hooks        │  │ Interface               │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
│                           │                     │               │
└───────────────────────────┼─────────────────────┼───────────────┘
                            │                     │
                            ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                            │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ JWT Auth    │  │ CRUD         │  │ Chat Service            │ │
│  │ Multi-tenant│  │ Endpoints    │  │ Intent Resolution       │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
│           │              │                     │               │
│           ▼              ▼                     ▼               │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ Analytics   │  │ Permissions  │  │ OpenAI Integration      │ │
│  │ Endpoints   │  │ org_id filter│  │                         │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Layer                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ PostgreSQL  │  │ Redis        │  │ inventory_movements     │ │
│  │ Core Tables │  │ Cache        │  │ (Event Sourcing)        │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                Analytics Pipeline (dbt)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ Staging     │  │ Business     │  │ Reports                 │ │
│  │ Models      │  │ Marts        │  │ (sales_daily, etc.)     │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Linear Data Flow
User actions / imports → FastAPI CRUD → PostgreSQL core tables → append‑only `inventory_movements` (event sourcing) → dbt staging & marts (`sales_daily`, etc.) → Analytics & Reports endpoints → React/Next.js (App Router) + React Query → AI Chat assistant surfaces metrics with structured responses.

### Key Components

| Layer | Purpose | Notables |
|-------|---------|----------|
| FastAPI | Multi‑tenant CRUD + analytics | Org scoping via JWT `org` claim; role via `role` |
| Event Sourcing | Derive on‑hand from summed movements | Never store static stock quantity |
| dbt | Transform + precompute metrics | `sales_daily` supplies velocity + margin + rolling avgs |
| Analytics Endpoints | `/analytics`, `/analytics/sales`, `/analytics/stockout-risk`, `/reports/week-in-review` | Mart‑first with graceful fallback |
| Frontend | Next.js (App Router) | Hooks isolate data fetching; dynamic API base in `src/lib/api.ts` |
| AI Chat | Intent resolution + LLM fallback | Deterministic rules → OpenAI; structured data responses |

## Multi‑Tenancy & Security

All core tables include `org_id`. Every endpoint injects claims via `get_current_claims`; always filter queries (`Model.org_id == claims['org']`). Use `require_role("admin")` (see purchasing endpoints) for privileged mutations. Tokens created with `create_access_token(sub, org_id, role)`.

## Analytics & Metrics

`sales_daily` mart columns used in code: `units_sold`, `gross_revenue`, `gross_margin`, `margin_percent`, `orders_count`, `units_7day_avg`, `units_30day_avg`.

Features:

- Sales KPIs & revenue trend (`/analytics`)
- Detailed sales breakdown & channel performance (`/analytics/sales`)
- Stockout risk (live on‑hand + rolling velocity, risk tiers ≤7/≤14/≤30 days) (`/analytics/stockout-risk`)
- Week in Review consolidated report (`/reports/week-in-review` + CSV export)
- AI Chat with intent recognition (`/chat`) - supports queries like "top margin products", "stockout risk", "slow movers"

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

## Environment Variables

Essential backend environment variables (create `.env` in project root):

```env
# Core Configuration
DATABASE_URL=postgresql://stockpilot:stockpilot_dev@localhost:5432/stockpilot
SECRET_KEY=your-jwt-secret-key
REDIS_URL=redis://localhost:6379/0

# AI Chat Features
OPENAI_API_KEY=your-openai-api-key
CHAT_ENABLED=1
CHAT_LLM_FALLBACK_ENABLED=1
LLM_BASE_URL=http://127.0.0.1:1234  # Alternative local LLM
LLM_MODEL_ID=openai/gpt-oss-20b

# Alerting / Notifications
ALERT_CRON_TOKEN=dev-cron-token
ALERT_EMAIL_FROM=alerts@stockpilot.local
ALERT_EMAIL_TO=
SMTP_HOST=
SMTP_PORT=1025
SMTP_USER=
SMTP_PASS=
ALERT_WEBHOOK_URL=
ALERT_SIGNING_SECRET=
ALERT_DAILY_HOUR=8
```

`ALERT_CRON_TOKEN` secures the internal `POST /api/v1/internal/run-daily-alerts` endpoint.
If SMTP / webhook settings are blank the system logs digest output instead of erroring.

## Reorder Computation (W5)

The purchase suggestions algorithm computes intelligent reorder recommendations using velocity forecasting, lead times, safety stock, and supplier constraints.

### Algorithm Overview

```
horizon_days = max(7, lead_time_days + safety_stock_days)
demand_forecast = chosen_velocity × horizon_days
net_available = on_hand + incoming_units_within_horizon  
raw_shortfall = max(0, demand_forecast - net_available)
```

### Adjustment Sequence

1. **Reorder Point Bump**: If `on_hand < reorder_point`, ensure minimum `reorder_point - on_hand`
2. **MOQ Enforcement**: If quantity > 0 and < MOQ, raise to MOQ
3. **Pack Rounding**: Round up to nearest multiple of `pack_size`
4. **Max Stock Capping**: Limit total coverage ≤ `max_stock_days`
5. **Guardrails**: Skip zero-velocity products unless below reorder point

### Velocity Strategies

- **Latest**: Priority 7d → 30d → 56d (most recent available)
- **Conservative**: Minimum non-zero velocity across time windows

### API Usage

```bash
# Get reorder suggestions
GET /api/v1/purchasing/reorder-suggestions?strategy=latest

# Explain calculation for specific product  
GET /api/v1/purchasing/reorder-suggestions/explain/{product_id}

# Create draft purchase orders
POST /api/v1/purchasing/reorder-suggestions/draft-po
{
  "product_ids": ["uuid1", "uuid2"],
  "strategy": "conservative",
  "auto_number": true
}
```

### Example Calculation

Product: Widget-001
- On hand: 15 units
- Lead time: 10 days
- Safety stock: 5 days  
- Velocity: 2.5 units/day (7d average)
- MOQ: 50 units
- Pack size: 12

**Calculation:**
1. Horizon: max(7, 10+5) = 15 days
2. Demand forecast: 2.5 × 15 = 37.5 units
3. Net available: 15 + 0 = 15 units
4. Raw shortfall: max(0, 37.5 - 15) = 22.5 units
5. MOQ enforcement: max(22.5, 50) = 50 units
6. Pack rounding: ceil(50/12) × 12 = 60 units
7. **Final recommendation: 60 units**

### Frontend Access

Visit `/purchasing/suggestions` to:
- View AI-powered reorder recommendations
- Filter by velocity strategy, coverage days, suppliers
- Select products and create draft POs in one click
- Export suggestions to CSV
- View detailed explanations for each recommendation

## AI Chat System

The chat interface (`/chat`) provides natural language access to business metrics with intent-based routing:

### Supported Queries
- **Top Margin Products**: "top 5 margin products", "most profitable SKUs"
- **Stockout Risk**: "what might run out", "stockout risk next 14 days"
- **Sales Review**: "week in review", "last week summary"
- **Reorder Suggestions**: "what to reorder", "purchase suggestions" 
- **Slow Movers**: "slow moving inventory", "dead stock"
- **Product Details**: "tell me about SKU-001", "sales for Widget-A"

### Technical Implementation
1. **Intent Resolution**: Deterministic keyword matching in `backend/app/services/intent_rules.py`
2. **LLM Fallback**: OpenAI integration for ambiguous queries when enabled
3. **Structured Responses**: JSON data tables with confidence/freshness metadata
4. **Existing Hook Reuse**: Chat responses leverage the same React Query hooks as the UI

---

## Recent Features & Updates

- **AI Chat Interface**: Natural language queries with structured data responses
- **Product Detail Intent**: Get comprehensive product metrics via chat
- **Enhanced Error Handling**: Improved fallback logic for missing analytics data
- **Intent Resolution Service**: Deterministic keyword matching with LLM backup
- **Structured Chat Responses**: Tabular data rendering with metadata

Concise docs intentionally; see code & tests for authoritative patterns.
