# Metrics & KPIs v1 — Implementation Plan

**Status:** Draft v1
**Date:** 2026-04-21
**Spec:** [Top-level](../spec.md) | [v1 scoped](./spec.md)
**Research:** [research.md](./research.md)
**Domain map:** [docs/domain-map.md](../../../docs/domain-map.md)

---

## 1. Overview

Build the end-to-end chain: **Metric creation → reuse in charts → KPI definition → KPI page → KPI dashboard chart**. This delivers reusable metric definitions, a scannable KPI view for leadership, and KPI charts inside dashboards (Bhumi's mid-June blocker).

**Services affected:**
- **DDP_backend** — New Metric + KPI models, CRUD APIs, warehouse query execution for metric values, reference tracking
- **webapp_v2** — Metrics library page, KPI page, KPI detail drawer, MetricsSelector refactor, KPI dashboard chart

**Not affected:** prefect-proxy (freshness polling deferred to follow-up)

---

## 2. Blast Radius

Derived from `docs/domain-map.md` by traversing 1-hop and 2-hop consumers of the primary entities (Metric, KPI, Chart, Dashboard).

| Surface | Hop | Why affected | Edge type | Status | Notes |
|---------|-----|-------------|-----------|--------|-------|
| **Chart** | 1 from Metric | Charts can reference saved Metrics | `reference` | **In scope** | US-3: MetricsSelector refactor + saved Metric tab |
| **KPI** | 1 from Metric | KPI has required FK to Metric | `reference` | **In scope** | US-4: Define a KPI |
| **Dashboard** | 1 from KPI | KPI chart is a new DashboardComponentType | `compose` | **In scope** | US-7: KPI dashboard chart |
| **Dashboard** | 2 from Metric (via Chart) | Charts with saved Metrics appear on dashboards | `compose` | **Auto-inherited** | No extra work — chart render already handles this |
| **Alert** | 1 from Metric, 1 from KPI | Alerts can fire on Metric/KPI thresholds | `reference` | **Deferred** | Parallel Alerts spec; no integration in v1 |
| **ReportSnapshot** | 2 from KPI (via Dashboard) | New KPI chart type needs render support in `frozen_chart_configs` | `snapshot-of` | **In scope** | Milestone 4: freeze KPI chart data into snapshot configs |
| **Share link (live Dashboard)** | 2 from KPI (via Dashboard) | KPI charts auto-render on publicly shared dashboards | `embed` (live) | **Auto-inherited (OK)** | User confirmed this is acceptable. No extra filtering needed. |
| **Share link (ReportSnapshot)** | 3 from KPI | Same as ReportSnapshot — render support needed | `embed` | **In scope** | Milestone 4: auto-inherited once ReportSnapshot handles KPI charts |
| **Explore** | — | Explore does NOT reuse MetricsSelector (confirmed by Pratiksha 2026-04-21) | — | **Not affected** | Explore keeps its own picker; Saved Metrics land there in a future iteration |
| **Notification** | 3 from KPI (via Alert→Notification) | Only affected if Alerts fire on KPIs | `trigger` | **Not affected** | Blocked by Alert being deferred |

### Known v2 debt from this table
1. **Explore** should eventually get Saved Metrics support via the shared MetricsSelector.
2. **Alert → Metric/KPI integration** ships with the Alerts feature.

---

## 3. High-Level Design (HLD)

### 3.1 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      webapp_v2                          │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ Metrics      │  │ KPI Page     │  │ Dashboard     │ │
│  │ Library      │  │ (cards+RAG)  │  │ Builder       │ │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘ │
│         │                 │                   │         │
│  ┌──────┴─────────────────┴───────────────────┴───────┐ │
│  │              MetricsSelector                       │ │
│  │         (Saved Metrics tab + Ad-hoc tab)           │ │
│  └────────────────────────┬───────────────────────────┘ │
└───────────────────────────┼─────────────────────────────┘
                            │ HTTP (apiGet/apiPost/...)
┌───────────────────────────┼─────────────────────────────┐
│                    DDP_backend                          │
│                            │                            │
│  ┌────────────────┐  ┌────┴───────────┐  ┌───────────┐ │
│  │ /api/metrics/  │  │ /api/kpis/     │  │ /api/     │ │
│  │ CRUD + preview │  │ CRUD + trend   │  │ charts/   │ │
│  └───────┬────────┘  └───────┬────────┘  └─────┬─────┘ │
│          │                   │                  │       │
│  ┌───────┴───────────────────┴──────────────────┴─────┐ │
│  │            MetricService / KPIService              │ │
│  │    (value computation, reference tracking)         │ │
│  └────────────────────────┬───────────────────────────┘ │
│                           │                             │
│  ┌────────────────────────┴───────────────────────────┐ │
│  │  AggQueryBuilder + WarehouseFactory                │ │
│  │  (build SQL, execute against Postgres/BigQuery)    │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

**Metric value computation:**
1. Frontend requests metric preview or KPI current value
2. Backend resolves Metric:
   - Simple (`column` + `aggregation`) → builds `AggQueryBuilder` with `AGG(column)`
   - Expression (`column_expression`) → inlines expression as raw select in query
3. Executes against org's warehouse via `WarehouseFactory`
4. Returns scalar numeric result

**KPI trend computation:**
1. Frontend requests trend data for a KPI
2. Backend resolves KPI → Metric → builds time-series query grouping by KPI's `time_grain`
3. Returns array of `{period, value}` for the last N periods (KPI's `trend_periods`)

**KPI RAG computation:**
- Computed at query time, not stored
- `achievement_pct = (current_value / target_value) * 100`
- For `direction=increase`: green if `achievement_pct >= green_threshold`, amber if `>= amber_threshold`, else red
- For `direction=decrease`: green if `achievement_pct <= green_threshold`, amber if `<= amber_threshold`, else red
- No target → no RAG badge

### 3.3 New API Endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| `POST` | `/api/metrics/` | `can_create_metrics` | Create a metric |
| `GET` | `/api/metrics/` | `can_view_metrics` | List metrics (paginated, search, filter) |
| `GET` | `/api/metrics/{id}/` | `can_view_metrics` | Get single metric |
| `PUT` | `/api/metrics/{id}/` | `can_edit_metrics` | Update metric |
| `DELETE` | `/api/metrics/{id}/` | `can_delete_metrics` | Delete metric (blocked if referenced) |
| `POST` | `/api/metrics/{id}/preview/` | `can_view_metrics` | Compute current value |
| `GET` | `/api/metrics/{id}/consumers/` | `can_view_metrics` | List charts/KPIs using this metric |
| `POST` | `/api/kpis/` | `can_create_kpis` | Create a KPI |
| `GET` | `/api/kpis/` | `can_view_kpis` | List KPIs (paginated, search, filter) |
| `GET` | `/api/kpis/{id}/` | `can_view_kpis` | Get single KPI with current value + RAG |
| `PUT` | `/api/kpis/{id}/` | `can_edit_kpis` | Update KPI |
| `DELETE` | `/api/kpis/{id}/` | `can_delete_kpis` | Delete KPI |
| `GET` | `/api/kpis/{id}/trend/` | `can_view_kpis` | Get trend data (period + value array) |
| `GET` | `/api/kpis/summary/` | `can_view_kpis` | Batch: all KPIs with current values + RAG (for KPI page) |

### 3.4 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **RAG computation** | Query-time, not stored | Values change when warehouse data refreshes; storing would go stale |
| **Metric value caching** | No caching in v1 | Simpler; add Redis caching in v2 if needed |
| **Metric has no filters, no tags** | Metric stores column expression + aggregation (Simple) or raw SQL (SQL mode) | Lean reusable entity; filters and tags belong on consumers |
| **Two definition paths** | Simple (`column` + `aggregation`) or Expression (`column_expression`) — mutually exclusive | Simple covers most cases via dropdowns; Expression for power users writing complex aggregations |
| **Validation on save** | Test query executed against warehouse for both paths | Guardrail against invalid definitions without restricting power users |
| **No "measure" rename** | Keep `ChartMetric` and `MetricsSelector` as-is | Chart builder adds a "Saved Metrics" tab; no terminology change needed |
| **MetricSchema layer** | DB `Metric` model → `MetricSchema` → convert to `ChartMetric` for query | Clean separation: persisted entity → API schema → chart-specific inline shape |
| **KPI-Metric relationship** | Strict FK (required), `on_delete=PROTECT` | Every KPI must have exactly one Metric; delete-blocked pattern from spec |
| **Dashboard KPI chart** | New component type `kpi` in `DashboardComponentType` | Aligns with existing `chart`/`text`/`heading` pattern |
| **Saved Metric in chart builder** | `saved_metric_id` in `extra_config.metrics[]` | Extends existing ChartMetric pattern without breaking ad-hoc mode |
| **Trend time-series query** | Group by `DATE_TRUNC(time_grain, dimension_col)` | Reuses existing `apply_time_grain()` from charts_service |
| **KPI trendline rendering** | ECharts sparkline component | Used for KPI card (KPI page), KPI dashboard chart, and frozen KPI chart in ReportSnapshots |
| **ReportSnapshot** | In scope (Milestone 4) | KPI chart data frozen into `frozen_chart_configs`; commenting support included |
| **Public share** | Auto-inherited | KPI charts render live on shared dashboards; no filtering needed |

---

## 4. Low-Level Design (LLD)

### 4.1 Data Model

#### Metric model (`ddpui/models/metric.py` — new file)

```python
class Metric(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Data source (same pattern as Chart: schema_name + table_name)
    schema_name = models.CharField(max_length=255)
    table_name = models.CharField(max_length=255)

    # Option A: Simple — column + aggregation (dropdown picks)
    column = models.CharField(max_length=255, null=True, blank=True)  # null for COUNT(*)
    aggregation = models.CharField(max_length=30, null=True, blank=True)  # sum/avg/count/min/max/count_distinct

    # Option B: Expression — free-text expression (e.g. "SUM(col_a - col_b) / COUNT(DISTINCT id)")
    # Validated on save by executing a test query against the warehouse
    column_expression = models.TextField(null=True, blank=True)

    # Exactly one of (column + aggregation) or column_expression must be set

    # Org scoping + ownership (same pattern as Chart)
    org = models.ForeignKey("Org", on_delete=models.CASCADE)
    created_by = models.ForeignKey("OrgUser", on_delete=models.CASCADE, related_name="metrics_created")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "metric"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["org", "name"], name="unique_metric_name_per_org")
        ]
```

**Two definition paths (mutually exclusive):**
- **Simple** (`column` + `aggregation`): user picks a column from a dropdown and an aggregation function. Metric computes `AGG(column)`.
- **Expression** (`column_expression`): user writes a free-text expression that computes to a numeric scalar (e.g. `SUM(col_a - col_b) / COUNT(DISTINCT id)`).

**Validation on save:**
- For simple: build `SELECT AGG(column) FROM schema.table LIMIT 1` and execute against warehouse. If query fails, reject with error.
- For expression: execute `SELECT (column_expression) FROM schema.table LIMIT 1` against warehouse. Must return a single numeric value. If query fails or returns non-numeric, reject with error.
- This ensures every saved Metric is a valid, executable definition.

#### KPI model (same file)

```python
class KPI(models.Model):
    id = models.BigAutoField(primary_key=True)
    metric = models.ForeignKey(Metric, on_delete=models.PROTECT, related_name="kpis")

    # Display
    name = models.CharField(max_length=255)  # Display name (defaults to Metric name)

    # Target & direction
    target_value = models.FloatField(null=True, blank=True)
    direction = models.CharField(max_length=10)  # "increase" or "decrease"

    # RAG thresholds (percentage of target)
    green_threshold_pct = models.FloatField(default=100.0)
    amber_threshold_pct = models.FloatField(default=80.0)

    # Time configuration
    time_grain = models.CharField(max_length=20)  # daily/weekly/monthly/quarterly/yearly
    time_dimension_column = models.CharField(max_length=255, null=True, blank=True)
    # ^ Column in the metric's table to use for time-series grouping
    trend_periods = models.IntegerField(default=12)

    # Tags
    metric_type_tag = models.CharField(max_length=20, null=True, blank=True)
    # "input" / "output" / "outcome" / "impact"
    program_tags = models.JSONField(default=list, blank=True)

    # Display order on KPI page
    display_order = models.IntegerField(default=0)

    # Org scoping + ownership
    org = models.ForeignKey("Org", on_delete=models.CASCADE)
    created_by = models.ForeignKey("OrgUser", on_delete=models.CASCADE, related_name="kpis_created")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kpi"
        ordering = ["display_order", "-updated_at"]
```

#### Migration
- Single migration `0158_metric_kpi.py`
- Creates `metric` and `kpi` tables
- Adds permission slugs via `RunPython`

### 4.2 API Design

#### Schemas (`ddpui/schemas/metric_schema.py` — new file)

```python
class MetricCreate(Schema):
    name: str
    description: Optional[str] = None
    schema_name: str
    table_name: str
    # Simple path (mutually exclusive with column_expression)
    column: Optional[str] = None
    aggregation: Optional[str] = None        # sum/avg/count/min/max/count_distinct
    # Expression path (mutually exclusive with column + aggregation)
    column_expression: Optional[str] = None  # e.g. "SUM(col_a - col_b) / COUNT(DISTINCT id)"

class MetricUpdate(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    column: Optional[str] = None
    aggregation: Optional[str] = None
    column_expression: Optional[str] = None

class MetricSchema(Schema):
    """Serializes DB Metric model → API response. Also used when resolving
    saved_metric_id in chart builder before converting to ChartMetric."""
    id: int
    name: str
    description: Optional[str]
    schema_name: str
    table_name: str
    column: Optional[str]
    aggregation: Optional[str]
    column_expression: Optional[str]
    created_at: datetime
    updated_at: datetime

class MetricPreviewResponse(Schema):
    value: Optional[float]
    error: Optional[str] = None

class MetricConsumersResponse(Schema):
    charts: List[dict]   # [{id, title, chart_type}]
    kpis: List[dict]     # [{id, name}]
```

```python
class KPICreate(Schema):
    metric_id: int
    name: Optional[str] = None  # defaults to metric name
    target_value: Optional[float] = None
    direction: str
    green_threshold_pct: float = 100.0
    amber_threshold_pct: float = 80.0
    time_grain: str
    time_dimension_column: Optional[str] = None
    trend_periods: int = 12
    metric_type_tag: Optional[str] = None
    program_tags: List[str] = []

class KPIUpdate(Schema):
    name: Optional[str] = None
    target_value: Optional[float] = None
    direction: Optional[str] = None
    green_threshold_pct: Optional[float] = None
    amber_threshold_pct: Optional[float] = None
    time_grain: Optional[str] = None
    time_dimension_column: Optional[str] = None
    trend_periods: Optional[int] = None
    metric_type_tag: Optional[str] = None
    program_tags: Optional[List[str]] = None

class KPIResponse(Schema):
    id: int
    name: str
    metric: MetricSchema
    target_value: Optional[float]
    direction: str
    green_threshold_pct: float
    amber_threshold_pct: float
    time_grain: str
    time_dimension_column: Optional[str]
    trend_periods: int
    metric_type_tag: Optional[str]
    program_tags: List[str]
    display_order: int
    created_at: datetime
    updated_at: datetime

class KPISummaryResponse(Schema):
    """Used for the KPI page — includes computed values."""
    id: int
    name: str
    metric_name: str
    current_value: Optional[float]
    target_value: Optional[float]
    direction: str
    rag_status: Optional[str]  # "green"/"amber"/"red"/null
    achievement_pct: Optional[float]
    period_over_period_change: Optional[float]
    time_grain: str
    metric_type_tag: Optional[str]
    program_tags: List[str]
    updated_at: datetime

class KPITrendResponse(Schema):
    periods: List[dict]  # [{period: "Jan 2026", value: 1234.0}, ...]
    time_grain: str
```

### 4.3 Backend Logic

#### MetricService (`ddpui/services/metric_service.py` — new file)

Key methods:
- `create_metric(data, orguser)` → validates path-specific fields (simple or expression), runs validation query against warehouse, creates Metric
- `validate_metric(metric, org_warehouse)` → executes test query to verify metric definition is valid
- `get_metric(metric_id, org)` → fetch with org scoping
- `list_metrics(org, search, dataset_filter, page, page_size)` → paginated list
- `update_metric(metric_id, org, orguser, **fields)` → update + re-validate if definition changed
- `delete_metric(metric_id, org, orguser)` → check for consumers first, block if referenced
- `preview_metric_value(metric_id, org)` → build query, execute, return scalar
- `get_metric_consumers(metric_id, org)` → find charts (scan `extra_config` for `saved_metric_id`) and KPIs (FK query)

**Value computation logic** (shared between preview and KPI):
```python
def compute_metric_value(metric: Metric, org_warehouse: OrgWarehouse) -> float:
    warehouse = WarehouseFactory.get_warehouse_client(org_warehouse)
    qb = AggQueryBuilder()
    qb.fetch_from(metric.table_name, metric.schema_name)
    if metric.column_expression:
        # Expression path: expression is the full aggregate (e.g. "SUM(col_a - col_b) / COUNT(DISTINCT id)")
        qb.add_raw_select(metric.column_expression, alias="metric_value")
    else:
        # Simple path: column + aggregation
        qb.add_aggregate_column(metric.column, metric.aggregation, alias="metric_value")
    results = execute_query(warehouse, qb)
    return results[0]["metric_value"] if results else None
```

#### KPIService (`ddpui/services/kpi_service.py` — new file)

Key methods:
- `create_kpi(data, orguser)` → validates metric exists, creates KPI
- `get_kpi(kpi_id, org)` → fetch with org scoping
- `list_kpis(org, search, program_tags, metric_type, page, page_size)` → paginated list
- `update_kpi(kpi_id, org, orguser, **fields)` → update
- `delete_kpi(kpi_id, org, orguser)` → delete KPI + remove from any dashboard components
- `get_kpi_summary(org)` → batch compute all KPIs with current values + RAG
- `get_kpi_trend(kpi_id, org)` → time-series query for trendline

**RAG computation (pure function, no DB):**
```python
def compute_rag_status(current_value, target_value, direction, green_pct, amber_pct) -> str | None:
    if target_value is None or current_value is None:
        return None
    if target_value == 0:
        return None  # avoid division by zero
    achievement = (current_value / target_value) * 100
    if direction == "increase":
        if achievement >= green_pct: return "green"
        if achievement >= amber_pct: return "amber"
        return "red"
    else:  # decrease — lower is better
        if achievement <= green_pct: return "green"
        if achievement <= amber_pct: return "amber"
        return "red"
```

#### API Layer (`ddpui/api/metric_api.py` — new file)

- `metric_router = Router()` registered at `/api/metrics/` in `routes.py`
- `kpi_router = Router()` registered at `/api/kpis/` in `routes.py`
- Thin API layer: validate → delegate to service → return typed response
- Follows same pattern as `charts_api.py` (typed `response=` on endpoints, HttpError for errors)

#### Saved Metric in Chart Builder

When building a chart query and `extra_config.metrics[]` contains `{"saved_metric_id": 42}`:
1. Resolve `Metric.objects.get(id=42, org=org)` in `charts_service.build_chart_data_payload()`
2. Serialize to `MetricSchema`, then convert to `ChartMetric`:
   - Simple: `ChartMetric(column=metric.column, aggregation=metric.aggregation)`
   - Expression: handled separately (inline the `column_expression` into the query as a raw select)
3. Query execution proceeds as normal

> **Open question:** Should the chart store only `saved_metric_id` (resolve at query time) or also snapshot column + aggregation alongside the reference? See §8 Open Questions.

**Modified file:** `ddpui/core/charts/charts_service.py` — `build_chart_data_payload()` function

### 4.4 Frontend Components

#### New Pages

| Route | File | Component |
|-------|------|-----------|
| `/metrics` | `app/metrics/page.tsx` | `<MetricsLibrary />` |
| `/kpis` | `app/kpis/page.tsx` | `<KPIPage />` |

#### New Components

**`components/metrics/`:**
- `metrics-library.tsx` — List view with search, filter-by-dataset
- `metric-form-dialog.tsx` — Create/edit dialog (name, data source, simple [column + aggregation] or expression [column_expression], description, preview with validation)
- `metric-card.tsx` — Card component for library grid
- `metric-preview.tsx` — Shows computed value during creation

**`components/kpis/`:**
- `kpi-page.tsx` — Grid of KPI cards with search + filter
- `kpi-form.tsx` — Create/edit form (metric picker → target → direction → RAG → time grain → tags)
- `kpi-card.tsx` — Scannable card: value + target + RAG badge + trendline + period-over-period + last-updated
- `kpi-detail-drawer.tsx` — Full trend chart, KPI config, edit button
- `kpi-chart.tsx` — Dashboard KPI chart renderer (value + target + RAG + trendline)

**Modified `components/charts/`:**
- Update `MetricsSelector.tsx` — add two tabs: "Saved Metrics" | "Ad-hoc"
- "Saved Metrics" tab: searchable list filtered by current dataset
- "Ad-hoc" tab: existing inline ChartMetric picker (unchanged) + "Save as Metric" action per ad-hoc metric (saves the current column + aggregation to the Metric library)

**Modified `components/dashboard/`:**
- `chart-selector-modal.tsx` — Add "KPI" tab alongside charts
- `dashboard-builder-v2.tsx` — Handle `kpi` component type in layout
- New `kpi-chart-element.tsx` — Renders KPI chart in dashboard grid

#### New Hooks

**`hooks/api/useMetrics.ts`** — SWR hook for list + standalone mutation functions
**`hooks/api/useKPIs.ts`** — SWR hook for list/summary + standalone mutation functions

#### New Types

**`types/metrics.ts`** — Metric, MetricCreate, MetricUpdate interfaces
**`types/kpis.ts`** — KPI, KPISummary, KPICreate, RAGStatus, RAG_COLORS

### 4.5 Navigation Updates

**`components/main-layout.tsx`:**
- Add `/kpis` as "KPIs" nav item (above Charts)
- Keep `/metrics` as "Metrics" nav item
- Remove both from `PRODUCTION_HIDDEN_ITEMS` when ready to ship

---

## 5. Security Review

### Authentication & Authorization
- All new endpoints protected with `@has_permission()`
- Permission slugs: `can_view_metrics`, `can_create_metrics`, `can_edit_metrics`, `can_delete_metrics`, `can_view_kpis`, `can_create_kpis`, `can_edit_kpis`, `can_delete_kpis`
- Migration adds these permissions and assigns them to appropriate roles

### Input Validation
- All user input validated via Pydantic schemas at API boundary
- `aggregation` validated against allowed list: `[sum, avg, count, min, max, count_distinct]` (required when using simple path)
- `column` validated by executing test query on save (simple path)
- `column_expression` free-text but validated by executing test query on save (expression path)
- Exactly one of (`column` + `aggregation`) or `column_expression` must be provided
- `direction` validated: `[increase, decrease]`
- `time_grain` validated: `[daily, weekly, monthly, quarterly, yearly]`
- `metric_type_tag` validated: `[input, output, outcome, impact]`

### Data Access Control
- All queries scoped to `org`: `Metric.objects.filter(org=orguser.org)`
- Metric value queries execute against org's own warehouse only (via `OrgWarehouse.objects.filter(org=org)`)
- No cross-org data leakage possible

### Injection Risks
- **Simple path**: `column` comes from warehouse metadata (user selects from dropdown); queries built via `AggQueryBuilder` (SQLAlchemy parameterized)
- **Expression path**: `column_expression` is free-text entered by user, executed against their own org's warehouse. Risk is limited to the org's own data (no cross-org access). Validation query on save ensures expression is executable.
- All expressions validated on save — invalid definitions rejected before metric is persisted

### Public Share Impact
- KPI charts auto-inherit on live public share URLs (confirmed acceptable)
- KPI data (current value, target, RAG status) becomes visible to anyone with a Dashboard share link
- No PII in KPI values (aggregated warehouse data)

### Rate Limiting
- `preview` and `trend` endpoints execute warehouse queries — potentially expensive
- v1: rely on existing Django middleware rate limiting

---

## 6. Testing Strategy

### Unit Tests

**Backend:**
- `tests/services/test_metric_service.py`:
  - Create metric with simple path (column + aggregation) — valid and invalid
  - Create metric with expression path (column_expression) — valid and invalid
  - Reject metric that has both simple and expression fields set
  - Validation query rejects invalid definitions on save
  - List metrics with search, pagination
  - Delete metric blocked when referenced by KPI
  - Delete metric blocked when referenced by chart (saved_metric_id in extra_config)
  - Preview metric value for both paths (mock warehouse)
- `tests/services/test_kpi_service.py`:
  - Create KPI with valid/invalid metric_id
  - RAG computation: all combinations of direction × thresholds
  - Trend data generation (mock warehouse)
  - Delete KPI removes from dashboard components
- `tests/core/test_rag_computation.py`:
  - Pure function tests for `compute_rag_status()`
  - Edge cases: zero target, null value, boundary values
- `tests/api_tests/test_metric_api.py`:
  - CRUD endpoints with permissions
  - Error responses for validation failures
- `tests/api_tests/test_kpi_api.py`:
  - CRUD endpoints with permissions

**Frontend:**
- `components/metrics/__tests__/`:
  - Metric form validation
  - Metric library search and filter
- `components/kpis/__tests__/`:
  - KPI card renders correct RAG color
  - KPI form defaults (amber threshold based on direction)
- `components/charts/__tests__/MetricsSelector.test.tsx`:
  - Tab switching between Saved Metrics and Ad-hoc
  - Saved metrics filtered by dataset

### Edge Cases
- Simple metric with `COUNT(*)` (null column)
- Expression metric (e.g. `SUM(col_a - col_b) / COUNT(DISTINCT id)`) — validation must confirm it returns numeric
- Expression metric that returns non-numeric — validation rejects
- Metric with both simple and expression fields set — validation rejects
- KPI without target (no RAG)
- KPI with zero target (division by zero protection)
- Empty warehouse table (no rows → null value)
- Dataset/table deleted from warehouse after metric created

---

## 7. Milestones

Each milestone delivers a complete vertical slice (backend + frontend) that is testable on the UI.

### Milestone 1: Metrics + Chart Builder Integration

**Deliverable:** Users can create (simple column+aggregation or free-text expression), browse, edit, and delete metrics from the `/metrics` page with validation on save and live value preview. Chart builder's MetricsSelector gets a "Saved Metrics" tab alongside the existing ad-hoc mode. Charts can reference saved metrics.

**Services:** DDP_backend + webapp_v2

**Backend tasks:**
- [ ] Create `ddpui/models/metric.py` with `Metric` and `KPI` models
- [ ] Create migration `0158_metric_kpi.py` (tables + permission slugs)
- [ ] Create `ddpui/schemas/metric_schema.py` (MetricSchema, MetricCreate, MetricUpdate, etc.)
- [ ] Create `ddpui/services/metric_service.py` (MetricService with CRUD + validation query on save + value computation for both paths)
- [ ] Modify `build_chart_data_payload()` in `charts_service.py` to resolve `saved_metric_id` references
- [ ] When `saved_metric_id` present: resolve Metric → MetricSchema → convert to ChartMetric (simple) or inline expression (expression path)
- [ ] Create `ddpui/api/metric_api.py` (metric_router with CRUD + preview + consumers endpoints)
- [ ] Register `metric_router` at `/api/metrics/` in `routes.py`
- [ ] Write `tests/services/test_metric_service.py` (both paths, validation failures, expression edge cases)
- [ ] Write `tests/api_tests/test_metric_api.py`

**Frontend tasks:**
- [ ] Create `types/metrics.ts` (Metric, MetricCreate, MetricUpdate)
- [ ] Create `hooks/api/useMetrics.ts`
- [ ] Create `components/metrics/metrics-library.tsx` (card grid with search/filter)
- [ ] Create `components/metrics/metric-card.tsx`
- [ ] Create `components/metrics/metric-form-dialog.tsx` (dialog: name, data source, simple [column + aggregation] or expression [column_expression], description, preview with validation)
- [ ] Create `components/metrics/metric-preview.tsx`
- [ ] Create `app/metrics/page.tsx`
- [ ] Update `MetricsSelector.tsx` — add two tabs: "Saved Metrics" | "Ad-hoc"
- [ ] Implement saved metrics tab: fetch from `/api/metrics/?schema_name=X&table_name=Y`
- [ ] Add "Save as Metric" action on ad-hoc metrics in chart builder (opens metric-form-dialog pre-filled with column + aggregation)
- [ ] Update `components/main-layout.tsx` — unhide Metrics nav item
- [ ] Update tests (including existing `MetricsSelector.test.tsx`)
- [ ] Write new frontend tests for metrics library

**UI test plan — what you can verify after this milestone:**
- [ ] Navigate to `/metrics` and see the metrics library (or empty state with CTA)
- [ ] Click "Create Metric" → fill name, pick data source → choose simple path (column + aggregation) → save (validation query runs)
- [ ] Click "Create Metric" → fill name, pick data source → choose expression path (column_expression) → save (validation query runs)
- [ ] Invalid expression → save rejected with error message in preview panel
- [ ] See live preview value during creation
- [ ] Save metric → row appears in table with name, data source, definition, current value
- [ ] Search by name, filter by data source
- [ ] Edit a metric (click row → edit dialog)
- [ ] Delete a metric (blocked if referenced — shows consumer list)
- [ ] Open chart builder → MetricsSelector shows two tabs: "Saved Metrics" and "Ad-hoc"
- [ ] Saved Metrics tab lists metrics filtered to the chart's current data source
- [ ] Select a saved metric → chart preview updates correctly
- [ ] Switch to Ad-hoc tab → existing behavior works exactly as before (no regression)
- [ ] In Ad-hoc tab, click "Save as Metric" on an ad-hoc metric → metric-form-dialog opens pre-filled → save creates a Metric in the library
- [ ] Save chart with saved metric reference → chart renders correctly on dashboard
- [ ] Create a new chart with ad-hoc metric → still works (backward compatibility)

---

### Milestone 2: KPIs End-to-End

**Deliverable:** Users can create KPIs from metrics, see them on the `/kpis` page with values, RAG badges, trendlines, and open a detail drawer.

**Services:** DDP_backend + webapp_v2

**Backend tasks:**
- [ ] Create `ddpui/schemas/kpi_schema.py` (KPI schemas)
- [ ] Create `ddpui/services/kpi_service.py` (KPIService with CRUD + RAG + trend + summary)
- [ ] Implement `compute_rag_status()` pure function
- [ ] Implement `compute_kpi_trend()` time-series query
- [ ] Implement `get_kpi_summary()` batch endpoint
- [ ] Create `ddpui/api/kpi_api.py` (kpi_router with CRUD + trend + summary endpoints)
- [ ] Register `kpi_router` at `/api/kpis/` in `routes.py`
- [ ] Write `tests/services/test_kpi_service.py`
- [ ] Write `tests/core/test_rag_computation.py`
- [ ] Write `tests/api_tests/test_kpi_api.py`

**Frontend tasks:**
- [ ] Create `types/kpis.ts`
- [ ] Create `hooks/api/useKPIs.ts`
- [ ] Create `components/kpis/kpi-page.tsx` (card grid with search/filter)
- [ ] Create `components/kpis/kpi-card.tsx` (value + target + RAG badge + trendline + change + last-updated)
- [ ] Create `components/kpis/kpi-form.tsx` (wizard: metric picker [select existing or create inline via metric-form-dialog] → target/direction/thresholds → trend config → tags/summary)
- [ ] Create `components/kpis/kpi-detail-drawer.tsx` (full trend chart, config, edit)
- [ ] Create `app/kpis/page.tsx`
- [ ] Add KPIs nav item in `main-layout.tsx`
- [ ] Implement trendline using ECharts sparkline (metric line over time + target threshold line)
- [ ] Write frontend tests

**UI test plan — what you can verify after this milestone:**
- [ ] Navigate to `/kpis` and see the KPI page (or empty state)
- [ ] Click "Create KPI" → pick a saved metric → set target, direction, thresholds → set trend frequency → add tags → save
- [ ] In KPI creation Step 1, click "Create a new metric" → metric-form-dialog opens inline → save metric → auto-selected in KPI form → continue to Step 2
- [ ] KPI card appears with: current value (large), target, RAG badge (On Track / At Risk / Off Track), sparkline trendline, period-over-period change, last-updated
- [ ] Search by name, filter by program tag and metric type
- [ ] Click a card → detail drawer slides in with full trend chart, configuration details, edit button
- [ ] Edit a KPI (change target, thresholds)
- [ ] Delete a KPI (confirmation dialog)
- [ ] "Create KPI" shortcut from metric card dropdown (pre-fills metric selection)

---

### Milestone 3: KPI Dashboard Widget

**Deliverable:** KPI appears as a chart type in the dashboard builder. Users can add, position, resize KPI charts. Auto-inherits on live public share views.

**Services:** DDP_backend + webapp_v2

**Backend tasks:**
- [ ] Add `KPI = "kpi"` to `DashboardComponentType` enum
- [ ] Handle KPI component type in dashboard save/load

**Frontend tasks:**
- [ ] Create `components/kpis/kpi-chart.tsx` (KPI chart: value + target + RAG + ECharts sparkline trendline with threshold line)
- [ ] Create `components/dashboard/kpi-chart-element.tsx` (wrapper for dashboard grid)
- [ ] Update `chart-selector-modal.tsx` — add "KPI" tab with KPI selection grid
- [ ] Update `dashboard-builder-v2.tsx` — handle `kpi` component type in layout rendering
- [ ] KPI chart adapts to grid size (small/medium/large via `useResizeObserver`)
- [ ] Write tests

**UI test plan — what you can verify after this milestone:**
- [ ] Open dashboard builder → click "Add Component"
- [ ] See "KPI" tab alongside "Charts" in the selector modal
- [ ] Select a KPI → KPI chart appears on dashboard canvas
- [ ] Widget renders: current value, target, RAG badge, sparkline trendline
- [ ] Drag to reposition, resize handles work
- [ ] Save dashboard → KPI chart persists on reload
- [ ] View shared (public) dashboard → KPI chart renders correctly
- [ ] Edit the KPI (from `/kpis` page) → dashboard KPI chart reflects updated values automatically

---

### Milestone 4: ReportSnapshot KPI Widget Support

**Deliverable:** ReportSnapshots correctly render KPI charts and support commenting on them. When a dashboard containing KPI charts is snapshotted, the KPI chart's current value, target, RAG status, and trendline are frozen into `frozen_chart_configs` and render correctly in snapshot views and shared snapshot links. Users can comment on KPI charts just like they comment on charts.

**Services:** DDP_backend + webapp_v2

**Backend tasks:**
- [ ] Update ReportSnapshot creation logic to handle `kpi` component type in `frozen_chart_configs`
- [ ] When freezing a dashboard with KPI charts: compute and store current value, target, RAG status, trend data
- [ ] Add `KPI = "kpi"` to `CommentTargetType` enum (currently only `CHART` and `SUMMARY`)
- [ ] Update `comment_service.create_comment()` validation to accept `target_type="kpi"` and validate KPI entry exists in `frozen_chart_configs`
- [ ] Update `comment_service.get_comment_states()` to include KPI chart targets
- [ ] Ensure `CommentReadStatus` works with `target_type="kpi"` (uses `chart_id` field — may need renaming to `component_id` or accepting KPI ID in the same field)
- [ ] Write tests for snapshot creation with KPI charts
- [ ] Write tests for commenting on KPI charts (create, read, mention, mark-read)

**Frontend tasks:**
- [ ] Update snapshot render code to handle `kpi` component type in `frozen_chart_configs`
- [ ] Render frozen KPI chart (static value + target + RAG badge + trendline from snapshot data, not live)
- [ ] Add `CommentPopover` support for `targetType="kpi"` on KPI charts in snapshot view
- [ ] Update `CommentIcon` to render on KPI charts with correct state (mentioned/unread/read/none)
- [ ] Ensure shared snapshot links render KPI charts correctly
- [ ] Ensure deep links from comment notification emails work for KPI chart comments (`?commentTarget=kpi&chartId={kpi_id}`)
- [ ] Write tests

**UI test plan — what you can verify after this milestone:**
- [ ] Create a dashboard with KPI charts → take a snapshot
- [ ] Open the snapshot → KPI charts render with the frozen values (not live)
- [ ] Share the snapshot link → KPI charts visible to recipient
- [ ] Edit the KPI after snapshot → snapshot still shows original frozen values
- [ ] Click comment icon on a KPI chart in snapshot → comment popover opens
- [ ] Add a comment with @mention on a KPI chart → notification sent to mentioned user
- [ ] Open notification email link → navigates to snapshot with KPI comment thread open
- [ ] Comment icon shows correct state (unread/read/mentioned) for KPI chart threads

---

## 8. Open Questions & Risks

### Open Questions
1. **Saved metric resolution in charts:** When a chart references a saved metric via `saved_metric_id`, should `extra_config.metrics[]` store (A) only the reference (resolve at every query/render time — extra DB lookup per chart) or (B) reference + snapshot of column/aggregation (no extra lookup, but can drift if metric is edited)? **Decision pending.**

2. **Time dimension column for KPIs:** The KPI needs a date/time column to build the trend query. Should this come from the Metric's dataset (user picks during KPI creation) or from a separate configuration? **Recommendation:** User picks `time_dimension_column` during KPI creation from columns in the metric's table.

3. **Metric value for "current period":** When computing the KPI's current value, should it aggregate all rows (like metric preview) or only the latest period? **Recommendation:** v1 aggregates all rows for current value (matches metric preview). Period-specific values shown only in trend.

4. **KPI summary batch performance:** `GET /api/kpis/summary/` executes one warehouse query per KPI. For orgs with 20+ KPIs, this could be slow. **Mitigation:** v1 accepts this; v2 adds parallel execution or caching.

5. **Dashboard component cleanup:** When a KPI is deleted, should the dashboard `components` JSON be cleaned up automatically? **Recommendation:** Yes, `delete_kpi` removes references from dashboard components JSON.

### Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Warehouse query latency on KPI page (N queries for N KPIs) | Slow page load for orgs with many KPIs | Accept in v1; optimize with parallel queries or caching in v2 |
| Time dimension column may not exist or have wrong type | Trend query fails | Validate column type during KPI creation; show error if not datetime |
| Metric consumer tracking for charts relies on scanning `extra_config` JSON | Slow for orgs with many charts | Simple `Q(extra_config__contains=...)` filter; index if needed |
| MetricsSelector tab addition may break existing chart builder usage | Regression in chart creation | Run full test suite before merging |
| ReportSnapshot won't render KPI charts (v2 debt) | Users snapshot a dashboard with KPI charts → broken render | Document limitation; consider graceful fallback (render placeholder instead of error) |

---

### Quality Checklist
- [x] `README.md` and `docs/domain-map.md` were read before research began
- [x] Blast Radius section lists every 1-hop and 2-hop consumer from the domain map
- [x] Every affected surface has a confirmed status (in-scope / deferred / out-of-scope) — none left as TBD
- [x] User was asked about surfaces the spec did not explicitly address (ReportSnapshot, public share, Explore, Alerts)
- [x] HLD covers all affected services and their interactions
- [x] LLD has concrete schema, API, and component details
- [x] Security review covers auth, validation, and data access
- [x] Milestones are independently shippable and ordered
- [x] Testing strategy covers unit, integration, and edge cases
- [x] References existing codebase patterns

---

*Plan for Milestones 1-4 generated from [v1 spec](./spec.md), [codebase research](./research.md), and [domain map](../../../docs/domain-map.md).*

---

# Milestones 5-8 — Completion Plan

**Date:** 2026-05-03
**Status:** Draft v1
**Context:** Milestones 1-4 are complete. This section covers the remaining gaps between the current implementation (branch `prod/metrics_kpis_alerts` in `DDP_backend_metrics` worktree) and the spec.

Key gaps: `_compute_trend()` method missing (breaks PoP change + report KPI periods), no annotation/timeline system, no metric tags, no metric detail view, orphaned frontend components.

## Updated Blast Radius (confirmed 2026-05-03)

| Surface | Status | Notes |
|---------|--------|-------|
| Chart | in-scope | Metric picker exists, works |
| KPI | in-scope | Core feature |
| Dashboard | in-scope | KPI widget exists, works |
| ReportSnapshot | in-scope | Freezing + rendering exists, needs `_compute_trend` fix |
| Share link (live) | in-scope | Auto-inherits from Dashboard, acceptable |
| Share link (report) | in-scope | Auto-inherits from ReportSnapshot, acceptable |
| Alert | deferred | Alerts spec |
| Explore page | out-of-scope | Per user decision |
| Notification | deferred | Downstream of Alert |

## Open Questions — Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Metric filters (baked-in vs layered) | **Defer to v2** | High complexity, no current user request. Expression path covers simple filter cases. |
| Calculated SQL validation | Blocklist + test query | Already validated via test query. Add keyword blocklist for safety. |
| Time-window: filter annotations? | **No** — annotations show full history | Preserves context, simpler. |
| MetricEntry restoration | Build fresh as `AnnotationEntry` | Clean model, no old code to restore. |

---

### Milestone 5: Fix `_compute_trend` + Wire Orphaned Components

**Deliverable:** `_compute_trend()` works, trend + summary API endpoints exist, KPI detail drawer is wired into the KPI page, report snapshots freeze period data correctly.

**Services:** DDP_backend + webapp_v2

#### Backend (`DDP_backend_metrics`)

**5.1 — Implement `_compute_trend()` in `kpi_service.py`**

The trend logic already exists inline in `compute_kpi_data()` (lines 372-429). Extract it into a standalone `@staticmethod` on `KPIService`:

```python
@staticmethod
def _compute_trend(kpi: KPI, org_warehouse: OrgWarehouse, limit: Optional[int] = None) -> List[dict]:
```

- Reuse the same `AggQueryBuilder` + `apply_time_grain` + `format_time_grain_label` pattern from lines 377-427
- Takes a KPI model instance (not a payload dict) — uses `kpi.metric`, `kpi.time_grain`, `kpi.time_dimension_column`, `kpi.trend_periods`
- Returns `[{period: str, value: float|None}, ...]` ordered ascending
- Place between `_validate_fields` and `get_kpi` (~line 104)
- Remove dead `return periods` at line 534

Keep `compute_kpi_data()` as-is (it works with payload dicts for reports). `_compute_trend()` is the model-based version used by `get_kpi_summary()` and `_freeze_chart_configs()`.

- **File:** `ddpui/services/kpi_service.py`

**5.2 — Add `/api/kpis/{kpi_id}/trend/` endpoint**

```python
@kpi_router.get("/{kpi_id}/trend/")
@has_permission(["can_view_kpis"])
def get_kpi_trend(request, kpi_id: int, periods: int = None):
```

Returns `{periods: [{period, value}, ...], time_grain: str}`. Used by frontend `useKPITrend` hook.

- **File:** `ddpui/api/kpi_api.py`

**5.3 — Add `/api/kpis/summary/` endpoint**

The service method `get_kpi_summary()` exists but has no API route. Add:

```python
@kpi_router.get("/summary/")
@has_permission(["can_view_kpis"])
def get_kpi_summary(request):
```

**Important:** Register this route BEFORE `/{kpi_id}/` to avoid Django Ninja treating "summary" as a kpi_id.

- **File:** `ddpui/api/kpi_api.py`

#### Frontend (`webapp_v2`)

**5.4 — Add missing types to `types/kpis.ts`**

```typescript
export interface KPISummary {
  id: number;
  name: string;
  metric_name: string;
  current_value: number | null;
  target_value: number | null;
  direction: 'increase' | 'decrease';
  rag_status: RAGStatus | null;
  achievement_pct: number | null;
  period_over_period_change: number | null;
  time_grain: string;
  metric_type_tag: string | null;
  program_tags: string[];
  updated_at: string;
}
```

**5.5 — Add `useKPITrend` and `useKPISummary` hooks to `hooks/api/useKPIs.ts`**

```typescript
export function useKPITrend(kpiId: number | null, periods?: number) { ... }
export function useKPISummary() { ... }
```

**5.6 — Wire `KPIDetailDrawer` into `kpi-page.tsx`**

- Add `selectedKpiId` state
- On card click → open drawer (currently opens edit form)
- Import and render `<KPIDetailDrawer>` with `onEdit` callback
- Keep the existing inline `KPICardWithData` component
- **Delete orphaned `kpi-card.tsx`**

#### Testing
- Backend: Unit test `_compute_trend()` with mocked warehouse. Test trend + summary endpoints.
- Frontend: Verify drawer opens, shows trend chart and PoP change. Verify report snapshots freeze period data.

#### UI test plan
- [ ] Navigate to `/kpis` → cards show period-over-period change (was `null` before)
- [ ] Click a KPI card → detail drawer opens with full trend chart
- [ ] Drawer shows: trend chart, PoP change, configuration details, Edit button
- [ ] Create report snapshot from dashboard with KPI → frozen KPI has period data
- [ ] View report → KPI widget shows trendline (was empty before)

---

### Milestone 6: Metric Tags + Detail View + Edit Blast-Radius

**Deliverable:** Metrics have tags (searchable/filterable), a detail drawer with references panel, and edit confirmation showing affected consumers.

**Services:** DDP_backend + webapp_v2

#### Backend

**6.1 — Add `tags` JSONField to Metric model**

```python
tags = models.JSONField(default=list, blank=True)
```

New migration. Add `tags` to `MetricCreate`, `MetricUpdate`, `MetricResponse` schemas. Add `tag` query param to `list_metrics` with `Q(tags__contains=[tag])` filter.

- **Files:** `ddpui/models/metric.py`, `ddpui/schemas/metric_schema.py`, `ddpui/services/metric_service.py`, `ddpui/api/metric_api.py`
- **New:** migration file

#### Frontend

**6.2 — Add tags to Metric form and library**

- Add comma-separated tags input to `metric-form-dialog.tsx` (same pattern as `programTagsInput` in `kpi-form.tsx`)
- Show tag badges on metric rows in `metrics-library.tsx`
- Add tag filter to library header

**6.3 — Build Metric Detail Drawer**

New component: `components/metrics/metric-detail-drawer.tsx`

Uses `Sheet` (Shadcn). Sections:
- Full definition: dataset, column/expression, aggregation, description, tags
- References panel: calls `getMetricConsumers(id)` → "Used by N charts, M KPIs" with names
- Current value: calls existing preview endpoint
- Edit / Delete buttons

Wire into `metrics-library.tsx` — clicking a metric row opens the drawer.

**6.4 — Add edit blast-radius confirmation**

In `metric-form-dialog.tsx`, before submitting an update:
1. Call `getMetricConsumers(metricId)`
2. If consumers exist → show `ConfirmationDialog`: "This change affects N charts and M KPIs. Changes propagate immediately. Continue?"
3. On confirm → submit

#### Testing
- Backend: Test tags CRUD and filtering.
- Frontend: Test detail drawer renders references. Test edit confirmation shows when consumers exist.

#### UI test plan
- [ ] Create a metric with tags → tags appear in library table
- [ ] Search/filter by tag → library filters correctly
- [ ] Click a metric row → detail drawer opens with full definition + references
- [ ] Edit a metric that has KPIs → confirmation dialog shows affected consumers
- [ ] Confirm edit → metric updates, KPIs reflect new values

---

### Milestone 7: KPI Annotations (AnnotationEntry)

**Deliverable:** KPIs have a timeline of annotations (comments + beneficiary quotes) with auto-captured snapshots.

**Services:** DDP_backend + webapp_v2

#### Backend

**7.1 — Add `AnnotationEntry` model to `models/metric.py`**

```python
ENTRY_TYPE_CHOICES = [("comment", "Comment"), ("quote", "Beneficiary Quote")]

class AnnotationEntry(models.Model):
    kpi = models.ForeignKey(KPI, on_delete=CASCADE, related_name="annotation_entries")
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES)
    period_key = models.CharField(max_length=50)  # e.g. "Jan 2026"
    content = models.TextField()
    attribution = models.CharField(max_length=255, null=True, blank=True)  # quotes only
    snapshot_value = models.FloatField(null=True, blank=True)
    snapshot_rag = models.CharField(max_length=10, null=True, blank=True)
    snapshot_achievement_pct = models.FloatField(null=True, blank=True)
    created_by = models.ForeignKey(OrgUser, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
```

- **New:** migration file

**7.2 — Add annotation schemas to `kpi_schema.py`**

```python
class AnnotationEntryCreate(Schema):
    entry_type: str  # "comment" or "quote"
    period_key: str
    content: str
    attribution: Optional[str] = None

class AnnotationEntryResponse(Schema):
    id: int
    entry_type: str
    period_key: str
    content: str
    attribution: Optional[str]
    snapshot_value: Optional[float]
    snapshot_rag: Optional[str]
    snapshot_achievement_pct: Optional[float]
    created_by_name: str
    created_at: datetime
```

**7.3 — Add annotation service methods to `kpi_service.py`**

- `list_entries(kpi_id, org)` → returns entries for a KPI
- `create_entry(kpi_id, org, orguser, payload)` → validates KPI, computes current value + RAG snapshot via `MetricService.compute_metric_value()` and `compute_rag_status()`, creates entry
- `delete_entry(kpi_id, entry_id, org, orguser)` → validates ownership (author or edit permission)

**7.4 — Add annotation endpoints to `kpi_api.py`**

```
GET    /api/kpis/{kpi_id}/entries/                  → list entries
POST   /api/kpis/{kpi_id}/entries/                  → create entry (auto-snapshots)
DELETE /api/kpis/{kpi_id}/entries/{entry_id}/        → delete entry
```

Permissions: `can_view_kpis` for list, `can_edit_kpis` for create/delete.

#### Frontend

**7.5 — Add annotation types and hooks**

Types in `types/kpis.ts`:
```typescript
export interface AnnotationEntry {
  id: number;
  entry_type: 'comment' | 'quote';
  period_key: string;
  content: string;
  attribution: string | null;
  snapshot_value: number | null;
  snapshot_rag: RAGStatus | null;
  snapshot_achievement_pct: number | null;
  created_by_name: string;
  created_at: string;
}
```

Hooks in `hooks/api/useKPIs.ts`:
```typescript
export function useAnnotationEntries(kpiId: number | null) { ... }
export async function createAnnotationEntry(kpiId: number, data: ...) { ... }
export async function deleteAnnotationEntry(kpiId: number, entryId: number) { ... }
```

**7.6 — Add annotation timeline to `KPIDetailDrawer`**

Extend `kpi-detail-drawer.tsx`:
- "Add Entry" button → opens a form/popover
- Entry form: type selector (Comment/Quote tabs), period dropdown (from trend periods), content textarea, attribution field (quote only)
- Timeline section below the trend chart: entries grouped by `period_key`, each showing type badge, content, attribution, snapshot value+RAG, delta since previous period, author, timestamp
- Delete button on entries (with confirmation)

Period dropdown values come from `useKPITrend` response (the period labels).

#### Testing
- Backend: Test CRUD for entries. Test snapshot captures correct value/RAG. Test delete permissions.
- Frontend: Test entry form, timeline grouping, delete.

#### UI test plan
- [ ] Open KPI detail drawer → "Add Entry" button visible
- [ ] Click "Add Entry" → form appears with type selector, period dropdown, content field
- [ ] Select "Beneficiary Quote" → attribution field appears
- [ ] Submit entry → appears in timeline with auto-captured value + RAG snapshot
- [ ] Multiple entries per period → grouped correctly
- [ ] Delete an entry → removed with confirmation
- [ ] Entry shows delta since previous period (e.g. "+230 since last month")

---

### Milestone 8: UX Polish

**Deliverable:** Time-window selector in KPI drawer, SQL expression safety blocklist.

**Services:** DDP_backend + webapp_v2

#### Frontend

**8.1 — KPI time-window selector in drawer**

Add a `<Select>` above the trend chart in `kpi-detail-drawer.tsx`. Options computed from `time_grain`:
- monthly: "Last 6 / 12 / 24 months"
- quarterly: "Last 4 / 8 / 12 quarters"
- yearly: "Last 3 / 5 / 10 years"

Default: KPI's configured `trend_periods`. Session-only (component state). Pass selected count to `useKPITrend(kpiId, selectedPeriods)`. Annotations are NOT filtered — full history always shown.

#### Backend

**8.2 — SQL expression blocklist**

In `MetricService.validate_metric_definition()`, when `column_expression` is set, add:
```python
BLOCKED_KEYWORDS = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"]
upper_expr = column_expression.upper()
for kw in BLOCKED_KEYWORDS:
    if re.search(rf'\b{kw}\b', upper_expr):
        raise MetricValidationError(f"SQL expressions cannot contain '{kw}' statements")
```

#### Testing
- Manual: verify time-window selector changes trend range, annotations stay visible.
- Backend: test SQL blocklist rejects mutating statements.

#### UI test plan
- [ ] Open KPI drawer → time-window selector above trend chart
- [ ] Change window from "Last 12 months" to "Last 6 months" → trendline updates
- [ ] Annotations stay visible regardless of window selection
- [ ] Create metric with SQL expression containing "DROP" → rejected with error

---

## Milestone Dependency Graph (5-8)

```
M5 (fix _compute_trend + wire drawer)  ←── start here
 │
 ├── M6 (metric tags + detail view)    ←── can run in parallel with M5
 │
 └── M7 (annotations)                  ←── depends on M5 (needs trend endpoint for period dropdown)
      │
      └── M8 (polish)                  ←── depends on M7 (time-window in same drawer)
```

**Start M5 and M6 in parallel.** M7 follows once M5's trend endpoint is ready.

## Key Files Summary (M5-M8)

| File | Milestones | Changes |
|------|-----------|---------|
| `DDP_backend_metrics/ddpui/services/kpi_service.py` | 5, 7 | Add `_compute_trend()`, annotation methods, remove dead code |
| `DDP_backend_metrics/ddpui/api/kpi_api.py` | 5, 7 | Add trend, summary, annotation endpoints |
| `DDP_backend_metrics/ddpui/models/metric.py` | 6, 7 | Add `tags` field, `AnnotationEntry` model |
| `DDP_backend_metrics/ddpui/schemas/metric_schema.py` | 6 | Add `tags` to schemas |
| `DDP_backend_metrics/ddpui/schemas/kpi_schema.py` | 7 | Add annotation schemas |
| `DDP_backend_metrics/ddpui/services/metric_service.py` | 6, 8 | Tags handling, SQL blocklist |
| `DDP_backend_metrics/ddpui/api/metric_api.py` | 6 | Add tag filter param |
| `webapp_v2/types/kpis.ts` | 5, 7 | Add KPISummary, AnnotationEntry |
| `webapp_v2/types/metrics.ts` | 6 | Add tags |
| `webapp_v2/hooks/api/useKPIs.ts` | 5, 7 | Add useKPITrend, useKPISummary, annotation hooks |
| `webapp_v2/components/kpis/kpi-page.tsx` | 5 | Wire detail drawer |
| `webapp_v2/components/kpis/kpi-detail-drawer.tsx` | 5, 7, 8 | Fix imports, add timeline, time-window |
| `webapp_v2/components/metrics/metrics-library.tsx` | 6 | Tags display/filter, detail drawer trigger |
| `webapp_v2/components/metrics/metric-form-dialog.tsx` | 6 | Tags input, edit blast-radius |
| **New:** `webapp_v2/components/metrics/metric-detail-drawer.tsx` | 6 | Metric detail view |
| **New:** 2 migration files | 6, 7 | tags field, AnnotationEntry model |
| **Delete:** `webapp_v2/components/kpis/kpi-card.tsx` | 5 | Orphaned, replaced by inline KPICardWithData |

## Verification (M5-M8)

After each milestone:
1. Backend: `cd DDP_backend_metrics && uv run pytest ddpui/tests` — all tests pass
2. Frontend: `cd webapp_v2 && npm run lint && npm test` — no regressions
3. Manual: start services via PM2, verify end-to-end in the browser

End-to-end flow after all milestones:
1. Create a Metric with tags → verify in library with search/filter
2. Open Metric detail drawer → verify references panel and current value
3. Edit Metric → verify blast-radius confirmation appears
4. Create a KPI from Metric → verify on KPI page with PoP change
5. Open KPI drawer → verify trend chart, time-window selector, add annotation entry
6. Add KPI to dashboard → verify widget renders
7. Create report snapshot from dashboard → verify KPI data is frozen
8. View report → verify KPI widget renders from frozen data
