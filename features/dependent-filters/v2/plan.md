# Dependent Filters (Group Model) — v2 Implementation Plan

**Status:** All milestones done and browser-verified (2026-10-07) — 1, 3, 4, 5, and 6. Milestone 2 has no separate backend deliverable (see §7). Feature complete per this plan.
**Spec:** [features/dependent-filters/spec.md](../spec.md) — "v2 — supersedes parent-child"
**Research:** [research.md](./research.md)
**Services affected:** `DDP_backend` (Django + Ninja), `webapp_v2` (Next.js)

## 1. Overview

A dashboard has at most one unnamed "dependent group" of categorical (dropdown) filters, and every member narrows every other member, in every direction, at once. Picking a value in any member instantly narrows the others; if a pick makes another member's own selection impossible, that older selection is silently cleared.

**Example:** Priya groups Country, State, District, City. Picking District = Ernakulam narrows State to "Kerala" and Country to "India" — not just downward, both ways at once.

## 2. Blast Radius

`DashboardFilter` composes into `Dashboard`. Reusing the confirmed blast-radius findings from research.md rather than re-deriving them, since grouping doesn't change *which* downstream surfaces consume `Dashboard`/`DashboardFilter`.

| Surface | Hop distance | Why affected | Status | Notes |
|---------|--------------|--------------|--------|-------|
| Live public Dashboard share | 1 (`embed`) | Viewer can still pick/change filters on a public link | **In scope** | Same reasoning as v1: auto-covered once shared components (`unified-filters-panel.tsx`) are updated. |
| ReportSnapshot / public report share | 1 (`snapshot-of`) | Spec says narrowing behaves identically here | **In scope** | Backend's public preview routes need the same update as the internal one. |
| Scheduled Email Reports + PDF export | 1 (via `ReportSnapshot`) | Non-interactive freeze | **Out of scope** | Same reasoning as v1 — no filter panel involved in a frozen render. |
| Chart / KPI | 1 (`compose`) | Filters apply their final values to every tile | **Not affected** | Grouping only changes what a builder/viewer *sees* in the dropdown, not how a chosen value reaches a chart's query. |
| Alert (`standalone`) | 2 | Unrelated ad-hoc filter shape | **Not affected** | Same as v1 — Alert doesn't consume `Dashboard`/`DashboardFilter`. |
| Explore, Notification | — | N/A | **Not affected** | Terminal / unrelated surfaces, same as v1. |

## 3. High-Level Design (HLD)

**What changes, at a glance:**

```
Builder (edit mode)                         Viewer (view mode)
┌───────────────────────┐                  ┌──────────────────────┐
│ unified-filters-panel   │  gear icon      │ unified-filters-panel  │
│  [+Add] [⚙ Dependent]   │ ───────────────►│  picks District=Kerala │
└───────────────────────┘   opens checklist └──────────┬────────────┘
        │                                              │ every OTHER member's
        │ PUT .../dependent-group/                     │ SWR key now includes
        ▼                                              ▼ everyone else's value
┌──────────────────────────┐            ┌─────────────────────────────┐
│ dashboard_native_api.py    │           │ GET /api/filters/preview/     │
│  set_dependent_group        │          │ (+ 2 public variants)         │
│  validates: same table,     │          │  ANDs in every other member's │
│  categorical only            │         │  current value                │
└──────────────────────────┘            └─────────────────────────────┘
```

**Key design decisions:**

