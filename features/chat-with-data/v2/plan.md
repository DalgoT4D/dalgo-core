# Chat with Data v2 — Multi-Stage Pipeline Plan (Draft)

**Date:** 2026-07-07
**Builds on:** [v1 plan](../v1/plan.md) (shipped: single-agent loop, M1–M5 complete)
**Status:** Draft — architecture direction agreed in session, not yet scheduled

Acronyms: LLM (large language model) · BM25 (a classic keyword-ranking algorithm,
no ML involved) · AST (abstract syntax tree — parsed SQL structure).

---

## 1. The question this plan answers

The proposed pipeline was:

```
Query understanding agent  → intent + entity extraction
Schema retrieval agent     → knowledge graph + vector search
SQL generation agent       → writes SQL with business context
Reflection agent           → self-critiques SQL before execution
Execution + validation     → run + check result plausibility
Answer synthesis           → final answer
```

**The core design decision: only two of these six boxes should be agents.**
The rest are single LLM calls or plain code.

**The rule:** climb this ladder only when the cheaper rung fails —
prompt change → one extra LLM call → subagent-as-tool → supervisor graph.
**Example:** GoPie (Factly's open-source equivalent) promoted every box to a
graph node and now maintains ~25 custom nodes and ~20 prompt files. Our v1
ships the same user value with 1 agent and 5 tools.
**Why it matters:** every promoted box adds latency, cost, and a new way to
fail — and most boxes don't need agency (tools + looping), just one answer.

---

## 2. Stage-by-stage mapping

| Proposed stage | What it becomes for us | Model | Why not a full agent |
|---|---|---|---|
| 1. Query understanding | One structured LLM call: `{intent, entities, complexity}`. Routes small-talk/clarification away from the SQL path entirely | Haiku | Reads one question, emits JSON. No tools to loop over |
| 2. Schema retrieval | **No LLM at runtime.** BM25 ranking of the question against pre-built "table cards"; top 2–3 injected into the system prompt | — | Retrieval is deterministic once the knowledge exists (built offline, §3) |
| 3. SQL generation | **Agent #1 — already shipped.** The v1 `create_agent` loop with the tool registry | Sonnet 5 | This is where agency pays: unexpected errors, ambiguous values, retries |
| 4. Reflection | One checklist LLM call, **complex-lane only** | Haiku | The AST guard already covers safety on every query; semantic pre-checks on simple queries tax the 80% case |
| 5. Execution + validation | Execution = existing guard + warehouse (code). Validation = one post-execution call: grain / filters / false-zero / number-match checks | Haiku | Judging one result against one question is single-shot work |
| 6. Answer synthesis | The SQL agent's own final message (v2.1: structured answer card via `response_format`) | — | A separate synthesis agent loses the context the SQL agent holds |

**Example (Priya):** "How many farmers enrolled in Maharashtra last month?"
→ stage 1 says `{intent: data_question, complexity: simple, entities: farmers/Maharashtra/last-month}`
→ stage 2 injects the `prod.farmers` table card (grain: one row per farmer,
time column: `enrollment_date`, state stores full names)
→ the SQL agent writes correct SQL in 1–2 turns instead of 4–6 discovery turns
→ validator confirms the count matches the question. Latency roughly halves.

---

## 3. The agent census

```
OFFLINE (per org, on-demand + auto-refresh)
┌─────────────────────────────────────────────────────────┐
│ AGENT #2 — ENRICHMENT AGENT (new)                       │
│ For each allowed table, uses the SAME tool registry to  │
│ read columns, samples, dbt docs, uniqueness — then      │
│ writes a "table card": grain, time column, description, │
│ metrics vs dimensions, join hints, value quirks (MH vs  │
│ Maharashtra). Stored in Postgres with a fingerprint.    │
└──────────────────────────┬──────────────────────────────┘
                           │ table cards
RUNTIME (runner.py orchestrates; graph topology unchanged)
──────────────────────────────────────────────────────────
question
  → [1] understand+route (Haiku call) ── small-talk? → answer, done
  → [2] BM25 ranker (code) → top cards → system prompt injection
  → [3] AGENT #1 — SQL AGENT (v1 loop, unchanged)
        complex lane only: may call ──► SUBAGENT #1 (later)
  → [5] execute (guard) → validate (Haiku call) → "validation" WS event
  → [6] answer + result table + chart chips
```

| # | What | Kind | When |
|---|---|---|---|
| Agent 1 | SQL agent (v1 loop) | Full agent | Shipped |
| Agent 2 | Enrichment agent — builds table cards offline | Full agent, build-time | Phase 2 |
| Subagent 1 | `analyze_complex(question)` — decomposes multi-table comparisons into parallel sub-questions, merges findings. Enters as **a tool in the registry** — no graph change | Subagent-as-tool | Phase 3, only if traces prove the need |
| Subagent 2 | Chart verifier — renders the created chart, checks the image | Subagent-as-tool (vision) | Backlog |

**The rule:** subagents enter through the tool registry, never through graph
surgery. **Why it matters:** the v1 promise — "adding a capability touches one
file" — survives every phase of this plan.

---

## 4. Data model additions (`ddpui/models/chat_with_data.py`)

```python
class ChatWithDataTableCard(models.Model):      # Phase 2
    org          = FK(Org)
    schema_name  = CharField()
    table_name   = CharField()
    card         = JSONField()   # grain, time_column, description,
                                 # metrics, dimensions, join_hints, value_notes
    source_fingerprint = CharField()  # hash(columns + dbt docs)
    built_at     = DateTimeField()

# ChatWithDataTurnAudit gains (Phase 1):
    intent       = JSONField(null=True)   # routed intent + complexity
    validation   = JSONField(null=True)   # {verdict, assumptions, caveat}
```

**The staleness rule:** before injecting a card, compare its fingerprint with a
hash of the live schema. Mismatch → fall back to v1 live discovery for that
table and mark the card for rebuild.
**Why it matters:** the enrichment agent WILL sometimes be wrong or outdated;
this makes that failure visible and self-healing instead of silently poisoning
every future answer (the biggest risk flagged in our architecture review).

---

## 5. Integration points (verified in both codebases)

| Need | Existing pattern to reuse |
|---|---|
| Run enrichment as a background job | Celery + `TaskProgress` (Redis) + poll `GET /api/tasks/{task_id}` — template: `post_run_dbt_commands` → `run_dbt_commands.delay()` (`dbt_api.py:345`, `tasks.py:110`) |
| Admin "Rebuild AI metadata" trigger | New route beside the AI-consent endpoint in `org_preferences_api.py`, gated `can_edit_llm_settings` |
| Auto-refresh after dbt runs | `do_handle_prefect_webhook` (`webhook_functions.py:327`), `FLOW_RUN_COMPLETED` branch → re-fingerprint cards, rebuild stale ones |
| BM25 ranking | Net-new tiny dependency (`rank_bm25` or `rapidfuzz`) — repo has no ranking/embedding libs today; no vector DB needed at NGO table counts |
| Frontend settings page | New `app/settings/ai-data/page.tsx` + nav entry; progress UI modeled on `elementary-setup.tsx` + `pollTaskProgress` |
| Observability for all stages | Langfuse (per session decision): env-gated callback in `runner.py`; validator verdicts pushed as trace scores |

---

## 6. Phasing — each phase ships value alone

| Phase | Contents | Effort | Exit evidence |
|---|---|---|---|
| **1 — Calls, no new agents** | understand+route call · post-execution validator (+ audit fields, WS `validation` event, amber caveat strip) · Langfuse instrumentation · answer-structure prompt template + markdown-subset rendering | ~3–4 days | Warn-rate visible per org; small-talk no longer hits the SQL path; answers readable |
| **2 — Enrichment agent + ranker** | `ChatWithDataTableCard` + fingerprints · Celery enrichment job + settings page trigger · dbt-webhook auto-refresh · BM25 injection into `dynamic_prompt` | ~1 week | Discovery tool-turns per query drop (Langfuse); latency roughly halves on simple questions |
| **3 — Complex-lane subagent** | `analyze_complex` registry tool: plan → parallel sub-queries → merge | ~1 week | Build only if Phase 1–2 traces show complex questions failing/timing out |

**Deliberately not doing:** a supervisor graph (only justified if the tool
registry outgrows one prompt), embeddings/vector search (BM25 first at our
scale), and a pre-execution reflection call on the simple lane.

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Enrichment agent writes a wrong card → persistent wrong answers | Fingerprint staleness check + cards are human-reviewable JSON + validator warn-rate localizes the bad table |
| Two more LLM calls per turn (route + validate) add cost | Both Haiku, ~1–2K tokens each ≈ fraction of a cent; validator runs off the critical path |
| Router misclassifies a data question as small-talk | Route only obviously-non-data intents away; when unsure, send to the SQL agent (fail open) |
| LLM-validates-LLM shared blind spots | Checklist framing + actual result in hand + human review of `warn` rows builds the real eval set over time |
