# Approach 1 — Compiled Agent Loop with Staged Calls

**Status:** CURRENT (running on `feature/chat-with-data` in DDP_backend + webapp_v2)
**Date:** 2026-07-08 · covers v1 (M1–M5) + v2 Phase 1 + chart/dashboard tools
**Convention:** this folder versions our architecture. When the architecture
materially changes (e.g. the TurnGraph lands), we write `approach-2.md` and
mark this one SUPERSEDED — the docs never silently drift.

Acronyms: LLM (large language model) · AST (abstract syntax tree — parsed SQL
structure) · WS (WebSocket) · RBAC (role-based access control).

---

## 1. What this system is

A chat page where an NGO program manager (Priya) asks questions in plain
English; an agent inspects her org's warehouse, writes guarded read-only SQL,
streams back the answer with a result table, and can create charts and
dashboards on request. Backend: `DDP_backend/ddpui/core/chat_with_data/`.
Frontend: `webapp_v2/app/chat-with-data/`.

### One turn, end to end

```
Priya's question ──► WS consumer (JWT cookie · permission · flag · llm_optin
                     consent · session ownership · rate limit · turn lock)
                          │ builds RunContext (org, warehouse client,
                          │ allowed schemas, permissions)   context.py:46
                          ▼
                 runner.run_turn  ← the transport-independent core
                          │
   STAGE 1  route_question (Haiku call, fail-open)        runner.py:75
            sees question + conversation tail; small talk / first-turn
            clarification short-circuit — the agent never runs for them
                          ▼
   STAGE 3  SQL AGENT — the ONE compiled graph            agent.py:47
            model (claude-sonnet-5) ⇄ ToolNode loop, 8 registry tools,
            Postgres-checkpointed memory per session thread
            execute_sql gauntlet: sqlglot AST guard → reflection
            (Haiku, complex lane only) → warehouse, errors return AS TEXT
                          ▼
            answer streams (thinking blocks stripped → text only)
                          ▼
   STAGE 5  validate_turn (Haiku call, after the answer, never blocks)
            grain / missing-filter / false-zero / number-match checks
            → "validation" WS event → amber caveat strip → audit column
            → Langfuse score                              runner.py:205
```

Stages 2 (schema retrieval via table cards) and the explicit pipeline graph
are Approach 2 territory — designed, not yet built (see §8).

---

## 2. The three-layer stack and who owns what

```
┌─ OURS (the differentiating layer) ────────────────────────────────┐
│ runner pipeline · sqlglot guard · RunContext tenancy · WS protocol│
│ router/validator/reflection/titles · audit rows · Langfuse handler│
├─ LANGCHAIN (the vocabulary) ──────────────────────────────────────┤
│ ChatAnthropic · @tool + ToolRuntime · middleware · create_agent   │
│ messages / callbacks (langchain_core)                             │
├─ LANGGRAPH (the machine) ─────────────────────────────────────────┤
│ CompiledStateGraph · state channel + reducer · Postgres           │
│ checkpointer · astream · aget/aupdate_state · recursion_limit     │
└───────────────────────────────────────────────────────────────────┘
```

**The rule:** rent everything that isn't differentiating; own only what is.
**Example:** the agent loop (threading messages across tool calls, parallel
tool execution, streaming) is rented via `create_agent`; the SQL guard is
ours because no library knows Dalgo's threat model.
**Why it matters:** the predecessor branch hand-rolled the loop — ~8,300
lines, died with a bypassable regex SQL guard. This split is the lesson.

Pinned versions: `langchain==1.3.11`, `langgraph==1.2.7`,
`langchain-anthropic==1.4.8`, `langgraph-checkpoint-postgres==3.1.0`,
`sqlglot==30.12.0`, `langfuse==2.60.10` (v2 SDK — see §7), `rank-bm25`
(staged for Approach 2).

---

## 3. Where we use LANGCHAIN, and why

### 3.1 `ChatAnthropic` — one interface, five brains

| Brain | Model (env override) | Job | Kind |
|---|---|---|---|
| SQL agent | `claude-sonnet-5` (`CHAT_WITH_DATA_MODEL`) | the loop | **agent** |
| Router | `claude-haiku-4-5` (`…_ROUTER_MODEL`) | intent/complexity/entities | one call |
| Validator | haiku (`…_VALIDATOR_MODEL`) | post-execution audit | one call |
| Reflection | haiku (`…_REFLECTION_MODEL`) | pre-execution SQL critique, complex lane | one call |
| Titles | haiku (`CHAT_WITH_DATA_TITLE_MODEL`) | session naming | one call |

