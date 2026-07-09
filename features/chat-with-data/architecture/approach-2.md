# Approach 2 — TurnGraph: the pipeline as a hand-built graph

**Status:** CURRENT (running on `feature/chat-with-data` in DDP_backend + webapp_v2)
**Date:** 2026-07-09 (TurnGraph) · updated same day with the answer contract (§6)
and the end-to-end turn walkthrough (§3) · supersedes [`approach-1.md`](./approach-1.md)
**What changed:** (1) the turn pipeline moved from Python control flow in
`runner.py` into our first hand-built LangGraph; (2) answers became structured —
a prompt-side answer template paired with a frontend markdown-subset renderer.
Everything else — tools, guard, brains, WebSocket protocol — is unchanged from
Approach 1.

Acronyms: LLM (large language model) · WS (WebSocket) · BM25 (a classic
keyword-ranking algorithm, no ML involved) · HITL (human-in-the-loop).

---

## 1. What this system is (unchanged)

A chat page where an NGO program manager (Priya) asks questions in plain
English; an agent inspects her org's warehouse, writes guarded read-only SQL,
streams back the answer, and can create charts and dashboards. See
[`approach-1.md`](./approach-1.md) §1–§3 for the layers that did not move:
the three-layer rent-vs-own stack, the five brains, tools + `RunContext`
tenancy, middleware, and the SQL guard.

## 2. The TurnGraph — actual topology

`ddpui/core/chat_with_data/graph.py` builds it; this diagram is printed from
`get_graph().draw_mermaid()` and pinned by a shape test
(`test_graph.py::test_graph_shape_matches_the_approach_2_diagram`) — the doc
cannot silently drift from the code.

```
START → route_node ──┬─ small talk        → casual_reply_node → END
                     ├─ needs clarify*    → clarify_node      → END
                     └─ data question     → retrieve_context_node
                                            (*first turn only)  ↓
                                            sql_agent (the Approach-1 compiled
                                            agent, mounted as a SUBGRAPH node)
                                                                ↓
                                            validate_node → END
```

**The rule:** stages are nodes; brains stay in `calls/`. A node is a thin
adapter that calls `router.py` / `validator.py` — no logic moved.
**Example:** `route_node` calls the same `route_question()` Haiku call the
runner used to call; its output now lands in `state["route"]` (checkpointed)
instead of a local Python variable.
**Why it matters:** every stage is now visible — named in traces and
`updates` streams with per-stage timing, replayable from the checkpoint, and
drawable. "Where did this turn spend its time?" is a query, not a grep.

### TurnState

```python
class TurnState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]  # shared with the agent subgraph
    question: str
    route: dict          # router verdict — in the checkpoint
    has_history: bool    # first-turn flag for the clarify divert
    validation: dict | None  # validator verdict — in the checkpoint
```

## 3. The journey of one question — end to end

What exactly happens when Priya hits Enter, layer by layer:

