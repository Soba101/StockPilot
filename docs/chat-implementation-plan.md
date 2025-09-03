# Chat + Trends + Reports — Implementation Plan

This plan turns the current chatbot foundations into a production-grade assistant with three routes: RAG (docs with citations), BI (analytics via tools), and OPEN (general assistant). Scheduled reports remain separate. We keep mart-first, multi-tenant, event-sourced guardrails and use LM Studio for both routing support and narrative composition.

## 0) Current state snapshot (brief)

- Endpoints: Legacy (`/api/v1/chat/query`) and Hybrid (`/api/v1/chat2/query`). Hybrid now supports RAG, BI, and OPEN under `HYBRID_CHAT_ENABLED`.
- Core: Router, Params, Composer, Contracts present; LM Studio client available.
- Reporting: Week-in-Review implemented with CSV/JSON export and tests.
- Alerts: Daily stockout digest + internal cron endpoint + notify (email/webhook).
- Missing: unified FE path to `/chat2/query`, report templating/PDF, scheduler, forecasts.

## 1) Goals and success criteria

- Single entrypoint for chat: `/api/v1/chat2/query` routes RAG/BI/OPEN.
- High-fidelity answers: RAG includes citations; BI returns deterministic metrics (mart-first, org-scoped) with a concise LLM narrative; OPEN is helpful and concise (no uncited numbers).
- On-demand and scheduled reports (HTML/PDF) with charts and narrative.
- Tenant isolation for DB and vector search; read-only analytics; safe defaults.

Acceptance (MVP by Day 14)

- Policy/doc questions return RAG answers with ≥1 citation.
- BI questions like “sales last 30 days” return totals + AOV (mart-first with raw fallback), plus a short narrative.
- OPEN responses are coherent, avoid uncited numeric claims.
- FE uses `/chat2/query` and renders unified schema (RAG citations, BI metrics, or OPEN text).

## 2) 30/60/90-day roadmap (deliverables)

### Day 0–14: MVP “RAG + BI + OPEN”

Deliverables

- Hybrid endpoint: RAG path org-scoped; BI path returns sales summary (totals/orders/units/AOV) for simple periods; OPEN path returns assistant replies.
- Router tuned for RAG vs BI vs OPEN (rules + embeddings + optional LLM tiebreaker).
- Contracts/composer support RAG/BI/OPEN/NO_ANSWER; schema validation wired.
- Frontend switched to `/chat2/query` and renders RAG citations and BI summaries.

Acceptance tests

- Unit: router thresholds/ambiguity for BI vs RAG vs OPEN; composer schema validation.
- Integration: doc questions return citations; BI returns totals for “this year”, “last 30 days”; OPEN handles small talk.

### Day 15–45: Expand BI Tools + Scheduled Reports (separate from chat)

Deliverables

- BI tools (server-side) exposed to chat orchestration:
  - get_sales_summary(period), get_sales_by_day(date), get_top_products(period, k), get_channel_breakdown(period)
  - get_returns_summary(period), get_inventory_snapshot(as_of_date, filters), get_stockouts(period)
- Report service: `make_report(template, payload)` → HTML/PDF (WeasyPrint) + artifact storage reference.
- Templates: Daily Ops, Weekly Exec, Monthly Finance; chart generator (PNG/JSON) + 120-word narrative with 1–2 actions.
- Scheduler: APScheduler/Celery job runner; endpoints to create/run/list schedules; delivery via email/webhook + audit record.

Acceptance tests

- “Email Weekly Exec every Monday 08:00 (SG)” creates a schedule and sends a PDF; audit shows success.
- Reports include KPI header, stockouts, inbound vs due, ageing >120d, narrative, actions.

### Day 46–90: Forecasts, Alerts, RCA (non-chat)

Deliverables

- Forecasts: MA28/ETS per SKU×location → `fct_forecast_daily`.
- Reorder suggestions: `recommended_qty = max(0, demand_lead_time + safety_stock – available)` wired into chat/report.
- Alert subscriptions: create/list/subscribe to conditions (DOC threshold, aged stock ↑, inbound delay); daily digest + links.
- RCA heuristics: Stockouts correlated to demand spike/late inbound/transfer lag; short explanation in responses.

Acceptance tests

- Daily alert digest includes causes and links to detail; forecasts present for selected SKUs; reorder suggestions render.

## 3) Architecture deltas

- Unified entrypoint: FE calls `/chat2/query`; legacy remains for compatibility.
- Hybrid orchestration
  - RAG: Retriever filters/searches by `org_id`; LM Studio composes answer; output → `compose_rag` with citations.
  - BI: Tool-first (mart-first + raw fallback) data retrieval under org_id; LLM composes short narrative from tool outputs only; output → `compose_bi` with metrics card and data provenance.
  - OPEN: LM Studio assistant; no data fetch.
