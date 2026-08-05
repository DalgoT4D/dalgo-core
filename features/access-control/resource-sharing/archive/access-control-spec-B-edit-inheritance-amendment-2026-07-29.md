# Spec B Amendment — Edit Inheritance (Dashboard → Charts/KPIs)

**Date:** 2026-07-29
**Owner:** Product (Abhishek)
**Status:** Locked — replaces the "Edit on a container = structure only" rule in Spec B §7.1/§7.2, revises §8.3, and retires worked example A.
**Scope:** Edit cascade from a Dashboard to its child Charts/KPIs (PR #46, changes 1 & 2).

---

## The rule

1. **Edit on a Dashboard confers Edit on its child Charts/KPIs.** A dashboard-editor can edit both the dashboard structure *and* the content of the charts/KPIs inside it.
2. **Removing a dashboard's Edit removes the derived Edit on those children — with a warning** naming the affected users and charts.
3. **Embedding a chart fires an edit-exposure warning** naming the dashboard's editors who will gain Edit on that chart (mirrors the existing view-broadening warning).

Edit is now resolved as a **union across paths**, and unwound **only at its source**.

## Resolution logic

A user has **Edit on a chart/KPI** if *any* of these hold:

- a **direct** Edit grant on the chart, **or**
- **Edit on any dashboard** that contains it, **or**
- **Admin** override — per Spec A, an Admin is effective owner of every resource, so always holds Edit (and delete) regardless of grants or dashboards.

What "union across paths" implies:

- **Most permissive path wins** — Edit via one dashboard + View via another = Edit.
- **Direct grants are independent** — a direct Edit on the chart survives even if every containing dashboard is View-only.
- **You can't downgrade a chart below a live edit path.** An Admin cannot set a user to View on a chart while that user holds Edit on a dashboard containing it. The action is **blocked**, and the Admin is told to lower access **at the dashboard(s)** first. Editing chart access never propagates upward to change dashboard access.
- **Removal recomputes, it doesn't blunt-strip** — removing one edit path drops the derived edit only if no other path remains.
- **Dashboard-derived Edit is standalone** — the chart appears in the editor's `/charts` and is editable there, not just inline. (View on a dashboard stays inline-only; only **Edit** cascades to standalone access. A heavy dashboard-editor will accumulate `/charts` entries as a result.)

## Worked examples

*Chart C sits in Dashboard A and Dashboard B.*

1. Edit on A, View on B → **Edit on C** (most permissive path).
2. Direct Edit on C, View on A and B → **Edit on C** (direct grant stands).
3. Edit on A and B; Admin tries to set C → View → **blocked**; Admin told *"user has Edit via Dashboards A and B — change those to View first."* No upward propagation.
4. Edit on A (→ Edit on C) **plus** a direct Edit on C; remove Edit on A → **still Edit on C** (direct grant remains; warning notes it's retained).
5. Edit on A only (→ Edit on C); remove Edit on A → **loses Edit on C** (warned: *"N users lose Edit on M charts"*).
6. Edit on A granted to **Group G (20 people)** → all 20 get Edit on C; remove G from A → all 20 lose the derived Edit (recomputed per person; those with another path keep it).

## Consequences to internalize (mental-model shift)

- **Embedding a chart exposes it to that dashboard's editors — accepted, no opt-out.** Any chart placed in a dashboard becomes editable by everyone who can edit the dashboard — this **overrides the chart's own floor**, including a Private/PII chart. There is **no per-chart lock**; the old protection (edit-on-dashboard ≠ edit-on-chart, Spec B §8.3 + worked example A) is **retired**. Protection is by placement only.
- **The only lever to protect a chart's content is placement**, not per-chart access: don't embed it in a dashboard editable by people who shouldn't edit it, or remove their dashboard-Edit.
- **You cannot restrict a chart directly — the system blocks it.** Lowering a user to View on a chart is **not allowed** while any dashboard-Edit path exists (see resolution logic). To actually restrict them you must go change their access on **every dashboard** that contains the chart — real operational cost when a chart is widely embedded.
- **Cascade scope is one level:** Dashboard → its direct Charts/KPIs. **Reports do not cascade** (Report-Edit = regenerate snapshot / edit summary / moderate comments only).
- **Cascade confers content-Edit, not delete** (delete stays owner/Admin) and **not metric-edit** — data-layer actions inside a KPI (selecting/creating a library metric) still follow the metric rules (role + dataset gated).

## Decisions (resolved)

1. **No sensitive-chart opt-out.** Embedding always exposes a chart to the dashboard's editors — there is no per-chart lock. Spec B worked example A is retired; protection is by placement only. *(This is the consequential one — it partially reverses the oversharing protection Spec B was built around. Communicate it explicitly at launch.)*
2. **Dashboard-derived Edit is both standalone and inline.** The chart appears in the editor's `/charts` and is editable there as well as inside the dashboard. (View on a dashboard stays inline-only; only **Edit** cascades to standalone access.)
3. **Embedding fires an edit-exposure warning** naming the dashboard's editors who will gain Edit on the chart — the in-flow signal for decision 1.
