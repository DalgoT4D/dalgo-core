# Chat with Data — state of play vs. the industry (2026-07-09)

**What this is:** an honest read on where our text-to-SQL agent stands today,
how the rest of the industry solves the same problems, and the few things worth
doing next. Grounded in the actual code (file:line), not the architecture docs'
self-description.

**Who should skim this:** a reviewer deciding what to fund next. If you read one
thing, read the two-line summary and Part 3's "Do soon."

Acronyms: SQL (the query language warehouses speak) · LLM (large language model)
· BM25 (a classic keyword-ranking algorithm, no ML) · AST (abstract syntax tree,
the parsed structure of a SQL string) · VQR (verified query repository).

---

## Two-line summary

We build the *agent* well — a clean rented LangGraph loop, a real AST SQL guard,
tenancy that holds by construction, and per-turn measurement. We under-invest in
the thing every commercial competitor leans on hardest: **a library of
admin-verified question→SQL pairs** that doubles as **a ground-truth accuracy
test**. Neither exists yet, and M5 does not add them.

---

## Part 1 — How we're doing

Read against the real files, not the docs.

### The strengths are real

**The rent-vs-own split is disciplined.**
The agent loop is one line of `create_agent` (`agent/build.py:47`); we never call
`add_node`/`add_edge` inside it. The new TurnGraph (`graph.py`) is the *only*
hand-built graph, and it stays thin — nodes are adapters that call the brains in
`calls/`, no logic moved. This is the opposite of the GoPie cautionary tale
(~25 hand-maintained nodes for the same user value).

**The SQL guard is structural, not regex.**
`guards/sql_guard.py` parses with sqlglot and rejects on AST node type — a
`DELETE` hidden in a CTE is still caught (`sql_guard.py:83`), comment tricks
can't bypass it, and it clamps `LIMIT` and enforces the schema allowlist. This is
the single most important safety property and it is done right.

**Tenancy holds by construction, not by prompt.**
Every tool takes `runtime: ToolRuntime[RunContext]` (e.g. `tools/schema_tools.py:15`);
the org id, warehouse client, and allowed schemas are injected server-side and
never appear as a model-suppliable parameter (`agent/context.py:46` is the only
place that reads the ORM). The model *cannot* name another org's data — there is
no argument for one to land in.

**We already do two things a bare agent skips — and they matter:**

| Feature | Where | What it buys us |
|---|---|---|
| Column-value profiling | `tools/profile_tools.py` (`profile_column`) | catches "Maharashtra" vs stored "MH" before filtering — a top-cited silent failure |
| Post-execution validator | `calls/validator.py` | a second Haiku call hunts wrong-grain / missing-filter / false-zero / number-mismatch after the answer |

The validator is genuinely ahead of the median open-source agent. Value-profiling
is exactly the "value/entity awareness" layer that ThoughtSpot and Snowflake build
in (Part 2).

**Every auxiliary brain fails open, and every turn is measured.**
Router, validator, and reflection all return a safe default on any error
(`router.py:135`, `validator.py:121`, `reflection.py:65`) — an aux-brain outage
can never kill a real question. Each turn writes a `ChatWithDataTurnAudit` row
(question, SQL, tools, tokens, latency, intent, verdict) joined to a Langfuse
trace by `request_uuid` (`runner.py:242`).

**The content boundary is handled.**
Claude 5 returns content as block lists (thinking + signature). `extract_text`
(`messages/content.py`) strips the signed thinking blocks at every render/store
boundary. This is a real bug class, handled consistently.

### The weaknesses are also real

**1. No memory of what worked before — every question starts from zero.**
The agent rediscovers the schema by calling `list_tables` / `get_table_details`
each session. There is no store of verified example queries, no few-shot
retrieval of "we answered this before, here's the SQL." This is the biggest gap
and Part 2 shows why. *M5 does NOT close it* (see the note below — table cards are
a different artifact).

**2. We measure activity, not correctness.**
We have rich telemetry but no ground truth. The validator warn-rate is a
*proxy*: it's an LLM judging an LLM, and the plan itself flags the shared-blind-spot
risk (`v2/plan.md` §7). We cannot answer "did that change make answers more
correct?" because we have no set of questions with known-right answers.

**3. The `trim_history` P1 is still live in the code.**
`agent/middleware.py:77` returns `{"llm_input_messages": trimmed}`. The team's
own 2026-07-08 audit found this is a silent no-op in the installed version, so
long threads are not actually trimmed (`approach-2.md` §8, `v2/plan.md` M0-0.1).
The code still shows the un-fixed form. *This is already owned* — the action is
"ship M0," not "re-investigate." An NGO with a long-running session eventually
sends the full history every turn: rising cost and latency, then a hard failure
when it exceeds the model's context window.

