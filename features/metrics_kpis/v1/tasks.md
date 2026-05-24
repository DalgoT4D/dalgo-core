# Metrics & KPIs v1 — Task List

**Last audited:** 2026-05-22
**Sources:** spec.md, plan.md, design.md, FIGMA.md, **Figma v2 designs** vs code in `DDP_backend_metrics` + `webapp_v2`
**Figma file:** `v8BYFkebTGQNuiRrCXWssa` → section "Metrics & KPI - V2" (node `11914:1422`)

## Figma v2 Design Notes (source of truth for UI)

These override design.md where they conflict:

**Navigation:**
- "Impact" is the top-level nav item for the KPI page (icon: target), NOT "KPIs"
- "Metrics" lives under the "Data" section (after Quality)

**Metrics Library table columns (exact order):**
Name | Mode | Data Source | Expression | Used By | Last Updated | Actions
- NO "Current Value" column (removed from Figma v2 — was in design.md)
- "Expression" not "Definition"

**Mode badges:** "Simple" and "Calculated" (NOT "SQL")

**Metrics form dialog (Figma labels):**
- Title: "Create Metric" / "Edit Metric"
- Mode toggle: "Simple" / "Calculated" (two-segment)
- Fields: Name *, Definition (description), Datasource *, Function * + Column * (Simple), Expression * (Calculated)
- Calculated validation states: "running expression" (loading), "Expression valid ✓" (success), "Syntax error. View Log >" (error)
- Edit blast radius: "NOTE: Saving will affect usage. This change cannot be reversed" + consumer count "2 Charts, 1 KPI, 2 Alerts"
- Edit no blast radius: same dialog, no warning

**Delete metric:**
- No consumers: "Are you sure you want to delete Metric [name]? This change cannot be undone."
- With consumers: "Cannot Delete Metric" — "[name] is in use by Charts and KPI. Remove these dependencies before deleting" + consumer count "NOTE: Change will affect: 2 Charts, 1 KPI, 3 Alerts"

**KPI page:**
- Title: "KPI", subtitle: "Track business objectives with measurable KPIs linked to your metrics"
- Filters: Search, Program, Type, Status
- Card: name, program tag, RAG badge, ⋮ menu, current value (large), "Target: X", sparkline with X-axis (Q1/Q2/Q3/Q4 or Jan/Apr/Jul/Oct), target line, period-over-period change "↓ +2.1%", "Updated 1 day ago" / "Data as of [date]"
- Card action menu: Edit KPI, Delete, Create Alert

**RAG labels (Figma v2):** "On Track", "Needs Attention" (NOT "At Risk"), "Off Track"

**Create KPI wizard (Figma v2 — 3 steps, not 4):**
- Step 1: "Select metric" — searchable list from Metrics Library + "Create a new metric" link
- Step 2: "KPI Target & Direction" — Name this KPI *, Target Value *, Direction * ("Higher is better")
- Step 3: Combined step — "Target & RAG Status" (On Track >= 100%, Needs Attention 90%, Off Track < 80%) + "Time Configuration" (Time Column, Time Grain: Monthly) + KPI Type (Input/Output/Outcome/Impact) + Program Name
- Buttons: CANCEL / Continue (steps 1-2), CANCEL / Create KPI (step 3)

**MetricsSelector in Charts (Figma v2):**
- Tabs: "Simple" / "Calculated" (NOT "Saved Metrics" / "Ad-hoc")
- Simple tab: function dropdown + Column dropdown + "Metric name *" + "SAVE METRIC" button
- Calculated tab: Expression textarea + "Name metric *" + "SAVE METRIC" button
- Saved metric display: pill with name + expression + close button + "ADD ANOTHER METRIC"

---

# Milestone 1 — Metrics Library + Create/Edit Metric

## Backend
- [x] Metric + KPI models, migration, permissions, seed data
- [x] Metric schemas, service, API (CRUD + preview + consumers)
- [x] Metric validation: exactly one of (column+aggregation) or column_expression
- [x] Validation query against warehouse on save
- [x] Renamed `validate_metric_definition` → `validate_metric_payload` (accepts `MetricCreate` schema)
- [x] Renamed `validate_metric_against_warehouse` → `validate_metric_query` (accepts `MetricCreate` schema)
- [x] Added `POST /api/metrics/validate/` endpoint — validates payload + runs warehouse query without saving
- [x] Added `MetricValidateResponse` schema (`{valid, error?}`)
- [x] Added SQL statement blocklist via `sqlparse` — rejects SELECT, INSERT, DELETE, DROP, etc. in expressions
- [x] Tests passing (48/48)

