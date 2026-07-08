# Research: What LangGraph Prescribes for Our Pipeline

**Date:** 2026-07-08
**Sources:** LangGraph official "Workflows & Agents" patterns doc, LangGraph
"Use subgraphs" doc, community best-practices guide (Swarnendu De, Sep 2025),
GoPie source (comparative), our own audit/latency data.
**Question:** should the turn pipeline (route → retrieve → SQL agent → validate)
be a real LangGraph graph instead of Python orchestration in `runner.py`?

**Answer: yes — as a WORKFLOW graph that wraps the agent as a subgraph node.**
LangGraph's own guidance: *"Workflows beat agents when predetermined paths,
clear steps, and fixed task decomposition apply — better performance and
debuggability. Combining them: workflows provide structure for predictable
components; agents handle autonomous problem-solving within workflows."*
Our pipeline IS a predetermined path with one autonomous component in the
middle. That is precisely the shape they name.

---

## 1. Our stages map 1:1 onto LangGraph's official pattern catalog

| Our stage | Official pattern | Primitive |
|---|---|---|
| Query understanding | **Routing** | node with structured output + `add_conditional_edges` |
| Schema retrieval (Phase 2) | plain workflow node | no LLM — BM25 over table cards |
| SQL generation | **Agent** | `create_agent` graph mounted **as a subgraph node** |
| Reflection | **Evaluator-Optimizer** | already realized *inside* `execute_sql` (error-as-observation loop + pre-execution check); stays there — a graph-level evaluator would have to intercept tool calls |
| Validation | evaluator (one-way) | node after the agent |
| Answer synthesis | agent's final message | — |
| Decomposer (Phase 3) | **Orchestrator-Worker** | `Send` API fan-out — slots in later as another branch |

## 2. Subgraph mechanics (why the agent drops in cleanly)

- `create_agent` returns a compiled graph; **all subgraph rules apply directly**.
- Shared state key (`messages` with `add_messages`) → pass the compiled agent
  straight to `add_node("sql_agent", agent)` — no wrapper, it reads/writes the
  parent's `messages` channel.
- Checkpointing: compile only the **parent** with our `AsyncPostgresSaver`;
  the subgraph inherits it per-invocation (the recommended default). Same
  `thread_id` keys the whole turn. Existing threads keep working — the state
  gains channels (`route`, `validation`), which is additive.
- Streaming: `astream(..., subgraphs=True)` yields namespaced chunks — the
  runner's event mapping handles `(namespace, mode, chunk)` instead of
  `(mode, chunk)`.

## 3. Community best-practices checklist vs us

| Practice (article) | Us today | After TurnGraph |
|---|---|---|
| Typed, minimal state; reducers only where needed | agent-only state | `TurnState(messages+route+validation)` |
| Conditional edges only at real branches | branches live in Python `if`s | route branch becomes a real conditional edge |
| Bounded cycles | ✅ recursion_limit + 3-SQL limiter | unchanged |
| Postgres checkpointer, thread_id first-class | ✅ | ✅ whole turn checkpointed, not just the agent |
| Stream modes deliberately | ✅ messages+updates | + `subgraphs=True` |
| Error handling node/graph/app level | Python try/except | route/validate stay fail-open; graph edges make fallbacks explicit |
| HITL interrupts on sensitive actions | ❌ none | becomes POSSIBLE at graph level (e.g. approve dashboard creation) — checkpointer makes pause/resume durable |
| Test graphs, not just functions | runner event tests | + graph-shape assertions (nodes/edges) |
| Supervisor → specialists | N/A | explicitly NOT adopting (GoPie's 25-node lesson); decomposer later via `Send`, not a supervisor |

## 4. Target design — the TurnGraph

```
TurnState: {messages (shared w/ agent), route, validation, question}

START → route_node ──(conditional edge)──┬─ small_talk  → casual_reply_node → END
                                         ├─ clarify*    → clarify_node      → END   (*first turn only)
                                         └─ data_question
                                              ↓
                                    retrieve_context_node        [Phase 2: BM25 over table cards;
                                              ↓                   until cards exist: no-op]
                                    sql_agent  (create_agent SUBGRAPH — unchanged)
                                              ↓
                                    validate_node → END
```

The stage *brains* stay exactly where they are (`router.py`, `validator.py`,
`retrieval.py`) — graph nodes are thin adapters calling them. `runner.py` stops
orchestrating stages and becomes pure event translation. The WS event protocol
does not change → consumer and frontend untouched.

**What this buys** (the user's "I don't see the agents" concern, answered
structurally): `agent.get_graph().draw_mermaid()` now draws the actual pipeline;
every stage is a named node in traces and `updates` streams with per-stage
timings; per-stage state is in the checkpoint; HITL interrupts become available
at stage boundaries.

**What it costs:** runner streaming rework (namespaced chunks) — the one real
piece of work; everything else is adapters. Est. 1–2 days including tests,
before resuming Phase 2's enrichment content.

## 5. Recommended order

1. **M-graph:** build `graph.py` (TurnState + nodes + edges), rewire
   `runner.py` streaming, keep the event contract identical (existing runner
   tests must pass unmodified — that's the regression harness).
2. **M5 (resumes):** enrichment agent + table cards + BM25 → the
   `retrieve_context_node` body.
3. Later: HITL interrupt before dashboard/chart writes; Phase 3 decomposer via
   `Send` as a new branch.
