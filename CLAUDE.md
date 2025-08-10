# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

StockPilot is a modern inventory management system with analytics and chat capabilities. The architecture follows a clean separation with FastAPI backend, PostgreSQL database, dbt transformations, and Next.js frontend with shadcn/ui components.

## Architecture

**Data Flow:** CSV/Excel/API → FastAPI → PostgreSQL → dbt transforms → API → Next.js Frontend → Analytics/Chat AI

**Stack:**
- Backend: FastAPI + SQLAlchemy + Pydantic (Python)
- Database: PostgreSQL 15 with UUID PKs
- Data Pipeline: dbt for staging/marts transformations
- Frontend: Next.js 15 + TypeScript + Tailwind + shadcn/ui
- Infrastructure: Docker Compose (PostgreSQL + Redis)

## Development Commands

### Local Setup
```bash
# Start infrastructure
docker-compose up -d

# Backend development
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend development  
cd frontend
npm install
npm run dev

# Database connection tests
python backend/host_test.py      # Test from host to Docker PostgreSQL
python backend/container_test.py # Test from container context
```

### Frontend Commands
```bash
cd frontend
npm run dev        # Start development server
npm run build      # Build for production
npm run start      # Start production server
npm run lint       # Run ESLint
```

### Backend Testing & Database
```bash
cd backend
pytest                           # Run all tests
python -m pytest -v             # Run with verbose output
python backend/host_test.py      # Test DB connection from host
python backend/container_test.py # Test DB connection in container context

# dbt operations (requires connection to analytics schema)
cd backend/dbt
dbt run              # Run all models
dbt test             # Run tests
dbt run --models marts  # Run only marts models
```

### Common Operations
```bash
# Reset database with fresh data
docker-compose down -v && docker-compose up -d

# API documentation
open http://localhost:8000/docs

# Frontend
open http://localhost:3000

# Check database connectivity
lsof -i :5432  # Check if local PostgreSQL conflicts with Docker port
```

## Database Architecture

### Core Models (SQLAlchemy)
- **Organization** - Multi-tenant structure
- **Location** - Warehouses/stores per org (type: warehouse/store/virtual)
- **Product** - Catalog with SKU, cost, price, reorder_point
- **InventoryMovement** - Event sourcing for all transactions (in/out/adjust/transfer)
- **Supplier** - Vendor info with lead_time_days, minimum_order_quantity
- **Order/OrderItem** - Sales tracking

### Key Relationships
```
Organization (1) → (many) Locations, Products
Product (1) → (many) InventoryMovements  
Location (1) → (many) InventoryMovements
Order (1) → (many) OrderItems
```

### dbt Models Structure
- **Staging:** `stg_products`, `stg_inventory_movements`, `stg_locations` (views in staging schema)
- **Marts:** `inventory_snapshot_daily`, `stockout_risk`, `velocity_analysis` (tables in marts schema)
- **Schemas:** staging (views), core (tables), marts (analytics tables), seeds (reference data)
- **Target Schema:** analytics (configured in profiles.yml)

## Backend Patterns

### API Structure
```
/api/api_v1/endpoints/
├── products.py - CRUD operations
├── organizations.py - Org management
├── locations.py - Location management
└── inventory.py - Movement tracking
```

### Key Patterns
- **Dependency injection** for database sessions via `get_db()`
- **Pydantic schemas** for request/response validation in `/schemas/`
- **SQLAlchemy models** with Base inheritance in `/models/`
- **Environment config** via Pydantic Settings in `core/config.py`
- **Multi-tenant** design with org_id foreign keys

## Frontend Architecture

### App Router Structure
```
/app/
├── page.tsx - Homepage with navigation cards
├── dashboard/ - KPI dashboard with stockout alerts
├── products/ - Product management and bulk import
└── analytics/ - Reporting interface
```

### Component Patterns
- **shadcn/ui components** in `/components/ui/`
- **React Query hooks** for server state (use-products, use-organizations)
- **Axios client** in `/lib/api.ts` with error handling
- **TypeScript types** in `/types/` matching backend schemas

### Key Files
- `lib/api.ts` - Centralized Axios client with auth interceptors and endpoint definitions
- `hooks/use-*.ts` - Custom React Query hooks (use-products.ts, use-organizations.ts)
- `components/layout/navbar.tsx` - Main navigation component
- `types/index.ts` - TypeScript definitions matching backend schemas
- `contexts/auth-context.tsx` - Authentication state management

## Database Connection

**Connection Strings:**
- **Main App:** `postgresql://postgres:stockpilot_dev@127.0.0.1:5432/stockpilot`
- **dbt Analytics:** `postgresql://stockpilot:stockpilot_dev@127.0.0.1:5432/stockpilot` (schema: analytics)

### Database Users & Permissions
- **postgres** - Superuser for Docker container setup
- **stockpilot** - Application user with SUPERUSER, CREATEDB, CREATEROLE privileges
- Both users share password: `stockpilot_dev`

### Troubleshooting DB Issues
- Local PostgreSQL may conflict with Docker on port 5432
- Kill local instances: `lsof -i :5432` then `kill <PID>`  
- Fresh reset: `docker-compose down -v && docker-compose up -d`
- Test connections: `python backend/host_test.py` and `python backend/container_test.py`
- Database initialized with `backend/init.sql` (creates schema + sample data)

## Important Configuration

### Backend (.env)
```
DATABASE_URL=postgresql://postgres:stockpilot_dev@127.0.0.1:5432/stockpilot
REDIS_URL=redis://localhost:6379/0
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
SECRET_KEY=development-secret-key
OPENAI_API_KEY=your-openai-key-here
```

### Key Configuration Files
- **backend/app/core/config.py** - Pydantic settings with environment variables
- **frontend/src/lib/api.ts** - Axios configuration with auth interceptors
- **docker-compose.yml** - PostgreSQL 15 + Redis 7 setup
- **backend/dbt/profiles.yml** - dbt connection configuration for analytics

### Docker (docker-compose.yml)
- PostgreSQL 15 with init.sql for schema + sample data
- Redis 7 for caching
- Health checks configured

## Data Patterns

### Event Sourcing
All inventory changes recorded as `inventory_movements` with:
- `movement_type`: in/out/adjust/transfer
- Audit trail with timestamp and notes
- Never delete movements, only add adjusting entries

### Multi-tenant Security
- All core tables have `org_id` foreign key to organizations
- Row-level security pattern ready for implementation
- JWT authentication structure in place

### Analytics Pipeline
1. **Raw data** → `inventory_movements`, `products` 
2. **Staging** → dbt models clean and standardize
3. **Marts** → Business logic aggregations (daily snapshots, velocity analysis)
4. **API** → Endpoints serve pre-calculated analytics
5. **Frontend** → Charts and dashboards with real-time data

## Feature Implementation Guidelines

### Adding New Models
1. Create SQLAlchemy model in `/backend/app/models/`
2. Add Pydantic schemas in `/backend/app/schemas/`  
3. Create API endpoints in `/backend/app/api/api_v1/endpoints/`
4. Add frontend types in `/frontend/src/types/`
5. Create React hooks in `/frontend/src/hooks/`

### Adding Analytics
1. Create dbt staging model if needed
2. Build mart model with business logic
3. Add API endpoint to serve data
4. Create frontend components with React Query integration

This codebase emphasizes type safety, clean architecture, and scalable patterns for inventory management with advanced analytics capabilities.