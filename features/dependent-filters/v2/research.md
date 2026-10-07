# Dependent Filters (Group Model) — v2 Research

**Date:** 2026-09-28
**Spec:** [features/dependent-filters/spec.md](../spec.md) — "v2 — supersedes parent-child"
**Purpose:** codebase findings specific to the *group* model. Where a finding from the old parent-child research (kept in a local stash, not committed) still holds unchanged, it's referenced, not repeated. See `docs /domain-map.md` for platform-wide entity relationships (not duplicated here).

---

## 1. What survives from the old parent-child build, unchanged

**The rule:** most of the backend query mechanics don't change — only the shape of *what* gets queried, not *how*.

**Example:** `AggQueryBuilder.where_clause()` (`ddpui/core/datainsights/query_builder.py`) still just appends any SQLAlchemy boolean condition, ANDed with everything else. The group model still needs "AND every other member's constraint together" — same mechanism, different source of constraints (every other group member instead of a filter's own parent list).

**Why it matters — carries over as-is:**
- The two backend code paths (`ddpui/api/filter_api.py::get_filter_preview` and `ddpui/api/public_api.py::_execute_filter_preview`, shared via `get_value_filter_options_with_fallback` in `ddpui/core/charts/charts_service.py`) still both need updating — same "don't miss one of the two surfaces" risk as before.
- `apply_chart_filters()` (`charts_service.py`) — the operator-based (`in`, `greater_than_equal`, etc.) query applier already built and tested for the parent-child model's numerical/datetime narrowing — is still the right tool, *if* numeric/date filters ever re-enter scope. For v2's categorical-only scope, only the `in` operator is actually needed.
- No new permission slug needed — same `@has_permission(["can_view_dashboards"])` + `has_access(ResourceType.DASHBOARD, AccessLevel.EDIT, ...)` gate on `create_filter`/`update_filter`.
- Test pattern precedent unchanged: `ddpui/tests/api_tests/test_dashboard_native_api.py`'s direct-call-with-`mock_request` style.
- Live public dashboard share is still auto-covered once the shared components (`unified-filters-panel.tsx`, `dashboard-filter-widgets.tsx`) are updated — confirmed via component reuse (only 4 usages of `UnifiedFiltersPanel` repo-wide: its own file, `dashboard-native-view.tsx`, `dashboard-builder-v2.tsx`, `responsive-filters-section.tsx`).

## 2. Cycle detection is no longer needed — a genuine simplification

**The rule:** the parent-child model needed a graph cycle-check (`_has_cycle` in `ddpui/services/dashboard_service.py`) because a filter could point at another filter, and that link could loop. The group model has no direction at all — membership is just "in the one group, or not" — so there's nothing that *can* loop.

**Example:** Old model: City → depends_on → [State, Country]; a cycle check had to walk that graph before saving. New model: a dashboard just has a list of member filter ids; adding State to the list can never create a cycle, because there's no edge to traverse.

**Why it matters:** `_has_cycle` and the graph-walk inside `_validate_filter_dependency` become dead code for this feature — they can be deleted, not adapted. This is less code than before, not more.

## 3. Data model — where "one dependent group per dashboard" should live

**The rule:** the old `depends_on_filter_ids` lived inside each `DashboardFilter.settings` JSON (no migration). For a *dashboard-level* group, the natural equivalent is one new field on `Dashboard` itself, not on each filter.

**Example:** `ddpui/models/dashboard.py`'s `Dashboard` model has no existing catch-all JSON config field (unlike `DashboardFilter`, which has `settings`). Adding `dependent_group_filter_ids = models.JSONField(default=list)` directly on `Dashboard` needs one small migration (next number: check the current highest under `ddpui/migrations/` at implementation time) — but it's a single new column, not a new table (confirmed with the user separately).

**Why it matters — the alternative and its cost:** storing a boolean flag per filter instead (`DashboardFilter.settings.in_dependent_group = true`) avoids touching `Dashboard` at all, but then "who's in the group" requires scanning every filter on the dashboard instead of reading one field. Given a dashboard's filter count is small (per the old research, "a handful, not thousands"), either works — this is a plan-level decision, not one research resolves. Recommend the `Dashboard`-level field: it matches how the group is actually scoped (per-dashboard, not per-filter) and makes "which table is the group anchored to" (see §5) a one-hop lookup instead of a scan.

## 4. Frontend — the "display-controls panel" the spec describes doesn't exist as a live UI element

**The rule:** `dashboard-builder-v2.tsx` has a "Dashboard Settings" popover with a "Filter Layout" toggle — but it's commented out (`{/* COMMENTED OUT: Dashboard Settings - not needed anymore */}`, ~line 2282). The actual, live filter-management UI (the "+ Add" button) is rendered inline inside the filters panel itself, via an `onAddFilter` prop passed into `UnifiedFiltersPanel` (two call sites, ~lines 2719 and 2756 of `dashboard-builder-v2.tsx`).

**Example:** there is no existing "beside Filters in the display-controls panel" location to slot a new "Dependent filters" section into, because that panel is dead code.

**Why it matters — resolved directly with the user, not left open:** the new "Dependent filters" entry point is a settings/gear icon placed immediately to the **left of the existing "+ Add" button**, inside `unified-filters-panel.tsx`'s edit-mode toolbar (same row as `onAddFilter`). Clicking it opens the group-membership checklist. This replaces the plan's need to guess UI placement.

## 5. Open question the spec doesn't resolve — which table is "the" table once the group has members

**The rule:** the spec's Setup mockup shows ineligible filters greyed out ("different table," "date, not supported") but never states what determines the reference table when the group is still empty.

**Example:** Before any filter is checked, every categorical filter on the dashboard is theoretically eligible — "different table" has nothing to compare against yet. The most natural rule: the table of the *first* filter checked becomes the group's anchor table; every filter after that greys out unless it matches.

**Why it matters:** this is **not** written in spec.md — flagged to the user directly, who agreed it's an assumption for the plan to state explicitly, not something to silently build as if decided. **Resolved — see plan.md §8:** the table of the first filter checked is the group's anchor table.

## 6. Frontend — per-filter modal changes from editable to read-only

**The rule:** `filter-config-modal.tsx` currently has no "Depends on" field at all in the shipped codebase (that was parent-child-only work, not yet merged to main `webapp_v2`). For v2, the modal needs a small **read-only** display — "Linked with: State, District, City" — sourced from the dashboard-level group field (§3), not an editable picker.

**Why it matters:** this is *less* modal work than the parent-child model needed (no sibling-filter-list prop, no cycle-aware eligibility filtering inside the modal, no Combobox multi-select) — the modal just needs to know "is this filter's id in the dashboard's group list, and if so, who else is."

## 7. Backend query shape — one call per member, or one combined call?

**The rule:** the old model had each child query its own narrowed options independently (one API call per filter, triggered by its own SWR key depending on its parents' values). The group model's "every member depends on every other member" means, in the worst case, changing one filter should refresh every *other* member in the group at once.

**Example:** a 4-member group (Country, State, District, City); changing State means Country, District, and City's option lists should all be recomputed.

**Why it matters — a real HLD decision, not yet made:** two options —
- **(a) Keep N independent calls**, one per member, same `/api/filters/preview/`-style endpoint, just with a different `parents`-equivalent payload (now "every other member's current value" instead of "my parent's value"). Simple, reuses the existing endpoint shape, but means N network round-trips every time any one filter changes.
- **(b) One combined endpoint** that takes the whole group's current selections and returns narrowed options for every member in one response. Fewer round-trips, but a new endpoint shape, and a bigger change to how `unified-filters-panel.tsx` currently fetches (each filter's own widget currently owns its own SWR call).

This directly feeds the spec's own flagged-open performance question ("cost grows with group size, caching is engineering's call") — needs deciding in the plan's HLD, not deferred to implementation. **Resolved — see plan.md §8:** option (a), N independent calls.

## 8. Dashboard duplication still needs a remap step

**The rule:** same class of bug as before — `duplicate_dashboard` (`ddpui/api/dashboard_native_api.py`) copies each filter and gets a new id; whatever holds the group membership list needs those ids remapped in the copy, exactly like `TestDuplicateDashboardTabs` already tests for filter ids embedded in `dashboard.tabs`.

**Example:** if group membership lives on `Dashboard.dependent_group_filter_ids` (§3), duplicating a dashboard must translate old filter ids in that list to the new copy's filter ids — same remap pattern already proven for `depends_on_filter_ids` in the parent-child build.

---

## Summary — net-new findings for the plan

1. Query mechanics (`AggQueryBuilder`, `apply_chart_filters`, the two backend endpoints) carry over unchanged in shape — only the constraint source changes.
2. Cycle detection is deleted, not adapted — the group model has no possible cycle.
3. Group membership should live as a new field on `Dashboard`, not scattered per-filter — needs one small migration, not a new table.
4. The "display-controls panel" in the spec doesn't exist in the live codebase — resolved directly: new gear icon left of "+ Add" inside `unified-filters-panel.tsx`.
5. What determines the group's anchor table when it's still empty — not stated in spec.md, flagged to the user. **Resolved (plan.md §8):** the table of the first filter checked.
6. The per-filter modal's dependent-filter UI gets *simpler* than the parent-child version (read-only display, no picker).
7. N independent narrowing calls vs. one combined group-narrowing endpoint — ties directly to the spec's own flagged performance question. **Resolved (plan.md §8):** N independent calls.
8. Dashboard duplication needs the same filter-id remap treatment, just for a new field.
