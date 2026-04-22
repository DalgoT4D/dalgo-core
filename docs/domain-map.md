# Dalgo Domain Map

Single source of truth for Dalgo's product entities, how they depend on each other, and how changes propagate.

## Purpose

When you change an entity (e.g. Metric), the spec and plan must account for every downstream surface that consumes it. This map exists because product-level relationships (e.g. "ReportSnapshot freezes Dashboard layout but queries data live") are not derivable from code alone — they live in the team's head and must be written down.

## How the AI uses this

`/product/write-spec` and `/engineering/plan-feature` read this file before producing a spec or plan:

1. Identify primary entity(ies) being changed.
2. Read each entity's **One-line identity**, **Consumed by** (with edge labels), and **Platform-specific behaviors** — the three fields that carry the most reasoning signal.
3. Traverse `Consumed by` edges 1-hop and 2-hop. Use the edge label to decide whether the impact is auto-inherited (`snapshot-of`, `compose`) or explicit (`embed`, `reference`).
4. Produce the plan's **Blast Radius** table. For any unaddressed surface, stop and ask the user.

## How humans maintain this

Every entry has a **Confidence** tag. Treat the map as living — the tags are your roadmap for what to verify with the team:

| Confidence | Meaning | Action |
|------------|---------|--------|
| `verified` | Grounded in code (models, endpoints, components read directly). Safe to reason from. | Re-check only when code changes. |
| `draft` | Based on filesystem / naming / spec references, not direct code read. | Have someone read the actual code and promote to `verified`. |
| `tribal-knowledge-needed` | Behavior depends on team convention or planned work not yet in code. | Pradeep / Pratiksha / whoever owns that surface must confirm; then promote. |

When an entry gets proven wrong in production, downgrade its confidence and add a note.

---

## Entity shape

Every entity has these fields:

| Field | What goes here |
|-------|----------------|
| **One-line identity** | The 30-second explanation for a new hire. Platform-generic language dies here — if it sounds like it could describe any NGO tool, it's too vague. |
| **What it is (detail)** | Extended explanation when the one-liner isn't enough. |
| **Consumes** | Direct upstream edges. Each edge labeled with **how** it consumes (see edge labels below). |
| **Consumed by** | Direct downstream edges with **how** they consume this entity. Load-bearing for impact analysis. |
| **Platform-specific behaviors** | Dalgo-only truths. "In Dalgo specifically, this entity…" — captures tribal knowledge that's invisible from the outside. |
| **Change impact** | How changes propagate. Includes gotchas and known edge cases. |
| **Confidence** | `verified` / `draft` / `tribal-knowledge-needed` |

### Edge labels (the "how" of a relationship)

| Label | Meaning | Propagation semantics |
|-------|---------|----------------------|
| `snapshot-of` | Frozen copy of upstream at a point in time. | Whatever upstream looked like at snapshot time is baked in. Future upstream changes do NOT flow. |
| `compose` | User explicitly arranges/includes children. | New child types need explicit support in the composer UI; otherwise they won't appear. |
| `embed` | Upstream rendered inline at view-time. | Live — upstream edits appear immediately on next render. |
| `reference` | Linked by ID. | Value/config changes on the referenced entity cascade live. Renames are safe if consumers use the ID. Deletions cause broken references. |
| `trigger` | Event-driven firing. | Upstream event causes downstream creation. No persistent link afterward. |
| `query-from` | Runtime query against upstream data. | Schema changes in upstream break queries. No stored link. |

Only 1-hop edges are listed per entity. Transitive paths (Metric → Dashboard → Report) are computed by traversal, never hardcoded — hardcoded chains rot when a new hop is added.

---

# Entities

## Data Layer

### Source
- **One-line identity:** An Airbyte connector pulling external data into the org's warehouse.
- **What it is (detail):** Source represents a connection to an external system (Google Sheets, Postgres, KoboToolbox, Salesforce) managed through Airbyte. Credentials, schema mapping, and schedule are stored here.
- **Consumes:** External system APIs (`query-from`), credentials (`reference`).
- **Consumed by:**
  - Pipeline (`compose`) — a Source is one step in the ingest flow
  - Warehouse (`query-from` → writes raw tables)
