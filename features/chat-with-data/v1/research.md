# Chat with Data v1 — Research

**Date:** 2026-07-04
**Spec:** [v1 spec](./spec.md)
**Companion:** [plan.md](./plan.md)

Net-new findings only. Backend/frontend patterns already mapped by prior research are
referenced, not repeated: see `features/alerts/v1/research.md` (permission migrations,
Ninja API/schema/service layout, nav patterns, SWR hooks, toasts) and
`features/access-control/dataset-access/research.md` (the full map of every
warehouse-touching endpoint and its permission slug).

> **Note for harness maintainers:** the plan-feature command says to read
> `.claude/skills/backend-architecture/landmarks.md` and
> `.claude/skills/frontend-architecture/landmarks.md` — neither skill exists in
> `dalgo-core` today. Prior feature research filled the gap.

Acronyms: LLM (large language model) · AST (abstract syntax tree — the parsed structure
of a query) · WS (WebSocket) · ORM (Django's database layer) · JWT (login token) ·
RBAC (role-based access control).

---

## 1. Codebase findings (DDP_backend)

### 1.1 WebSocket infrastructure exists but is sync-only

**The finding:** `ddpui/websockets/__init__.py` has `BaseConsumer(WebsocketConsumer)` —
JWT auth reading the `access_token` httpOnly cookie (query-string `token` is a
deprecated webapp_v1 fallback). All four existing consumers are **sync**. Routing lives
in `ddpui/urls.py` `ws_urlpatterns` (`wss/...` paths); `ddpui/asgi.py` wires
`ProtocolTypeRouter` + `AllowedHostsOriginValidator`; `channels==4.1.0` +
`channels-redis==4.2.0` already installed.

**Why it matters:** LangGraph streaming needs an **async** consumer. We must write the
first `AsyncWebsocketConsumer` in the codebase and port `BaseConsumer`'s cookie-auth
into an async variant — the auth logic is copyable, the base class is not.

### 1.2 Feature flags: a plain dict + org rows

`ddpui/utils/feature_flags.py` holds `FEATURE_FLAGS` (a dict of allowed flag names) and
`enable/disable_feature_flag(flag_name, org)` writing `OrgFeatureFlag` rows.
`GET /api/organizations/feature-flags` (`user_org_api.py:614`) returns them to the
frontend. Adding `CHAT_WITH_DATA` = one dict entry, zero migration.
Note: an `AI_DATA_ANALYSIS` flag already exists — it gates the **old** warehouse
"ask a question about this table" feature (`warehouse_api.py:324`), not us. Don't reuse
it; the two features must be toggleable independently.

### 1.3 Org AI consent already has a full approval flow

`OrgPreferences` (`ddpui/models/org_preferences.py:11-15`) has `llm_optin` +
`llm_optin_approved_by` (who approved) + `llm_optin_date`. `org_preferences_api.py:53`
updates it. `OrgUser.llm_optin` is marked deprecated — ignore it.
**Decision (Siddhant, 2026-07-04): Chat with Data requires BOTH `CHAT_WITH_DATA` flag
AND `llm_optin=True`.** Example: Priya's org has the flag on but consent off → the nav
entry stays hidden and the status endpoint says why.

### 1.4 Warehouse access: one canonical client

Per DDP_backend's own `warehouse-client` skill (authoritative, supersedes the stale
`ddpui/datatypes/` path named in the alerts research):

```python
from ddpui.utils.warehouse.client.warehouse_factory import WarehouseFactory
warehouse = WarehouseFactory.get_warehouse_client(org_warehouse)  # creds via AWS Secrets Manager
rows = warehouse.execute(sql)  # -> list[dict]
```

Interface ABC: `ddpui/utils/warehouse/client/warehouse_interface.py`. Only Postgres and
BigQuery exist. The client is **sync/blocking** — inside our async consumer it must run
in a worker thread (LangGraph does this automatically for sync tools).

### 1.5 Default schema allowlist source

`OrgDbt.default_schema` (`ddpui/models/org.py:94`) holds the org's dbt output schema.
**Decision (Siddhant): orgs without dbt fall back to raw schemas** — an org that only
syncs KoboToolbox forms still gets answers, from raw tables.

### 1.6 Versions that constrain us

| Fact | Value | Consequence |
|---|---|---|
| Python | 3.10.12 (`.python-version`) | Two async caveats — §3.5 below |
| DB driver | `psycopg2-binary==2.9.6` | Checkpointer needs psycopg **3** — coexists fine as a separate package (§3.3) |
| sentry-sdk | 2.39.0 | LangGraph integration available (needs ≥2.37) — §3.6 |
| ASGI | `uvicorn`, `ASGI_APPLICATION` set | WS already served in prod; no deploy-model change |

### 1.7 Permission + API wiring patterns (pointers only)

