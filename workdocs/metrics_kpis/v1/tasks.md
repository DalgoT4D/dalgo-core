# Milestone 1 (COMPLETE) — Metrics + Chart Builder Integration

## Backend
- [x] Metric + KPI models, migration `0158`, permissions, seed data
- [x] Metric schemas, service, API (CRUD + preview + consumers)
- [x] Charts integration: `saved_metric_id` + `column_expression` via `literal_column`
- [x] Tests: 48 passing

## Frontend
- [x] Types, hooks, metrics library page, metric form dialog
- [x] MetricsSelector: Saved Metrics / Ad-hoc tabs + inline Save
- [x] Navigation: Metrics under Data section

---

# Milestone 2 (COMPLETE) — KPIs End-to-End

## Backend
- [x] KPI schemas, service, API
- [x] `compute_kpi_data()` — common function used by live API + reports
- [x] Number chart (no time dimension) vs line chart (with time dimension)
- [x] Tests passing

## Frontend
- [x] KPI page: card grid with ECharts, value/target, filters
- [x] KPI form: 2-step, direction-aware RAG, time column dropdown
- [x] "Create KPI" from metrics library

---

# Milestone 3 (COMPLETE) — KPI Dashboard Widget

## Backend
- [x] `KPI = "kpi"` in `DashboardComponentType` + `CHART_SIZE_CONSTRAINTS`

## Frontend
- [x] KPI chart element for dashboard
- [x] Chart selector modal with Charts + KPIs tabs
- [x] Dashboard builder: KPI add/render/remove with action buttons
- [x] View mode + public share rendering

---

# Milestone 4 (COMPLETE) — ReportSnapshot KPI Widget Support

## Backend — Comment system refactor
- [x] Migration `0159`: Rename `snapshot_chart_id` → `target_id`, `chart_id` → `target_id`
- [x] Add `KPI = "kpi"` to `CommentTargetType` enum
- [x] Refactor `comment_service.py`: generic `target_id` with `_ENTITY_TARGET_TYPES` set
- [x] Refactor `mention_service.py`: KPI target type in URLs + entity name resolution
- [x] Update `report_schema.py`: all comment schemas use `target_id`
- [x] Update `report_api.py`: API params use `target_id`
- [x] Update all comment/mention tests

## Backend — Snapshot freeze + KPI data
- [x] `FrozenKpiConfig` + `FrozenKpiMetric` schemas (metric def, target, direction, RAG, time config, tags, periods)
- [x] `_freeze_chart_configs()` freezes KPIs alongside charts
- [x] `create_snapshot()` handles KPI entries (skips `FrozenChartConfig` validation)
- [x] `compute_kpi_data(payload, org, date_filter)` — common function for live + report
- [x] `get_report_kpi_data()` builds payload from frozen config, passes date filter from snapshot
- [x] API endpoint: `GET /api/reports/{snapshot_id}/kpis/{kpi_id}/data/`
- [x] All tests passing (246+)

## Frontend — Report mode
- [x] `types/comments.ts`: `chart_id` → `target_id`, add `'kpi'` to unions
- [x] `hooks/api/useComments.ts`: `chart_id` → `target_id`
- [x] `hooks/api/useKPIs.ts`: `useKPIData` accepts `snapshotId`, switches to report endpoint
- [x] `comment-popover.tsx`: payloads use `target_id`
- [x] `chart-element-view.tsx`: comment states lookup uses `target_id`
- [x] `kpi-chart-element.tsx`: accepts `snapshotId` + comment props, renders `CommentPopover` in report mode
- [x] `dashboard-native-view.tsx`: passes `snapshotId`, `commentStates`, `onCommentStateChange` to KPI element
- [x] `comment-states-lookup.test.ts`: uses `target_id`, includes KPI test case
- [x] Frontend builds successfully
