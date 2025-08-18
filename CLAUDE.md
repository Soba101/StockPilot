# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Backend (FastAPI + Python)
```bash
# Start backend API server
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Run tests
pytest                           # Full test suite (requires running Postgres)
DATABASE_URL=sqlite:///./test.db pytest -q  # Quick tests with SQLite

# dbt analytics pipeline
cd dbt
dbt run && dbt test
```

### Frontend (Next.js + React)
```bash
# Start development server
cd frontend
npm install
npm run dev                      # http://localhost:3000
npm run build                    # Production build
npm run lint                     # ESLint check
```

### Infrastructure
```bash
# Start/reset database and services
docker-compose up -d             # Start Postgres + Redis
docker-compose down -v && docker-compose up -d  # Reset DB (replays init.sql)
```

## Architecture Overview

### Core Principles
- **Multi-tenancy**: Every model includes `org_id`; all queries filter by `claims['org']`
- **Event Sourcing**: Inventory quantities derived from `inventory_movements` table (never store static stock)
- **Analytics-First**: Use dbt marts (`sales_daily`) with graceful fallback to raw tables
- **Single Data Layer**: Frontend uses `src/lib/api.ts` → React Query hooks → components

### Data Flow
```
User Actions → FastAPI CRUD → PostgreSQL + inventory_movements (events) 
→ dbt transforms → Business marts → Analytics endpoints → React Query hooks → UI
```

### Key Components

**Backend Structure:**
- `app/api/api_v1/endpoints/` - All API routes with org-scoped queries
- `app/models/` - SQLAlchemy models (all include `org_id`)
- `app/schemas/` - Pydantic request/response schemas
- `app/core/` - Auth, config, database, hybrid chat system
- `dbt/models/marts/` - Business intelligence transformations

**Frontend Structure:**
- `src/lib/api.ts` - Axios client with auth + dynamic API base URL
- `src/hooks/` - React Query hooks for data fetching
- `src/app/` - Next.js App Router pages and components
- `src/components/ui/` - Enhanced shadcn/ui design system
- `src/components/settings/` - Enterprise settings management system

## Multi-Tenancy & Security

### Authentication Pattern
```python
# All endpoints use org-scoped queries
@router.get("/products")
def get_products(claims: dict = Depends(get_current_claims)):
    return db.query(Product).filter(Product.org_id == claims['org']).all()

# Privileged operations require role check
@require_role("admin")
def delete_product(product_id: str):
    # Admin-only operation
```

### JWT Claims Structure
- `sub`: User ID
- `org`: Organization ID (critical for multi-tenancy)
- `role`: User role (admin, user, etc.)

## Event Sourcing & Inventory

### Inventory Movement Pattern
```python
# ALWAYS insert movements, never update quantities
db.add(InventoryMovement(
    product_id=product_id,
    location_id=location_id,
    quantity=delta,              # Can be negative
    movement_type='adjust',      # in|out|adjust|transfer
    timestamp=datetime.utcnow()
))

# Derive current stock from movements
current_stock = sum(movements.quantity)
```

### Analytics Pattern
```python
# Mart-first with fallback
try:
    # Attempt optimized dbt mart
    rows = db.execute(text("SELECT * FROM analytics_marts.sales_daily")).fetchall()
except Exception:
    # Fallback to raw table calculation
    rows = db.execute(text("SELECT product_id, SUM(quantity) FROM raw_sales")).fetchall()
```

## Settings System Architecture

The settings system uses a modular, enterprise-grade architecture:

### Settings Layout System
- `SettingsLayout` - Tabbed navigation with permission-based visibility
- `SettingsForm` - Auto-save forms with sectioned organization
- Collapsible sections with validation and error handling

### Component Pattern
```typescript
// Settings sections follow this interface
interface SettingsSection {
  id: string
  title: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  component: React.ComponentType
  permissions?: string[]
  badge?: string
}
```

### Form Validation Pattern
- React Hook Form + Zod schemas for type-safe validation
- Auto-save with 2-second debouncing
- Section-based error reporting
- Optimistic UI updates

## AI Chat System

