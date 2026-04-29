# Spec: Metrics & KPIs

**Status:** Draft for review **Audience:** Engineering (Pradeep, Pratiksha, wider eng team), product, leadership **Paired spec:** [`alerts-spec.md`](http://./alerts-spec.md) **Vocabulary / scope map:** [`README.md`](http://./README.md)

---

## 1\. Problem & opportunity

Across four April-sprint demos (TAP, Bhumi, Baala, Goalkeep) four signals repeated:

- **"Let us define a calculation once and reuse it."** Swapneel from Goalkeep raised it explicitly; Goalkeep echoed it mentioning Superset metrics as the mental model. Today every chart defines its metric inline, so the same logic gets duplicated and drifts.  
- **"Give leadership a scannable KPI view."** All four orgs. A dedicated page that shows "here's where we stand" with target and RAG state, not buried inside a dashboard.  
- **"Put KPIs inside dashboards as a chart type."** Bhumi's explicit ask, with a **mid-June deadline** for their next quarterly review.  
- **"Tell me WHY this number moved."** M\&E coordinators need to annotate KPIs with program context and beneficiary quotes — both for their own memory and for stakeholder updates.

This spec covers the data and surface that makes all four possible:

1. A reusable **Metric** primitive (analyst-facing, consumable everywhere)  
2. A **KPI** layer on top (leadership-facing, tracked with target \+ RAG \+ annotations \+ trendline)  
3. A **KPI dashboard widget** (resolves Bhumi's June blocker)

## 2\. Vocabulary & scope boundary

See the [README](http://./README.md) for the full vocabulary map. Summary:

- **Metric** — named, saved aggregation; reusable primitive  
- **KPI** — a Metric \+ target \+ direction \+ RAG \+ trend \+ annotations; leadership-facing  
- **Metric (Charts)** — the chart-builder's per-chart picker

**Out-of-scope concepts, called out explicitly here so reviewers know we've considered them:**

- **Time-intelligence helpers** (YoY / MoM / QoQ / rolling windows / cumulative as first-class Metric attributes). People can still compute period-over-period inside a chart or KPI, just not reusably at the Metric level. Deferred.  
- **Derived Metrics** via a dedicated UI (e.g. Metric\_C \= Metric\_A / Metric\_B as a first-class mode). Users who want metric composition can use **Calculated SQL** mode to write the underlying SQL. No separate derivation builder in v1.  
- **Access controls, row-level security, per-object ACLs** — covered in the upcoming **Access Controls spec**, not duplicated here. Today's hardcoded `canEdit=true` on the KPIs page needs to be replaced with real role gating as part of that work.  
- **Staggered targets per period** (different target per quarter / month on the same KPI) — every KPI has a single target in v1. Period-specific overrides deferred.  
- **Drill-down to a dimension** (runtime "split by state" / "filter to Karnataka" on KPIs) — every KPI is viewed at its configured Metric grain in v1. Dimension drill-down deferred.  
- **Page-level time filter on the KPIs page** — deferred per team feedback (mixing time grains across KPIs on one page creates confusing views). Time scoping is handled per-KPI via the Metric's trend config.

## 3\. Users & primary use cases

- **Analyst / data lead** — owns the Metric library. Defines Metrics once, tags them, helps the rest of the org find and reuse them.  
- **Program lead** — defines KPIs on top of Metrics. Sets targets, directions, thresholds. Reviews RAG state weekly/monthly.  
- **M\&E coordinator** — annotates KPIs with comments and beneficiary quotes. Owns the "what happened and why" narrative  
- **Internal leadership** — consumes KPIs on the dedicated page and as dashboard widgets. Glances at current value, target, RAG state, period-over-period change, and last-updated date in one shot.  
- **Chart builder user** (anyone making charts) — references saved Metrics; still has the option to define Metrics inline.  
- **Field team** (future) — consumes alerts derived from Metrics / KPIs. Cross-referenced in the Alerts spec.

## 4\. User flows — Metrics

Short text walk-throughs; no wireframes yet.

### 4.1 Create a Metric

1. The user opens the Metrics library and clicks "New Metric."  
2. Picks a dataset (schema.table from the warehouse).  
3. Picks creation mode:  
   - **Simple** — column \+ aggregation, or a column expression (e.g. `col_a - col_b` before aggregating)  
   - **SQL** — raw SQL expression returning a numeric scalar  
4. For Simple: picks the column (or column expression), picks an aggregation (sum / avg / count / min / max / count\_distinct).  
5. For SQL: writes a raw SQL expression returning a numeric scalar.  
6. Optionally adds filters (e.g. "active beneficiaries only"). Decides whether each filter is baked-in (always applied when the Metric is used) or layered (consumers can opt out).  
7. Names the Metric, writes a description, adds tags.  
8. Saves.

### 4.2 Browse the Metrics library

- Search by name or tag  
- Filter by dataset, creation mode, creator  
- List view shows name, description, dataset, tags, number of consumers (charts / KPIs / alerts using it)

### 4.3 View a Metric's detail

- Full definition (dataset, column or SQL expression, aggregation, filters, tags, description)  
- **References panel**: "Used by 3 charts, 2 KPIs, 1 alert" — click through to each  
- Recent value \+ trend snapshot (running the Metric against the warehouse, like today's MetricDataPoint)  
- Edit / delete actions (gated by reference check)

### 4.4 Edit a Metric

1. The user clicks "Edit" from the detail view.  
2. Adjusts fields.  
3. On save, the system calculates the blast radius: "This change will affect 3 charts, 2 KPIs, 1 alert. The change propagates immediately to all of them. Continue?"  
4. User confirms. Change applies to all consumers.

### 4.5 Delete a Metric

- Blocked if the Metric is referenced anywhere. User sees "This Metric is used by \[list\]. Remove those references first."  
- Unblocked Metrics delete cleanly.

### 4.6 Use a Metric in chart builder

- In the chart builder's Metric picker, the user sees two tabs or a toggle: **Saved Metrics** (pick from library) and **Ad-hoc** (column \+ aggregation inline, as today).  
- Saved Metrics tab shows the library, filtered to Metrics compatible with the current dataset.  
- Inline "Create new Metric" button in the picker — lets user define a brand-new Metric right there and save it to the library without leaving the chart builder.

### 4.7 Use a Metric as the basis for a KPI

- From the KPIs page, "New KPI" flow lets user pick an existing Metric OR define one inline (same "create Metric" form embedded).  
- After the Metric is chosen, the form asks for target, direction, RAG thresholds, trend config, tags. See flow 5.1.

### 4.8 Use a Metric in an alert

See [`alerts-spec.md`](http://./alerts-spec.md) § 4\. Entry points are the same pattern: pick from library or create inline.

## 5\. User flows — KPIs

### 5.1 Create a KPI

1. From the KPIs page, "New KPI."  
2. Pick an existing Metric from the library OR define one inline.  
3. Set **target value** (Compulsory)  
4. Set **direction** — "higher is better" (increase) or "lower is better" (decrease). Controls how RAG \+ trend colour reads.  
5. Set **RAG thresholds** — green % of target (default 100), amber % of target (default 80 for increase, 120 for decrease). Red is auto-computed as "anything below amber" (or above, for decrease).  
6. Set **trend config** — time grain (month / quarter / year — inherits from the Metric's trend grain by default) and number of trailing periods to show in the trendline (default 12).  
7. Add **tags** and **metric type** (Input / Output / Outcome / Impact — from the existing taxonomy).  
8. Save.

### 5.2 Browse the KPIs page

- Search, filter by program tag, metric type, group-by (same as today's MetricsList)  
- Each card shows: current value, target, RAG badge, trendline with readable X-axis, period-over-period change, last-updated timestamp  
- **Linked-alerts indicator** (dot or small badge) on each card when alerts are linked to that KPI. Does NOT show firing state or counts — just "has alerts." Full state available from the alert list.  
- No page-level time filter — each KPI is scoped by its own trend config, which avoids confusion when the page mixes time grains (team feedback).

### 5.3 Open a KPI's detail drawer

- Opens from clicking a card (today's MetricDetailDrawer pattern)  
- Header: KPI name, current value, target, RAG badge, full trendline with X-axis, period-over-period change  
- **Time-window selector** in the drawer header — viewer can widen or narrow the trendline's window (e.g. "Last 6 / 12 / 24 months" for a monthly-grain KPI; equivalents for quarterly / yearly). Defaults to the KPI's configured `trend_periods`. Session-only — does not persist to the KPI's config. The trendline and period-over-period change respect the selected window. Annotation-timeline filtering under the window is an open question (see § 10).  
- Body: **annotations timeline** (see flow 5.6), linked alerts section (see Alerts spec)  
- Actions: Edit, Delete, Create Alert from here, Add Entry

### 5.4 Edit / delete a KPI

- Edit is a modal version of the create form  
- Delete is blocked if any alert is linked — user removes the alert first (same pattern as today's Metric-with-alerts constraint)

### 5.5 Render a KPI in a dashboard (Bhumi's blocker)

1. In the dashboard builder, user picks "KPI" as the chart type.  
2. Selects a KPI from a dropdown.  
3. The widget renders **the same shape as a KPI card**: current value \+ target \+ RAG \+ trendline with X-axis — a single unified render (v1 ships one shape only).  
4. User positions and resizes the widget on the dashboard canvas like any other chart.  
5. Widget always reflects the live KPI — if the KPI is edited later, dashboards update.

### 5.6 Annotate a KPI (timeline of entries)

1. From the drawer, user clicks "Add Entry."  
2. Picks entry type: **Comment** (internal note) or **Beneficiary Quote** (with attribution field).  
3. Picks a period (from a dropdown of the KPI's trailing periods).  
4. Writes content.  
5. For quotes, adds attribution (e.g. "Beneficiary, Karnataka").  
6. Saves. A snapshot of the KPI's current value \+ RAG at save time is captured automatically.  
7. The entry appears in the timeline, newest first, grouped by period.  
8. Multiple entries per period are allowed — each preserves its author, timestamp, and snapshot.  
9. **Delta since the last time period in the config** is computed automatically (e.g. "+230 since last month" when the KPI's grain is monthly) and shown on the entry card.

Entries can be deleted by the author or anyone with edit permission on the KPI.

### 5.7 Create an alert from a KPI

See [`alerts-spec.md`](http://./alerts-spec.md) § 4.1.

## 6\. Functional requirements — Metrics

- **Dataset \+ table \+ column \+ aggregation** (sum / avg / count / min / max / count\_distinct)  
- **Column expressions in Simple mode** — a Metric's column slot can be a simple arithmetic expression over columns (e.g. `col_a - col_b`), evaluated before aggregation.  
- **Optional filters at definition time** (e.g. "active beneficiaries only"). User chooses at creation time whether a filter is baked into the Metric (always applied) or layered by the consumer (passed in at reference time).  
- **Name, description, tags**  
- **Reference tracking**: given a Metric, list every chart / KPI / alert that uses it.  
- **Chart builder's Metric picker** offers saved Metrics alongside ad-hoc column+aggregation. Ad-hoc is always available — never gated.  
- **Inline Metric creation** — when picking a Metric (in chart builder, KPI creation, or Alert creation), user can define a brand-new Metric inline and save it to the library without leaving the current flow.  
- **Calculated SQL expression Metrics** — a Metric's formula can be a raw SQL expression returning a numeric scalar (e.g. `SUM(CASE WHEN status='active' THEN 1 END)`). No special authoring permission — anyone who can create a Metric can use SQL mode. This mode is also how users can express metric-over-metric composition (write the full SQL); there is no separate Derived-Metric builder. Validation rules and UI shape are open questions (see § 8).  
- **Edit propagation** — when a Metric is edited, the change propagates immediately to every consumer (chart, KPI, alert). Before saving, the user is shown a confirmation dialog listing all affected consumers so they can review the blast radius. No version-locking in v1.

## 7\. Functional requirements — KPIs

- **Maps from today's `MetricDefinition`** to a new KPI object that holds a foreign key to a Metric.  
- **Direction-aware RAG** (increase / decrease). Thresholds adapt to direction.  
- **Single target per KPI** — no staggered-by-period targets in v1.  
- **Period-over-period change \+ last-updated timestamp on every card** — surfaced on the card, not only in the drawer.  
- **Trendline with readable X-axis** — replaces today's sparkline. Shown on both the card and inside the drawer.  
- **In-drawer time-window selector** — inside the KPI detail drawer, the viewer can widen or narrow the trendline window (e.g. "Last 6 / 12 / 24 months" for a monthly-grain KPI). Defaults to the KPI's configured `trend_periods`. Session-only (does not mutate the KPI's stored config). Trendline and period-over-period change respect the selected window. Card and dashboard-widget renders are not affected — they always use the KPI's configured default.  
- **Annotations timeline** — timeline-of-entries model (Linear-style activity feed). Each entry: type (comment / beneficiary quote), period, content, attribution (for quotes), snapshot of value \+ RAG at entry time, author, timestamp. Multiple entries per period allowed. Delta-since-last-period (anchored to the KPI's time grain) computed. Full audit trail.  
- **KPI as a dashboard chart type** — one render at v1 (value \+ target \+ RAG \+ trendline with X-axis in one widget). Editable placement and size.  
- **Linked-alerts indicator** on cards — KPIs page only, not on dashboard widgets. Simple "has alerts" marker, no counts or firing-state on the indicator.  
- **Freshness** — surface a "last updated" label anchored to the last completed transform/pipeline that fed this KPI's data. Data refresh: poll on page load; additionally re-poll when a new transform completes (if engineering-feasible; otherwise ship on-load-only and add the transform-completion poll in a follow-up).

**Access controls** (view/edit/delete permissions) are out of scope for this spec — covered in the separate Access Controls spec.

## 8\. Data model — conceptual

Entities and relationships at a conceptual level; schema details deferred to engineering design.

- **`Metric`** — the reusable primitive.  
    
  - Identity: `id`, `name`, `description`, `tags`  
  - Source: `dataset_id`, creation mode (simple / sql)  
  - For simple mode: `column` (or column expression), `aggregation`, optional `filters` (with a flag per filter: baked-in vs layered)  
  - For SQL mode: raw SQL formula string  
  - Metadata: `created_by`, `created_at`, `updated_at`  
  - Indexes for reference-tracking queries (find all consumers of Metric X)


- **`KPI`** — the tracked layer.  
    
  - `metric_id` (FK to Metric — required)  
  - `target_value` (nullable — no target \= tracking-only)  
  - `direction` (increase / decrease)  
  - `green_threshold_pct`, `amber_threshold_pct`  
  - `trend_grain` (month / quarter / year — inherits from Metric by default)  
  - `trend_periods` (default 12\)  
  - `metric_type_tag` (Input / Output / Outcome / Impact)  
  - `program_tag`, general tags  
  - `display_order`  
  - Timestamps \+ `created_by`


- **`AnnotationEntry`** — timeline model.  
    
  - `kpi_id` (FK)  
  - `entry_type` (comment / quote)  
  - `period_key`  
  - `content`  
  - `attribution` (nullable — used for quotes)  
  - `snapshot_value`, `snapshot_rag`, `snapshot_achievement_pct` — captured at save time  
  - `created_by`, `created_at`  
  - Multiple entries per (kpi\_id, period\_key) are allowed.


- **`DashboardWidget` reference** — on the dashboard side, points at a KPI. The existing dashboard-widget model extends to accept `kpi_id` as a source.

## 9\. Out of scope (explicit)

- **Time-intelligence helpers** (YoY / MoM / QoQ / rolling windows / cumulative as first-class Metric attributes). People can still compute period-over-period inside a chart or KPI, just not reusably at the Metric level. Deferred.  
- **Derived Metrics as a dedicated creation mode** — metric-over-metric composition lives in Calculated SQL, not a separate builder UI.  
- **Access controls, row-level security, per-object ACLs** — covered in the separate Access Controls spec.  
- **Staggered targets per period** — every KPI has a single target in v1. Period-specific overrides deferred.  
- **Drill-down to a dimension** — every KPI is viewed at its configured grain in v1. Runtime "split by state" / "filter to Karnataka" deferred.  
- **Page-level time filter on the KPIs page** — mixing time grains on one page creates confusing views. Time scoping is per-KPI via the trend config.  
- **Public / external sharing of KPIs** — not in v1; funders / external stakeholders receive *alerts* via email (see Alerts spec).  
- **AI chat over KPIs** (TAP's future vision) — separate spec.  
- **Cross-org Metrics** — Metrics are scoped to the org that defined them. No sharing across orgs.  
- **Showing dataset-** when people are computing metrics

## 10\. Open questions — for team / engineering review

These are design calls we have NOT made. Please weigh in when you review.

- **Calculated SQL — validation.** What does the backend check before saving a SQL formula?  
    
  - That it returns a single numeric scalar?  
  - That it doesn't reference prohibited tables?  
  - That no data-mutating statements (INSERT / UPDATE / DELETE / DROP) are present?  
  - Which warehouse-specific dialect features are allowed (window functions, CTEs, JSON extraction, …)?


- **Calculated SQL — UI surface.** A single "Create Metric" form with a mode toggle (simple column+agg vs SQL editor), or two separate flows? How do we prevent a user from accidentally landing in SQL mode when they wanted a simple Metric?  
    
- **Simple-mode column expressions — how far?** Today's "column \+ aggregation" is one slot. Allowing `col_a - col_b` in the column slot is a meaningful expansion. Do we support arbitrary arithmetic (+, \-, \*, /, parentheses), or something more constrained? Where's the line between "Simple mode with expressions" and "you should use SQL mode"?  
    
- **In-drawer time-window — does it filter the annotations timeline too?** When a user narrows the drawer's window to "Last 6 months," does the annotations timeline also hide entries older than 6 months, or stay as a full-history scroll regardless? Option A (filter) keeps the view consistent; option B (full history) preserves context. Could also land on "filter but with a visible count like '+12 older entries, expand to see'."  
    
- **`MetricEntry` restoration on backend.** The frontend on the current branch still references `MetricEntry` endpoints (`useMetricEntries`, `useCreateEntry`, `useDeleteEntry`) and the full timeline drawer UI, but the backend on this branch has dropped the model, migration, schemas, and API. The product decision is to keep the timeline model. Production build needs to **restore the backend** — re-add the `MetricEntry` model (or equivalent, named appropriately under the KPI rename), migration, schemas, and three endpoints (`GET /{kpi_id}/entries/`, `POST /{kpi_id}/entries/`, `DELETE /{kpi_id}/entries/{entry_id}/`).

## 11\. Success indicators

**Adoption:**

- **\# of Metrics defined per org**  
- % of charts in dashboards that reference a saved Metric vs ad-hoc metrics(measures the pull-through of the reusable layer)  
- of KPIs defined per org  
- % of KPIs referenced in a dashboard widget (not just the KPIs page)

**Engagement:**

- % of KPIs with at least one annotation in the last 30 days (is the timeline being used?)  
- of timeline entries per active KPI per month

**Qual signals:**

- Leadership confidence: "do you know where the org stands on its goals?" — asked in quarterly check-ins  
- M\&E coordinator feedback: "has the timeline made it easier to write your stakeholder updates?"

---

## Dependencies

- **`MetricEntry` backend restoration.** See open question above.  
- **Real access controls.** Today `canEdit=true` is hardcoded in `MetricsList.tsx`. Replace with role-based gating as part of the Access Controls work.

## Prototype → production migration

The current `pratiksha/alerts-metrics-changes` branch is not released. No existing production data to migrate. Engineering has a clean cut to rebuild the data model:

- Today's `MetricDefinition` table splits into two: a new `Metric` table (holds the computation) and a new `KPI` table (holds target/RAG/trend config with a FK to Metric).  
- `MetricAnnotation` stays or gets deprecated in favour of the restored annotation-entries timeline — decision TBD with engineering during review. Product direction is the timeline.

---

*Questions? Open a comment on this doc or ping the product team. Final sign-off from product \+ engineering before production build begins.*

# Team feedback (applied)

Both items below came from team review and have been baked into the spec above.

- ✅ **"Success Metrics" renamed to "KPIs"** — single word to avoid cluttering the nav menu.  
- ✅ **Page-level time filter dropped** — mixing time grains on one page is messy. Time scoping is now per-KPI via each KPI's own trend config.

