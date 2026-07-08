# Research — Dataset Access + Self-Service Connections (Layer 2)

**For:** `features/access-control/dataset-access/plan.md`
**Date:** 2026-07-02 · **Branch read:** `feature/rbac` (DDP_backend + webapp_v2)
**Scope:** net-new findings only. Layer 1 spine (ResourceShare, resolver, registry) is in `../resourcesharing/research.md` + `../resourcesharing/plan.md`.

Acronyms: FK (foreign key) · dbt (the transform tool) · RLS (row/column security — Layer 3).

---

## 1. There is no "Connection" Django model — and no ownership anywhere in the data section

**The rule:** Airbyte sources/connections live in Airbyte; Django keeps only satellite metadata keyed by the Airbyte connection UUID (a 36-char string).
**Evidence:**
- `ConnectionMeta` (`models/org.py:305`) — just `connection_id` + `connection_name`. **No org, no created_by.**
- `OrgTask` (`models/tasks.py:87`) — the real per-connection anchor: `org` FK + `connection_id` string + task slug (`airbyte-sync`/`airbyte-clear`). No user FK.
- `OrgDataFlowv1` (`models/org.py:276`) — Prefect deployment wrapper (`manual` | `orchestrate`), carries the cron.
**Why it matters:** connection ownership needs a place to live. Plan: upgrade `ConnectionMeta` (add `org`, `owner`, floor fields), backfilled from `OrgTask`. And Layer 1's `ResourceShare.resource_id` being a **CharField** is what lets `resource_type="connection"` use the UUID directly — but see §6 (length).

## 2. Analysts hold zero data-section write slugs today

From `seed/003_role_permissions.json`: `can_create/edit/delete_source`, `can_create/edit/delete_connection`, `can_run_pipeline`, `can_run_orgtask` — **admin + super-admin only**. Analyst holds only view slugs (45 total, all read). Self-service = granting Analysts the connection write slugs + **ownership-scoping them in the service layer** (an Analyst edits/deletes/syncs only connections they own or hold Edit on).

## 3. Sync today is Prefect-only — but the direct-sync function already exists, unused

- Connections are created with Airbyte `scheduleType: "manual"` (`airbyte_service.py:757`); scheduling = putting the sync OrgTask into an `orchestrate` dataflow (a pipeline).
- Manual "Sync now" today = trigger the connection's `manual` Prefect deployment (`pipeline_api.py:173`, gated `can_run_pipeline` — which Analysts lack).
- **`airbyte_service.sync_connection(workspace_id, connection_id)` → `abreq("connections/sync")` (`airbyte_service.py:971`) exists and is referenced only by tests.** This is the exact hook for a Prefect-free, owner-gated "Sync now."
- No non-Prefect *scheduled* path exists. Options: flip the Airbyte connection's own `scheduleType` to cron, or a Celery-beat tick that calls `sync_connection` for due connections. (Plan recommends Celery beat — keeps schedule state in Django, uniform with invite-expiry pattern, and Airbyte job telemetry still lands in `AirbyteJob`/`SyncStats`.)

## 4. Warehouse namespace isolation is a per-connection knob that already exists

`AirbyteConnectionCreate.destinationSchema` (`ddpairbyte/schema.py:68`) switches the connection to `namespaceDefinition="customformat"` (`airbyte_service.py:753-763`). **This is the isolation mechanism:** an Analyst-created connection writes to a dedicated schema (e.g. `raw_priya_kobo`), which becomes a Dataset they own.

## 5. Every warehouse-touching surface (the enforcement map for dataset grants)

One flat slug — `can_view_warehouse_data` — gates the browse/query surfaces, org-wide. The full enforcement map:

| Surface | File | Endpoints | Gated by |
|---|---|---|---|
| Warehouse browse/query | `api/warehouse_api.py` | 12: schemas :57, tables :50, columns :64, column-values :73, table_data :134/:194, count :158, CSV download :256, insights :222, LLM ask :320, sync_tables :513 | `can_view_warehouse_data` |
| Filters | `api/filter_api.py` | 4: schemas :60, tables :107, columns :154, preview :208 | `can_view_warehouse_data` |
| Transform datatypes | `api/transform_api.py:210` | 1 | `can_view_warehouse_data` |
| **Chart authoring/query** | `api/charts_api.py` | chart-data :492, preview :537, total-rows :644, `{id}/data` :1028, map-data :817, CSV :950 | **`can_view_charts`** (content slug!) |
| **Metric validate/preview** | `api/metric_api.py` | validate :124, preview :223 | `can_create_metrics` / `can_view_metrics` |
| KPI aggregates | `api/kpi_api.py` + `kpi_service` | — | `can_view_kpis` |

**The catch:** chart/metric/KPI endpoints execute warehouse SQL under *content* slugs. A dataset grant enforced only in `warehouse_api` leaves the chart-preview path as a full-warehouse oracle.

**The stub that was waiting for us:** `charts_api.py:has_schema_access(request, schema_name)` (:111) — currently `return True` with `# TODO: Implement proper schema access control`.

**Chart query choke point:** every chart-data endpoint funnels through `generate_chart_data_and_config` (`charts_api.py:142`) → `charts_service.execute_chart_query` (:937) / `execute_query` (:877). This is where Layer 1's `run_chart_query` seam lands.

**Authoring vs consuming split (maps cleanly to endpoint shape):** payload-driven endpoints (client sends `schema_name`/`table_name` — chart-data-preview, filters preview, metric validate) are **authoring** → dataset-gated. `chart_id`-driven endpoints (render an existing chart) are **consuming** → gated by the chart's Layer 1 access, NOT the viewer's dataset access.

## 6. "Dataset" today: no backend entity; the frontend already uses the word

- Backend: everything is `schema_name` + `table_name` string pairs (Chart, Metric, filters). Only a display label `f"{schema}.{table}"` in alerts.
- Frontend: `components/charts/DatasetSelector.tsx` — "Search datasets…", value `${schema}.${table}`. The chart builder, Explore (`components/explore/`), Ingest "Your Warehouse" tab, and Data Quality all browse via `hooks/api/useWarehouse.ts` (which hits `/sync_tables` etc.).
- dbt runs with **org-level warehouse credentials** (`dbtautomation_service._get_wclient` :363) — independent of the requesting user. Dataset grants therefore do NOT constrain dbt runs (a privileged process), only user-facing browse/query/authoring.
- **Length note for Layer 1's model:** dataset keys are `schema` or `schema.table`; Postgres identifiers are 63 bytes each, so a key can reach ~127 chars. `ResourceShare.resource_id` must be **CharField(255)**, not 64. (Flagged back to the Layer 1 plan.)

## 7. Migration reality (how to not break existing orgs)

Today every Analyst reads everything. Flipping to deny-by-default would break every chart builder overnight. Non-breaking path: at migration, every discovered dataset gets **floor = analysts_plus / view** (preserves today's behavior exactly); Admins then narrow specific datasets (HR, salary) to Private/grants. New Analyst-created connection datasets start at **private** (owner + Admin only). "Replace blanket read" thus happens by *narrowing*, not by a breaking cutover.