**Why LangChain here:** identical `.ainvoke()` + message types across all
five; swapping any brain is an env var, not a refactor. Note: Claude 5
models reject `temperature` — behavior is tuned by prompts (and the `effort`
knob, staged).

### 3.2 `@tool` + `ToolRuntime[RunContext]` — the tenancy mechanism

Every tool (all in `tools/`) declares `runtime: ToolRuntime[RunContext]`.
LangChain strips that parameter from the schema the model sees and injects it
at execution time.

**The rule:** all tenant facts (org id, warehouse client, allowed schemas,
permissions) travel in the injected context; the model can only supply
domain arguments (`sql`, `title`, …).
**Example:** the model cannot query another org by hallucinating an org id —
there is no parameter for one to land in.
**Why it matters:** multi-tenant isolation holds *by construction*, not by
prompt instruction.

Second tool feature we rely on: `response_format="content_and_artifact"` —
compact text goes to the model; the full result table / chart link rides the
`ToolMessage.artifact` to the UI without spending prompt tokens.

### 3.3 Middleware — house rules without graph surgery (`middleware.py`)

| Middleware | Kind | Effect |
|---|---|---|
| `org_system_prompt` (`@dynamic_prompt`) | inside model node | per-org, dialect-aware system prompt rebuilt every call |
| `trim_history` (`@before_model`) | **becomes a graph node** | caps request at 60K tokens; checkpoint keeps full history |
| `sql_retry_limiter` (`@before_model`, `can_jump_to=["end"]`) | **becomes a graph node** | 3 failed SQLs → apology + deterministic loop exit |
| `ContextEditingMiddleware` | inside model node | clears bulky old tool results past 40K tokens |

**Why it matters:** middleware is the sanctioned customization channel —
two weeks of feature work (charts, dashboards, router, validator) changed
the compiled graph's topology **zero** times.

### 3.4 `create_agent` — the factory (`agent.py:47`)

The single line that assembles model + tools + middleware + `context_schema`
+ checkpointer into a compiled LangGraph. History note: `create_agent` is
LangChain's successor to LangGraph's deprecated `create_react_agent` — the
API is LangChain's; the object it returns is pure LangGraph.

### 3.5 `langchain_core` messages & callbacks

The common types every layer speaks (`AIMessage`, `ToolMessage`, content
block lists). Two of our components exist *because* these types are open:
`content.extract_text()` (strips claude-sonnet-5's signed thinking blocks —
adaptive thinking is on by default and content arrives as block lists), and
`observability.LangfuseTurnHandler`, a hand-rolled `BaseCallbackHandler`.

---

## 4. Where we use LANGGRAPH, and why

### 4.1 The compiled graph — actual topology (printed via `get_graph()`)

```
__start__ → sql_retry_limiter.before_model ─► __end__   (limiter escape)
                     ↓
            trim_history.before_model
                     ↓
                   model ───────────────────► __end__   (no tool calls)
                     ↓ (tool calls)
                   tools  ──loops back──↑
```

Two library nodes (`model`, `tools`), two nodes generated from our
`@before_model` decorators, all edges inferred. **We have never written
`add_node`/`add_edge`** — that is the defining property of Approach 1.

### 4.2 Capabilities we exercise

| Capability | Where | What it gives the product |
|---|---|---|
| Loop + conditional edges + `recursion_limit=25` | `runner.py:107` | multi-step tool use with a runaway backstop |
| **Postgres checkpointer** (`AsyncPostgresSaver`, `checkpointer.py`) | thread per session (`ChatWithDataSession.thread_id`) | follow-up questions, history replay after refresh, memory that survives restarts |
| `aget_state` | `runner.py:308` | router reads the conversation tail without running the graph |
| `aupdate_state` | `runner.py:273` | small-talk turns recorded into memory though the agent never ran |
| Two-mode streaming `astream(["messages","updates"])` | `runner.py:122` | token typing effect + tool chips/artifacts per node completion |
| Parallel tool calls (ToolNode) | free | "create all of them" → 5 `create_chart` calls in one turn |

