# Metrics & KPIs — Feature Spec

**Status:** Draft for review
**Audience:** Engineering (Pradeep, Pratiksha, wider eng team), product, leadership
**Paired spec:** alerts-spec.md
**Date:** 2026-04-20

---

## Problem Statement

Across four April-sprint demos (TAP, Bhumi, Baala, Goalkeep), four signals repeated:

1. **"Let us define a calculation once and reuse it."** — Today every chart defines its measure inline, so the same logic gets duplicated and drifts across dashboards.
2. **"Give leadership a scannable KPI view."** — A dedicated page showing "here's where we stand" with target and RAG state, not buried inside dashboards.
3. **"Put KPIs inside dashboards as a chart type."** — Bhumi's explicit ask, with a mid-June deadline for their next quarterly review.
4. **"Tell me WHY this number moved."** — M&E coordinators need to annotate KPIs with program context and beneficiary quotes for stakeholder updates.

This spec covers:
- A **Metric** primitive (analyst-facing, reusable building block)
- A **KPI** layer on top (leadership-facing, tracked with target + RAG + annotations + trendline)
- A **KPI dashboard widget** (resolves Bhumi's June blocker)

---

## Vocabulary (binding decisions)

| Term | Definition | Who sees it |
|------|-----------|-------------|
| **Metric** | Named, saved aggregation. Reusable primitive. | Analysts in the library; everyone in chart builder as "Saved Metrics" |
| **KPI** | A Metric + target + direction + RAG + trend + annotations. Tracked over time. | Leadership, program leads, M&E coordinators on the dedicated KPI page and as dashboard widgets |
| **Measure** | The chart-builder's per-chart value picker. Can be a Saved Metric or an ad-hoc column+aggregation. | Chart builders (rename from today's "Metric" label in charts — dependency below) |

**Team feedback incorporated:**
- "Success Metrics" renamed to **KPIs** — shorter, fits the nav menu, universally understood by leadership.
- "Measure" is the chart-builder concept only — resolves the terminology collision where the chart UI says "Metric" today.

---

## Target Users

| Persona | Primary action | Frequency |
|---------|---------------|-----------|
| **Analyst / data lead** | Defines Metrics in the library. Tags them. Helps others find and reuse them. | Weekly |
| **Program lead** | Defines KPIs on top of Metrics. Sets targets, directions, thresholds. Reviews RAG state. | Weekly/monthly |
| **M&E coordinator** | Annotates KPIs with comments and beneficiary quotes. Owns the "what happened and why" narrative. | Weekly |
| **Internal leadership** | Consumes KPIs on the dedicated page and as dashboard widgets. Glances at current value, target, RAG, trend. | Daily/weekly |
| **Chart builder user** | References saved Metrics as Measures in charts; still has the option to define Measures inline. | As needed |
| **Field team (future)** | Consumes alerts derived from Metrics/KPIs. Cross-referenced in Alerts spec. | — |

---

## Success Metrics (how we measure this feature's success)

**Adoption:**
- Number of Metrics defined per org (target: 10+ within 2 months of launch)
- % of charts using a Saved Metric vs ad-hoc Measures (target: >30% within 3 months)
- Number of KPIs defined per org (target: 5+ within 2 months)
- % of KPIs embedded as dashboard widgets (target: >50%)

**Engagement:**
- % of KPIs with at least one annotation in the last 30 days (target: >40%)
- Number of timeline entries per active KPI per month (target: 2+)

**Qualitative:**
- Leadership confidence: "do you know where the org stands on its goals?" — quarterly check-in question
- M&E coordinator feedback: "has the timeline made it easier to write your stakeholder updates?"

---

## User Stories

### US-1: Create a reusable Metric (visual builder)
**As a** program lead or analyst,
**I want to** define a calculation once and save it to the library,
**So that** the same logic is reused consistently across charts, KPIs, and alerts without drift.

**Acceptance Criteria:**
- [ ] User picks a dataset (schema.table) from the warehouse
- [ ] User picks creation mode: **Simple** (column + aggregation) is default; **SQL** is behind an "Advanced" toggle
- [ ] Simple mode: pick column, pick aggregation (sum/avg/count/min/max/count_distinct), optionally add filters
- [ ] SQL mode: write a raw SQL expression returning a numeric scalar
- [ ] User names the Metric, writes a description, adds tags
- [ ] Preview shows the current computed value before saving
- [ ] Metric is saved to the org's library

### US-2: Browse and find Metrics
**As a** chart builder or program lead,
**I want to** search the Metrics library by name, tag, or dataset,
**So that** I can find and reuse existing calculations instead of creating duplicates.

