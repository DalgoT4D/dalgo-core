# How Dalgo uses Langfuse: production observability

*Everything except evals — those have their own writeup
(`DDP_backend/ddpui/core/ai/evals/README.md` and the eval report). This covers what
Langfuse records when real users use the AI features, and how to read it.*

All of it lives in one module: `ddpui/core/ai/tracing.py` (~230 lines). Two entry
points cover every AI feature: `start_turn_trace` for the chat agent,
`record_generation` for one-shot features.

---

## The one rule everything follows

**Tracing can never break the product.** Every call in `tracing.py` is wrapped; the
callback handler sets `raise_error = False`; if the Langfuse keys aren't set, tracing
is silently off and every function no-ops. A Langfuse outage costs us visibility,
never a chat turn. (Same fail-open discipline as the router and validator — tracing
is a helper, not a deliverable.)

## Why the integration is hand-rolled (a dependency story)

We don't use Langfuse's off-the-shelf LangChain integration, and the reason is a
chain of pins: our dbt 1.8 stack pins `protobuf<5` → which rules out the Langfuse v3
SDK (its OpenTelemetry core needs protobuf 5) → and the v2 SDK's bundled LangChain
handler imports pre-1.x langchain modules that no longer exist in langchain 1.x.

So we use the **v2 SDK's low-level client** (plain HTTP, still accepted by current
Langfuse servers) behind a **~100-line callback handler of our own**
(`LangfuseTurnHandler`). Owning the handler turned out to be a feature: we decide
exactly what gets recorded, clipped, named, and tagged.

## What a chat turn looks like in Langfuse

One turn = one trace, flat structure — the trace is the turn, each model call is a
generation, each tool call a span:

```
chat_with_data_turn                    ← trace (id = request_uuid)
├─ model_call     (router: intent)       generation — tokens, latency, cost
├─ model_call     (agent: thinks, picks list_tables)
├─ list_tables                           span — input/output, timing
├─ model_call     (agent: writes SQL)
├─ execute_sql                           span — the SQL in, rows-preview out
├─ model_call     (agent: final answer)
└─ score: result_validation              the post-answer audit's verdict
```

The handler maps LangChain callbacks one-to-one: `on_chat_model_start`/`on_llm_end`
→ generations (with token usage pulled from `usage_metadata`, which is what gives
the cost column), `on_tool_start`/`on_tool_end` → spans, and both error variants
end the observation with `level="ERROR"` and the message — which is exactly the red
ERROR span that made yesterday's streaming bug findable in one glance.

### The identifiers, and why each one is what it is

| Field | Value | Why |
|---|---|---|
| trace `id` | the turn's `request_uuid` | **Deterministic addressing**: the audit table row, the trace, and (future) feedback all share one id — anything that knows the request can find the trace without storing a second key |
| `session_id` | chat session id | Langfuse groups turns into conversations — you can read a whole session top to bottom |
| `user_id` | `orguser.id` (opaque integer) | Never emails or names — same privacy rule as our analytics |
| `tags` | `org_slug`, `dialect`, `scope:org` \| `scope:dashboard` | The three slicing axes: per-NGO usage, per-warehouse-type behavior, and main-page vs dashboard-drawer chats |
| `metadata` | `request_uuid`, `scope_type`, `scope_id`, final `status` | Cross-reference back to the audit row and the exact dashboard |

### What deliberately does NOT go in

- **Payloads are clipped at 4,000 chars** (`MAX_IO_CHARS`) — traces are for
  debugging, not archival. Full results live in the warehouse; full conversation
  state lives in the checkpoint.
- **PII never arrives**: the masking middleware rewrites conversation state *before*
  model calls, so what the callbacks observe is already masked.
- **Session titles and casual replies** aren't traced — they're helper calls whose
  failure modes don't need forensics. (The router IS traced, because it's on the
  critical path of every turn.)

## Scores on production traces

The post-answer audit (`validate_node`) writes its verdict onto the trace as a
`result_validation` score (1 = ok, 0 = warn, with the caveat as the comment). That
means Langfuse's score dashboards show answer-quality-as-judged-by-the-validator
across *all real traffic*, not just eval runs — a free, always-on quality signal
with zero extra model calls, since the audit runs anyway.

## One-shot features: `record_generation`

Features that make a single model call don't need a callback handler. The report
summary calls `record_generation(...)` after the fact — fire-and-forget, one trace
+ one generation, tagged with the org, carrying latency, token usage, status, and
the error message on failure. **Success or failure, every "Generate summary" click
becomes a trace.**

This is the template for every future one-shot AI feature: make the call, then one
`record_generation` line. No graph, no handler, same dashboards.

## How this connects to the rest of observability

Langfuse is one of three layers, each answering a different question:

| Layer | Question it answers | Where |
|---|---|---|
| **Langfuse trace** | *Why* did this turn behave this way? (model inputs/outputs, tool timings, errors, cost) | Langfuse UI |
| **Audit row** (`ChatWithDataTurnAudit`) | *What* happened, queryable in SQL: question, SQL executed, tools, tokens, latency, status per turn | Postgres |
| **WS events** | What the *user* saw, live | Frontend |

They're linked by `request_uuid`. The audit table is the durable system of record
(it survives Langfuse retention limits and works when tracing is off); the trace is
the forensic detail. In practice: start from an audit row or user report, take its
`request_uuid`, open that trace id in Langfuse, read the exact span that went red.

## Reading the dashboards: what we actually look at

- **Cost & tokens per turn** — the generations carry usage, so Langfuse computes
  cost per turn / per org (tag filter) / per model. This is how we know a chat turn
  costs ~$0.01 and where the 3.6k-token system prompt shows up.
- **Latency breakdown** — span timings tell you whether a slow turn was the model
  (generation seconds) or the warehouse (execute_sql span).
- **Error triage** — filter traces by ERROR level; the failing observation names
  the exact stage. Yesterday's incident diagnosis started from precisely this view.
- **Sessions view** — full conversations for UX review: where users rephrase,
  where they give up.
- **Filter evals OUT**: eval traces are tagged `eval` — production dashboards
  should exclude that tag, or the nightly golden runs pollute cost and quality
  numbers. (The one deliberate crossover: both worlds share the same score
  vocabulary, so `result_validation` on prod traces and `eval_*` scores on eval
  runs read side by side.)

## Ops notes

- **Config**: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
  (defaults to `http://localhost:3000` — we self-host). No keys → silently off.
- **Performance**: the v2 client batches events on a background thread; callbacks
  do no network I/O on the event loop.
- **Client lifecycle**: one singleton per process (`get_langfuse`), initialized
  lazily on first use.
- **Self-hosting caveat we hit**: Langfuse on ClickHouse 26.x needs
  `enable_analyzer=0` (upstream bug langfuse#14065) — ours is pinned via a mounted
  users.d config in the docker-compose.
