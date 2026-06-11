# Alerts v1 — Research

**Date:** 2026-06-11
**Spec:** [v1 spec](./spec.md) | [parent spec](../spec.md)
**Companion:** [plan.md](./plan.md)

This document captures codebase research, existing patterns to reuse, library options, and the architecture decisions made in scope-confirmation conversation with the user.

---

## 1. Codebase patterns to reuse

### DDP_backend (Django + Django Ninja)

| Concern | File / Pattern | How we use it |
|---|---|---|
| **Org-scoped models** | `ddpui/models/metric.py` — Metric, KPI; `org = FK(Org, on_delete=CASCADE)` | Same shape for `Alert`, `AlertRecipient`, `AlertFire`, `AlertDelivery` |
| **Permission gating** | `@has_permission(["can_view_metrics"])` from `ddpui/auth.py` | New slugs: `can_view_alerts`, `can_create_alerts`, `can_edit_alerts`, `can_delete_alerts` |
| **Permission migration** | `ddpui/migrations/0137_update_landing_page_permissions.py` | Same pattern: `RunPython` adds Permission rows + RolePermission rows |
| **Ninja Schema layer** | `ddpui/schemas/metric_schema.py` | New `ddpui/schemas/alert_schema.py` with Create/Update/Response variants |
| **API router pattern** | `ddpui/api/charts_api.py` — typed `response=` on endpoints, `HttpError` for errors | New `ddpui/api/alert_api.py` |
| **Service layer** | `ddpui/core/metric/metric_service.py` — static methods, validation via warehouse query | New `ddpui/core/alerts/alert_service.py` |
| **AggQueryBuilder** | `ddpui/core/datainsights/query_builder.py` — fluent SQL builder, supports all aggregates incl. `count_distinct` | Reused as-is by the evaluator to build Standalone alert queries |
| **MetricService.compute_metric_value** | `ddpui/core/metric/metric_service.py` | Reused by the evaluator for Metric-threshold alerts (no duplication) |
| **WarehouseFactory** | `ddpui/datatypes/warehouse_*.py` | Reused to execute alert SQL against org's warehouse |
| **SES email send** | `ddpui/utils/awsses.py` — `send_text_message`, `send_html_message` | Reused for alert email delivery (one call per recipient) |
| **Webhook POST** | `ddpui/utils/discord.py` — `requests.post(url, json=..., timeout=10)` with `raise_for_status` | Identical pattern for Slack webhook POST |
| **Celery worker** | `ddpui/celeryworkers/` — existing `task = @shared_task` pattern | New `ddpui/celeryworkers/alert_tasks.py` for `dispatch_due_alerts` + `evaluate_alert` |
| **Celery beat config** | `ddpui/celery.py` + Django settings `CELERY_BEAT_SCHEDULE` | Add one entry: `alerts-dispatcher` ticking every 60s |

### webapp_v2 (Next.js 15 + Shadcn)