- **No cycle detection.** Membership is a flat list, not a graph — nothing to walk, nothing that can loop (research §2).
- **Group membership is stored per-filter.** `DashboardFilter.dependent_group_id` is a nullable integer; filters sharing the same value belong to the same group, `null` means ungrouped (research §3). `Dashboard.to_json()` computes the flat `dependent_group_filter_ids` list the frontend consumes by querying the dashboard's filters for a non-null `dependent_group_id` — the API shape stays a flat list of ids either way.
- **"Just-changed-wins" needs no extra bookkeeping.** Because the UI only ever processes one change at a time, and every *other* member recomputes from the full current selection set on every change, whichever member's own current pick becomes invalid *as a direct result of this change* gets cleared by an auto-drop check run symmetrically for every member. No "who changed most recently" tracking needed.
- **Narrowing query stays AND-combination, reusing `apply_chart_filters`.** For member X, the constraint list is "every other member's current value, as an `in` operator," sourced from everyone else in the group.
- **Query shape: N independent calls per change, not one combined endpoint (see Decisions §8).** Each member keeps its own `/preview/`-style call, including every other member's current value. Simpler, reuses the existing endpoint shape and frontend SWR pattern; the trade-off is more round-trips for a large group. Given Dalgo's dashboards have a handful of filters, not dozens, this is the pragmatic default — flagged as revisitable if real usage shows otherwise.

**External service integrations:** none new — stays within the existing warehouse-query path.

## 4. Low-Level Design (LLD)

### Data model

New field on `DashboardFilter` (`ddpui/models/dashboard.py`):

```python
dependent_group_id = models.BigIntegerField(null=True, blank=True)
```

One migration (adds a column, not a table). The group itself has no separate row or id-generation scheme — `dependent_group_id` is a fixed `1` whenever a dashboard has a group, since a dashboard holds at most one group in this version (see §8). `Dashboard.to_json()` computes the flat `dependent_group_filter_ids` list the frontend/API consume from this field, so the external contract is still "a list of filter ids."

**Example:** Dashboard 5's Country, State, District, and City filters (ids 12, 13, 14, 15) each have `dependent_group_id = 1`. Filter 16 (CF work type) has `dependent_group_id = null` — it stays independent regardless of its own settings.

### API design

- **`PUT /api/dashboards/{id}/dependent-group/`** (new) — body `{"filter_ids": [12, 13, 14, 15]}`, replaces the whole list (matches spec: "membership is the whole config"). Validates server-side: every id belongs to this dashboard, every filter is a categorical (`VALUE`-type) filter, and every filter shares the same `(schema_name, table_name)` — same checks the greyed-out checklist enforces client-side, re-checked server-side (client-side is UX only).
- **`GET /api/filters/preview/`** (no change needed) — its `constraints` param already accepts a generic `{column, operator, value}` list and ANDs it in. For a group member, the frontend builds this list itself (§7 Milestone 4) — the endpoint doesn't need to know "group" is a concept at all.
- Public routes (`public_api.py`) — same, no change needed; they already accept the same `constraints` shape.

### Backend logic

**The rule:** validation for the group-set endpoint belongs in `DashboardService`, matching the existing API → Core → Models layering.

```python
def set_dependent_group(dashboard_id, org, filter_ids: list[int]) -> list[int]:
    # every id belongs to this dashboard, is categorical (VALUE type),
    # and shares one (schema_name, table_name) — raises FilterValidationError otherwise.
    # Clears any existing group on this dashboard first, then sets dependent_group_id = 1
    # on the given filters (dissolving instead, i.e. returning [], if fewer than 2 ids).
```

**Narrowing itself needs no backend function.** Building the "every other member's current value" list is just relaying values the frontend already holds (the current selection of each filter, which lives only in the browser) paired with column names it already has from the loaded dashboard — there's no decision or lookup the backend needs to make that the frontend can't. That list gets built in `dashboard-filter-utils.ts` (§7 Milestone 4) and sent as the existing `constraints` param, unchanged from how it works today.

### Frontend components

