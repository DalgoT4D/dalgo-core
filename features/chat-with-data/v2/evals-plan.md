# Chat with Data — Continuous Evals Plan

**Date:** 2026-07-09
**Builds on:** [langfuse-evaluation.md](./langfuse-evaluation.md) (the four Langfuse
mechanisms — scores, LLM-as-a-judge, annotation queues, datasets/experiments) and
[plan.md](./plan.md) §8 (the v2 execution plan; §8 is the slice-level milestone list).
**Status:** Draft — tool decision made below; Phase 1 ready to schedule.

Acronyms: LLM (large language model) · SDK (software development kit — the Python
library we call Langfuse with) · CI (continuous integration — the tests that run on
every pull request) · PR (pull request) · OSS (open-source software) ·
OTel (OpenTelemetry — a tracing standard the newer Langfuse SDK is built on).

---

## 1. What "continuous evals" means here

**The rule:** evals run on a schedule and on real traffic, in the background —
nobody has to remember to run them.
**Example:** on Tuesday an engineer tweaks the SQL agent's prompt to improve chart
answers. Nobody re-tests counting questions. Wednesday 6 am, the nightly eval run
scores 25 golden questions and the "SQL correct" rate drops from 24/25 to 20/25.
The team sees the alert Wednesday morning — not a support ticket from Priya on Friday.
**Why it matters:** Chat with Data changes weekly (prompts, models, pipeline nodes).
A one-time test pass proves nothing about next week's build.

Three loops run at once, at different speeds:

```
 every user turn        every night              every prompt/model change
┌────────────────┐    ┌──────────────────┐     ┌──────────────────────────┐
│ ONLINE          │    │ SCHEDULED         │     │ PRE-MERGE                │
│ validator score │    │ golden dataset    │     │ same golden dataset,     │
│ 👍/👎 feedback   │    │ through the real  │     │ run by the engineer,     │
│ sampled judge   │    │ pipeline (Celery  │     │ run-link pasted in the PR│
│                 │    │ beat, 6 am)       │     │                          │
│ → dashboards    │    │ → alert on drop   │     │ → hard metrics must not  │
│   (alert only)  │    │   (alert only)    │     │   regress (blocks merge) │
└────────────────┘    └──────────────────┘     └──────────────────────────┘
          all three land as scores in our self-hosted Langfuse
```

---

## 2. What already exists (verified in code, 2026-07-09)

| Raw material | Where | What it gives evals |
|---|---|---|
| One audit row per turn: question, SQL, tools, tokens, latency, routed intent, validator verdict | `ChatWithDataTurnAudit` — `DDP_backend/ddpui/models/chat_with_data.py` | The candidate pool golden datasets grow from |
| Post-execution validator (grain / filter / false-zero / number checks) | `calls/validator.py`; verdict pushed as Langfuse score `result_validation` in `runner.py` (line ~228) | An online eval already running on every turn |
| One Langfuse trace per turn, generations + tool spans, joined to audit via `request_uuid` | `core/chat_with_data/observability.py` (hand-rolled handler, v2 SDK) | Where all scores attach; per-stage timing |
| The TurnGraph: route → retrieve_context → sql_agent → validate as named nodes | `core/chat_with_data/graph.py` | Per-stage evals (routing accuracy is just the `route_node` output vs a label) |
| Dev harness that drives the real agent from a terminal | `management/commands/chat_with_data_repl.py` | The template for the eval runner command |
| Nightly-capable scheduler | Celery + RedBeat (`ddpui/celery.py:61`) | Where the scheduled loop runs |
| Unit CI with `ScriptedChatModel` (no API key, no cost) | backend test suite (2,138 tests) | Stays the merge gate; evals never slow it down |

**One gap found while verifying:** `langfuse` 2.60.10 is installed in the
`DDP_backend` virtualenv but is **not in `pyproject.toml`** — a fresh
`uv sync` would silently drop tracing. Fixing that pin is Phase 1, slice 1.

---

## 3. Tool decision: Langfuse evals, not DeepEval

Both tools were researched fresh (July 2026) and checked against our stack.

### Comparison

