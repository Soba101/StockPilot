# W5 Implementation Plan – Purchase Suggestions & PO Drafting ✅ COMPLETED

**Status**: Implementation complete as of 2025-08-12

## Overview

Week 5 delivers proactive replenishment: compute reorder suggestions from live inventory (movement sums), velocity/forecast signals, supplier lead times, MOQ, safety stock, and pack sizes; then generate draft Purchase Orders in one click. Emphasis: correctness, transparency, additive only.

## Current Foundation (Prereqs ✅)

- Rolling velocities + `forecast_30d_units`
- Suppliers with lead times & MOQ
- Purchasing CRUD (PO + items)
- Stockout risk + velocity strategy logic
- Movement‑based on_hand computation

## Core Deliverables

1. Product & Supplier Data Enhancements

   - New fields: `reorder_point`, `safety_stock_days`, `preferred_supplier_id` (nullable), `pack_size` (default 1), `max_stock_days` (nullable)
   - (Deferred) Multi-supplier pricing table
2. dbt / Analytics Support
   - Mart `reorder_inputs` (products + suppliers + velocity metrics + inbound PO qty + on_hand)
   - Tests: not_null product_id; non_negative numeric fields
3. Reorder Algorithm Service
   - Function `compute_reorder_suggestions(org_id, location_id?, strategy, horizon_days_override?)`
   - Strategies: latest (7d→30d→56d), conservative (min non-zero)
4. API Endpoints
   - GET `/purchasing/reorder-suggestions`
   - POST `/purchasing/reorder-suggestions/draft-po`
   - GET `/purchasing/reorder-suggestions/explain/{product_id}`
5. Frontend UI & Hooks
   - Hook `use-reorder-suggestions.ts`
   - Page `/purchasing/suggestions` (table, filters, badges, selection, CSV export)
   - Explain drawer (computation breakdown)
6. Draft PO Creation Flow
   - Group by supplier; sequential PO numbers
   - Apply MOQ & pack rounding; annotate adjustments
7. Guardrails & Filtering
   - Skip if coverage beyond horizon (unless below reorder point)
   - Cap by `max_stock_days`
   - Zero velocity skip unless below reorder point
8. Transparency
   - Suggestion payload + explanation endpoint (intermediate values)
9. Testing
   - Unit, integration (API), frontend flows
10. Documentation
   - README formulas & example
11. Performance & Indexing

   - Verify/add indices (movements, PO items, POs)

12. Deferred Scope

   - Multi-supplier optimization; advanced forecasting; budget caps; auto-approval; persistent audit

## Algorithm Contract

Inputs:

- on_hand (movement sum)
- incoming_units_within_horizon (open PO items expected within horizon; status pending|ordered)
- chosen_velocity (per strategy)
- lead_time_days, safety_stock_days (default 3 if null)
- horizon_days = lead_time_days + safety_stock_days (min 7 unless override)
- demand_forecast_units = chosen_velocity * horizon_days
- net_available_after_incoming = on_hand + incoming_units_within_horizon
- raw_shortfall = demand_forecast_units - net_available_after_incoming
- recommended_base = max(0, raw_shortfall)

Adjustments (order):

1. Reorder bump (ensure at least `reorder_point - on_hand` if below)
2. MOQ (raise to MOQ if >0 and < MOQ)
3. Pack rounding (ceil to multiple of `pack_size`)
4. Cap by max_stock_days (limit coverage ≤ max)
5. Zero velocity skip unless below reorder point
6. Drop if <1 after adjustments (unless MOQ enforced)

Returned fields: product_id, sku, name, supplier_id, supplier_name, on_hand, incoming, days_cover_current, days_cover_after, recommended_quantity, chosen_velocity, velocity_source, horizon_days, demand_forecast_units, reasons[], adjustments[], optional explanation.

Reason Codes: BELOW_REORDER_POINT, LEAD_TIME_RISK, MOQ_ENFORCED, PACK_ROUNDED, CAPPED_BY_MAX_DAYS, ZERO_VELOCITY_SKIPPED, INCOMING_COVERAGE, NO_VELOCITY.

## Testing Strategy

Unit: velocity selection; MOQ; pack rounding (37→40 pack 20); cap by max_stock_days; reorder bump vs zero velocity; incoming coverage.

Integration: suggestions filtering; draft PO grouping; explanation endpoint; auth scoping.
Frontend: table render; selection; draft creation; explanation drawer.

## Performance Considerations

- Single aggregate query feeding algorithm
- Avoid per-product queries (prefetch joins)
- Target <1s for 1k products (add pre-aggregation/pagination if slower)

## Timeline

Day 1: Product fields + dbt model + tests
Day 2: Service logic + unit tests
Day 3: API endpoints + integration tests
Day 4: Frontend UI + hook + draft PO flow
Day 5: Polish, docs, perf review, CSV export, final QA

## Success Criteria

- Explainable accurate suggestions
- Fast draft PO generation (<1s typical)
- No over-order beyond max_stock_days cap
- Transparent explanations (endpoint + UI)
- All new tests pass; no regressions

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Velocity volatility | Over/under ordering | Conservative strategy; future blended windows |
| Missing supplier data | Skipped suggestions | Reason code + UI flag |
| Rounding inflation | Excess units | Adjustment annotations; later budget constraints |
| Query latency | Slow UX | Pre-aggregate; add indexes |
| Zero velocity edge | False negatives | Reorder bump logic |

## Deferred (Post-W5)

- Multi-supplier & cost optimization
- Advanced forecasting models
- Budget / capital allocation logic
- Auto approval / submission workflows
- Supplier performance scoring loop
- Persistent suggestion/audit table

## Files To Add / Modify

Backend:

```text
app/models/product.py                # new fields
app/schemas/product.py               # extend schemas
app/services/reorder.py              # algorithm & service
app/api/api_v1/endpoints/purchasing_suggestions.py
app/api/api_v1/api.py                # include router
backend/dbt/models/marts/reorder_inputs.sql
backend/dbt/models/marts/schema.yml  # tests for new model
backend/tests/test_reorder.py        # unit tests
backend/tests/test_api_integration.py# endpoint integration
```

Frontend:

```text
frontend/src/hooks/use-reorder-suggestions.ts
frontend/src/app/purchasing/suggestions/page.tsx
frontend/src/components/purchasing/ReorderExplanation.tsx (optional)
```

Docs:
```text
README.md (Reorder computation section)
.env.example (DEFAULT_SAFETY_STOCK_DAYS, DEFAULT_PACK_SIZE optional)
```

## Next Immediate Actions

1. Add product columns + migration/DDL
2. Build `reorder_inputs` + dbt tests
3. Implement service + unit tests
4. Expose endpoints & integrate front-end
5. Document formulas + finalize UX polish

---
Prepared for W5 execution; additive, no breaking changes.
