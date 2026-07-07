# Plan — Dataset Access + Self-Service Connections (Layer 2) — v1

**Status:** Draft v1 (for engineering review)
**Spec:** [spec.md](./spec.md) · **Research:** [research.md](./research.md) · **Roadmap:** [../ACCESS-MODEL-ROADMAP.md](../ACCESS-MODEL-ROADMAP.md)
**Depends on:** Layer 1 (`../resourcesharing/plan.md`) — specifically `ResourceShare` (with CharField `resource_id`), `UserGroup`, the resolver + `RESOURCE_TYPES` registry, and the `run_chart_query` seam. **Do not start M2+ of this plan before Layer 1's M1–M3 are merged.**
**Date:** 2026-07-02

**Acronyms:** FK (foreign key) · dbt (transform tool) · RLS (Layer 3) · PII (personal data).

---

## 1. Overview

**What we're building:** the Dataset becomes Dalgo's 7th shareable resource and the Connection its 8th. An Admin grants Analysts the specific datasets they can browse/query/build on (replacing the blanket `can_view_warehouse_data`); Analysts create + own their own Airbyte connections, each writing into a dedicated schema that becomes a dataset they own, with self-serve "Sync now" + a per-connection schedule that bypasses Prefect.

**Services affected:**

| Service | Touched? | What |
|---|---|---|
| DDP_backend | ✅ heavily | `Dataset` model + discovery, `ConnectionMeta` upgrade (org/owner/floor), dataset-grant enforcement across ~20 endpoints, direct-sync endpoint + Celery-beat scheduler, seed changes (Analyst gains scoped connection slugs) |
| webapp_v2 | ✅ | dataset badges/filtering in every table picker, Datasets settings page, connection ownership UI + Sync now + schedule, share modal reuse for datasets/connections |
| prefect-proxy | ❌ | self-serve sync deliberately bypasses Prefect (direct Airbyte trigger) |

---

## 2. Blast Radius

Primary entities: **Dataset (new)**, **Connection** (gains ownership), **warehouse read surfaces**. Traversed from `docs/domain-map.md` + research §5's enforcement map.

| Surface | Why affected | Status | Notes |
|---|---|---|---|
| Warehouse browse APIs (12 endpoints) | dataset grants replace flat slug | **in scope** | `warehouse_api.py` — research §5 |
| Filters API (4 endpoints) | same | **in scope** | `filter_api.py` |
| Chart authoring/preview endpoints | run warehouse SQL under `can_view_charts` | **in scope** | payload-driven = authoring = gated; `chart_id`-driven = consuming = NOT gated |
| Metric validate/preview, KPI aggregates | run warehouse SQL | **in scope** | authoring paths gated |
| Explore, Ingest "Your Warehouse" tab, Data Quality pages | browse tables | **in scope (frontend)** | show only accessible datasets |
| Chart builder `DatasetSelector` | the picker | **in scope** | lists only accessible datasets |
| Source/Connection CRUD | Analyst self-service | **in scope** | ownership-scoped |
| Pipelines / Orchestration | shared Prefect flows | **out of scope** | untouched; self-serve sync is a parallel path |
| Transform (dbt) | privileged org-level process | **out of scope** | dbt runs unconstrained by grants (spec rule); transform UI's warehouse *browse* calls ARE gated (they use the same endpoints) |
| Dashboards/charts render (consuming) | Layer 1 governs | **explicitly NOT gated** | a funder viewing a shared dashboard needs no dataset grant |
| LLM "ask warehouse" + CSV download | read full tables | **in scope** | gated like any read |
| Alerts (standalone type queries a table) | evaluation queries | **out of scope (v1)** | alert evaluation is a system process like dbt; alert *creation* UI picker is gated |
| Member role | — | **unaffected** | data section stays hidden |

---

## 3. High-Level Design

### 3.1 The mental model

**The rule:** a Dataset is a resource like a Dashboard — owner, floor, shares, resolved by the Layer 1 resolver. "Can Priya query `kobo_survey.responses`?" = `effective_permission(priya, "dataset", that_dataset) is not None`.
**Example:** Sarah sets `hr_data`'s floor to Private. Priya's chart-builder picker no longer lists any `hr_data` table; a hand-crafted preview request for it 403s. Her `raw_kobo_priya` dataset (floor Private, she owns it) works fully — for her.
**Why it matters:** one access model across content and data; the Layer 1 spine does the work (roadmap: ~80% reuse).