- **Platform-specific behaviors:** Sources in Dalgo live behind the `ingest/` route on webapp_v2 and are orchestrated via Airbyte's own API, not directly queried by the Django backend.
- **Change impact:** Source schema changes break downstream Transforms. Credential rotation requires re-auth. Removing a Source orphans its raw tables in the Warehouse.
- **Confidence:** `draft` (filesystem + CLAUDE.md; need to read `models/airbyte.py` + `ddpairbyte/` for `verified`)

### Warehouse
- **One-line identity:** The org's analytical database — Postgres or BigQuery — where raw and modeled data live.
- **What it is (detail):** Configured per-org. Sources write raw tables; Transforms write modeled tables; Charts and Metrics read from it at render/evaluation time.
- **Consumes:** Source data (`query-from`), Transform output (`query-from`).
- **Consumed by:**
  - Transform (`query-from` reads raw, writes modeled)
  - Chart (`query-from` at render time)
  - Metric (`query-from` at evaluation time)
  - Data Quality check (`query-from` for assertions)
- **Platform-specific behaviors:** Warehouse type (Postgres vs BigQuery) is an org-level setting; SQL dialect differs. Dalgo has a warehouse-adapter layer that normalizes some but not all operations.
- **Change impact:** Schema change cascades to every Chart/Metric/Transform referencing affected columns. Warehouse type switch requires SQL-dialect audit across every consumer.
- **Confidence:** `draft`

### Transform
- **One-line identity:** A dbt model that shapes raw ingested data into analytics-ready tables.
- **What it is (detail):** Managed through the Transform UI (`transform/` route). dbt runs via Prefect as a step in the Pipeline.
- **Consumes:** Warehouse raw tables (`query-from`), upstream Transforms (`query-from`).
- **Consumed by:**
  - Warehouse (writes modeled tables)
  - Chart (`query-from` — Charts typically point at modeled tables)
  - Metric (`query-from`)
  - Pipeline (`compose` — Transforms are steps in the flow)
- **Platform-specific behaviors:** dbt lineage view shows lineage *inside* dbt but not the link from a modeled column out to a Chart or Metric — that cross-cut is only visible via this map.
- **Change impact:** Column renames/removals in modeled tables silently break every downstream Chart/Metric. No compile-time check across the boundary.
- **Confidence:** `draft` (need to read `ddpdbt/` + `models/dbt_workflow.py`)

### Pipeline
- **One-line identity:** A Prefect flow that orchestrates Sources → Transforms → checks on a schedule.
- **What it is (detail):** Runs Airbyte syncs, dbt models, and Data Quality checks as sequential tasks under a shared schedule.
- **Consumes:** Source (`compose`), Transform (`compose`), Data Quality check (`compose`).
- **Consumed by:**
  - Notification (`trigger` — success/failure events create notifications)
  - Alert (`trigger` — pipeline-failure alerts)
- **Platform-specific behaviors:** Pipelines run via the `prefect-proxy` service, not directly from Django. "Last updated" timestamps on downstream Charts/Metrics/Reports are all anchored to the last successful Pipeline run.
- **Change impact:** Schedule changes affect every downstream "last updated" timestamp and Report/Scheduled-email timing. Pipeline failure makes all downstream data stale until next success — silently, unless an Alert fires.
- **Confidence:** `draft`

### Data Quality check
- **One-line identity:** An assertion on warehouse data (not-null, unique, freshness, row count) that runs as a Pipeline step.
- **What it is (detail):** Managed through `data-quality/` route. Checks pass/fail during Pipeline execution; results drive Alerts.
- **Consumes:** Warehouse table / column (`query-from`).
- **Consumed by:**
  - Pipeline (`compose`)
  - Alert (`trigger` on failure)