| | **Langfuse evals** (what we'd use) | **DeepEval 4.0.7** |
|---|---|---|
| LLM-as-judge metrics | Managed judges configured in the UI, run server-side on incoming traces; custom judges via our own code + `score()` | G-Eval: judge with chain-of-thought, custom criteria/steps, rubrics — genuinely good metric ergonomics |
| Datasets + experiments | **Verified in our installed v2 SDK (2.60.10):** `create_dataset`, `create_dataset_item`, `get_dataset`, `get_dataset_run(s)`, `DatasetItemClient.link()` — dataset runs compare side-by-side in the UI | `EvaluationDataset` + pytest-style `deepeval test run`; comparison dashboards need Confident AI cloud |
| CI integration | Any script that calls the SDK — our management command | Native pytest plugin (its best feature) |
| Self-hosting / privacy | Server fully MIT OSS since June 2025 — LLM-as-a-judge, annotation queues, experiments all free self-hosted. **Already running self-hosted for tracing** | Framework runs locally, but datasets/dashboards/history live in Confident AI's cloud (free tier: 2 seats, 1 GB; paid from ~$10/seat/mo). No self-hosted server product |
| Fits our dependency pins? | Yes — already installed and shipping traces | **No — hard conflict.** DeepEval requires `grpcio ^1.67.1`; `DDP_backend/pyproject.toml` pins `grpcio==1.63.0` and `protobuf==4.25.3` for the dbt/BigQuery stack. `uv` would refuse to resolve. It also hard-depends on the `openai` SDK (we are an Anthropic shop) and ships `posthog`/`sentry-sdk` telemetry as runtime deps |
| Python floor | any (v2 SDK is plain HTTP) | ≥3.9 — our 3.10 is fine (not the blocker) |
| Cost | ₹0 software; we pay only the judge-model tokens | ₹0 for the framework; cloud dashboards paid; NGO chat data would sit in a third-party US cloud |

### The decision

**The rule:** all evals land as scores in our self-hosted Langfuse; the eval
*runner* and *hard metrics* are our own small Python (a Django management command),
and judge metrics are our own locked prompts — the same pattern as `validator.py`.
No DeepEval dependency in `DDP_backend`.
**Example:** the nightly run loops golden questions through the TurnGraph, links each
trace to its dataset item with `item.link(trace_id, run_name="nightly-2026-07-10")`,
and pushes `eval_sql_correct = 1/0`. The next morning the two runs sit side-by-side
in the Langfuse dataset UI.
**Why it matters:** DeepEval literally cannot be installed into this environment
(the `grpcio` pin conflict is a resolver error, not a style preference), and working
around it — a second virtualenv that can't import Django, or shipping audit rows to
Confident AI's cloud — buys us metric ergonomics at the price of a second system and
a data-privacy exception. Langfuse is already wired, already self-hosted, and its
free OSS server includes every eval feature we need.

**What we borrow from DeepEval anyway (no dependency):** its G-Eval discipline —
write judge *evaluation steps* explicitly and lock them (never let the judge
improvise criteria per run), and use score rubrics with defined bands. Our judge
prompts adopt both.

**Revisit trigger:** if evals ever move to a standalone repo with its own
virtualenv (no dbt pins), DeepEval's pytest runner becomes viable — note it in that
repo's ADR, don't pre-build for it.

### What the v2 SDK can and can't do (the protobuf constraint, restated)

Per `observability.py`'s header and approach-1.md §7 (dbt 1.8 pins `protobuf<5`;
the v3/OTel SDK needs protobuf 5 — so we hand-rolled a v2-SDK handler):

| Need | v2 SDK 2.60.10 | Notes |
|---|---|---|
| Scores on traces | ✅ `trace.score()` / `client.score()` | Already shipping (`result_validation`) |
| Datasets, items, runs | ✅ verified by introspection (§ above) | Everything the plan needs |
| Server-side LLM-as-a-judge, annotation queues | ✅ — server features, SDK-independent | Configured in the UI |
| `run_experiment()` convenience runner | ❌ v3+ only | We write ~40 lines of loop ourselves |
| Server-side "code evaluators" | ❌ needs OTel-ingested traces (v3+) | Our hard metrics run client-side instead — same result |

**Why it matters:** nothing in this plan is blocked by the v2 SDK. When dbt is
upgraded and v3 becomes possible, only `observability.py` and the eval runner's
linking calls change.

---

## 4. What we measure — the six dimensions

Score names are a fixed vocabulary; dashboards and alerts key off them.

