# Metrics & KPIs v1 — Implementation Plan

**Status:** Draft v1
**Date:** 2026-04-21
**Spec (full vision):** [../spec.md](../spec.md)
**Spec (v1 scope):** [./spec.md](./spec.md)
**Research:** [./research.md](./research.md)

---

## 1. Overview

Ship the end-to-end chain: **Metric creation → reuse in charts → KPI definition → KPI page → KPI dashboard widget** (plus Measure rename + basic edit/delete with consumer check). Unblocks Bhumi's June quarterly-review deadline and delivers the "define a calculation once, reuse everywhere" primitive that four NGOs asked for.

**Services affected:**
- **DDP_backend** — new `Metric` and `KPI` models, APIs, core services, schemas, migration. Extends `DashboardComponentType` enum. Extends Chart extra_config shape to support Metric references. Extends Report render path to handle the KPI widget type.
- **webapp_v2** — new Metrics Library + KPI page + KPI detail drawer, Metric/KPI creation forms, MeasureSelector (rename + Saved Metrics tab), KPI dashboard widget, new SWR hooks.
- **prefect-proxy** — no change.

---

## 2. Blast Radius

Confirmed with user in the Pre-Check conversation on 2026-04-21.

| Surface | Hop | Why affected | Status | Notes |
|---------|-----|-------------|--------|-------|
| Chart | 1 from Metric | Gains "Saved Metrics" tab in Measure picker + Measure rename | **in-scope** | US-3 + terminology rename |
| KPI | — (new) | Net-new entity | **in-scope** | US-4, US-5 |
| Dashboard | 1 from KPI | New KPI widget component type | **in-scope** | US-7 |
| ReportSnapshot | 2 (via Dashboard) | `snapshot-of` Dashboard → captures KPI widget configs once the new type exists | **in-scope by inheritance** | Render code must support KPI widget type — covered in Milestone 3 |
| Share link (Dashboard mode) | 2 (via Dashboard) | Live share auto-renders any Dashboard widget including KPI | **in-scope by inheritance** | User confirmed acceptable — "yes we can share it using dashboard" |
| Share link (Report mode) | 2 (via ReportSnapshot) | Same inheritance path as ReportSnapshot | **in-scope by inheritance** | Same test coverage as above |
| Alert | 1 from Metric + KPI | Thresholds, RAG transitions | **deferred** | Paired Alerts spec, separate feature owner |
| Notification | 3+ | Only triggered via Alert | **unaffected in v1** | Comes along when Alerts ships |
| Explore | 2 (via Chart) | Would need Saved Metrics picker integration | **out-of-scope** | User confirmed picker is NOT reused from dashboard builder. Tracked separately. |
| Source / Warehouse / Transform / Pipeline | upstream | Metrics read from these; don't change them | **unaffected** | — |
| Data Quality check | — | Independent | **unaffected** | — |
| Organization / OrgUser | — | Standard org-scoping, no ACL changes | **unaffected** | Access control explicitly out of scope per spec |

**Note on Scheduled email:** Not a Dalgo feature today. Removed from the domain map.

**Stakeholder-trust note** (not a scope item, but belongs in release comms): because ReportSnapshot is frozen-layout-live-data, editing a Metric's formula retroactively changes the numbers shown in historical reports. Call this out in release notes so NGOs don't get surprised.

---

## 3. High-Level Design

### 3.1 System-level flow