- **Platform-specific behaviors:** Unknown whether a failing check blocks downstream Pipeline steps or only logs. Need to confirm with team.
- **Change impact:** A removed check can silently allow data regressions to propagate into Reports. A flipped-to-failing check may cascade into pipeline failures if blocking.
- **Confidence:** `tribal-knowledge-needed` (blocking vs non-blocking behavior is unclear to me)

---

## Analytics Layer

### Chart
- **One-line identity:** A single visualization (bar / pie / line / number / map / table / pivot_table) configured via the chart builder, bound to a warehouse table.
- **What it is (detail):** Stores `schema_name + table_name + extra_config`. The `extra_config.metrics[]` array contains `ChartMetric` entries — either inline (`column + aggregation + alias`) or saved metric references (`saved_metric_id`). Chart types are a fixed enum.
- **Consumes:** Warehouse (`query-from`), Transform (`query-from`), Metric (`reference` — via `saved_metric_id` in `extra_config.metrics[]`), ad-hoc ChartMetric inline.
- **Consumed by:**
  - Dashboard (`compose` — Charts are one of the DashboardComponentType values: CHART, TEXT, HEADING)
  - ReportSnapshot (`snapshot-of` Dashboard → captures `frozen_chart_configs` keyed by chart_id)
  - Explore page (`embed` — live exploration; relationship unclear — see Explore)
- **Platform-specific behaviors:**
  - Chart types are a **fixed enum**; adding a new type (e.g. a KPI chart) requires code changes, not config.
  - Chart config lives in `extra_config` as a JSON blob — loose schema, brittle to LLM introspection.
  - `computation_type` field is deprecated (kept for DB compatibility) — don't base new logic on it.
- **Change impact:** Chart config ties to specific column names; upstream renames break rendering. Chart-type additions must be wired into both the builder and every render surface (Dashboard, ReportSnapshot, Explore, public share views).
- **Confidence:** `verified` (read `models/visualization.py`)

### Metric picker *(sub-concept of Chart, not a standalone entity)*
- **One-line identity:** The chart-builder's per-chart metric picker — either a Saved Metric or an ad-hoc column+aggregation.
- **What it is (detail):** Lives in the chart-builder UI as `MetricsSelector`. Two tabs: "Saved Metrics" (references a `Metric` by `saved_metric_id`) and "Ad-hoc" (inline `ChartMetric` with column + aggregation + alias). No rename — "metric" is used everywhere.
- **Consumes:** Metric (`reference`, optional), Warehouse column (`query-from`, inline mode).
- **Consumed by:** Chart (`compose`).
- **Platform-specific behaviors:**
  - `ChartMetric` is the inline schema shape (`column + aggregation + alias`); `Metric` is the DB model (saved, reusable, with mode: simple or SQL).
  - When a saved Metric is used in a chart, it's resolved at query time: `saved_metric_id` → `Metric` DB row → `MetricSchema` → `ChartMetric`.
- **Change impact:** Adding "Saved Metrics" tab to MetricsSelector; existing ad-hoc behavior unchanged.
- **Confidence:** `draft`

### Metric *(arriving in v1 of the Metrics & KPIs spec)*
- **One-line identity:** A named, saved aggregation (e.g. "Active Students") — defined once in the library, referenced from Charts, KPIs, and Alerts.
- **What it is (detail):** New DB model per the Metrics & KPIs spec. Two creation modes: Simple (`column_expression + aggregation`) and SQL (`sql_expression` returning numeric scalar). No filters, no tags. Validated on save by executing a test query against the warehouse. Serialized via `MetricSchema` for API responses; converted to `ChartMetric` when used in chart query execution.
- **Consumes:** Warehouse (`query-from`), Transform (`query-from`).
- **Consumed by:**
  - Chart (`reference` — via `saved_metric_id` in `extra_config.metrics[]`)
  - KPI (`reference` — required FK, `on_delete=PROTECT`)
  - Alert (`reference` — threshold evaluation against Metric value; deferred to Alerts spec)
