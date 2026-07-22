# Scoped Chat with Data — v2.1 tasks

Plan: `features/chat-with-data/v2.1/plan.md`
Worktrees: `.dalgo-worktrees/scoped-chat/{DDP_backend,webapp_v2}` on `feature/scoped-chat`
(branched off `feature/chat-with-data`). Migration number: **0171** (0170 is taken by the
parallel evals session's feedback migration).

## S1 — Table-level SQL guard

- [x] RunContext: `allowed_tables` / `scope_context` / `scope_type` fields (state.py)
- [x] Guard: `validate(..., allowed_tables=None)` + `_check_tables` — allowed table passes
- [x] Guard: out-of-scope table blocked in FROM (error names table + lists available)
- [x] Guard: blocked in JOIN / subquery / UNION branch
- [x] Guard: CTE alias not table-checked
- [x] Guard: `None` = old behavior; `[]` blocks everything
- [x] Guard: case-insensitive comparison
- [x] sql_tools passes `allowed_tables=ctx.allowed_tables`
- [x] Commit S1

## S2 — Session scope (backend-complete)

- [x] Model: scope_type/scope_id on ChatWithDataSession + migration 0171
- [x] scope.py: resolve_scope — chart tables collected
- [x] scope.py: KPI via metric tables
- [x] scope.py: DashboardFilter tables + dedup
- [x] scope.py: empty dashboard raises ScopeUnavailable; missing dashboard raises
- [x] scope.py: scope_context markdown block
- [x] service.create_session(scope_type, scope_id) + validation (org-owned native dashboard, can_view_dashboards, has components)
- [x] API: SessionCreate payload (optional body, legacy empty POST OK) + SessionOut scope fields
- [x] API: list_sessions scope_type filter
- [x] context.py: build_run_context(orguser, session=None) — scoped session sets allowed_tables/scope_context, narrows allowed_schemas
- [x] schema_tools: list_tables filtered to allowed_tables
- [x] prompts.py: scoped system-prompt section
- [x] consumer: pass session=, catch ScopeUnavailable → error event
- [x] Commit S2

## S3 — Frontend: dashboard chat drawer

- [x] useChatSessions: createSession(scope?) + session type fields + org filter on main page
- [x] ChatDrawer.tsx: creates scoped session, renders ChatPane
- [x] Mount button in dashboard-native-view header with gating
- [x] Tests: scope payload posted; button gating
- [x] Commit S3

## S4 — Report executive summary

- [x] summary_generator.py: prompt assembly from frozen components (mocked fetch + model)
- [x] summary_generator.py: partial-failure tolerance; all-fail raises
- [x] API: POST /{snapshot_id}/generate-summary/ + llm_optin consent gate
- [x] Frontend: Generate summary button → summaryDraft (+ overwrite confirm)
- [x] Commit S4

## Validation & ship

- [x] Full backend suite (`--ignore=ddpui/tests/integration_tests`)
- [x] Frontend suite + lint
- [x] Browser smoke: dashboard drawer on/off-scope Q&A; report summary generate→edit→save
- [x] ~~Separate PRs~~ — user chose to fast-forward merge into `feature/chat-with-data` in both repos (2026-07-11); worktrees and `feature/scoped-chat` branches removed. Migration-number collision with resource-sharing still applies when THAT branch merges.


## Post-merge notes (2026-07-11)

- Browser smoke (worktree servers on 8003/3002): dashboard drawer answered on-scope
  (145 responses from prod_intermediate.int_classroom_surveys_indonesia), refused
  off-scope loans question with full-chat pointer, no off-scope SQL ran. Report 11:
  Generate summary → clean markdown draft with real ₹ figures → saved → persisted.
- Smoke test caught + fixed: thinking-block lists leaking into the summary draft
  (58f213b5 — extract_text).
- Full-suite caveat: chat/report/consumer/scope suites all green in isolation; two
  full-suite runs were poisoned by a concurrent pytest from the resource-sharing
  session (shared test DB). Run one clean full suite before pushing the branch.
- 0171 migration applied to the shared dev DB; scope_type has a DB-level default
  so other branches' inserts stay safe.
