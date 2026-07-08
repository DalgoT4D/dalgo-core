# Chat with Data v1 — Task Checkpoint

**Plan:** [plan.md](./plan.md) · **Branch:** `feature/chat-with-data`, checked out in the main repos `../DDP_backend` and `../webapp_v2` (worktrees removed 2026-07-07; not pushed yet)

Status legend: `[ ]` todo · `[x]` done · `[~]` in progress

## Milestone 1: SQL guard + limits (pure library code) ✅ (commit: "Chat with Data M1")
- [x] Add sqlglot dep to DDP_backend (sqlglot==30.12.0 via uv)
- [x] `guards/sql_guard.py` — validate(): parse, single-statement, SELECT-only by node type (both dialects; UNION/INTERSECT/EXCEPT allowed)
- [x] `guards/sql_guard.py` — schema allowlist enforcement (CTE aliases exempt)
- [x] LIMIT inject/clamp via AST — *deviation: lives in sql_guard.py, no separate limits.py; smaller user LIMIT preserved*
- [x] Bypass-catalog test suite green — 21 tests: comments, COPY/SET/SHOW/EXPLAIN/VACUUM, CTE-named-delete, DML-in-CTE (both dialects), SELECT INTO, FOR UPDATE, multi-statement, unqualified tables, homoglyph fail-closed

## Milestone 2: Agent core + dev harness (LangSmith) ✅ (commits 0c611695, ade4b918, 788abebb)
- [x] Deps pinned — *deviations: bumped repo pins typing-extensions>=4.14, websockets>=14,<16 (nothing imports websockets directly)*
- [x] `state.py` RunContext + `context.py` (dbt schema → raw fallback; system schemas excluded) — *deviation: no custom ChatState; default AgentState suffices, retry counting reads messages*
- [x] `prompts.py` — dialect-aware system prompt
- [x] `tools/` — registry + 5 tools; execute_sql returns content_and_artifact (UI table on ToolMessage.artifact)
- [x] `middleware.py` — dynamic_prompt (per-org), trim via llm_input_messages, sql_retry_limiter (jump_to end after 3 fails), ContextEditingMiddleware
- [x] `agent.py` — build_agent via langchain create_agent
- [x] Checkpointer singleton + `chat_with_data_setup` command
- [x] REPL (`manage.py chat_with_data_repl --org <slug>`) + dev doc `docs/docs/features/chat-with-data-dev.md` — **`.env.template` edit blocked by sandbox permissions; snippet in dev doc, add before PR**
- [x] Agent-loop tests: happy path, error-recovery, retry exhaustion (44 tests total)
- [x] Sentry LanggraphIntegration(include_prompts=False) wired in settings.py (pulled forward from M4)
- Note: earlier "sentry breaks jump_to" diagnosis was wrong — root cause was the scripted test model reusing message ids; integration verified compatible

## Milestone 3: Sessions, REST, gating, audit
- [ ] Models `ChatWithDataSession`, `ChatWithDataTurnAudit`, `ChatWithDataOrgConfig` + migration
- [ ] `CHAT_WITH_DATA` feature flag entry
- [ ] `can_use_chat_with_data` permission: seed json + RunPython migration
- [ ] `chat_with_data_api.py`: status, session CRUD, history (async, from checkpointer)
- [ ] Audit writes wired into agent runner
- [ ] API tests incl. owner-scoping

## Milestone 4: WebSocket streaming ✅ (commit: "Chat with Data M4")
- [x] Async cookie-JWT auth — *deviation: implemented inline in ChatWithDataConsumer, no separate AsyncBaseConsumer base class (only one async consumer exists; extract when a second appears)*
- [x] `chat_with_data_consumer.py` + ws_urlpatterns entry (`wss/chat-with-data/<session_id>/`) + FORBIDDEN close code 4004
- [x] astream→WS event mapping in transport-independent `runner.py` (token/tool_start/tool_end/message_complete/error) + audit row per turn
- [x] Turn lock (Redis SET NX EX 180) + rate limit (10 msg/min/user) + title generation (`titles.py`, Haiku, non-fatal)
- [x] Sentry LanggraphIntegration — done in M2
- [x] Consumer test suite (8 tests: auth rejects, flag/consent reject, owner-scoping, full turn event sequence + title, unsupported action, turn-lock rejection, rate limit) + runner tests (2)
- [x] Fix: removed `MapLayer` from models `__init__` registry imports — it has no migration (table loaded out-of-band from geojson dumps), registering it broke test-DB creation (Channels communicator)

## Milestone 5: Frontend chat page ✅ (commit: "Chat with Data M5", 4f63ea1)
- [x] `FeatureFlagKeys.CHAT_WITH_DATA` + nav item (gated on flag AND `can_use_chat_with_data`) + status-driven empty states (feature off / consent / no warehouse)
- [x] `hooks/api/useChatSessions.ts` (SWR CRUD + status) + `hooks/useChatWithData.ts` (pure `applyChatEvent` reducer + `historyToChatMessages` + WS lifecycle)
- [x] Components — *deviation: PascalCase filenames per repo convention:* SessionSidebar, ChatPane, MessageBubble, ToolProgress (+view SQL), ResultTable
- [x] Analytics: session created/renamed/deleted, message_sent (value action), sql_viewed, feature:viewed via PATHNAME_TO_FEATURE
- [x] Hook reducer tests + component render tests + page gating tests (21 tests)
- [x] FORBIDDEN (4004) close code added to lib/websocket.ts, no-reconnect
- [x] *Deviation: no markdown renderer exists in webapp_v2* — assistant text renders whitespace-pre-wrap plain text; backend prompt now instructs plain text (prompts.py, uncommitted in backend worktree)
- [ ] Playwright browser smoke test — deferred to M6 live validation (needs running stack + flagged org)

## Post-M5 additions (2026-07-07)
- [x] Fix: content-block extraction (`content.py` `extract_text`) — claude-sonnet-5 runs adaptive thinking by default, so AIMessage.content is a block list (signed thinking block + text); str() was leaking raw block reprs into the chat. Applied in runner (tokens + final), history, titles. (backend `e3efffac`)
- [x] `create_chart` tool — first registry extension (spec §12): creates a saved Dalgo Chart (bar/line/pie/number) via ChartService; validates chart type, schema allowlist, aggregation, and `can_create_charts` (resolved into RunContext at context-build time). Chart links ride `message_complete.charts[]` and replay in history; frontend renders link chips to /charts/{id}. (backend `3557927c`, frontend `e977b0d`)

## Milestone 6: Hardening + live validation
- [ ] Live E2E: Postgres org + BigQuery org, canned questions, error-recovery case — *needs running stack + ANTHROPIC_API_KEY; REPL: `manage.py chat_with_data_repl --org <slug>`*
- [ ] Playwright browser smoke test (moved from M5 — needs running stack)
- [ ] Concurrency sanity (3 sessions streaming)
- [ ] Audit rows + per-turn cost measured; prompt tuning if needed
- [x] domain-map.md entity entry (Analytics Layer → "Chat with Data")
- [ ] User-facing docs page (documentation skill, dalgo_docs)
- [ ] `.env.template`: add ANTHROPIC_API_KEY / CHAT_WITH_DATA_MODEL / LANGSMITH_* — **still blocked by sandbox perms; snippet in DDP_backend dev doc**
- [ ] Backend PR + frontend PR (backend first, cross-linked)