| # | Dimension | Score name | How it's measured | Hard or judge? |
|---|---|---|---|---|
| 1 | SQL correctness | `eval_sql_correct` | **Execution-based:** each golden item stores a hand-written *gold SQL*. Run both the agent's SQL and the gold SQL against the dev warehouse; compare result sets (order-insensitive, numeric tolerance). Falls back to expected-value match ("answer contains 1,204") when gold SQL is overkill | Hard |
| 2 | Answer faithfulness | `eval_faithful` | Judge (Haiku, locked steps): every number/claim in the answer text must appear in the result table — the validator's NUMBERS check, run offline with the gold result in hand | Judge |
| 3 | Routing accuracy | `eval_routing` | Compare `route_node` output intent to the item's `expected_intent` label (`small_talk` / `needs_clarification` / `data_question`) — string equality | Hard |
| 4 | Validator agreement | `eval_validator_agreement` | % agreement between `result_validation` and human labels from the annotation queue, computed monthly over labeled turns | Hard (over human labels) |
| 5 | Chart correctness | `eval_chart_correct` | For chart items: assert `tools_called` includes the chart tool and the saved chart config matches expected `{chart_type, dimension_column, metric}` | Hard |
| 6 | Latency & cost | `eval_latency_p95`, `eval_tokens_avg` | From `ChatWithDataTurnAudit.latency_ms` / token columns over the run; asserted against budgets (below) | Hard |

**The rule:** hard metrics gate; judge metrics inform.
**Example:** if `eval_sql_correct` drops 24→20, the pre-merge run fails the PR
ritual. If `eval_faithful` dips 0.9→0.85, it shows amber on the dashboard and a
human reads the three worst traces — no gate, because judges are noisy.
**Why it matters:** blocking merges on a noisy LLM judge trains engineers to
ignore evals; blocking only on deterministic checks keeps the gate trusted.

**Budgets (initial, revisit after 2 weeks of runs):** p95 turn latency ≤ 30 s on
simple questions · average ≤ 40K total tokens per data turn · nightly eval spend
≤ $3 (see §7).

---

## 5. Dataset strategy — how golden sets are born and keep growing

### Seeding (Phase 1)

**The rule:** golden dataset v1 is 25–30 questions against the **dev org's**
warehouse, each item storing `{question, expected_intent, gold_sql or
expected_value, expected_chart (optional), schema_fingerprint, tags}`.
**Example item:** question *"How many farmers enrolled in Maharashtra in May
2026?"* · `expected_intent: data_question` · `gold_sql: SELECT COUNT(DISTINCT
farmer_id) FROM prod.farmers WHERE state='Maharashtra' AND enrollment_date …` ·
tags `["counting", "canary"]`.
**Why it matters:** items with verifiable expectations are what turn "the prompt
feels better" into "run 47 passed 26/28 vs run 46's 22/28".

Coverage checklist for v1 (so we don't seed 25 variations of one question):
counting with grain traps · filtered counts (place + time) · false-zero bait
('MH' vs 'Maharashtra') · trends over time · top-N · a chart request · a
dashboard request · two small-talk turns · two ambiguous first-turns
(expect `needs_clarification`) · one follow-up pair ("…now chart that").

### The growth loop — how it stays continuous

```
real turn ──▶ validator says `warn` ──┐
real turn ──▶ user taps 👎 ───────────┼──▶ Langfuse annotation queue
                                      │      (human labels with rubric:
weekly 10-sample of `ok` turns ───────┘       correct / wrong-grain /
                                              wrong-filter / wrong-value)
                                                      │
                                        interesting? ▼
                              `--promote <trace_id>` on the eval command:
                              anonymize question → retarget to dev schema →
                              write gold SQL → new dataset item
