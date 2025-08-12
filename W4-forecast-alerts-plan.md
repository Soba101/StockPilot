# W4 Implementation Plan – Forecast & Alerts

## Overview

Week 4 delivers forward‑looking inventory intelligence: multi‑horizon velocity (adding 56‑day MA), improved days‑to‑stockout logic, and a lightweight alert engine that emits daily stockout risk digests (email/webhook) with idempotent execution. Scope intentionally lean (no persistent alert log yet) to unblock proactive workflows in later weeks (purchase suggestions, automation).

## Current Foundation (Prereqs ✅)

- Rolling 7/30‑day velocity & margin available via `sales_daily` mart.
- Stockout risk endpoint (`/api/v1/analytics/stockout-risk`) computes on‑hand dynamically from movements.
- Week in Review & sales analytics endpoints operational.

---

## Core Deliverables (Status: Completed 2025-08-12)

All scope items below have been delivered and merged except the explicitly optional frontend "Last alerts run" badge (left unchecked and deferred). APScheduler remains deferred per plan.

1. Velocity Expansion & Forecast
   - [x] Add 56‑day moving average column `units_56day_avg` to `sales_daily` mart.
   - [x] Add computed `forecast_30d_units` (simple: chosen_velocity * 30) for downstream PO drafting.
2. Enhanced Stockout Risk API
   - [x] Extend `/analytics/stockout-risk` to expose `velocity_source`, support `velocity_strategy` param (`latest|conservative`).
   - [x] Prioritize velocity: latest => 7d > 30d > 56d; conservative => min(non‑zero of 7/30/56).
   - [x] Include `units_56day_avg` when available; keep response backward compatible.
3. Days‑to‑Stockout Logic Upgrade
   - [x] Uniform formula: `on_hand / max(chosen_velocity, ε)`; null if no non‑zero velocity.
   - [x] Maintain risk tiers: ≤7 high, ≤14 medium, ≤30 low, else none. Preserve reorder point bump (medium if below reorder point).
4. Alert Engine (Daily Digest)
   - [x] Service function to compute products with `days_to_stockout <= 14` (separate lists high (≤7) & medium (≤14)).
   - [x] Summarize: counts, top 5 soonest (sku, name, on_hand, days_to_stockout, velocity_source).
   - [x] Idempotency (per org, per date) via Redis key OR in‑process memory fallback.
5. Notification Channels
   - [x] Email channel (graceful no‑SMTP fallback logs output).
   - [x] Generic webhook POST with optional HMAC signature header.
6. Scheduling / Invocation
   - [x] Internal secured endpoint `POST /internal/run-daily-alerts` (Bearer token env `ALERT_CRON_TOKEN`).
   - [x] Document cron usage; optional later APScheduler (deferred).
7. Configuration & Env
   - [x] Add new settings (see Configuration section) to `core/config.py` & example env doc.
8. Testing & Quality
   - [x] dbt tests for new columns (non‑negative, schema presence).
   - [x] Unit tests: velocity selection, risk calculation, alert generation, idempotency, notification dispatch.
   - [x] Integration: stockout API extended fields; internal endpoint auth & execution path.
9. Frontend Surfacing (Minimal)
   - [x] Extend `use-stockout-risk` types with `velocity_source`.
   - [ ] Add small “Last alerts run: HH:MM” badge placeholder (optional endpoint or manual config—deferred).

---

## Technical Implementation Details

### 1. dbt Changes
File: `backend/dbt/models/marts/sales_daily.sql`

Add 56‑day moving average window column:

```sql
avg(units_sold) over (
   partition by org_id, product_id
   order by sales_date
   rows between 55 preceding and current row
) as units_56day_avg,
```

Add forecast column (simple linear projection):

```sql
coalesce(units_7day_avg, units_30day_avg, units_56day_avg) * 30 as forecast_30d_units,
```

Tests (`schema.yml`): presence + non_negative for new columns; allow null when <56 days of history.

### 2. API Enhancements (`analytics.py`)

Stockout risk endpoint:

- Query param `velocity_strategy` (default `latest`).
- Compute chosen velocity & expose `velocity_source` (`7d|30d|56d|none`).
- Include `units_56day_avg` & `forecast_30d_units` without removing existing fields (additive).

### 3. Alert Service (`alerts.py`)

New module: `backend/app/services/alerts.py`

Responsibilities:

- Fetch on‑hand + velocities in one aggregate query (reuse existing movement sum logic).
- Derive `days_to_stockout` using strategy.
- Select products with `days_to_stockout <= 14` partitioned into high (≤7) and medium (≤14).
- Idempotency per org/date: key pattern `alerts:daily:{org_id}:{YYYYMMDD}` (Redis preferred, fallback in‑memory set).
- Build digest payload (counts + top 5 soonest).

Pseudo‑signature:

```python
def generate_daily_stockout_digest(db: Session, org_id: UUID, strategy: str) -> DailyDigest:
   ...
```

### 4. Notifications (`notify.py`)

Module: `backend/app/services/notify.py`