**Acceptance Criteria:**
- [ ] Search by name or tag
- [ ] Filter by dataset, creation mode, creator
- [ ] Each Metric card shows: name, description, dataset, tags, consumer count ("Used by 3 charts, 2 KPIs")
- [ ] Click-through to Metric detail view

### US-3: Use a Metric in the chart builder
**As a** chart builder user,
**I want to** pick a saved Metric as my chart's Measure,
**So that** my chart stays consistent with the org's official definitions.

**Acceptance Criteria:**
- [ ] Measure picker shows two modes: "Saved Metrics" (library) and "Ad-hoc" (column + aggregation, as today)
- [ ] Saved Metrics tab filtered to those compatible with the current dataset
- [ ] Inline "Create new Metric" button — define and save without leaving the chart builder
- [ ] Ad-hoc mode always available (never gated)

### US-4: Define a KPI with target and RAG
**As a** program lead,
**I want to** promote a Metric to a KPI by setting a target and direction,
**So that** leadership can see at a glance whether we're on track.

**Acceptance Criteria:**
- [ ] Pick an existing Metric from library OR define one inline
- [ ] Set target value (optional — KPIs without a target still track trend, no RAG colour)
- [ ] Set direction: "higher is better" (increase) or "lower is better" (decrease)
- [ ] Set RAG thresholds: green % of target (default 100%), amber % of target (default 80% for increase, 120% for decrease). Red auto-computed.
- [ ] Set time grain per KPI: daily/weekly/monthly/quarterly/yearly (team feedback: per-KPI, not page-level)
- [ ] Set trend periods (default 12)
- [ ] Add tags and metric type (Input / Output / Outcome / Impact)
- [ ] Save

### US-5: Browse the KPI page
**As a** leadership user or program lead,
**I want to** see all my KPIs in one scannable view with current status,
**So that** I know where the org stands without opening multiple dashboards.

**Acceptance Criteria:**
- [ ] Each KPI card shows: current value, target, RAG badge, trendline with readable X-axis, period-over-period change, last-updated timestamp
- [ ] Search, filter by program tag, metric type
- [ ] Linked-alerts indicator (simple "has alerts" dot) on cards with linked alerts
- [ ] Click a card to open detail drawer

### US-6: Annotate a KPI (timeline entries)
**As an** M&E coordinator,
**I want to** add comments and beneficiary quotes to a KPI tied to a specific period,
**So that** I can explain WHY numbers moved and use these notes in stakeholder reports.

**Acceptance Criteria:**
- [ ] From KPI detail drawer, click "Add Entry"
- [ ] Pick entry type: Comment (internal note) or Beneficiary Quote (with attribution field)
- [ ] Pick a period from the KPI's trailing periods dropdown
- [ ] Write content; for quotes, add attribution (e.g. "Beneficiary, Karnataka")
- [ ] On save: snapshot of current value + RAG captured automatically
- [ ] Timeline shows entries newest-first, grouped by period
- [ ] Delta since last period shown on entry card (e.g. "+230 since last month")
- [ ] Multiple entries per period allowed
- [ ] Entries deletable by author or anyone with edit permission

### US-7: Render a KPI in a dashboard widget (Bhumi's blocker)
**As a** dashboard builder,
**I want to** add a KPI as a chart type on my dashboard,
**So that** leadership sees key numbers with status right inside their existing dashboards.

**Acceptance Criteria:**
- [ ] In dashboard builder, "KPI" is a chart type option
- [ ] User selects a KPI from a dropdown
- [ ] Widget renders: current value + target + RAG badge + trendline with readable X-axis (one unified shape in v1)
- [ ] Widget is positionable and resizable on the dashboard canvas like any other chart
- [ ] Widget reflects live KPI state — edits to the KPI propagate to dashboards

### US-8: Edit a Metric with blast-radius awareness
**As an** analyst,
**I want to** edit a Metric and see exactly what will be affected,
**So that** I don't accidentally break charts or KPIs others depend on.

**Acceptance Criteria:**
- [ ] Edit form shows current definition, allows changes
- [ ] On save, confirmation dialog: "This change will affect [list of named consumers]. Continue?"
- [ ] Consumer list shows specific chart/KPI/alert names (not just counts)
- [ ] Change propagates immediately to all consumers on confirm
- [ ] Delete blocked if Metric has any consumers — shows list of what to remove first

---

## Scope

### IN for MVP (v1)