```
         Analyst                              Program lead                       Leadership / Dashboard viewer
            │                                       │                                       │
            ▼                                       ▼                                       ▼
  ┌──────────────────┐                    ┌──────────────────┐                    ┌────────────────────────┐
  │ Metrics Library  │                    │    KPI Page      │                    │  Dashboard (+ widget)  │
  │  (webapp_v2)     │                    │  (webapp_v2)     │                    │    (webapp_v2)         │
  └────────┬─────────┘                    └────────┬─────────┘                    └───────────┬────────────┘
           │                                       │                                          │
           │ useMetrics / useCreateMetric          │ useKpis / useCreateKpi                   │ existing useDashboards
           ▼                                       ▼                                          ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐
  │                           DDP_backend — REST (Django Ninja)                                   │
  │  metrics_api.py        kpis_api.py         dashboard_native_api.py (extended)                 │
  │  ↓                     ↓                   ↓                                                  │
  │  core/metrics/         core/kpis/          core/dashboard/ (existing)                         │
  │  ↓                     ↓                                                                      │
  │  models/metric.py      models/kpi.py       models/dashboard.py (DashboardComponentType + KPI) │
  └──────────────────────────────────────────────────────────────────────────────────────────────┘
                                                 │
                                                 ▼
                                         Warehouse (Postgres / BigQuery)
                                        queried at Metric-evaluation time
```

### 3.2 Data flow (Metric evaluation at render time)

1. Frontend renders a Chart that has a `metric_id` reference in its `extra_config`.
2. `charts_api.get_chart_data` resolves the Metric via `core/metrics/resolve_measure(chart_or_kpi_config)`.
3. `core/metrics` builds the aggregation SQL (column + aggregation + filters), joins to the dataset, runs it against the warehouse.
4. Returns the scalar value (or trendline series for KPI).
5. KPI RAG computed in-memory via pure function `core/kpis/compute_rag(value, target, direction, thresholds)`.

### 3.3 Key design decisions

| Decision | Rationale | Alternatives rejected |
|----------|-----------|----------------------|
| Metric is a **separate model**, not a column on Chart | Reusability is the whole point of the feature | Storing Metric definitions inline per-chart — causes the drift the spec is solving |
| KPI has `metric_id` FK to Metric (required) | Spec is explicit: every KPI is a Metric with target+RAG | Embedding Metric shape into KPI — couples the two, blocks reuse |
| `DashboardComponentType.KPI` added as new enum value | Cleanest way to extend the existing dashboard widget system | Treating KPI widget as a special Chart — would force KPI-specific logic into chart paths |
| KPI widget data loaded via KPI endpoint, not Chart endpoint | KPI already holds target/thresholds/trend periods — no need to reshape into a Chart query | Having the widget call `/chart/{id}/data` — requires Chart to know about KPIs, inverted dependency |
| Metric reference in Chart lives in `extra_config` (JSON) | Matches existing pattern; no schema migration for Chart | Adding a FK column on Chart — migration risk, touches every existing row |
| Consumer check at delete time uses live SQL queries, not a reference table | v1 scope; spec explicitly defers reference-tracking index | Building a dedicated reference table — open question #6 in spec, deferred |

### 3.4 New API surface (Django Ninja)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/metrics/` | List Metrics for org (with filters: search, dataset, tags) |
| `POST` | `/api/metrics/` | Create a Metric |
| `GET` | `/api/metrics/{id}/` | Get Metric detail (incl. consumer counts) |
| `PUT` | `/api/metrics/{id}/` | Update Metric |
| `DELETE` | `/api/metrics/{id}/` | Delete Metric (blocked if consumers exist) |
| `POST` | `/api/metrics/preview/` | Preview current value for a draft Metric config |
| `GET` | `/api/kpis/` | List KPIs for org |
| `POST` | `/api/kpis/` | Create a KPI |
| `GET` | `/api/kpis/{id}/` | Get KPI detail (current value, target, RAG, trendline, period-over-period) |
| `PUT` | `/api/kpis/{id}/` | Update KPI |
| `DELETE` | `/api/kpis/{id}/` | Delete KPI |

### 3.5 External service integrations

None new. Metrics + KPIs read from the existing Warehouse via the existing warehouse adapter layer (`core/warehousefunctions.py`). No Airbyte, Prefect, or dbt changes.

---

## 4. Low-Level Design

### 4.1 Data model

