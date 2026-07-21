# Dev Sandbox — one-command local environments per feature

**What it is:** a script (`scripts/sandbox.sh`) plus a `/sandbox` skill that spin up a
complete, isolated local Dalgo environment for a new feature: git worktrees on a fresh
branch off `main`, a dedicated Postgres database with fresh migrations, its own Redis,
and both servers on their own ports.

**The problem it solves:** today all branches share one dev database. The
resource-sharing work documented the result — the shared DB became a multi-branch
migration hybrid with migration-number collisions (`features/access-control/resourcesharing/tasks.md`,
"schema drift" notes). Setting up a clean second instance by hand takes ~an hour and
five non-obvious env overrides; people skip it and pollute the shared DB instead.

**Example:** Siddhant wants to try a chart-filter UI. He types `/sandbox`, says
"chart filter UI", confirms the name `chart-filters`. Three minutes later he has
`http://localhost:3002` (frontend) talking to `http://localhost:8003` (backend) on
branch `feature/chart-filters` in both repos, logged in as
`admin@sbx-chart-filters.local`, with the shared dev stack on 8002/3001 untouched.

---

## Decisions (user-approved 2026-07-21)

| Decision | Choice |
|---|---|
| Packaging | Script does the work; skill is the conversational front door. Script usable standalone. |
| Default stack | Backend + frontend + celery worker + own redis + org/admin user. **No chat-with-data by default** — `--with-chat` flag adds the checkpointer tables. |
| Branch source | Always `origin/main`, freshly fetched. |
| Branch name | `feature/<name>` (matches repo convention). |

## Naming convention is the registry

No state file. Everything derives from the sandbox name; a small `sandbox.json`
manifest per sandbox records the assigned ports (so `list`/`destroy` don't re-probe).

| Thing | Convention | Example (`chart-filters`) |
|---|---|---|
| Sandbox dir | `.dalgo-worktrees/<name>/` | `.dalgo-worktrees/chart-filters/` |
| Branch (both repos) | `feature/<name>` | `feature/chart-filters` |
| Database | `dalgo_sbx_<name with _>` | `dalgo_sbx_chart_filters` |
| Org / login | `sbx-<name>` / `admin@sbx-<name>.local` | org `sbx-chart-filters` |
| pm2 apps | `<service>-sbx-<name>` | `django-asgi-sbx-chart-filters` |
| Ports | first free, probing up from 8003 / 3002 / 6380 | 8003, 3002, 6380 |

## What `create` does, in order

```
checks   → tools present, name free (dir, branches, DB), ports probed
worktree → DDP_backend + webapp_v2 worktrees, branch feature/<name> off origin/main
env      → cp .env/.env.test from main backend checkout, cp .env/.env.local from
           main webapp; sed-override ONLY: DBNAME, REDIS_PORT, FRONTEND_URL,
           FRONTEND_URL_V2, CORS_ALLOWED_ORIGINS (+sandbox origin),
           NEXT_PUBLIC_BACKEND_URL
deps     → uv sync --frozen (own .venv), npm ci (own node_modules)
database → CREATE DATABASE → migrate → loaddata roles/permissions/role-perms/tasks
           → createorganduser (random password, printed + stored in sandbox.json)
run      → pm2 start <sandbox>/ecosystem.config.js: redis-server, uvicorn, celery
           default worker, next dev — all on sandbox ports
verify   → poll backend until it answers, then print URLs + login + destroy hint
```

### Why each env override exists (the five traps)

| Override | Without it |
|---|---|
| `DBNAME` | Sandbox writes migrations into the shared dev DB — the exact problem this tool exists to stop |
| `REDIS_PORT` (own redis-server) | Redis DB indexes 0–4 are hardcoded in `ddpui/utils/redis_db.py`; two backends on one Redis share celery broker/beat/channels/cache and cross-talk |
| `CORS_ALLOWED_ORIGINS` | Settings default only allows :3000/:3001 — sandbox frontend gets CORS-blocked |
| `FRONTEND_URL`, `FRONTEND_URL_V2` | Deep links (emails, share links) open the main instance on :3001 (bug hit during RBAC work) |
| `NEXT_PUBLIC_BACKEND_URL` | Frontend (and its derived WebSocket URL) talks to the main backend on :8002 |

Ports are CLI flags, not env: uvicorn gets `--port`, next gets `-p` — both baked into
the generated pm2 config.

## `destroy <name>`

Mirror of create: `pm2 delete` the four apps → `DROP DATABASE ... WITH (FORCE)` (also
the `test_` twin if present) → `git worktree remove --force` both repos → remove the
sandbox dir. The branch is **kept** unless `--delete-branch` is passed — unmerged work
must not vanish with the sandbox.

## `list`

Joins the `sandbox.json` manifests with live port checks: name, ports, DB, running or
stopped, path.

## Flags

| Flag | Effect |
|---|---|
| `--with-chat` | Also runs `chat_with_data_setup` (LangGraph checkpointer tables) and prints the remaining manual steps (connect warehouse in UI, load `seed/warehouse/test_ngo_seed.sql` into the warehouse DB, enable the feature flag) |
| `--delete-branch` (destroy) | Also deletes `feature/<name>` in both repos |

## Out of scope for v1

- prefect-proxy / airbyte / superset — shared infra; pipeline endpoints simply won't
  work inside a sandbox (server boots fine without them — verified: `PREFECT_PROXY_API_URL`
  is only read per-request, never at startup)
- Template-DB instant cloning (`CREATE DATABASE ... TEMPLATE`) — add if the ~2-min
  migrate ever feels slow
- Automatic warehouse attachment for `--with-chat`

## Safety rules

- The script **copies** `.env` files with `cp` and edits them with `sed` — secret
  values never pass through Claude or appear in output.
- Never touches the main checkouts' `.venv`, DB, or pm2 apps; sandbox pm2 apps are
  namespaced `*-sbx-<name>` and managed only by name (never by PID).
- `create` aborts if any name/branch/DB collision exists; a failed half-create is
  cleaned up with `destroy <name>`.