```

**The rule:** every promoted item passes an anonymization step — names, places,
and program identifiers in the question are replaced, and the gold SQL targets the
dev org's warehouse, never the source org's.
**Example:** a warn turn from the SNEHA org asks about "ASHA workers in Dharavi".
The promoted item becomes "field workers in District A" against dev tables. The
original trace stays in Langfuse, tagged with SNEHA's org slug, visible as ever.
**Why it matters:** dataset items are visible to everyone with Langfuse project
access and live forever; per-org trace isolation must not be undone by the eval
layer. (Tracing itself is already env-gated and self-host-only by default —
external hosts need the explicit `CHAT_WITH_DATA_TRACE_EXTERNAL=true` opt-in,
plan.md §8 slice 0.3.)

**The weekly `ok`-sample rule:** the queue must not contain only turns the
validator already suspected — sample 10 `ok` turns weekly too.
**Why it matters:** an LLM validator shares blind spots with the LLM it judges
(plan.md §7 risk); only human labels on *unsuspected* turns reveal them, and this
same labeled set is what `eval_validator_agreement` (§4) is computed from.

### Staleness

Each item stores the `schema_fingerprint` of the tables its gold SQL touches
(same hash the table cards use, `ChatWithDataTableCard.source_fingerprint`). The
runner skips-and-flags items whose fingerprint no longer matches the live dev
schema, and the run summary lists them — a stale item becomes a visible chore,
not a silent false failure.

---

## 6. Continuous execution architecture — what runs where

| Loop | Trigger | What runs | Cost | Blocks merge? | Who looks |
|---|---|---|---|---|---|
| Unit CI | every PR | existing 2,138 tests, `ScriptedChatModel`, zero API calls | ₹0 | **Yes** (already does) | PR author |
| Pre-merge eval | engineer runs `manage.py chat_with_data_eval --dataset golden-v1` before merging any prompt/model/pipeline-node change; pastes the dataset-run link in the PR | full golden set through the real TurnGraph, dev warehouse | ~$1–2 | **Yes, by convention:** hard metrics may not regress vs the last nightly; reviewer checks the link | PR reviewer |
| Nightly | Celery beat (RedBeat), 6 am IST | same command as a Celery task; compares hard-metric pass rate to the previous run; drop > 5 points or any runner error → email alert to platform admins | ~$1–2/night | No — alerts | Eng on rotation, next morning |
| Post-deploy canary | deploy pipeline calls the trigger endpoint | the ~6 items tagged `canary` | ~$0.30 | No — alerts | Whoever deployed |
| Online, every turn | production traffic | `result_validation` (shipping) + `user_feedback` 👍/👎 (Phase 1) + server-side Langfuse judge on a 10% sample (Phase 3) | fractions of a cent/turn | No — dashboards | Weekly eval review |

```
                       ┌── pre-merge (engineer, on demand) ──┐
 golden dataset ───────┼── nightly  (Celery beat 6 am)  ─────┼──▶ TurnGraph
 (Langfuse, self-host) └── canary   (post-deploy, tag)  ─────┘   (dev org warehouse,
        ▲                                                         dedicated eval user)
        │ --promote                                                    │
 annotation queue ◀── warn turns · 👎 turns · weekly ok-sample         │ item.link()
        ▲                                                              ▼
 production traffic ──▶ traces + result_validation ──▶  Langfuse dataset runs,
                        + user_feedback scores           scores, dashboards
                                                               │
                                              weekly 30-min eval review
                                              (warn-rate, feedback, run trend,
                                               3 worst traces read aloud)