**`Metric` (new — `DDP_backend/ddpui/models/metric.py`)**
```python
class Metric(models.Model):
    id = models.BigAutoField(primary_key=True)
    org = models.ForeignKey(Org, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    tags = models.JSONField(default=list)  # list of strings

    schema_name = models.CharField(max_length=255)
    table_name = models.CharField(max_length=255)

    creation_mode = models.CharField(
        max_length=20,
        choices=[("simple", "Simple"), ("derived", "Derived"), ("sql", "SQL")],
        default="simple",
    )
    # v1: only 'simple' is fully supported. The field exists now so v2 additions don't need a migration.

    column = models.CharField(max_length=255, blank=True, default="")
    aggregation = models.CharField(
        max_length=20,
        choices=AGGREGATE_FUNC_CHOICES,  # reuse from visualization.py
        blank=True,
        default="",
    )
    filters = models.JSONField(default=list)  # [{column, operator, value}]

    # Reserved for v2 — left nullable/empty so migration isn't needed later.
    metric_references = models.JSONField(default=list, blank=True)
    arithmetic_expression = models.TextField(blank=True, default="")
    sql_formula = models.TextField(blank=True, default="")

    created_by = models.ForeignKey(OrgUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "metric"
        constraints = [
            models.UniqueConstraint(fields=["org", "name"], name="unique_metric_name_per_org"),
        ]
```

**`KPI` (new — `DDP_backend/ddpui/models/kpi.py`)**
```python
class KPI(models.Model):
    id = models.BigAutoField(primary_key=True)
    org = models.ForeignKey(Org, on_delete=models.CASCADE)
    metric = models.ForeignKey(Metric, on_delete=models.PROTECT, related_name="kpis")

    name = models.CharField(max_length=255)  # display name; defaults to metric.name
    target_value = models.FloatField(null=True, blank=True)
    direction = models.CharField(
        max_length=10,
        choices=[("increase", "Higher is better"), ("decrease", "Lower is better")],
        default="increase",
    )
    green_threshold_pct = models.FloatField(default=100.0)
    amber_threshold_pct = models.FloatField(default=80.0)

    time_grain = models.CharField(
        max_length=10,
        choices=[("daily","Daily"),("weekly","Weekly"),("monthly","Monthly"),
                 ("quarterly","Quarterly"),("yearly","Yearly")],
        default="monthly",
    )
    trend_periods = models.IntegerField(default=12)

    metric_type_tag = models.CharField(
        max_length=10,
        choices=[("input","Input"),("output","Output"),("outcome","Outcome"),("impact","Impact")],
        default="output",
    )
    program_tags = models.JSONField(default=list)
    display_order = models.IntegerField(default=0)

    created_by = models.ForeignKey(OrgUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kpi"
```

**`DashboardComponentType` (extend — `models/dashboard.py`)**
```python
class DashboardComponentType(str, Enum):
    CHART = "chart"
    TEXT = "text"
    HEADING = "heading"
    KPI = "kpi"      # ← new
```

**`Chart.extra_config` shape (extend — no migration)**

Existing ad-hoc Measure stays unchanged. Add an optional discriminator:
```json
{
  "measure": {
    "mode": "saved",         // ← new: "saved" | "adhoc"
    "metric_id": 42,         // present if mode=saved
    "column": "student_id",  // present if mode=adhoc (existing path)
    "aggregation": "count_distinct",
    "filters": []
  },
  ...
}
```

Charts created before v1 have `measure` absent — the render code must treat "no measure key" as "adhoc using legacy inline fields" to stay backward compatible.

### 4.2 API schemas (Pydantic — `schemas/metric_schema.py` + `schemas/kpi_schema.py`)

```python
# metric_schema.py
class MetricFilter(BaseModel):
    column: str
    operator: Literal["=", "!=", ">", "<", ">=", "<=", "in", "not_in", "is_null", "is_not_null"]
    value: Any | None = None

class MetricCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    tags: list[str] = []
    schema_name: str
    table_name: str
    creation_mode: Literal["simple"] = "simple"  # v1: restrict
    column: str
    aggregation: Literal["sum","avg","count","min","max","count_distinct"]
    filters: list[MetricFilter] = []

class MetricResponseSchema(MetricCreateSchema):
    id: int
    consumer_counts: dict[str, int]  # {"charts": 3, "kpis": 2}
    current_value: float | None  # preview value
    created_at: datetime
    updated_at: datetime
```

