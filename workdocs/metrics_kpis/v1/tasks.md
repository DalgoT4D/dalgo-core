# Milestone 1 Tasks

## Backend

- [x] Create `ddpui/models/metric.py` with Metric and KPI models
- [x] Create migration `0158_metric_kpi.py` + seed permission data
- [x] Create `ddpui/schemas/metric_schema.py`
- [x] Create `ddpui/services/metric_service.py`
- [x] Create `ddpui/api/metric_api.py` + register in `routes.py`
- [x] Modify `charts_service.py` for `saved_metric_id` resolution (+ expression support in ChartMetric)
- [x] Write `tests/services/test_metric_service.py` (29 tests)
- [x] Write `tests/api_tests/test_metric_api.py` (19 tests)
- [x] Run migration, seed data, tests — all 89 pass

## Frontend

- [x] Create `types/metrics.ts`
- [x] Create `hooks/api/useMetrics.ts`
- [x] Create `components/metrics/metric-form-dialog.tsx` (with DatasetSelector + column Combobox)
- [x] Create `components/metrics/metrics-library.tsx`
- [x] Create `app/metrics/page.tsx`
- [x] Update `MetricsSelector.tsx` — add Saved Metrics / Ad-hoc tabs
- [x] Update `ChartDataConfigurationV3.tsx` — pass schemaName/tableName to MetricsSelector
- [x] Update `main-layout.tsx` — move Metrics under Data, remove from PRODUCTION_HIDDEN_ITEMS
- [x] Update `types/charts.ts` — add saved_metric_id + column_expression to ChartMetric
- [x] Frontend builds successfully