**Metrics:**
- Simple mode: column + aggregation + optional baked-in filters
- SQL mode: raw SQL expression (behind "Advanced" toggle)
- Derived Metrics: expression over other Metrics (single-level in UI builder)
- Reference tracking (which charts/KPIs/alerts use this Metric)
- Inline Metric creation from chart builder, KPI creation, and alert creation
- Edit propagation with blast-radius confirmation dialog
- Delete protection (blocked if referenced)

**KPIs:**
- Metric FK (required)
- Target value (optional)
- Direction (increase/decrease)
- RAG thresholds (green/amber/red) adapting to direction
- Time grain per KPI (daily/weekly/monthly/quarterly/yearly) — team feedback incorporated
- Trend periods config (default 12)
- Trendline with readable X-axis (replaces sparkline)
- Period-over-period change + last-updated timestamp on cards
- Metric type tags (Input/Output/Outcome/Impact)
- Linked-alerts indicator on cards (dot only, no firing-state)

**Annotations:**
- Timeline-of-entries model (Linear-style activity feed)
- Entry types: Comment, Beneficiary Quote (with attribution)
- Period picker, snapshot capture, delta computation
- Multiple entries per period

**Dashboard Widget:**
- KPI as chart type in dashboard builder
- Single unified render: value + target + RAG + trendline
- Positionable and resizable on canvas

**Freshness:**
- "Last updated" label anchored to last completed pipeline run
- Poll on page load

### OUT of scope (explicit, deferred)

