# Approach 2 — TurnGraph: the pipeline as a hand-built graph

**Status:** CURRENT (running on `feature/chat-with-data` in DDP_backend + webapp_v2)
**Date:** 2026-07-09 · supersedes [`approach-1.md`](./approach-1.md)
**What changed:** the turn pipeline moved from Python control flow in `runner.py`
into our first hand-built LangGraph. Everything else — tools, guard, brains,
WebSocket protocol, frontend — is unchanged from Approach 1.

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

## 3. What the graph replaced in runner.py

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

## 4. Mechanics that make it low-risk

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

## 5. Design rules — carried forward and new

Rules 1–5 of Approach 1 §6 stand (frozen agent topology; single calls for
single jobs; every auxiliary brain fails open; contracts from real consumers;
everything measured). New with the TurnGraph:

6. **The pipeline graph is ours to rewire; the agent subgraph is not.**
   New stages (decomposer, HITL approval) enter as parent nodes/edges; the
   agent still only grows through its tool registry and middleware.
7. **The diagram is a test.** Any topology change must update the shape test —
   which forces updating this document's diagram too.
8. **Validation sees one turn.** `validate_node` extracts SQL/results only
   from messages after the last user message — a turn-2 verdict can never be
   contaminated by turn-1 queries.

## 6. What this unlocks (earmarked, not built)

| Capability | First concrete use |
|---|---|
| `retrieve_context_node` body | M5: BM25 over enrichment-agent table cards — latency roughly halves on simple questions |
| `interrupt()` at stage boundaries | HITL "approve before creating this dashboard", durable across a disconnect |
| `Send` API fan-out from a new branch | Phase-3 decomposer for multi-table comparisons (evidence-gated via Langfuse) |
| Per-stage state in the checkpoint | pause/resume + stage-level eval slices |

## 7. Known constraints

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
