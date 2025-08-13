StockPilot — Project Plan (Markdown)

One-liner: Inventory + sales analytics with a trustworthy chat interface that turns data into decisions.

1) Goals & Non-Goals

Goals
	•	Single source of truth for stock, sales, and purchasing.
	•	Self-serve insights: “Ask a question, get a chart + next best action.”
	•	Reduce stockouts and overstock with forecasting + auto-PO drafts.

Non-Goals (MVP)
	•	Full ERP (GL, payroll, tax).
	•	Complex manufacturing (multi-level BOM with routing).
	•	Real-time IoT bin sensors.

⸻

2) Target Users & JTBD

Users
	•	Store/warehouse ops leads, purchasing managers, founders/GM, finance analyst.

Jobs-to-be-done
	•	“Know what to reorder today and why.”
	•	“Explain last week’s performance by SKU/channel.”
	•	“Prevent stockouts for top movers.”
	•	“Close month with accurate COGS and margin.”

⸻

3) MVP Scope
	•	Ingestion: CSV/Excel upload, Shopify/Woo, Stripe, simple POS REST.
	•	Inventory: On-hand, allocated, available; reorder points; lead times; FEFO optional.
	•	Dashboards: Sales, margin, stockouts, aging inventory, forecast (30 days).
	•	Alerts: “12 SKUs will stock out in ≤7 days.”
	•	Chat to Insight (guardrailed): NL → parameterized metrics; show query + calculation method.
	•	Purchase Suggestions: Draft PO qty = forecast demand – available + safety stock, bounded by MOQ.

⸻

4) Success Metrics (North Stars)
	•	↓ stockout events ≥20% in 60 days.
	•	↓ weekly reporting time 2h → 10m.
	•	≥ 80% “trust” on chat answers (thumbs-up rate).
	•	≥ 50% adoption of auto-generated PO drafts.

⸻

5) Data Model (Canonical)

Tables
	•	products(product_id, sku, name, category, cost, price, uom, shelf_life_days?)
	•	locations(location_id, name, type)
	•	inventory_movements(id, product_id, location_id, qty, type[in|out|adjust|transfer], ref, ts)
	•	orders(order_id, channel, status, ordered_at, fulfilled_at, location_id)
	•	order_items(order_item_id, order_id, product_id, qty, unit_price, discount)
	•	suppliers(supplier_id, name, lead_time_days, moq, currency)
	•	purchase_orders(po_id, supplier_id, status, created_at, expected_at)
	•	purchase_order_items(poi_id, po_id, product_id, qty, unit_cost)
	•	batches(batch_id, product_id, lot, expiry_at) (if FEFO)

Derived Views / Marts
	•	inventory_snapshot_day(product_id, location_id, date, on_hand, allocated, available)
	•	sales_daily(product_id, location_id, date, units, net_rev, gross_margin)
	•	velocity(product_id, location_id, daily_units_8wk_ma)
	•	days_to_stockout = available / max(velocity, ε)

⸻

6) Architecture (Lean)

flowchart LR
A[Sources: CSV, Shopify, Woo, POS, Stripe] --> B[Ingestion Service]
B --> C[(Postgres)]
C --> D[dbt transforms -> marts]
D --> E[API (FastAPI)]
E --> F[Web App (React)]
E --> G[Chat Orchestrator (LLM + Tools)]
G --> E
F --> E

Notes
	•	Dev analytics: DuckDB local; Prod: Postgres.
	•	dbt tests for schema + freshness.
	•	Row-level security by location; role-based masking for costs.

⸻

7) Chat Design (Guardrails)

Intents (templates → SQL/metrics)
	•	top_skus_by_margin(period, n, channel?, location?)
	•	stockout_risk(horizon_days, location?)
	•	week_in_review(location?, channel?)
	•	reorder_suggestions(location?)

Response Contract
	•	Title + short answer
	•	Table/chart
	•	“How computed” (definition + query link)
	•	Confidence + data freshness badge
	•	Optional next step (e.g., “Create PO draft”)