### Dual Chat Architecture
- **Legacy**: `/api/v1/chat/query` - Intent rules → LLM fallback
- **Hybrid**: `/api/v1/chat2/query` - Enhanced routing with feature flags

### Intent Resolution
```python
# Deterministic intent matching in app/services/intent_rules.py
if any(term in query.lower() for term in ["top margin", "most profitable"]):
    return "top_margin_products"
```

### Structured Responses
Chat responses return JSON with tabular data and metadata:
```json
{
  "response": "Here are your top margin products:",
  "data": [...],
  "confidence": "high",
  "data_freshness": "real-time"
}
```

## Development Patterns

### Adding New Features

**Backend Checklist:**
1. SQLAlchemy model in `app/models/` with `org_id` and `BaseModel` inheritance
2. Pydantic schemas in `app/schemas/`
3. API endpoint in `app/api/api_v1/endpoints/` with org filtering
4. Register router in `app/api/api_v1/api.py`
5. Add integration tests with JWT token minting

**Frontend Checklist:**
1. API method in `src/lib/api.ts`
2. React Query hook in `src/hooks/use-<feature>.ts`
3. Component/page in `src/app/<feature>/`
4. Never call axios directly in components

### Analytics Extensions
1. Create/extend dbt model in `dbt/models/marts/`
2. Add mart-first endpoint with fallback logic
3. Use snake_case in SQL, camelCase in TypeScript
4. Maintain backward compatibility for existing JSON keys

## Enhanced UI Components

### Design System
- Built on Radix UI primitives with shadcn/ui patterns
- Tailwind CSS with custom design tokens for inventory-specific colors
- CVA (Class Variance Authority) for component variants

### Key Enhanced Components
- `StatusBadge` - Inventory-specific status indicators
- `StockLevelBar` - Visual stock level representation
- `DataTable` - Advanced tables with TanStack Table
- `FileUpload` - Drag-and-drop with validation
- `SettingsForm` - Enterprise form management

## Testing Strategy

### Backend Tests
```bash
# Integration tests require running API server
uvicorn app.main:app --reload &
pytest tests/test_integration/

# Unit tests with SQLite
DATABASE_URL=sqlite:///./test.db pytest tests/test_unit/
```

### Frontend Tests
- Component tests with Jest/React Testing Library
- End-to-end tests for critical workflows
- Accessibility compliance (WCAG 2.1 AA)

## Environment Configuration

### Required Backend Variables
```env
DATABASE_URL=postgresql://stockpilot:stockpilot_dev@localhost:5432/stockpilot
SECRET_KEY=your-jwt-secret-key
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=your-openai-api-key
CHAT_ENABLED=1
```

### Frontend Configuration
- `NEXT_PUBLIC_API_BASE` - Override API base URL
- Dynamic API resolution for LAN access support
- Next.js rewrites for `/api/*` → `http://localhost:8000/api/v1/*`

## Critical Constraints

### Never Do
- Store computed inventory quantities (always derive from movements)
- Skip `org_id` filtering in queries
- Rename existing JSON response keys (only append new fields)
- Leak foreign organization data
- Use broad `except:` clauses without specific error handling

### Always Do
- Filter all queries by `claims['org']`
- Use explicit column lists in SQL
- Maintain mart-first analytics pattern with fallbacks
- Follow event sourcing for inventory changes
- Use TypeScript interfaces for new components

## Recent Enhancements

### Settings Page Modernization (Current)
- Transformed basic demo settings into enterprise-grade interface
- Modular tabbed navigation with permission-based sections
- Auto-save forms with comprehensive validation
- Organization profile management with file uploads
- Foundation for user management, permissions, and system configuration

### Reorder Algorithm (W5)
Advanced purchase suggestions using velocity forecasting, lead times, and supplier constraints with MOQ/pack size enforcement.

### AI Chat Integration
Natural language queries with intent-based routing, structured responses, and existing hook reuse for consistent data access.

## Current Implementation Status

**Completed**: Settings foundation (25% of enhancement plan)
**In Progress**: User management interface
**Next Priority**: Permission matrix, inventory configuration, system settings

The architecture supports rapid feature development with consistent patterns for authentication, data access, validation, and UI composition.