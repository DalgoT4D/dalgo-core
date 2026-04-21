# Metrics & KPIs — v1

**Scoped from**: ../spec.md
**Version**: v1
**Status**: Draft
**Date**: 2026-04-21

---

## Scope for this iteration

### Guiding principle

Ship the end-to-end chain: **Metric creation -> reuse in charts + KPI definition -> KPI page -> KPI dashboard widget**. This resolves Bhumi's mid-June blocker, delivers the "scannable KPI view" that four orgs asked for, and fulfills the core ask of "define a calculation once and reuse it" across both charts and KPIs.

### What's included

- **US-1 (simplified): Create a Metric** — Simple mode only (column + aggregation + optional filters). No SQL mode, no derived Metrics.
- **US-2: Browse Metrics library** — Search by name/tag, filter by dataset. Basic card view with name, description, dataset, tags.
- **US-4: Define a KPI** — Pick a Metric, set target/direction/RAG thresholds/time grain/trend periods/metric type tag. Full story.
- **US-5: KPI page** — Scannable card view with current value, target, RAG badge, trendline, period-over-period change, last-updated. Search and filter.
- **US-7: KPI dashboard widget** — KPI as a chart type in the dashboard builder. Renders value + target + RAG + trendline. Positionable and resizable.
- **US-3: Use a Metric in the chart builder** — Measure picker shows "Saved Metrics" tab alongside ad-hoc mode. Saved Metrics filtered to compatible dataset.
- **"Measure" rename in chart builder** — Rename MetricsSelector to MeasureSelector, update labels across chart types. Resolves terminology collision.
- **Basic Metric/KPI edit and delete** — Edit forms for both. Delete blocked if Metric has consumers (show list of KPIs and charts). No full blast-radius dialog yet.

### What's deferred to later versions

