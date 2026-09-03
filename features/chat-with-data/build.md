# Chat with Data — How We Built It

**Date:** 2026-08-07 (written after the build; branch work ran 2026-07-04 → 2026-07-14)
**Status:** Built, in review — backend [DDP_backend#1429](https://github.com/DalgoT4D/DDP_backend/pull/1429), frontend [webapp_v2#343](https://github.com/DalgoT4D/webapp_v2/pull/343)
**Branches:** `feature/chat-with-data` on both repos
**Covers:** v1 (chat page + agent), v2 (routed turn pipeline), v2.1 (scoped sessions + report summaries), plus the production-readiness pass (restructure, PII, evals)

Acronyms: LLM (large language model) · AST (abstract syntax tree — the parsed structure of a SQL query) · WS (WebSocket) · RBAC (role-based access control) · PII (personally identifiable information) · HLD/LLD (high/low-level design).

This is the build record — what we actually did, in what order, and why. The pre-build artifacts are in [`v1/spec.md`](./v1/spec.md), [`v1/plan.md`](./v1/plan.md), [`v1/research.md`](./v1/research.md), [`v1/tasks.md`](./v1/tasks.md). The living technical map is `../DDP_backend/ddpui/core/ai/CLAUDE.md` — when this doc and that one disagree, that one wins.

---

## 1. What shipped

Priya (a program manager, not an engineer) asks *"how many surveys did we run in Maharashtra?"* on a chat page inside Dalgo. A LangGraph agent inspects her org's warehouse, writes a guarded read-only SQL query, runs it, and streams the answer back with a results table. Three surfaces:

1. **Chat page** (`/chat-with-data`) — persistent sessions, streaming answers, tool-progress chips, collapsible SQL, result tables.
2. **Dashboard chat drawer** — "Ask about this dashboard" opens a chat scoped to only that dashboard's tables.
3. **Report AI summaries** — one click drafts an executive summary from a report snapshot's data; nothing saves until the user clicks Save.

Scale: backend +10.5k lines across 103 files (52 commits); frontend +2.3k lines across 33 files. 184 backend tests + 51 frontend tests, all running against scripted fake models — zero API calls in CI.

## 2. Build timeline

We built in vertical milestones, safety-first: the SQL guard was **M1, before any agent existed**, so there was never a moment where a model could reach the warehouse unguarded.

| When (2026) | Milestone | What landed |
|---|---|---|
| 07-04 | **v1 M1** | AST SQL guard (sqlglot): single SELECT, forbidden-node blocklist, schema allowlist, LIMIT clamp — pure library code, red-team test suite first |
| 07-04 | **v1 M2** | Tool registry + 5 discovery/query tools; agent loop via langchain `create_agent` + middleware; Postgres checkpointer; terminal REPL harness |
| 07-04 | **v1 M3** | Django models (Session, TurnAudit), feature flag, `can_use_chat_with_data` permission, REST session CRUD |
| 07-05 | **v1 M4** | Async WebSocket consumer + turn runner streaming token/tool events |
| 07-07 | **v1 M5** | Frontend chat page: session sidebar, streaming UI, tool chips, result tables. Post-M5 polish: chart creation tool, Langfuse tracing |
| 07-08 | **v2 pipeline** | Router (intent + complexity), post-answer audit, pre-execution SQL reflection for complex queries, dashboard tools, async-permission fix |
| 07-09 | **TurnGraph** | Restructured the implicit flow into a real LangGraph graph with named nodes (route → retrieve → sql_agent → validate) and a graph-shape test pinning it to the design diagram |
| 07-11 | **v2.1** | Dashboard-scoped sessions (table allowlist through guard + discovery + prompt); report summary endpoint; frontend drawer + summary button |
| 07-11 | **Restructure** | Everything into `ddpui/core/ai/` with one artifact contract and a package CLAUDE.md as the map |
| 07-12 | **Production pass** | Multi-provider model factory, PII masking middleware, golden-set eval harness (2 datasets, 26 items), recursion-limit fix |
| 07-14 | Last substantive commit | `Dashboard.component_ids()` — one shared tabs-walk for reports, KPIs, and chat scope |

Everything after 07-14 is merges from main (RBAC v2, inline metrics, warehouse changes).

## 3. Architecture in one diagram

```
question ─► route ──┬─ small talk ──► canned/casual reply ─► END
                    ├─ needs clarification (turn 1 only) ─► ask ─► END
                    └─ data question ─► sql_agent loop:
                          discover tables → write SQL → execute
                            guard:      AST allowlist, fail-closed, before EVERY query
                            reflection: small model reviews complex SQL before it runs
                          ─► validate: does the answer match the SQL and rows?
                                       (never blocks; adds a caveat chip in the UI)
Per turn: WS events stream to the UI · LangGraph checkpoint persisted ·
          an audit row is ALWAYS written · Langfuse trace (if configured)
```

Full HLD/LLD (component tables, WS protocol, endpoint list, model schemas, per-package breakdown) live in the two PR descriptions linked at the top — we keep them there so review and design stay in one place.

## 4. The decisions that shaped the build

**Safety is structural, not prompt-based.** The model is never trusted: `execute_sql` is the single query path, and the sqlglot AST guard clamps every query to one SELECT with a row limit — writes are impossible by construction, not by instruction. Discovery is filtered to match the guard (in scoped sessions the model can't even *see* off-scope tables), so the model never plans SQL that would be rejected.

**Three LLM checks, three postures.** Router (before), reflection (during, complex queries only), audit (after). All three **fail open** — a helper-model outage degrades quality but can't take down a turn. The one fail-loud path is report summaries, because there a wrong/empty output *is* the deliverable.

**The model never sees org identity.** Credentials, schemas, permissions, and scope travel in a server-side `RunContext` built fresh each turn by the one module allowed to touch the ORM (`context_builder.py`). PII (emails, credit cards, Indian phone numbers) is masked in both directions *and rewritten into checkpointed state*, so it never reaches a provider, the checkpoint DB, or traces.

**Brains are injected, not imported.** The turn graph takes `route_fn` / `validate_fn` / the agent as parameters. That's why every unit test runs against scripted fakes — 184 backend tests with zero API calls — and why the eval harness can swap checkpointers per item.

**Hard metrics gate, LLM judges inform.** The eval harness compares **executed result sets** (gold SQL vs agent SQL, order/alias-agnostic) rather than asking a judge "is this SQL right?". This was measured, not assumed: the SQL judge false-failed **21 of 21** of its disagreements with execution. Latest runs: golden-v1 12/12, golden-work-orders 13/14 (`.../ddpui/core/ai/evals/README.md` documents the 8/14 → 13/14 progression — most "failures" were ambiguous questions or wrong gold answers, a lesson in itself).

**One event protocol, one component tree.** The frontend's dashboard drawer and full chat page are the same `ChatPane` + `useChatWithData` hook with a scope prop. Live turns stream over WS; history replays over REST into the same message shape. The agent's markdown renders through a hand-rolled subset parser (bold, lists, one heading level, callouts) — anything outside the subset renders as literal text, so the model can never inject links or HTML.

**Frozen pins with reasons.** `langfuse==2.60.10` (v2) because dbt pins `protobuf<5`, ruling out the OTel-based v3. `psycopg3` pool for the checkpointer coexists with Django's psycopg2. The riskiest dependency change is `websockets 10.4 → >=14` — the existing WS consumers ride on it.

## 5. Things we got wrong and fixed (worth remembering)

- **Async views + our permission decorator = silent 500s.** Django Ninja only awaits a view if it *is* a coroutine function; our sync `has_permission` wrapper hid that. Fixed with split sync/async wrappers in `ddpui/auth.py` — this touched **every endpoint in the codebase** and is easy to re-break; there are dedicated tests.
- **Middleware nodes count against the recursion limit.** Each middleware hook is its own graph node, so chat died at 3 tool calls until `RECURSION_LIMIT` was raised to 120 — guarded now by a realistic-discovery-turn test, not a comment.
- **Session switching mid-stream clobbered live turns** on the frontend — late-arriving REST history overwrote a streaming answer. Fixed with a "live turn started" ref; there's a regression test.
- **Eval "failures" were mostly our fault, not the agent's** — ambiguous golden questions and wrong gold SQL. Fix the dataset before blaming the model.

## 6. Deliberate scaffolding (shipped but unwired — do not mistake for features)

- `ChatWithDataTableCard` model + `rank-bm25` dependency + the no-op `retrieve_context_node`: the seam for v3 semantic-layer retrieval.
- `ChatWithDataOrgConfig` (per-org row limits / timeouts): model exists, nothing reads it yet — limits are hardcoded (100 rows, 30s).
- `get_allowed_schemas` remains the plug point for per-user dataset grants (deferred from v1 planning).

## 7. Current status & what's left

- Both PRs are open with full HLD/LLD in their descriptions (links at top).
- **Merge blocker (backend):** the 2026-08-07 merge from main re-forked the Django migration graph — a `makemigrations --merge` migration (0173) must land before merge.
- Pre-merge checklist (tracked in the backend PR): `.env.template` needs the ~10 new env vars; `docs/docs/features/chat-with-data-dev.md` lags the restructure; per-org **read-only warehouse role** is the top fast-follow (enforcement is AST-only today); BigQuery has no per-query timeout.
- Deploy steps per environment: `manage.py chat_with_data_setup` (checkpointer tables), seed permissions, enable the `CHAT_WITH_DATA` flag + `llm_optin` per org, set a provider API key.

## 8. Where to look

| Question | Go to |
|---|---|
| Why does this feature exist, for whom? | [`v1/spec.md`](./v1/spec.md) |
| What was the plan and blast radius? | [`v1/plan.md`](./v1/plan.md), [`v1/research.md`](./v1/research.md) |
| How does the code actually work today? | `../DDP_backend/ddpui/core/ai/CLAUDE.md` |
| How do I run/extend evals? | `../DDP_backend/ddpui/core/ai/evals/README.md` |
| Full HLD/LLD | The two PR descriptions linked at the top |
| Try it locally | `manage.py chat_with_data_repl` (no frontend needed) |
