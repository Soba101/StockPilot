# W2 Foundation Implementation Plan - Inventory Truth

## Overview
W2 focuses on building the core inventory management system with movement tracking, daily snapshots, and comprehensive inventory screens. This establishes the "single source of truth" for stock levels across all locations.

## Core Deliverables

### 1. Inventory Movement Pipeline ✅ (Partially Complete)
**Backend:**
- ✅ InventoryMovement model exists with proper schema
- ✅ dbt staging model `stg_inventory_movements.sql` ready
- ✅ dbt mart `inventory_snapshot_daily.sql` for daily snapshots
- 🔲 **Create inventory movements API endpoints** (`/api/v1/inventory/`)
  - POST `/movements` - Record new inventory transactions
  - GET `/movements` - List movements with filtering (product, location, date range)
  - GET `/movements/{id}` - Get specific movement details
- 🔲 **Create inventory movement schemas** in `app/schemas/inventory.py`
- 🔲 **Test dbt pipeline** - Ensure staging and marts models run correctly

### 2. Daily Inventory Snapshots
**dbt & Analytics:**
- ✅ Basic daily snapshot mart exists
- 🔲 **Enhance snapshot calculation** to handle:
  - Proper allocated quantity logic (reserved for orders)
  - Available quantity = on_hand - allocated
  - Reorder point comparisons
- 🔲 **Create inventory summary API endpoint** (`/api/v1/inventory/summary`)
  - Current stock levels by location
  - Low stock alerts (below reorder point)
  - Out of stock items
- 🔲 **Schedule daily dbt runs** (manual for MVP, automated later)

### 3. Inventory Management Frontend
**New Pages & Components:**
- 🔲 **Create inventory main page** (`/app/inventory/page.tsx`)
  - Current stock levels table with search/filter
  - Quick actions: adjust stock, transfer between locations
  - Low stock and out of stock alerts
- 🔲 **Create inventory movement history** (`/app/inventory/movements/page.tsx`)
  - Filterable movement log (by product, location, type, date)
  - Movement details with references and notes
- 🔲 **Create stock adjustment form** (`/app/inventory/adjust/page.tsx`)
  - Quick stock adjustments with reason codes
  - Bulk adjustment via CSV import
- 🔲 **Create transfer form** (`/app/inventory/transfer/page.tsx`)
  - Transfer stock between locations
  - Transfer history and tracking

### 4. Inventory APIs & Hooks
**Backend APIs:**
- 🔲 **Movement recording** - POST with validation for movement types
- 🔲 **Current stock query** - GET with location/product filtering
- 🔲 **Movement history** - GET with pagination and filters
- 🔲 **Stock adjustment shortcuts** - POST for common operations

**Frontend Hooks:**
- 🔲 **`use-inventory.ts`** - Current stock levels and summaries
- 🔲 **`use-movements.ts`** - Movement history and creation
- 🔲 **`use-stock-adjustments.ts`** - Stock adjustment operations

### 5. Aging & Cycle Count Exports
- 🔲 **Create aging report** - Products by days since last movement
- 🔲 **Cycle count export** - CSV/Excel export for physical counts
- 🔲 **Variance reconciliation** - Compare physical vs system counts

## Technical Implementation Details

### Database Schema Updates
- ✅ InventoryMovement model complete
- 🔲 Add indexes on (product_id, location_id, timestamp) for performance
- 🔲 Add constraints for movement_type enum values

### dbt Models Enhancement
- 🔲 Add data quality tests to `schema.yml`
- 🔲 Create `inventory_aging.sql` mart for aging analysis
- 🔲 Create `low_stock_alerts.sql` mart for reorder notifications

### Frontend Navigation Updates
- 🔲 Add "Inventory" navigation item to main navbar
- 🔲 Update dashboard to show inventory KPIs (stock value, low stock count)
- 🔲 Add inventory quick actions to dashboard

## Success Criteria
- ✅ All inventory movements recorded with audit trail
- ✅ Daily snapshots calculate accurate stock levels
- ✅ Inventory screen shows real-time stock across all locations
- ✅ Users can perform stock adjustments and transfers
- ✅ Aging and cycle count reports exportable
- ✅ Low stock alerts visible on dashboard and inventory pages

## Testing Strategy
- Unit tests for movement API endpoints
- Integration tests for dbt pipeline
- Frontend testing for inventory operations
- Manual testing of stock adjustment flows

## Dependencies & Risks
- **dbt setup** - Ensure analytics database connection works
- **Performance** - Large movement tables may need partitioning
- **Data integrity** - Movement validation to prevent negative stock
- **Multi-location** - Proper org/location scoping for movements

This plan builds the foundation for accurate inventory tracking that will support sales analytics (W3) and forecasting (W4).