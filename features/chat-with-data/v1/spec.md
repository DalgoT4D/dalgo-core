# Chat with Data — v1 Spec

**Date:** 2026-07-04
**Status:** Approved design, ready for planning
**Repos touched:** `DDP_backend` (agent + APIs), `webapp_v2` (chat page)

---

## 1. What we're building and why

Priya is a program manager at an NGO using Dalgo. Her field data is already synced
and transformed into warehouse tables, but to answer "how many households did we
survey in Pune last month?" she either opens a dashboard that may not have that
exact number, or asks an engineer to write SQL (a database query language).

**Chat with Data** gives Priya a chat page inside Dalgo where she types that
question in plain English. An AI agent looks at her org's tables, writes and runs
a safe read-only query, and replies with the number, the table of results, and a
one-line explanation — in seconds, with no engineer involved.

Follow-up questions work naturally: after the answer above, Priya can ask
"and how does that compare to the month before?" and the agent understands
"that" from the conversation.

### What v1 is NOT

- No chart, dashboard, or report creation from chat (future tools — the
  architecture is built so these can be added without rework, see §4).
- No writing/changing data in the warehouse. Ever. Read-only by design.
- No cross-org access. The agent only ever sees the asking user's org.

---

## 2. Decisions already made

These were settled during design review with Siddhant:

| Decision | Choice |
|---|---|
| Prior art (two old branches) | Ignore both; build greenfield |
| Where the agent lives | Inside `DDP_backend` (new module), not a separate service |
| LLM provider | Anthropic Claude only |
| Scope | Full stack: backend agent + webapp_v2 chat page |
| Warehouses | Postgres and BigQuery (both Dalgo supports today) |
| Chat surface | Dedicated sidebar page, not a floating widget |
| Graph architecture | Single LangGraph agent loop with a tool registry (option A) |

**Why greenfield when two branches exist?** The old dashboard-chat branch
(~8,300 lines) had custom orchestration and open security findings (its regex
SQL guard was bypassable). The old experiment branch didn't use LangGraph.
Rebuilding on native LangGraph patterns is less work than untangling either.

---

## 3. Architecture at a glance

```
webapp_v2  "Chat with Data" page
    │  WebSocket (streaming) + REST (sessions)
    ▼
DDP_backend
    ├─ chat_with_data_consumer.py     (WebSocket, runs the agent, streams events)
    ├─ chat_with_data_api.py          (REST: session create/list/rename/delete/history)
    └─ ddpui/core/chat_with_data/     (the agent — transport-independent)
         ├─ agent.py        LangGraph agent loop (model ⇄ ToolNode)
         ├─ state.py        conversation state + runtime context schema
         ├─ tools/          tool registry — the extension point
         ├─ guards/         SQL safety (sqlglot AST) + limits
         ├─ context.py      builds per-turn org/warehouse context
         └─ prompts.py      system prompt assembly
    │
    ├─ LangGraph Postgres checkpointer  (conversation memory, existing Django DB)
    ├─ WarehouseFactory                 (existing client: Postgres / BigQuery)
    └─ Anthropic API                    (Claude, deployment-level API key)
```

**New libraries:** `langgraph` 1.x, `langchain-anthropic`,
`langgraph-checkpoint-postgres`, `sqlglot` (a SQL parser that understands
query structure — used for safety checks instead of fragile text matching).

---

## 4. The agent loop (LangGraph)

**The rule:** Use LangGraph's prebuilt agent constructor — one model node bound
to tools, one native `ToolNode`, loop until the model stops calling tools. No
hand-rolled orchestration nodes.

**Example:** Priya asks "surveys per district last month". The model calls
`list_tables`, then `get_table_details('prod', 'surveys')`, then
`execute_sql(...)`, then answers. Four loop iterations, zero custom edges.

**Why it matters:** Every future capability (charts, reports, exports) becomes
"register one more tool". The graph never changes, so extending the agent
never risks breaking the core loop.

Customization happens only at the three sanctioned extension points:

1. **Custom state** — adds `sql_attempts` (bounds retries, see §6) and
   `last_result_meta` (row counts for the UI) on top of message history.