```python
# kpi_schema.py
class KPICreateSchema(BaseModel):
    metric_id: int
    name: str
    target_value: float | None = None
    direction: Literal["increase", "decrease"] = "increase"
    green_threshold_pct: float = 100.0
    amber_threshold_pct: float = 80.0
    time_grain: Literal["daily","weekly","monthly","quarterly","yearly"] = "monthly"
    trend_periods: int = 12
    metric_type_tag: Literal["input","output","outcome","impact"] = "output"
    program_tags: list[str] = []

class KPIResponseSchema(KPICreateSchema):
    id: int
    current_value: float | None
    rag_state: Literal["green", "amber", "red"] | None
    trendline: list[dict]   # [{period, value}]
    period_over_period_change: float | None
    last_updated_at: datetime | None  # anchored to last pipeline run
```

### 4.3 Backend logic — new modules

```
DDP_backend/ddpui/
├── api/
│   ├── metrics_api.py          # NEW — router, endpoints
│   └── kpis_api.py             # NEW
├── core/
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── evaluator.py        # NEW — builds + runs aggregation SQL
│   │   ├── consumers.py        # NEW — "who uses this metric?" query
│   │   └── preview.py          # NEW — live value preview for creation UI
│   └── kpis/
│       ├── __init__.py
│       ├── evaluator.py        # NEW — current value + trendline + period-over-period
│       └── rag.py              # NEW — pure function for RAG computation
├── schemas/
│   ├── metric_schema.py        # NEW
│   └── kpi_schema.py           # NEW
└── models/
    ├── metric.py               # NEW
    └── kpi.py                  # NEW
```

**Chart render-time integration** (`core/charts/` — existing path):
- `resolve_measure(chart_config)` new helper: if `measure.mode == "saved"`, fetch Metric and substitute; else use legacy inline fields.

**Report render integration** (`core/reports/` — existing path):
- Extend the chart-config-to-rendered-chart pipeline so `DashboardComponentType.KPI` components route to KPI evaluator, not Chart evaluator. Needed because `frozen_chart_configs` captures them.

**Dashboard component registration** (`core/dashboard/`):
- Extend component-type handler registry so KPI widget is a first-class option alongside CHART/TEXT/HEADING.

### 4.4 Frontend components

```
webapp_v2/
├── app/
│   ├── metrics/
│   │   ├── page.tsx            # NEW — Metrics Library
│   │   └── [id]/
│   │       └── page.tsx        # NEW — Metric detail / edit
│   └── kpis/
│       ├── page.tsx            # NEW — KPI page (card grid)
│       └── [id]/
│           └── page.tsx        # NEW — KPI detail (drawer is default; this is the full-page fallback)
├── components/
│   ├── metrics/                # NEW directory
│   │   ├── metric-library.tsx
│   │   ├── metric-card.tsx
│   │   ├── metric-form.tsx     # simple mode only in v1
│   │   ├── metric-preview.tsx
│   │   └── metric-delete-dialog.tsx   # shows consumer list
│   ├── kpis/                   # NEW directory
│   │   ├── kpi-page.tsx
│   │   ├── kpi-card.tsx
│   │   ├── kpi-detail-drawer.tsx
│   │   ├── kpi-form.tsx
│   │   └── kpi-trendline.tsx   # Recharts-based
│   ├── charts-v2/
│   │   └── builder/
│   │       └── data-config/
│   │           ├── measure-selector.tsx   # RENAME from metrics-selector.tsx
│   │           └── saved-metrics-tab.tsx  # NEW — lists compatible Saved Metrics
│   └── dashboard-v2/
│       └── elements/
│           └── kpi-widget.tsx   # NEW — KPI rendered as a Dashboard widget
└── hooks/api/
    ├── useMetrics.ts           # NEW — list / detail / create / update / delete / preview
    └── useKpis.ts              # NEW — same set plus current-value fetch
```

### 4.5 Integration points

