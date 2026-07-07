# Layer 3 — Row/Column RLS (scope stub)

**Status:** not yet planned — deferred follow-on. This stub records the intent and the seams so it isn't lost.
**Depends on:** Layer 2 (`../dataset-access/`) for datasets, and Layer 1 (`../content/`) for groups + the principal model.
**Roadmap:** `../ACCESS-MODEL-ROADMAP.md`.

**Acronyms:** RLS (row-level security — filter rows / mask columns by who's viewing) · PII (personal data) · dbt (transform tool).

---

## The idea in one line

Within a *single* dataset, show different people different **rows** and **columns** based on who they are — the "proper answer to audience-aware data on one dashboard" that Layer 1 explicitly deferred.

**Example:** on one `beneficiaries` table, a funder sees only their region's rows with names masked; field staff see full names for their own program.

## Why it's a separate layer, not another resource type

RLS is the **data plane**, not the control plane. It doesn't grant access to a *resource* — it filters *data* per row, per query. It reuses Layer 1's **groups** and **principal** concept (a rule is "this group sees these rows"), but **not** the `ResourceShare` grant table. It needs its own engine.

## What it will likely need (draft — to refine at planning)

- **Policy model:** per-dataset row-filter rules (column = attribute) and column-mask rules, targeting a `UserGroup` or an attribute principal.
- **A principal attribute** (e.g. `region = North`) — the likely 4th `principal_type` the Layer 1 model was kept open for.
- **A query-enforcement layer:** Postgres RLS policies / BigQuery row-access policies, or a query-rewrite layer in the warehouse adapter.
- **Coverage across every read path:** charts, report snapshots (which query *live* data under a frozen layout), public links, and Explore must all honor the same policy.

## Open questions to resolve when planning

1. **Enforcement mechanism:** warehouse-native policies vs application-side query rewrite (differs Postgres vs BigQuery).
2. **How policies bind to identity** at query time — the resolver runs app-side; RLS needs the viewer's identity/attributes pushed into the warehouse query.
3. **Report snapshots + public links:** snapshots query live data, and public viewers are anonymous — what does RLS mean for a frozen-layout live-data report, or for an anonymous link?
4. **Performance:** row filters on every query on slow/old devices and large tables.

## Key dependency to protect now

Layer 1's decision to keep `principal_type` an **open enum** (not a rigid three-value assumption) is what lets RLS add an attribute principal later without a rewrite. See `../ACCESS-MODEL-ROADMAP.md` implication #4.