2. **Runtime context** — `org_id`, warehouse type, allowed schemas, row/time
   limits. Injected into tools at call time; **never** part of the text the
   LLM (large language model) sees.
   The model cannot cross org boundaries by making up an org ID, because it
   never supplies one.
3. **Pre-model hook** — trims old turns to a token budget before each model
   call (keeps system prompt + recent turns), so week-long sessions don't
   overflow the context window.

A `recursion_limit` (~25 steps) is the hard backstop against infinite loops.

---

## 5. Tools (v1) and the registry

**The rule:** `tools/registry.py` exposes `get_tools(context)`; each tool module
self-registers with a decorator. Adding a tool touches one new file, nothing else.

| Tool | What it does for the agent |
|---|---|
| `list_schemas()` | Which schemas (folders of tables) this org allows |
| `list_tables(schema)` | Tables + approximate row counts |
| `get_table_details(schema, table)` | Columns, types, sample values per column |
| `profile_column(schema, table, column)` | Top distinct values in a column |
| `execute_sql(sql)` | Runs one guarded, read-only query. The only execution path. |

**Why `profile_column` exists:** filter values are where text-to-SQL agents
fail silently. If Priya asks about "Maharashtra" but the column stores `MH`,
a naive query returns zero rows and a wrong "no data" answer. The system
prompt instructs the agent to profile filter columns *before* writing SQL.

All tools return compact structured text sized for an LLM (truncated cells,
capped lists), and reach the warehouse through the existing
`WarehouseFactory.get_warehouse_client(org_warehouse)` — never raw credentials.

---

## 6. Error recovery

**The rule:** A failed query is not an exception — the warehouse error message
becomes the tool result, and the model reads it and corrects itself. Max 3 SQL
attempts per user question (tracked in state), then the agent apologizes and
suggests rephrasing.

**Example:** The agent writes `SELECT districtname FROM surveys` but the column
is `district_name`. Postgres returns `column "districtname" does not exist`.
The agent sees the error, re-checks `get_table_details`, fixes the column, and
succeeds — all invisible to Priya except a slightly longer "Running query…" step.

**Why it matters:** Self-correction is the difference between an agent that
works on real, messy warehouses and a demo.

---

## 7. Security guardrails (layered)

All enforcement lives inside `execute_sql` and `guards/` — a tool the model
can't route around, because it's the only execution path.

| Layer | Enforcement |
|---|---|
| 1. AST validation | AST = abstract syntax tree, the parsed structure of a query. `sqlglot` parses the SQL in the org's dialect. Exactly one statement, and it must be a SELECT. Write statements (INSERT/UPDATE/DELETE, table changes, `COPY`), multi-statement input, and writes hidden inside CTEs (WITH-clauses) are rejected **by node type**, so comment tricks and keyword-lookalike bypasses (which broke the old regex guard) don't work. |
| 2. Schema allowlist | Every table referenced in the AST must live in an org-allowed schema. Default: the org's dbt output schemas (transformed data). Configurable per org. |
| 3. Limits | `LIMIT` injected/clamped via AST (default 100 rows, max 500). Statement timeout: Postgres `SET LOCAL statement_timeout`; BigQuery job timeout + `maximum_bytes_billed`. Result cells truncated before reaching the LLM. |
| 4. Access gating | `OrgFeatureFlag` `CHAT_WITH_DATA` per org, plus new RBAC (role-based access control) permission `can_use_chat_with_data`, following the existing `@has_permission` pattern. |
| 5. Audit | Every executed query recorded: org, user, SQL, row count, duration, success/error. |

**Known limitation (stated, not hidden):** read-only is enforced at the SQL
layer, not the credential layer — Dalgo's warehouse credentials are read-write.
A dedicated read-only warehouse role per org is the right defense-in-depth and
is a fast-follow, not v1.

---

## 8. Sessions, memory, transport

### Session model

One new Django model: `ChatWithDataSession` (org, orguser, title, `thread_id`,
timestamps, soft-delete). **Message content is not duplicated into Django** —
the LangGraph Postgres checkpointer is the single source of truth. The history
endpoint reads the checkpointer thread and maps it to UI messages. One store,
no sync bugs.

### REST APIs (Django Ninja)