| Frontend component | Backend call | SWR hook |
|--------------------|--------------|----------|
| `metric-library.tsx` | `GET /api/metrics/` | `useMetrics(filter)` |
| `metric-form.tsx` (save) | `POST/PUT /api/metrics/` | `useCreateMetric` / `useUpdateMetric` |
| `metric-preview.tsx` | `POST /api/metrics/preview/` | `useMetricPreview(draftConfig)` |
| `measure-selector.tsx` → "Saved" tab | `GET /api/metrics/?dataset=X` | `useMetrics({ dataset_id })` |
| `kpi-page.tsx` | `GET /api/kpis/` | `useKpis()` |
| `kpi-form.tsx` | `POST/PUT /api/kpis/` | `useCreateKpi` / `useUpdateKpi` |
| `kpi-detail-drawer.tsx` | `GET /api/kpis/{id}/` | `useKpi(id)` |
| `kpi-widget.tsx` (dashboard) | `GET /api/kpis/{id}/` | `useKpi(id)` |

---

## 5. Security Review

| Concern | Addressed by |
|---------|--------------|
| **AuthN / AuthZ** | Every new endpoint decorated with `@has_permission(...)`. Roles: analysts/program leads can create/edit; everyone in org can read. Use existing `CAN_*` permission strings; add `CAN_MANAGE_METRICS`, `CAN_MANAGE_KPIS` if none fit. |
| **Input validation** | Pydantic schemas at API boundary validate everything — Metric column/table names, aggregation choice, filter operators, KPI target/thresholds. Column/table names validated against warehouse introspection before Metric save (reject references to non-existent columns). |
| **Data access control** | All list/detail endpoints filter by `request.user.orguser.org` — cannot cross-read another org's Metrics/KPIs. Uniqueness constraint on `(org, metric_name)` prevents inter-org confusion. |
| **Sensitive data** | No PII handled by Metrics/KPIs themselves. Metric definitions may reference columns that contain PII — no change to how that PII is stored; evaluation still happens inside the org's warehouse with no external data egress. |
| **Injection risks** | SQL mode is **out of v1 scope** — the injection risk vector doesn't exist in this iteration. Simple-mode aggregation is built via parameterized builders, never string concatenation. Column/table names sourced from warehouse introspection (allowlist), not free user input. |
| **External service calls** | None new. |
| **Rate limiting** | `/api/metrics/preview/` runs a live warehouse query on every keystroke-debounced preview. Must throttle on frontend (debounce 500ms) and on backend (per-user preview rate limit, e.g. 10/sec). |
| **Share-link exposure** | KPI widgets render inside publicly shared Dashboards and public ReportSnapshots. This is intentional (user confirmed). Ensure KPI widget render does not include `created_by` email or other user-identifying fields in the public payload. |

---

## 6. Testing Strategy

### 6.1 Unit tests (backend)

- `core/metrics/evaluator.py` — aggregation SQL generation: sum, avg, count, count_distinct with and without filters. Edge cases: empty table, null values, filter matches 0 rows.
- `core/kpis/rag.py` — RAG computation purity tests. Every direction × threshold combination. Target=None case. Target=0 edge case.
- `core/kpis/evaluator.py` — trendline bucketing for each time_grain. Period-over-period math.
- `core/metrics/consumers.py` — "who uses this metric?" query across Chart extra_config + KPI FKs.
- Metric save validation: uniqueness per org, column-exists check, aggregation-column-type compatibility.

### 6.2 Unit/component tests (frontend)

- `metric-form.tsx` — form validation; preview value fetch.
- `kpi-form.tsx` — threshold-adapt-by-direction behavior; target-optional behavior.
- `measure-selector.tsx` — both tabs render; dataset filter; "Saved Metrics" tab shows compatible-only list.
- `kpi-card.tsx` + `kpi-trendline.tsx` — renders with/without target, all three RAG states, missing-data fallback.
- `kpi-widget.tsx` — renders inside Dashboard layout with correct resize behavior.

### 6.3 Integration tests (cross-service)

