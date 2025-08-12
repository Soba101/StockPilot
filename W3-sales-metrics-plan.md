# W3 Implementation Plan - Sales & Metrics (Hybrid Approach)

## Overview
W3 focuses on completing the core foundation while building advanced sales analytics and metrics capabilities. This hybrid approach ensures a rock-solid inventory system before adding external integrations, following Option C strategy.

**Current Status**: We have real sales data (8 orders), analytics working, and KPI dashboards functional. Need to complete foundation and enhance sales reporting.

---

## Phase 1: Foundation Completion (Priority 1 - 15-20 mins)

### 1.1 Complete React Query Integration ⚡ HIGH PRIORITY
**Status**: 🔲 In Progress - Fixed `useProducts` and `useInventory`, need to audit remaining hooks

**Backend APIs (Already Working):**
- ✅ Products API returning real data (30 products)  
- ✅ Inventory summary API working (60 stock items across 3 locations)
- ✅ Authentication API functional
- ✅ Locations API working (3 locations)

**🔴 CRITICAL: Fix Dashboard Hook Simulated Data**
- 🔲 **Fix `use-dashboard.ts`** - Currently uses `Math.random()` for stock levels!
  - Replace: `currentStock: Math.floor(Math.random() * 100) + 1`
  - With: Real inventory data from inventory summary API
  - Fix: `recentActivity` simulated data with real inventory movements
- 🔲 **Fix `use-analytics.ts`** - Currently simulates sales revenue
  - Replace: `totalRevenue = totalStockValue * 0.6` (fake calculation)
  - With: Real order data from database (8 real orders available)
  - Fix: Simulated recent sales with real order history

**Frontend Hooks to Audit:**
- 🔲 **Check `use-locations.ts`** - May need similar fix as useProducts
- 🔲 **Verify all pages load** - Dashboard, Products, Inventory, Analytics

**Files to Review:**
```
/frontend/src/hooks/use-dashboard.ts  ← CRITICAL FIX
/frontend/src/hooks/use-analytics.ts  ← CRITICAL FIX
/frontend/src/hooks/use-locations.ts
/frontend/src/app/dashboard/page.tsx
/frontend/src/app/chat/page.tsx     ← Basic chat responses
```

### 1.2 Fix Purchasing Page Mock Data 🔲 HIGH PRIORITY
**Current Issue**: Purchasing page shows mock purchase orders instead of real supplier/order data

**Backend Tasks:**
- 🔲 **Create Purchase Order API endpoints** (`/app/api/api_v1/endpoints/purchasing.py`)
  - GET `/api/v1/purchase-orders/` - List POs with filters
  - POST `/api/v1/purchase-orders/` - Create new PO
  - GET `/api/v1/purchase-orders/{id}` - Get PO details
  - PUT `/api/v1/purchase-orders/{id}/status` - Update PO status
- 🔲 **Create PO schemas** (`/app/schemas/purchasing.py`)
- 🔲 **Add PO endpoints to main API router**

**Frontend Tasks:**
- 🔲 **Update purchasing page** (`/frontend/src/app/purchasing/page.tsx`)
  - Replace mock data with real API calls
  - Add `use-purchasing.ts` hook
  - Connect to real supplier and PO data
- 🔲 **Create PO creation form** - New PO with supplier selection
- 🔲 **Test PO workflow** - Create, view, update purchase orders

### 1.3 Fix Chat Page Mock Responses 🔲 MEDIUM PRIORITY
**Current Issue**: Chat page shows hardcoded demo responses instead of inventory insights

**Frontend Tasks:**
- 🔲 **Update chat responses** (`/frontend/src/app/chat/page.tsx`)
  - Replace: `Insight: Blue Widget is trending` (hardcoded)
  - With: Real inventory insights (low stock alerts, recent movements)
  - Add: Basic inventory query responses (stock levels, reorder alerts)
- 🔲 **Connect to existing APIs** - Use inventory summary and movements APIs
- 🔲 **Add basic query parsing** - Simple keyword matching for inventory questions

### 1.4 Test Core CRUD Operations 🔲 HIGH PRIORITY  
**Goal**: Ensure all basic inventory operations work flawlessly

**Product Management:**
- 🔲 **Test Add Product** - Create new product via form
- 🔲 **Test Edit Product** - Update existing product details  
- 🔲 **Test Delete Product** - Remove product (with safeguards)
- 🔲 **Test Bulk Import** - CSV product import functionality

**Inventory Management:**
- 🔲 **Test Stock Adjustments** - Increase/decrease inventory levels
- 🔲 **Test Stock Transfers** - Move inventory between locations
- 🔲 **Test Inventory Movements** - View movement history
- 🔲 **Test Low Stock Alerts** - Verify reorder point notifications

**Error Handling:**
- 🔲 **Test API failures** - How frontend handles backend errors
- 🔲 **Test validation** - Form validation and error messages
- 🔲 **Test authentication** - Token expiry and refresh

---

## Phase 2: W3 Sales & Metrics Features

### 2.1 Enhanced Sales Daily Mart 🔲 MEDIUM PRIORITY
**Current**: We have real orders and basic analytics. Need to enhance with proper dbt mart.

**dbt Pipeline:**
- 🔲 **Create `sales_daily.sql` mart** in `/backend/dbt/models/marts/`
  - Daily aggregation: product_id, location_id, date, units, revenue, margin
  - Handle multiple channels (online, pos, phone)
  - Calculate gross margin from cost and price
- 🔲 **Create staging model** `stg_orders.sql` and `stg_order_items.sql`
- 🔲 **Add dbt tests** for data quality (non-null, relationships, accepted values)
- 🔲 **Schedule daily dbt runs** (manual trigger for MVP)

