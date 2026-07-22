# Scoped Chat with Data — dashboard chat + report executive summary

## Context

Chat with Data today is one org-wide surface: a standalone page where the agent can query
any allowed schema. The user wants it to become a **reusable primitive** that can be
embedded in multiple places, starting with two surfaces:

1. **Dashboard chat** — Priya opens the "Field Performance" dashboard and clicks "Ask about
   this dashboard". The chat answers **only from the tables behind that dashboard's charts**
   (hard scope — decided). Example: the dashboard's charts read `prod.surveys` and
   `prod.field_visits`; a question about donations gets "that's outside this dashboard —
   open the full Chat with Data page."
2. **Report executive summary** — a "Generate summary" button on a report. The AI drafts an
   executive summary from the report's frozen chart data; the user edits, then saves
   (button + editable draft — decided). `ReportSnapshot.summary` already exists as a
   user-typed field (`ddpui/models/report.py:48`); we're filling it with a draft, not adding
   a new concept.

Build order (decided): dashboard chat first — its scope plumbing is the foundation.

### Why this is cheap: what already exists

| Need | Already there |
|---|---|
| Dashboard → tables | `Chart.schema_name/table_name` (`models/visualization.py:52-53`); walk pattern in `ReportService._freeze_chart_configs` (`core/reports/report_service.py:85-121`) and `discover_datetime_columns` (`:800-805`) |
| SQL enforcement | `guards/sql_guard.py` — sqlglot AST guard, fail-closed, schema-level today |
| Per-turn prompt injection | `org_system_prompt` dynamic-prompt middleware rebuilds the system prompt from `RunContext` every model call (`agent/middleware.py:46`) |
| Report chart data | `ReportService.get_report_chart_data` / `get_report_kpi_data` (`report_service.py:320/380`) fetch from frozen configs |
| One-shot LLM call pattern | `core/chat_with_data/calls/titles.py` |
| Reusable chat UI | `ChatPane` + `useChatWithData(sessionId)` — props are just messages/isStreaming/onSend |

### Key design decisions

- **Scope lives on the session** (`scope_type` + `scope_id` columns), set at create time.
  One WS connection = one session, so nothing changes on the wire.
- **Scope is re-resolved every turn**, not frozen at session create. `build_run_context`
  already runs per turn in the consumer (`chat_with_data_consumer.py:118`), so a chart
  added to the dashboard mid-conversation is picked up on the next question for free.
- **Inject scope via the dynamic-prompt middleware, NOT `retrieve_context_node`.** The
  graph's `retrieve_context_node` (`graph.py:136-140`) stays reserved for M5's
  question-derived BM25 retrieval. Scope is session-static config; putting it in the
  prompt (rebuilt per call, never checkpointed) avoids bloating the checkpointed history.
- **Hard scope = guard-enforced table allowlist** (fail-closed), plus discovery-tool
  filtering so `list_tables` doesn't advertise tables the guard would reject (each wasted
  attempt burns one of the 3 SQL retries).
- **`report` scope_type is reserved in the enum now, implemented later** — the summary
  feature is a one-shot call, not a chat.

## Architecture review — improvements this plan bakes in (and what it doesn't)

- **Fixed by this work:** schema-only scoping (guard gains table-level allowlist, reusable
  beyond dashboards); org-only context (RunContext gains scope); chat locked to one page.
- **Deliberately untouched:** `retrieve_context_node` no-op (M5 BM25 + table cards),
  M0 pre-ship audit fixes (separate open work in `features/chat-with-data/v2/tasks.md`),
  verified-query library, PII middleware slice. These stay on their own tracks.
