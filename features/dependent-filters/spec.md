# Dependent (Cascading) Dashboard Filters

**Owner:** Product (Abhishek) · **Date:** 2026-08-05 · **Status:** Draft · **Area:** Dashboards → Filters

**In one line.** Let a dashboard builder link filters so a viewer's choice in one narrows the options in the next — pick Kerala in State and the District filter shows only Kerala's districts, chaining Country → State → District → Block → School.

---

## Problem

Dashboard filters are independent today. A State filter and a District filter each always show every value, so filtering to Kerala still lists all ~700 districts. Viewers scroll through irrelevant options and can pick impossible combinations (Kerala + a Gujarat district).

## Key decisions (read this first)

- **Per-dashboard.** Relationships are set in the dashboard's filter config (edit mode) — not inferred from the data, not defined org-wide.
- **Same table.** Parent and child must be columns on the same warehouse table. Cross-table links (via joins) are out for v1.
- **Child = value filter; parent = any filter.** The filter being narrowed is always a dropdown (value) filter. The parent narrowing it can be a value, date, or numerical filter — so a date range with no data hides the child values that fall outside it.
- **Live options, Apply gates charts.** Picking a parent narrows the child dropdowns instantly. Charts only re-render on Apply (unchanged from today).
- **Auto-drop invalid selections.** If a parent change makes a child selection impossible (District = Pune, then State → Kerala), Pune is cleared silently and the child shows Kerala's districts. No note, no block, no error.
- **Cross-tab unchanged.** Filters already apply to every tile on every tab; that stays.
- **No cycles.** A can't depend on B if B already depends on A.

Everything below is the detail behind these.

## The model (edit mode)

A value filter gets a **"Depends on"** dropdown in its config. It lists eligible parents — any value / date / numerical filter **on the same table**, minus any that would create a cycle. Empty = independent filter (today's behavior).

- One parent per filter. A parent can have many children, and a child can itself be a parent — so chains form (Country → State → District).
- Children render below their parent in the panel, so narrowing reads top-to-bottom.
- Filters on another table, or ones that would close a loop, don't appear in the picker.

## Behavior (view mode)

**On load.** Nothing is pre-selected (filters have no defaults today), so every filter shows its full list. Narrowing starts on the viewer's first parent pick.

**Pick or change a parent.**

- Child dropdowns re-fetch their valid options for the current selection. Multi-select parents merge results (India + USA → Indian and American states).
- Child selections that are now invalid are cleared silently — the child just shows the newly valid options.
- Narrowing flows down the whole chain: change Country → State re-narrows → District re-narrows.

**Apply.** Commits the current selections to all tiles on all tabs. Only still-valid selections apply. A child left empty applies nothing — its options were narrowed, but it adds no filter of its own.

**Clear a parent.** Its children re-open to full lists; selections that only existed under it are dropped. The dashboard is not forced empty.

**Deselect one value in a multi-select parent.** Re-narrows to the remaining values and drops selections that no longer fit. Removing the last value = "no parent selected" → child re-opens fully.

**Child filter states:** full-list · narrowed · empty ("no values for current selection") · broken (edit mode only).

## Edge cases

- **Parent value has no children** → child shows an empty state, not a spinner or error.
- **Same child value under two parents** (a district name reused across states) → matched by the actual row pairing, not by name. Same-table makes this exact.
- **Large lists** → option lists stay capped (100 today) with in-dropdown search; narrowing usually shrinks them, and search respects the current narrowing.
- **Deep chains** → each level is one more query when an ancestor changes. No hard limit; nudge builders to keep chains to levels viewers actually use.
- **Column renamed or removed** → the filter shows as broken in edit mode (prompt to remap/remove); its children fall back to full-list rather than breaking the dashboard.
- **Public links / report view** → identical narrowing; no authoring involved.

## Scope

**In (v1):** same-table parent→child links (child = value; parent = value/date/numerical), chains, one-parent-many-children, cycle prevention, live narrowing, silent auto-drop of invalid selections, Apply-gated + cross-tab application, and the filter states above.

**Out (later versions):**

- **Cross-table links via joins** — needs a table-relationship model we don't have. Biggest single lever; its own spec.
- **Reusable field hierarchies** — define Country > State > District once and reuse across dashboards, instead of per-dashboard linking. Natural v2 once per-dashboard proves out.
- **Date/numerical filter as a *child*** — narrowing a date picker's own min/max *bounds* to an ancestor. That's a range-bounds problem, not option-list narrowing. (A date/numerical filter as a *parent* is in scope.)
- **Filter defaults** — no way to set a default today; it's a separate feature. If it ships, a child's default must apply only when valid for the current parent.

**Engineering's call:** how child options are re-queried and cached.

---

## Appendix — how other BI tools do this

- **Superset** native filters cascade the same way: re-query the child when the parent changes, block cyclic dependencies. Their well-known bug is *not* dropping invalid child selections — which is exactly why we auto-drop.
- **Metabase, Power BI, Tableau** all require the linked levels either on one table or joined by a defined relationship. Confirms the same-table-first call for v1.
