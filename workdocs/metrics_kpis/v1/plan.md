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
- **webapp_v2** — Metrics library page, KPI page, KPI detail drawer, MeasureSelector refactor, KPI dashboard chart

**Not affected:** prefect-proxy (freshness polling deferred to follow-up)

---

## 2. Blast Radius

Derived from `docs/domain-map.md` by traversing 1-hop and 2-hop consumers of the primary entities (Metric, KPI, Chart, Dashboard).

| Surface | Hop | Why affected | Edge type | Status | Notes |
|---------|-----|-------------|-----------|--------|-------|
| **Chart** | 1 from Metric | Charts can reference saved Metrics as Measures | `reference` | **In scope** | US-3: MeasureSelector refactor + saved Metric tab |
| **KPI** | 1 from Metric | KPI has required FK to Metric | `reference` | **In scope** | US-4: Define a KPI |
| **Dashboard** | 1 from KPI | KPI chart is a new DashboardComponentType | `compose` | **In scope** | US-7: KPI dashboard chart |
| **Dashboard** | 2 from Metric (via Chart) | Charts with saved Metrics appear on dashboards | `compose` | **Auto-inherited** | No extra work — chart render already handles this |
| **Alert** | 1 from Metric, 1 from KPI | Alerts can fire on Metric/KPI thresholds | `reference` | **Deferred** | Parallel Alerts spec; no integration in v1 |
| **ReportSnapshot** | 2 from KPI (via Dashboard) | New KPI chart type needs render support in `frozen_chart_configs` | `snapshot-of` | **In scope** | Milestone 4: freeze KPI chart data into snapshot configs |
| **Share link (live Dashboard)** | 2 from KPI (via Dashboard) | KPI charts auto-render on publicly shared dashboards | `embed` (live) | **Auto-inherited (OK)** | User confirmed this is acceptable. No extra filtering needed. |
| **Share link (ReportSnapshot)** | 3 from KPI | Same as ReportSnapshot — render support needed | `embed` | **In scope** | Milestone 4: auto-inherited once ReportSnapshot handles KPI charts |
| **Explore** | — | Explore does NOT reuse MeasureSelector (confirmed by Pratiksha 2026-04-21) | — | **Not affected** | Explore keeps its own picker; Saved Metrics land there in a future iteration |
| **Notification** | 3 from KPI (via Alert→Notification) | Only affected if Alerts fire on KPIs | `trigger` | **Not affected** | Blocked by Alert being deferred |

### Known v2 debt from this table
1. **Explore** should eventually get Saved Metrics support via the shared MeasureSelector.
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
│  │              MeasureSelector                       │ │
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
2. Backend resolves Metric → builds `AggQueryBuilder` with column + aggregation
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
| **Metric has no filters** | Metric stores only column + aggregation | Filters belong on the chart or KPI level, not on the reusable metric definition |
| **KPI-Metric relationship** | Strict FK (required), `on_delete=PROTECT` | Every KPI must have exactly one Metric; delete-blocked pattern from spec |
| **Dashboard KPI chart** | New component type `kpi` in `DashboardComponentType` | Aligns with existing `chart`/`text`/`heading` pattern |
| **Saved Metric in chart builder** | `saved_metric_id` in `extra_config.metrics[]` | Extends existing ChartMeasure pattern without breaking ad-hoc mode |
| **ChartMetric → ChartMeasure rename** | Rename existing `ChartMetric` schema to `ChartMeasure` everywhere | One `Metric` entity in the codebase; inline chart configs use "measure" terminology |
| **MetricSchema layer** | DB `Metric` model → `MetricSchema` → convert to `ChartMeasure` for query | Clean separation: persisted entity → API schema → chart-specific inline shape |
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

    # Simple mode: column + aggregation
    column = models.CharField(max_length=255, null=True, blank=True)  # null for COUNT(*)
    aggregation = models.CharField(max_length=30)  # sum/avg/count/min/max/count_distinct

    # Tags
    tags = models.JSONField(default=list, blank=True)  # ["education", "quarterly"]

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
    column: Optional[str] = None
    aggregation: str
    tags: List[str] = []

