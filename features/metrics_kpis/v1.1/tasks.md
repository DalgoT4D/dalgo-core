# KPI v1.1 — Execution Tasks

Checkpoint for `/engineering/execute-plan`. Mark items as `[x]` when complete. Resume from the first unchecked item if work is interrupted.

**Plan:** [plan.md](./plan.md)
**Research:** [research.md](./research.md)

---

## M1 — Backend: schema, storage, parity formatter ✅

### Schema + model

- [x] Add `KPIExtraConfig` Pydantic schema (with optional `customizations: NumberChartCustomizations`) to `DDP_backend/ddpui/schemas/kpi_schema.py`
- [x] Make `extra_config: KPIExtraConfig` a **required** field on `KPICreate`, `KPIUpdate`, `KPIResponse` (no default)
- [x] Add `extra_config = JSONField(default=dict, blank=False, null=False)` to `KPI` model in `DDP_backend/ddpui/models/metric.py`
- [x] Create migration `DDP_backend/ddpui/migrations/0166_kpi_extra_config.py` (AddField with `default=dict`)
- [x] Migration applied successfully

### Service layer

- [x] `kpi_service.create_kpi` — persists `payload.extra_config.model_dump()`
- [x] `kpi_service.update_kpi` — works via existing `model_dump(exclude_unset=True)` path
- [x] `kpi_service.kpi_to_response` — includes `extra_config=KPIExtraConfig(**kpi.extra_config)`
- [x] `report_service.get_report_kpi_data` — reads frozen customizations from `kpi_config["extra_config"]` (defaults to empty for pre-v1.1 snapshots)

### Shared backend formatter (`number_formatting.py`)

- [x] Create `DDP_backend/ddpui/core/charts/number_formatting.py` with `format_number_v2`
- [x] Implement all 7 format types via babel
- [x] Handle `None` / `NaN` / `Inf` → return `"No data"` without prefix/suffix wrap
- [x] Refactor `echarts_config_generator._format_number` to delegate

### Tests

- [x] `DDP_backend/ddpui/tests/core/charts/test_number_formatting.py` — 39 cases (all format types × edge cases) **PASSING**
- [x] Update `tests/api_tests/test_kpi_api.py` — KPICreate / KPIUpdate include `extra_config`
- [x] Update `tests/services/test_kpi_service.py` — same, plus new `test_create_kpi_with_customizations` round-trip + `test_update_kpi_replaces_customizations`
- [x] Chart tests (`tests/core/charts/`) — **42 PASSING** (no regressions from formatter delegation)
- [x] Report tests (`tests/core/reports/`) — **71 PASSING**
- [ ] Cross-stack parity fixture — **deferred** to validation phase (JSON file + frontend half written in M2)

### Acceptance

- [x] Full backend suite: **2003 passed**, 5 unrelated dbt-service failures (external GitHub API — pre-existing)
- [ ] Manual: POST `/api/kpis/` with `extra_config.customizations.numberFormat="indian"` round-trips (covered by unit test; manual smoke test in final validation)

---

## M2 — Frontend: KPI form + card + drawer + dashboard widget ✅

- [x] Reuse existing `NumberFormatSection` shared component (no extraction needed — already shared across chart types)
- [x] Add Display Formatting panel in `webapp_v2/components/kpis/kpi-form.tsx` Step 2 — placed **above** Program Tags / KPI Type per user request, with an Info tooltip explaining the scope
- [x] Add `formatKPIValue(value, customizations)` to `webapp_v2/lib/formatters.ts` — falls back to legacy `formatMetricValue` when no customizations are set
- [x] Swap `formatMetricValue` → `formatKPIValue` in `kpi-card.tsx` (current value + target)
- [x] Swap in `kpi-detail-drawer.tsx` (current value + target only; annotation snapshot stays raw per scope)
- [x] `kpi-chart-element.tsx` (dashboard widget) — pass `chartData?.customizations` into `KPICardData`. Inherits via `KPICard` render
- [x] Backend: customizations included in `compute_kpi_data` response payload so the widget + snapshot viewer have them without a second fetch
- [x] TypeScript types: `KPICustomizations`, `KPIExtraConfig`, `KPI.extra_config` (non-optional)
- [x] `formatMetricValue` audit done — kept on annotation timeline (out of scope per user)
- [x] **Fallback behavior changed**: when no `customizations.numberFormat` is set, `formatKPIValue` now returns `String(value)` (raw number, no compression, no grouping). The legacy `formatMetricValue` "1.2M" compression is no longer used as a fallback.