- **`unified-filters-panel.tsx`** — new gear icon in the edit-mode toolbar, immediately left of the existing `onAddFilter` button (confirmed placement — research §4). Opens a new **`dependent-filters-config-modal.tsx`** (new file) — the checklist screen from the spec's mockup.
- **`dependent-filters-config-modal.tsx`** (new) — lists every filter on the dashboard; greys out non-categorical and different-table filters (same-table check anchored to whichever filter is checked first — see Decisions §8). Saves via the new `PUT .../dependent-group/` endpoint.
- **`filter-config-modal.tsx`** — removes any editable "Depends on" UI; adds a read-only line, "Linked with: State, District, City", computed by looking up the dashboard's group list.
- **`lib/dashboard-filter-utils.ts`** — new function (name TBD, e.g. `getGroupNarrowingInfo`) computing, for one member, every *other* group member's current value — just "everyone else in my group," no direction to resolve.
- **`dashboard-filter-widgets.tsx`** — `ValueFilterWidget`'s SWR key includes every other group member's current value; the auto-drop effect runs for every group member symmetrically.

### Integration points

Frontend → backend: same query-param pattern on the existing `/preview/` endpoints, extended with the group-set endpoint. Backend → warehouse: no new query infrastructure — `apply_chart_filters()` already handles this.

## 5. Security Review

- **Authentication & Authorization:** unchanged — same `@has_permission(["can_view_dashboards"])` + `has_access(ResourceType.DASHBOARD, AccessLevel.EDIT, ...)` gate on the new group-set endpoint.
- **Input validation:** the new `PUT .../dependent-group/` endpoint validates every filter id belongs to the requesting org's dashboard, is categorical, and shares one table — real server-side validation, not just the UI's greyed-out checklist.
- **Data access control:** unchanged — narrowing queries stay scoped to the requesting dashboard's own `org_warehouse`, same as today.
- **Injection risk:** none new — `apply_chart_filters()` already binds values as parameters, not raw SQL.
- **Sensitive data / external calls:** none new.

## 6. Testing Strategy

**Backend:**
- Unit: `set_dependent_group` rejects a different-table filter (done — accepting/replacing a valid set is a trivial assignment, not separately tested).
- Integration: dashboard duplication carries each filter's `dependent_group_id` into the copy unchanged (done).
- No new tests needed for narrowing itself — `get_filter_preview`/public routes' `constraints`-based narrowing is pre-existing and already covered.

**Frontend:**
- Unit: the new group-narrowing-info function returns the right "everyone else" set, symmetric regardless of which member is asked.
- Unit/RTL: auto-drop clears a now-invalid selection on *any* member; changing one member correctly narrows every other member's SWR key.
- Manual/E2E: create a 4-member group, verify narrowing works in every direction (not just "downward"), verify the read-only "Linked with" text in the per-filter modal, verify the greyed-out checklist behavior.

## 7. Milestones

#### Milestone 1: Backend data model + group validation — ✅ DONE (2026-09-29)
- **Deliverable:** a dashboard's dependent group (a flat list of filter ids) can be set via a new endpoint, with same-table + categorical-only validation.
- **Services:** DDP_backend
- **Key tasks:**
  - [x] `DashboardFilter.dependent_group_id` field + migration (`0189_dashboard_filter_dependent_group_id.py`)
  - [x] `DashboardService.set_dependent_group()` + validation
  - [x] New endpoint (`PUT /api/dashboards/{id}/dependent-group/`) + `SetDependentGroup`/`DependentGroupResponse` schemas
  - [x] `duplicate_dashboard` copies each filter's `dependent_group_id` straight to its counterpart in the new dashboard — safe without remapping, since every query reading it is already scoped by dashboard
  - [x] Delete the now-unused `_has_cycle` / `depends_on_filter_ids` cycle-check code (done in pre-execution cleanup pass)
