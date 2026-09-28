# Dependent Filters

**Owner:** Product (Abhishek) · **Date:** 2026-09-28 · **Status:** Draft (v2 — supersedes parent-child) · **Area:** Dashboards → Filters

**In one line.** Group filters so selecting a value in one narrows the options in the others — pick a State and Country / District / City narrow to what's consistent with it.

## Problem

Filters are independent today: a District filter lists all ~700 districts even after a State is picked. Viewers scroll irrelevant options and can choose impossible combinations (Kerala + a Gujarat district) that return empty charts.

## Key points

- **Dependent group** = a set of filters that mutually narrow each other. No direction, no parent/child, no cycles.
- **Per dashboard.** Groups are configured on the dashboard; they are not shared or reused across dashboards.
- **Set in one place** — a central "Dependent groups" config, not a per-filter "depends on".
- **Categorical only (v1).** Groups contain string / categorical (dropdown) filters. Date and numeric filters don't participate yet — deferred.
- **No name.** A group is just its set of filters; there's nothing to name.
- **One group per dashboard (v1).** A dashboard has a single dependent group; each filter is either in it or independent. Multiple groups are deferred.
- **Same-table members** — but for *narrowing only* (see Two mechanisms). Ungrouped filters stay independent.
- **Live narrowing; Apply still gates charts; cross-tab application unchanged.**
- **Reverse narrowing:** pick City → State and Country narrow too.
- **Conflicts auto-resolve silently:** the just-changed filter wins; an older, now-impossible selection is dropped (no note).

## Model

Within a group, a filter's available values = distinct values from the group's table where **all other members' selections** apply — never its own (the exclude-self rule; otherwise it collapses to the value you just picked). The result is the same regardless of click order.

## Two mechanisms — don't conflate

1. **Application (filter → charts)** — unchanged and already cross-table. Filters apply by column name (`WHERE <col> IN (...)`) with no table check, so one State filter drives charts on *any* table that has a `state` column.
2. **Narrowing (valid options for a member)** — what groups add, and the only thing needing same-table: computing valid value *combinations* requires the columns to sit on one table. Two tables that merely share a column can't supply combinations without a join (deferred). Build the group on the hierarchy table; its filters still drive charts on every table by column name.

## Setup — central config

A **Dependent filters** section sits beside Filters in the display-controls panel. A dashboard has one dependent group: check the filters that belong to it — no name to fill in. Only same-table categorical (string / dropdown) filters are selectable; date, numeric, and different-table filters are greyed out. The per-filter modal just shows a read-only "Linked with: State, District, City". Membership is the whole config — no direction, so no cycles.

┌ Dependent filters ───────────────────────┐
│ Filters that narrow each other            │
│ (same table, dropdown only):              │
│   [x] Country    [x] State               │
│   [x] District   [x] City                │
│   [ ] CF work type  — different table     │
│   [ ] work_month    — date, not supported  │
│                          Cancel    Save  │
└──────────────────────────────────────────┘

Left rail after saving:
  Filters (5):        Country · State · District · City · work_month
  Dependent group:    Country, State, District, City

## Behavior (view mode)

- On load: nothing pre-selected, all full lists; narrowing starts on the first pick.
- Select or change any member → the others re-query options for the current selections (exclude-self), instantly, in all directions. Multi-select unions within a filter and intersects across filters.
- One valid option left → narrow to it, don't auto-select.
- Apply commits selections to every tile on every tab (charts update only on Apply).
- Clear a member → the others widen. Reset all → full lists.
- Member states: full · narrowed · empty ("no values for current selection") · broken (edit mode only).

## Ungrouped filters

An ungrouped filter is independent: always its full list, never narrows or is narrowed. It can hold a selection that contradicts the group and return empty charts on Apply — by design; add it to the group to fix. Membership is all-or-nothing (no "relates to District but not Country").

## Edge cases

- **Column renamed → the group survives.** The member re-binds to the renamed column (via warehouse mapping, or a remap prompt in edit mode); membership and links are preserved, never silently dropped.
- **Column removed** (truly gone) → that member shows broken in edit mode; the rest of the group keeps working.
- **Over-constraint** → members with no matching values show the empty state, not an error.
- **Auto-drop converges** — dropping only relaxes constraints, so it can't loop.
- **Unlink or delete a member** → the others widen; a group under 2 members dissolves.
- **Large lists** stay capped (100) with search that respects the current narrowing.
- **Performance** — each change re-queries the other N−1 members; cost grows with group size (caching is engineering's call).
- **Public / report view** — identical narrowing.

## Scope

**In (v1):** one dependent group per dashboard; **categorical (string) filters only**; unnamed group; mutual all-direction narrowing; same-table membership; multi-select; live narrowing; narrow-only on a single option; silent auto-drop (just-changed-wins); Apply-gated cross-tab application; rename-safe group; the member states above.

**Out (later):** multiple dependent groups per dashboard; date & numeric filters in the group (as drivers and as narrowed members); cross-table groups via joins; reusable groups across dashboards; filter defaults.