- **End-to-end Metric lifecycle (API-level, pytest):** create Metric → use in Chart via saved-metric reference → verify Chart renders correct value → delete Metric blocked → remove Chart reference → delete Metric succeeds.
- **End-to-end KPI lifecycle (API-level, pytest):** create Metric → create KPI referencing it → add KPI widget to Dashboard → verify widget renders → take ReportSnapshot → verify snapshot's `frozen_chart_configs` contains KPI config → verify snapshot renders KPI widget.

### 6.4 E2E tests (Playwright, webapp_v2)

- **Critical path** (must pass for v1 to ship): Analyst creates a Metric → program lead creates a KPI → KPI appears on KPI page → KPI widget added to Dashboard → leadership views Dashboard → Dashboard shared publicly → public viewer sees the KPI widget.
- **Edit blast-radius:** attempt to delete a Metric that's used by a KPI → blocked with named consumer list.
- **Measure rename:** chart builder shows "Measure" label (not "Metric"); both tabs (Saved Metrics, Ad-hoc) work.

### 6.5 ReportSnapshot render coverage (special)

- Take ReportSnapshot of a Dashboard containing a KPI widget → open the snapshot → verify widget renders with live data for the snapshot's date range.
- Edit the underlying Metric after snapshot is taken → re-open snapshot → confirm **new** value renders (frozen-layout-live-data behavior).
- Delete the underlying KPI after snapshot → re-open snapshot → confirm frozen config still renders (no FK into snapshot; snapshot self-contained).

### 6.6 Test data

Fixtures needed:
- An Org with a Warehouse containing ≥1 dataset with numeric columns suitable for each aggregation type.
- An OrgUser per role (analyst, program lead, leadership, M&E coordinator).
- Seed Metric(s) and KPI(s) for the Dashboard-widget and Report-snapshot tests.

---

## 7. Milestones

Each milestone is independently shippable and reviewable as one PR (or small PR set).

#### Milestone 1: Measure rename (chart builder)
- **Deliverable:** `MetricsSelector` → `MeasureSelector` rename in charts-v2; labels updated from "Metric" to "Measure" across every chart type. Legacy `components/charts/MetricsSelector.tsx` investigated and deprecated if dead code.
- **Services:** webapp_v2 only
- **Key tasks:**
  - [ ] Rename file `components/charts-v2/builder/data-config/metrics-selector.tsx` → `measure-selector.tsx`
  - [ ] Update component name, test file name, and imports
  - [ ] Update user-facing labels: "Metric" → "Measure" across chart types
  - [ ] Investigate whether legacy `components/charts/MetricsSelector.tsx` is still reachable; delete if dead
  - [ ] Update snapshot / component tests
- **Acceptance criteria:** chart builder shows "Measure" label; all chart types build and render unchanged; no broken imports.

#### Milestone 2: Metric backend — model, API, preview
- **Deliverable:** `Metric` model + migration, CRUD API, preview endpoint, consumer count query. No frontend yet.
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Create `models/metric.py` + migration
  - [ ] Create `schemas/metric_schema.py`
  - [ ] Create `core/metrics/evaluator.py`, `preview.py`, `consumers.py`
  - [ ] Create `api/metrics_api.py` with router, CRUD endpoints, `@has_permission`, `api_response()` wrapping
  - [ ] Add `CAN_MANAGE_METRICS` permission if new one needed
  - [ ] Column-exists validation against warehouse introspection
  - [ ] Uniqueness constraint per org
  - [ ] pytest for evaluator, consumer query, API endpoints
- **Acceptance criteria:** can POST/GET/PUT/DELETE Metrics via API, with correct org scoping, consumer-count returned, delete blocked when consumers exist. pytest passes.