- **Acceptance criteria:** valid same-table categorical sets save; a different-table or non-categorical id is rejected with a clear error; duplicating a dashboard with a group produces a correctly-relinked copy.
- **Verified:** 121 passed (`test_dashboard_service.py`, `test_dashboard_native_api.py`, `test_filter_api.py`, `test_public_report_api.py`), worktree `DDP_backend-dependent-filters`.
- **Bug found + fixed (2026-09-30):** `delete_filter()` never removed a deleted filter's id from `dependent_group_filter_ids`, leaving a dangling reference. Concretely: this didn't just show stale data -- it *blocked saving any new group* afterward, since `set_dependent_group`'s "every id must belong to this dashboard" check rejected the whole save because of the one dead id. Found via manual testing, confirmed against spec.md's edge case ("unlink or delete a member → the others widen; a group under 2 members dissolves"). Fixed: `delete_filter` now removes the deleted id from the group, and dissolves the group entirely (empty list) if fewer than 2 members remain. One test covers the removal behavior. This also covers part of Milestone 5's "Group-under-2-members dissolves correctly" — the delete-triggered case is done; the checklist-uncheck-triggered case is still open there.

#### Milestone 2: Backend narrowing query — ⏭️ NOT NEEDED (folded into Milestone 4, 2026-09-30)
- **Why:** the three preview endpoints already accept a generic `constraints` param and already narrow correctly against it (pre-existing, tested behavior, unrelated to this feature). A group member's narrowing constraints are just "every other member's current value" — data the frontend already holds — so building that list is Milestone 4's job (`getGroupNarrowingInfo`), not a new backend function. No backend code changes needed for this milestone.
- **Services:** none

#### Milestone 3: Frontend group config UI — ✅ DONE (2026-09-30)
- **Deliverable:** builder can create/edit the dashboard's one dependent group via the new gear-icon checklist.
- **Services:** webapp_v2
- **Key tasks:**
  - [x] Gear icon in `unified-filters-panel.tsx`, left of "+ Add" (both horizontal and vertical layouts, edit mode only, only shown once a dashboard has at least one filter)
  - [x] `dependent-filters-config-modal.tsx` (new file) — checklist, greys out non-categorical and different-table filters; anchor table = whichever filter is checked first; saves via `PUT .../dependent-group/`
  - [x] `filter-config-modal.tsx` — read-only "Linked with: ..." line added (no editable picker ever existed here to remove)
  - [x] `useDashboards.ts` — `setDependentGroup()` mutation fn + `Dashboard.dependent_group_filter_ids` type field
  - [x] `dashboard-builder-v2.tsx` — threads `dependentGroupFilterIds` (stable/live fallback, same pattern as `initialFilters`) into both panel layouts and the linked-names computation for the edit modal
