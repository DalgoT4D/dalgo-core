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

---

## M5 — Connection-block-based architecture revision

Pivot away from deployment-param-embedded SQL. See plan `Architecture Revision — Nov 2026 (M5)` section.

### M5.1 — `prefect-airbyte` package (Dalgo fork)

- [x] Add `extra: Dict[str, Any] = Field(default_factory=dict, ...)` to `AirbyteConnection` in `prefect_airbyte/connections.py`
- [x] Update class docstring to mention `extra`
- [x] Push to `github.com/Ishankoradia/prefect-airbyte` on `feature/ingest-cast` branch
- [x] Update `prefect-proxy/pyproject.toml` to consume the branch (`branch = "feature/ingest-cast"`) + `uv sync`
- [ ] Tag a release (e.g. `v0.91`) once merged to main and repin

### M5.2 — prefect-proxy: block upsert + flow refactor

- [x] Extend `AirbyteConnectionCreate` schema with `connectionName` + `extra` (`proxy/schemas.py`)
- [x] Replace stubbed `update_airbyte_connection_block` with `upsert_airbyte_connection_block` in `proxy/service.py`
- [x] Add `PUT /proxy/blocks/airbyte/connection/` endpoint in `proxy/main.py`
- [x] Rewrite `run_airbyte_connection_flow_v1` to async, load block via `AirbyteConnection.aload(connection_id)`, fall back to inline on `ValueError`
- [x] Update `_run_task_runner` to `asyncio.run(run_airbyte_connection_flow_v1(...))`
- [x] Decorate `_run_post_sync_ops` as `@task(name="post-sync-ops", retries=0)` — visible in UI
- [x] Use `get_run_logger()` in both flow + task for logs to surface in Prefect UI
- [ ] Push to git + restart prefect-proxy + prefect workers

### M5.3 — DDP_backend: block upsert on connection save

- [x] Remove `env` + `post_sync_ops` from `PrefectAirbyteSyncTaskSetup` (+`to_json()`) — `ddpui/ddpprefect/schema.py`
- [x] Extract SQL-gen into `build_connection_block_extra(org_task)` helper — `ddpui/core/pipelinefunctions.py`
- [x] Simplify `setup_airbyte_sync_task_config` (drop SQL gen path)
- [x] Add `upsert_airbyte_connection_block(...)` helper — `ddpui/ddpprefect/prefect_service.py`
- [x] `airbytehelpers.create_connection` — call `upsert_airbyte_connection_block` when `post_sync_transform` is set
- [x] `airbytehelpers.update_connection` — delete buggy multi-pipeline deployment-params rewrite; replace with `upsert_airbyte_connection_block` call
- [x] Use `connection.get("name", "")` (safer than `connection["name"]`) for the block name
- [x] Rewrite `BigqueryClient.generate_cast_sql` to use `SELECT * REPLACE(...)` — no `get_table_columns()` call needed
- [x] Airbyte Destinations V2 column normalization: `re.sub(r"[^a-zA-Z0-9_$]", "_", col)` in both Postgres + BigQuery clients

### M5.4 — Test updates

- [x] `test_airbytehelpers.py` — update `test_create_connection_saves_post_sync_transform` + `test_update_connection_saves_post_sync_transform` to mock/assert `upsert_airbyte_connection_block`
- [x] Add `test_create_connection_no_transform_skips_upsert`
- [x] `test_cast_sql.py` — rewrite BigQuery tests to match `SELECT * REPLACE` output; add column-normalization test
- [x] `test_service.py` — drop obsolete `update_airbyte_connection_block` stubs; add tests for `upsert_airbyte_connection_block` (happy, missing server block, save failure, invalid payload)
- [x] `test_main.py` — add tests for `PUT /proxy/blocks/airbyte/connection/`
- [x] `test_post_sync_ops.py` — convert all tests to async + `AsyncMock` for `Secret.aload`
- [x] All prefect-proxy tests green (247 passed)
- [x] All DDP_backend tests green (2214 passed, excluding pre-existing GitHub-API integration test failures)

### M5.5 — Move SQL generation to prefect-proxy (2nd revision — Nov 2026)

**Why:** BigQuery `CREATE OR REPLACE TABLE` needs to preserve Airbyte's partition/cluster spec, which we can only discover at flow-run time via `bq_client.get_table(...)`. Rather than baking half-a-solution into the backend, move all SQL generation to the proxy — closer to execution, always fresh, uses live warehouse metadata.

**Backend changes:**
- [ ] `build_connection_block_extra` — stop calling `generate_cast_sql`; store raw config `{type, schema, table, column_casts}` in each op
- [ ] Delete `generate_cast_sql` from `PostgresClient` and `BigqueryClient`
- [ ] Delete `POSTGRES_CAST_TYPE_MAP` and `BIGQUERY_CAST_TYPE_MAP` constants
- [ ] Delete `ddpui/tests/utils/warehouse/test_cast_sql.py`
- [ ] Update `test_airbytehelpers.py` — assert new `extra` shape

**prefect-proxy changes:**
- [ ] Add type maps + `_normalize_column_name` helper (`proxy/prefect_flows_runner.py` or new `proxy/cast_sql.py`)
- [ ] Rewrite `_run_post_sync_ops` — dispatch by `wtype` (from secret block):
  - Postgres path: build ALTER TABLE from op config, execute
  - BigQuery path: `bq_client.get_table()` → build `CREATE OR REPLACE TABLE ... PARTITION BY ... CLUSTER BY ... AS SELECT * REPLACE (...)`, execute
- [ ] Update `test_post_sync_ops.py` — mock `bq_client.get_table()` for BigQuery path, verify SQL structure includes partitioning/clustering

### M5.6 — Deploy + verify

- [ ] Push all changes to `feature/ingest-cast` (DDP_backend, prefect-proxy, prefect-airbyte)
- [ ] Restart Django (`pm2 restart django-backend-asgi-ingest-cast`)
- [ ] Restart prefect-proxy (`pm2 restart prefect-proxy-ingest-cast`)
- [ ] Restart prefect workers (`pm2 restart prefect-worker-ddp-1-ingest-cast prefect-worker-ddp-2-ingest-cast`)
- [ ] Save a connection with cast config → verify block created in Prefect UI with `extra` populated
- [ ] Trigger a sync → verify post-sync-ops task appears in graph with logs, column type changes in warehouse
- [ ] Update the connection's casts → verify block's `extra` updated on next sync
- [ ] Same connection in a multi-task pipeline → verify no other tasks are affected
- [ ] BigQuery: partitioned & clustered raw table → cast succeeds, partition/cluster spec preserved