| Item | Reason |
|------|--------|
| Time-intelligence helpers (YoY/MoM/QoQ/rolling windows as Metric attributes) | Can compute inside charts; deferred to future iteration |
| Deeper metric composition (chains beyond one level in UI builder) | Achievable via Calculated SQL for power users |
| Access controls / row-level security / per-object ACLs | Separate Access Controls spec |
| Public/external sharing of KPIs | Funders receive alerts via email (Alerts spec) |
| AI chat over KPIs | Separate spec (TAP's future vision) |
| Cross-org Metrics | Metrics scoped to defining org |
| Staggered targets (per-period target overrides) | Deferred — revisit after basic targets ship |
| Drill-down to a dimension (runtime split-by filter) | Deferred — solid v1 without it; avoids time-grain complexity |
| Re-poll on transform completion (freshness) | Ship on-load-only first; add event-driven refresh in follow-up |
| Metric templates/gallery | Post-launch based on usage patterns |

---

## Technical Implications

### Repos affected

| Repo | Changes |
|------|---------|
| **DDP_backend** | New Metric model + CRUD API, new KPI (SuccessMetric) model + CRUD API, AnnotationEntry model + API, reference-tracking queries, SQL validation service |
| **webapp_v2** | Metrics Library page, KPI page (refactor from MetricsList), KPI detail drawer, Metric creation forms (visual + SQL), MeasureSelector refactor (rename from MetricsSelector), KPI dashboard widget component |
| **prefect-proxy** | Possibly: expose pipeline-completion events for freshness polling (follow-up) |

### Data model (conceptual)

**Metric**
- id, name, description, tags (JSONField or M2M)
- dataset_id (FK to existing dataset/source model)
- creation_mode: simple | derived | sql
- For simple: column, aggregation, filters[] (each with baked_in flag)
- For derived: metric_references[] + arithmetic_expression
- For sql: sql_formula (text)
- org_id, created_by, created_at, updated_at

**KPI (SuccessMetric)**
- id, metric_id (FK to Metric — required)
- name (display name, can differ from Metric name)
- target_value (nullable)
- direction: increase | decrease
- green_threshold_pct, amber_threshold_pct
- time_grain: daily | weekly | monthly | quarterly | yearly
- trend_periods (default 12)
- metric_type_tag: input | output | outcome | impact
- program_tags, general_tags
- display_order
- org_id, created_by, created_at, updated_at

**AnnotationEntry**
- id, kpi_id (FK to KPI)
- entry_type: comment | quote
- period_key (string — e.g. "2026-Q1", "2026-04")
- content (text)
- attribution (nullable — for quotes)
- snapshot_value, snapshot_rag, snapshot_achievement_pct
- created_by, created_at

**DashboardWidget extension**
- Existing dashboard component model gains optional kpi_id FK as a source type

### Key existing code to modify
- `webapp_v2/components/charts/MetricsSelector.tsx` — rename to MeasureSelector, add Saved Metrics tab
- `DDP_backend/ddpui/models/dashboard.py` — extend DashboardComponentType to include KPI widget
- `DDP_backend/ddpui/schemas/chart_schema.py` — ChartMetric schema unchanged for ad-hoc; new MetricReference schema for saved
- Frontend KPI page (currently `MetricsList` on prototype branch) — rebuild against new API

---

## Open Questions (for engineering review)

### 1. Derived Metrics — evaluation model
Does `Metric_C = Metric_A / Metric_B` compute at **query time** (backend builds a single SQL joining both base queries) or at **reference time** (fetch A's value, fetch B's value, divide in memory)?

*Trade-off:* Query-time is more correct when consumers add filters/group-by, but harder to implement. Reference-time is simpler but may produce wrong results with dimensional splits.

### 2. Derived Metrics — circular reference prevention
When `Metric_A → Metric_B → Metric_A`, detect and reject. Backend-only validation? UI-time validation? Both?

### 3. Calculated SQL — validation rules
What does the backend check before saving?
- Returns a single numeric scalar?
- No data-mutating statements (INSERT/UPDATE/DELETE/DROP)?
- No prohibited table references?
- Which warehouse-specific features are allowed (CTEs, window functions, JSON)?

### 4. Calculated SQL — UI surface
Single "Create Metric" form with a mode toggle (Simple vs Advanced/SQL), or two separate entry points? Recommendation: single form, SQL behind "Advanced" toggle, with Simple as the clear default.

### 5. MetricEntry backend restoration
Frontend on `pratiksha/alerts-metrics-changes` references MetricEntry endpoints but backend dropped the model. Product decision: keep the timeline. Backend needs to restore: model, migration, schemas, 3 endpoints (GET/POST/DELETE entries).

### 6. Reference tracking implementation
Index strategy for efficiently answering "which charts/KPIs/alerts reference Metric X?" — reverse FK from chart config, or a dedicated reference table?

---

## Dependencies

| Dependency | Description | Blocking? |
|-----------|-------------|-----------|
| **Chart-builder "Measure" rename** | Rename `MetricsSelector` → `MeasureSelector`, update labels across 4 chart types. UI-only, no migration. | Should ship before or alongside |
| **MetricEntry backend restoration** | Re-add model, migration, schemas, 3 endpoints on backend | Blocks annotation timeline |
| **Access controls** | Replace hardcoded `canEdit=true` in MetricsList with role-based gating | Parallel work, not blocking MVP |

### Prototype → production migration
The `pratiksha/alerts-metrics-changes` branch is not released. No production data to migrate. Clean cut:
- Today's `MetricDefinition` table splits into: **Metric** (computation) + **KPI** (target/RAG/trend, FK to Metric)
- `MetricAnnotation` deprecated in favour of restored `AnnotationEntry` timeline

---

## Handoff Checklist

- [x] Problem statement grounded in real user requests (4 orgs, named signals)
- [x] Vocabulary settled (Metric / KPI / Measure — team feedback incorporated)
- [x] User stories with acceptance criteria
- [x] Scope clearly defined (IN vs OUT)
- [x] Data model conceptual design
- [x] Technical implications identified (repos, existing code)
- [x] Dependencies listed
- [ ] Open questions resolved by engineering (6 items pending)
- [ ] Team feedback on time-grain-per-KPI approach confirmed
- [ ] Final sign-off from product + engineering

**Ready for `/plan-feature`?** — After open questions 1-5 are resolved by engineering review.

---

## Appendix: NGO User Perspective Notes

Key recommendations from user-perspective evaluation (to inform UI/UX decisions during planning):

1. **Visual builder must be the default** — SQL mode behind "Advanced" toggle. Preview computed value at each step.
2. **Plain-English labels everywhere** — "How we add up the numbers" not "Aggregation". Inline "?" tooltips.
3. **Blast-radius dialog must name specific charts/KPIs** — not just counts. Show who created them.
4. **Data traceability** — "Last updated" always visible. Drill-down to sample rows for verification.
5. **One-click promotion** — From a Metric card, "Turn into KPI" button. From KPI detail, "Edit underlying Metric" link.
6. **Templates (post-MVP)** — Pre-built Metrics for common NGO calculations (Total Beneficiaries, Attendance Rate, etc.).
7. **Error messages that teach** — "You picked 'Average' but this column contains text. Try 'Count' instead."

---

## Team Feedback Log

| Feedback | Decision |
|----------|----------|
| "Success metrics can be KPIs, or some one word option else it will clutter the menu" | Renamed to **KPI** throughout |
| "Time filters against varying time grains and periods in metrics will make it messy at the metrics dashboard level. Make it per metric." | Time grain is now **per-KPI** configuration, not a page-level filter. Each KPI defines its own grain at creation time. |