- **Acceptance criteria:** checklist correctly greys out different-table/non-categorical filters; saving persists; per-filter modal shows the read-only linked list.
- **Verified:** 200/200 frontend tests passing; TS error count unchanged (7, all pre-existing baseline in `dashboard-builder-v2.tsx`, unrelated); manually browser-tested end to end by the user (2026-09-30) — checklist, greying, save, and the "Linked with" display all confirmed working.
- **Found + fixed during manual testing:** a "Maximum update depth exceeded" render loop, caused by `dependentGroupFilterIds` being recomputed as a fresh `[]` array on every render (both the `?? []` fallback in `dashboard-builder-v2.tsx` and the prop's own destructuring default in `unified-filters-panel.tsx`). Fixed by using a shared stable empty-array constant in both places.
- **Narrowing does not work yet, by design** — that's Milestone 4's job, not M3's. M3 only builds group membership config, not live narrowing.

#### Milestone 4: Frontend live mutual narrowing — ✅ DONE for all surfaces, browser-verified (2026-10-01)
- **Deliverable:** the full viewer-facing experience from the spec's "Behavior (view mode)" section — narrowing in every direction, symmetric auto-drop. Absorbs former Milestone 2's goal (narrowing actually working end to end) since building the `constraints` payload is frontend work.
- **Services:** webapp_v2
- **Key tasks:**
  - [x] `getGroupNarrowingInfo()` in `dashboard-filter-utils.ts` — for one member, returns every *other* group member's `{column, operator: "in", value}` (skips members without a value, excludes self); reuses the existing `filterValueToOperatorEntries` helper. One unit test covering self-exclusion + unset-exclusion + correct shape together.
  - [x] `ValueFilterWidget`'s SWR key includes every other group member's current value — computed once per filter in `unified-filters-panel.tsx` (`getGroupNarrowingInfo` + `JSON.stringify`), threaded down as a JSON-string prop through `SortableFilterItem` → `FilterElement` → `DashboardFilterWidget` → `ValueFilterWidget`, appended to the API URL as the existing `constraints` param.
  - [x] Auto-drop runs symmetrically for every member — re-added inside `ValueFilterWidget` itself (removed during the earlier parent-child cleanup), gated on "this filter is currently narrowed," not on any "child" designation.
- **Acceptance criteria:** picking any member narrows every other member; a pick that invalidates another member's selection clears it silently; verified in-browser on internal dashboard, live public share, and public report view.
- **Verified:** 201/201 frontend tests passing (1 new); 271/271 backend report tests passing (1 new); no new TS errors. Manually browser-tested end to end by the user: a 2-filter group and a 3-filter group (City/State/Name) with narrowing in every direction and auto-drop (2026-09-30); internal preview mode (2026-09-30); public dashboard view and report mode, both private and public (2026-10-01) — all confirmed working correctly.
- **Config-modal cache-invalidation gap — found during this milestone, fixed 2026-10-01:** `DependentFiltersConfigModal.handleSave()` now mutates `/api/dashboards/{id}/` after saving, matching the pattern already used by `handleFilterSave`/`handleFilterCreate`/`removeFilter` in `dashboard-builder-v2.tsx`. Previously only local state updated, leaving the dashboard-level cache stale until an unrelated action refreshed it.
- **Design note — a passed-as-string prop, not an object/array:** `groupNarrowingConstraintsJson` is threaded down already-JSON-encoded, not as a plain array. A fresh array/object literal would be a new reference every render (exactly the bug just fixed in M3 for `dependentGroupFilterIds`); a string compares by value, so passing it pre-stringified keeps `SortableFilterItem`'s `React.memo` and the SWR key both stable when the underlying data hasn't actually changed.
- **Bug found + fixed (2026-09-30): narrowing only worked in the builder.** `dependentGroupFilterIds` was only ever threaded through `dashboard-builder-v2.tsx` (edit mode) — `dashboard-native-view.tsx` and `responsive-filters-section.tsx` (actual view mode, public share, report view) never received it. Fixed in two steps, at the user's request, verified separately each time:
  - **Step 1 (2026-09-30): internal preview.** `dashboard-native-view.tsx` threads `dashboard.dependent_group_filter_ids` into both `<UnifiedFiltersPanel>` and `<ResponsiveFiltersSection>`, gated to internal mode only at first. Browser-verified.
  - **Step 2 (2026-09-30): public dashboard view.** Removed the `!isPublicMode` half of the gate — no backend change needed, since `PublicDashboardResponse` already inherits the field from `DashboardResponse` (confirmed before touching anything). Browser-verified 2026-10-01.
  - **Step 3 (2026-10-01): report mode (private + public) — real backend work, not just a gate.** Report snapshots freeze the dashboard's filters into a separate stored config at creation time (`ReportSnapshot.frozen_dashboard`) — they never carried `dependent_group_filter_ids` at all. Fixed:
    - `ReportService._freeze_dashboard()` (`report_service.py`) now includes `dependent_group_filter_ids` when freezing.
    - `FrozenDashboardConfig` (`report_schema.py`) needed the field declared explicitly — the freeze dict is validated through this schema before storage, which was silently dropping the key otherwise.
    - `get_snapshot_view_data` needed no change — it spreads the frozen dict straight into the response, which flows untouched to both the private-preview and public-report endpoints (`SnapshotViewResponse.dashboard_data` is an untyped `Dict[str, Any]`).
    - Old, already-created snapshots are unaffected — the key is just absent, same safe `?? []` fallback as everywhere else.
    - One new test: `test_view_data_includes_dependent_group_filter_ids` — creates a group, snapshots the dashboard, confirms the group survives into view data. Full report suite: 271 passed.
    - Frontend: removed the `!isReportMode` exclusion entirely.
    - Browser-verified by the user 2026-10-01 — both private and public report modes confirmed working.

#### Milestone 5: Polish + manual verification — ✅ DONE, browser-verified (2026-10-04)
- **Deliverable:** remaining edge cases from the spec, verified end to end.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [x] Column-removed (truly gone) shows broken in edit mode, rest of group keeps working — verified by the user with a real `DROP COLUMN`: broken member shows the edit-mode notice, sibling members gracefully fall back to unnarrowed (not erroring), confirmed by `test_narrowed_query_falls_back_to_full_list_on_error` (backend) and the existing "broken filter" widget test (frontend). No new code needed — already correctly handled by pre-existing infrastructure.
  - [x] Column-rename handling (pure column_name change, same table/type) — already works, no new code: `table_name`/`schema_name` can't change via the UI once a filter exists (`DatasetSelector` is `disabled={mode === 'edit'}`), and group membership is id-based, so a rename-remap never risks the group's invariants.
  - [x] **Resolved (2026-10-04), by the user's own call, not the spec:** editing a group member's *column* can silently flip its `filter_type` away from categorical (`filterType` auto-derives from the selected column's data type in `filter-config-modal.tsx`), which `set_dependent_group`'s categorical-only check would have rejected if attempted at group-creation time. Not mentioned anywhere in spec.md — this was an engineering gap the spec didn't anticipate. **Decision: allow the edit, auto-remove the filter from its group (dissolving the group too if it drops below 2 remaining), and notify the user why** — rather than rejecting the save outright, since the usual trigger is someone legitimately fixing a renamed column, and blocking the save would force an awkward "un-group it first, then edit" round trip. Mirrors the spec's own "silent auto-drop" principle for values, one level up at the membership level, except with an explicit toast instead of staying silent, since losing group membership is a bigger change than losing one value.
    - Backend: `DashboardService.update_filter()` now re-checks the same invariants `set_dependent_group()` enforces (categorical-only; same table) whenever the edited filter is a current group member, removing it (and dissolving below 2) if the edit breaks them. One test: a 3-member group, change one member's `filter_type`, confirm it's removed while the other two stay correctly grouped (the 2-member dissolve path was already covered by the analogous `delete_filter` test).
    - Frontend: no new backend response field needed — `handleFilterSave` already refetches the dashboard after any edit; it now compares the filter's dependent-group membership before vs. after that refetch, and shows a toast if it dropped out.
    - Browser-verified by the user 2026-10-04.
  - [x] 100-item cap + search respects group narrowing — already correct, no new code: the cap is proven unaffected by narrowing (`test_multi_constraint_narrowing_keeps_the_same_cap_as_unnarrowed`), and client-side search (`combobox.tsx`) only ever filters within `availableOptions` — the set already fetched *with* narrowing applied — so there's no path for search to reach a wider, unnarrowed list.
  - [x] **Fixed (2026-10-04):** confirmed explicitly in spec.md ("unlink or delete a member → the others widen; a group under 2 members dissolves") — not an engineering-only addition. The *delete* path already dissolved correctly; `set_dependent_group()` now does too: saving a single-member list dissolves the group to empty instead of persisting a meaningless 1-member "group." Backend-only — the checklist modal already passes the response straight through via `onSaved()`, so a dissolved result flows to the frontend with no extra code. One test: `test_saving_a_single_member_dissolves_the_group`. Full regression: 99 passed.
- **Acceptance criteria:** spec's Edge Cases section verified end to end.

#### Milestone 6: Linked filters visual grouping + polish — ✅ DONE, browser-verified (2026-10-07)
- **Deliverable:** group members render as a visually distinct, fixed "Linked filters" card at the top of the filter panel, across edit/view/public/report modes and both layouts; drag-reorder stays scoped within the linked group or within independent filters, never across; locked filters (report mode's frozen date filter) always render above the card.
- **Services:** webapp_v2, DDP_backend
- **Key tasks:**
  - [x] `unified-filters-panel.tsx` — filters partition into locked / grouped / ungrouped at render time; each partition gets its own `SortableContext`; `handleDragEnd` only reorders within one partition at a time.
  - [x] "Linked filters" card — bordered, gray header strip with a filter-count badge, no edit icon, rendered first and not itself draggable; present in both horizontal and vertical layouts, across edit, view, public, and report modes.
  - [x] `dependent-filters-config-modal.tsx` — titled "Linked filters"; dialog scrolls independently (`max-h-[90vh]`) on top of the filter list's own internal scroll region; Save stays disabled unless the selection actually differs from what's saved; success toast reads "saved" (neutral wording, covers create/update/clear alike).
  - [x] Chart empty-state message, consistent across Table, Pivot Table, and chart detail views: "No data for the selected filters" / "Try removing a filter or choosing different values."
  - [x] `datetime-filter-widget.tsx` — clearing a date filter via the shared clear-filter icon now resets the calendar's own displayed start/end dates, not just the applied value.
  - [x] `ddpui/api/filter_api.py` — `FilterNarrowingConstraint` rejects a missing `value` for value-dependent operators (`in`, `equals`, range comparisons, etc.), while still allowing valueless operators (`is_null`, `is_not_null`).
  - [x] `ddpui/core/charts/charts_service.py` — the narrowed-query fallback's warning log records only the affected column names and exception type, not raw constraint values or the exception message.
- **Acceptance criteria:** linked filters visually group and stay pinned at top in every mode/layout; dragging never crosses between linked and independent filters; the config modal never shows a false "saved" toast for a no-op save; chart empty states read clearly when filters narrow to zero rows; date filters have no max-date restriction (see §8).
- **Verified:** 233/233 frontend test suites passing; 49/49 relevant backend filter-API tests passing; no new TS errors.

## 8. Decisions confirmed (2026-09-29)

- **Anchor table when the group is empty:** the table of the first filter checked becomes the group's table; every filter after that greys out unless it matches. Not stated in spec.md — this is engineering's call, now settled.
- **Narrowing calls: N independent calls, not one combined endpoint.** Each affected member keeps its own `/preview/`-style call (research §7, HLD §3) — reuses the existing per-widget SWR pattern, fires in parallel, and the real bottleneck (the warehouse query itself) costs the same either way. Revisit only if a real dashboard's group size makes this noticeably slow in practice.
- **Column-rename: ship the "remap prompt" fallback only for v1.** The spec's stronger "re-binds via warehouse mapping" promise needs infrastructure this codebase doesn't have. Automatic detection is separate, later work if the team wants it.
- **Numeric/datetime filters are fully out of scope for v2**, including as drivers — a deliberate, confirmed trade-off.
- **Date filters have no max-date restriction (2026-10-07).** Future dates stay selectable in both the Start and End pickers — the underlying warehouse data can legitimately include future-dated rows (planned/scheduled/forecast entries), so capping at "today" isn't a safe default.

## 9. Remaining Risk

- **Migration path for any pre-existing `depends_on_filter_ids` production data**, from before this model existed. If no dashboard has real data in that field yet, this is a non-issue; if any does, decide whether to write a one-time data migration or accept that those dashboards silently lose their old links. Still open — no production-data check has been confirmed done.

---

**Status:** feature complete — all 6 milestones done and browser-verified. No further execution pending against this plan.