```

**Honest constraint:** GitHub-hosted CI runners have no warehouse and no model
keys, so the merge-blocking eval is a *ritual* (command + link in the PR
description + reviewer check), not a required status check. If it's ever
skipped-and-burned twice, that's the evidence to invest in a self-hosted runner
with warehouse access — not before.

**Eval traffic hygiene:** eval runs execute as a dedicated dev-org user
(`eval-runner`) with traces tagged `eval`, so org analytics and warn-rate
dashboards can exclude them with one filter, and eval audit rows are identifiable
by that orguser.

**Who looks — the weekly review:** 30 minutes, the engineer shipping chat +
one reviewer. Fixed agenda: nightly-run trend · warn-rate per org · 👎 turns ·
three worst faithfulness traces read end-to-end · promote 1–3 queue items to the
dataset. The review is the flywheel; skip it twice and the system decays into
dashboards nobody opens.

---

## 7. Cost budget

Rough math per nightly run (30 items, ~22 data questions):

| Piece | Model | Approx tokens/item | Cost/run |
|---|---|---|---|
| Agent turns | Sonnet | ~12K in / 1.5K out | ~$1.30 |
| Route + validate + faithfulness judge | Haiku ×3 | ~5K total | ~$0.15 |
| **Total** | | | **~$1.50/night ≈ $45/month** |

**The rule:** the runner carries a hard token ceiling (env
`CHAT_WITH_DATA_EVAL_MAX_TOKENS`, default ~1.5M/run) and stops with a loud
partial-run alert when hit.
**Why it matters:** a looping agent bug at 3 am should cost $3, not $300.

---

## 8. Phased milestones

Every slice is one red-green-refactor cycle (write the failing test first, make
it pass, tidy). Each phase ships value alone. Phase 1 is **days, not weeks**.

### Phase 1 — Baseline: a golden set and a runner (~2–3 days)

Exit evidence: two dataset runs visible side-by-side in Langfuse; a prompt tweak
demonstrably moves (or holds) `eval_sql_correct`.

| Slice | RED test first | Then |
|---|---|---|
| 1.1 Pin the dep | — (repo hygiene, no test) | add `langfuse==2.60.10` to `DDP_backend/pyproject.toml` + `uv lock` — today a fresh `uv sync` drops tracing |
| 1.2 Feedback score | endpoint test: POST `/api/chat-with-data/turns/{request_uuid}/feedback` `{value: 1\|-1}` → 200, wrong-org → 404 | endpoint resolves the audit row's trace and calls `client.score(name="user_feedback")`; frontend 👍/👎 on answer bubbles (already named in tasks.md item 5) |
| 1.3 Dataset seed command | command test with a fake client: `chat_with_data_eval --seed golden-v1.jsonl` creates dataset + items with `{question, expected_intent, gold_sql, fingerprint, tags}` | `create_dataset` / `create_dataset_item` (v2 SDK, verified §3); author the 25–30 items per the §5 coverage checklist |
| 1.4 Runner core | runner test with `ScriptedChatModel` + fake Langfuse: loops items, calls the TurnGraph service, `item.link(trace_id, run_name)`, pushes `eval_routing` | `chat_with_data_eval --dataset golden-v1 --run-name <auto: date+git-sha>`; template: the REPL command (`chat_with_data_repl.py`) |
| 1.5 SQL-correct metric | pure function test: result-set compare (order-insensitive, float tolerance, column-name-agnostic) over fixture pairs | run gold SQL vs agent SQL on the dev warehouse; push `eval_sql_correct`; expected-value fallback |
| 1.6 Baseline | — | two real runs on the dev warehouse (once, then once after a trivial prompt touch); links recorded in tasks.md — the ritual's first rehearsal |

### Phase 2 — Continuous: nightly, canary, alerts (~3–4 days)

Exit evidence: an eval ran with nobody at a keyboard, and a seeded regression
produced an email.

| Slice | RED test first | Then |
|---|---|---|
| 2.1 Faithfulness judge | parsing/fail-open tests like `validator.py`'s: locked evaluation-steps prompt, rubric bands, returns None on any failure | Haiku judge over (answer, gold result table) → `eval_faithful`; steps written explicitly, G-Eval style (§3) |
| 2.2 Chart assertions | fixture turn with a chart tool call → `eval_chart_correct` 1/0 against expected config | assert over `tools_called` + saved chart config for `expected_chart` items |
| 2.3 Nightly task | Celery task test (mocked runner): schedules via RedBeat, records run summary | `run_chat_evals` beat entry, 6 am IST |
| 2.4 Alert on drop | summary test: pass-rate drop > 5 points vs previous run, or runner error, or token-ceiling hit → alert path called | compare to previous `get_dataset_runs`; email platform admins via the existing email util |
| 2.5 Token ceiling | runner test: fake usage crossing `CHAT_WITH_DATA_EVAL_MAX_TOKENS` → run stops, partial summary flagged | the §7 budget guard |
| 2.6 Canary | trigger-endpoint test: gated `can_edit_llm_settings`, runs only `canary`-tagged items | `POST /api/chat-with-data/evals/canary` → deploy pipeline calls it post-deploy |
| 2.7 Staleness skip | runner test: item whose fingerprint mismatches live schema → skipped + listed in summary | the §5 staleness rule |

### Phase 3 — The human loop: queues, growth, validator calibration (~2–3 days + ongoing ritual)

Exit evidence: dataset grew by ≥ 5 promoted real-world items; first
`eval_validator_agreement` number exists.

| Slice | RED test first | Then |
|---|---|---|
| 3.1 Queue feed | — (Langfuse UI config, no code) | annotation queue with the rubric (`correct / wrong-grain / wrong-filter / wrong-value`); fed by validator warns + 👎 + weekly `ok` sample |
| 3.2 Promote command | command test: `--promote <trace_id>` drafts an item JSON from the audit row, **blocks until** the anonymization fields (rewritten question, dev-schema gold SQL) are filled | the §5 growth loop, human-in-the-middle by construction |
| 3.3 Validator agreement | pure function test: agreement % over (validator verdict, human label) pairs | monthly `eval_validator_agreement` from queue labels; target ≥ 80%, else recalibrate the validator prompt |
| 3.4 Online judge sample | — (Langfuse UI config) | server-side LLM-as-a-judge (free OSS since June 2025) on a 10% trace sample: plain-language clarity + hallucination spot-check, per langfuse-evaluation.md §2 (judges annotate traces; the in-app validator stays the product's caveat source) |

### Phase 4 — Harden the gate (later, evidence-driven)

PR-template checkbox + `make evals` target formalizing the pre-merge ritual ·
latency/cost budget assertions promoted from dashboard to alert · self-hosted CI
runner with warehouse access **only if** the ritual gets skipped twice ·
migrate runner linking to the v3 SDK when dbt drops the `protobuf<5` pin
(touches `observability.py` + the runner's linking calls only).

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| LLM-judge blind spots — Haiku judging Sonnet (same family) misses shared failure modes | Hard metrics (execution-based SQL compare, routing equality) carry the gate; judges only inform. Weekly `ok`-sampling + human labels measure the validator itself (`eval_validator_agreement`) |
| Eval cost creep as the dataset grows | §7 token ceiling with loud partial-run alert; nightly full set but canary is ~6 items; judges stay on Haiku |
| Dataset staleness — dev schema drifts, gold SQL rots | Per-item `schema_fingerprint`; mismatched items skip-and-flag (Phase 2.7), never fail silently |
| Golden set overfits to the dev org — real orgs' schemas are messier | The growth loop (§5) keeps importing anonymized real-org failures; warn-rate per org (online loop) is the metric no offline set can fake |
| Judge nondeterminism makes runs jitter | Locked evaluation steps + rubric bands (the G-Eval discipline), temperature 0, and no gating on judge metrics |
| `protobuf<5` pin strands us on the frozen v2 SDK (no new SDK features, security-patch-only) | Everything needed is verified present in 2.60.10 (§3 table); pin now committed (Phase 1.1); v3 migration is a contained two-file change when dbt upgrades |
| Privacy — eval artifacts leak NGO data | Datasets seeded from the dev org only; promotion requires anonymization by construction (Phase 3.2); Langfuse stays self-hosted with the external-host opt-in gate (plan.md §8 slice 0.3) |
| The ritual decays — links stop appearing in PRs, the weekly review gets skipped | The review has a fixed 30-min agenda and named owners (§6); two skipped rituals = the Phase 4 trigger to automate the gate |

---

## 10. Deliberately not doing

- **DeepEval / Confident AI** — resolver-level dependency conflict and a
  third-party cloud for NGO data (§3); revisit only if evals get their own repo.
- **A custom eval dashboard in the webapp** — Langfuse's dataset-run and score
  views are the dashboard; build nothing until someone outgrows them.
- **Blocking CI on LLM judges** — noisy gates get ignored (§4 rule).
- **Embedding-based answer similarity metrics** — execution-based SQL compare is
  stricter and cheaper for text-to-SQL; similarity scores would only blur it.

---

## Sources (tool research, July 2026)

- Langfuse OSS announcement (all product features MIT, incl. LLM-as-a-judge and
  annotation queues): [langfuse.com/blog/2025-06-04-open-sourcing-langfuse-product](https://langfuse.com/blog/2025-06-04-open-sourcing-langfuse-product)
- Langfuse datasets / dataset runs via SDK: [langfuse.com/docs/evaluation/dataset-runs/run-via-sdk](https://langfuse.com/docs/evaluation/dataset-runs/run-via-sdk) · v2 low-level SDK: [langfuse.com/docs/observability/sdk/python/low-level-sdk](https://langfuse.com/docs/observability/sdk/python/low-level-sdk)
- v2→v3 upgrade path (v2 = critical fixes only; code evaluators need OTel SDKs): [langfuse.com/docs/observability/sdk/upgrade-path/python-v2-to-v3](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v2-to-v3)
- DeepEval G-Eval docs: [deepeval.com/docs/metrics-llm-evals](https://deepeval.com/docs/metrics-llm-evals) · repo/deps (v4.0.7: `grpcio ^1.67.1`, `openai *`): [github.com/confident-ai/deepeval](https://github.com/confident-ai/deepeval)
- Confident AI pricing (free: 2 seats/1 GB; paid from ~$10/seat/mo): [confident-ai.com/pricing](https://www.confident-ai.com/pricing)
- Verified locally: `langfuse==2.60.10` in the `DDP_backend` venv exposes
  `create_dataset`, `create_dataset_item`, `get_dataset`, `get_dataset_run(s)`,
  `DatasetItemClient.link/observe` (introspected 2026-07-09); `pyproject.toml`
  pins `grpcio==1.63.0`, `protobuf==4.25.3`, `requires-python >=3.10`.