## Frontend — Core
- [x] Types (`types/metrics.ts`), hooks (`useMetrics.ts`)
- [x] Metrics library page (`/metrics`) with table view
- [x] Metric form dialog (create/edit with Simple + Expression modes)
- [x] Navigation: Metrics under Data section

## Frontend — Design Alignment (from Figma v2)

### Metrics Library table
- [x] Add "Mode" column with badge: **Simple** (green) / **Calculated** (grey)
- [x] Rename "Definition" column → **"Expression"**
- [x] Add **"Used By"** column — lazy-loaded per metric, clickable with hover popover listing consumers
- [x] Rename "Last Modified" → **"Last Updated"**
- [x] Add **"Actions"** column header label
- [x] Sort icons on Name, Data Source, Last Updated headers
- [x] Filter icon on Name header
- [x] Row action menu: **Edit Metric**, **Create KPI**, **Delete**
- [x] Subtitle: "Define reusable metric definitions that power your KPIs & Charts"
- [x] Empty state: "No metrics defined yet" + "Create your first metric..."
- [x] Font sizes match charts page (`text-lg` name, `text-base` data, `py-4` padding)

### Metric Form Dialog
- [x] Mode tabs: **"Simple"** / **"Calculated"** with green (primary) active state
- [x] Labels: **"Function *"**, **"Column *"**, **"Definition"**, **"Datasource *"**, **"Expression *"**
- [x] Calculated validation: Create Metric validates first → "running expression" → "Expression valid ✓" or error (red icon, grey text)
- [x] Info icon tooltip on Expression label: "Write a SQL expression that returns a single numeric value"
- [x] Edit blast radius warning at bottom: amber box with "NOTE: Saving will affect usage..." + clickable consumer links
- [x] Consistent tab content height (`min-h-[100px]`)
- [x] Save disabled during validation; save blocked until expression validated for Calculated mode

### Delete Dialog
- [x] No consumers: "Delete Metric" — "Are you sure you want to delete Metric **[name]**? This change cannot be undone." + CANCEL / DELETE
- [x] With consumers: "Cannot Delete Metric" — bold name + "Remove these dependencies" + amber box with clickable consumer links + CANCEL only
- [x] Buttons right-aligned via AlertDialogFooter

### Reusable Components
- [x] `ConsumerLinks` component — shows "2 Charts, 1 KPI" with hover popovers listing clickable items (open in new tab)
- [x] `variant="default"` (green links for table) vs `variant="inherit"` (amber links inside note boxes)
- [x] Used in: table Used By column, delete dialog, edit dialog

### Frontend hooks/types
- [x] `validateMetric()` hook added to `useMetrics.ts`
- [x] `MetricMode`, `MetricPreviewDefinitionRequest` types added
- [x] `AGGREGATION_OPTIONS` labels updated (Count, Sum, Avg, Min, Max, Count Distinct)

### Backend
- [x] Renamed `MetricCreate`/`MetricUpdate` → unified `MetricPayload` (backend + frontend)
- [x] `update_metric` accepts `MetricPayload` directly, auto-clears other mode's fields on switch
- [x] Error message: "Invalid expression: ..." (was misleading "Metric definition is invalid")

### Tests
- [x] Backend: 60/60 passing (validate endpoint + sqlparse blocklist tests added)
- [x] Frontend: zero type errors in our files, zero new test failures (4 pre-existing failures in unrelated files)

### Refactors
- [x] Metric form refactored to `react-hook-form` (register, Controller, per-field errors, handleSubmit)

---

# Milestone 2 — KPI Page + Create/Edit KPI

## Backend
- [x] KPI schemas, service, API (CRUD)
- [x] `compute_kpi_data()` — common function for live API + reports
- [x] `compute_rag_status()` — direction-aware RAG pure function
- [x] Number chart (no time dimension) vs line chart (with time dimension)
- [x] `data_last_date` — MAX(time_dimension_column) returned in KPI data response
- [x] KPI search matches both name and program_tags (`__icontains`)
- [x] Chart config: clean blue line, no area fill, dashed grey target series, no Y-axis, X-axis labels only
- [x] Removed `trend_periods` from model, schemas, service, tests
- [x] Tests passing

## Frontend — Core
- [x] KPI page (`/kpis`) with card grid, ECharts, value/target, filters
- [x] KPI form: 3-step progressive reveal, react-hook-form
- [x] "Create KPI" from metrics library

## Frontend — Design Alignment (from Figma v2)


