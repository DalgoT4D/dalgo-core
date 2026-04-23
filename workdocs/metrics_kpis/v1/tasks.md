# Milestone 1 (COMPLETE)

## Backend
- [x] Metric + KPI models, migration `0158`, permissions (8 slugs), seed data (34 role mappings)
- [x] Metric schemas, service (CRUD + validation + preview + consumers)
- [x] Metric API: 7 endpoints at `/api/metrics/`
- [x] Charts integration: `saved_metric_id` resolution + `column_expression` via `literal_column`
- [x] Tests: 48 passing (29 service + 19 API)

## Frontend
- [x] Types, hooks, metrics library page (table pattern matching charts page)
- [x] Metric form dialog (DatasetSelector + column Combobox from warehouse)
- [x] MetricsSelector: Saved Metrics / Ad-hoc tabs + inline Save button
- [x] Navigation: Metrics under Data section

---

# Milestone 2 (COMPLETE)

## Backend
- [x] KPI schemas (KPICreate, KPIUpdate with `metric_id`, KPIResponse, KPIListResponse)
- [x] KPI service: CRUD + RAG computation + `get_kpi_data()` + `_compute_trend()`
- [x] `compute_rag_status()` pure function (direction-aware)
- [x] `get_kpi_data()` returns `{data, echarts_config}` — line chart (with trend) or number chart (without)
- [x] `generate_kpi_trend_config()` in EChartsConfigGenerator
- [x] KPI API: CRUD + `/{id}/data/` endpoint, `metric_id` changeable on update
- [x] Tests: 43 passing

## Frontend
- [x] Types, hooks (useKPIs, useKPIData)
- [x] KPI page: card grid with ECharts, value/target display, metric type + program tag filters
- [x] KPI form: 2-step (metric selection → config), works for both create and edit
- [x] Direction-aware RAG defaults, time column dropdown from warehouse, metric change resets time config
- [x] "Create KPI" action in metrics library dropdown
- [x] Number chart (gauge) when no time dimension, line chart when time dimension exists
- [x] ECharts dispose/reinit on config type change
- [x] Navigation: KPIs between Impact and Charts

---

# Milestone 3 (COMPLETE)

## Backend
- [x] Add `KPI = "kpi"` to `DashboardComponentType` enum
- [x] Add `kpi` entry to `CHART_SIZE_CONSTRAINTS` (same size as standard charts)

## Frontend
- [x] Create `components/dashboard/kpi-chart-element.tsx` — fetches `/{id}/data/`, renders ECharts
- [x] Update `chart-selector-modal.tsx` — Charts + KPIs tabs
- [x] Update `dashboard-builder-v2.tsx` — KPI enum, `handleKPISelected`, render switch, action buttons (view + remove), `excludedKPIIds`
- [x] Update `dashboard-native-view.tsx` — KPI case in view mode (public share works)
- [x] KPI widget: same action button pattern as charts (hover overlay), no double borders
- [x] All backend tests passing, frontend builds

---

# Milestone 4 (NOT STARTED)

## Backend
- [ ] Update ReportSnapshot creation to handle `kpi` component type in `frozen_chart_configs`
- [ ] Freeze KPI data: current value, target, RAG status, trend data
- [ ] Add `KPI = "kpi"` to `CommentTargetType` enum
- [ ] Update comment service to accept `target_type="kpi"`
- [ ] Tests for snapshot creation with KPI charts + commenting

## Frontend
- [ ] Update snapshot render code to handle `kpi` component type
- [ ] Render frozen KPI chart (static data from snapshot, not live)
- [ ] CommentPopover support for KPI charts in snapshot view
- [ ] Tests