### 3.2 Enforcement: one helper, ~20 call sites, two categories

```
can_read_dataset(viewer, schema, table=None) -> bool
   → Dataset row lookup (schema exact, table exact-or-schema-wide)
   → effective_permission(viewer, "dataset", ds) is not None
   → unknown schema/table → Admin-only (fail closed; discovery job will register it)

AUTHORING (payload carries schema/table)          CONSUMING (chart_id carries config)
warehouse_api (12) · filter_api (4)               GET /charts/{id}/data (render)
chart-data-preview · metric validate/preview      dashboard tiles (Layer 1 context param)
transform datatypes · explore                     public links
   → can_read_dataset() enforced                     → Layer 1 content access only
```

The existing stub `has_schema_access()` (`charts_api.py:111`, a literal TODO) becomes real and delegates to `can_read_dataset`. The `run_chart_query` seam (Layer 1) gains its first check: authoring-context queries verify dataset access; render-context queries don't.

### 3.3 Self-service connection flow

```
Priya: "Add source" (KoboToolbox creds) → "Create connection"
   → backend forces destinationSchema = raw_{org}_{slug}   (namespace isolation)
   → Airbyte connection created (scheduleType stays "manual")
   → ConnectionMeta upgraded row: org, owner=Priya, floor=private
   → Dataset row auto-created: schema=raw_{org}_{slug}, owner=Priya, floor=private
   → NO Prefect deployment created for self-serve connections
Priya: "Sync now"  → airbyte_service.sync_connection()  (direct, owner/Edit-gated)
Priya: schedule "daily 6am" → ConnectionSchedule row → Celery-beat tick triggers due syncs
```

Admin-created connections keep today's Prefect path untouched. Sync telemetry still lands in `AirbyteJob`/`SyncStats` (Airbyte-side, path-independent).

### 3.4 New / modified endpoints

| Endpoint | Change |
|---|---|
| `/api/sharing/dataset/...`, `/api/sharing/connection/...` | free — registry entries; Layer 1 endpoints serve them |
| `/api/datasets/` GET | list datasets with access badges (Admin: all; others: accessible) |
| `/api/datasets/discover` POST (or beat task) | sync warehouse schemas/tables → Dataset rows |
| `/api/airbyte/v1/connections` CRUD | Analyst-callable; service layer enforces owner-or-Edit |
| `/api/airbyte/v1/connections/{id}/sync` POST | **new** — direct sync, owner/Edit-gated, rate-limited |
| `/api/airbyte/v1/connections/{id}/schedule` PUT | **new** — per-connection cron (ConnectionSchedule) |
| ~20 read endpoints (research §5) | + `can_read_dataset` check |

---

## 4. Low-Level Design

### 4.1 Data model

```python
class Dataset(models.Model):                    # the resource rows floor/owner hang on
    org        = models.ForeignKey(Org, on_delete=CASCADE)
    schema_name= models.CharField(max_length=128)
    table_name = models.CharField(max_length=128, null=True)  # null = whole schema
    owner      = models.ForeignKey(OrgUser, on_delete=SET_NULL, null=True)
    floor_audience   = models.CharField(max_length=15, default="analysts_plus")
    floor_permission = models.CharField(max_length=5, default="view")
    source_connection_id = models.CharField(max_length=64, null=True)  # lineage to the producing connection
    discovered_at / created_at ...
    class Meta: unique_together = [("org", "schema_name", "table_name")]
```

- **Grain:** schema-level row (table_name null) covers all current + future tables in it; table-level rows allow finer grants. Resolution: table row wins if present, else schema row, else fail-closed (Admin-only).
- **Registry entries:** `dataset` → floor + shares, not public-linkable; `resource_id` = `str(Dataset.pk)` (the string pk contract from Layer 1). `connection` → full share (View=see config+history, Edit=edit/sync/delete), not public-linkable; `resource_id` = Airbyte UUID.
- **`ConnectionMeta` upgrade:** add `org` FK, `owner` FK, `floor_*` (backfill org from `OrgTask`, owner null → Admin-owned legacy).
- **`ConnectionSchedule`:** `connection_id`, `org`, `cron`, `enabled`, `last_triggered_at`.
- **Layer 1 amendment (already flagged in research §6):** `ResourceShare.resource_id` → **CharField(255)** (dataset keys can exceed 64).

