# Metrics & KPIs v1 — Research Notes

**Date:** 2026-04-21
**Purpose:** Codebase analysis to inform implementation plan

---

## 1. Backend Architecture (DDP_backend)

### Framework & Patterns
- **Django + Django Ninja** for REST APIs with automatic Pydantic schema validation
- **Layer architecture**: API (`api/`) → Core/Service (`core/`, `services/`) → Models (`models/`)
- **Auth**: JWT via `rest_framework_simplejwt` + `@has_permission(["can_verb_module"])` decorator
- **Response format**: `api_response(success=True, data=...)` wrapper from `utils/response_wrapper.py`
- **Latest migration**: `0157_orgdbt_is_repo_managed_by_system.py` — next migration will be `0158`

### Key Models (relevant)
| Model | File | Purpose |
|-------|------|---------|
| `Chart` | `models/visualization.py` | Stores chart config; `extra_config` JSONField holds metrics/dimensions/filters |
| `Dashboard` | `models/dashboard.py` | Dashboard with `layout_config` (JSON grid positions) and `components` (JSON component configs) |
| `DashboardComponentType` | `models/dashboard.py` | Enum: `CHART`, `TEXT`, `HEADING` — needs `KPI` added |
| `Org` | `models/org.py` | Organization entity |
| `OrgUser` | `models/org_user.py` | User-org link with `new_role` FK for permissions |
| `OrgWarehouse` | `models/org.py` | Warehouse credentials (`wtype`, `credentials`) |

### Warehouse Query Pattern
- `WarehouseFactory.get_warehouse_client(org_warehouse)` creates DB client
- `AggQueryBuilder` (`core/datainsights/query_builder.py`) builds SQLAlchemy aggregate queries
- Supports: `sum, avg, count, min, max, count_distinct`
- `charts_service.build_chart_query()` → `execute_chart_query()` → `transform_data_for_chart()`
- Supports Postgres and BigQuery (time grain uses `DATE_TRUNC` / `DATETIME_TRUNC`)

### API Routing
- Routers registered in `routes.py`: `src_api.add_router("/api/{module}/", {module}_router)`
- Charts at `/api/charts/`, Dashboards at `/api/dashboards/`
- New metrics/KPIs will follow: `/api/metrics/`, `/api/kpis/`

### Permission Slugs Convention
- `can_view_charts`, `can_create_charts`, `can_edit_charts`, `can_delete_charts`
- New: `can_view_metrics`, `can_create_metrics`, `can_edit_metrics`, `can_delete_metrics`
- New: `can_view_kpis`, `can_create_kpis`, `can_edit_kpis`, `can_delete_kpis`

### Service Layer Pattern (from ChartService)
```python
@dataclass
class ChartData:
    title: str; chart_type: str; ...

class ChartService:
    @staticmethod
    def create_chart(data: ChartData, orguser: OrgUser) -> Chart: ...
    @staticmethod
    def get_chart(chart_id: int, org: Org) -> Chart: ...
```
- Services throw custom exceptions (ChartNotFoundError, etc.)
- API layer catches and converts to HttpError

### Test Pattern
- pytest with `@pytest.mark.django_db`
- Fixtures: `authuser`, `org`, `orguser`, `sample_chart`
- Tests in `ddpui/tests/services/`, `ddpui/tests/api_tests/`

---

## 2. Frontend Architecture (webapp_v2)

### Framework & Patterns
- **Next.js 15** (App Router), **React 19**, **TypeScript**
- **UI**: Shadcn UI (Radix) + Tailwind CSS v4
- **State**: Zustand (global), SWR (server), useState (local)
- **API client**: Custom `apiGet/apiPost/apiPut/apiDelete` in `lib/api.ts`
- **Charts**: ECharts

### Navigation
- Sidebar defined in `components/main-layout.tsx`
- **"Metrics"** item already exists at `/metrics` (hidden in production via `PRODUCTION_HIDDEN_ITEMS`)
- No `/kpis` route yet — needs to be added
- `app/impact/page.tsx` exists as the "home" page

### Key Frontend Files
| File | Purpose |
|------|---------|
| `components/charts/MetricsSelector.tsx` | Current measure picker — column + aggregation. **Rename to MeasureSelector** |
| `components/charts/ChartDataConfigurationV3.tsx` | Uses MetricsSelector |
| `components/dashboard/dashboard-builder-v2.tsx` | Dashboard canvas with react-grid-layout |
| `components/dashboard/chart-selector-modal.tsx` | Modal to add charts to dashboard |
| `components/dashboard/chart-element-v2.tsx` | Renders chart widgets on dashboard |
| `types/charts.ts` | ChartMetric interface, ChartTypes enum |
| `hooks/api/useCharts.ts` | SWR hook for charts |
| `lib/api.ts` | Centralized API client |

### Component Organization Pattern
```
components/{feature}/
├── {feature}-list.tsx
├── {feature}-form.tsx
├── utils.ts
├── constants.ts
└── __tests__/
```

### Dashboard Widget System
- `layout_config` stores grid positions as `[{i, x, y, w, h}, ...]`
- `components` stores component data keyed by ID: `{id: {type, chartId, ...}}`
- `DashboardComponentType` enum on backend controls allowed types
- Widget types: `chart`, `text`, `heading` — need to add `kpi`

---

## 3. No Existing Metric/KPI Code

- No `MetricDefinition` or `SuccessMetric` models exist in the current codebase
- The spec mentions a `pratiksha/alerts-metrics-changes` branch (unreleased prototype) — this is a clean implementation
- No production data to migrate

---

## 4. Chart-Metric Integration Point

The existing `ChartMetric` schema (backend and frontend) defines ad-hoc metrics:
```python
class ChartMetric(Schema):
    column: Optional[str] = None
    aggregation: str
    alias: Optional[str] = None
```

For saved Metrics in chart builder, we need a way to reference a saved Metric by ID. The chart's `extra_config` can include:
```json
{
  "metrics": [
    {"saved_metric_id": 42}        // Saved metric reference
    {"column": "amount", "aggregation": "sum", "alias": "Total"}  // Ad-hoc
  ]
}
```

When building the query, if `saved_metric_id` is present, resolve the Metric object and use its column/aggregation/filters.