| Concern | File / Pattern | How we use it |
|---|---|---|
| **App router page** | `app/metrics/page.tsx`, `app/kpis/page.tsx` | New `app/alerts/page.tsx` |
| **Nav item already defined** | `components/main-layout.tsx` lines 186–190 — "Alerts" item with `AlertTriangle` icon, gated by `PRODUCTION_HIDDEN_ITEMS` | Unhide when ready to ship |
| **SWR data hook** | `hooks/api/useMetrics.ts`, `useKPIs.ts` | New `hooks/api/useAlerts.ts` |
| **API client** | `lib/api.ts` — `apiGet/apiPost/apiPut/apiDelete`, auto-attaches auth + org headers | Reused |
| **Toast** | Sonner via `lib/toast.ts` — `toastSuccess.created('Alert')`, `toastError.api(err, ...)` | All wizard / listing actions |
| **Shadcn Tabs** | `components/ui/tabs.tsx` — used in `metric-form-dialog.tsx` for Simple/Calculated | All alerts / Firing tabs on /alerts page |
| **Table component** | `components/ui/table.tsx` (Shadcn HTML table, NOT TanStack) — see `app/charts/page.tsx` for sort/filter pattern | New `components/alerts/AlertsTable.tsx` |
| **DropdownMenu (3-dot row menu)** | `app/charts/page.tsx:58-63` | Same pattern for Edit / Delete / Alert log |
| **Combobox** | `components/ui/combobox.tsx` — single + multi mode, custom `renderItem` | RecipientCombobox builds on this |
| **Tag chips (recipient list)** | `components/kpis/kpi-form.tsx` `ProgramTagsInput` pattern (Badge + X to remove) | Same pattern, with avatar/envelope icons to distinguish Dalgo users vs. external emails |
| **DatasetSelector** | `components/charts/DatasetSelector.tsx` — `onDatasetChange(schema, table)` callback | Reused in Standalone alert Step 1 |
| **Metric form (for Standalone primitive)** | `components/metrics/metric-form-dialog.tsx` (Simple + Calculated modes) | Standalone alert wizard Step 1 reuses the column/aggregation/expression form fields |
| **KPI detail drawer** | `components/kpis/kpi-detail-drawer.tsx` — no "Create Alert" button today; we add one | Story 2 entry point |
| **Permission hook** | `hooks/api/usePermissions.ts` — `useUserPermissions().hasPermission('slug')` | Conditional render for CTAs and 3-dot menu items |
| **Relative time** | `date-fns` — `formatDistanceToNow(date, { addSuffix: true })` | "2h ago" Last fire column |

---

## 2. Library choices

| Concern | Choice | Why |
|---|---|---|
| **Cron parsing on backend** | `croniter` (pip package) | Standard, mature, `.get_prev()` and `.get_next()` are one-liners. Used by django-celery-beat itself. |
| **Mustache template rendering** | `pystache` (pip package) | Spec calls out Mustache by name. `pystache` is the canonical Python implementation. Safe — no eval. |
| **Cron parsing/validation on frontend** | `cron-parser` (npm) | Match backend semantics. Lets us validate the cron client-side before save and reverse-render "what does this mean" for display. |
| **Frontend tz → UTC conversion** | Browser-native `Date` + `Intl.DateTimeFormat` | No extra dep. The user picks local time + frequency in the wizard; we compute the UTC cron at submit. |

---

## 3. Architecture decisions (confirmed with user)

### 3.1 Triggers — schedule only

Pipeline-completion and Data Quality check failure as trigger sources are **deferred to a future spec**. v1 ships only the three schedule-driven alert types (Metric-threshold, KPI-RAG, Standalone).

**Why:** The original (pre-v1) spec was pipeline-triggered. The v1 spec collapsed everything to user-set schedules (daily/weekly/monthly) because: (a) NGO users want predictable cadence, not "whenever pipeline runs," (b) schedule-driven is simpler to reason about and to build.

### 3.2 No in-app notification rows on fire

When an alert fires, we **do NOT** create rows in Dalgo's existing `Notification` model. Delivery is Email + Slack only. The in-app surfaces are:
- `/alerts` listing **Firing tab** — shows alerts whose most recent evaluation fired.
- **Alert log modal** — per-alert fire history.

**Why:** Spec is explicit about Email + Slack channels and tabs/log as the in-app affordances. Adding Notification rows would couple Alerts to the existing notification infrastructure without solving a user-facing problem.

### 3.3 Scheduler — Celery Beat tick + conditional-UPDATE claim

- Single Celery Beat entry fires `dispatch_due_alerts` **every 60 seconds**.
- Dispatcher iterates `Alert.objects.filter(is_active=True)`, computes `is_due(alert, now)`, and enqueues `evaluate_alert.delay(alert.id)` for each due alert.
- `is_due(alert, now)` uses `croniter(alert.schedule_cron, now).get_prev()` to find the most recent scheduled instant ≤ now, and returns `True` iff `last_evaluated_at` is NULL or `< that instant`.
- Evaluator **claims** the run via an atomic conditional UPDATE:
  ```python
  rows = Alert.objects.filter(
      id=alert_id, is_active=True
  ).filter(
      Q(last_evaluated_at__isnull=True) | Q(last_evaluated_at__lt=scheduled_for)
  ).update(last_evaluated_at=now)
  if rows == 0: return  # someone else claimed this run
  ```
  Postgres serializes concurrent UPDATEs to the same row; only one worker's WHERE clause matches; the other sees `rows=0` and exits.