- **Deferred extensions this design keeps cheap:** report-scoped chat (frozen configs →
  same `ResolvedScope`), "suggest reports" agent tool, scope escape hatch ("look beyond
  this dashboard?" — needs HITL interrupt plumbing), pipeline/table-scoped chat.

## Data flow

```
POST /chat/sessions/ {scope_type:"dashboard", scope_id:12}
        │  validate: org-owned native dashboard, can_view_dashboards, has charts
        ▼
ChatWithDataSession(scope_type, scope_id)
        │  WS connect /wss/chat-with-data/<session_id>/
        ▼  (every turn)
build_run_context(orguser, session) ── resolve_scope(org, "dashboard", 12)
        │                                 └─ tabs → chartId/kpiId → (schema, table)
        ▼                                    + DashboardFilter tables
RunContext{allowed_tables, scope_context, narrowed allowed_schemas}
        ├─ dynamic prompt: "query ONLY these tables … suggest full chat otherwise"
        ├─ list_tables filtered to allowed_tables
        └─ sql_guard.validate(..., allowed_tables=…)  ← fail-closed
```

## Milestones

### S1 — Table-level SQL guard (pure, mergeable alone)

- `guards/sql_guard.py`: `validate(..., allowed_tables: list[str] | None = None)`. New
  `_check_tables`: every physical `schema.table` ref must be in the allowlist,
  case-insensitive. `None` = today's behavior; `[]` = block everything (fail-closed).
  CTE aliases already skipped by `_referenced_tables`; unqualified tables already rejected
  by `_check_schemas`. Error text is written for the model to relay: names the blocked
  table, lists available ones, says to suggest the full chat page.
- `tools/sql_tools.py:30`: pass `allowed_tables=ctx.allowed_tables`.
- `agent/state.py` RunContext: `allowed_tables: list[str] | None = None`,
  `scope_context: str = ""`, `scope_type: str = "org"`.
- Tests (extend `tests/core/chat_with_data/test_sql_guard.py`, one at a time): pass/fail in
  FROM, JOIN, subquery, UNION; CTE alias ignored; `None` unchanged; `[]` blocks;
  case-insensitivity.

### S2 — Session scope: model, REST, resolution, prompt (backend-complete)

- `models/chat_with_data.py` `ChatWithDataSession`: `scope_type` (CharField, default
  `"org"`), `scope_id` (IntegerField, null). Migration; existing rows = org scope.
- `schemas/chat_with_data_schemas.py`: `SessionCreate{scope_type="org", scope_id=None}`;
  `SessionOut` gains both fields (additive).
- `api/chat_with_data_api.py` + `service.create_session(orguser, scope_type, scope_id)`:
  optional body (empty POST still works). Dashboard scope validation: scope_id required,
  org-owned native dashboard exists, caller has `can_view_dashboards`, ≥1 chart/KPI.
  `list_sessions` gains optional `scope_type` filter (main page passes `org` so drawer
  sessions don't clutter the sidebar).
- **New `core/chat_with_data/scope.py`**: `resolve_scope(org, scope_type, scope_id) →
  ResolvedScope{allowed_tables, scope_context, scope_type}`. Walk `dashboard.tabs[].components`:
  `chart` → `config.chartId` → Chart's table; **`kpi` → `config.kpiId` → `KPI.metric.
  schema_name/table_name`** (KPI has no table fields itself — mirror `_freeze_chart_configs`).
  Include `DashboardFilter` tables. Empty/missing dashboard → raise `ScopeUnavailable`
  (friendly message; never emit `allowed_tables=[]` implicitly). `scope_context` = markdown
  block: dashboard title/description, per-chart "title — type on schema.table", filters.
- `agent/context.py`: `build_run_context(orguser, session=None)` (default keeps the only
  other caller, `management/commands/chat_with_data_repl.py:41`, working). Scoped session →
  set allowed_tables/scope_context and derive `allowed_schemas` from the scoped tables.
- `tools/schema_tools.py`: filter `list_tables` output to `ctx.allowed_tables` when set.
- `agent/prompts.py`: when `allowed_tables` set, append scoped section — query ONLY these
  tables, here's the dashboard context, interpret questions against it, and for anything
  outside say so plainly and point to the full Chat with Data page.
- `websockets/chat_with_data_consumer.py:118`: pass `session=`; catch `ScopeUnavailable`
  → error event (no protocol change).
- Tests: new `test_scope.py` (chart+KPI+filter collection, dedup, empty raises, missing
  raises); extend context/prompt tests (scoped vs org unchanged); API tests (cross-org 400,
  missing scope_id 400, legacy empty POST OK).

### S3 — Frontend: dashboard chat drawer

- `hooks/api/useChatSessions.ts`: `createSession(scope?)`; session type gains scope fields;
  main chat page lists `?scope_type=org`.
- **New `components/chat-with-data/ChatDrawer.tsx`**: shadcn `Sheet`, props
  `{dashboardId, dashboardTitle, open, onOpenChange}`. First open creates a dashboard-scoped
  session, keeps `sessionId` for the page visit, renders existing `ChatPane` via
  `useChatWithData`. Header: "Ask about *<title>*" + hint "Answers come only from this
  dashboard's data".
- Mount in `components/dashboard/dashboard-native-view.tsx` header: "Ask about this
  dashboard" button. Gate: chat `/status` enabled + permission + native dashboard + ≥1
  chart/KPI (disabled with tooltip otherwise; hidden for Superset).
- Tests: drawer posts scope payload and renders ChatPane; button gating.

### S4 — Report executive summary

- **New `core/reports/summary_generator.py`** (titles.py pattern, but errors raise — the
  user clicked a button): `generate_report_summary(snapshot) → str`. Fetch each frozen
  component via `get_report_chart_data`/`get_report_kpi_data`; per-chart failure → "(data
  unavailable)" note, fail only if all fail; cap per-chart payload (~15 rows). ONE LLM call:
  snapshot title + period + chart blocks; markdown subset matching the renderer (bold,
  bullets, `###`); "executive summary for NGO leadership; never invent numbers".
- `api/report_api.py`: `POST /{snapshot_id}/generate-summary/`,
  `@has_permission(["can_create_dashboards"])`, org-scoped snapshot, **`llm_optin` consent
  gate** (reports don't otherwise touch LLMs). Returns `{"summary": text}` — draft only;
  saving stays on existing `PUT update_snapshot`.
- `app/reports/[snapshotId]/page.tsx`: "Generate summary" button beside the summary editor
  → sets `summaryDraft` + `summaryTouched=true` (existing state, prevents revalidation
  clobber); confirm before overwriting a non-empty draft; existing save path unchanged.
- Tests: `test_summary_generator.py` (mock data fetch + model; prompt assembly; partial
  failure tolerance); API consent-gate + happy path; frontend button test.

## Risks

- **KPI components**: tables come via `KPI.metric`, not the KPI row — the walk must mirror
  `_freeze_chart_configs` exactly.
- **Stale history**: old answers may mention tables later removed from the dashboard;
  acceptable — the guard blocks new queries per turn.
- **Identifier case**: compare table refs case-insensitively (Postgres folds unquoted
  identifiers); note BigQuery caveat in the guard docstring.
- **Superset dashboards** have no warehouse tables — excluded at create-validation and UI.
- **Summary cost**: cap per-chart rows/chars; sequential fetches first.

## Execution mechanics

Per `executing-feature-plans`: worktrees `feature/scoped-chat` off both repos, red-green
one test at a time, `tasks.md` checkpoint in `features/chat-with-data/` (new version folder
`v2.1/` via plan-enhancement convention), backend PR first. Note: `feature/chat-with-data`
and `feature/resource-sharing` both have 0168-0170 migrations — number the new migration
after whatever the branch's head is and flag the merge-order collision in the PR.

## Verification

- Backend: `pytest ddpui/tests/core/chat_with_data/ ddpui/tests/core/reports/` plus full
  suite (`--ignore=ddpui/tests/integration_tests`).
- Guard: scoped session in `chat_with_data_repl` — ask an off-dashboard question, confirm
  polite refusal + full-chat suggestion; confirm on-dashboard questions answer normally.
- Browser (Playwright MCP, port 3001, creds from `.claude/test-credentials.local.json`):
  open a native dashboard → Ask about this dashboard → ask a question answered from its
  tables → ask an off-scope question → see the refusal. Report page → Generate summary →
  edit draft → save → summary persists.