Safety
	•	No free-form SQL on raw DB.
	•	Only metric endpoints; hard fail on undefined fields.
	•	Unit tests for each template.

⸻

8) Core Screens
	•	Home: KPIs + freshness + issues (stockout risks, stale data).
	•	Inventory: On-hand/available, aging, FEFO batches, cycle counts.
	•	Sales: Trend, mix (SKU/channel), margin waterfall.
	•	Purchasing: Suggestions, POs, supplier performance.
	•	Chat: Prompt, history, export, “show query.”

⸻

9) Alerts & Automations
	•	Daily 8am: Stockout risks (horizon 7–14d).
	•	Weekly Mon 9am: “Last week in 60 seconds” digest.
	•	Event-based: When on_hand < reorder_point, when lead_time slips.

⸻

10) Non-Functional Requirements
	•	Perf: P95 dashboard < 2s on 100k orders / 10k SKUs.
	•	Uptime: 99.5% (MVP), error budget tracked.
	•	Security: JWT/OAuth, RLS, encrypted at rest, audit log of queries.
	•	Privacy: SOC2-ready roadmap, least-privilege connectors.

⸻

11) Milestones & Timeline (8 Weeks)

W1 — Foundations
	•	Define schema & dbt project
	•	CSV/Excel importer (idempotent upserts)
	•	Auth, orgs, roles

W2 — Inventory Truth
	•	Movements pipeline & daily snapshot
	•	Inventory screen (search, filters)
	•	Basic aging & cycle count export

W3 — Sales & Metrics
	•	Orders ingestion (Shopify first)
	•	Sales daily mart + KPI cards
	•	“Week in Review” canned report

W4 — Forecast & Alerts
	•	Velocity calc (8-week MA)
	•	Days-to-stockout & alert engine
	•	Email/webhook notifications

W5 — Purchase Suggestions
	•	Reorder algorithm (MOQ, lead time, safety)
	•	PO draft UI + export (CSV/PDF)

W6 — Chat v1 (Guardrailed)
	•	Intent templates (4)
	•	Orchestrator calling metric API
	•	“Show query” + freshness labels

W7 — Polish & Hardening
	•	dbt tests, data contracts, seed demo data
	•	Role-based masking for cost
	•	Performance passes on sample large tenant

W8 — Pilot & Feedback
	•	3 design partners onboarded
	•	Success metric dashboard
	•	Iterate on top 5 asks

⸻

12) Demo Script (10 minutes)
	1.	Import sample CSV → freshness badge updates.
	2.	Show stockout risks → open one SKU → create PO draft.
	3.	Ask chat: “Which SKUs will stock out in 14 days at Tampines?” → table + “how computed.”
	4.	Run “Week in Review” → export PDF.

⸻

13) Pricing (Draft)
	•	Starter: $79/mo — 1 location, basic connectors, alerts.
	•	Pro: $299/mo — multi-location, purchase suggestions, batch/FEFO.
	•	Plus: Usage add-on per order or per extra location.
	•	Implementation: Fixed fee for vertical setups.

⸻

14) Risks & Mitigations
	•	Dirty data → reconciliation views, variance reports, source freshness.
	•	LLM hallucination → metric-only endpoints, require definitions in responses.
	•	Connector drift → dbt tests + versioned contracts, fail loud with guidance.
	•	Adoption → embed “Show me how” tours; weekly email digest.

⸻

15) Open Questions
	•	Which vertical first? (e.g., cafés with expiries, clinics with FEFO, DTC brands)
	•	Required channels (Shopify? retail POS?)
	•	Do we need lot/batch tracking in MVP?
	•	Which export formats matter most (XLSX, PDF, PO to supplier email/API)?

⸻

16) Naming & Branding
	•	Working name: StockPilot (alt: Opsight, StockSense).
	•	Chat persona label: Pilot Chat (clear separation from analytics UI).

⸻

Next Actions
	•	Pick vertical + top 5 user problems.
	•	Confirm source systems; finalize schema (above).
	•	Lock W1–W2 deliverables; schedule 3 pilot users.