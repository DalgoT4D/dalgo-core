# Chat with Data v2 — Task Checkpoint

**Plan:** [plan.md](./plan.md) · **Branch:** `feature/chat-with-data` checked out in the
main repos `../DDP_backend` and `../webapp_v2` (*deviation from the worktree rule: the user
converted to main-checkout workflow on 2026-07-07 to test locally; branch, not main*).

Status legend: `[ ]` todo · `[x]` done · `[~]` in progress

## Milestone 1: Query-understanding router (Phase 1) ✅ (backend 4727ca0a)
- [x] `router.py` — `route_question()` Haiku call → {intent, complexity, entities, clarification}; fail-open to data_question/simple; `casual_reply()` for small talk
- [x] runner integration: route first; small_talk/needs_clarification short-circuit (reply + turn recorded in checkpointer via `aupdate_state`); complexity+question onto RunContext — *deviation: intent not in Langfuse trace metadata yet (router runs before trace creation); it IS on the audit row*
- [x] `ChatWithDataTurnAudit.intent` + `.validation` JSONFields (one migration, 0168)
- [x] Tests: router parsing/fail-open, short-circuit path (incl. thread memory), audit write; router stubbed autouse so tests never construct a real model

## Milestone 2: Result validator (Phase 1) ✅ (backend 5f8ff906)
- [x] `validator.py` — post-execution Haiku checklist (grain / missing filter / false zero / number match) → {verdict, assumptions, caveat}; non-fatal, skips when no SQL ran
- [x] runner: `validation` WS event after message_complete; audit `.validation`; Langfuse score `result_validation` via new handler `.score()`
- [x] Tests: validator parsing/skip/fail-open, runner event emission + audit field

## Milestone 3: Frontend validation strip (Phase 1) ✅ (frontend c873070e)
- [x] types + reducer: `validation` event attaches to last assistant message
- [x] MessageBubble: amber "Worth checking: …" strip on warn; silent on ok
- [x] Tests: reducer + component (warn and ok paths)

## Milestone 4: Reflection, complex lane only (Phase 1) ✅ (backend a508435d)
- [x] RunContext gains `question` + `complexity`; runner sets both from the route
- [x] execute_sql: complexity == "complex" → `reflection.check_sql()` on the GUARDED sql before execution; flawed → "SQL rejected: …" feedback (counts toward the 3-attempt limiter); fail-open
- [x] Tests: check_sql parsing/fail-open, gate on/off, must-not-execute path

**Phase 1 validation:** backend full suite 2138 passed · frontend full suite 1458 passed (2026-07-08)

## Post-Phase-1 additions (2026-07-08)
- [x] Fix: context-blind router diverted follow-ups ('chart this', 'above one') to needs_clarification — router now sees a thread tail; clarify can only divert the first turn (backend 405ca315)
- [x] Fix: blank chart pages — create_chart wrote x_axis_column but the render path GROUPs BY dimension_column; existing rows repaired (backend d5ffbfb8)
- [x] Dashboard tools: list_dashboards / create_dashboard / add_charts_to_dashboard with suggest-first prompt flow, can_create_dashboards in RunContext, dashboard chips in chat (backend f4d77040, frontend)

## Milestone 5: Table cards + enrichment agent + BM25 injection (Phase 2)
- [ ] `ChatWithDataTableCard` model + fingerprint + migration
- [ ] Enrichment agent (offline, reuses tool registry) + Celery task (`TaskProgress` pattern) + trigger endpoint beside `org_preferences_api`
- [ ] dbt-webhook auto-refresh hook (`FLOW_RUN_COMPLETED` branch)
- [ ] BM25 ranker (`rank_bm25` dep) + top-card injection via dynamic_prompt middleware + staleness fallback
- [ ] Tests throughout

## Milestone 6: Settings UI for metadata rebuild (Phase 2)
- [ ] `app/settings/ai-data/page.tsx` + nav entry (pattern: elementary-setup polling)
- [ ] Rebuild button → task_id → poll `GET /api/tasks/{id}`
- [ ] Tests
