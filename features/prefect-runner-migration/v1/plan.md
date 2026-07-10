# Migrate Dalgo dbt execution off `DbtCoreOperation`

## Context

Prefect has deprecated `DbtCliProfile` and `DbtCoreOperation` — the two blocks Dalgo's dbt execution currently hangs off. We move dbt execution to `PrefectDbtRunner` (the supported replacement, from `prefect_dbt`), with warehouse credentials sourced from a Prefect `Secret` block at flow-run start.

**Version alignment (prerequisite).** `PrefectDbtRunner` uses dbt-core as a Python library from the worker process's Python env, so all orgs converge onto one dbt-core version. Target line: **`dbt-core==1.10.19`** (matches the `dbt-1.10.19` venv already baked into `Dockerfile.prefect-job-runner`), paired with `dbt-postgres==1.10.2` and `dbt-bigquery==1.10.3`. Every client's dbt project must be bumped to this line before rollout — owned outside this plan.

**What this migration gains vs today:**
- Per-node Prefect UI tasks: each dbt model / test / seed shows up as its own task with duration + logs (today's `DbtCoreOperation` bundles everything into one task).
- One dbt install in the worker image instead of three per-version venvs — image gets simpler over time.
- Off the deprecated block APIs.

The migration is additive:
- Old code (`prefect_flows.py`, `_create_dbt_cli_profile`, `DbtCliProfile` blocks) stays in place. Nothing gets deleted.
- A **new flow file** in `prefect-proxy` defines `PrefectDbtRunner`-based equivalents. Existing deployments keep working against the old file.
- Cutover is a Prefect DB script (owned separately, out of scope) that rewrites a deployment's `entrypoint` from the old flow to the new one. Rollback = reverse the script.
- Warehouse credentials move to **Prefect `Secret` blocks** (matches branch name `feature/prefect-secret-blk`). **One Secret block per warehouse; the entire credentials dict is stored JSON-encoded inside it.**
- **No org-level flag.** Backend always writes both sets of artifacts (new Secret block **and** old `DbtCliProfile` block) on every warehouse-cred write. DB rollback of a deployment's entrypoint is always safe — whichever flow file is active finds fresh state.
- **All profile building lives in prefect-proxy.** Django never sees `profiles.yml`, never templates it, never writes it. The new flow reads the Secret block at flow-run start, builds a resolved profile dict in memory, dumps it to `<project_dir>/profiles/profiles.yml`, then calls `PrefectDbtRunner.invoke(argv)`. Ephemeral on EKS pods; idempotent overwrite on persistent workers.

Launch scope: **Postgres + BigQuery** (mirrors today's `WarehouseFactory`). Snowflake deferred.

## Implementation order

Do the version pinning first, sanity-check it locally, then start on the runner integration. Same branch, one PR — this is just the sequence to reduce debugging surface later.

### Step 1: Move the runner Dockerfile to prefect-proxy

The Prefect worker image belongs with prefect-proxy, not DDP_backend. Move:

```
DDP_backend/dbt_deps/Dockerfile.prefect-job-runner  →  prefect-proxy/docker/Dockerfile.job-runner
DDP_backend/dbt_deps/dbt-1.8.7/                      →  prefect-proxy/docker/dbt-1.8.7/
DDP_backend/dbt_deps/dbt-1.9.8/                      →  prefect-proxy/docker/dbt-1.9.8/
DDP_backend/dbt_deps/dbt-1.10.19/                    →  prefect-proxy/docker/dbt-1.10.19/
DDP_backend/dbt_deps/README.md                       →  prefect-proxy/docker/README.md
```

Use `git mv` so history follows. Then:
- Update `DDP_backend/README.md:148-160` — swap the `cd dbt_deps/dbt-1.*/` snippets for the new paths (or delete if the docs belong with the moved README).
- Update `prefect-proxy/docker/README.md` — its "From the dbt_deps directory" build-instruction paths, and the image-tag/build-arg examples.

### Step 2: Lock versions

**`prefect-proxy/pyproject.toml`** — add explicit pins:
```toml
"dbt-core==1.10.19",
"dbt-postgres==1.10.2",
"dbt-bigquery==1.10.3",
```
`prefect-dbt==0.7.24` stays (its `dbt-core>=1.7.0` constraint has no upper bound — the explicit pin is what stops it from resolving to latest). Run `uv sync` to regenerate `uv.lock`.

**`prefect-proxy/docker/Dockerfile.job-runner`** (new path) — line 39 currently pip-installs `prefect-dbt[bigquery,postgres]==${PREFECT_DBT_VERSION}`, which pulls whatever `dbt-core` is latest at build time. Pin explicitly + drop the extras (redundant with the explicit adapter pins):
```dockerfile
RUN pip install --no-cache-dir \
    "prefect==${PREFECT_VERSION}" \
    "prefect-dbt==${PREFECT_DBT_VERSION}" \
    "prefect-shell==${PREFECT_SHELL_VERSION}" \
    "prefect-airbyte @ git+https://github.com/Ishankoradia/prefect-airbyte.git@${PREFECT_AIRBYTE_REF}" \
    "dbt-core==1.10.19" \
    "dbt-postgres==1.10.2" \
    "dbt-bigquery==1.10.3"
```

Leave the per-version venvs (`/home/ddp/dbt/venv`, `venv-1.9.8`, `venv-1.10.19`), `requirements_dbt.txt`, and `elementary-data==0.15.1` alone — retirement is a follow-up after v1 lands.

### Step 3: Sanity-check the lock

Local — make sure `prefect-dbt` didn't sneak a newer `dbt-core` in via the transitive:
```bash
cd prefect-proxy && rm -rf .venv && uv sync
.venv/bin/python -c "
import dbt.version
from dbt.adapters import postgres, bigquery
import importlib.metadata as m
print('dbt-core:', dbt.version.__version__)
print('dbt-postgres:', m.version('dbt-postgres'))
print('dbt-bigquery:', m.version('dbt-bigquery'))
print('prefect-dbt:', m.version('prefect-dbt'))
"
```
Expect exactly `1.10.19 / 1.10.2 / 1.10.3 / 0.7.24`.

Image — same check inside the built runner image:
```bash
docker build -f prefect-proxy/docker/Dockerfile.job-runner -t dalgo-runner:test prefect-proxy/docker
docker run --rm dalgo-runner:test python -c "import dbt.version; print(dbt.version.__version__)"
```
Expect `1.10.19`.

If either version drifts, the pin isn't taking — fix before continuing.

### Step 4: Runner integration

Everything in the sections below.

---

## Runner integration

### 1. New flow file in prefect-proxy

Create `prefect-proxy/proxy/prefect_flows_runner.py` alongside the existing `prefect_flows.py`. Re-import unchanged task functions (`shellopjob`, `run_airbyte_connection_flow_v1`, `dbtcloudjob_v1`) from the old file — do not duplicate them.

Define:

- **`dbtjob_v2_runner(task_config, task_slug)`** — replaces `dbtjob_v1` (`prefect_flows.py:181-232`). Body sketch:
  ```python
  import shlex, json, yaml
  from pathlib import Path
  from prefect.blocks.system import Secret
  from prefect_dbt import PrefectDbtRunner, PrefectDbtSettings

  env = task_config["env"]
  block_value = json.loads(Secret.load(env["warehouse-secret-block-name"]).get())
  creds = block_value["creds"]
  extras = block_value.get("extras", {})

  # profiles.yml has exactly one output. Target label is a fixed constant
  # ("default") on the runner side. `schema` in the output is OrgDbt.default_schema,
  # sent as env["default-schema"].
  TARGET = "default"
  profile_dict = build_profile_dict(
      wtype=env["wtype"],                 # "postgres" | "bigquery"
      target=TARGET,
      schema=env["default-schema"],       # = OrgDbt.default_schema
      creds=creds,
      extras=extras,
      threads=4,                          # hardcoded, matches current behavior
  )

  profiles_dir = Path(task_config["profiles_dir"])
  profiles_dir.mkdir(parents=True, exist_ok=True)
  (profiles_dir / "profiles.yml").write_text(yaml.safe_dump(profile_dict))

  # If postgres SSL cert content is present in extras, write it next to
  # profiles.yml and point the sslrootcert path in profile_dict at it.

  # task_config["commands"][i] is e.g. "/data/dbt_venv/<org>/bin/dbt run --full-refresh".
  # PrefectDbtRunner uses the worker's own dbt-core Python API — the binary path
  # is ignored. Split, drop the first token (binary), and dbt subcommand (e.g.
  # "run") plus any flags become argv for .invoke().
  runner = PrefectDbtRunner(settings=PrefectDbtSettings(
      project_dir=task_config["project_dir"],
      profiles_dir=str(profiles_dir),
  ))
  for cmd in task_config["commands"]:
      argv = shlex.split(cmd)[1:]   # drop the leading dbt-binary path
      try:
          runner.invoke(argv)
      except Exception:
          if task_config["slug"] == "dbt-test":
              return State(
                  type=StateType.COMPLETED,
                  name="DBT_TEST_FAILED",
                  message="WARNING: dbt test failed",
              )
          raise
  ```
  Keep the `_retry_if_short_runtime` decorator verbatim from `dbtjob_v1`. **Per-node observability**: each dbt node (model / test / seed) automatically becomes its own Prefect task inside the flow-run graph.
- **`_run_task_runner(task_config)`** — copy of `_run_task` (`prefect_flows.py:366`) with the `DBTCORE` branch dispatching to `dbtjob_v2_runner`. Other branches re-dispatch to the originals.
- **`deployment_schedule_flow_v5(config, ...)`** — copy of the latest `deployment_schedule_flow_v4` calling `_run_task_runner`. This is the entrypoint the DB cutover script will point deployments at: `proxy/prefect_flows_runner.py:deployment_schedule_flow_v5`.

**`build_profile_dict` helper** lives in the same file (or a small `proxy/dbt_profile.py`). Postgres and BigQuery branches. Reuses the same field mapping already encoded in `_create_dbt_cli_profile` (`service.py:341-387`) — extract to a small pure function that both call sites can share. BQ's `keyfile_json` = the creds dict itself.

**Imports needed in the new flow file:** `prefect.blocks.system.Secret`, `prefect_dbt.PrefectDbtRunner` + `PrefectDbtSettings`, and stdlib (`shlex`, `json`, `pathlib`, `yaml`).

### 2. Warehouse Secret block

**Django side:**
- Add `OrgWarehouse.secret_block = ForeignKey(OrgPrefectBlockv1, null=True, on_delete=SET_NULL, related_name="+")`. Mirrors the existing `OrgDbt.cli_profile_block` pattern. One Django migration. Nullable so existing rows migrate cleanly; populated on next cred write.
- Prefect block name: `dalgo-wh-<org.slug>` (deterministic; the FK is source of truth, the name is for humans).
- On warehouse cred write, backend calls a new prefect-proxy endpoint with `{name, creds, extras}`; prefect-proxy JSON-encodes `{"creds": ..., "extras": ...}` and upserts a Secret block, returns `(block_id, block_name)`. Backend upserts the `OrgPrefectBlockv1` row and sets `OrgWarehouse.secret_block`.

**Secret block value shape** (JSON-encoded string):
```json
{
  "creds":  { ... full airbyte destination spec creds ... },
  "extras": { ... bq: {"location": "...", "priority": "..."};
                   pg: {"sslrootcert_content": "..."} ... }
}
```
One source of truth per warehouse. Runner reads one block and has everything it needs to shape the profile dict.

**Warehouse Secret block lifecycle** (every path that touches `OrgWarehouse.credentials` must handle the Secret block too):

| Event | Backend path | Secret block action |
|---|---|---|
| Create warehouse | `airbytehelpers.create_warehouse` (`airbytehelpers.py:873`, after `save_warehouse_credentials`) | Create the Secret block, create `OrgPrefectBlockv1` row, set `OrgWarehouse.secret_block` FK |
| Update warehouse creds | `airbytehelpers.update_destination` (`airbytehelpers.py:779`, after `update_warehouse_credentials`) + `airbytehelpers.py:783` (`create_or_update_org_cli_block`) | Update the Secret block value in place (same block name) |
| Update via management CLI | `management/commands/addparamstodbtcliprofile.py:54` | Update the Secret block value in place |
| Delete warehouse | `services/org_cleanup_service.py:delete_warehouse:251` (after `delete_warehouse_credentials`) | Delete the Secret block, delete the `OrgPrefectBlockv1` row (FK nulled by SET_NULL) |
| Delete dbt workspace | `ddpdbt/dbt_service.py:delete_dbt_workspace:222,232` (currently deletes `DbtCliProfile` block) | **No action here** — the Secret block belongs to the warehouse, not the dbt workspace. Leave it for `delete_warehouse` to clean up. |
| Test-connection endpoints | `airbyte_api.py:305, 322` (check_connection, check_connection_for_update) | **No action** — these don't persist to `OrgWarehouse`. |

`extras` for the block value are built in the backend from the same fields today's code passes to `_create_dbt_cli_profile` (bq location/priority; pg SSL bits).

**prefect-proxy helpers** (in `proxy/service.py`):
- `create_or_update_warehouse_secret_block(name, creds, extras)` — thin wrapper around the existing `upsert_secret_block` path (`service.py:515-544`). JSON-encodes `{"creds": creds, "extras": extras}` and stores in the Secret block's value.
- `delete_warehouse_secret_block(name)` — wraps the existing block-delete path. Called from `delete_warehouse`.

**Leave `_create_dbt_cli_profile` (service.py:341) untouched.** Backend continues to write the CLI profile block on every warehouse-cred write, guaranteeing safe DB rollback of the entrypoint. Same for `delete_dbt_cli_profile_block` — old cleanup path is untouched.

### 3. task_config shape for `DBTCORE` tasks

**No new top-level fields.** The emitter (`ddpui/core/pipelinefunctions.py:setup_dbt_core_task_config`) keeps sending the same shape it does today, plus three keys populated inside `env` (which was previously `{}` for DBTCORE tasks).

```python
{
  "type": "DBTCORE",
  "slug": "dbt-run",
  "seq": 1,

  # unchanged from today
  "commands": ["/venv/bin/dbt run --full-refresh --select my_model"],
  "working_dir": "...",
  "project_dir": "...",
  "profiles_dir": "...",

  # env was {} for DBTCORE today; now populated for the runner
  "env": {
    "warehouse-secret-block-name": "dalgo-wh-<slug>",  # from OrgWarehouse.secret_block.block_name
    "wtype": "postgres",                      # or "bigquery"; from OrgWarehouse.wtype
    "default-schema": "<OrgDbt.default_schema>",     # goes into outputs.<target>.schema in profiles.yml
  },

  # kept as-is so old flow still works after a rollback (runner ignores it)
  "cli_profile_block": "<name>"
}
```

**Verified against backend code:**
- `commands` today are shell strings that prepend the dbt binary path (`pipelinefunctions.py:setup_dbt_core_task_config` builds `f"{dbt_binary} {org_task.get_task_parameters()}"`). They never carry `--target`. The runner `shlex.split`s each string and drops the first token (the binary path is irrelevant — `PrefectDbtRunner` uses the worker's own dbt-core). Remaining tokens (e.g. `["run", "--full-refresh"]`) become `argv` for `runner.invoke()`. `--profiles-dir` / `--project-dir` are configured on `PrefectDbtSettings`, not appended to argv.
- `schema` in the profile output is `OrgDbt.default_schema` (`org.py:94`).
- `target` is not sent — it's a fixed constant (`"default"`) inside the runner. profiles.yml has exactly one output; dbt picks it via the `target:` field. Django doesn't need to care.
- `threads` is not sent — hardcoded to 4 inside the runner (matches today's behavior).

**No `commands_argv` field, no top-level `wtype`/`target`/`schema`/`threads`/`extras` fields.** The Django emitter's change is minimal: populate three keys in `env`. Everything else the runner needs it derives from the Secret block value.

### 4. What stays untouched on the Django side

- `dbt_service.py` — **no changes.** Manifest generation continues to use the CLI profile block, which backend keeps writing. No temp-dir profile logic, no new helpers.
- `dbtfunctions.py` — no new helpers. `map_airbyte_destination_spec_to_dbtcli_profile` unchanged.
- `DbtProjectManager` — unchanged.
- Elementary integration — stays on the old CLI-block path. If it ever needs to run on a runner-mode deployment, it migrates separately.
- `prefect_flows.py`, `_create_dbt_cli_profile`, `DbtCliProfile` block creation — all preserved.

## Critical files

- `prefect-proxy/pyproject.toml` — pin `dbt-core==1.10.19`, `dbt-postgres==1.10.2`, `dbt-bigquery==1.10.3`; then `uv sync` + regenerate `uv.lock`
- `prefect-proxy/proxy/prefect_flows_runner.py` *(new)* — `dbtjob_v2_runner`, `_run_task_runner`, `deployment_schedule_flow_v5`, `build_profile_dict`
- `prefect-proxy/proxy/service.py` — add `create_or_update_warehouse_secret_block` and `delete_warehouse_secret_block` + route handlers that Django calls
- `prefect-proxy/docker/Dockerfile.job-runner` *(moved from `DDP_backend/dbt_deps/Dockerfile.prefect-job-runner` with `git mv`)* — line 39: pin `dbt-core==1.10.19`, `dbt-postgres==1.10.2`, `dbt-bigquery==1.10.3` in the base env; drop the `[bigquery,postgres]` extras
- `prefect-proxy/docker/dbt-1.{8.7,9.8,10.19}/` *(moved from `DDP_backend/dbt_deps/`)* — venv build-sources, unchanged
- `prefect-proxy/docker/README.md` *(moved from `DDP_backend/dbt_deps/README.md`)* — update build-command paths to reference the new location
- `DDP_backend/README.md:148-160` — swap the `cd dbt_deps/dbt-*/` snippets to point at the new prefect-proxy path (or delete if the moved README covers it)
- `DDP_backend/ddpui/ddpairbyte/airbytehelpers.py` — mirror `{creds, extras}` to Prefect Secret block in `create_warehouse` and `update_destination`
- `DDP_backend/ddpui/services/org_cleanup_service.py` — delete Secret block in `delete_warehouse` after `delete_warehouse_credentials`
- `DDP_backend/ddpui/management/commands/addparamstodbtcliprofile.py` — also update Secret block alongside the existing CLI-profile-block update
- `DDP_backend/ddpui/models/org.py` — add `OrgWarehouse.secret_block: FK(OrgPrefectBlockv1, null=True)` + Django migration
- `DDP_backend/ddpui/core/pipelinefunctions.py` — `setup_dbt_core_task_config` populates `env` with `warehouse-secret-block-name`, `wtype`, `default-schema` (was `env={}`)

## Verification (local, single test org)

1. Trigger warehouse re-save from UI → confirm (a) Prefect `Secret` block `dalgo-wh-<slug>` exists and its value round-trips through `json.loads` back to the creds dict; (b) `OrgWarehouse.secret_block` FK is populated; (c) the old `DbtCliProfile` block is still being written (regression check).
2. Create a deployment normally (lands on old `deployment_schedule_flow_v4`). Run the Prefect DB script to switch its `entrypoint` to `proxy/prefect_flows_runner.py:deployment_schedule_flow_v5`.
3. Trigger the deployment on an EKS work pool. In the Prefect UI, confirm `profiles.yml` was written on the pod, `PrefectDbtRunner.invoke(["run"])` executed, and **each dbt node appears as its own Prefect task** in the flow-run graph (per-node observability upgrade). Check the warehouse for the expected table.
4. Rotate the Prefect Secret block value; re-run the deployment; confirm the new password is picked up without redeploying.
5. Repeat 2–4 for a BigQuery org.
6. **Rollback regression**: DB-script the entrypoint back to `deployment_schedule_flow_v4`. Trigger the deployment. Confirm it runs against the still-fresh `DbtCliProfile` block — unchanged behavior.

## Open items to confirm before implementation

- **Client dbt-project bumps to 1.10.19** — every org's dbt project must be validated and bumped to compile cleanly against `dbt-core==1.10.19` before their deployment entrypoint gets flipped. Owned outside this plan but blocks per-org cutover. Coordinate with client onboarding.
- **argv splitter** — the runner does `shlex.split(cmd)[1:]` on each stored command. Grep production `Task.command` values + `OrgTask.parameters` once to confirm no unusual shell metacharacters or `--vars '{...}'`-style quoting confuses `shlex.split`.
- **SSL cert on postgres** — cert content travels inside the Secret block's `extras` (e.g. `extras.sslrootcert_content`). `dbtjob_v2_runner` writes it to disk next to `profiles.yml` at flow-run start and points the `sslrootcert` field in the profile dict at that path. Confirm today's field name (`sslrootcert_content`) is what backend actually stores.
- **Retire the multi-venv `Dockerfile.prefect-job-runner` layout** *(follow-up, not v1)* — once all orgs are on `1.10.19` and Django's manifest generation is switched to use the base env's dbt, remove the `venv`, `venv-1.9.8`, `venv-1.10.19` builds and the corresponding `COPY dbt-1.*/` steps. Not blocking for v1 rollout.
- **Elementary compatibility** — Elementary orgs stay on the old CLI-block path for v1 (per Section 4). When they migrate later:
  - Pin `elementary-data==0.22.0`. Verified: installs cleanly alongside `dbt-core==1.10.19` + `dbt-postgres==1.10.2` + `dbt-bigquery==1.10.3` (no pip resolver conflicts), and `edr` CLI + `elementary.monitor.cli` module import + run. Elementary's declared `dbt-core<2.0.0,>=0.20` bound at `0.22.0` is loose, but the install/import combo works.
  - **Still needs one round of runtime validation** — run `edr send-report` end-to-end against a real 1.10.19-generated dbt project before shipping.
  - Bump in `prefect-proxy/requirements_dbt.txt` (from `0.15.1`) and correspondingly in the runner Dockerfile if we move edr into the base env.
  - Each client's `packages.yml` (Elementary dbt package `elementary/elementary`) needs a matching bump — client-side coordination, not this plan.
  - Not blocking v1 rollout for non-Elementary orgs.