- **Platform-specific behaviors:**
  - **Does NOT have a direct render path to ReportSnapshot in Dalgo.** Metric values reach Reports only via Chart → Dashboard → ReportSnapshot. Do not treat Report as a direct Metric consumer.
  - **One Metric entity in the codebase.** The existing inline chart config shape (`column + aggregation + alias`) is `ChartMetric`. `Metric` is the persisted, reusable entity; `ChartMetric` is the inline, per-chart shape. When a chart uses a saved Metric, the resolution path is: `saved_metric_id` → `Metric` DB row → `MetricSchema` → `ChartMetric`.
  - Delete-blocked if consumers exist (Charts with `saved_metric_id` or KPIs with FK).
- **Change impact:** Column/aggregation change flows live to every consumer on next evaluation. Renames are safe if consumers reference by ID. Deletion is blocked until consumers are removed.
- **Confidence:** `tribal-knowledge-needed` — entity doesn't exist in code yet; this entry is written from the spec and must be re-confirmed once the feature ships.

### KPI *(arriving in v1 of the Metrics & KPIs spec)*
- **One-line identity:** A Metric wrapped with target + direction + RAG thresholds + trendline; leadership-facing.
- **What it is (detail):** New model. Has Metric FK (`on_delete=PROTECT`), target, direction (increase/decrease), green/amber thresholds, time grain (daily/weekly/monthly/quarterly/yearly), trend periods, metric-type tag (Input/Output/Outcome/Impact).
- **Consumes:** Metric (`reference` — required FK).
- **Consumed by:**
  - Dashboard (`compose` — KPI chart type in `DashboardComponentType`)
  - ReportSnapshot (2-hop via Dashboard — KPI chart data frozen into `frozen_chart_configs` at snapshot time)
  - Alert (`reference` — alerts can fire on RAG transitions; deferred to Alerts spec)
- **Platform-specific behaviors:**
  - Target is optional. If omitted, RAG is not shown �� KPI renders as trend only.
  - RAG thresholds are % of target, with red auto-computed.
  - Per-KPI time grain (team feedback) — not a page-level filter.
  - KPI deletion cleans up references from dashboard `components` JSON.
- **Change impact:** Target change recolors historical RAG — note on backdating. Threshold change affects Alert fire rate. KPI value/target changes appear live on dashboards and live share links, but NOT in already-captured ReportSnapshots (frozen).
- **Confidence:** `tribal-knowledge-needed` — entity arriving in v1; confirm shape after ship.

### Dashboard
- **One-line identity:** A user-composed canvas of Charts + text/heading blocks, with filters, optionally published for public viewing.
- **What it is (detail):** Has `DashboardType` (NATIVE or SUPERSET), `DashboardComponentType` enum (CHART / TEXT / HEADING / KPI), a grid layout (`layout_config`), a JSON `components` blob, and separate `DashboardFilter` rows. Supports **two independent sharing surfaces**: live public share (via `is_public` + `public_share_token`) and snapshot share (via ReportSnapshot, with its *own* token).
- **Consumes:** Chart (`compose`), KPI (`compose` — as KPI chart), filters (`compose`).
- **Consumed by:**
  - ReportSnapshot (`snapshot-of` — freezes layout + chart configs at snapshot time)
  - Live public share view (`embed` — same Dashboard rendered behind a share token)
  - Explore page — no, Explore is separate (does not embed Dashboards)
- **Platform-specific behaviors:**
  - **Component types are a fixed enum (CHART / TEXT / HEADING / KPI).** Adding a new type requires extending the enum and every render surface.
  - **Two sharing tokens exist:** Dashboard's `public_share_token` (live) and ReportSnapshot's `public_share_token` (frozen). Different URLs, different semantics.
  - `DashboardLock` provides editor-level concurrent-edit protection.
  - One dashboard per org can be marked `is_org_default` (landing page) — unique constraint enforced.
  - NATIVE vs SUPERSET dashboards are distinct; "Dashboard" in modern specs typically refers to NATIVE.
- **Change impact:**
  - Widget type additions need updates in: dashboard builder UI, live public-share renderer, ReportSnapshot render code (for new snapshots), Scheduled email renderer.
  - Layout changes flow live to existing public-share URLs; do NOT flow into already-captured ReportSnapshots.