#### Milestone 3: Metric frontend — library + creation form + chart-builder tab
- **Deliverable:** Metrics Library page, Create/Edit Metric form, Measure picker "Saved Metrics" tab with dataset filter.
- **Services:** webapp_v2
- **Key tasks:**
  - [ ] `hooks/api/useMetrics.ts` — list, detail, create, update, delete, preview
  - [ ] `app/metrics/page.tsx` + `app/metrics/[id]/page.tsx`
  - [ ] `components/metrics/*` (library, card, form, preview, delete dialog)
  - [ ] Extend `measure-selector.tsx` with two tabs: Saved Metrics (from `useMetrics({dataset_id})`) and Ad-hoc (existing path)
  - [ ] Extend Chart `extra_config` reader on backend to resolve `mode: "saved"` references
  - [ ] Ensure backward compatibility: charts with no `measure` key continue working
  - [ ] jest tests; playwright E2E create → use-in-chart path
- **Acceptance criteria:** analyst creates a Metric, sees preview value, the same Metric appears in the Measure picker's Saved tab, selecting it renders the chart correctly. Existing charts unaffected.

#### Milestone 4: KPI backend — model, API, RAG/trendline evaluator
- **Deliverable:** `KPI` model + migration, CRUD API, detail endpoint returning value + RAG + trendline + period-over-period.
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] `models/kpi.py` + migration
  - [ ] `schemas/kpi_schema.py`
  - [ ] `core/kpis/rag.py` (pure function, heavily tested)
  - [ ] `core/kpis/evaluator.py` (current value, trendline bucketed by time_grain, period-over-period)
  - [ ] `api/kpis_api.py`
  - [ ] Last-updated-at anchored to last successful pipeline run — reuse existing flow-run lookup helper
  - [ ] pytest for rag.py, evaluator, API
- **Acceptance criteria:** KPI CRUD works; detail endpoint returns current value + correct RAG + trendline array + last-updated timestamp; all RAG permutations covered by tests.

#### Milestone 5: KPI frontend — KPI page + detail drawer + form
- **Deliverable:** KPI page with card grid, detail drawer with full trendline, Create/Edit KPI form.
- **Services:** webapp_v2
- **Key tasks:**
  - [ ] `hooks/api/useKpis.ts`
  - [ ] `app/kpis/page.tsx` + `app/kpis/[id]/page.tsx`
  - [ ] `components/kpis/*` (page, card, detail-drawer, form, trendline)
  - [ ] Threshold UI adapts to direction choice (higher/lower)
  - [ ] Target-optional UX: no RAG when target empty
  - [ ] Search + filter by program tag, metric type
  - [ ] jest component tests
  - [ ] playwright E2E: create Metric → create KPI → see on KPI page
- **Acceptance criteria:** full KPI management flow works end-to-end. All three RAG states render correctly. Trendline has readable X-axis.

#### Milestone 6: KPI dashboard widget (Bhumi's blocker)
- **Deliverable:** KPI widget as a chart type in the dashboard builder, rendering value + target + RAG + trendline; positionable and resizable. Works in live Dashboard, in public Dashboard share, and in ReportSnapshot render.
- **Services:** DDP_backend + webapp_v2
- **Key tasks:**
  - [ ] Extend `DashboardComponentType` enum with `KPI` (migration for enum usage if DB-enforced)
  - [ ] Extend `core/dashboard/` component handler registry
  - [ ] Extend Report render path (`core/reports/`) to route `DashboardComponentType.KPI` components to the KPI evaluator
  - [ ] `components/dashboard-v2/elements/kpi-widget.tsx`
  - [ ] Register KPI widget in chart-type picker of dashboard builder
  - [ ] Ensure widget renders in `dashboard-v2/view/` (public share path)
  - [ ] Ensure widget renders in `components/reports/` detail view
  - [ ] Integration test: take a ReportSnapshot of a Dashboard with a KPI widget; verify snapshot renders correctly
  - [ ] E2E: add KPI widget to Dashboard → view → share publicly → public viewer sees it → take snapshot → snapshot viewer sees it
- **Acceptance criteria:** KPI widget works in Dashboard builder, live view, public share, and ReportSnapshot. Bhumi's quarterly-review dashboard blocker is unblocked.

