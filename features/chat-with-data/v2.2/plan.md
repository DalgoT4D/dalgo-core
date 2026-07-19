# Chat with Data v2.2 — Human approval before chart creation (HITL)

## Context

Today the agent creates a chart the moment it decides to — Priya asks "chart silt by
state" and a saved chart appears in her org's chart library with no confirmation. This
slice adds a **human-in-the-loop gate on `create_chart`**: the agent proposes the chart,
the turn pauses, the UI shows a highlighted approval card ("Create this chart? — Bar
chart of silt_achieved by state, from ss_work_order_metric_niti_25"), and only an
explicit **Approve** creates it. **Cancel** tells the model the user declined and the
conversation continues gracefully.

This is the HITL pattern we deferred in the v3 plan with a written trigger — but the
trigger here is different and simpler than table approval: chart creation is a
**side-effect** (rows written to the org's chart library), and side-effects are the
canonical case for approval gates (PostHog: `is_dangerous_operation()` on the tool).
Table approval stays deferred pending the `eval_tables` signal; this slice gates a
*write*, not a *guess*.

### Why this is cheap: what already exists

| Need | Already there |
|---|---|
| The approval machinery | `HumanInTheLoopMiddleware` ships in our installed langchain 1.3.11 (`langchain.agents.middleware`) — `interrupt_on={tool_name: config}`, decisions approve/edit/reject/respond |
| Pause/resume durability | LangGraph `interrupt()` checkpoints to our existing Postgres saver — approval survives disconnects; resume is `Command(resume=…)` on the same thread_id |
| The seam to add it | `build_agent()`'s middleware list (`agent/chat_data_agent.py`) — one entry |
| Stream translation | `turn_runner.py` already translates graph events → WS protocol; interrupts surface as `__interrupt__` chunks in the same stream |
| Frontend chat plumbing | `useChatWithData` + `ChatPane` render typed WS events; approval card is one more event type + one send action |

### Key design decisions

- **Approve / Reject only in v1.** The middleware also supports "edit" (user modifies
  the args) and "respond" — both need real UI; deferred. Reject uses the middleware's
  built-in behavior: a ToolMessage telling the model the tool was not executed and not
  to retry unless asked.
- **Gate `create_chart` only.** `create_dashboard` / `add_charts_to_dashboard` are also
  writes and can join later — it's one dict entry each — but chart creation is the
  common path today. The config dict is the policy surface; no new code per tool.
- **The interrupt fires BEFORE the tool runs** (`after_model` hook inspects the
  proposed tool call) — `create_chart`'s body never executes until approval, so the
  research warning "keep pre-interrupt code side-effect-free" is satisfied by
  construction; the tool needs zero changes.
- **HITL is on for the product, off for harnesses.** `build_agent(approval=True)`
  default; the eval runner and REPL pass `approval=False` (no human present). An eval
  item asking for a chart must keep working headlessly.
- **A custom `description` callable renders the human-readable summary** (title, type,
  table, metrics, dimension) — this string is what the frontend highlights, so the
  model's raw args never need client-side interpretation.
- **The middleware is one more graph node.** The recursion-limit war story applies:
  `RECURSION_LIMIT` and `test_realistic_discovery_turn_fits_in_the_recursion_limit`
  must be re-verified with the new stack (the test exists precisely for this moment).

## Data flow

```
"chart silt by state"
      │
  agent loop: …discovery… → model proposes create_chart(…)
      │
  HITL middleware (after_model): create_chart is in interrupt_on
      │        └─► interrupt() — state checkpointed, stream yields __interrupt__
      ▼
  turn_runner: yields {"type":"approval_request", "request_id", "tool":"create_chart",
                       "summary":"Bar chart of silt_achieved by state…", "args":{…}}
      │        └─ stream ends; audit row status="awaiting_approval"; turn lock released
      ▼
  UI: highlighted approval card — [Approve] [Cancel]  (input disabled while pending)
      │
  WS: {"action":"approval_response", "decision":"approve"|"reject"}
      │
  consumer: run_turn(resume_decision=…) → graph.astream(Command(resume=…), same thread)
      │
  approve → tool executes → chart chip → message_complete (audit "completed")
  reject  → ToolMessage("user declined") → model acknowledges → message_complete
```

## Milestones

### H1 — Backend: middleware + pause (agent and runner)

- `agent/chat_data_agent.py`: `build_agent(…, approval: bool = True)`; when on, append
  `HumanInTheLoopMiddleware(interrupt_on={"create_chart": {"allowed_decisions":
  ["approve", "reject"], "description": _chart_approval_summary}})`. The summary fn
  formats args into one sentence + a details dict.
- `chat/turn_runner.py`: recognize the `__interrupt__` chunk in the update stream →
  yield `approval_request` event (request payload + summary), stop the stream cleanly,
  write the audit row with `status="awaiting_approval"` (new status value; no
  migration — CharField).
- `evals/runner.py` + `chat_with_data_repl.py`: pass `approval=False`.
- Re-check `RECURSION_LIMIT` headroom; update the regression test's expected node
  arithmetic.
- Tests (scripted model, no network): create_chart proposal pauses with the right
  payload; non-chart tools don't pause; `approval=False` never pauses.

### H2 — Backend: resume (consumer)

- `websockets/chat_with_data_consumer.py`: accept
  `{"action":"approval_response","decision":…}`; validate a paused turn exists for the
  session; invoke the resume path (`run_turn` gains `resume_decision`), reusing the
  same streaming/translation loop; turn-lock semantics: lock released at pause,
  re-acquired on resume.
- Reject path test: chart NOT created, model's follow-up text streams, audit completes.
- Approve path test: tool executes exactly once; chip event carries the chart id.
- Edge: approval_response with no pending interrupt → polite error event.

### H3 — Frontend: highlighted approval card

- `useChatWithData`: handle `approval_request` (state: pendingApproval), send
  `approval_response`; input disabled while pending.
- `ChatPane`/new `ApprovalCard.tsx`: visually prominent (accent border + chart icon —
  the "highlight" ask): summary line, details (type, table, metrics, dimension),
  **Approve** (primary) / **Cancel** (ghost) buttons; card collapses into a normal
  status line after the decision ("Chart approved ✓" / "Chart declined").
- Tests: card renders from event payload; buttons send the right action; input gating.

### H4 — Polish + docs

- History replay: a session closed while awaiting approval → on reconnect the pending
  card is re-derived from checkpoint state if cheap, else the turn shows as
  awaiting-approval text and the user re-asks (documented limitation for v1).
- `core/ai/CLAUDE.md`: document the approval seam (how to gate any tool: one dict
  entry) + the evals/REPL `approval=False` convention.

## Risks

- **Resume payload shape** (`HITLResponse` decisions list) is version-specific —
  pin with an integration-style test against the installed 1.3.11, not docs.
- **Subgraph interrupt propagation**: the agent is a mounted subgraph; verify the
  `__interrupt__` chunk surfaces through `astream(…, subgraphs=True)` with the parent
  checkpointer (H1's first test).
- **Turn-lock/rate-limit interplay**: approval_response must not be swallowed by the
  rate limiter or blocked by a stale lock.
- **Recursion budget**: one more after_model node per cycle — measured by the existing
  regression test, adjust limit if needed.
- **Abandoned approvals**: user closes the tab mid-approval; checkpoint keeps the turn
  paused indefinitely — acceptable (thread just stays resumable), noted in docs.

## Verification

- `uv run pytest ddpui/tests/core/ai ddpui/tests/websockets -v` — new + existing.
- Eval regression: both golden datasets with `--no-judge` — chart items must pass
  unchanged (headless `approval=False` path).
- REPL: unchanged behavior (no pause).
- Browser: ask for a chart → highlighted card appears → Cancel → no chart in library,
  polite acknowledgment → ask again → Approve → chart chip + chart in library.