```
BROWSER (webapp_v2)
  ChatPane input ──► WebSocket already open for this session (cookie JWT)
                     sends {"action": "send_message", "message": "how many surveys?"}
        │
        ▼
CONSUMER  websockets/chat_with_data_consumer.py
  connect-time gates (already passed): JWT cookie → OrgUser · can_use_chat_with_data
  permission · CHAT_WITH_DATA feature flag · AI consent (llm_optin) · warehouse exists
  · session belongs to this user
  per-message gates: rate limit (10/min, Redis) · turn lock (one question at a
  time per session, Redis, 180s TTL)
        │
        │  build_run_context(orguser)          agent/context.py
        │  = the ONLY ORM/credentials touch: warehouse client, allowed schemas,
        │    chart/dashboard permissions → RunContext (the model never sees org ids)
        ▼
RUNNER  runner.py — builds the TurnGraph, streams it, translates events
        │  Langfuse trace starts · thread_id = session's checkpointer thread
        ▼
TURNGRAPH  graph.py (each box = a real graph node, checkpointed in Postgres)
        │
   route_node ── one Haiku call; sees the conversation tail; fail-open
        │
        ├── small talk ────────► casual_reply_node ──► END   (agent never runs)
        ├── vague FIRST turn ──► clarify_node ───────► END   ("Compare what to what?")
        └── data question
                │
        retrieve_context_node   (no-op today — M5 will inject BM25 table cards here)
                │
        sql_agent  ◄─ the compiled agent, mounted as a subgraph
        │   middleware: org system prompt (dialect + answer template) ·
        │   history trim · 3-failed-SQLs limiter · old-tool-result clearing
        │   model (Sonnet 5) ⇄ tools loop:
        │     list_tables / get_table_details / profile_column   (discovery)
        │     execute_sql ─► sqlglot AST GUARD (single SELECT only, schema
        │        allowlist, LIMIT clamp) ─► reflection critique (complex lane
        │        only) ─► warehouse. Errors return AS TEXT so the model retries.
        │     create_chart / dashboards tools (permission-gated via RunContext)
                │
        validate_node ── Haiku checklist over THIS turn's SQL + result + answer
                │         → state.validation → END
        ▼
RUNNER translates the stream into WS events, in this order:
  tool_start/tool_end (chips: "Running query…" + view SQL)
  token, token, token…        (ONLY from the agent's model node — router/
                               validator tokens can never leak)
  message_complete            (answer text + result table + chart chips + token usage)
  validation                  (only if verdict = warn → amber strip)
  title_updated               (first turn: Haiku names the session)
        ▼
BROWSER  reducer applies events → MessageBubble renders the answer through
  AssistantMarkdown (bold · bullets · ### topics · teal callout · code chips)
  + ResultTable + chart links + "Worth checking:" strip
```

Three things persist after the stream ends (in a `finally:` — even on failure):

| Store | What | Why |
|---|---|---|
| LangGraph Postgres checkpointer | the full message thread | follow-ups have memory; history survives refresh |
| `ChatWithDataTurnAudit` (Django) | question, SQL(s), tools, tokens, latency, route intent, validation verdict | the evaluation layer — eval golden datasets grow from here |
| Langfuse trace | per-stage spans + `result_validation` score | "where did this turn spend its time" is a query |

**Failure behavior is deliberate and asymmetric.** The router, reflection, and
validator all **fail open** — a broken helper can never block a real question;
worst case you get v1 behavior. The SQL guard **fails closed** — no parse, no
execution. If the model itself dies mid-turn, the user gets one friendly error
event and the audit row is still written with `status="failed"`.

## 4. What the graph replaced in runner.py

| Approach 1 (runner.py Python) | Approach 2 (graph) |
|---|---|
| `route_question()` call, then `if diverts:` | `route_node` + a conditional edge |
| `_short_circuit_turn()` + manual `aupdate_state` to record small talk into memory | `casual_reply_node` / `clarify_node` — inside the graph, so the exchange checkpoints naturally |
| `_thread_tail()` peeking at state via `aget_state` | `route_node` reads `state["messages"]` directly |
| `validate_turn()` call after the stream | `validate_node` writing `state["validation"]` |
| — (didn't exist) | `retrieve_context_node`, a named no-op M5 fills with BM25 table cards |

`runner.py` (326 → ~260 lines) is now pure event translation: it streams the
TurnGraph with `astream(..., stream_mode=["messages","updates"], subgraphs=True)`
and maps namespaced chunks onto the **unchanged** WS protocol. The consumer
and the entire frontend were not touched; the 9 pre-existing runner tests
pass unmodified — that was the milestone's regression harness.

## 5. Mechanics that make it low-risk

**Subgraph mounting.** `create_agent`'s compiled graph is passed straight to
`add_node("sql_agent", agent)` — it reads/writes the parent's `messages`
channel by name, no wrapper.

**Checkpointer on the parent only.** The parent compiles with the saver
(`runner` reuses `agent.checkpointer`); the subgraph inherits it
per-invocation. Same `thread_id`, same default namespace, so existing
production threads and the history-replay endpoint (which reads
`channel_values.messages` from the raw checkpoint) keep working — the state
gains channels (`route`, `validation`), which is additive.

**Injected brains.** `build_turn_graph(agent, route_fn=…, casual_reply_fn=…,
validate_fn=…)` — the runner passes its own module globals at call time. This
keeps them patchable per-turn (the hermetic test fixtures depend on it) and
avoids a circular import between `graph.py` and `runner.py`.

**Token gating.** With brains inside the graph, their LLM calls would stream
into `messages` mode. The runner forwards tokens only from the agent's
`model` node — router/validator/casual-reply output can never leak into
Priya's chat. (This absorbed audit fix M0-0.2.)

## 6. The answer contract — prompt ⇄ renderer (added 2026-07-09)

Answers are structured by a two-sided contract between the repos:

| Side | File | Role |
|---|---|---|
| DDP_backend | `agent/prompts.py` "How to answer" | teaches the answer SHAPE and names the only formatting allowed |
| webapp_v2 | `components/chat-with-data/AssistantMarkdown.tsx` + `markdown.ts` | renders exactly that subset; everything else stays literal text |

**The shape:** bold headline number first → structure scaled to answer size
(a single fact stays one sentence; 3+ items become "- " bullets; long
multi-topic answers get "### " headings) → at most one "> " key-insight
callout (rendered as a teal highlight strip) → one closing line on how the
answer was computed. Numbers use thousands separators.

**Example (real output, browser-verified):** "Break down our surveys by
country" → bold **1,818** headline, three bullets (India **908**, Uganda
**765**, Indonesia **145**), a teal callout flagging Indonesia's low count as
a possible data-collection gap, then "Source: `prod.classroom_surveys_merged`,
grouped by `country`."

