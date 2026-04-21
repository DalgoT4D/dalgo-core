# Metrics & KPIs v1 — Research

**Companion to:** `plan.md`
**Date:** 2026-04-21
**Author (AI pass):** initial draft from `/engineering/plan-feature` run

This file captures the findings gathered before drafting the implementation plan. Structured as inputs, not decisions — decisions live in `plan.md`.

---

## 1. Context sources

| Source | Purpose |
|--------|---------|
| `dalgo-core/README.md` | AI workflow, directory conventions |
| `dalgo-core/docs/domain-map.md` | Product entity relationships and blast radius |
| `workdocs/metrics_kpis/spec.md` | PM's full vision (US-1 through US-8, derived Metrics, SQL mode, annotations) |
| `workdocs/metrics_kpis/v1/spec.md` | Scoped v1 iteration (simple mode only, no annotations, no derived, no blast-radius dialog) |
| `DDP_backend/ddpui/models/visualization.py` | Existing Chart model |
| `DDP_backend/ddpui/models/dashboard.py` | Existing Dashboard model + DashboardComponentType enum |
| `DDP_backend/ddpui/models/report.py` | ReportSnapshot model — frozen layout, live data |
| `DDP_backend/ddpui/models/notifications.py` | Notification delivery layer |
| `webapp_v2/components/charts-v2/builder/data-config/metrics-selector.tsx` | New MetricsSelector (target of rename) |
| `webapp_v2/components/charts/MetricsSelector.tsx` | Legacy MetricsSelector (also needs rename/deprecation path) |

---

## 2. Pre-Check outcomes (confirmed with user)

Primary entities introduced/changed: **Metric** (new), **KPI** (new), **Dashboard** (new component type), **Chart/Measure** (rename + Saved Metrics tab).

Blast Radius decisions from conversation on 2026-04-21:

| Surface | Decision | Source |
|---------|----------|--------|
| Chart | in-scope (US-3, rename) | spec |
| KPI | in-scope (US-4, US-5) | spec |
| Dashboard | in-scope (US-7 widget type) | spec |
| ReportSnapshot | in-scope by inheritance — render code must handle new KPI widget type | code (`report.py` frozen_chart_configs) + user confirm |
| Share link (Dashboard mode) | in-scope by inheritance — user confirmed "yes we can share it using dashboard" | user |
| Alert | deferred to paired Alerts spec | spec |
| Explore | out-of-scope for v1 — picker is NOT reused per Pratiksha | user |
| Scheduled email | **not a Dalgo feature** — removed from domain map | user |
| Notification | unaffected | map traversal |
| Upstream (Source/Warehouse/Transform/Pipeline) | unaffected (Metrics read from Warehouse; don't change upstream) | map |

---

## 3. Codebase findings

### 3.1 Backend architecture (DDP_backend)

Layered service-oriented architecture — see `DDP_backend/.claude/CLAUDE.md`:

- `ddpui/api/` — thin API entry points, one file per feature (`charts_api.py`, `dashboard_native_api.py`, `report_api.py`)
- `ddpui/core/` — business logic (`core/charts/`, `core/reports/`, `core/comments/`)
- `ddpui/schemas/` — Pydantic request/response schemas (`chart_schema.py`, `dashboard_schema.py`, `report_schema.py`)
- `ddpui/models/` — Django ORM models

**Patterns we must follow:**
- Router naming: `{module}_router` per file
- Every endpoint decorated with `@has_permission(...)`
- Every response wrapped in `api_response()`
- No local imports inside functions — all imports at top of file
- Feature-specific exceptions, no bare `except:`
- Pydantic schemas for all request validation
- `__init__.py` kept empty (no barrel exports)

### 3.2 Backend — existing Chart model (`models/visualization.py`)

- `Chart` has: `title`, `description`, `chart_type` (enum), `schema_name`, `table_name`, `extra_config` (JSONField blob).
- Chart types enum: `bar`, `pie`, `line`, `number`, `map`, `table`, `pivot_table` — **no KPI yet**.
- `computation_type` field is **deprecated** — kept for DB compatibility only; don't base new logic on it.
- `extra_config` carries all the Measure/filter/customization state as a JSON blob — loose schema.

**Implication:** The v1 spec's "Saved Metrics as Measure" requires a new path inside `extra_config` (or alongside it) to carry a Metric FK reference. Proposal: add an optional `metric_id` discriminator in `extra_config`, falling back to current inline Measure shape.

### 3.3 Backend — Dashboard model (`models/dashboard.py`)

- `DashboardComponentType` enum: `CHART`, `TEXT`, `HEADING` — **no KPI widget type yet.**
- Layout stored as `layout_config` (grid) + `components` (JSON blob).
- Dashboard has its OWN `public_share_token` — this is the live public share.
- `DashboardLock` provides editor concurrent-edit protection.

**Implication:** KPI widget requires extending `DashboardComponentType` with a new value (e.g. `KPI`), plus wiring the new type into:
1. Dashboard builder UI
2. Public dashboard share view (auto-inherits per user confirmation)
3. ReportSnapshot render code (see 3.4)

### 3.4 Backend — ReportSnapshot model (`models/report.py`)

- Stores `frozen_dashboard` (layout + filters) and `frozen_chart_configs` (full chart configs keyed by chart_id).
- **Data is live** — queried each view through a date-range filter.
- Has its own `public_share_token`, independent of Dashboard's.

**Implication for v1:** Any snapshot taken *after* the KPI widget ships will include KPI widget configs in `frozen_chart_configs` (assuming KPI widget is modeled as a Chart). The render path for ReportSnapshot must know how to render the new KPI chart type; otherwise frozen configs will exist but fail-render. This must be covered in the testing strategy.

**Gotcha to highlight in plan:** Since Report data is live-queried, editing a Metric's formula retroactively changes numbers in historical Reports. Worth calling out for stakeholder trust reasons — but this is not a v1 blocker, it's a user-communication concern.

### 3.5 Backend — API surface (existing similar features)

API files relevant as patterns:
- `charts_api.py` → pattern for Metric API
- `dashboard_native_api.py` → pattern for KPI API (similar list/detail/CRUD shape)
- `report_api.py` → pattern for read-only-plus-snapshot endpoints

Core services as patterns:
- `core/charts/` → logic layer for Chart operations — Metric will sit alongside here
- `core/reports/` → ReportSnapshot service — read for its freeze/render pattern
- `core/visualizationfunctions.py` → helper functions for chart rendering — extend for KPI

### 3.6 Frontend architecture (webapp_v2)

Per `webapp_v2/CLAUDE.md`:

- Next.js 15 with App Router, React 19.
- Shadcn UI + Radix primitives + Tailwind v4.
- SWR hooks under `hooks/api/` — one hook file per resource (`useCharts.ts`, `useDashboards.ts`, `useReports.ts`).
- Pattern: `useFeatures` (list), `useFeature` (detail), `useCreateFeature` / `useUpdateFeature` / `useDeleteFeature` (mutations).
- Zustand for client state, TypeScript everywhere, no `any`.
- `data-testid` on every interactive element.
- Toast via `lib/toast.ts` (`toastSuccess` / `toastError`), not raw `toast()`.

**New hook files needed:** `useMetrics.ts`, `useKpis.ts`.

### 3.7 Frontend — existing chart builder

- Newer chart builder: `components/charts-v2/builder/chart-builder-shell.tsx`.
- Newer Measure picker: `components/charts-v2/builder/data-config/metrics-selector.tsx`.
- Older parallel picker: `components/charts/MetricsSelector.tsx` (with its tests) — still referenced somewhere, needs check.

**Implication:** The "Measure" rename must hit BOTH the v2 file and the legacy file. The legacy one likely should be deprecated — but the spec only requires the v2 rename. Note for investigation: is the legacy `charts/` folder still reachable at runtime, or is it dead code?

### 3.8 Frontend — existing Dashboard/Report components

- `components/dashboard-v2/` — current dashboard builder. Has `builder/`, `view/`, `list/`, `filters/`, `elements/`.
- `components/reports/` — Report UI. Uses snapshot model.

**Implication:** KPI widget needs placement in:
- `dashboard-v2/elements/` for the composable widget
- Some registration in the builder UI's chart-type picker
- Ensure it renders in `dashboard-v2/view/` (public share path goes through the same components)
- Ensure it renders in `reports/` detail view (since ReportSnapshot inherits Dashboard widgets)

---

## 4. Multi-service impact

| Service | Change scope | Validation approach |
|---------|--------------|---------------------|
| **DDP_backend** | New Metric + KPI models + migrations. New `metrics_api.py` + `kpis_api.py` routers. New `core/metrics/` + `core/kpis/` services. New schemas. Extend `DashboardComponentType` enum. Extend Chart `extra_config` reader to resolve Metric references. Extend Report render for KPI widget type. | `pytest` per module — unit tests for Metric resolution, KPI RAG computation, blast-radius queries. Integration tests for Metric → Chart → Dashboard → ReportSnapshot flow. |
| **webapp_v2** | New `Metrics Library` page, `Create/Edit Metric` form, extended Measure picker with "Saved Metrics" tab, `MetricsSelector` → `MeasureSelector` rename, new `KPI page`, new `KPI detail drawer`, `KPI widget` component, `useMetrics` + `useKpis` hooks. | `jest` component + hook tests. `playwright` E2E: create Metric → use in Chart → define KPI → see on KPI page → embed on Dashboard → view in public share. |
| **prefect-proxy** | No change — Metrics read from Warehouse at evaluation time. Pipeline timing unchanged. | N/A |

---

## 5. External research

Minimal external research needed — feature follows standard patterns. Key references:

- **RAG computation** — standard "green if ≥target, amber if ≥threshold%, red otherwise" logic. Inverted for direction=decrease. No external library needed; implement as a pure function.
- **Trendline rendering** — use existing Recharts setup from Dashboard widgets. Don't introduce a new charting library for one widget type.
- **Metric aggregation SQL** — reuse the warehouse adapter's existing aggregation helpers; mirror how Chart builds its current ad-hoc Measure SQL.
- **Period-over-period calculation** — compute at read time from the trendline data; no extra storage needed.

No third-party libraries added in v1.

---

## 6. Gotchas & risks identified during research

1. **ReportSnapshot render path for KPI widget** — frozen configs will exist for KPIs only in snapshots taken after the widget ships. Older snapshots are unaffected. Must be explicit in tests.
2. **Live data in frozen report means Metric edits rewrite history** — not a v1 blocker but belongs in user-facing documentation: "Editing a Metric will change the numbers displayed in historical reports."
3. **Legacy `charts/MetricsSelector.tsx`** — is it dead code? If not, rename there too. Investigate during M1.
4. **Public share inherits KPI widget automatically** — user confirmed this is acceptable. No gating needed.
5. **`extra_config` JSON blob is loose** — adding a Metric reference shape needs a discriminator and backward-compat handling. Existing charts with inline Measures must keep working unchanged.
6. **Chart type enum addition** — must be applied everywhere charts are rendered (builder, dashboard view, public share, ReportSnapshot render). Missing a render site = broken rendering in that surface only, silent.

---

## 7. Patterns confirmed for the plan

- Backend: one API file + one core module + one schema file + one model file per entity (Metric, KPI).
- Frontend: one SWR hook file + one page + one form component + list/detail components per entity.
- Testing: pytest for backend, jest + playwright for frontend, covering the cross-surface rendering paths.
- Migrations: two new tables (Metric, KPI). One enum extension (DashboardComponentType). No data migration needed since prototype branch is not released.