| Item | Reason |
|------|--------|
| SQL mode for Metrics | Resolves open question #3/#4 first; simple mode covers >80% of NGO use cases |
| Derived Metrics (Metric_A / Metric_B) | Resolves open questions #1/#2 first; complex evaluation model |
| Inline Metric creation from chart builder | v1 requires picking from library; inline creation in v2 |
| US-6: Annotations / timeline entries | Valuable but not blocking the core KPI view; ships in v2 |
| US-8: Full blast-radius confirmation dialog | v1 has basic delete protection; full named-consumer dialog in v2 |
| Reference tracking (consumer counts on Metric cards) | Needs indexing strategy (open question #6); basic FK check sufficient for v1 |
| Linked-alerts indicator on KPI cards | Depends on Alerts feature progress |
| Metric templates/gallery | Post-launch based on usage patterns |

---

## User Stories (scoped)

### Story 1: Create a Metric (simple mode)
**As a** program lead or analyst, **I want to** define a calculation by picking a column and aggregation, **so that** I can reuse it across charts and KPIs.

**Acceptance Criteria:**
- [ ] User picks a dataset (schema.table) from the warehouse
- [ ] User picks a column and aggregation (sum/avg/count/min/max/count_distinct)
- [ ] User can optionally add filters (column + operator + value)
- [ ] User names the Metric, writes a description, adds tags
- [ ] Preview shows the current computed value before saving
- [ ] Metric is saved to the org's library
- [ ] Validation: name is required, column + aggregation is required

### Story 2: Browse Metrics library
**As a** program lead, **I want to** search and browse saved Metrics, **so that** I can find the right one to attach to a KPI.

**Acceptance Criteria:**
- [ ] List view of all Metrics in the org
- [ ] Search by name or tag
- [ ] Filter by dataset
- [ ] Each card shows: name, description, dataset, tags, current value
- [ ] Click to open edit view

### Story 3: Use a Metric in the chart builder
**As a** chart builder user, **I want to** pick a saved Metric as my chart's Measure, **so that** my chart stays consistent with the org's official definitions.

**Acceptance Criteria:**
- [ ] Measure picker shows two tabs: "Saved Metrics" (library) and "Ad-hoc" (column + aggregation, as today)
- [ ] Saved Metrics tab filtered to those compatible with the current dataset
- [ ] Ad-hoc mode always available (never gated)
- [ ] Rename MetricsSelector to MeasureSelector; update "Metric" labels to "Measure" across all chart types

### Story 4: Define a KPI
**As a** program lead, **I want to** promote a Metric to a KPI with target and RAG thresholds, **so that** leadership can see at a glance whether we're on track.

**Acceptance Criteria:**
- [ ] Pick an existing Metric from the library (required)
- [ ] Set display name (defaults to Metric name)
- [ ] Set target value (optional — no RAG colour if omitted)
- [ ] Set direction: "higher is better" or "lower is better"
- [ ] Set RAG thresholds: green % (default 100%), amber % (default 80% for increase / 120% for decrease)
- [ ] Set time grain: daily/weekly/monthly/quarterly/yearly
- [ ] Set trend periods (default 12)
- [ ] Set metric type tag: Input / Output / Outcome / Impact
- [ ] Add program tags
- [ ] Save

### Story 5: Browse the KPI page
**As a** leadership user, **I want to** see all KPIs in one scannable view, **so that** I know where the org stands.

**Acceptance Criteria:**
- [ ] Each KPI card shows: current value, target, RAG badge, trendline (with readable X-axis), period-over-period change, last-updated timestamp
- [ ] Search by name
- [ ] Filter by program tag, metric type
- [ ] Click a card to open detail drawer (shows full trend chart, KPI config, edit button)
- [ ] "Last updated" anchored to last completed pipeline run

### Story 6: KPI dashboard widget
**As a** dashboard builder, **I want to** add a KPI as a chart type, **so that** leadership sees key numbers inside their existing dashboards.

**Acceptance Criteria:**
- [ ] "KPI" appears as a chart type option in dashboard builder
- [ ] User selects a KPI from a dropdown
- [ ] Widget renders: current value + target + RAG badge + trendline (readable X-axis)
- [ ] Widget is positionable and resizable on the dashboard canvas
- [ ] Widget reflects live KPI state — edits propagate automatically

### Story 7: Edit and delete Metrics/KPIs
**As an** analyst, **I want to** edit or delete Metrics and KPIs safely.

**Acceptance Criteria:**
- [ ] Edit Metric: update name, description, tags, column, aggregation, filters
- [ ] Edit KPI: update display name, target, thresholds, time grain, tags
- [ ] Delete Metric: blocked if any chart or KPI references it — show list of consumers
- [ ] Delete KPI: confirmation dialog, removes from KPI page and any dashboard widgets

---

## Dependencies

- **Requires**: Existing dataset/source model in DDP_backend (already exists)
- **Requires**: Existing dashboard builder infrastructure in webapp_v2 (already exists)
- **Enables**: v2 (annotations, SQL mode, derived Metrics, blast-radius dialog)
- **Parallel**: Alerts feature can proceed independently; linked-alerts indicator ships when both features are ready

---

## Open questions carried into v1

These are scoped out of v1 implementation but should be resolved before v2 planning:

1. Derived Metrics evaluation model (query-time vs reference-time)
2. Circular reference prevention strategy
3. SQL validation rules
4. MetricEntry backend restoration (needed for v2 annotations)
5. Reference tracking index strategy (needed for v2 blast-radius dialog)

---

## Acceptance gate

v1 is shippable when:
- [ ] An analyst can create a simple Metric and preview its value
- [ ] A chart builder can pick a saved Metric as a Measure in any chart type
- [ ] A program lead can create a KPI from that Metric with target and RAG
- [ ] Leadership can see all KPIs on the KPI page with live RAG and trendlines
- [ ] A dashboard builder can embed a KPI widget on a dashboard
- [ ] Bhumi can use KPI widgets in their quarterly review dashboards