### Trendline tooltip (scope expanded mid-build)

Originally marked out-of-scope; user opted in after seeing the inconsistency between the card render (formatted) and trendline hover (ECharts default with locale grouping).

- [x] `kpi-card.tsx::EChartsRenderer` — accept `customizations`, inject `tooltip.valueFormatter` using `formatKPIValue`
- [x] `kpi-detail-drawer.tsx::TrendChart` — same wiring, customizations read from `kpi.extra_config?.customizations`
- [x] Card → renderer wiring (`data.customizations` passed through)

### Form UX refinements (user-driven)

- [x] Display Formatting section placed **after** Classification (Program Tags + KPI Type) in Step 2
- [x] Title styled as a muted section sub-header (`text-sm text-muted-foreground font-medium`) — matches "Target & RAG Status" / "Time Configuration"
- [x] Added a "Classification" section sub-header above Program Tags + KPI Type for visual consistency
- [x] Info tooltip on the Display Formatting heading removed (user choice — title alone is sufficient)
- [x] RAG threshold defaults updated:
  - Increase: green=80, amber=50 (≥80% green, ≥50% amber, <50% red)
  - Decrease: green=50, amber=80 (≤50% green, ≤80% amber, >80% red) — same two numbers as increase, swap slots so green<amber per backend validation
  - Reflected in `defaultValues`, create-mode reset, and direction-change handler

### Tests

- [x] Jest tests for `formatKPIValue` — null/NaN guard, fallback path (raw `String(value)`), all four format types with prefix/suffix combinations — **PASSING (82 KPI+formatter tests)**
- [ ] `kpi-card.test.tsx` snapshot tests with each format — deferred to validation phase
- [ ] `kpi-form.test.tsx` persist-payload test — deferred (manual smoke test covers it)
- [ ] Trendline tooltip formatter test (verify ECharts gets `valueFormatter` callback) — deferred
- [ ] Frontend half of parity fixture — deferred to validation phase
- [x] **1423 passing webapp_v2 tests overall**; 3 unrelated failures in pipeline + DataPreview (untouched files)

### Acceptance

- [x] KPI form persists `extra_config.customizations` in create + update payloads
- [x] KPI card uses `formatKPIValue(value, data.customizations)` — render-tested
- [x] Dashboard widget consumes customizations from the data response — render-tested
- [x] Pre-v1.1 KPIs (no customizations) render with raw numbers (no compression) — fallback verified
- [x] Trendline tooltip on card AND drawer renders with the KPI's prefix/suffix/format — matches the card's current value byte-for-byte
- [ ] Manual end-to-end smoke test — recommended in final validation phase

### Operational notes (out-of-scope but completed during this session)

- [x] PM2 config (`dev/dalgo_dev.config.js`) updated — all Django services now run from `DDP_backend` (the worktree on `enhancements/alerts-metrics-kpis` where v1.1 changes live), replacing the previous `DDP_backend_alerts` pointing.
- [x] Service names dropped the `-alerts` suffix where it referred to the worktree (kept `django-celery-alerts-worker` since it refers to the alerts *queue*).

---

## M3 — ReportSnapshot freeze + render

- [ ] Extend `FrozenKpiConfig` in `DDP_backend/ddpui/schemas/report_schema.py` with `customizations: Optional[Dict] = None`
- [ ] Find snapshot freeze call sites (grep `FrozenKpiConfig(`) — copy `kpi.extra_config.customizations` at snapshot time
- [ ] Snapshot render path reads frozen `customizations` (not live KPI)
- [ ] Frontend snapshot KPI viewer consumes frozen `customizations`
- [ ] Unit test: pre-v1.1 snapshots (no frozen customizations) render with no formatting

### Acceptance

- [ ] Snapshot dashboard with formatted KPI → edit format → snapshot still shows original format

---

## M4 — Alert: formatted `{{current_value}}`

- [ ] Update `DDP_backend/ddpui/core/alerts/rendering.py` — format `{{current_value}}` via `format_number_v2` + KPI customizations
- [ ] Update existing alert-render tests with new expectations
- [ ] Add a release note (intentional behavior change)

### Acceptance

- [ ] kpi_rag alert email body shows formatted value matching the KPI card byte-for-byte

---

## Final validation

- [ ] `uv run pytest ddpui/tests` — all pass
- [ ] `npm test` in `webapp_v2` — all pass
- [ ] Cross-stack parity fixture passes on both sides
- [ ] No new lint errors
- [ ] Manual end-to-end flow per plan § Verification works