- New API router registered in `ddpui/routes.py` (`src_api.add_router("/api/alerts/", …)` at line 118 is the newest example).
- Permission slugs seeded via `seed/003_role_permissions.json` + a `RunPython` migration (pattern: `ddpui/migrations/0137_update_landing_page_permissions.py`). Details in `features/alerts/v1/research.md` §1.
- The old experiment branch left a management-command pattern (`chatwithdatasetup.py`) — we are greenfield, but the "setup command" idea returns for the checkpointer (§3.3).

---

## 2. Codebase findings (webapp_v2)

### 2.1 WebSocket client plumbing already exists

`hooks/useBackendWebSocket.ts` wraps `react-use-websocket`: builds the URL from a
relative path (`lib/websocket.ts` `generateWebSocketUrl`), shared reconnect config, and
auth-close-code handling (`isAuthCloseCode`). Our `useChatWithData` hook composes this —
no new transport code.

### 2.2 Nav gating pattern

`components/main-layout.tsx` uses `useFeatureFlags()` → `isFeatureFlagEnabled(FeatureFlagKeys.X)`
and per-item `hide:` composition (line 131 shows the REPORTS example). New enum value
`CHAT_WITH_DATA` in `hooks/api/useFeatureFlags.ts` + one nav item. `llm_optin` is not
surfaced anywhere in webapp_v2 yet — our status endpoint carries that signal instead.

### 2.3 Everything else follows the standard hooks/api pattern

`hooks/api/useAlerts.ts` (SWR + `lib/api.ts`) is the newest reference for session CRUD
hooks. Permission-conditional rendering via `useUserPermissions().hasPermission(slug)`.

---

## 3. External research — LangGraph stack (July 2026)

Full sourced report gathered 2026-07-04 from official docs (python.langchain.com,
docs.langchain.com, PyPI). Key facts the plan depends on:

### 3.1 The spec's "prebuilt agent constructor" is `create_agent`

`from langchain.agents import create_agent` — `langgraph.prebuilt.create_react_agent`
is **deprecated in LangGraph 1.0, removed in 2.0**. Signature facts that changed our
spec's wording:

| Spec said | Reality in langchain 1.3.x |
|---|---|
| "pre-model hook" | Gone. Use **middleware**: `@before_model` decorator, or built-ins `SummarizationMiddleware`, `ContextEditingMiddleware(edits=[ClearToolUsesEdit(...)])` (clears bulky old tool outputs — ideal for SQL result cleanup) |
| "prompt" param | `system_prompt=` |
| Injected context | `context_schema=` dataclass + tools declare `runtime: ToolRuntime` param (auto-hidden from the LLM); `InjectedState` is the superseded older pattern |

### 3.2 Pinned versions (all Python 3.10-compatible)

`langgraph==1.2.7`, `langchain==1.3.11`, `langchain-anthropic==1.4.8`,
`langgraph-checkpoint-postgres==3.1.0`, `langsmith==0.9.7`, `sqlglot==30.12.0`,
plus `psycopg[binary,pool]` (psycopg 3).

### 3.3 Checkpointer: AsyncPostgresSaver

- `from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver`
- Needs **psycopg 3** with `autocommit=True` + `row_factory=dict_row`; use one
  app-level `psycopg_pool.AsyncConnectionPool` created lazily inside the running event
  loop — **never** `from_conn_string()` per message.
- `await checkpointer.setup()` once (creates `checkpoints`, `checkpoint_blobs`,
  `checkpoint_writes`, `checkpoint_migrations` tables) → wrap in a management command
  run at deploy, like the old branch's `chatwithdatasetup`.
- History outside a run: `await graph.aget_state({"configurable": {"thread_id": tid}})`
  → `StateSnapshot.values["messages"]`. This powers the REST history endpoint.

### 3.4 Streaming + token usage

- `astream(stream_mode=["messages", "updates"])` yields `(mode, chunk)` tuples:
  `messages` → `(AIMessageChunk, metadata)` for token streaming; `updates` → per-node
  deltas — an `AIMessage` with `tool_calls` = **tool_start**, a `ToolMessage` from the
  `tools` node = **tool_end**. This maps 1:1 onto our WS event protocol.
- `ChatAnthropic` streams usage by default (`stream_usage=True`) → final message's
  `usage_metadata` has `input_tokens`/`output_tokens` for the audit record.

### 3.5 Python 3.10 caveats (we're on 3.10.12)

1. `get_stream_writer()` (custom stream mode) **does not work in async code on 3.10**.
   Consequence: no in-tool progress events in v1 — tool_start/tool_end from `updates`
   mode is enough for the UI. Spec's `stream_mode=["messages","updates","custom"]`
   drops `custom`.
2. Runtime config is not auto-propagated to nested async calls on 3.10 — pass `config`
   explicitly if a node invokes sub-runnables.
3. LangGraph Studio (`langgraph dev`) needs Python ≥3.11 — **Studio is out**; LangSmith
   tracing is the local debugging tool instead (§3.7).

### 3.6 Sentry

`sentry_sdk.integrations.langgraph.LanggraphIntegration` auto-enables when langgraph is
importable (we have sentry-sdk 2.39.0 ≥ 2.37). **Must configure
`LanggraphIntegration(include_prompts=False)`** — otherwise prompts (= warehouse data)
can flow to Sentry when `send_default_pii` is on.

