# Layer 2 — Dataset Access + Self-Service Connections (scope stub)

**Status:** not yet planned — this is a scope stub capturing the 2026-07-02 brainstorm, so planning can start from a known shape.
**Depends on:** Layer 1 (`../content/`) — reuses `owner`, `ResourceShare`, `UserGroup`, the resolver, and the floor.
**Roadmap:** `../ACCESS-MODEL-ROADMAP.md`.

**Acronyms:** dbt (the transform tool that builds modeled tables) · RLS (row/column security — Layer 3) · FK (foreign key).

---

## The idea in one line

Make the **Dataset** a first-class shareable resource: an Admin grants Analysts the specific datasets they can work on, and Analysts can bring their own **sources/connections**, each of which produces a dataset they own.

## Confirmed decisions (from the brainstorm)

| Question | Decision |
|---|---|
| Driver | Analysts are **blocked** — waiting on Admins to set up ingestion is a real bottleneck |
| Reach | An Analyst manages **only what they own**, plus datasets/connections **shared with them** |
| Which data-section parts | **Ingest / Connections** only (this version). Transform, Warehouse, Orchestration, Data Quality stay role-gated as today |
| How an owned connection runs | **Self-serve sync** — a "Sync now" + per-connection schedule, independent of the shared Prefect pipeline |
| Visibility of others' connections | **Own + shared with me** — full content-style floor + shares model, extended to connections/datasets |

## What this version includes (draft — to refine at planning)

- **Dataset** as a new `resource_type` on `ResourceShare` — owner + floor + shares, resolved by the Layer 1 resolver.
- **Connection** as a new `resource_type` — Analysts get `can_create_connection`; owner-scoped edit/delete/sync; self-serve sync.
- **Connection → Dataset lineage:** a new connection writes to a raw dataset the Analyst owns.
- **Replace Spec A's blanket Analyst warehouse-read** with per-dataset grants (the key behavior change).
- Reuse the share modal, groups, request-access, and transfer from Layer 1.

## Open questions to resolve when planning

1. **What is a "Dataset" in warehouse terms?** A schema? A set of tables? Per-connection raw tables + their dbt models? (Postgres vs BigQuery enforcement differs.)
2. **Authoring vs consuming:** confirm that a chart built on a dataset still renders for the chart's viewers even if they lack dataset access (dataset access = who can *author/query directly*, not who can *see rendered output*).
3. **Guardrails for Analyst-created connections:** credential handling (source secrets), warehouse-write safety (namespace / name-collision / table bloat), and sync rate limits.
4. **Transform coupling:** dbt (Admin/shared) reads across datasets an Analyst may not have — confirm dbt runs as a privileged process and read-only transform views don't leak restricted datasets.
5. **Migration:** how existing orgs move from "all Analysts read everything" to per-dataset grants without breaking existing dashboards.

## Deferred from here

Row/column RLS → Layer 3 (`../rls-access/`). Transform/warehouse/orchestration ownership → future.
