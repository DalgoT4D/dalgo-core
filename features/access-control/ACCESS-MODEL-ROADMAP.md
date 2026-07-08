# Access Control — Model Roadmap (north star)

**What this is:** the map that ties Dalgo's access-control work together. Not a buildable spec — it states the layers, the shared foundation, and the decisions in each layer that keep the next one buildable. Read this before planning any single layer.

**Date:** 2026-07-02

**Acronyms:** RLS (row-level security — filtering rows / masking columns by who's viewing) · FK (foreign key) · ACL (access control list).

---

## The one-picture model — three layers of one onion

Every layer answers "who can touch what," at a different depth:

```
Layer 3 — RLS access:     which ROWS / COLUMNS within a dataset   ← future  (data plane)
Layer 2 — Dataset access: which whole DATASETS you can author on  ← next    (control plane)
Layer 1 — Content:        which dashboards/charts/reports you SEE ← planned (control plane)
──────────────────────────────────────────────────────────────────────────────
Foundation (Spec A, shipped):  roles (Admin/Analyst/Member) · ownership · Settings
Shared spine (built in Layer 1): owner · ResourceShare(user|group|audience) · groups · resolver · floor
```

- **Layers 1–2 are the control plane** — per-resource, enforced in Django before a query runs.
- **Layer 3 (RLS) is the data plane** — per-row, per-query, enforced in the warehouse (Postgres RLS policies / BigQuery row-access policies / query rewrite).

That control-plane vs data-plane split is the most important line in this doc: it's why Layer 2 reuses almost all of Layer 1, and Layer 3 reuses only part.

---

## Folder map

| Folder | Layer | Status |
|---|---|---|
| `v2/` | **Foundation** — role system (Spec A) | ✅ shipped (DDP_backend#1414, webapp_v2#331) |
| `resourcesharing/` | **Layer 1** — content resource sharing | 📋 planned (`resourcesharing/plan.md`) |
| `dataset-access/` | **Layer 2** — dataset access + self-service connections | 🔲 to plan next |
| `rls-access/` | **Layer 3** — row/column RLS | 🔲 to plan later |
| `v1/` | source/archive (original specs, holes analysis, PM vision) | 🗄️ reference |

We plan **one layer at a time**, in order: content (done) → dataset-access → rls-access.

---

## What Layer 1 (content) is actually building — the reusable spine

Layer 1 isn't just "share a dashboard." It builds a general access core that the later layers inherit:

| Spine piece | Built in Layer 1 for | Reused by Layer 2 | Reused by Layer 3 |
|---|---|---|---|
| `owner` + transfer + owner-only-delete + Admin override | content resources | ✅ datasets, connections | ✅ (dataset owner sets policies) |
| `ResourceShare` (polymorphic `resource_type` + principal user/group/audience) | shareable content (dashboards/reports/alerts + metric/kpi general-only; **charts are container-gated, not shareable** — 2026-07-02 decision) | ✅ add `dataset`, `connection` | ⚠️ principal model only, not the grant table |
| `UserGroup` / membership | content audiences | ✅ dataset grants | ✅ RLS row-policies target groups |
| Resolver (`effective_permission`, `accessible_filter`) | content lists + guards | ✅ dataset lists + guards | ⚠️ called from query layer, not reused wholesale |
| Two-axis floor (audience × permission) | content | ✅ datasets/connections | — |
| Request-access, invites, notifications | content | ✅ | — |

**Reuse estimate:** Layer 2 ≈ 80% spine reuse. Layer 3 ≈ 30% (only groups + the principal concept).

---

## The five "get-this-right-now" implications for the Layer 1 build

These are guardrails for building and reviewing `resourcesharing/plan.md`, so the later layers stitch in cleanly.

> **1. Keep the resolver resource-type-agnostic.** Branch on *data* (the floor field + share rows), never on hardcoded `if resource_type == "dashboard"`. Then adding `dataset`/`connection` is an enum value, not a rewrite.

> **2. Keep "access to a resource" separate from "access to the data."** Sharing a chart must not imply warehouse read. Layer 2 is the first control over data; Layer 3 refines it to rows. If Layer 1 conflates them, Layers 2–3 have nothing clean to attach to.

> **3. Make groups a general org primitive, not "content groups."** A "Funders" group must be shareable-with (L1), grantable-to (L2), and RLS-targetable (L3) — the same object, three uses.

> **4. Don't over-close the principal model.** Today `{user, group, audience}`. RLS may add an `attribute` principal ("region = North"). Keep `principal_type` an open enum, not a rigid three-value assumption.

> **5. Leave a query-layer hook.** The resolver runs at the app layer today. Datasets and RLS need enforcement at *query* time (when the backend queries the warehouse for a chart). Keep the resolver a callable function, so the query path can call it later.

---

## Where the model honestly strains (set expectations)

RLS is **not** "another resource type." It reuses the *vocabulary* (groups, principals, ownership) but needs its own engine: warehouse-native policies or a query-rewrite layer, working whether data is reached via a chart, a report snapshot (live data!), a public link, or Explore. Anyone expecting "RLS falls out of resource sharing for free" will be surprised. Layer 1 + Layer 2 give RLS its nouns; Layer 3 builds its verbs.

---

## The honest boundaries between layers (from the brainstorm, 2026-07-02)

- **Charts are not independently shareable (2026-07-02).** A chart is visible wherever its dashboards are visible; chart-level privacy is Layer 2's dataset grants. This deleted Layer 1's embed/broadening guardrails.
- **Sharing a resource ≠ sharing its data.** A shared chart renders for its viewers regardless of their dataset access. Dataset access governs *authoring against* the data; RLS governs *which rows/columns*.
- **Dataset access changes an existing Spec A rule.** Today Analysts have blanket warehouse read. Layer 2 replaces that with per-dataset grants — a real tightening to communicate.
- **Self-service is partial.** Layer 2 lets an Analyst get data *in* (own a connection + dataset) but not *model* it — transform (dbt) stays Admin/shared.