**4. No confirmed answer for a sustained provider outage.**
`build.py:50` wires `[sql_retry_limiter, org_system_prompt, trim_history,
clear_old_tool_results]` — no `ModelRetryMiddleware` or `ModelFallbackMiddleware`,
though both exist in the installed `langchain.agents.middleware`. `ChatAnthropic`
has SDK-level `max_retries` (~2), so a transient 529 blip is probably already
absorbed. What's *unverified* is what Priya sees on a sustained Anthropic outage:
today the broad `except` in `runner.py:233` turns it into one generic error and a
dead turn. Worth confirming, not asserting.

**5. First-question latency is 18–40s** (`approach-1.md` §7): RunContext rebuilt
per message, adaptive thinking on every call, schema re-discovery each session.
M5 targets this — roadmap-confirmed, not a new finding.

---

## Part 2 — What others are doing

The pattern is remarkably consistent across open-source and commercial systems.
Sources are linked inline.

### The one move everyone makes that we don't

**A repository of admin-verified question→SQL pairs.** It is cited as the single
biggest accuracy lever across every commercial product:

| System | What they call it | How it's used |
|---|---|---|
| Snowflake Cortex Analyst | Verified Query Repository (VQR) | on a matching question, reuse the *exact* verified SQL; on a near-match, few-shot template |
| Databricks Genie | Trusted Assets / example SQL | verified example queries + SQL functions that return *verified* answers |
| Dataherald | "Golden SQL" | verified pairs in a vector store, retrieved as few-shot |
| Vanna.ai | trained question→SQL pairs | embed the question, retrieve closest prior SQL, prompt with it |