### KPI Page
- [x] Page title: **"KPI"**, subtitle: **"Track business objectives with measurable KPIs linked to your metrics"**
- [x] Outer wrapper card (border rounded-lg) wrapping filters + KPI cards, scrollable inside
- [x] Filters inside content area: Search + Type + Status dropdowns
- [x] Removed Program text filter (search covers it via backend)
- [x] Status filter: client-side, cards hide when RAG doesn't match (proper fix in M5 with summary endpoint)
- [x] Card redesign per Figma:
  - Header section (border-bottom): name + program tags + RAG badge with dot + ⋮ menu
  - Value section: text-4xl bold value, "Target: X" below, "↑ +8.3% from last month" direction-aware
  - Chart section: clean ECharts sparkline (h-32)
  - Footer: inset divider + "Data as of [date]" from MAX(time_dimension_column)
- [x] RAG badge labels: **"On Track"**, **"Needs Attention"**, **"Off Track"** with colored dots
- [x] Card action menu: **Edit KPI**, **Delete**
- [ ] Card action menu: **Create Alert** (deferred — alerts feature)
- [x] Period-over-period change computed from last 2 trend periods, direction-aware coloring

### Create KPI Wizard (3-step progressive reveal)
- [x] Step 1: "Select metric *" — searchable list with name, schema.table, description, Simple/Calculated badge, green left-border selection
- [x] Step 2: reveals KPI Target & Direction — Name *, Target Value *, Direction * ("Higher is better"/"Lower is better")
- [x] Step 3: reveals RAG thresholds (On Track/Needs Attention/Off Track with concrete values) + Time Configuration (Time Column *, Time Grain *) + KPI Type (Input/Output/Outcome/Impact with icons) + Program Name
- [x] Progressive reveal: each step adds sections below, all previous sections stay editable
- [x] Metric selector in steps 2-3: Combobox with search, shows name + schema.table
- [x] Buttons: CANCEL / Continue (steps 1-2), CANCEL / Create KPI (step 3)
- [x] Direction labels: "Higher is better" / "Lower is better"
- [x] "CREATE A NEW METRIC" button (green border) opens `/metrics?create=true` in new tab (auto-opens create dialog)
- [x] Metrics list refetched when KPI form opens (picks up newly created metrics)
- [x] Time Column and Time Grain marked as required with validation
- [x] KPI Type buttons: horizontal with icons (Download/Upload/Target/Hammer), uppercase, primary color on selected
- [x] Refactored to `react-hook-form` (register, Controller, per-field errors, handleSubmit)
- [x] Removed `trend_periods` field from model, schemas, service, tests, frontend

---

# Milestone 3 — KPI Dashboard Widget

## Backend
- [x] `KPI = "kpi"` in `DashboardComponentType` + `CHART_SIZE_CONSTRAINTS`

## Frontend — Core
- [x] KPI chart element for dashboard
- [x] Chart selector modal with Charts + KPIs tabs
- [x] Dashboard builder: KPI add/render/remove with action buttons
- [x] View mode + public share rendering

## Frontend — Design Alignment
- [x] Shared `KPICard` component (`components/kpis/kpi-card.tsx`) used by both listing page and dashboard widget
- [x] Same layout: header + RAG badge with dot + value + target + PoP + chart + "Data as of" footer
- [x] `borderless` prop for dashboard (avoids double border)
- [x] `ResizeObserver` on chart container for dashboard grid resizing
- [x] Download as PNG (html2canvas-pro) + Export Data as CSV (Period, Period Date, Value)
- [x] Listing page: download options in ⋮ menu alongside Edit/Delete (`downloadInMenu` prop, `menuItems` prop)
- [x] Dashboard widget: download on hover toolbar (`showDownload` prop)
- [x] Enriched preview cards in selector modal: name + RAG badge + metric name + target + type badge

---

# Milestone 4 — ReportSnapshot KPI Widget Support

## Backend
- [x] Migration `0159`: Rename `snapshot_chart_id` → `target_id`, `chart_id` → `target_id`
- [x] `KPI = "kpi"` in `CommentTargetType`
- [x] Refactor comment_service + mention_service for generic target_id
- [x] `FrozenKpiConfig` + `_freeze_chart_configs()` freezes KPIs from `dashboard.tabs`
- [x] `compute_kpi_data()` for live + report, `get_report_kpi_data()`
- [x] API: `GET /api/reports/{snapshot_id}/kpis/{kpi_id}/data/`
- [x] `_freeze_chart_configs` updated: iterates `dashboard.tabs[].components` (not flat `dashboard.components`)
- [x] Tests: 14 new KPI freezing tests (trend data, RAG status, no warehouse, error handling, expression metrics, get_report_kpi_data, KPI survives deletion)
- [x] Test fixtures updated: `sample_dashboard` uses tabs structure (all dashboards use tabs)
- [x] All tests passing (72 report service tests)