- **Confidence:** `verified` (read `models/dashboard.py`)

### Explore
- **One-line identity:** Ad-hoc chart-building surface at `app/explore/`; users build throwaway charts/queries without saving.
- **What it is (detail):** Unclear whether it reuses the same MetricsSelector component as the dashboard chart builder. Assumed throwaway by name — no known persisted-artifact output.
- **Consumes:** Warehouse (`query-from`), Transform (`query-from`), Metric (`reference`, if picker is shared — *needs confirmation*).
- **Consumed by:** Nothing (terminal surface). Potentially "promote to saved Chart/Metric" but not confirmed.
- **Platform-specific behaviors:** Entirely unclear whether Explore shares the chart-builder's MetricsSelector component or has its own. This determines whether the v1 Metrics spec auto-lands in Explore or requires a separate extension.
- **Change impact:** If picker component is shared, auto-inherits Metric library changes. If not, changes must be duplicated.
- **Confidence:** `tribal-knowledge-needed` — **this is a blocker question for the Metrics v1 plan.** Ask Pratiksha whether Explore's chart builder reuses the dashboard chart builder's MetricsSelector.

---

## Output / Distribution Layer

### ReportSnapshot *(the entity called "Report" in product conversations)*
- **One-line identity:** An immutable snapshot of a Dashboard's **layout + chart configs**, rendered against **live data** queried through a date-range filter.
- **What it is (detail):**
  - Stored in `report_snapshot` table (model `ReportSnapshot`).
  - **Frozen at snapshot time:** `frozen_dashboard` JSON (layout + filters + components) and `frozen_chart_configs` JSON (full chart config keyed by chart_id). These survive deletion of the original Dashboard and Charts.
  - **Live at view time:** the data itself is queried each time the snapshot is viewed, filtered by the captured date range.
  - Only mutable field is `summary` (executive-summary text).
  - Has its own `public_share_token` distinct from Dashboard's.
  - `period_start` + `period_end` define the date lens through which data is queried.
- **Consumes:** Dashboard (`snapshot-of` — freezes dashboard config at snapshot time), Chart (`snapshot-of` — freezes chart configs), KPI (`snapshot-of` — freezes KPI chart data: value, target, RAG, trend), Warehouse (`query-from` — live data under a date filter).
- **Consumed by:** External stakeholders (terminal node inside Dalgo).
- **Platform-specific behaviors:**
  - **This is the most commonly misunderstood entity in Dalgo.** It is **not** "a Dashboard with data frozen in time" — the **data is live**; the **layout and chart configs** are frozen. Two separate behaviors.
  - **Reports inherit new Dashboard widget types only for snapshots taken after the widget is added.** Existing snapshots stay as they were.
  - **KPI chart support in ReportSnapshot is in scope for v1** (Milestone 4). Snapshot creation freezes KPI chart data (current value, target, RAG status, trend) into `frozen_chart_configs`. Snapshot renders show the frozen values, not live.
  - **Report's public share is independent of Dashboard's public share.** Sharing a Dashboard publicly does NOT auto-share its snapshots.
  - No direct path from Metric or KPI to Report except via Dashboard → Chart.
- **Change impact:**
  - Terminal. Historical Report snapshots are immutable (except `summary`).
  - New chart/widget types: must be wired into Report render code before they can appear in snapshots — otherwise snapshots taken today will fail-render tomorrow.
  - Warehouse schema changes: since data is live-queried, underlying schema renames break historical Report views even though the snapshot config is frozen.
- **Confidence:** `verified` (read `models/report.py`)

### Alert *(paired Alerts spec — parallel work)*
- **One-line identity:** A triggered notification fired when a Metric/KPI crosses a threshold, or a Pipeline / Data Quality check fails.
- **What it is (detail):** Defined in the parallel Alerts spec. Thresholds, firing conditions, and subscribers live on the Alert.
- **Consumes:** Metric (`reference`), KPI (`reference`), Pipeline (`trigger` on failure), Data Quality check (`trigger` on failure).
- **Consumed by:**
  - Notification (`trigger` — alert firing creates Notification records)
  - External channels — if Slack / email integrations are added (future)
