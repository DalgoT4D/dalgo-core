# KPI v1.2 — Inline Metric Creation & KPI Wizard — Implementation Plan

**Status:** Draft v1  
**Date:** 2026-08-05  
**Parent version:** [`features/metrics_kpis/v1.1/plan.md`](../v1.1/plan.md)  
**Domain map:** [`docs/domain-map.md`](../../../docs/domain-map.md)

---

## 1. Overview

Creating a KPI today requires the user to navigate away to the Metrics page, create a metric, come back, and refresh. This breaks the flow for new users who don't yet have any metrics.

This enhancement:
1. Adds **inline metric creation** inside the KPI form — users can define a brand-new metric without leaving the dialog.
2. Restructures the KPI form from a 2-step flow into a **3-step wizard** with a step indicator, making the large number of fields easier to navigate.

The pattern for inline metric creation mirrors the chart builder's `MetricAccordionItem` / `MetricsSelector` approach (same metric form fields, same API calls), but adapted for the modal context (toggle, not accordion).

**Services affected:** `webapp_v2` only. No backend changes.

---

## 2. New Wizard Structure

| Step | Label | Fields |
|------|-------|--------|
| 1 | Metric | Select existing metric OR create new inline |
| 2 | KPI Setup | KPI name, target value, direction, time column, time grain |
| 3 | Thresholds & Display | RAG thresholds, program tags, KPI type, number formatting |

**Edit mode** opens at Step 2 (Step 1 is hidden entirely). The locked fields — `metric_id` (Step 1, hidden), `time_dimension_column` and `time_grain` (Step 2) — remain `disabled` exactly as they are today. The amber warning banner ("Metric, time column, and time grain cannot be changed after creation") moves to the top of Step 2 so it is immediately visible when the edit dialog opens.

**Current → new field mapping:**

| Current Step 1 | New Step |
|---|---|
| metric_id | Step 1 |
| name | Step 2 |
| target_value | Step 2 |
| direction | Step 2 |

| Current Step 2 | New Step |
|---|---|
| time_grain, time_dimension_column | Step 2 |
| green_threshold_pct, amber_threshold_pct | Step 3 |
| metric_type_tag, program_tags | Step 3 |
| numberFormat, decimalPlaces, prefix, suffix | Step 3 |

---

## 3. Step 1: Inline Metric Creation UX

Step 1 renders a two-mode toggle (tab or button pair):

- **Select existing** (default): The existing `MetricPicker` combobox. No change.
- **Create new**: An inline metric form with the same fields as `MetricFormDialog`:
  - Name (required)
  - Definition / description (optional)
  - Datasource — `DatasetSelector`
  - Mode tabs: **Simple** (function + column) / **Calculated** (SQL expression)

When Continue is clicked in "Create new" mode:
1. If calculated mode: `POST /api/metrics/validate/` — show validation state; block on error.
2. `POST /api/metrics/` — create the metric; get back the new `metric_id`.
3. `mutateMetrics()` — refresh the SWR metrics cache.
4. Store `metric_id` in the KPI form; auto-populate the KPI name from the metric name.
5. Advance to Step 2.

When Continue is clicked in "Select existing" mode: same as today — validate `metric_id` is set, then advance.

---

## 4. File Changes

### New files — `webapp_v2/components/kpis/`

**`KpiMetricStep.tsx`**
- Owns its own `useForm<MetricFormData>` for the inline metric fields (same shape as `MetricFormDialog`).
- Props: `metricId`, `onMetricSelected(id, name)`, `metrics`, `mutateMetrics`.
- Exposes a `ref`-based or callback-based `handleContinue(): Promise<boolean>` that the parent calls before advancing.
- Renders the Select / Create toggle and conditionally the `MetricPicker` or inline metric form.
- Inline metric form reuses `DatasetSelector`, `Combobox`, `validateMetric`, `createMetric`.

**`KpiSetupStep.tsx`**
- Stateless. Props: `control`, `register`, `watch`, `errors`, `isEdit`, `dateColumns`.
- Fields: KPI name, target value, direction (with threshold auto-flip side-effect passed up via callback), time column, time grain.
- When `isEdit=true`: renders the amber warning banner at the top; `time_dimension_column` and `time_grain` selectors are `disabled`; behavior is identical to the current form.

**`KpiThresholdsStep.tsx`**
- Stateless. Props: `control`, `register`, `watch`, `errors`, `existingTags`.
- Fields: RAG threshold grid (green/amber/red), program tags, KPI type buttons, `NumberFormatSection`, prefix/suffix `DebouncedInput` pair.

### Modified file