## Frontend
- [x] Comment types/hooks use `target_id` with `'kpi'` support
- [x] `kpi-chart-element.tsx`: snapshotId + comment props
- [x] `dashboard-native-view.tsx`: passes snapshot + comment state to KPI element
- [x] Fixed duplicate comment icon on non-KPI charts in report view (removed redundant CommentPopover)
- [x] Frontend builds successfully

---

# Milestone 5 — KPI Service Refactor + Detail Drawer + Filters

## Backend
- [x] Implemented `_compute_trend(kpi_response, org_warehouse, date_filter, limit)` — single source of truth for trend queries
- [x] Implemented `kpi_to_response(kpi)` — model-to-schema converter in service layer
- [x] Refactored `compute_kpi_data` to accept `KPIResponse` schema (not raw dict)
- [x] Current value derived from last trend period (removed separate query)
- [x] `data_last_date` derived from last trend period label (removed MAX query)
- [x] Removed gauge echarts fallback (empty config when no trend)
- [x] Added `GET /api/kpis/summary/` endpoint (wired existing service method)
- [x] Added `time_grain`, `date_from`, `date_to` query params to `GET /api/kpis/{id}/data/`
- [x] `time_grain` override replaces KPI's default; `date_from`/`date_to` filter trend range
- [x] Removed limit on trend periods (was hardcoded to 12)
- [x] Verified: migrations exist (0161), permissions in seed data
- [x] 98/98 tests passing

## Frontend — Wire Orphaned Components
- [x] Deleted orphaned `kpi-card.tsx`
- [x] Wired `KPIDetailDrawer` into KPI page — card name click opens drawer, menu opens edit form
- [x] `useKPIData` hook updated to accept `timeGrain`, `dateFrom`, `dateTo` options

## Frontend — KPI Detail Drawer (Figma v2)
- [x] 600px width, sticky header with name + program tags + schema.table (green) + edit + close
- [x] Value section: large value, Target, PoP change (direction-aware), time grain dropdown, RAG badge
- [x] Duration picker (reusable `components/ui/duration-picker.tsx`): single calendar, from/to selection, OK to apply
- [x] Duration picker + time grain dropdown side by side, above chart
- [x] Full trend chart (h-56) with clean blue line + dashed target
- [x] Notes section placeholder (ready for M7 annotations)

## Frontend — KPI Form
- [x] Simplified to 2-step progressive reveal (was 3)
- [x] Metric selector: Combobox with name + schema.table + description + Simple/Calculated badge
- [x] Combobox `footer` prop added — "CREATE A NEW METRIC" always visible at bottom of dropdown
- [x] Step 1: metric + name + target + direction
- [x] Step 2: RAG + time config + program + KPI type

## Frontend — MetricsSelector
- [x] Full form redesign: "Defined Metrics" dropdown (pick from library) + Simple/Calculated tabs + Name + Display Name + Save/Add buttons
- [x] Tabs: "Simple" / "Calculated" (default Shadcn styling, no green)
- [x] Simple tab: Function + Column pickers (same as before)
- [x] Calculated tab: Expression textarea with validation via `POST /api/metrics/validate/` before adding
- [x] Validation states: "Validating expression..." spinner, error below textarea
- [x] "Name Metric *" required for both add and save
- [x] "SAVE METRIC" button: saves to library + adds to chart
- [x] "ADD ANOTHER METRIC" button: adds to chart without saving
- [x] Metric pills: name + expression/aggregation summary + Save icon (unsaved only) + X (remove)
- [x] Save icon on pills: saves inline metric to library, shows "Saved" badge after
- [x] Expression metrics: `aggregation: null`, `column_expression` set — backend handles correctly
- [x] Backend: `ChartMetric.aggregation` nullable, chart_validator skips expression metrics, `.lower()` guards on all aggregation checks in charts_service.py
- [x] Frontend: `ChartMetric.aggregation` optional in type, `isChartDataReady` accepts expression metrics


---

# Milestone 7 — KPI Annotations (AnnotationEntry)