class MetricUpdate(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    column: Optional[str] = None
    aggregation: Optional[str] = None
    tags: Optional[List[str]] = None

class MetricSchema(Schema):
    """Serializes DB Metric model → API response. Also used when resolving
    saved_metric_id in chart builder before converting to ChartMeasure."""
    id: int
    name: str
    description: Optional[str]
    schema_name: str
    table_name: str
    column: Optional[str]
    aggregation: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime

class MetricPreviewResponse(Schema):
    value: Optional[float]
    error: Optional[str] = None

class MetricConsumersResponse(Schema):
    charts: List[dict]   # [{id, title, chart_type}]
    kpis: List[dict]     # [{id, name}]
```

#### ChartMeasure (`ddpui/schemas/chart_schema.py` — rename from `ChartMetric`)

```python
class ChartMeasure(Schema):
    """Inline measure definition for chart extra_config.metrics[].
    Renamed from ChartMetric to avoid confusion with the Metric DB entity."""
    column: Optional[str] = None  # null for COUNT(*)
    aggregation: str
    alias: Optional[str] = None
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
- `create_metric(data, orguser)` → validates, creates Metric
- `get_metric(metric_id, org)` → fetch with org scoping
- `list_metrics(org, search, dataset_filter, tags, page, page_size)` → paginated list
- `update_metric(metric_id, org, orguser, **fields)` → update
- `delete_metric(metric_id, org, orguser)` → check for consumers first, block if referenced
- `preview_metric_value(metric_id, org)` → build query, execute, return scalar
- `get_metric_consumers(metric_id, org)` → find charts (scan `extra_config` for `saved_metric_id`) and KPIs (FK query)

**Value computation logic** (shared between preview and KPI):
```python
def compute_metric_value(metric: Metric, org_warehouse: OrgWarehouse) -> float:
    warehouse = WarehouseFactory.get_warehouse_client(org_warehouse)
    qb = AggQueryBuilder()
    qb.fetch_from(metric.table_name, metric.schema_name)
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
2. Serialize to `MetricSchema`, then convert to `ChartMeasure(column=metric.column, aggregation=metric.aggregation)`
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
- `metrics-library.tsx` — List view with search, filter-by-dataset, filter-by-tag
- `metric-form.tsx` — Create/edit form (dataset picker → column picker → aggregation → name/desc/tags → preview)
- `metric-card.tsx` — Card component for library grid
- `metric-preview.tsx` — Shows computed value during creation

**`components/kpis/`:**
- `kpi-page.tsx` — Grid of KPI cards with search + filter
- `kpi-form.tsx` — Create/edit form (metric picker → target → direction → RAG → time grain → tags)
- `kpi-card.tsx` — Scannable card: value + target + RAG badge + trendline + period-over-period + last-updated
- `kpi-detail-drawer.tsx` — Full trend chart, KPI config, edit button
- `kpi-chart.tsx` — Dashboard KPI chart renderer (value + target + RAG + trendline)

**Modified `components/charts/`:**
- Rename `MetricsSelector.tsx` → `MeasureSelector.tsx`
- Add two tabs: "Saved Metrics" | "Ad-hoc"
- "Saved Metrics" tab: searchable list filtered by current dataset
- Update all imports across `ChartDataConfigurationV3.tsx`, `MapDataConfigurationV3.tsx`, tests

**Modified `components/dashboard/`:**
- `chart-selector-modal.tsx` — Add "KPI" tab alongside charts
- `dashboard-builder-v2.tsx` — Handle `kpi` component type in layout
- New `kpi-chart-element.tsx` — Renders KPI chart in dashboard grid

#### New Hooks

**`hooks/api/useMetrics.ts`** — SWR hook for list + standalone mutation functions
**`hooks/api/useKPIs.ts`** — SWR hook for list/summary + standalone mutation functions

#### New Types

**`types/metrics.ts`** — Metric, MetricCreate, MetricUpdate interfaces
**`types/charts.ts`** — Rename `ChartMetric` → `ChartMeasure` interface
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
- `aggregation` validated against allowed list: `[sum, avg, count, min, max, count_distinct]`
- `direction` validated: `[increase, decrease]`
- `time_grain` validated: `[daily, weekly, monthly, quarterly, yearly]`
- `metric_type_tag` validated: `[input, output, outcome, impact]`

### Data Access Control
- All queries scoped to `org`: `Metric.objects.filter(org=orguser.org)`
- Metric value queries execute against org's own warehouse only (via `OrgWarehouse.objects.filter(org=org)`)
- No cross-org data leakage possible

### Injection Risks
- **No raw SQL**: All warehouse queries built via `AggQueryBuilder` (SQLAlchemy parameterized)
- Column/table names come from warehouse metadata (user selects from dropdown, not free text)

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
  - Create metric with valid/invalid data
  - List metrics with search, pagination
  - Delete metric blocked when referenced by KPI
  - Delete metric blocked when referenced by chart (saved_metric_id in extra_config)
  - Preview metric value (mock warehouse)
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
- `components/charts/__tests__/MeasureSelector.test.tsx`:
  - Tab switching between Saved Metrics and Ad-hoc
  - Saved metrics filtered by dataset

### Edge Cases
- Metric with `COUNT(*)` (null column)
- KPI without target (no RAG)
- KPI with zero target (division by zero protection)
- Empty warehouse table (no rows → null value)
- Dataset/table deleted from warehouse after metric created

---

## 7. Milestones

Each milestone delivers a complete vertical slice (backend + frontend) that is testable on the UI.

### Milestone 1: Metrics + Chart Builder Integration

**Deliverable:** Users can create, browse, edit, and delete metrics from the `/metrics` page with live value preview. Chart builder uses metrics via a refactored MeasureSelector with "Saved Metrics" and "Custom (Ad-hoc)" tabs. Existing `ChartMetric` renamed to `ChartMeasure` throughout.

**Services:** DDP_backend + webapp_v2

**Backend tasks:**
- [ ] Create `ddpui/models/metric.py` with `Metric` and `KPI` models
- [ ] Create migration `0158_metric_kpi.py` (tables + permission slugs)
- [ ] Create `ddpui/schemas/metric_schema.py` (MetricSchema, MetricCreate, MetricUpdate, etc.)
- [ ] Rename `ChartMetric` → `ChartMeasure` in `chart_schema.py` and all usages across backend
- [ ] Create `ddpui/services/metric_service.py` (MetricService with CRUD + value computation)
- [ ] Modify `build_chart_data_payload()` in `charts_service.py` to resolve `saved_metric_id` references
- [ ] When `saved_metric_id` present: resolve Metric → MetricSchema → convert to ChartMeasure
- [ ] Create `ddpui/api/metric_api.py` (metric_router with CRUD + preview + consumers endpoints)
- [ ] Register `metric_router` at `/api/metrics/` in `routes.py`
- [ ] Write `tests/services/test_metric_service.py`
- [ ] Write `tests/api_tests/test_metric_api.py`

**Frontend tasks:**
- [ ] Create `types/metrics.ts`
- [ ] Rename `ChartMetric` → `ChartMeasure` in `types/charts.ts` and all frontend usages
- [ ] Create `hooks/api/useMetrics.ts`
- [ ] Create `components/metrics/metrics-library.tsx` (card grid with search/filter)
- [ ] Create `components/metrics/metric-card.tsx`
- [ ] Create `components/metrics/metric-form.tsx` (wizard: data source → column → aggregation → name/tags → preview)
- [ ] Create `components/metrics/metric-preview.tsx`
- [ ] Create `app/metrics/page.tsx`
- [ ] Rename `MetricsSelector.tsx` → `MeasureSelector.tsx`
- [ ] Add two-tab UI: "Saved Metrics" | "Custom (Ad-hoc)"
- [ ] Implement saved metrics tab: fetch from `/api/metrics/?schema_name=X&table_name=Y`
- [ ] Update `ChartDataConfigurationV3.tsx` imports/usage
- [ ] Update `MapDataConfigurationV3.tsx` imports/usage
- [ ] Update labels from "Metric" to "Measure" across all chart type configs
- [ ] Update `components/main-layout.tsx` — unhide Metrics nav item
- [ ] Update tests (including existing `MetricsSelector.test.tsx`)
- [ ] Write new frontend tests for metrics library

**UI test plan — what you can verify after this milestone:**
- [ ] Navigate to `/metrics` and see the metrics library (or empty state with CTA)
- [ ] Click "Create Metric" → step through wizard: pick data source, field, calculation type
- [ ] See live preview value at each step
- [ ] Save metric → card appears in library with name, description, tags, current value
- [ ] Search by name, filter by data source
- [ ] Edit a metric (click card → edit form)
- [ ] Delete a metric (blocked if referenced — shows consumer list)
- [ ] Open chart builder → see "Measure" section (not "Metrics")
- [ ] Measure picker shows two tabs: "Saved Metrics" and "Custom (Ad-hoc)"
- [ ] Saved Metrics tab lists metrics filtered to the chart's current data source
- [ ] Select a saved metric → chart preview updates correctly
- [ ] Switch to Custom tab → existing ad-hoc behavior works exactly as before (no regression)
- [ ] Save chart with saved metric reference → chart renders correctly on dashboard
- [ ] Create a new chart with ad-hoc measure → still works (backward compatibility)

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
- [ ] Create `components/kpis/kpi-form.tsx` (wizard: metric picker → target/direction/thresholds → trend config → tags/summary)
- [ ] Create `components/kpis/kpi-detail-drawer.tsx` (full trend chart, config, edit)
- [ ] Create `app/kpis/page.tsx`
- [ ] Add KPIs nav item in `main-layout.tsx`
- [ ] Implement trendline using ECharts sparkline (metric line over time + target threshold line)
- [ ] Write frontend tests

**UI test plan — what you can verify after this milestone:**
- [ ] Navigate to `/kpis` and see the KPI page (or empty state)
- [ ] Click "Create KPI" → pick a saved metric → set target, direction, thresholds → set trend frequency → add tags → save
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
| MeasureSelector rename may break existing chart builder usage | Regression in chart creation | Update all imports; run full test suite before merging |
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

*Plan generated from [v1 spec](./spec.md), [codebase research](./research.md), and [domain map](../../../docs/domain-map.md).*
