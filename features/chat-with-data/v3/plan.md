# Chat with Data v3 — Context, Correction, Containment

## Context

This version started as a bigger idea: rebuild Chat with Data as a fixed multi-stage
pipeline (the Uber/AWS shape from `ai-learnings/docs/chat-with-data-agent-workflow.md`
§A), with a PostHog-style orchestrator, specialist SQL/checker agents, and human-in-the-
loop (HITL — the agent pauses and asks the user before proceeding) table approval.

We rejected most of that after reading it against our own research and our own eval
results. What survived is the half every source agrees on: **give the agent better
context up front, correct failures with structure instead of raw retries, and contain
the blast radius of any bug with a read-only database role.** The agent loop stays.

### The architecture ruling (recorded so it doesn't get re-litigated)

**The rule:** the single tool-calling agent loop stays; we do not replace it with a
fixed plan→generate→validate→correct pipeline.
**Evidence:** three sources, all ours.

1. `ai-learnings/research/langchain-langgraph-chat-with-data.md` §1 (3-0 verified):
   production systems converge on "deterministic stages **wrapped around a bounded agent
   loop**" — LinkedIn SQL Bot, the official LangGraph SQL tutorial. That is our current
   topology. §10 opens with "The topology itself — no need to re-litigate."
2. `ai-learnings/research/posthog-agent-architecture.md` §9: PostHog publicly killed
   graph orchestration for their interactive agent (learning #2, "agents beat
   workflows") and warns that plan/decompose scaffolding rots as models improve
   (learning #1).
3. Our eval runs (July 2026): after item calibration, 12/12 (golden-v1) and 13/14
   (golden-work-orders) hard-metric pass. The residual failures are **context**
   failures — date bucketing over TEXT columns, label formats like `'Q3 (Oct-Dec
   2025)'` — not "the loop chose wrong SQL". A pipeline rebuild treats a disease our
   measurements don't show.

**Revisit trigger:** if, after M1+M2 ship, eval runs still show wrong-table selection
(low `eval_tables` overlap) or a persistent wrong-SQL failure class, build the pipeline
as an **A/B experiment the eval harness judges** — not as a commitment. (Workflow doc
§9.2: "measure, don't guess"; PostHog doc §11.6: "let evals judge.")

**Also deferred — HITL table approval.** Uber added it because auto-picked tables were
frequently wrong across thousands of tables; NGO warehouses have dozens, plus dashboard
scoping (v2.1). The new `eval_tables` metric (M4) tells us whether we have Uber's
disease before we build Uber's cure. When HITL does come, follow PostHog's pattern:
`is_dangerous_operation()` on the **tool base class** with a generic interrupt — policy
travels with the capability, every future mutating tool inherits approval for free
(posthog doc §11.3) — not a graph node.

### Why this is cheap: what already exists

| Need | Already there |
|---|---|
| Table-card storage | `ChatWithDataTableCard` model with `source_fingerprint` drift detection (`models/chat_with_data.py:80`) — designed in v2, never populated. Card body is JSON: **no migration needed** |
| A place to inject retrieved context | `retrieve_context_node` in `core/ai/chat/turn_graph.py` — an empty placeholder built for exactly this (M5 of the v2 plan) |
| Table refs from SQL | the guard already extracts referenced tables via sqlglot (`guards/sql_guard.py`) — reuse for the `eval_tables` overlap score |
| Column/table introspection | `Warehouse.get_table_columns` + `execute` on Postgres and BigQuery clients (`utils/warehouse/client/`) |
| Eval harness with `expected_tables` | golden items already carry the field (`core/ai/evals/README.md`) — it was "metadata for now"; M4 makes it a score |
| Per-turn SQL audit rows | `ChatWithDataTurnAudit.sql_queries` — the online safety scan reads these, zero new infra |

### Key design decisions

- **Deterministic cards first, LLM enrichment optional.** The card's high-value content
  (columns, types, row count, date ranges, top-K distinct values) is computable by
  code. An optional `--describe` pass can add LLM prose later; it is not on the
  critical path. (Deterministic-first — workflow doc principle #2.)
- **Value profiles are the point, not a nice-to-have.** Example: Priya asks "what was
  achieved in Q3?" — today the agent guesses `WHERE quarter = 'Q3'` and gets zero rows,
  because the column actually holds `'Q3 (Oct-Dec 2025)'`. A card that lists the real
  values kills our two known flaky eval classes (date bucketing, label formats).
- **Inject at `retrieve_context_node`, keep discovery tools.** Cards are question-time
  context, not session-static config (that's scope's seam, v2.1). The agent keeps
  `list_tables`/`get_table_details`/`profile_column` for anything cards miss — cards
  make those calls rarer, they don't forbid them.
- **No embeddings, no new dependency for ranking.** Dozens of tables per org: a
  ~30-line tokenized keyword-overlap scorer picks which cards go in full vs as
  one-liners. BM25 (a standard keyword-relevance formula) via `rank_bm25` only if the
  simple scorer measurably under-ranks — swap is one function.
- **Structured correction, not naive retry.** Research-verified (workflow doc §Stage 6):
  pasting the raw error back makes the model repeat the same fix. On failure, code
  classifies the error and attaches the *missing context* (the value profile for a bad
  filter, next-ranked cards for an unknown table) to the tool error the model sees.
  `MAX_SQL_ATTEMPTS = 3` stays.
- **Read-only role is layer 1, the AST guard is layer 2.** A read-only warehouse role
  is "the only guarantee that survives a guard bug" (langchain research §10 gap #1).
  Fail-soft: orgs without the role provisioned keep working on existing credentials,
  with a warning log — provisioning rolls out org by org.
- **Composability without a pipeline.** Every new piece is a plain function with typed
  inputs/outputs and no ORM imports past the boundary: `build_table_card(warehouse,
  schema, table)`, `rank_cards(question, cards)`, `classify_sql_error(error, card)`.
  Report summaries, a future "suggest charts" feature, or dalgo-mcp can call any of
  them without touching the chat graph.

## Data flow (one question, after v3)

```
"What was achieved in Q3?"          BUILD TIME (cron / manual)
        │                           sync_table_cards --org test-ngo
        ▼                             walks allowed schemas → per table:
   route_node (unchanged)             columns, row count, date ranges,
        │                             top-K values for low-cardinality cols
        ▼                             → ChatWithDataTableCard (fingerprinted)
   retrieve_context_node  ◄────────────────────┘
     rank_cards(question, org cards, scope)
     → top-k full cards + one-liners for the rest → state
        │
        ▼
   sql_agent loop (unchanged shape, better informed)
     writes: WHERE quarter = 'Q3 (Oct-Dec 2025)'   ← value profile in context
     execute_sql:
       guard (AST, allowlist)            ← unchanged
       EXPLAIN dry-run                   ← new: syntax/reference errors caught
       run on READ-ONLY role             ← new: survives any guard bug
     on failure: classify_sql_error → error + missing context back to model (≤3)
        │
        ▼
   validate_node (unchanged) → answer + [View SQL]
```

## Milestones

### M1 — Semantic layer: build and store table cards (additive, no behavior change)

- New package `ddpui/core/ai/semantic/`: `cards.py` (`build_table_card`,
  `fingerprint_columns`), `profiler.py` (`profile_values`).
- Profiling rules (each bounds cost): text columns only, cardinality probed with
  `SELECT COUNT(DISTINCT col) … LIMIT`-guarded sampling; profile only columns with
  ≤50 distinct values, store top-20 with counts; date/timestamp columns get min/max;
  per-table statement timeout reused from `ChatWithDataOrgConfig.query_timeout_s`.
- Management command `sync_table_cards --org <slug> [--schemas …] [--force]`:
  idempotent; skips tables whose `source_fingerprint` is unchanged unless `--force`;
  prints a per-table summary line.
- Card JSON extends the documented shape: `{description, grain, time_column,
  dimensions, metrics, value_notes}` + `{columns, row_count, date_ranges,
  value_profiles}`. JSONField → no migration.
- Tests: card builder + profiler against `FakeWarehouse`; fingerprint stability;
  cardinality cap respected.

### M2 — Retrieval: cards reach the agent (the behavior change, eval-gated)

- `semantic/retrieve.py`: `rank_cards(question, cards) -> RankedCards` — tokenized
  keyword overlap, top-k (start k=4) rendered in full, the rest as one-line stubs
  ("`test_ngo.donations` — 12 columns, donations by donor and date"); total character
  cap so 50-table orgs can't blow the prompt budget.
- `chat/turn_graph.py::retrieve_context_node`: load the org's cards (scope-aware —
  dashboard sessions only see their scoped tables' cards), rank, put the rendered
  block in graph state; agent prompt template gains the block. Cards absent → node is
  a no-op (today's behavior, orgs roll out as they sync).
- Baseline discipline: run both golden datasets **before** (run name `pre-m2`) and
  **after** (`post-m2`) on the same metric version.
- Tests: ranking picks the obvious table; scope filtering; empty-cards no-op; prompt
  assembly with cards present.

### M3 — Hardening: EXPLAIN, structured correction, read-only role

- **EXPLAIN dry-run** in `tools/sql_tools.py` after the guard passes: Postgres
  `EXPLAIN <sql>`, BigQuery dry-run flag. Failure returns a structured tool error
  without touching data. (langchain research §10 gap #2.)
- **`tools/sql_errors.py`**: `classify_sql_error(error, cards) -> CorrectionHint`.
  Taxonomy v1: `unknown_column | unknown_table | bad_filter_value | type_mismatch |
  syntax | timeout | empty_result`. Enrichment per class — `bad_filter_value` attaches
  the column's value profile ("column `quarter` contains: 'Q3 (Oct-Dec 2025)', …");
  `unknown_table` attaches the next-ranked cards (LinkedIn's repair-with-expanded-
  context pattern). Wired into `execute_sql`'s error path; retry cap unchanged.
- **Read-only warehouse role** (fail-soft slice): optional read-only credentials on
  `OrgWarehouse` (secrets manager, alongside existing creds); chat's warehouse client
  prefers them when present, else logs a warning and uses existing creds. Management
  command `provision_chat_readonly_role --org` for Postgres (`CREATE ROLE … GRANT
  SELECT`); BigQuery documented as a viewer-role manual step in v1.
- Tests: EXPLAIN failure short-circuits execution; each taxonomy class maps and
  enriches correctly; credential preference + fallback.

### M4 — Eval upgrades: measure what M1–M3 changed

- `eval_tables` (inform): parse the agent's SQL with the guard's table extractor,
  overlap vs the item's `expected_tables` → 0–1. The Uber table-overlap score; also
  the sensor for the deferred HITL/pipeline decisions.
- Trajectory capture: `ItemResult` gains `tools_called`; informational assertions
  (SQL ran before the answer; no identical SQL attempted twice — the "repeated wrong
  fix" smell the correction work should eliminate).
- Online safety scan: management command `chat_safety_scan` greps
  `ChatWithDataTurnAudit.sql_queries` for DML keywords (INSERT/UPDATE/DELETE/DROP —
  SQL that modifies data); exits non-zero on any hit. Cron-able; replicates the AWS
  online evaluator with zero new infra.
- Docs: new scores added to `core/ai/evals/README.md` score table.

### M5 — Decision gate (not a build milestone)

Run both golden sets + judges; compare `pre-m2` → `post-m3` in Langfuse. Record in
`tasks.md`:

| Signal | Decision |
|---|---|
| Date/label flakes gone, `eval_tables` ≥ ~0.9 | v3 done; pipeline and HITL stay rejected/deferred |
| `eval_tables` low (wrong tables persist) | build HITL table approval (tool-base pattern) |
| Wrong-SQL class persists with right tables | build the pipeline **as an A/B experiment** |

## Risks

- **Profiling cost on big tables** — `COUNT(DISTINCT)` over millions of rows. Bounded
  by: text-columns-only, sampling, cardinality cap, statement timeout. Sync is
  offline; worst case is a slow sync, never a slow chat turn.
- **Stale cards lie.** A dbt run renames a column; the card says otherwise until
  re-sync. Mitigations: fingerprint mismatch marks the card stale (excluded from
  injection); card block carries "synced <date>"; the discovery tools remain the
  agent's live fallback. Future: trigger sync from pipeline completion.
- **Context bloat** — top-k + one-liner stubs + character cap; M2's eval comparison
  catches regression (cards could make the agent faster AND worse — posthog doc §11.1).
- **EXPLAIN dialect gaps** — Postgres/BigQuery covered; other warehouses skip the
  dry-run (guard still applies), noted in the tool docstring.
- **Read-only provisioning varies per warehouse** — fail-soft design keeps every org
  working; the role rolls out org by org.
- **Eval comparison validity** — pin the metric version across `pre-m2`/`post-m3`
  runs; a `sql_compare.py` change mid-stream invalidates the comparison
  (evals README gotcha).

## Execution mechanics

Per `executing-feature-plans`: branch `feature/cwd-v3-semantic-layer` off the current
chat branch in `DDP_backend` (no `webapp_v2` work in v3 — nothing user-visible changes),
red-green one test at a time, checkpoint in `features/chat-with-data/v3/tasks.md`.
Mergeable chunks: M1+M2 (one PR), M3 (one PR), M4 (one PR). No migrations expected;
if one appears, check migration-number collisions with in-flight branches first
(v2.1 hit this at 0170/0171).

## Verification

- Unit: `uv run pytest ddpui/tests/core/ai -v` (new: `test_semantic_cards.py`,
  `test_retrieve.py`, `test_sql_errors.py`; extended: eval runner, sql_tools).
- Eval: `chat_with_data_eval` on both golden datasets, run names `pre-m2`,
  `post-m2`, `post-m3`; expect the Q3-vs-Q4 flaky item to stabilize — it is the
  designated canary for the value-profile thesis.
- REPL: `chat_with_data_repl --org test-ngo` — ask the Q3 question, confirm the SQL
  filters on the real label; ask about a renamed column post-sync, confirm the agent
  falls back to live discovery.
- Safety: run `chat_safety_scan` against dev audit rows; assert clean exit.