### 4.3 Capabilities we deliberately do NOT use (yet)

Hand-built `StateGraph`, custom reducers beyond `add_messages`, `Send` API
fan-out, `interrupt()` (human-in-the-loop), cross-thread `Store`. Each is
earmarked in the Approach 2 design with a concrete first use.

---

## 5. The layer that is OURS

| Component | File | What it does |
|---|---|---|
| Turn pipeline | `runner.py` | route → agent → validate orchestration + WS event protocol (`token`, `tool_start/end`, `message_complete`, `validation`, `error`, `title_updated`) |
| SQL guard | `guards/sql_guard.py` | sqlglot AST: single SELECT only (by node type), schema allowlist, LIMIT clamp — the only execution path |
| RunContext | `state.py`, `context.py` | server-resolved tenancy; the ONLY place that reads ORM/credentials |
| Router / Validator / Reflection / Titles | own modules | four fail-open Haiku calls (see §6 rule 2) |
| Registry | `tools/registry.py` | 8 tools: 4 discovery, `execute_sql`, `create_chart`, `list_dashboards`, `create_dashboard`/`add_charts_to_dashboard` |
| Audit | `ChatWithDataTurnAudit` | per turn: question, SQL(s), tools, tokens, latency, route intent, validation verdict — the evaluation layer |
| Langfuse handler | `observability.py` | hand-rolled (dbt pins protobuf<5 → v3 SDK impossible; v2 SDK's bundled handler needs pre-1.x langchain); env-gated, fail-safe |
| Consumer + REST | `websockets/chat_with_data_consumer.py`, `api/chat_with_data_api.py` | auth/gating/locks; session CRUD + history replay |

Storage split: **messages live only in the checkpointer** (one source of
truth); Django keeps session metadata, audit rows, and artifacts (Chart /
Dashboard, created through the same services the UI uses, storing the exact
JSON shapes the builders store).

---

## 6. Design rules that define Approach 1

1. **Topology is frozen; evolution enters through registry tools, middleware,
   or calls around the loop.** A subagent enters as a tool wrapping its own
   graph — never as top-level rewiring.
2. **Single LLM calls, not agents, for single jobs.** Agent = tools +
   iteration. Router/validator/reflection/titles read one input and emit one
   JSON — no loop.
3. **Every auxiliary brain fails OPEN.** Router error → treat as data
   question; reflection error → execute; validator error → no strip. Nothing
   new can make the chat worse than v1.
4. **Contracts come from real consumers.** All three production bugs were
   contract mismatches (router vs conversation context; chart config vs the
   renderer's `dimension_column`; async view vs the sync `has_permission`
   wrapper) — read the consumer's actual data/behavior, not the docs in your
   head.
5. **Everything is measured.** Audit row + Langfuse trace per turn, joined by
   `request_uuid`; validator verdicts double as Langfuse scores.

---

## 7. Known constraints

- **Latency:** first questions 18–40s. Causes: RunContext rebuilt per message
  (secrets + catalog query), Sonnet 5 adaptive thinking on every call, schema
  re-discovery each session (2 extra model round trips). Fixes staged.
- **protobuf<5 pin** (dbt 1.8 stack) → Langfuse v2 SDK with our own handler;
  revisit at the dbt upgrade.
- **Charts are single-table, no top-N ordering** in saved configs.
- **Read-only enforced at the SQL layer**, not the credential layer —
  read-only warehouse role remains a fast-follow.
- **No auto-selected session after refresh** (UX gap, fix queued).

---

## 8. What Approach 2 will change (pointer, not spec)

Designed in [`../v2/research-langgraph-pipeline.md`](../v2/research-langgraph-pipeline.md)
and [`../v2/plan.md`](../v2/plan.md): the pipeline becomes our first
hand-built LangGraph **workflow graph** (`TurnState` = messages + route +
validation; route node + conditional edges; BM25 `retrieve_context_node` fed
by an offline **enrichment agent** building `ChatWithDataTableCard` rows; the
existing compiled agent mounted **as a subgraph node**). LangGraph's own
framing: *"workflows provide structure for predictable components; agents
handle autonomous problem-solving within workflows."* When it lands, that
document becomes `approach-2.md` and this one is marked superseded.
