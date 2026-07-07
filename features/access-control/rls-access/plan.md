# Plan — Row/Column RLS (Layer 3) — scoping plan

**Status:** Scoping draft — deliberately NOT an implementation plan. Layer 3's detailed LLD depends on decisions Layer 2 hasn't shipped yet (dataset grain, discovery, the `run_chart_query` seam in production). This document scopes the approach, names the one big architectural decision, and defines the trigger for full planning.
**Depends on:** Layer 2 (`../dataset-access/`) shipped; Layer 1 (`../content/`) groups + principal model.
**Roadmap:** [../ACCESS-MODEL-ROADMAP.md](../ACCESS-MODEL-ROADMAP.md) · **Stub:** [README.md](./README.md)
**Date:** 2026-07-02

**Acronyms:** RLS (row-level security — filter rows / mask columns by viewer) · PII (personal data) · dbt (transform tool).

---

## 1. What Layer 3 is

**The rule:** within a *single* dataset, different viewers see different **rows** and different **columns**.
**Example:** one `beneficiaries` table. A funder viewing the shared dashboard sees only their region's rows, with the `name` column masked to initials. Field staff see full names for their own program. Same dashboard, same chart, audience-aware data.
**Why it matters:** it removes v1's "split the dashboard per audience" workaround (Layer 1 spec §17) — the single most-requested privacy capability for orgs handling beneficiary PII.

**What it reuses from Layers 1–2:** groups ("this *group* sees these rows"), the principal model (with the `attribute` principal Layer 1's `principal_value` column was kept open for), dataset identity (policies attach to Layer 2's `Dataset` rows), and the `run_chart_query(viewer_ctx, chart, context)` choke point (Layer 1 built the seam; Layer 2 put the first check in it; Layer 3 rewrites the query inside it).

**What it does NOT reuse:** the `ResourceShare` grant table. An RLS policy is not a grant on a resource — it's a filter on data, evaluated per query. Layer 3 gets its own policy model.

## 2. The one big architectural decision — enforcement mechanism

| Option | How | Pros | Cons |
|---|---|---|---|
| **A. Query rewrite (app-layer)** — recommended direction | inside `run_chart_query`: wrap the compiled statement with `WHERE` predicates + column-mask projections derived from the viewer's policies | one implementation for Postgres AND BigQuery; works for every read path that goes through the seam; no per-user warehouse credentials needed (Dalgo queries as the org user today — warehouse-native RLS can't distinguish viewers without per-user DB roles, which don't exist) | must cover *every* read path (any endpoint that bypasses the seam bypasses RLS); SQL-injection-grade care in predicate construction |
| **B. Warehouse-native policies** | Postgres `CREATE POLICY` / BigQuery row-access policies + session variables per query | enforcement can't be bypassed by a missed endpoint | needs per-viewer identity pushed into the warehouse session on every query; two divergent implementations; masking (columns) isn't covered by row policies on Postgres; dbt and system processes fight the policies |
| **C. Materialized per-audience views** | generate filtered views per group and point charts at them | simple queries at read time | view explosion (groups × tables); staleness; doesn't handle per-user attributes |

**Why A is the working recommendation:** Dalgo's warehouse identity is a single org-level credential (verified — `dbtautomation_service._get_wclient`, Layer 2 research §5). Warehouse-native RLS distinguishes viewers by database identity, which Dalgo doesn't have per user and shouldn't create for 30+ Members per org. Query rewrite at the choke point matches the architecture we already have. Option B stays on the table as *defense in depth* for Postgres later.

## 3. Draft policy model (to be finalized after Layer 2 ships)

```python
class DatasetPolicy(models.Model):        # one row-filter or column-mask rule
    org         = FK(Org)
    dataset     = FK(Dataset)             # Layer 2's entity
    kind        = CharField()             # row_filter | column_mask
    # who it applies to — same principal vocabulary as ResourceShare:
    principal_type  = CharField()         # group | user | audience | attribute
    principal_id    = BigIntegerField(null=True)
    principal_value = CharField(null=True)
    # row_filter: column + operator + value-or-user-attribute ("region = @viewer.region")
    filter_column / filter_op / filter_value = ...
    # column_mask: column + mask style (hide | initials | hash)
    mask_column / mask_style = ...
```

Semantics to pin during full planning: do multiple matching row-filters OR or AND together; does *no matching policy* mean "all rows" (grant-shaped) or "no rows" (deny-shaped); who authors policies (dataset owner? Admin only?); where viewer attributes (e.g. `region`) live (OrgUser profile fields? group metadata?).

## 4. The read-path coverage matrix (the hard part)

Every path that turns a chart config into warehouse rows must pass through the rewrite:

| Path | Viewer identity available? | Note |
|---|---|---|
| Chart render (authenticated) | ✅ OrgUser | main case — via `run_chart_query` |
| Dashboard tiles | ✅ (Layer 1's `dashboard_id` context) | same seam |
| Report snapshot view | ✅ | **live data under frozen layout** — policies apply at view time, so historical reports become viewer-dependent. Communicate: two viewers of the same report may see different numbers. |
| Public links (anonymous) | ⚠️ `PublicLinkContext` (Layer 1 typed the resolver for this) | decide: public links on RLS-policied datasets are (a) blocked, (b) served with a designated "public" policy row. Recommend (a) block in v1 of Layer 3. |
| Explore / warehouse browse / CSV / LLM ask | ✅ | Layer 2 already gates whole-dataset; Layer 3 adds row/column shaping to permitted datasets |
| Alert evaluation, dbt | system processes | run unfiltered (consistent with Layer 2's rule) — alerts on policied datasets see full data; flag in alert-creation UI |

## 5. Coarse milestones (shape, not commitment)

1. **Policy model + authoring UI** (Admin-only first) on Layer 2's dataset settings page.
2. **Row filters via query rewrite** in `run_chart_query` — group + attribute principals; deny-shaped default on policied datasets.
3. **Column masks** (projection rewrite) — hide / initials / hash.
4. **Coverage hardening** — the read-path matrix as a parameterized test suite; public-link blocking; report-snapshot messaging.
5. **Performance pass** — rewritten-query plans on large tables; predicate indexes guidance.

## 6. Trigger for full planning

Run `/engineering/plan-feature features/access-control/rls-access/spec.md` (spec to be written first) when **all three** hold:
1. Layer 2 is merged (Dataset model + `run_chart_query` enforcing in production).
2. At least one org has narrowed a dataset below `analysts_plus` (proof the grant model is used).
3. PM confirms the driving use case (funder row-scoping vs PII masking — they order milestones 2 and 3 differently).

## 7. Open questions (carried from README + new)

1. Deny-shaped vs grant-shaped default on a policied dataset (recommend: dataset with ≥1 row-filter policy becomes deny-shaped for non-covered viewers).
2. Where viewer attributes live (`region`, `program`) — OrgUser fields vs group-encoded. Group-encoded ("Field Staff — North" group gets `region=North` filter) needs no schema change and reuses Layer 1 groups; attribute-encoded is cleaner at scale. Leaning group-encoded for v1.
3. Report snapshots: is viewer-dependent historical data acceptable to PM, or do policied datasets block report snapshotting?
4. Performance budget: rewritten predicates on slow org warehouses (the NGO constraint) — needs a spike during full planning.
