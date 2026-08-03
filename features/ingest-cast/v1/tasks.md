# ingest-cast v1 — Task List

**Plan:** `features/ingest-cast/v1/plan.md`
**Branch:** `feature/ingest-cast`

---

## M0 — Prerequisite model changes (DDP_backend)

- [x] **M0.1** — Add `dbt_profile_secret_block` FK to `OrgWarehouse` (`ddpui/models/org.py`) + migration `0172`
- [x] **M0.2** — Dual-write block to `warehouse` in `create_or_update_dbt_profile_secret_blk()` (`dbthelpers.py:208`)
- [x] **M0.3** — Thread `warehouse_secret_block` through `pipeline_with_orgtasks()`:
  - `setup_dbt_core_task_config()` (pipelinefunctions.py:55) — add `warehouse_secret_block` param
  - `setup_edr_send_report_task_config()` (pipelinefunctions.py:220) — add `warehouse_secret_block` param
  - `pipeline_with_orgtasks()` (pipelinefunctions.py:256) — look up `OrgWarehouse` once, pass block to both setup fns
- [x] **M0.4** — Remove block deletion from dbt teardown (`dbt_service.py:253-259`)
- [x] **M0.5** — Fix org cleanup to read block from warehouse (`org_cleanup_service.py:273`)
- [x] **M0.6** — Update `patch_edr_deployment_env` management command (`patch_edr_deployment_env.py:53`)
- [x] **M0.7** — Update `backfill_dbt_profile_secret_blocks` management command (`backfill_dbt_profile_secret_blocks.py:115`)
- [x] **M0.8** — Add `post_sync_transform = models.JSONField(null=True, blank=True, default=None)` to `OrgTask` (`tasks.py`) + migration `0173`

---

## M1 — SQL generation + task config schema (DDP_backend)

- [x] **M1.1** — Add `generate_cast_sql(schema, table, column_casts)` instance method to `PostgresClient` and `BigqueryClient`
  - Postgres: `ALTER TABLE` using `self.engine.dialect.identifier_preparer` for quoting
  - BigQuery: `CREATE OR REPLACE TABLE AS SELECT`, fetches live columns via `self.get_table_columns()`
- [x] **M1.2** — Extend `PrefectAirbyteSyncTaskSetup` with `env: dict = {}` and `post_sync_ops: list = []`; update `to_json()`
- [x] **M1.3** — Update `setup_airbyte_sync_task_config()` (`pipelinefunctions.py:55`) to populate `env` + `post_sync_ops` from `org_task.post_sync_transform`
- [x] **M1.4** — Unit tests (`ddpui/tests/utils/warehouse/test_cast_sql.py`)

---

## M2 — Connection API CRUD with cast config (DDP_backend)

- [x] **M2.1** — Add `post_sync_transform: Optional[dict] = None` to `AirbyteConnectionCreate`, `AirbyteConnectionUpdate`, `AirbyteConnectionCreateResponse` (`ddpui/ddpairbyte/schema.py`)
- [x] **M2.2** — Save `post_sync_transform` on `OrgTask` in `create_connection()` (`airbytehelpers.py:264`) before `create_airbyte_deployment()` is called
- [x] **M2.3** — Save + regenerate deployment params in `update_connection()` (`airbytehelpers.py:606`)
- [x] **M2.4** — Include `post_sync_transform` in `get_one_connection()` response (`airbytehelpers.py:583`)
- [x] **M2.5** — Unit tests

---

## M3 — Prefect-proxy cast execution (prefect-proxy)

- [x] **M3.1** — Implement `_run_post_sync_ops(payload)` in `proxy/prefect_flows.py` (Postgres + BigQuery paths, both with `try/finally` for connection close)
- [x] **M3.2** — Call `_run_post_sync_ops(payload)` in `run_airbyte_connection_flow_v1()` after `run_connection_sync()`
- [x] **M3.3** — Unit tests (`proxy/tests/test_post_sync_ops.py`)

---

## M4 — Frontend cast config UI (webapp_v2)

- [x] **M4.1** — Add `cast_to_type: string | null` to `StreamColumn`; add `PostSyncOp`, `PostSyncTransform` types; add `post_sync_transform` to `Connection` (`types/connections.ts`)
- [x] **M4.2** — Add `CAST_TYPE_OPTIONS` constant (`constants/connections.ts`)
- [x] **M4.3** — Add `updateCastType` callback to `useStreamConfig`; clear cast on stream deselect + column deselect (`hooks/useStreamConfig.ts`)
- [x] **M4.4** — Add "Cast to" column in expanded stream view (`stream-config-table.tsx`)
- [x] **M4.5** — Wire up in `ConnectionForm`: hydrate on edit load, compute + send on save (`connection-form.tsx`)
