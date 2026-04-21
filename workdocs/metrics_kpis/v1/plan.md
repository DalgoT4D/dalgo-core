# Metrics & KPIs v1 — Implementation Plan

**Status:** Draft v1
**Date:** 2026-04-21
**Spec:** [Top-level](../spec.md) | [v1 scoped](./spec.md)
**Research:** [research.md](./research.md)

---

## 1. Overview

Build the end-to-end chain: **Metric creation → reuse in charts → KPI definition → KPI page → KPI dashboard widget**. This delivers reusable metric definitions, a scannable KPI view for leadership, and KPI widgets inside dashboards (Bhumi's mid-June blocker).

**Services affected:**
- **DDP_backend** — New Metric + KPI models, CRUD APIs, warehouse query execution for metric values, reference tracking
- **webapp_v2** — Metrics library page, KPI page, KPI detail drawer, MeasureSelector refactor, KPI dashboard widget

**Not affected:** prefect-proxy (freshness polling deferred to follow-up)

---

## 2. High-Level Design (HLD)

### 2.1 System Architecture

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

### 2.2 Data Flow

**Metric value computation:**
1. Frontend requests metric preview or KPI current value
2. Backend resolves Metric → builds `AggQueryBuilder` with column + aggregation + filters
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

### 2.3 New API Endpoints

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

### 2.4 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **RAG computation** | Query-time, not stored | Values change when warehouse data refreshes; storing would go stale |
| **Metric value caching** | No caching in v1 | Simpler; add Redis caching in v2 if needed |
| **Metric filters storage** | JSONField on Metric model | Matches chart `extra_config` pattern; avoids extra filter table |
| **KPI-Metric relationship** | Strict FK (required) | Every KPI must have exactly one Metric |
| **Dashboard KPI widget** | New component type `kpi` in `DashboardComponentType` | Aligns with existing `chart`/`text`/`heading` pattern |
| **Saved Metric in chart builder** | `saved_metric_id` in `extra_config.metrics[]` | Extends existing ChartMetric pattern without breaking ad-hoc mode |
| **Trend time-series query** | Group by `DATE_TRUNC(time_grain, dimension_col)` | Reuses existing `apply_time_grain()` from charts_service |

---

## 3. Low-Level Design (LLD)

### 3.1 Data Model

#### Metric model (`ddpui/models/metric.py` — new file)

```python
class Metric(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Data source
    schema_name = models.CharField(max_length=255)
    table_name = models.CharField(max_length=255)

    # Simple mode: column + aggregation
    column = models.CharField(max_length=255, null=True, blank=True)  # null for COUNT(*)
    aggregation = models.CharField(max_length=30)  # sum/avg/count/min/max/count_distinct

    # Optional baked-in filters
    filters = models.JSONField(default=list, blank=True)
    # Format: [{"column": "status", "operator": "equals", "value": "active"}, ...]

    # Organization and tags
    tags = models.JSONField(default=list, blank=True)  # ["education", "quarterly"]
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

#### KPI model (`ddpui/models/metric.py` — same file)

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
    # "input"/"output"/"outcome"/"impact"
    program_tags = models.JSONField(default=list, blank=True)

    # Display order on KPI page
    display_order = models.IntegerField(default=0)

    # Organization
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
- Adds permission slugs for metrics and KPIs to the `Permission` table via `RunPython`

### 3.2 API Design

#### Schemas (`ddpui/schemas/metric_schema.py` — new file)

```python
class MetricFilter(Schema):
    column: str
    operator: str  # equals, not_equals, greater_than, less_than, in, not_in
    value: Any

class MetricCreate(Schema):
    name: str
    description: Optional[str] = None
    schema_name: str
    table_name: str
    column: Optional[str] = None  # null for COUNT(*)
    aggregation: str
    filters: List[MetricFilter] = []
    tags: List[str] = []

class MetricUpdate(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    column: Optional[str] = None
    aggregation: Optional[str] = None
    filters: Optional[List[MetricFilter]] = None
    tags: Optional[List[str]] = None

class MetricResponse(Schema):
    id: int
    name: str
    description: Optional[str]
    schema_name: str
    table_name: str
    column: Optional[str]
    aggregation: str
    filters: List[dict]
    tags: List[str]
    created_at: datetime
    updated_at: datetime

class MetricPreviewResponse(Schema):
    value: Optional[float]
    error: Optional[str] = None

class MetricConsumersResponse(Schema):
    charts: List[dict]  # [{id, title, chart_type}]
    kpis: List[dict]    # [{id, name}]
```

```python
class KPICreate(Schema):
    metric_id: int
    name: Optional[str] = None  # defaults to metric name
    target_value: Optional[float] = None
    direction: str  # "increase" or "decrease"
    green_threshold_pct: float = 100.0
    amber_threshold_pct: float = 80.0
    time_grain: str  # daily/weekly/monthly/quarterly/yearly
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
    metric: MetricResponse
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

### 3.3 Backend Logic

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

    # Apply baked-in filters
    for f in metric.filters:
        qb.where_clause(build_filter_clause(f))

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

**Trend query logic:**
```python
def compute_kpi_trend(kpi: KPI, org_warehouse: OrgWarehouse) -> list[dict]:
    metric = kpi.metric
    warehouse = WarehouseFactory.get_warehouse_client(org_warehouse)
    qb = AggQueryBuilder()
    qb.fetch_from(metric.table_name, metric.schema_name)

    # Time dimension with grain
    time_col = apply_time_grain(column(kpi.time_dimension_column), kpi.time_grain, warehouse_type)
    qb.add_column(time_col.label("period"))
    qb.add_aggregate_column(metric.column, metric.aggregation, alias="value")
    qb.group_cols_by(time_col)
    qb.order_by(time_col, asc=True)
    qb.set_limit(kpi.trend_periods)

    # Apply metric filters
    for f in metric.filters:
        qb.where_clause(build_filter_clause(f))

    return execute_query(warehouse, qb)
```

**RAG computation (pure function, no DB):**
```python
def compute_rag_status(current_value, target_value, direction, green_pct, amber_pct) -> str | None:
    if target_value is None or current_value is None:
        return None
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
- Thin API layer: validate → delegate to service → wrap response
- Follows same pattern as `charts_api.py`

#### Saved Metric in Chart Builder

When building a chart query and `extra_config.metrics[]` contains `{"saved_metric_id": 42}`:
1. Resolve `Metric.objects.get(id=42, org=org)` in `charts_service.build_chart_data_payload()`
2. Convert to equivalent `ChartMetric(column=metric.column, aggregation=metric.aggregation)`
3. Apply the metric's baked-in filters to the query
4. Query execution proceeds as normal

**Modified file:** `ddpui/core/charts/charts_service.py` — `build_chart_data_payload()` function

### 3.4 Frontend Components

#### New Pages

| Route | File | Component |
|-------|------|-----------|
| `/metrics` | `app/metrics/page.tsx` | `<MetricsLibrary />` |
| `/kpis` | `app/kpis/page.tsx` | `<KPIPage />` |

#### New Components

**`components/metrics/`:**
- `metrics-library.tsx` — List view with search, filter-by-dataset, filter-by-tag
- `metric-form.tsx` — Create/edit form (dataset picker → column picker → aggregation → filters → name/desc/tags → preview)
- `metric-card.tsx` — Card component for library grid
- `metric-preview.tsx` — Shows computed value during creation

**`components/kpis/`:**
- `kpi-page.tsx` — Grid of KPI cards with search + filter
- `kpi-form.tsx` — Create/edit form (metric picker → target → direction → RAG → time grain → tags)
- `kpi-card.tsx` — Scannable card: value + target + RAG badge + trendline + period-over-period + last-updated
- `kpi-detail-drawer.tsx` — Full trend chart, KPI config, edit button
- `kpi-widget.tsx` — Dashboard widget renderer (value + target + RAG + trendline)

**Modified `components/charts/`:**
- Rename `MetricsSelector.tsx` → `MeasureSelector.tsx`
- Add two tabs: "Saved Metrics" | "Ad-hoc"
- "Saved Metrics" tab: searchable list filtered by current dataset
- Update all imports across `ChartDataConfigurationV3.tsx`, `MapDataConfigurationV3.tsx`, tests

**Modified `components/dashboard/`:**
- `chart-selector-modal.tsx` — Add "KPI" tab alongside charts
- `dashboard-builder-v2.tsx` — Handle `kpi` component type
- New `kpi-widget-element.tsx` — Renders KPI widget in dashboard grid

#### New Hooks

**`hooks/api/useMetrics.ts`:**
```typescript
export function useMetrics(params?: { search?: string; dataset?: string }) { ... }
export function useMetric(id: number) { ... }
export async function createMetric(payload: MetricCreate) { ... }
export async function updateMetric(id: number, payload: MetricUpdate) { ... }
export async function deleteMetric(id: number) { ... }
export async function previewMetricValue(id: number) { ... }
export async function getMetricConsumers(id: number) { ... }
```

**`hooks/api/useKPIs.ts`:**
```typescript
export function useKPIs(params?: { search?: string; metric_type?: string }) { ... }
export function useKPI(id: number) { ... }
export function useKPISummary() { ... }  // All KPIs with values for KPI page
export function useKPITrend(id: number) { ... }
export async function createKPI(payload: KPICreate) { ... }
export async function updateKPI(id: number, payload: KPIUpdate) { ... }
export async function deleteKPI(id: number) { ... }
```

#### New Types

**`types/metrics.ts`:**
```typescript
export interface Metric {
  id: number; name: string; description?: string;
  schema_name: string; table_name: string;
  column?: string; aggregation: string;
  filters: MetricFilter[]; tags: string[];
  created_at: string; updated_at: string;
}
export interface MetricFilter {
  column: string; operator: string; value: any;
}
export interface MetricCreate { ... }
export interface MetricUpdate { ... }
```

**`types/kpis.ts`:**
```typescript
export interface KPI {
  id: number; name: string; metric: Metric;
  target_value?: number; direction: 'increase' | 'decrease';
  green_threshold_pct: number; amber_threshold_pct: number;
  time_grain: string; time_dimension_column?: string;
  trend_periods: number; metric_type_tag?: string;
  program_tags: string[]; display_order: number;
  created_at: string; updated_at: string;
}
export interface KPISummary {
  id: number; name: string; metric_name: string;
  current_value?: number; target_value?: number;
  direction: string; rag_status?: 'green' | 'amber' | 'red';
  achievement_pct?: number; period_over_period_change?: number;
  time_grain: string; metric_type_tag?: string;
  program_tags: string[]; updated_at: string;
}
export type RAGStatus = 'green' | 'amber' | 'red';
export const RAG_COLORS: Record<RAGStatus, string> = {
  green: '#22c55e', amber: '#f59e0b', red: '#ef4444'
};
```

### 3.5 Navigation Updates

**`components/main-layout.tsx`:**
- Rename "Metrics" to "KPIs" (or keep both)
- Add `/kpis` route
- Keep `/metrics` as "Metrics Library" sub-item or separate nav item
- Remove "Metrics" from `PRODUCTION_HIDDEN_ITEMS` when ready

Proposed navigation structure:
```
KPIs         → /kpis       (the scannable KPI page — leadership-facing)
Metrics      → /metrics    (the metrics library — analyst-facing)
Charts       → /charts
Dashboards   → /dashboards
```

---

## 4. Security Review

### Authentication & Authorization
- All new endpoints protected with `@has_permission()`
- Permission slugs: `can_view_metrics`, `can_create_metrics`, `can_edit_metrics`, `can_delete_metrics`, `can_view_kpis`, `can_create_kpis`, `can_edit_kpis`, `can_delete_kpis`
- Migration adds these permissions and assigns them to appropriate roles (analyst+above for metrics, all roles for viewing KPIs)

### Input Validation
- All user input validated via Pydantic schemas at API boundary
- `aggregation` validated against allowed list: `[sum, avg, count, min, max, count_distinct]`
- `direction` validated: `[increase, decrease]`
- `time_grain` validated: `[daily, weekly, monthly, quarterly, yearly]`
- `metric_type_tag` validated: `[input, output, outcome, impact]`

### Data Access Control
- All queries scoped to `org`: `Metric.objects.filter(org=orguser.org)`
- KPI queries scoped to org
- Metric value queries execute against org's own warehouse only (via `OrgWarehouse.objects.filter(org=org)`)
- No cross-org data leakage possible

### Injection Risks
- **No raw SQL**: All warehouse queries built via `AggQueryBuilder` (SQLAlchemy parameterized)
- Column/table names come from warehouse metadata (user selects from dropdown, not free text)
- Metric filters use parameterized SQLAlchemy `where_clause` — no string interpolation

### Sensitive Data
- No PII handled
- No credentials stored (warehouse creds already in `OrgWarehouse`)

### Rate Limiting
- `preview` and `trend` endpoints execute warehouse queries — potentially expensive
- v1: rely on existing Django middleware rate limiting
- v2 consideration: add per-endpoint throttling if abuse is observed

---

## 5. Testing Strategy

### Unit Tests

**Backend:**
- `tests/services/test_metric_service.py`:
  - Create metric with valid/invalid data
  - List metrics with search, filters, pagination
  - Delete metric blocked when referenced by KPI
  - Delete metric blocked when referenced by chart
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
  - Metric form validation (name required, aggregation required)
  - Metric library search and filter
- `components/kpis/__tests__/`:
  - KPI card renders correct RAG color
  - KPI form defaults (amber threshold based on direction)
  - KPI page loads summary data
- `components/charts/__tests__/MeasureSelector.test.tsx`:
  - Tab switching between Saved Metrics and Ad-hoc
  - Saved metrics filtered by dataset

### Integration Tests
- Create metric → use in chart → verify chart renders with metric value
- Create metric → create KPI → verify KPI page shows correct RAG
- Create KPI → add to dashboard → verify widget renders

### Edge Cases
- Metric with `COUNT(*)` (null column)
- KPI without target (no RAG)
- KPI with zero target (division protection)
- Empty warehouse table (no rows → null value)
- Metric filter returns zero rows
- Dataset/table deleted from warehouse after metric created

---

## 6. Milestones

### Milestone 1: Backend Models + Metric CRUD

**Deliverable:** Metric model, migration, CRUD API, and metric value preview — fully testable via API.

**Services:** DDP_backend

**Key tasks:**
- [ ] Create `ddpui/models/metric.py` with `Metric` and `KPI` models
- [ ] Create migration `0158_metric_kpi.py` (tables + permission slugs)
- [ ] Create `ddpui/schemas/metric_schema.py` (Metric schemas)
- [ ] Create `ddpui/services/metric_service.py` (MetricService with CRUD + value computation)
- [ ] Create `ddpui/api/metric_api.py` (metric_router with CRUD + preview endpoints)
- [ ] Register `metric_router` at `/api/metrics/` in `routes.py`
- [ ] Write `tests/services/test_metric_service.py`
- [ ] Write `tests/api_tests/test_metric_api.py`

**Acceptance criteria:**
- `POST /api/metrics/` creates a metric and returns it
- `GET /api/metrics/` lists metrics with search/filter
- `POST /api/metrics/{id}/preview/` returns the computed numeric value
- `DELETE /api/metrics/{id}/` is blocked when KPIs reference the metric
- All tests pass

---

### Milestone 2: KPI CRUD + Value Computation

**Deliverable:** KPI CRUD API, RAG computation, trend data endpoint.

**Services:** DDP_backend

**Key tasks:**
- [ ] Create `ddpui/schemas/kpi_schema.py` (KPI schemas)
- [ ] Create `ddpui/services/kpi_service.py` (KPIService with CRUD + RAG + trend)
- [ ] Implement `compute_rag_status()` pure function
- [ ] Implement `compute_kpi_trend()` time-series query
- [ ] Implement `get_kpi_summary()` batch endpoint
- [ ] Create `ddpui/api/kpi_api.py` (kpi_router with CRUD + trend + summary endpoints)
- [ ] Register `kpi_router` at `/api/kpis/` in `routes.py`
- [ ] Write `tests/services/test_kpi_service.py`
- [ ] Write `tests/core/test_rag_computation.py`
- [ ] Write `tests/api_tests/test_kpi_api.py`

**Acceptance criteria:**
- `POST /api/kpis/` creates a KPI linked to a metric
- `GET /api/kpis/summary/` returns all KPIs with current values and RAG status
- `GET /api/kpis/{id}/trend/` returns period-value array for trendline
- RAG computation correct for all direction/threshold combinations
- All tests pass

---

### Milestone 3: Metrics Library (Frontend)

**Deliverable:** Metrics library page where analysts can create, browse, edit, and delete metrics.

**Services:** webapp_v2

**Key tasks:**
- [ ] Create `types/metrics.ts`
- [ ] Create `hooks/api/useMetrics.ts`
- [ ] Create `components/metrics/metrics-library.tsx` (list with search/filter)
- [ ] Create `components/metrics/metric-card.tsx`
- [ ] Create `components/metrics/metric-form.tsx` (dataset → column → aggregation → filters → name/tags → preview)
- [ ] Create `components/metrics/metric-preview.tsx`
- [ ] Create `app/metrics/page.tsx`
- [ ] Update `components/main-layout.tsx` navigation
- [ ] Write tests for metric components

**Acceptance criteria:**
- User can navigate to `/metrics` and see the metrics library
- User can create a metric: pick dataset, column, aggregation, optional filters, name, tags
- Preview shows computed value before saving
- User can search and filter metrics
- User can edit and delete metrics (delete blocked if referenced)

---

### Milestone 4: KPI Page (Frontend)

**Deliverable:** KPI page with scannable cards showing value, target, RAG, trendline, and period-over-period change.

**Services:** webapp_v2

**Key tasks:**
- [ ] Create `types/kpis.ts`
- [ ] Create `hooks/api/useKPIs.ts`
- [ ] Create `components/kpis/kpi-page.tsx` (grid of KPI cards with search/filter)
- [ ] Create `components/kpis/kpi-card.tsx` (value + target + RAG badge + trendline + change)
- [ ] Create `components/kpis/kpi-form.tsx` (metric picker → target → direction → RAG → time grain → tags)
- [ ] Create `components/kpis/kpi-detail-drawer.tsx` (full trend chart, config, edit)
- [ ] Create `app/kpis/page.tsx`
- [ ] Add KPIs nav item in `main-layout.tsx`
- [ ] Implement trendline using ECharts mini line chart
- [ ] Write tests for KPI components

**Acceptance criteria:**
- User navigates to `/kpis` and sees all KPIs as cards
- Each card shows current value, target, RAG badge (color-coded), trendline, period-over-period change
- Search by name, filter by program tag and metric type
- Clicking a card opens detail drawer with full trend chart
- User can create a KPI from the page

---

### Milestone 5: MeasureSelector Refactor + Saved Metrics in Chart Builder

**Deliverable:** Chart builder's measure picker renamed to "Measure" with a "Saved Metrics" tab alongside ad-hoc mode.

**Services:** webapp_v2, DDP_backend (minor)

**Key tasks:**
- [ ] Rename `MetricsSelector.tsx` → `MeasureSelector.tsx`
- [ ] Add two-tab UI: "Saved Metrics" | "Ad-hoc (Custom)"
- [ ] Implement saved metrics tab: fetch from `/api/metrics/?schema_name=X&table_name=Y`
- [ ] Update `ChartDataConfigurationV3.tsx` imports/usage
- [ ] Update `MapDataConfigurationV3.tsx` imports/usage
- [ ] Update labels from "Metric" to "Measure" across all chart type configs
- [ ] Backend: modify `build_chart_data_payload()` to resolve `saved_metric_id` references
- [ ] Update `MetricsSelector.test.tsx` → `MeasureSelector.test.tsx`

**Acceptance criteria:**
- Measure picker shows two tabs
- Saved Metrics tab shows metrics filtered to current dataset
- Selecting a saved metric populates the measure correctly
- Ad-hoc mode works exactly as before (no regression)
- All existing chart builder tests pass

---

### Milestone 6: KPI Dashboard Widget

**Deliverable:** KPI appears as a widget type in the dashboard builder, rendering value + target + RAG + trendline.

**Services:** webapp_v2, DDP_backend

**Key tasks:**
- [ ] Backend: Add `KPI = "kpi"` to `DashboardComponentType` enum
- [ ] Backend: Handle KPI component type in dashboard save/load
- [ ] Frontend: Create `components/dashboard/kpi-widget-element.tsx`
- [ ] Frontend: Update `chart-selector-modal.tsx` to add KPI selection tab
- [ ] Frontend: Update `dashboard-builder-v2.tsx` to render KPI widgets
- [ ] Frontend: KPI widget renders: value + target + RAG badge + trendline
- [ ] Frontend: Widget is positionable and resizable
- [ ] Write tests for KPI widget component

**Acceptance criteria:**
- Dashboard builder shows "KPI" as a component type
- User can select a KPI and add it to the dashboard
- KPI widget renders with current value, target, RAG badge, and trendline
- Widget is positionable and resizable like other components
- Editing the KPI updates the widget automatically (live state)

---

## 7. Open Questions & Risks

### Open Questions
1. **Time dimension column for KPIs:** The KPI needs a date/time column to build the trend query. Should this come from the Metric's dataset (user picks during KPI creation) or from a separate configuration? **Recommendation:** User picks `time_dimension_column` during KPI creation from columns in the metric's table.

2. **Metric value for "current period":** When computing the KPI's current value, should it aggregate all rows (like metric preview) or only the latest period? **Recommendation:** v1 aggregates all rows for current value (matches metric preview). Period-specific values shown only in trend.

3. **KPI summary batch performance:** `GET /api/kpis/summary/` executes one warehouse query per KPI. For orgs with 20+ KPIs, this could be slow. **Mitigation:** v1 accepts this; v2 adds parallel execution or caching.

4. **Dashboard component storage:** Dashboard `components` JSON stores `{id: {type: "kpi", kpi_id: 42}}`. When a KPI is deleted, should the dashboard cleanup happen automatically? **Recommendation:** Yes, `delete_kpi` removes references from dashboard components JSON.

### Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Warehouse query latency on KPI page (N queries for N KPIs) | Slow page load for orgs with many KPIs | Accept in v1; optimize with parallel queries or caching in v2 |
| Time dimension column may not exist or have wrong type | Trend query fails | Validate column type during KPI creation; show error if not datetime |
| Metric consumer tracking for charts relies on scanning `extra_config` JSON | Slow for orgs with many charts | Simple `Q(extra_config__contains=...)` filter; index if needed |
| MeasureSelector rename may break existing chart builder usage | Regression in chart creation | Update all imports; run full test suite before merging |

---

*Plan generated from [v1 spec](./spec.md) and [codebase research](./research.md).*
