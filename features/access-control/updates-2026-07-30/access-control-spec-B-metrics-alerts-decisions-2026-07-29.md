# Spec B — Metrics & Alerts Decisions

**Date:** 2026-07-29
**Owner:** Product (Abhishek)
**Status:** Decisions locked — ready to fold into Spec B §4 / §6 / §11 (+ Spec A permission matrix)
**Source:** Working session off [PR #46](https://github.com/DalgoT4D/dalgo-core/pull/46/changes) — the "Updates to spec to be incorporated" block
**Scope note:** Covers Metrics, Alerts, the IA move, and the permission matrix. **Edit-inheritance (PR changes 1 & 2 — Dashboard-edit cascading to child edit, and removal cascade + user warning) is PINNED and handled in a separate pass.**

---

## 1. Core framing — two governance regimes

The product now has two explicit access regimes, and the line between them is the key decision:

- **Content layer — Visualisations (Charts, KPIs, Dashboards, Reports).** Grant-driven. **Role does not cap function** — a Member with an Edit grant can edit and re-share. Governed by the floor + direct-share model (existing Spec B).
- **Data layer — Pipeline, Metrics, Alerts.** Role- **and** dataset-gated. **Role gates *authoring*; consumption is gated by dataset/source access, not role.** This is the same regime that already governs Ingest/Transform in Spec A.

**Principle rewording (for §4):** the "role ≠ function" principle is scoped to content resources, not universal. State it as *"role does not cap View/Edit on **content** resources,"* and add: *"Data-layer objects (Pipeline, Metrics, Alerts) are role- and dataset-gated by design; consumption is gated by source access rather than role."* This turns an apparent contradiction (Members can't author metrics/alerts) into a stated, defensible boundary.

Why this is the right trade: you can have *"no per-resource ACLs on metrics/alerts"* OR *"role never gates authoring"* — **not both.** We chose no-ACLs (industry-standard Approach A), so role-gated authoring is the consistent price.

---

## 2. Information architecture

New sidebar structure:

- **Home**
- **Visualisations** — Dashboards, Charts, KPIs
- **Data** — Explore, Metrics, **Alerts**
- **Pipeline** — Overview, Ingest, Transform, Orchestrate, Data quality
- **Settings** — User management, Branding

**Metrics and Alerts move under Data** (confirms PR change 3). Divergence from peer tools noted and accepted: peers anchor alerts to the visualisation tile, but Dalgo allows a metric-level trigger, so grouping alerts with metrics under Data is coherent — as long as in-context creation (bell on a KPI/chart) still exists (see §5).

---

## 3. Permission matrix

| Role | Visualisations *(resource-level)* | Data — Metrics/Alerts/Explore *(dataset-gated)* | Pipeline *(resource-level)* | Settings |
|---|---|---|---|---|
| **Admin** | CRUD | CRUD (all) | CRUD | CRUD |
| **Analyst** | CRUD *(via grant)* | CRUD *(datasets they can access)* | CRU | Groups only — create/manage |
| **Member** | CRUD *(via grant)* | View + use, no CUD *(dataset-gated)* | Not visible | Groups only — view own |

Cell nuances to preserve when this becomes spec text:

- **Visualisations "via grant"** = the existing floor + direct-share model. A Member reaches Edit through a resource grant, not their role.
- **Data / Member** = view and *use*; may build **inline** metrics inside a chart but **cannot save to the metric library** (see §6). "Not visible" is *not* used here — Members see Data content they've been granted the dataset for.
- **Settings / Member "Groups only"** = view the groups they belong to. Members cannot create groups (reconcile with Spec A §9). Analyst "Groups only" = create/manage groups.

---

## 4. Metrics — settled model

Governance = **Approach A: semantic/data-layer, governed by dataset access.** Matches Power BI (measures are model-level), Metabase (metric use requires data permission), Looker (metrics live in the modeling layer). No per-metric ACL.

- **No ownership concept.** Metrics are shared canonical definitions; nobody "owns" one.
- **Members:** can see the Metrics menu item, and view + use metrics when building charts and KPIs — the metrics they can actually see/use are gated by dataset access. Can build **inline** metrics in the chart builder; **cannot save/promote to the metric library.**
- **Analysts:** CRUD any metric whose underlying dataset they can access.
- **Admins:** CRUD all metrics.
- **Referential guardrail retained (already built):** a metric can't be deleted until it's unlinked from all resources. **Editing has high blast radius — an update changes every linked chart/KPI at once — so edits must trigger a warning that surfaces the impact (e.g. "used in N resources") before saving.** Together, the delete-lock and the edit warning are what make "any analyst can create/edit/delete" safe without ownership.

---

## 5. Alerts — settled model

Governance = **Tableau/Looker lineage, not Power BI.** (Power BI rejected: alerts are strictly private and die with the creator — no transfer.) An alert is creator-owned personal automation with a recipient list; visibility inherits from the trigger source.

- **Trigger source:** a KPI or a Metric.
- **Ownership:** creator-owned, **ownership transferable**; Admin overrides all.
- **Create:** Analyst+ only, on sources whose datasets they can access. Members cannot create.
- **View (config):** dataset/source-gated — anyone who can access the trigger source (including a Member) can view the alert config. Creator always sees it. **Sensitive-source lock (from Looker):** if the trigger source is restricted, the alert drops to creator + Admin only.
- **Edit:** owner + Admin (creator-owned — chosen over "any analyst with access" to avoid "who touched my alert").
- **Delete:** owner + Admin.
- **Recipient list = a separate axis from config rights.** **Receiving a notification ≠ any config right** — Members can be recipients regardless of edit rights. Managing the recipient list (adding/removing people) is an edit action (owner/Admin).
- **Two entry points (like Tableau/Looker):** a **bell-in-context** on the KPI/chart to create where you're watching, **plus** a manage/list page under Data for "alerts I own or receive."

**Metrics ↔ Alerts are intentionally asymmetric.** Metrics = no ownership, any-analyst CRUD (shared definition). Alerts = owned + transferable (personal automation). Two rules by design; the spec should say why.

---

## 6. Inline vs. library metrics, and the KPI rule

Two things hide in the word "metric": an **inline** (chart-scoped) calculation, and a **library** (saved, reusable, shared) metric. The chart builder does both today.

- **Gate the promotion, not the builder.** Building an inline calc = editing content → available to anyone with Edit on the chart + dataset access (incl. Members). **"Save to metric library" = a data-layer create → Analyst+ only.** No standalone "New metric" entry for Members.
- **KPI rule (confirmed):** a KPI must be backed by a **library** metric. Consequence: Members build charts freely (inline metrics) but use only predefined metrics for KPIs, and don't mint new KPIs. This makes the chart/KPI split load-bearing — KPIs stay governed org indicators. *This is the feature, not a limitation.*

---

## 7. Confirmed decisions & carried-forward work

1. **KPI must be library-backed — CONFIRMED.** A KPI must be built on a library metric; Members use predefined metrics for KPIs and don't mint new ones (see §6).
2. **Member view of the Data section — CONFIRMED.** A Member sees a metric/alert only via a **direct dataset grant**. Members without dataset grants see the Data menu items but an empty list; their metric *use* still flows through the charts/KPIs they've been granted.
3. **Member + Settings "Groups only" — CONFIRMED.** Members view only the groups they belong to and cannot create groups (consistent with Spec A §9).
4. **Interim window before Spec C — CONFIRMED as a deliberate, time-boxed gap.** The dataset-gating in this model assumes Spec C (table-level access). Until it ships, the fallback gate is role-only (Analyst+ see all metrics/alerts). Accepted as an interim state; flag to leadership at launch.

**Carried forward (separate pass, not open):** Edit-inheritance (PR changes 1 & 2) — Dashboard-edit cascading to child Charts/KPIs, plus removal-cascade + user warning — is handled in its own amendment because it contradicts current §7.1/§7.2/§8.3 and worked example A, and needs a stated rewrite rather than a quiet patch.

---

## 8. Where Spec B needs updating (section map)

- **§1 Overview** — inheritance bullet (pinned edit-cascade) + note metrics/alerts as data-layer.
- **§2 Goals / Non-goals** — the deferred "individual sharing for KPIs/Metrics" line changes; alerts no longer a floor-governed resource.
- **§4 Boundary with Spec A** — scoped principle + data-layer boundary statement (§1 above).
- **§5.1** — floor no longer applies to Metric or Alert (remove them from the "every content resource carries a floor" list).
- **§6 Resource Taxonomy** — Metric and Alert rows: **not** individually shareable; governed by dataset access + (alerts) ownership.
- **§11 Alerts** — full rewrite per §5 above: drop floor/direct-share model; creator-owned + transfer; dataset-gated view; sensitive-source lock; recipient/follow as its own axis; bell-in-context + manage page.
- **§13 UI Surface** — Data section, Metrics page (no Member "new metric"), Alerts page + in-context bell, permission matrix.
- **§15 Technical** — drop Alert floor; add ownership + transfer; dataset-gated resolver for metrics/alerts; "save to library" gated to Analyst+.
- **Spec A** — the permission matrix (§3) is primarily a Spec A artifact (role × capability).

---

## 9. Industry basis (for defending the model)

- **Power BI** — measures governed at the semantic-model level (Read/Build/Write); data alerts strictly private, no transfer.
- **Metabase** — metric use requires *data* permission on underlying tables; `Block` overrides collection access.
- **Looker** — metrics defined in the modeling layer, governed by data access + RLS; alerts public-if-you-can-see-the-source, followable, auto-locked on sensitive sources.
- **Tableau** — data-driven alerts are creator-owned, ownership transferable, optional visibility, recipient list; permissions checked at send time.