**Backend API:**
- 🔲 **Create sales analytics endpoint** (`/api/v1/analytics/sales`)
  - Daily/weekly/monthly sales trends
  - Channel breakdown (online vs pos vs phone)  
  - Product performance metrics
- 🔲 **Enhance existing analytics endpoint** with sales data from mart

### 2.2 "Week in Review" Report 🔲 MEDIUM PRIORITY
**Goal**: Automated weekly summary report as specified in original W3 plan

**Backend:**
- 🔲 **Create report generation endpoint** (`/api/v1/reports/week-in-review`)
  - Parameter: start_date (defaults to last week)
  - Returns: sales summary, top products, inventory changes, alerts
- 🔲 **Create report templates** for consistent formatting
- 🔲 **Add export functionality** (PDF/CSV generation)

**Frontend:**
- 🔲 **Create reports page** (`/frontend/src/app/reports/page.tsx`)
  - Week in Review generator
  - Historical reports list
  - Export/download functionality
- 🔲 **Add reports navigation** to main navbar
- 🔲 **Create report components** - Reusable chart and table components

### 2.3 Advanced KPI Dashboard Enhancements 🔲 MEDIUM PRIORITY
**Current**: Basic KPIs working. Need to enhance with W3 features.

**Enhanced Metrics:**
- 🔲 **Add velocity calculations** - 8-week moving average sales per product
- 🔲 **Add days-to-stockout** - Forecast when items will run out
- 🔲 **Add margin analysis** - Gross margin trends by product/category
- 🔲 **Add channel performance** - Revenue by sales channel

**Dashboard Improvements:**
- 🔲 **Add time period selectors** - 7/30/90 day views
- 🔲 **Add drill-down capability** - Click KPIs to see details
- 🔲 **Add real-time refresh** - Auto-refresh every 5 minutes
- 🔲 **Add export functionality** - Download dashboard as PDF

---

## Phase 3: Integration Preparation

### 3.1 External Integration Schema Prep 🔲 LOW PRIORITY
**Goal**: Prepare for future Shopify/external order ingestion

**Database Schema:**
- 🔲 **Add external_ref fields** to orders table for Shopify order IDs
- 🔲 **Create integration_sources** table to track data origins
- 🔲 **Add data quality flags** (is_reconciled, data_source, etc.)

**API Preparation:**
- 🔲 **Create webhook endpoints** for future Shopify integration
- 🔲 **Add order ingestion validation** - Detect and handle duplicates
- 🔲 **Create reconciliation reports** - Compare internal vs external data

### 3.2 Performance & Quality 🔲 LOW PRIORITY
**Goal**: Ensure system can handle larger datasets (per W3 requirements)

**Performance:**
- 🔲 **Add database indexing** for common queries
- 🔲 **Optimize API response times** - Target <2s for dashboard
- 🔲 **Add caching layer** - Redis for frequently accessed data
- 🔲 **Test with larger datasets** - 100k orders, 10k products

**Data Quality:**
- 🔲 **Expand dbt tests** - Freshness, volume, schema tests
- 🔲 **Add data contracts** - API schema validation
- 🔲 **Create monitoring** - Track API errors and performance
- 🔲 **Add audit logging** - Track all data changes

---

## Success Criteria

### Phase 1 Complete When:
- ✅ All pages load without errors
- ✅ All CRUD operations work (create, edit, delete products)
- ✅ Inventory movements function (adjustments, transfers)
- ✅ Purchasing page shows real data (no mock data)
- ✅ Authentication flows work seamlessly

### Phase 2 Complete When:
- ✅ dbt sales daily mart runs successfully
- ✅ "Week in Review" report generates correctly
- ✅ Advanced KPIs display (velocity, days-to-stockout)
- ✅ All reports export properly (PDF/CSV)

### Phase 3 Complete When:
- ✅ System performs well with sample large data
- ✅ All dbt tests pass
- ✅ External integration schema ready
- ✅ Monitoring and logging in place

---

## Technical Implementation Notes

### Key Files to Create/Modify:

**Backend:**
```
/app/api/api_v1/endpoints/purchasing.py    # New PO endpoints
/app/schemas/purchasing.py                 # PO schemas  
/backend/dbt/models/marts/sales_daily.sql  # Sales mart
/app/api/api_v1/endpoints/reports.py       # Reports API
```

**Frontend:**
```
/frontend/src/hooks/use-purchasing.ts      # PO data hook
/frontend/src/app/purchasing/page.tsx      # Fix mock data
/frontend/src/app/reports/page.tsx         # New reports page
/frontend/src/hooks/use-locations.ts       # Fix if needed
```

### Testing Strategy:
1. **Manual Testing**: Each CRUD operation and page load
2. **API Testing**: All endpoints with curl/Postman  
3. **Data Quality**: dbt test runs and validation
4. **Performance**: Dashboard load times and responsiveness

### Estimated Timeline:
- **Phase 1**: 15-20 minutes (critical path)
- **Phase 2**: 45-60 minutes (core W3 features)
- **Phase 3**: 30-45 minutes (polish and prep)

**Total**: ~2-2.5 hours for complete W3 implementation

---

## Next Steps

1. **Start with Phase 1.1** - Audit and fix React Query hooks
2. **Fix purchasing page** - Replace mock data with real APIs  
3. **Test all CRUD operations** - Ensure solid foundation
4. **Move to Phase 2** - Build W3 sales and metrics features
5. **Polish in Phase 3** - Performance and integration prep

This approach ensures you have a bulletproof inventory system while delivering the W3 sales & metrics capabilities from your original project plan.