### 4.2 Seed changes

Analyst gains: `can_create_source`, `can_create_connection`, `can_edit_connection`, `can_delete_connection`, `can_sync_connection` (**new slug**) — all **ownership-scoped in the service layer** (the slug lets you reach the endpoint; owner-or-Edit decides on the object, exactly like Layer 1's `can_share_* + resolver` pattern). `can_view_warehouse_data` stays as the coarse gate; `can_read_dataset` adds the per-dataset check behind it.

### 4.3 Enforcement details

- `core/sharing/datasets.py`: `can_read_dataset(viewer, schema, table)` + `accessible_datasets_q(viewer)` (the list filter — same one-query pattern as Layer 1's `accessible_filter`).
- `/sync_tables` + schema/table list endpoints filter their output through `accessible_datasets_q` — pickers only show what you can use.
- Fail-closed on unknown schemas (not yet discovered): only Admins see them; the discovery task (Celery beat, daily + on connection create/sync) registers new ones at the org-default dataset floor.
- CSV download + LLM `ask` + column-values + insights: same `can_read_dataset` check (they're full-table reads).
- dbt + alert evaluation: run under org credentials, unconstrained (system processes — spec rule).

### 4.4 Self-serve sync guardrails (the brainstorm's two named risks)

- **Credentials:** source secrets flow through the existing Airbyte secret handling — unchanged; Analysts never see stored secrets (Airbyte masks on read).
- **Warehouse-write safety:** forced `destinationSchema` (`raw_{org}_{slug}`, collision-checked against existing schemas) — an Analyst connection cannot write into shared/modeled schemas.
- **Rate limit:** "Sync now" per connection throttled (e.g. one concurrent run; min 5-min gap) via `ConnectionSchedule.last_triggered_at` + Airbyte job-status check before triggering.

### 4.5 Frontend

| Surface | Change |
|---|---|
| `DatasetSelector`, Explore, Ingest warehouse tab, Data Quality, filters | lists auto-narrow (backend filters); 🔒 badge on restricted; empty-state "request access from your Admin" |
| Datasets (Settings → Access Mgmt) | **new** table: schema/table, owner, floor badge, shared-with; share modal (Layer 1 component) opens per row |
| Connections list (Ingest) | owner column; "Shared with you" section; Sync now button + schedule editor on owned/Edit connections; Create source/connection wizard enabled for Analysts |
| Alerts/metrics pickers | inherit the narrowed table lists automatically (same hooks) |

---

## 5. Security Review

| Concern | Assessment |
|---|---|
| Blanket read replaced, not widened | Migration backfills every existing dataset at `analysts_plus/view` — identical to today; narrowing is an explicit Admin action. New Analyst schemas start Private. |
| Chart-preview oracle closed | Authoring endpoints (payload-driven) all check `can_read_dataset`; the `has_schema_access` TODO stub is finally real. |
| Consuming unaffected | Rendering an existing chart never checks dataset access — no funder-facing regression, and no path for a viewer to *author* against the underlying table (authoring endpoints are separately gated). |
| Ownership scoping server-side | Slugs gate the route; owner-or-Edit (resolver) gates the object. An Analyst PUT on someone else's connection → 403. |
| Namespace isolation | Forced `destinationSchema` + collision check: Analyst connections can't overwrite `prod`/modeled schemas. |
| Secrets | Unchanged Airbyte secret flow; no new storage. |
| Sync abuse | Rate-limited direct sync; Celery-beat scheduler honors the same limit; Airbyte concurrency is the backstop. |
| Multi-tenant | Dataset + ConnectionMeta carry `org`; every query org-filtered; `sync_connection` verifies the connection belongs to the caller's org workspace. |
| Fail-closed default | Unknown/undiscovered schemas are Admin-only until registered. |

---

## 6. Testing Strategy

**Backend:** `can_read_dataset` truth-table (schema row / table row precedence, fail-closed unknown, owner, group grant, floor); every authoring endpoint 403s on an ungated dataset (parameterized across the ~20 endpoints — this is the key regression suite); consuming path unaffected (viewer with zero dataset grants renders a shared dashboard); connection CRUD ownership scoping; direct sync gate + rate limit; scheduler triggers due syncs once; discovery idempotency; migration backfill preserves current visibility (before/after listing identical for an Analyst).
**Frontend:** pickers show only accessible datasets; restricted empty-states; Sync now + schedule flows.
**E2E (Playwright):** Priya creates a Kobo connection end-to-end → Sync now → builds a chart on her schema → cannot see `hr_data` anywhere; Sarah locks a dataset and Priya's picker updates.

---

## 7. Milestones

#### M1: Dataset model + discovery + migration backfill (backend)
- Dataset model, discovery task, backfill all existing schemas/tables at `analysts_plus/view`, registry entries, `ResourceShare.resource_id` → 255.
- **Acceptance:** every warehouse schema has a Dataset row; an Analyst's visible surface is unchanged from today.

#### M2: Dataset enforcement across read/authoring surfaces (backend)
- `can_read_dataset` + `accessible_datasets_q`; wire all ~20 endpoints (incl. the `has_schema_access` stub and `run_chart_query` authoring context); fail-closed unknowns.
- **Acceptance:** Sarah sets `hr_data` Private → Priya's pickers omit it, direct preview 403s, her existing shared-dashboard *viewing* is unaffected.

#### M3: Dataset sharing UI (frontend)
- Datasets settings table + Layer 1 share modal on datasets; picker badges/empty-states.
- **Acceptance:** Sarah grants `kobo_survey` to the M&E group in <30s; group members' pickers update.

#### M4: Connection ownership (backend + frontend)
- ConnectionMeta upgrade + backfill; Analyst CRUD slugs (ownership-scoped); connections list = own + shared + Admin-all; connection sharing via registry.
- **Acceptance:** Priya creates a connection she can edit; she can't touch Ravi's; Sarah sees all.

#### M5: Self-serve sync — Sync now + schedule (backend + frontend)
- Forced `destinationSchema` + auto-created owned Dataset; direct-sync endpoint (`sync_connection`) + rate limit; `ConnectionSchedule` + beat tick; sync history surfaced.
- **Acceptance:** Priya's full flow — create → sync now → scheduled daily → chart on her own schema — with zero Admin involvement and zero Prefect objects created.

#### M6: Hardening + browser verification
- Parameterized 403 regression suite across all authoring endpoints; migration dry-run on a staging copy; **stop and ask the user** before a Playwright-MCP browser pass (Admin + Analyst).
- **Acceptance:** regression suite green; staging Analyst sees identical pre/post-migration surface.

---

## 8. Open Questions & Risks

1. **Dataset grant grain default:** plan supports schema- and table-level rows; recommend Admins grant at schema level by default (fewer rows, matches how NGOs think: "the Kobo data"). Confirm with Design how the picker presents the two grains.
2. **Should transform UI browsing be dataset-gated?** Plan says yes (it uses the same endpoints — free), but Analysts are read-only on Transform anyway (Spec A). Confirm no workflow breaks for analysts inspecting dbt sources they lack dataset grants on.
3. **Standalone alerts** query a table on schedule under system credentials. v1 gates only the creation-time picker. Is an alert on a later-restricted dataset acceptable (it keeps firing)? Flag to PM.
4. **Scheduler choice:** Celery beat (recommended — uniform with Layer 1's expiry task, schedule state in Django) vs flipping Airbyte's own `scheduleType`. If ops prefers Airbyte-native, M5 swaps implementations behind the same endpoint.
5. **Org-default dataset floor:** reuse Layer 1's `default_visibility_floor_*` or a separate data-plane default (`analysts_plus` recommended)? Plan assumes separate constant; confirm.
6. **Layer 1 coupling:** this plan needs Layer 1's M1–M3 merged (ResourceShare/resolver/registry/groups + share modal). If Layer 2 must start earlier, M1 here can proceed against the models alone.

---

Draft v1 saved. Review and tell me what to revise. When ready (after Layer 1 M1–M3 merge), run `/engineering/execute-plan features/access-control/dataset-access/plan.md`.
