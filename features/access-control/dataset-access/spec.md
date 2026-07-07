# Dataset Access + Self-Service Connections — v1 (Layer 2)

**Status:** Draft (from the 2026-07-02 brainstorm; decisions confirmed with the user)
**Depends on:** Layer 1 — content resource sharing (`../content/`), which ships the spine: `ResourceShare`, groups, resolver, registry, share modal.
**Roadmap:** `../ACCESS-MODEL-ROADMAP.md` · **Research:** [research.md](./research.md) · **Plan:** [plan.md](./plan.md)

**Acronyms:** dbt (transform tool) · RLS (row/column security — Layer 3, not this spec) · PII (personal data).

---

## Problem

Two gaps, one root cause (the data section is all-or-nothing by role):

1. **Analysts are blocked.** An M&E Officer who needs a new KoboToolbox source files a ticket and waits for an Admin. Setup, sync, and iteration all bottleneck on 1–2 Admins.
2. **Warehouse read is blanket.** Every Analyst can read every table — including HR/salary/beneficiary-PII tables. There's no way to say "Priya works on the Kobo survey data and nothing else."

## The idea

- **Dataset becomes a shareable resource.** A dataset = a warehouse schema, or one table in it. It gets an owner, a floor, and direct shares — the same model as a dashboard, resolved by the same Layer 1 resolver.
- **Analysts bring their own connections.** An Analyst creates a source + connection, which writes into a dedicated schema that becomes a dataset they own. They sync it self-serve ("Sync now" + a per-connection schedule) without touching the org's shared Prefect pipelines.

## Confirmed decisions (brainstorm, 2026-07-02)

| Question | Decision |
|---|---|
| Driver | Analysts are blocked — capability, not just consistency |
| Reach | Own + explicitly shared (full floor+shares model, not blanket edit) |
| Data-section scope | **Connections/Ingest only** — Transform, Warehouse config, Orchestration, Data Quality stay role-gated as today |
| How owned connections run | **Self-serve sync** on the connection — no Prefect pipeline required |
| Visibility of others' connections | Own + shared with me (Admin sees all) |
| RLS (rows/columns within a table) | **Layer 3, later** — this spec is whole-datasets only |

## What's included

- **Dataset registry**: discovered from the warehouse; each dataset (schema, or schema.table) carries owner + two-axis floor + direct shares (users/groups, View = read/query).
- **Dataset grants replace blanket warehouse read.** Browse/query/authoring surfaces (warehouse browser, Explore, chart builder's dataset picker, filters, metric validate/preview, CSV download, LLM ask) only show/serve datasets the viewer can access.
- **Authoring ≠ consuming.** Dataset access governs *authoring against* data (building charts/metrics on it, browsing rows). Rendering an *existing* chart stays governed by Layer 1 content access — a funder viewing a shared dashboard needs no dataset grant.
- **Analyst connection CRUD**: create source + connection (writes to an owned schema via Airbyte's `destinationSchema`); edit/delete own (or shared-Edit) connections; Admin governs all.
- **Self-serve sync**: "Sync now" (direct Airbyte trigger) + per-connection schedule; both owner/Edit-gated; visible sync history.
- **Migration that narrows, not breaks**: existing datasets start at `analysts_plus / view` (today's behavior); Admins then lock down sensitive ones. New Analyst connections start Private.

## What's deferred

- Row/column-level security within a dataset → Layer 3 (`../rls-access/`).
- Ownership/sharing on Transform (dbt models), Warehouse config, Pipelines, Data Quality.
- Dataset **Edit** grants beyond re-share (no user-facing "edit a dataset's data" concept in v1).
- Per-user warehouse credentials (dbt and queries keep org-level credentials; enforcement is app-layer).

## Target users & example

- **Sarah (Admin):** locks `hr_data` to Private, grants `kobo_survey` to the "M&E team" group, keeps governance on everything.
- **Priya (Analyst):** creates a KoboToolbox connection → data lands in `raw_kobo_priya` (a dataset she owns) → hits "Sync now" → builds charts on it — without seeing `hr_data` and without filing a ticket.
- **James (Member):** unaffected — Members never see the data section; dashboards shared with him render exactly as before.

## Success metrics

- Time from "Analyst needs a new data source" to first synced table: **days → under 30 minutes**, no Admin involvement.
- Orgs restricting ≥1 sensitive dataset below `analysts_plus`: **50% of active orgs within 3 months**.
- Admin tickets for "set up a connection for me": **down 80%**.
- Zero broken charts at migration (the narrowing-not-breaking guarantee).

## Key product rules

- A dataset grant is **View = read/query/author-against**. Re-sharing a dataset requires Edit on it (same re-share rule as Layer 1); in practice owner + Admin manage grants in v1.
- A connection and its produced dataset are linked: sharing the **connection** (config access) is separate from sharing the **dataset** (data access) — sharing one never implies the other (same "references ≠ shares" principle as Layer 1).
- dbt is a privileged org-level process; dataset grants don't constrain it.
- Member role: no change — the data section stays hidden from Members entirely.