- Contracts: unified schema supports citations and optional metrics cards; no arbitrary SQL in chat.
- Guardrails: org filter; explicit columns; required bounded time range; LIMIT; no mutable stock; avoid uncited numeric claims.

## 4) Work breakdown (tickets)

Data & dbt

- Create `models/marts/kpi_daily.sql` + tests (not null, accepted values).
- Create `models/marts/ageing_buckets.sql` + tests.
- Add weekly/monthly rollups for reports; later: `fct_forecast_daily`.

Backend: Chat

- Router: ensure RAG/BI/OPEN; thresholds + tiebreaker; exemplars (doc_qna/open_chat/bi_intents).
- Params: lightweight period parser (year, last 7/30, last month) → start/end dates.
- Composer/Contracts: support RAG/BI/OPEN/NO_ANSWER; validate via `contracts.validate_output`.
- RAG: org-scoped retriever; LM Studio health check; route metrics.
- BI minimal tool: sales summary (totals/orders/units/AOV) with mart-first fallback.

Backend: Reports

- Module: `services/reports.py` with `make_report` (HTML via Jinja + WeasyPrint/PDFKit), artifact metadata.
- Endpoints: create template, schedule, execute, list history; reuse notify.
- Scheduler: APScheduler (in-process) or Celery (worker + Redis) with retries and idempotency.

Frontend

- Switch hooks to `/chat2/query`; render RAG citations, BI summaries (metrics block), and OPEN assistant text.
- Keep reports UI separate (download PDF/CSV from report endpoints).

Security & governance

- org_id enforced on all DB and vector lookups; RBAC by role/location; log question/SQL/rows/latency/cost.

Evaluation

- 50-question eval set → expected SQL/results; nightly run; in-UI thumbs-up/down.

## 5) Risks and mitigations

- Hallucinations in OPEN: instruct model to avoid numeric claims without citations; prefer RAG/BI when possible.
- Metrics drift: mart-first, versioned SQL, tests; fallback to raw with explicit columns.
- Performance: embeddings/tiebreaker feature flags; semantic cache for prompts; monitor LM Studio latency.
- Multi-tenancy: hard filters by `org_id`; segregate embeddings; avoid leaking org identifiers in messages.

## 6) Try-first milestones (2-week slices)

- Week 1–2: RAG + OPEN MVP; FE switch to /chat2; router thresholds tuned; ingestion polish.
- Week 3–4: report service + Weekly Exec PDF + basic scheduler + narrative tool.

## 7) Definition of Done (phase-by-phase)

- MVP: RAG answers with citations; BI answers for simple periods with totals/AOV + short narrative; OPEN answers coherent; FE renders unified schema variations.
- Reports: schedule executes and delivers PDF; artifacts listed; narrative appears with actions.
- Proactive: forecast table filled; alerts with RCA in daily digest.

---

Appendix A: Tool contracts (initial)

- get_sales_summary(period)
  - Input: { start_date: date, end_date: date, org_id: uuid }
  - Output: { total_revenue: number, total_orders: number, total_units: number, aov: number, tables: string[] }
  - Notes: mart-first (analytics_marts.sales_daily) → raw fallback; require bounded period (≤ 366 days); explicit columns.

- get_sales_by_day(date)
  - Input: { date: date, org_id: uuid }
  - Output: { revenue: number, orders: number, units: number, top_products: { sku: string, name: string, units: number, revenue: number }[] }

- get_top_products(period, k)
  - Input: { start_date: date, end_date: date, k: number ≤ 20, org_id: uuid }
  - Output: { items: { sku, name, units, revenue, margin_percent? }[] }

- get_channel_breakdown(period)
  - Input: { start_date: date, end_date: date, org_id: uuid }
  - Output: { channels: { channel: string, revenue: number, units: number, orders: number, aov: number }[] }

- get_inventory_snapshot(as_of_date, filters)
  - Input: { as_of: date, location_id?: uuid, category?: string, org_id: uuid }
  - Output: { products: { sku, name, on_hand, days_of_cover?, aged_120d? }[] }

---

Appendix: Minimal metric formulas

- DOC = available / NULLIF(avg_daily_demand_28d, 0)
- Fill rate = 1 - (lost_sales / demand) (or fulfilled_qty / requested_qty)
- Turns = COGS / avg_inventory_value
- Ageing buckets = based on current_date - receipt_date per lot
