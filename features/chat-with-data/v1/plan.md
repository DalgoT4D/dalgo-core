# Chat with Data v1 — Implementation Plan (Draft v1)

**Date:** 2026-07-04
**Spec:** [v1 spec](./spec.md) · **Research:** [research.md](./research.md)
**Status:** Draft — for engineering review

Acronyms used: LLM (large language model) · AST (abstract syntax tree — the parsed
structure of a SQL query) · WS (WebSocket) · RBAC (role-based access control) ·
ORM (Django's database layer) · PII (personally identifiable information) ·
HLD/LLD (high/low-level design) · FK (foreign key).

---

## 1. Overview

A chat page where Priya (a program manager, not an engineer) asks questions like
"how many surveys did we run in Pune last month?" and a LangGraph agent inspects her
org's warehouse, writes a guarded read-only SQL query, runs it, and streams back the
answer with a results table. Follow-ups keep context.

- **Services affected:** `DDP_backend` (agent, REST, WS), `webapp_v2` (chat page). `prefect-proxy`: untouched.
- **New backend deps:** `langgraph==1.2.7`, `langchain==1.3.11`, `langchain-anthropic==1.4.8`, `langgraph-checkpoint-postgres==3.1.0`, `sqlglot==30.12.0`, `psycopg[binary,pool]` (coexists with psycopg2 — research §3.3).

---

## 2. Blast Radius

Chat with Data is a **new terminal entity** — it consumes the Warehouse, creates no
artifacts, and modifies no existing entity. Full traversal in research §5
(domain-map walk). Confirmed statuses (Siddhant, 2026-07-04):

| Surface | Hop | Why affected | Status | Notes |
|---|---|---|---|---|
| Warehouse | 1 | Agent runs read-only SELECTs | **In scope** | Guarded; no stored queries, so upstream schema changes can't rot anything |
| Transform (dbt) | 1 | dbt output schemas = default allowlist | **In scope** | Orgs without dbt fall back to raw schemas |
| Organization | 1 | New flag + consent + config | **In scope** | `CHAT_WITH_DATA` flag AND existing `llm_optin` both required |
| OrgUser | 1 | New permission, per-user sessions | **In scope** | `can_use_chat_with_data` slug |
| Explore page | overlap | Both let users query ad-hoc | **Out of scope** | No bridge in v1; revisit after usage data |
| Dataset grants (access-control Layer 2) | future | Per-user schema/table access | **Deferred, seam left** | One function `get_allowed_schemas(orguser)` is the plug point |
| Chart, Dashboard, Metric, KPI, Report, Alert, Notification, Pipeline, Source, Data Quality | — | Not consumed, not modified | **Unaffected** | Chart/dashboard creation from chat is explicitly future (spec §12) |

Post-ship task: add the new entity to `docs/domain-map.md`.

---

## 3. High-Level Design

### 3.1 One turn, end to end

```
Priya types "surveys in Pune last month?"          webapp_v2
    │ WS send_message                                  │
    ▼                                                  │
ChatWithDataConsumer (async, first in codebase)        │
    │ 1. auth (JWT cookie) + permission + flag + consent
    │ 2. rate-limit + per-session turn lock (Redis)
    │ 3. build RunContext (org, warehouse client,
    │    allowed schemas, limits) — ORM via sync_to_async
    ▼
LangGraph agent  (create_agent: model ⇄ ToolNode loop)
    │  Claude (claude-sonnet-5) plans:
    │  list_tables → get_table_details → execute_sql
    │                     │
    │              guards/ (sqlglot AST: SELECT-only,
    │              allowlist, LIMIT clamp, timeout)
    │                     ▼
    │              WarehouseFactory client (sync, runs
    │              in worker thread)
    ▼
astream(stream_mode=["messages","updates"])
    │ mapped to WS events: token / tool_start / tool_end
    ▼
message_complete (+ result table) → Priya's screen
    │
    ├─ checkpointer saves the turn (conversation memory)
    └─ ChatTurnAudit row (SQL run, tokens, latency)
```

### 3.2 Key design decisions

**The rule:** the agent core (`ddpui/core/chat_with_data/`) never imports transport
code — consumers and REST call *it*.
**Example:** the Milestone-2 REPL script drives the same `build_agent()` from a
terminal, no WebSocket involved.
**Why it matters:** testable without sockets; future transports (API-only, Slack bot)
reuse the agent unchanged.

**The rule:** all per-org/per-user facts travel in the run **context**
(`context_schema` dataclass), resolved by the consumer before the turn starts.
**Example:** `execute_sql` gets the warehouse client from `runtime.context.warehouse`;
the LLM never sees or supplies an org id, so a hallucinated org id cannot cross tenants.
**Why it matters:** org isolation by construction + no ORM calls inside tools
(research §3.9 — `SynchronousOnlyOperation`).

**The rule:** agent runs inside the async consumer — no Celery hop.
**Example:** tokens stream to Priya as Claude generates them; a Celery worker would
have to relay chunks through Redis channel-layer messages instead.
**Why it matters:** native streaming, less infrastructure. Accepted trade-off: socket
drop kills the in-flight turn (history up to it survives in the checkpointer).

**The rule:** messages live only in the LangGraph Postgres checkpointer; Django keeps
session metadata + audit.
**Why it matters:** one source of truth — no Django-vs-checkpointer sync bugs.

### 3.3 API surface (all new)

| Kind | Route | Purpose |
|---|---|---|
| REST | `GET /api/chat-with-data/status` | `{enabled, reason}` — flag + consent + warehouse + permission in one call (drives nav + empty states) |
| REST | `POST/GET /api/chat-with-data/sessions/` | Create / list my sessions |
| REST | `PUT/DELETE /api/chat-with-data/sessions/{id}` | Rename / soft-delete |
| REST | `GET /api/chat-with-data/sessions/{id}/messages` | History, mapped from checkpointer state |
| WS | `wss/chat-with-data/{session_id}/` | The chat turn: `send_message` in; `token`, `tool_start`, `tool_end`, `message_complete`, `error`, `title_updated` out |

### 3.4 External integrations

| System | How |
|---|---|
| Anthropic API | `ChatAnthropic(model=settings.CHAT_WITH_DATA_MODEL)` — default `claude-sonnet-5`; titles via `claude-haiku-4-5`. **No `temperature`** (rejected by these models). Deployment-level `ANTHROPIC_API_KEY`. |
| Org warehouse | Existing `WarehouseFactory.get_warehouse_client(org_warehouse)` — Postgres + BigQuery |
| LangSmith (dev) | Env-vars only: `LANGSMITH_TRACING=true` + key + project (research §3.7). Off in prod. |
| Sentry | `LanggraphIntegration(include_prompts=False)` added to the existing `sentry_sdk.init` |

---

## 4. Low-Level Design

### 4.1 Data model (Django, new file `ddpui/models/chat_with_data.py`)

```python
class ChatWithDataSession(models.Model):
    org        = FK(Org, CASCADE)
    orguser    = FK(OrgUser, CASCADE)          # owner; sessions are personal
    title      = CharField(255, default="New chat")
    thread_id  = UUIDField(unique=True, default=uuid4)  # checkpointer thread key
    created_at / updated_at
    deleted_at = DateTimeField(null=True)      # soft-delete

class ChatWithDataTurnAudit(models.Model):     # one row per user question (spec §7 layer 5 + §9)
    org, orguser, session = FKs
    request_uuid  = UUIDField()
    user_message  = TextField()                # the question asked
    sql_queries   = JSONField(default=list)    # [{sql, status, row_count, duration_ms, error}]
    tools_called  = JSONField(default=list)    # ["list_tables", "execute_sql", ...]
    input_tokens / output_tokens = IntegerField(default=0)
    latency_ms    = IntegerField(null=True)
    status        = CharField                  # completed | failed | aborted
    created_at

class ChatWithDataOrgConfig(models.Model):     # admin-tuned knobs; Django admin only in v1
    org             = OneToOneField(Org, CASCADE)
    allowed_schemas = JSONField(null=True)     # null = derive (dbt default_schema, else raw)
    max_result_rows = IntegerField(default=100)   # clamped to hard max 500
    query_timeout_s = IntegerField(default=30)
```

Plus **checkpointer tables** (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`,
`checkpoint_migrations`) created by `python manage.py chat_with_data_setup` — a
management command wrapping `AsyncPostgresSaver.setup()` (not a Django migration; the
tables belong to the library). Run once per deploy environment.

**Retention:** deleting a session hard-deletes its checkpointer thread rows via
`checkpointer.adelete_thread(thread_id)` after the soft-delete grace period — v1 does
soft-delete only; a cleanup command is listed in Open Questions.

### 4.2 The agent package `ddpui/core/chat_with_data/`

```
agent.py       build_agent(checkpointer) -> CompiledStateGraph
state.py       ChatState(AgentState) + RunContext dataclass
context.py     build_run_context(orguser) -> RunContext   (the ONLY place that reads ORM/warehouse config)
prompts.py     system prompt assembly (dialect-aware: postgres vs bigquery)
middleware.py  trimming (@before_model + trim_messages), ContextEditingMiddleware config,
               sql-retry limiter (counts failed execute_sql ToolMessages since last user msg; ≥3 → instructs model to stop)
tools/
  registry.py  @register_tool decorator + get_tools() — the extension point
  schema_tools.py   list_schemas, list_tables, get_table_details
  profile_tools.py  profile_column
  sql_tools.py      execute_sql
guards/
  sql_guard.py validate(sql, dialect, allowed_schemas) -> GuardedSQL | GuardError
  limits.py    LIMIT clamp via AST, timeout application, result truncation
```

Core construction (research §3.1 — `create_agent`, middleware, `ToolRuntime`):

```python
# agent.py
agent = create_agent(
    model=ChatAnthropic(model=settings.CHAT_WITH_DATA_MODEL, max_tokens=4096),
    tools=get_tools(),
    system_prompt=build_system_prompt,        # dialect + allowlist-aware
    state_schema=ChatState,
    context_schema=RunContext,
    middleware=[trim_history, sql_retry_limiter, clear_old_tool_results],
    checkpointer=checkpointer,
)
# consumer:  agent.astream({"messages": [...]}, config={"configurable": {"thread_id": ...},
#            "recursion_limit": 25}, context=run_context, stream_mode=["messages", "updates"])
```

```python
# tools/sql_tools.py — the only execution path
@register_tool
@tool
def execute_sql(sql: str, runtime: ToolRuntime) -> str:
    """Run one read-only SELECT against the org warehouse. ..."""
    ctx = runtime.context                      # RunContext — invisible to the LLM
    guarded = sql_guard.validate(sql, ctx.dialect, ctx.allowed_schemas)  # raises -> error text
    rows = ctx.warehouse.execute(guarded.sql_with_limit_and_timeout)     # sync; LangGraph runs it in a worker thread
    return format_result(rows, ctx.max_result_rows)   # compact text + row count; audit via callback
```

**Python 3.10 constraint honored:** no `custom` stream mode / `get_stream_writer()`
(broken in async on 3.10 — research §3.5). Tool progress comes from `updates` mode.

### 4.3 SQL guard (`guards/sql_guard.py`)

**The rule:** parse with `sqlglot` in the org's dialect; reject unless the tree is
exactly one statement whose root is SELECT (or WITH whose final body is SELECT and all
CTEs are SELECTs); every table reference resolves to an allowed schema; then rewrite:
clamp/inject LIMIT, and (Postgres) run under a transaction-local statement timeout,
(BigQuery) set job timeout + `maximum_bytes_billed`.
**Example:** `WITH d AS (DELETE FROM surveys RETURNING *) SELECT * FROM d` parses fine
but contains a Delete node → rejected by node-type walk, no regex involved.
**Why it matters:** the old branch's regex guard was bypassable with comments and
keyword-lookalikes (review finding 1b); AST checks are structural.

Checks, in order: parse errors → reject · multi-statement → reject · non-SELECT node
anywhere (Insert/Update/Delete/Create/Drop/Alter/Merge/Copy/Command/Set) → reject ·
unqualified or non-allowlisted schema → reject · LIMIT missing or > org max → rewrite.

### 4.4 WebSocket consumer (`ddpui/websockets/chat_with_data_consumer.py`)

First **async** consumer in the codebase (existing `BaseConsumer` is sync — research
§1.1). Port the JWT-cookie auth into an `AsyncBaseConsumer` (auth logic copied,
wrapped with `database_sync_to_async`).

Per-connection flow: authenticate → load session (must belong to this orguser + org) →
check flag + `llm_optin` + `can_use_chat_with_data` → accept, else close with auth code.
Per-message flow: rate-limit check (Django cache/Redis: max 10 messages/min/user) →
acquire per-session turn lock (Redis `SET NX EX 120`) → build `RunContext` → stream.

Event mapping (research §3.4):

| astream yields | WS event sent |
|---|---|
| `("messages", (chunk, meta))` with text | `{type: "token", text}` |
| `("updates", …)` model node emits `AIMessage.tool_calls` | `{type: "tool_start", tool, label, sql?}` — label from a per-tool friendly-name map ("Running query…"); `sql` included for execute_sql |
| `("updates", …)` tools node emits `ToolMessage` | `{type: "tool_end", tool, status}` |
| stream ends | `{type: "message_complete", message, result_table?, usage}` — `result_table` re-extracted from the final execute_sql ToolMessage |
| exception / guard exhaustion | `{type: "error", message}` (user-friendly, logged with request_uuid) |
| first turn only, after complete | Haiku title call → `{type: "title_updated", title}` + save |

After each turn: write `ChatWithDataTurnAudit` (tokens from `usage_metadata`), call
`aclose_old_connections()` (research §3.9).

### 4.5 REST API (`ddpui/api/chat_with_data_api.py`)

Django Ninja router registered in `routes.py` as `/api/chat-with-data/` (newest
pattern: alerts router, `routes.py:118`). Schemas in
`ddpui/schemas/chat_with_data_schemas.py`. All endpoints
`@has_permission(["can_use_chat_with_data"])`; session queries always filtered
`org=orguser.org, orguser=orguser, deleted_at__isnull=True`.

History endpoint: `graph.aget_state(thread config)` → map `HumanMessage` → user bubble;
`AIMessage` (with content) → assistant bubble; `execute_sql` ToolMessages → attached
`{sql, result_table}` so "view SQL" and tables survive a reload. Endpoint is async
(Ninja supports async views) reusing the shared checkpointer.

### 4.6 Gating & permissions

| Layer | Change |
|---|---|
| Feature flag | Add `CHAT_WITH_DATA` to `FEATURE_FLAGS` dict (`ddpui/utils/feature_flags.py`) — no migration |
| Consent | Status endpoint + consumer check `OrgPreferences.llm_optin` (research §1.3). Example: flag on, consent off → nav hidden, status says `reason: "llm_consent_required"` |
| RBAC | New slug `can_use_chat_with_data` seeded to account-manager, org-admin, pipeline-manager, analyst (NOT guest) via the 0137-style RunPython migration + `seed/003_role_permissions.json` |
| Existing AI_DATA_ANALYSIS flag | Untouched — gates the old warehouse-prompt feature (research §1.2) |

### 4.7 Frontend (webapp_v2)

```
app/chat-with-data/page.tsx            two-pane layout (spec §10 wireframe)
components/chat-with-data/
  session-sidebar.tsx                  list + new/rename/delete (Shadcn Sheet on mobile)
  chat-pane.tsx                        message list + composer
  message-bubble.tsx                   markdown (existing renderer), user/assistant
  tool-progress.tsx                    chips w/ friendly labels; collapsible "view SQL"
  result-table.tsx                     scrollable table from result_table payload
hooks/api/useChatSessions.ts           SWR CRUD on the REST endpoints (pattern: useAlerts.ts)
hooks/useChatWithData.ts               WS turn lifecycle over useBackendWebSocket:
                                       reducer: token→append streaming text, tool_start/end→chips,
                                       message_complete→finalize, error→toast + retry affordance
```

Nav: `FeatureFlagKeys.CHAT_WITH_DATA` + `hide:` composition in `main-layout.tsx`
(research §2.2) + `status.enabled` check; page itself renders friendly empty states per
`status.reason` (e.g. consent missing → "Ask your admin to enable AI features").

### 4.8 Dev tooling (Siddhant's requirement)

- `scripts/chat_with_data_repl.py` (management command or script): terminal REPL that
  builds the same agent against a dev org and streams to stdout — try the agent
  without the frontend.
- `.env.template` additions + a `docs/` note in DDP_backend:
  `ANTHROPIC_API_KEY`, `CHAT_WITH_DATA_MODEL`, and the three `LANGSMITH_*` vars
  (research §3.7 — free Developer tier, traces show every tool call + SQL).
- Definition of "working": run the REPL, ask a question, open smith.langchain.com,
  see the trace with `list_tables` → `execute_sql` spans and the generated SQL.

---

## 5. Security Review

| Area | Design |
|---|---|
| **AuthN/AuthZ** | REST: `@has_permission(["can_use_chat_with_data"])`. WS: JWT from httpOnly cookie (existing pattern), then the same permission + flag + `llm_optin` checks before accept. Sessions owner-scoped: Priya cannot open Sarah's session (404, filtered query). |
| **Input validation** | REST bodies via Ninja/Pydantic schemas. WS messages validated against a typed schema; unknown `action` → error event. User's chat text goes only into the LLM prompt, never into SQL directly. |
| **Multi-tenant isolation** | Org id and warehouse client come from server-resolved `RunContext`; the LLM cannot name an org. Session ↔ org ↔ thread_id binding checked on every connect. Checkpointer threads keyed by server-generated UUID. |
| **SQL injection / write attempts** | The LLM's SQL is treated as untrusted input: sqlglot AST guard (§4.3), SELECT-only by node type, schema allowlist, LIMIT clamp, timeouts. Known limitation (spec §7): credentials are read-write; read-only warehouse role is a fast-follow. |
| **Prompt injection via data** | Residual risk: a malicious value *inside* warehouse data could instruct the model. Mitigation: tools are read-only + guarded, so the blast radius is "weird answer", not data change. Documented, accepted for v1. |
| **PII / data egress** | Query results go to Anthropic — gated on org's explicit `llm_optin` (with approver + date). LangSmith tracing off in prod. Sentry: `LanggraphIntegration(include_prompts=False)` so prompts/results never reach Sentry. Audit rows store SQL + row counts, not result data. |
| **Secrets** | `ANTHROPIC_API_KEY` env-only. Warehouse creds stay inside `WarehouseFactory`/Secrets Manager; never in state, prompts, or logs. |
| **Abuse / cost control** | Rate limit 10 msgs/min/user + one in-flight turn per session (Redis lock) + `recursion_limit=25` + `max_tokens` cap + per-turn token audit. BigQuery `maximum_bytes_billed` caps scan cost. |

---

## 6. Testing Strategy

| Layer | Tests (where) |
|---|---|
| SQL guard — heaviest | `tests/core/chat_with_data/test_sql_guard.py`: the old review's bypass catalog — comment-split statements, `COPY`, CTE named `delete`, DML inside CTE, `SET`/`SHOW`/`EXPLAIN`, unicode lookalikes, multi-statement, allowlist escape via unqualified table, LIMIT inject/clamp — parametrized over both dialects |
| Tools | Mocked warehouse client on a fake `RunContext`; assert compact output truncation, profile_column caps |
| Agent loop | `FakeMessagesListChatModel`-style scripted model: happy path (schema→details→sql→answer), error-then-recovery, 3-failure exhaustion (limiter middleware), recursion limit |
| Trimming middleware | Long fake history → trimmed request, checkpoint intact |
| WS consumer | Channels `WebsocketCommunicator`: auth reject (no cookie / wrong org), flag/consent reject, event sequence for a scripted turn, turn-lock rejection, rate limit |
| REST | Ninja test client: CRUD, owner-scoping (Sarah can't rename Priya's session), history mapping incl. sql attachment |
| Frontend | `useChatWithData` reducer unit tests (event stream → UI state, reconnect), component render tests (chips, table, error) — RTL per webapp_v2 conventions |
| Integration (live) | REPL script against dev warehouse (Postgres AND one BigQuery org): 5 canned questions incl. one that forces a SQL error; verify traces in LangSmith |
| Edge cases | empty warehouse, org with no dbt (raw fallback), 0-row result, huge result (truncation), warehouse down (friendly error), Anthropic 529/overload (retry surface), session deleted mid-turn |

---

## 7. Milestones

Ordered; each is one reviewable PR and leaves the codebase shippable (feature stays
dark behind the flag until M5).

#### Milestone 1: SQL guard + limits (pure library code)
- **Deliverable:** `guards/` package with full test suite; no LangGraph yet
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Add `sqlglot` dep; implement `sql_guard.validate()` (both dialects) + `limits.py`
  - [ ] Bypass-catalog test suite (§6 row 1)
- **Acceptance:** every bypass test red-team case rejected; valid SELECTs pass with clamped LIMIT

#### Milestone 2: Agent core + dev harness (LangSmith)
- **Deliverable:** working agent callable from a terminal REPL, traced in LangSmith
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Pin langgraph/langchain/langchain-anthropic/psycopg deps (research §3.2)
  - [ ] `state.py`, `context.py`, `prompts.py`, `middleware.py`, `tools/` (registry + 5 tools), `agent.py`
  - [ ] Checkpointer singleton (psycopg3 pool) + `chat_with_data_setup` management command
  - [ ] REPL script + `.env.template` (`ANTHROPIC_API_KEY`, `CHAT_WITH_DATA_MODEL`, `LANGSMITH_*`) + dev-setup doc
  - [ ] Scripted-model agent-loop tests + tool tests
- **Acceptance:** dev runs REPL against dev org, gets correct answer with follow-up; trace visible in LangSmith showing tool calls + SQL

#### Milestone 3: Sessions, REST, gating, audit
- **Deliverable:** full REST surface + models + permission, exercised by API tests
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Models + migration; `CHAT_WITH_DATA` flag entry; permission slug seed + migration
  - [ ] `chat_with_data_api.py` (status, session CRUD, history from checkpointer)
  - [ ] `ChatWithDataTurnAudit` writes wired into the agent runner
- **Acceptance:** API tests green incl. owner-scoping; status endpoint reflects flag/consent/permission matrix

#### Milestone 4: WebSocket streaming
- **Deliverable:** end-to-end turn over WS (testable with wscat/Channels communicator)
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] `AsyncBaseConsumer` (async port of cookie-JWT auth) + `chat_with_data_consumer.py` + `ws_urlpatterns` entry
  - [ ] astream→event mapping, turn lock, rate limit, title generation (Haiku), error surfaces
  - [ ] Sentry `LanggraphIntegration(include_prompts=False)`
  - [ ] Consumer test suite
- **Acceptance:** scripted WS session shows token → tool_start(sql) → tool_end → message_complete sequence; second concurrent message rejected by lock

#### Milestone 5: Frontend chat page
- **Deliverable:** the visible feature — nav entry, page, streaming UI
- **Services:** webapp_v2
- **Key tasks:**
  - [ ] `FeatureFlagKeys.CHAT_WITH_DATA` + nav item + status-driven empty states
  - [ ] `useChatSessions` (SWR) + `useChatWithData` (WS reducer)
  - [ ] Components: sidebar, chat pane, bubbles, progress chips + view-SQL, result table
  - [ ] Hook + component tests
- **Acceptance:** Priya's flow from spec §10 works on staging against a flagged org; slow-connection check (streaming visible, no layout jank)

#### Milestone 6: Hardening + live validation
- **Deliverable:** production go/no-go evidence
- **Services:** both
- **Key tasks:**
  - [ ] Live E2E on staging: Postgres org + BigQuery org, canned question set, error-recovery case
  - [ ] Load sanity: 3 concurrent sessions streaming
  - [ ] Verify audit rows, token costs per turn; tune system prompt if needed
  - [ ] `docs/domain-map.md` entity entry + user-facing docs page (documentation skill)
- **Acceptance:** checklist in PR description with evidence links (traces, audit rows, screenshots)

---

## 8. Open Questions & Risks

| # | Item | Type | Current stance |
|---|---|---|---|
| 1 | Which roles get `can_use_chat_with_data`? | Question | Plan says admin+pipeline-manager+analyst, not guest — confirm at M3 review |
| 2 | Checkpointer growth — no pruning in v1 | Risk | Soft-deleted sessions keep thread rows; add a cleanup command (delete threads for sessions deleted >30 days) as fast-follow |
| 3 | Per-turn cost | Risk | Sonnet-5 ~$3/$15 per MTok; a schema-heavy turn ≈ 10-30K input tokens → few cents/turn. M6 measures real numbers; `CHAT_WITH_DATA_MODEL` can downshift |
| 4 | sqlglot BigQuery dialect edge cases | Risk | Guard tests parametrized over both dialects; unparseable SQL is rejected (fail-closed) |
| 5 | Read-only warehouse credentials | Deferred | Spec §7 known limitation; fast-follow after v1 |
| 6 | Dataset grants integration | Deferred | Seam = `get_allowed_schemas(orguser)` in `context.py`; access-control Layer 2 replaces its body |
| 7 | Python 3.11 upgrade | Nice-to-have | Would unlock in-tool progress events (`custom` stream mode) and LangGraph Studio; not required for v1 |
| 8 | Prompt injection via warehouse data values | Accepted risk | Read-only tools bound the damage to wrong answers; revisit if tools gain write powers (future charts) |