**Why this design (vs. alternatives):**
- vs. `next_run_at` stored: no derived state to keep in sync when schedules are edited. `Alert.schedule_cron` is the only source of truth.
- vs. `django-celery-beat` PeriodicTask-per-alert: no per-alert rows in the celery_beat tables; less indirection between Alert.schedule and the cron entry; no extra config when alerts are created/edited.
- vs. Prefect deployment per alert: prefect-proxy is reserved for data orchestration; coupling Alert lifecycle to it complicates local dev and adds a network hop.
- vs. `select_for_update` lock: conditional UPDATE is a single SQL statement, no transaction management, atomicity guaranteed by SQL standard. Same correctness, simpler code.

**Trade-offs accepted:**
- O(N active alerts) iteration per minute. At NGO scale (≤ a few hundred alerts per org, very small org count), this is negligible. If it ever matters, add `WHERE last_evaluated_at < (now - smallest_schedule_interval)` to prune in the SQL.
- Beat granularity: 60 seconds. Alerts can fire up to ~60s late. Spec doesn't need sub-minute precision (daily/weekly/monthly only).
- At-most-once per scheduled tick. If a worker crashes between the UPDATE claim and notification send, that one fire is lost; next scheduled tick runs normally. Acceptable for these cadences.

### 3.4 Schedule storage — cron in UTC, no TZ column

- Backend stores `schedule_cron: str` only (a 5-field cron expression in UTC).
- Frontend wizard takes the user's pick (frequency + day-of-week/month + time-of-day in their browser TZ) and computes the UTC cron at submit:
  - `09:00 IST` (UTC+5:30) → `30 3` for HH:MM fields → `"30 3 * * *"` for daily.
- On display (listing, edit modal), the frontend reverse-renders the stored UTC cron into the **viewer's** local TZ — matches spec "displayed in the viewer's local timezone."

**Why no TZ stored:**
- User explicitly chose this for simplicity. One fewer column to maintain; no per-row TZ math on the backend.
- Acceptable risk: DST-observing timezones see a 1-hour silent shift twice a year. Dalgo's user base is India-dominant (IST = no DST), so this rarely bites.
- If DST safety becomes important later, adding `schedule_timezone: CharField` and evaluating `croniter(cron, now_local).get_prev()` is a single-column migration.

### 3.5 Base branch — fresh on `feature/alerts`

The prototype branches (`pratiksha/alerts-metrics-changes` ~3,371 LOC; others) were built for the **pipeline-triggered** model. v1 replaces that with the schedule-driven model. The data model, Celery integration, and most of the API surface differ enough that starting fresh is less work than refactoring.

**What we mine from the prototype (manual lift, not branch-merge):**
- Mustache token rendering logic (~50 lines).
- Email-send loop pattern (~30 lines).
- SQL-building approach for Standalone alerts (reference for shaping our reuse of `AggQueryBuilder`).
- Test fixtures.

Everything else is rewritten from the v1 spec.

---

## 4. Open architecture questions (carried to plan)

1. **Slack webhook URL storage** — store as plain `TextField`? Treat as a secret (encrypt at rest)? Mask on GET response? Recommend: store plain, mask on GET (only the author sees full URL on edit), no at-rest encryption in v1.
2. **`AlertFire.sql_executed` visibility** — Story 6 says "View SQL" in the Alert log is visible to every logged-in user. Confirm this exposes schema/table names is acceptable. (Same surface as the Test step in the wizard.)
3. **Schedule-frequency derivation from cron for display** — the listing UI shows "daily/weekly/monthly" as a column. We derive this from the cron pattern (`* * *` for daily, `* * <0-6>` for weekly, `<1-28> * *` for monthly). If the cron doesn't match one of these patterns (which can't happen via our UI), display falls back to the cron string.
4. **Cron drift on schedule edit** — if a user edits an alert's schedule mid-day, `last_evaluated_at` is preserved. The next dispatcher tick re-evaluates `is_due` against the new cron. This is correct behavior but worth a unit test.