Snowflake's own framing: classic hallucination is rare because every answer runs
real SQL — the failures are *semantic gaps* (missing joins, undefined metrics),
fixed by extending the semantic model and the VQR.
(https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/verified-query-repository,
https://docs.databricks.com/aws/en/genie/trusted-assets)

### A persisted semantic layer (this one M5 *does* plan)

Wren AI (MDL modeling language), Snowflake (semantic YAML), ThoughtSpot (indexed
TML) all hand the model a stored contract: table/column meaning, **explicit join
relationships**, metrics, synonyms — so the model doesn't re-derive joins every
turn. (https://docs.getwren.ai/oss/concepts/what_is_mdl)

**Our M5 table cards are exactly this** — grain, time column, join hints, value
quirks. So this is a *roadmap confirmation, not a gap.* Note the difference from
the item above: a semantic layer describes the *data*; a verified-query repo is a
library of *answered questions*. M5 builds the first, not the second.

### An eval harness as a first-class artifact

Databricks Genie ships a Benchmarks feature (up to 500 test questions per space)
and Databricks' practical bar is **>80% accuracy before user testing**. The
operating loop everywhere is: curated question set → measure accuracy → improve
the semantic layer → re-measure. (https://docs.databricks.com/aws/en/genie/benchmarks)

We have telemetry but no such question set and no accuracy bar.

### What the benchmarks and research say actually moves accuracy

- **BIRD** (large, dirty real databases): human execution accuracy is **92.96%**;
  top systems reach ~73–80%. What tops it: value retrieval, multiple candidates +
  selection, execution-based self-correction. (https://bird-bench.github.io/,
  CHASE-SQL https://arxiv.org/html/2410.01943v1) One honest caveat worth keeping in
  mind for our own validator: BIRD's pass/fail labels agree with human experts only
  ~62% of the time — LLM-as-judge is noisy. (https://www.vldb.org/cidrdb/papers/2026/p5-jin.pdf)
- **Spider 2.0** (real enterprise warehouses, BigQuery/Snowflake dialects, thousands
  of columns): even strong agents crater — o1-preview ≈ **21.3%**. This is the honest
  ceiling on hard, real schemas, and a reason not to over-promise.
  (https://arxiv.org/abs/2411.07763)
- **Techniques that consistently help:** schema linking/retrieval, few-shot
  example retrieval, execution-based self-correction (feed the error back and
  retry), and value/entity normalization. (https://arxiv.org/html/2410.01943v1)
- **A useful contrarian result — "The Death of Schema Linking?":** with strong
  long-context models, aggressively pruning the schema can *hurt* by dropping needed
  columns. At small schemas, just pass the whole (well-described) schema.
  (https://arxiv.org/html/2408.07702v1)

### LangChain's own current SQL-agent guidance

Their canonical agent gives three DB tools (list tables, get schema, run query)
and adds a dedicated **query-checker LLM step** that reviews the SQL *before* it
runs. They note the prebuilt agent is the quick path; a hand-built graph is the
production path. (https://docs.langchain.com/oss/python/langgraph/sql-agent)

Our reflection call (`calls/reflection.py`) is the same idea as their
query-checker — but we run it complex-lane only, to spare the 80% simple case.
That's a defensible, cost-aware variant of standard practice.

---

## Part 3 — What we should improve

Grouped by decision, most valuable first. Each item: **what / why / rough effort /
bucket.**

### Do soon

**A. Build a verified question→SQL library that doubles as the eval set — one loop, two payoffs.**

**The rule:** curate a small set of admin-blessed question→SQL pairs once; use the
same set two ways — as a regression test for accuracy, and as a few-shot retrieval
store injected at query time.
**Example:** an admin marks Priya's "How many farmers enrolled in Maharashtra last
month?" turn as verified. That one pair (a) becomes a test we re-run after every
change to confirm the agent still gets it right, and (b) gets retrieved and shown
to the model the next time someone asks a similar question.
**Why it matters:** this is the single biggest accuracy lever in Part 2 (Snowflake
VQR, Genie Trusted Assets, Dataherald Golden SQL), *and* it's the only way to
answer "did we get more correct?" (the Part 1 weakness #2). It also fixes the
validator's blind spot — the eval set is ground truth, the validator is only a proxy.
**Why it's cheap for us:** the raw material already exists. `ChatWithDataTurnAudit`
already stores question + SQL + validation per turn (`runner.py:242`), and
`rank-bm25` is already staged for M5's retrieval. What's missing is a
curation/approval step and a place to store the blessed pairs. This collapses two
"big" industry practices into one modest initiative — the low-topology, high-leverage
move the repo's taste favors.
**Effort:** medium. Start tiny — a 20–50 question set for a couple of pilot orgs, an
admin "mark verified" action, a nightly job that re-runs the set and reports
pass-rate. The few-shot retrieval half can plug into the M5 `retrieve_context_node`
alongside table cards. Do the eval half first; it's the loop everything else
iterates against.

**B. Confirm the sustained-outage failure boundary.**

**The rule:** verify what Priya sees when Anthropic is down for minutes, not
seconds — before assuming it's fine.
**Example:** during an Anthropic incident Priya asks a question; today the broad
`except` in `runner.py:233` likely gives her one generic "something went wrong"
and a dead turn.
**Why it matters:** consent names Anthropic only, so there's no fallback provider
— a provider incident is a full outage for the feature. If the check shows a dead
turn, the fix is rented, not owned: add `ModelRetryMiddleware` (and consider a
graceful "the assistant is briefly unavailable" message). Both middlewares already
exist in the installed surface.
**Effort:** small — mostly a test that simulates repeated 529s and asserts the
user-facing outcome.

**C. Ship M0 (already owned) — including the `trim_history` fix.**

**The rule:** land the audit fixes before the PRs go up, as already planned.
**Why it matters:** the `trim_history` no-op (`middleware.py:77`) means long
threads aren't trimmed today; left alone, a heavy session grows cost and latency
until it breaks on context limit.
**Effort:** ~half a day (per `v2/plan.md` M0). No new investigation needed.

### Evidence-gated

**D. M5 table cards — build them, but let the data decide whether to prune.**

**The rule:** ship the semantic layer (grain, joins, value quirks) as planned; be
skeptical of the BM25 *top-3 pruning* at NGO scale.
**Example:** an org with 8 tables probably shouldn't have 5 of them hidden from the
model — the "Death of Schema Linking?" result says pruning can drop the column you
needed. The *value* of the cards is the semantic content, not the shortlist.
**Why it matters:** at a handful of tables the whole (well-described) schema fits
in context; pruning risks accuracy for a latency win we may not need.
**Effort:** already in M5 (E8/E9). This is a P2 refinement to that slice, not new work.

**E. Complex-lane decomposer (`analyze_complex`) — only if traces prove the need.**

Already evidence-gated in `v2/plan.md` §8 (Phase 3). Build only if Langfuse shows
complex multi-table questions failing or timing out. Enters as a registry tool, no
graph surgery. Roadmap-confirmed; nothing to change.

### Deliberately never (for us, at our scale)

| Not doing | Why |
|---|---|
| Multi-agent Selector/Decomposer/Refiner rigs (MAC-SQL style) | The GoPie 25-node tale — big latency/cost, marginal gains; our single agent + validator already covers this |
| Large-N candidate generation + trained selector (full CHASE-SQL) | Leaderboard machinery; not worth the cost for ~20 orgs |
| Fine-tuning a custom SQL model (SQLCoder path) | Only pays off past hundreds of verified pairs on a stable schema — verified-query few-shot (item A) gets most of the benefit far cheaper |
| Vector/embedding search for schema retrieval | BM25 is the deliberate, stated choice; embeddings add a store to run for no gain at our table counts |
| Multi-provider fallback | Consent names Anthropic only; a second provider is a legal/consent change, not a tech one |

---

## The one-paragraph version for the roadmap

Keep building the agent the way we build it — the topology discipline, the AST
guard, and by-construction tenancy are genuinely good and ahead of the median. The
gap that matters is not another agent or another node; it's a **curated set of
verified question→SQL pairs** that serves as both our few-shot memory and our
accuracy test. Everything the commercial products do to be trustworthy flows from
having that ground truth, and we can bootstrap it cheaply from the audit rows we
already store. Ship M0, build the tiny eval set, then let its numbers — not our
intuitions — decide what comes after.
