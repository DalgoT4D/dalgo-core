# Milestone 1 (COMPLETE)

## Backend
- [x] Create `ddpui/models/metric.py` with Metric and KPI models
- [x] Create migration `0158_metric_kpi.py` + seed permission data
- [x] Create `ddpui/schemas/metric_schema.py`
- [x] Create `ddpui/services/metric_service.py`
- [x] Create `ddpui/api/metric_api.py` + register in `routes.py`
- [x] Modify `charts_service.py` for `saved_metric_id` resolution (+ expression support via `literal_column`)
- [x] Write `tests/services/test_metric_service.py` (29 tests)
- [x] Write `tests/api_tests/test_metric_api.py` (19 tests)

## Frontend
- [x] Create `types/metrics.ts`
- [x] Create `hooks/api/useMetrics.ts`
- [x] Create `components/metrics/metric-form-dialog.tsx` (DatasetSelector + column Combobox)
- [x] Create `components/metrics/metrics-library.tsx` (table matching charts page pattern)
- [x] Create `app/metrics/page.tsx`
- [x] Update `MetricsSelector.tsx` — Saved Metrics / Ad-hoc tabs + inline Save button
- [x] Update `ChartDataConfigurationV3.tsx` — pass schemaName/tableName to MetricsSelector
- [x] Update `main-layout.tsx` — Metrics under Data section
- [x] Update `types/charts.ts` — add saved_metric_id + column_expression to ChartMetric
- [x] Update `chart_schema.py` — add column_expression to ChartMetric schema

---

# Milestone 2 (COMPLETE)

## Backend
- [x] Create `ddpui/schemas/kpi_schema.py` (KPICreate, KPIUpdate, KPIResponse, KPIListResponse)
- [x] Create `ddpui/services/kpi_service.py` (CRUD + RAG + `get_kpi_data()` + `_compute_trend()`)
- [x] Implement `compute_rag_status()` pure function
- [x] Implement `get_kpi_data()` — returns `{data, echarts_config}` (same pattern as chart data)
- [x] Add `generate_kpi_trend_config()` to `EChartsConfigGenerator` (full + compact modes)
- [x] Create `ddpui/api/kpi_api.py` — CRUD + `/{id}/data/` endpoint using `ChartDataResponse`
- [x] Register `kpi_router` at `/api/kpis/` in `routes.py`
- [x] Write `tests/services/test_kpi_service.py` (RAG computation, CRUD, dashboard cleanup, data)
- [x] Write `tests/api_tests/test_kpi_api.py`
- [x] All tests passing

## Frontend
- [x] Create `types/kpis.ts` (KPI, KPICreate, KPIUpdate, RAG_COLORS, option constants)
- [x] Create `hooks/api/useKPIs.ts` (useKPIs, useKPI, useKPIData, mutations)
- [x] Create `components/kpis/kpi-page.tsx` — card grid with ECharts rendering via `/{id}/data/`
- [x] Create `components/kpis/kpi-form.tsx` — 2-step form (Step 1: metric selection/creation, Step 2: KPI config)
- [x] KPI form sections: Target & RAG Status, Time Configuration, Classification (metric type cards)
- [x] Direction-aware RAG threshold defaults (increase: green=100/amber=80, decrease: green=100/amber=120)
- [x] Time column dropdown filtered to date/timestamp types from warehouse
- [x] Inline metric creation from KPI form step 1
- [x] RAG badges on KPI cards (On Track / At Risk / Off Track)
- [x] Create `app/kpis/page.tsx`
- [x] Add KPIs nav item in `main-layout.tsx` (Target icon, between Impact and Charts)
- [x] Filter by metric type + program tag on KPI page
- [x] "Create KPI" action in metrics library dropdown (pre-fills metric in KPI form)
- [x] Frontend builds successfully

## Design decisions (deviations from plan)
- Detail drawer removed — KPI cards show data directly with ECharts
- Summary batch endpoint removed — cards fetch individually via `/{id}/data/`
- KPI data endpoint uses `ChartDataResponse` schema — same pattern as charts
- ECharts config generated server-side via `EChartsConfigGenerator`
- KPI form is 2-step (metric selection → config) for both create and edit