---

## 5. Blast Radius — domain map traversal

Primary entity created: **Alert** (and `AlertRecipient`, `AlertFire`, `AlertDelivery`).

| Surface | Hop | Edge | Status | Notes |
|---|---|---|---|---|
| **Metric** | 1 (consumes) | `reference` | In scope — read-only | Metric-threshold alerts reference `Metric.id`. Delete-blocked when alerts exist (matches spec). |
| **KPI** | 1 (consumes) | `reference` | In scope — read-only | KPI-RAG alerts reference `KPI.id`. Delete-blocked when alerts exist. |
| **Warehouse** | 1 (consumes) | `query-from` | In scope | Evaluator runs SQL against org's warehouse. Reuses `MetricService.compute_metric_value` (metric/standalone) and `KPIService` for RAG eval. |
| **Pipeline** | 1 (consumes) | `trigger` per domain map | **Deferred** | v1 ignores pipeline events entirely. |
| **Data Quality check** | 1 (consumes) | `trigger` per domain map | **Deferred** | v1 has no DQ-check alert type. |
| **Notification** | 1 (consumed by, per domain map) | `trigger` | **Out of scope** | User confirmed: no in-app Notification rows. |
| **OrgUser** | 1 (consumed by, as recipient) | `reference` | In scope | `AlertRecipient.orguser_id` for Dalgo-user recipients. External emails stored as plain strings. |
| **Metrics page** (UI surface) | — | entry point | In scope | "Create Alert" CTA on metric rows. |
| **KPI detail drawer** (UI surface) | — | entry point | In scope | "Create Alert" CTA added. |
| **`/alerts` page** (new) | — | new surface | In scope | All alerts + Firing tabs, Alert log modal. |

No 2-hop downstream because Alert's only consumer (Notification) is out of scope.

---

## 6. Reference: data flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     webapp_v2 (Next.js)                          │
│                                                                  │
│  /metrics page          /kpis (drawer)         /alerts page      │
│      │                       │                       │           │
│      └───── "Create Alert" CTA opens Alert wizard ───┘           │
│                              │                                   │
│        AlertWizardModal (3 steps): Define → Notify → Test        │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │  HTTP via lib/api.ts
                               │
┌──────────────────────────────┼───────────────────────────────────┐
│                       DDP_backend (Django Ninja)                 │
│                              │                                   │
│  /api/alerts/  (CRUD)        /api/alerts/test/ (dry-run)         │
│  /api/alerts/{id}/fires/     /api/alerts/test-slack-webhook/     │
│                              │                                   │
│                       AlertService                               │
│                  (validate, persist, query)                      │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                               ▼  reads
                       Postgres (Alert, AlertRecipient,
                                 AlertFire, AlertDelivery)
                               ▲
                               │  writes
┌──────────────────────────────┼───────────────────────────────────┐
│                       Celery (worker + beat)                     │
│                              │                                   │
│  every 60s → dispatch_due_alerts:                                │
│       for alert in Alert.objects.filter(is_active=True):         │
│           if is_due(alert, now): evaluate_alert.delay(id)        │
│                              │                                   │
│  evaluate_alert(id) (worker):                                    │
│       atomic claim via conditional UPDATE last_evaluated_at      │
│       build SQL (reuse MetricService / KPIService / AggQB)       │
│       run query against org's warehouse                          │
│       check_condition → fired? bool                              │
│       render templates (pystache)                                │
│       if fired:                                                  │
│           send email per recipient via awsses.py                 │
│           POST to slack_webhook_url if set                       │
│       write AlertFire + AlertDelivery rows                       │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
                          ┌─────────┐     ┌─────────────┐
                          │   SES   │     │ Slack       │
                          │  email  │     │ webhook URL │
                          └─────────┘     └─────────────┘
```

---

*Captured during scope-confirmation conversation 2026-06-11. Saved as a snapshot of decisions that shaped the plan.*