### 3.7 LangSmith for local dev (user requirement, added 2026-07-04)

Siddhant asked for a way to run LangSmith locally to watch queries and tool calls
while developing. Findings:

- **Setup is env-vars only** — no code changes: `pip install langsmith` (already a
  transitive dep), then in `.env`:
  ```
  LANGSMITH_TRACING=true
  LANGSMITH_API_KEY=<from smith.langchain.com>
  LANGSMITH_PROJECT=dalgo-chat-with-data-dev
  ```
  Traces show the full agent run: every LLM call, every tool call **with its SQL input**, token counts, latency.
- **Free tier exists**: Developer plan, 5K traces/month, 14-day retention — enough for dev.
- **Self-hosted LangSmith is Enterprise-only.** If traces must never leave the machine, the free path is **Langfuse** (MIT, Docker Compose, LangChain callback) — noted as an alternative, not planned.
- Prod stays **off by default** (org data would leave the deployment); the same env vars enable it deliberately.

### 3.8 Model IDs (ChatAnthropic `model=`)

- Agent: **`claude-sonnet-5`** default (strong tool-use; ~$3/$15 per MTok — Opus-tier
  `claude-opus-4-8` is 1.7× the price; NGO budgets say Sonnet, config allows override).
- Session titles: **`claude-haiku-4-5`**.
- Gotcha: these models **reject `temperature`/`top_p`** — don't set them.

### 3.9 Django Channels × LangGraph gotchas (shape the consumer design)

- Sync tools are fine: LangGraph runs sync `@tool` functions in a worker thread under
  `astream` — the event loop is not blocked. But **no naked ORM calls inside tools**
  (raises `SynchronousOnlyOperation`). Our design: the consumer resolves everything
  (org, warehouse client, limits) into the run **context** before the turn starts, using
  `database_sync_to_async`; tools touch only `runtime.context`, never the ORM.
- Long turns + long-lived consumers: call `aclose_old_connections()` before ORM use
  after an agent turn (Channels only cleans connections on connect/receive/disconnect).
- One event loop: the psycopg3 pool is loop-bound — don't share it with
  `asyncio.run()` in management commands; the setup command builds its own connection.

---

## 4. Decisions from scope conversation (2026-07-04, Siddhant)

| # | Question | Decision |
|---|---|---|
| 1 | Require org AI consent (`llm_optin`) on top of the feature flag? | **Yes — both required** |
| 2 | Orgs with no dbt setup? | **Fall back to raw schemas** |
| 3 | Per-user dataset grants (access-control Layer 2, in flight)? | **Defer; leave one seam** — a single `get_allowed_schemas(orguser)` function the grants system can later replace |
| 4 | Explore page overlap? | **Out of scope in v1** — no bridge |
| 5 | LangSmith locally for dev (added mid-planning) | **In scope** — dev env setup + REPL harness in Milestone 2 |

---

## 5. Blast radius — domain map traversal

Primary change: a **new terminal entity** ("Chat with Data" surface) that consumes
Warehouse (`query-from`). It modifies no existing entity, so nothing downstream of
existing entities changes. The impact set is therefore inbound edges + platform gating:

| Surface | Hop | Edge | Status | Notes |
|---|---|---|---|---|
| Warehouse | 1 (consumes) | `query-from` | In scope, read-only | Guarded SELECT-only; upstream schema changes can't break us persistently (no stored queries) |
| Transform | 1 (consumes) | `query-from` | In scope, read-only | dbt output schemas are the default allowlist; raw fallback per decision 2 |
| Organization | 1 | gating | In scope | `CHAT_WITH_DATA` flag + `llm_optin` + new org config row |
| OrgUser | 1 | RBAC | In scope | New `can_use_chat_with_data` slug; sessions are per-user |
| Explore | product overlap | — | **Out of scope** | Decision 4 |
| Dataset grants (access-control) | future | enforcement | **Deferred, seam left** | Decision 3 |
| Chart / Dashboard / Metric / KPI / Report / Alert / Notification / Pipeline / Source / Data Quality | — | — | **Unaffected** | v1 creates no artifacts and modifies no entity these consume; chart/dashboard creation is explicitly future tools (spec §12) |

**Domain-map follow-up:** add a "Chat with Data" entity to `docs/domain-map.md` when
this ships (the map's own rule for new product entities).

---

## 6. Deprecated / superseded references spotted

- `features/alerts/v1/research.md` names `WarehouseFactory` at `ddpui/datatypes/warehouse_*.py` — the current canonical path is `ddpui/utils/warehouse/client/` (per DDP_backend's `warehouse-client` skill). Trust the skill.
- `OrgUser.llm_optin` — deprecated field; org-level consent lives on `OrgPreferences`.
- `langgraph.prebuilt.create_react_agent` and `pre_model_hook` — deprecated upstream; any older Dalgo branch code using them is not a pattern to copy.