- Email: use SMTP settings; if missing, log structured message instead of failing.
- Webhook: POST JSON; optional `X-Signature` HMAC (SHA256) using `ALERT_SIGNING_SECRET` over body.
- Unified interface `dispatch_digest(digest, channels: list[str])` returning status list.

### 5. Internal Endpoint (`internal.py`)

File: `backend/app/api/api_v1/endpoints/internal.py`
Route: `POST /internal/run-daily-alerts`
Auth: `Authorization: Bearer <ALERT_CRON_TOKEN>` (compare to config value).

Flow:

1. Validate token; 401 on mismatch.
2. Enumerate orgs.
3. For each org, attempt idempotency check; skip if already processed.
4. Generate digest; dispatch channels; tally results.
5. Return JSON `{ date, orgs_processed, alerts_sent_total, per_org: [...] , already_ran }`.

If all orgs already processed, set `already_ran=true` (still 200 for simpler automation).

### 6. Configuration
New env vars (document in README & sample):

```env
ALERT_EMAIL_FROM=alerts@stockpilot.local
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASS=
ALERT_WEBHOOK_URL=
ALERT_SIGNING_SECRET=
ALERT_DAILY_HOUR=08        # hour (24h) cron should invoke endpoint
```

Extend `core/config.py` with Pydantic settings + safe defaults (empty strings / None) and parsed int for hour.

### 7. Performance Notes
On‑hand aggregation remains runtime sum of movements; acceptable for current scale. Future: consider materialized daily inventory snapshot if latency grows. Ensure indices exist: `(product_id, movement_type)`, `(org_id, product_id)`.

---

## Testing Strategy

dbt: run & test ensuring new columns present; create synthetic data to cover <56 and ≥56 day windows.

Unit Tests (new `backend/tests/test_alerts.py`):

- Velocity strategy selection (latest vs conservative) matrix.
- Risk tier boundaries (6.9 → high, 7.1 → medium, 14.1 → low, 30.1 → none).
- Reorder point bump logic.
- Idempotency second invocation returns zero new dispatches.
- Notification functions: monkeypatch SMTP / requests.

Integration:

- Extend `test_api_integration.py` for `/analytics/stockout-risk?velocity_strategy=conservative` includes `velocity_source`.
- Internal endpoint auth (401 unauthorized without token, 200 with token).

Regression guard: ensure existing fields unaffected (no rename).

---

## Timeline (Suggested Daily Breakdown)

Day 1: dbt modifications + tests; validate in local run; update documentation.
Day 2: API velocity refactor + new param + integration test updates.
Day 3: Alert service + internal endpoint skeleton + idempotency.
Day 4: Notification channels + unit tests (mocked dependencies).
Day 5: Polish, config docs, frontend hook extension, final test pass & performance spot‑check.

---

## Success Criteria

- `sales_daily` exposes `units_56day_avg` & `forecast_30d_units` with passing dbt tests.
- `/analytics/stockout-risk` returns `velocity_source` & honors `velocity_strategy` param.
- Internal daily alerts endpoint produces deterministic digest; idempotent on re‑run same date.
- Email/webhook attempts logged (or delivered) without blocking on failure.
- All new & existing Python + dbt tests green.
- No breaking changes for existing frontend consumers.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Sparse sales → noisy velocity | False alerts | Fallback hierarchy + ε clamp + conservative mode |
| Duplicate alert runs | Spam | Idempotency key per org/date |
| SMTP / webhook failure | Lost notifications | Try/except; aggregate errors in response; non‑blocking |
| dbt column mismatch | API errors | Add column existence tests & CI run before merge |
| Performance degradation | Slow daily run | Single aggregate query + batching |

---

## Deferred (Explicitly Out of Scope W4)

- Persistent `alert_events` table / history UI.
- Weekly performance digest automation (foundation only).
- Advanced forecasting (statistical / ML models).
- Multi‑channel (Slack/SMS) notifications.
- Org‑level alert preference UI.

---

## Key Files to Add / Modify

```text
backend/dbt/models/marts/sales_daily.sql          # add columns
backend/dbt/models/marts/schema.yml               # tests for new columns
backend/app/api/api_v1/endpoints/analytics.py     # velocity logic + param
backend/app/api/api_v1/endpoints/internal.py      # new internal alerts endpoint
backend/app/services/alerts.py                    # compute & digest logic
backend/app/services/notify.py                    # email/webhook dispatch
backend/app/core/config.py                        # new settings
backend/tests/test_alerts.py                      # unit tests
frontend/src/hooks/use-stockout-risk.ts           # add velocity_source field
README.md / .env.example                          # document env vars
```

---

## Next Steps

1. Implement dbt changes & run tests.
2. Refactor stockout risk endpoint; add new param + field.
3. Build alert service & internal endpoint with idempotency.
4. Add notification implementations + configuration.
5. Write & pass tests; update docs; minimal frontend field extension.

---

This plan maintains additive, non‑breaking changes and sets the foundation for W5 purchase suggestions & automated PO drafts.