**`webapp_v2/components/kpis/kpi-form.tsx`**
- Change `step` state from `1 | 2` to `1 | 2 | 3`.
- Add a `StepIndicator` (same `StepBlock` + connecting-line pattern from `AlertWizardModal.tsx` lines 155–220) with labels `{ 1: 'Metric', 2: 'KPI Setup', 3: 'Thresholds & Display' }`.
- Replace inline JSX sections with the three new step components.
- Edit mode: `setStep(2)` on open (same as today); hide the `StepIndicator` for edit since step 1 is inaccessible.
- Footer buttons:
  - Step 1: Cancel + Continue (calls `KpiMetricStep.handleContinue()`)
  - Step 2: Cancel + Back + Continue
  - Step 3: Cancel + Back + Create KPI / Save KPI

---

## 5. Reuse Map

| Reused thing | Source path |
|---|---|
| `MetricPicker` | `components/metrics/MetricPicker.tsx` |
| `DatasetSelector` | `components/charts/DatasetSelector.tsx` |
| `Combobox` | `components/ui/combobox.tsx` |
| `createMetric`, `validateMetric` | `hooks/api/useMetrics.ts` |
| `useTableColumns` | `hooks/api/useWarehouse.ts` |
| `NumberFormatSection` | `components/charts/types/shared/NumberFormatSection.tsx` |
| `DebouncedInput` | `components/charts/debounced-input.tsx` |
| `StepIndicator` pattern | `components/alerts/AlertWizardModal.tsx` (lines 155–220) |
| Inline metric form fields + `buildPayload` | `components/metrics/metric-form-dialog.tsx` |
| `AGGREGATION_OPTIONS` | `types/metrics.ts` |

---

## 6. Implementation Notes

### selectedMetric fallback for Step 2
`dateColumns` in Step 2 is derived from `useTableColumns(selectedMetric?.schema_name, selectedMetric?.table_name)` where `selectedMetric = metrics.find(m => m.id === metricId)`. After creating an inline metric, `mutateMetrics()` triggers an async re-fetch — so `selectedMetric` may be `undefined` briefly when Step 2 first renders.

Fix: store the newly created `Metric` object (returned from `POST /api/metrics/`) in a local `useState<Metric | null>` in `kpi-form.tsx`. Use it as a fallback: `const selectedMetric = metrics.find(m => m.id === metricId) ?? inlineCreatedMetric`.

### MetricPicker "Create metric" footer link
`MetricPicker` currently renders a "Create metric →" link to `/metrics?create=true` in its footer (line 69 of `MetricPicker.tsx`). This is redundant when used inside the KPI wizard (users can create inline instead). Add a `hideCreateLink?: boolean` prop to `MetricPicker` and pass it as true from `KpiMetricStep`.

### Dialog width
Current `kpi-form.tsx` uses `max-w-lg`. Step 1 in "Create new" mode includes `DatasetSelector` + mode tabs + column/expression fields — denser than the current Step 1. Bump the `DialogContent` to `max-w-xl` to avoid cramped layout.

### Back navigation from Step 2
When the user clicks Back from Step 2 (regardless of whether the metric was created inline or selected from the list), Step 1 should always show in **"Select existing" mode** with the current `metric_id` pre-selected. The metric already exists in the backend at that point — "Create new" mode doesn't make sense on Back.

### `KpiMetricStep.handleContinue` exposure
Use `useImperativeHandle` + `forwardRef` so the parent (`kpi-form.tsx`) can call `await stepRef.current.handleContinue()` from the footer Continue button without prop-drilling callbacks through render.

---

## 7. What Does NOT Change

- Backend: no changes. Metric and KPI APIs (`POST /api/metrics/`, `POST /api/kpis/`) are unchanged.
- `metric-form-dialog.tsx`: unchanged, still used on the standalone Metrics page.
- Edit mode locked fields (metric, time column, time grain) and the amber warning banner: unchanged.

---

## 7. Verification

1. **Create KPI — select existing metric**: Pick metric in Step 1 → Continue → Step 2 (name auto-filled) → Continue → Step 3 → Create KPI. KPI appears in list.
2. **Create KPI — new simple metric**: Switch to "Create new" → fill datasource + function + column → Continue → metric created, Step 2 name auto-filled → complete wizard → KPI created.
3. **Create KPI — new calculated metric**: Same but with SQL expression → Continue triggers `validate/` → on validation error: error shown, step does not advance → on valid: metric created, wizard advances.
4. **Edit KPI**: Opens at Step 2; metric fields locked; Back/forward between Steps 2 and 3; Save works.
5. **Back navigation**: At Step 2 click Back → returns to Step 1 with prior selection intact. At Step 3 click Back → returns to Step 2 with prior values intact.
6. **Preselected metric** (`preselectedMetricId` prop): Step 1 starts with the metric already selected; Continue is immediately available.