## Backend
- [x] `AnnotationEntry` model: kpi FK, `note_type` (beneficiary_quote/note), `period_key`, `period_date` (DateField), `content`, `snapshot_value`, `snapshot_pop_change`, `created_by`
- [x] Migration `0162_annotation_entry.py`
- [x] Schemas: `AnnotationEntryCreate`, `AnnotationEntryUpdate`, `AnnotationEntryResponse`
- [x] Service: `_entry_to_response`, `list_annotations`, `create_annotation`, `update_annotation`, `delete_annotation`
- [x] API: GET/POST `/{kpi_id}/notes/`, PUT/DELETE `/{kpi_id}/notes/{entry_id}/`
- [x] Snapshot values (value + PoP change) sent by frontend from loaded trend data (no extra backend query)
- [x] `period_date` stored as raw date for ordering, `period_key` for display + matching
- [x] 98/98 tests passing

## Frontend
- [x] Types: `AnnotationEntry`, `AnnotationEntryCreate`, `AnnotationEntryUpdate`, `NoteType`
- [x] Hooks: `useAnnotations`, `createAnnotation`, `updateAnnotation`, `deleteAnnotation`
- [x] `period_date` added to trend data response for annotation linking
- [x] Notes section in KPI drawer per Figma v2:
  - "+ ADD NOTE" button → inline form: Time Period dropdown + Note type toggle (Beneficiary quote / Others) + Note textarea + CANCEL/SAVE
  - Notes list: period header (bold) + author email + time ago, card with snapshot value + PoP + type badge + ⋮ menu + content
  - Badge styles: "Beneficiary quote" (amber bg, green text) / "Note" (red bg, red text)
  - ⋮ menu inside card: Edit + Delete
  - Edit: full inline form (period, type, content all editable), re-snapshots if period changes
  - Delete: via ⋮ menu
- [x] Notes use KPI's default periods (captured from first fetch), not affected by drawer's time grain/date filter changes
- [x] Duplicate prevention: periods with existing notes filtered from add dropdown
- [x] KPI edit form: metric, time column, time grain disabled when annotations exist (amber warning shown)
- [x] Drawer resets time grain + date filters on close

---

# Milestone 8 — UX Polish + Security

## Backend
- [x] SQL expression blocklist via `sqlparse` in `validate_metric_payload()` (moved to M1)
- [x] `time_grain`, `date_from`, `date_to` query params on `GET /api/kpis/{id}/data/` (moved to M5)

## Frontend
- [x] Time grain dropdown in KPI drawer — overrides KPI default, session-only (moved to M5)
- [x] Duration picker (`components/ui/duration-picker.tsx`) — reusable, single calendar, from/to, OK to apply (moved to M5)
- [x] Annotations NOT filtered by time grain/date window — always use default periods

---

# Progress Summary

| Milestone | Backend | Frontend | Status |
|-----------|---------|----------|--------|
| 1. Metrics Library | Done | Done | **Complete** |
| 2. KPI Page | Done | Done | **Complete** |
| 3. Dashboard Widget | Done (filters via `apply_dashboard_filters`) | Done (shared KPICard + download + filters) | **Complete** |
| 4. ReportSnapshot | Done (72 tests, tabs-based freezing, KPI survival, filters) | Done (duplicate comment fix, filters) | **Complete** |
| 5. Service Refactor + Drawer + Filters + MetricsSelector | Done | Done | **Complete** |
| 6. ~~Metric Tags + Detail~~ | ~~Removed~~ | ~~Removed~~ | **Removed** |
| 7. Annotations | Done | Done | **Complete** |
| 8. Polish + Security | Done (moved to M1 + M5) | Done (moved to M5) | **Complete** |

## v1 Status: COMPLETE

All milestones delivered. The only deferred item is "Create Alert" in the KPI card menu, which depends on the alerts feature (separate workstream).

### Final fixes (post-milestone)
- [x] Dashboard & report filters integration with KPI widgets — all filter types (value, numerical, datetime) work identically to charts. Backend resolves via `DashboardService.resolve_dashboard_filters_for_chart` with `column_exists` check, applies via `apply_dashboard_filters`. Both live dashboard and report snapshot paths support filters.
- [x] `CommentPopover.targetType` accepts `'kpi'` (was only `'summary' | 'chart'`)
- [x] Removed duplicate comment icon on non-KPI charts in report view
- [x] Test fixtures updated: all dashboards use tabs structure (matches production)
- [x] `_freeze_chart_configs` iterates `dashboard.tabs[].components` (not flat `dashboard.components`)

### Test coverage
- 114+ backend tests passing (72 report service + 42 KPI service)
- Frontend: zero new TS errors from our changes