- **Platform-specific behaviors:** Paired spec is active parallel work; behavior details pending Alerts team confirmation.
- **Change impact:** Metric formula change can flip historical "was alerting" state. Threshold change without history migration creates inconsistent history.
- **Confidence:** `tribal-knowledge-needed` — paired spec in progress; confirm shape with Alerts feature owner.

### Share link *(a mode of Dashboard or ReportSnapshot, not a standalone entity)*
- **One-line identity:** A public URL + access token that lets external viewers access a Dashboard (live) or a ReportSnapshot (frozen layout, live data under date filter).
- **What it is (detail):** Implemented as a `public_share_token` column on both Dashboard and ReportSnapshot models — not a separate entity. `is_public` boolean controls whether the token is active. Separate analytics counters (`public_access_count`, `last_public_accessed`).
- **Consumes:** Dashboard (`embed`, live) OR ReportSnapshot (`embed`, frozen layout + live data).
- **Consumed by:** External viewers (terminal).
- **Platform-specific behaviors:**
  - **Two independent share surfaces exist.** A Dashboard share and a Report share are different URLs with different data semantics.
  - Share tokens have no per-user ACL — anyone with the URL has access.
  - Disabling a share sets `public_disabled_at`; the token stops working.
- **Change impact:**
  - Any change to the Dashboard propagates live to its share URL (no cache invalidation needed — it's the same backend view).
  - Any change that produces a new widget type in Dashboards *will automatically render in existing live Dashboard share URLs* — this is the "leak" vector for features the spec intended to keep private.
  - New widget types in ReportSnapshot render require both new-snapshot render support AND re-rendering historical snapshots if back-compat is desired.
- **Confidence:** `verified` (read `models/dashboard.py` + `models/report.py`)

### Notification
- **One-line identity:** In-app notification records with optional email delivery, addressed to specific OrgUsers.
- **What it is (detail):**
  - Model `Notification` has `author`, `message`, `email_subject`, `scheduled_time`, `sent_time`, `urgent` flag.
  - Delivery fan-out handled by `NotificationRecipient` (FK to OrgUser + read_status + task_id).
  - **Decoupled from Alert** — no FK; Alerts or other systems *create* Notifications but there is no persistent link.
- **Consumes:** Alert (`trigger`), Pipeline (`trigger` on run outcome), Data Quality check (`trigger`), system events.
- **Consumed by:** OrgUser (terminal — in-app feed or email delivery).
- **Platform-specific behaviors:**
  - Notifications are the **delivery layer only** — they don't retain a link back to the thing that fired them.
  - `task_id` suggests Celery-driven scheduling for email send.
  - Per-user notification preferences likely live in `UserPreferences` (not verified).
- **Change impact:** New notification sources flood the feed if not categorized. No retroactive scoping — settings changes affect new notifications only.
- **Confidence:** `verified` (read `models/notifications.py`)

---

## Platform Layer

### Organization
- **One-line identity:** The multi-tenant boundary — every entity above is scoped to exactly one Org.
- **What it is (detail):** Org contains configuration, plan, users (OrgUsers), warehouse connection, preferences.
- **Consumes:** Plan, billing, warehouse config, user roster.
- **Consumed by:** Every other entity (all data is org-scoped).
- **Platform-specific behaviors:**
  - Warehouse choice (Postgres vs BigQuery) is per-org.
  - `org_supersets`, `org_wren`, `org_preferences` are auxiliary per-org config tables.
  - Org deletion must cascade carefully — data-privacy / donor-compliance requirement.
- **Change impact:** Org-level config changes cascade to every entity within that org.
- **Confidence:** `draft`

### OrgUser
- **One-line identity:** A user within an organization, with a role that gates what they can see and edit.
- **What it is (detail):** Roles include analyst, program lead, leadership, M&E coordinator (per Metrics spec personas). Role-based access control via `role_based_access` model.
- **Consumes:** Organization (`reference`), Role (`reference`).
- **Consumed by:**
  - Dashboard (ownership via `created_by` / `last_modified_by`)
  - Chart (ownership)
  - ReportSnapshot (ownership)
  - Notification (delivery recipient)
- **Platform-specific behaviors:**
  - Per-object ACLs are currently out of scope per the Metrics spec — `canEdit` is hardcoded `true` in some prototype code.
  - Removing a user orphans their owned entities unless ownership is transferred.
- **Change impact:** Role changes affect what a user sees across every surface.
- **Confidence:** `draft`

---

## Canonical traversal example — "Change Metric definition"

With edge labels, the traversal now reasons about propagation semantics, not just topology:

**1-hop from Metric:**
- Chart — `reference` → value changes cascade live on next render
- KPI — `reference` → value changes cascade live
- Alert — `reference` → may flip fire state

**2-hop (via Chart, KPI):**
- Dashboard — `compose` on Chart + `compose` on KPI chart → new Metric value appears in every dashboard that composed the affected Chart/KPI
- ReportSnapshot — `snapshot-of` Dashboard + `query-from` Warehouse → **frozen layout, live data**: historical snapshots render with the NEW Metric value, not the original (because data is live-queried). This is a non-obvious gotcha.
- Share link (Dashboard mode) — `embed` → live; inherits change
- Share link (ReportSnapshot mode) — `embed` → frozen layout, live data; inherits change

**De-duplicated Blast Radius:**

| Surface | Hop | Propagation via | Auto-inherited? |
|---------|-----|-----------------|------------------|
| Chart | 1 | `reference` | Yes (live) |
| KPI | 1 | `reference` | Yes (live) |
| Alert | 1 | `reference` | Yes — may change fire state |
| Dashboard | 2 | `compose` of Chart/KPI | Yes (live) |
| ReportSnapshot | 3 | `snapshot-of` Dashboard + live data | **Yes — historical snapshots will show the new value** |
| Share link (live) | 3 | `embed` Dashboard | Yes (live) |
| Share link (report) | 3 | `embed` ReportSnapshot | Yes (live data under frozen layout) |

The key insight the old map missed: **ReportSnapshot's live-data-under-frozen-layout behavior means changing a Metric's formula retroactively changes the numbers shown in historical reports**. That's a stakeholder-trust concern that deserves explicit call-out in any Metric-editing plan.

---

## Maintenance notes

### Roadmap by confidence

Update order for the next team review session:

1. Promote `tribal-knowledge-needed` entries — these are blockers for correct planning:
   - Explore (picker is NOT reused per Pratiksha — confirmed 2026-04-21; confirm any other MetricsSelector integrations)
   - Data Quality check (blocking vs non-blocking?)
   - Alert (paired spec shape)
   - Metric / KPI (promote to `verified` after v1 ships; Metric has two modes: simple + SQL, no filters, no tags)
2. Promote `draft` entries — read the actual models:
   - Source (`models/airbyte.py`, `ddpairbyte/`)
   - Warehouse (org config + adapter layer)
   - Transform (`models/dbt_workflow.py`, `ddpdbt/`)
   - Pipeline (`ddpprefect/`, `models/flow_runs.py`)
   - Organization, OrgUser
3. `verified` entries only need re-check on model changes:
   - Chart, Dashboard, ReportSnapshot, Share link (both modes), Notification

### What is intentionally NOT in this map

- Internal plumbing (DashboardLock, UserPreferences, CanvasLock) — not user-facing product surfaces.
- Transient concepts (pending invitations, temporary filters) — no persistent identity.
- Infrastructure (Redis, Postgres-for-app-state, S3) — belongs in architecture docs, not product impact analysis.
- Third-party UIs (Superset, Wren, Airbyte native UI) — consumed through Dalgo's own surfaces, mapped via the entities above.

If a change touches only the above, the map traversal is a no-op. But if the change *surfaces* into a new product entity, add it here before shipping.