#### Milestone 7: Edit & delete with consumer awareness
- **Deliverable:** Edit and delete flows for Metric and KPI, with basic consumer check (delete blocked if consumers exist, with named list).
- **Services:** DDP_backend + webapp_v2
- **Key tasks:**
  - [ ] Delete endpoint returns named consumer list when blocked
  - [ ] `metric-delete-dialog.tsx` / `kpi-delete-dialog.tsx` render the list
  - [ ] Edit forms for both Metric and KPI
  - [ ] pytest + jest for the block-when-consumers path
- **Acceptance criteria:** cannot delete a Metric in use; get a list of consumers; delete succeeds once consumers are removed.

---

## 8. Open Questions & Risks

### 8.1 Open questions from the v1 spec (carried; not blocking v1 ship but answered before v2)

1. Derived Metrics evaluation model (query-time vs reference-time) — deferred to v2.
2. Circular reference prevention strategy — deferred to v2.
3. SQL validation rules — deferred to v2.
4. MetricEntry backend restoration (for v2 annotations) — deferred to v2.
5. Reference tracking index strategy (for v2 full blast-radius dialog) — deferred; v1 uses live consumer queries.

### 8.2 Implementation-time risks

| Risk | Mitigation |
|------|------------|
| **Legacy `components/charts/MetricsSelector.tsx` still reachable** | Investigate in M1 before renaming. If reachable, rename there too; if not, delete. |
| **`Chart.extra_config` backward-compat** | Render-time fallback: if no `measure` key present, use the legacy inline fields path. Cover with tests on both shapes. |
| **DashboardComponentType enum addition missed in one render surface** | Checklist in M6 explicitly enumerates all four render surfaces (builder, view, share, report). E2E test covers all four. |
| **ReportSnapshot live-data + Metric formula edits** | Not a technical risk; a communication risk. Release notes must call out that Metric edits retroactively change historical reports. |
| **Preview endpoint load on warehouse** | Debounce 500ms frontend, rate-limit backend. |
| **Permission model for Metrics/KPIs** | If no `CAN_MANAGE_METRICS` style permission exists, add via the existing permissions migration pattern. Clarify with owner of `role_based_access.py`. |

### 8.3 Dependencies on other work

- **Alerts spec (parallel):** Alerts will reference Metrics and KPIs. Must coordinate on schema stability — once `Metric.id` and `KPI.id` are live, Alerts can reference them. No blocking dependency.
- **`access controls` backlog:** Spec explicitly defers per-object ACLs. Current hardcoded `canEdit=true` remains until that separate spec lands.

### 8.4 Performance concerns

- KPI detail endpoint runs `trend_periods` × aggregation queries per call. At `trend_periods=12` and normal NGO dataset sizes this should be fine; if slow, batch into a single SQL with `DATE_TRUNC` grouping.
- Consumer-count query runs on every Metric list render — join across Charts' `extra_config` JSON + KPIs FK. Index carefully; consider denormalizing to a counter column if profiling shows slowness.

### 8.5 Migration risks

Minimal — this is purely additive:
- 2 new tables (`metric`, `kpi`)
- 1 enum value addition (`DashboardComponentType.KPI`)
- 0 data migrations (prototype branch not released; no existing Metric/KPI data to move)

---

## Quality Checklist
- [x] `README.md` and `docs/domain-map.md` were read before research began
- [x] Blast Radius section lists every 1-hop and 2-hop consumer from the domain map
- [x] Every affected surface has a confirmed status (in-scope / deferred / out-of-scope) — none left as `TBD`
- [x] User was asked about any surface the spec did not explicitly address (Explore, Scheduled email, Share link behavior)
- [x] HLD covers all affected services and their interactions
- [x] LLD has concrete schema, API, and component details with real file paths
- [x] Security review covers auth, validation, data access, rate limiting
- [x] Milestones are independently shippable and ordered (rename → Metric → Metric UI → KPI → KPI UI → Widget → Edit/Delete)
- [x] Testing strategy covers unit, integration, E2E, and cross-surface ReportSnapshot render
- [x] References existing codebase patterns (api/core/schema/model layering, SWR hook conventions, data-testid, toast helpers)