| Endpoint | Purpose |
|---|---|
| `POST /chat-with-data/sessions/` | New session |
| `GET /chat-with-data/sessions/` | List my sessions |
| `PUT /chat-with-data/sessions/{id}` | Rename |
| `DELETE /chat-with-data/sessions/{id}` | Soft-delete |
| `GET /chat-with-data/sessions/{id}/messages` | History (from checkpointer) |

### WebSocket streaming

New consumer at `ws/chat-with-data/<session_id>/`, reusing the existing
`ddpui/websockets` auth. The agent runs **directly in the async consumer** —
no Celery hop — because that is what makes native LangGraph token streaming
work (`astream` with `messages` + `updates` modes).

Trade-off accepted for v1: if the socket drops mid-turn, that turn dies (the
conversation up to it survives in the checkpointer). Turns are seconds long.
Protections: one in-flight turn per session (lock) + per-user rate limit.

Event protocol (typed, versioned):

```
token            streamed assistant text
tool_start       {tool, friendly_label, sql?}   "Running query…" + view-SQL
tool_end         {tool, status}
message_complete final message + structured result table for the UI
error            user-friendly failure
title_updated    auto-generated session title
```

### Memory

Checkpointer thread per session = follow-ups work for free ("compare that to
last month" — "that" is in the message history). Pre-model hook trims old
turns. Session title auto-generated after the first exchange (one cheap
Haiku call).

---

## 9. Observability

- Structured logs via existing `CustomLogger`, one request UUID per turn.
- Per-turn audit record: token usage, latency, tools called, SQL executed (§7 layer 5 — the audit table).
- Sentry's LangGraph integration enabled (already ships in the installed SDK).
- Optional LangSmith tracing behind an env var, **off** by default (org data
  must not leave the deployment unless explicitly enabled).

---

## 10. Frontend (webapp_v2)

Sidebar nav entry **"Chat with Data"** — rendered only when the org feature
flag and user permission allow. Dedicated page:

```
┌────────────┬──────────────────────────────────────┐
│ Sessions   │  Priya: How many surveys in Pune     │
│  ● Pune s… │        last month?                   │
│  ○ Water … │  ⚙ Looking at your tables…           │
│  ○ Attend… │  ⚙ Running query…  [view SQL ▸]      │
│            │  Agent: 1,284 surveys in June.       │
│ [+ New]    │  ┌─────────────┬───────┐             │
│            │  │ district    │ count │  (table)    │
│            │  └─────────────┴───────┘             │
│            │  [type a question…            send]  │
└────────────┴──────────────────────────────────────┘
```

- **Progress chips** in plain language while tools run; generated SQL behind a
  collapsible "view SQL" toggle — visible activity for Priya, transparency for
  the data-savvy.
- **Result tables** render from the structured `message_complete` payload
  (first 100 rows, scrollable) — not markdown blobs.
- **`useChatWithData` hook** owns the WebSocket lifecycle: connect, send,
  reduce events into message state, reconnect with backoff.
- SWR for session REST APIs, Shadcn components, per webapp_v2's CLAUDE.md.
- Built for slow connections and old devices: streaming makes waits feel
  short; no heavy chart libraries in v1.

---

## 11. Testing

| Layer | Approach |
|---|---|
| SQL guard | Heaviest coverage. Unit tests incl. the old review's bypass catalog: multi-statement via comments, `COPY`, CTEs named after keywords, DML inside CTEs, allowlist escapes, LIMIT clamping — both dialects. |
| Tools | Unit tests with mocked `WarehouseFactory`. |
| Agent loop | Scripted fake chat model (deterministic tool-call sequences): happy path, SQL-error-then-recovery, retry exhaustion, recursion limit. |
| WS consumer | Channels test client: auth, event sequence, one-turn lock. |
| REST APIs | Standard Ninja API tests for session CRUD + history. |
| Frontend | Hook tests (event reduction, reconnect) + component render tests. |
| Live check | Script running a real session against a dev warehouse end to end. |

---

## 12. Future tools (explicitly out of v1, enabled by the registry)

Chart generation, dashboard creation, report generation, saved queries, data
exports, notifications/alerts. Each is one new tool module (§5 — the registry
pattern); none require graph changes. If the tool count grows large enough that
one agent's prompt gets crowded, the promotion path is a supervisor multi-agent
graph — state and tools are designed to survive that move unchanged.