**Why hand-rolled, not react-markdown:** the renderer is an allowlist by
construction — links and raw HTML render as literal text (pinned by a test),
so a misbehaving model cannot inject them; zero added bundle weight for slow
connections; no ESM/Jest friction. One concession from live testing: models
wrap table names in backticks despite the ban, so single backticks render as
a subtle code chip instead of literal backticks.

**Drift guard:** a backend test
(`test_system_prompt_allows_exactly_the_markdown_subset_the_ui_renders`)
pins the prompt's allowed-formatting list to what the renderer styles — the
cross-repo contract fails a build instead of silently rotting. History
replays through the same renderer; pre-change plain-text answers render
unchanged.

## 7. Design rules — carried forward and new

Rules 1–5 of Approach 1 §6 stand (frozen agent topology; single calls for
single jobs; every auxiliary brain fails open; contracts from real consumers;
everything measured). New with this approach:

6. **The pipeline graph is ours to rewire; the agent subgraph is not.**
   New stages (decomposer, HITL approval) enter as parent nodes/edges; the
   agent still only grows through its tool registry and middleware.
7. **The diagram is a test.** Any topology change must update the shape test —
   which forces updating this document's diagram too.
8. **Validation sees one turn.** `validate_node` extracts SQL/results only
   from messages after the last user message — a turn-2 verdict can never be
   contaminated by turn-1 queries.
9. **Formatting is a two-sided contract.** The prompt may only permit what
   the renderer styles (§6); either side changing alone is a bug, and a test
   on the backend enforces the pairing.

## 8. What this unlocks (earmarked, not built)

| Capability | First concrete use |
|---|---|
| `retrieve_context_node` body | M5: BM25 over enrichment-agent table cards — latency roughly halves on simple questions |
| `interrupt()` at stage boundaries | HITL "approve before creating this dashboard", durable across a disconnect |
| `Send` API fan-out from a new branch | Phase-3 decomposer for multi-table comparisons (evidence-gated via Langfuse) |
| Per-stage state in the checkpoint | pause/resume + stage-level eval slices |

## 9. Known constraints

Approach 1 §7 still applies (first-question latency, protobuf pin,
single-table charts, SQL-layer read-only). Additionally:

- **The M0 audit fixes are still open** — most importantly the P1
  (`trim_history` is a silent no-op, long threads are not being trimmed).
  M-G shipped before M0 by an explicit priority call on 2026-07-09; M0 must
  land before the PRs go up.
- A stale `validation` value from a previous data turn remains in thread
  state after a later small-talk turn (harmless: events only ever emit from
  the current turn's `validate_node`).
- Traces now start before routing, so short-circuit turns also get Langfuse
  traces (Approach 1 only traced agent turns). More visibility, slightly more
  trace volume.
