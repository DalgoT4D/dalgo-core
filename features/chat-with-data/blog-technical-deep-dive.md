# Chat with Data: building a warehouse Q&A agent NGOs can trust

*How we built Dalgo's text-to-SQL agent — the architecture, the safety layers, the
production bugs, and the eval harness that tells us whether any of it actually works.*

---

Dalgo is an open-source data platform for NGOs. Our users are program managers and
field coordinators — people who know their programs deeply and their SQL not at all.
Their data lives in a warehouse we manage for them, behind dashboards someone else
built. The question we kept hearing was some version of: *"the dashboard shows Q3 —
I just want to know how Q2 compared."*

Chat with Data is our answer: type a question in plain language, get an answer from
your own warehouse, with the SQL one click away. This post is the engineering story —
not the demo, but the parts that took the time: keeping an agent honest, keeping
tenants isolated, keeping personal data out of model providers, and building the
evaluation harness that catches regressions before our users do.

Three constraints shaped everything:

1. **Our users can't debug us.** A wrong number presented confidently is worse than
   no answer. An engineer spots a suspicious query; a program manager reports it to
   a funder.
2. **The data is sensitive.** NGO warehouses hold beneficiary records — names,
   phone numbers, sometimes health and financial data.
3. **We're a small team.** Whatever we built had to be maintainable by a handful of
   engineers, not a platform group.

## The architecture: a pipeline around a loop

The text-to-SQL literature offers two poles. At one end, a **fixed multi-stage
pipeline** — classify intent, retrieve schema, generate SQL, validate, execute —
where code decides every step (Uber's QueryGPT, AWS's Bedrock reference
architecture). At the other, a **free agent loop** — give a model tools and let it
decide (the classic ReAct pattern).

We ended up where most production teams seem to: **deterministic stages wrapped
around a bounded agent loop**. LinkedIn's SQL Bot has this shape. So does the
official LangGraph SQL-agent tutorial. The pipeline handles what's predictable;
the loop handles what isn't.

```
question ──► route            small model, one call: data question,
                │             small talk, or needs clarification?
                ▼
        retrieve context      (reserved seat for semantic-layer retrieval — more below)
                │
                ▼
            sql_agent         the bounded loop: the model picks tools —
                │             list_tables → get_table_details → profile_column
                │             → execute_sql — until it can answer
                ▼
           validate           small model, after the answer: does the answer
                │             match the SQL and the rows? (never blocks)
                ▼
      events stream to the UI over WebSocket; every turn writes an audit row
```

The parent pipeline is a LangGraph graph; the agent is a subgraph inside it. The
router means a "thanks, that helped!" never spins up warehouse introspection. The
validator means every answer gets a second opinion. And the loop in the middle
means we don't have to enumerate every path a question can take — the model
figures out that answering *"which district improved most?"* needs a look at the
data's actual values first.

One decision we'd defend hard: **each stage is a plain async function with typed
inputs and outputs, and the graph is just wiring.** The router, the SQL guard, the
audit — each is importable, testable, and reusable on its own. When we later built
report summaries (a one-call feature, no loop), it reused the model factory,
tracing, and prompt conventions without touching the graph. When we exposed
capabilities over MCP, the tools shared the same service layer. Frameworks change;
functions with contracts survive.

## Three checks, three different jobs

The most load-bearing design decision is that "is this SQL okay?" is not one
question but three, answered by three different mechanisms:

| Check | When | Who | Can it block? |
|---|---|---|---|
| **Guard** | before every query | code (AST) | yes — fail-closed |
| **Reflection** | before complex queries | small model | yes — sends SQL back for revision |
| **Audit** | after the answer | small model | no — adds a caveat, never blocks |

The **guard** is deterministic: sqlglot parses every query, and the AST must be a
single `SELECT`, within the allowed schemas (and, for scoped sessions, an explicit
table allowlist), with a row limit enforced. `DELETE FROM surveys` doesn't get a
model's opinion; it gets rejected by a parser. This is the only check allowed to
be fail-closed, because it's the only one that can't hallucinate.

**Reflection** catches the queries that parse fine and lie: a JOIN that
double-counts because of a grain mismatch, a filter on the wrong status value. A
small, cheap model reviews complex SQL before execution and can send it back.

The **audit** runs after the answer is already streaming: given the question, the
SQL, and the result, does the narration actually match? It can't block anything —
it attaches a caveat the UI shows ("the question asked about Maharashtra but the
query has no state filter"). Users see the doubt instead of inheriting it.

The taxonomy behind all three: **helpers fail open, deliverables fail loud.** If
the router, reflection, or audit call errors, the turn proceeds as if the check
found nothing — a helper outage must never take down the product. If the report
summary generation fails, the user clicked a button and gets a real error. Every
LLM call in the system is classified as one or the other, and the error handling
follows mechanically.

## Multi-tenancy: the model never knows who it's working for

Every turn builds a `RunContext` server-side: the org's warehouse client, allowed
schemas, result-row caps, the user's permissions. Tools receive it through
LangGraph's runtime injection — **the model never sees org identifiers,
credentials, or connection strings**, so it can't leak what it never had. The
prompt personalizes with the org's *name*; everything that grants access stays in
code.

Query execution goes through exactly one path — the `execute_sql` tool — and that
path runs the guard first, every time. Tools that "create" things (charts,
dashboards) write Dalgo metadata only; nothing the agent can do writes to the
warehouse.

## PII: the result set is the leak surface

Most prompt-safety writeups focus on masking the user's message. That's necessary
and mostly beside the point: in a data agent, **the personal data arrives in the
query results.** Ask "who are our top donors?" and the leak isn't in the question.

We use LangChain's `PIIMiddleware` on the agent — email, credit card, and Indian
phone number rules (the built-in phone pattern is North-America-shaped; ours is
`(?<!\d)(?:\+91[\-\s]?|0)?[6-9]\d{9}(?!\d)`), applied to both user input and tool
results. Two properties took actual verification:

- **Masking rewrites the checkpointed state**, not just the prompt. Conversation
  memory lives in a Postgres checkpointer (more below); the masked version is what
  gets persisted and what any later turn replays. PII never reaches the model
  provider, the checkpoint DB, or the traces.
- **The UI is unaffected.** The result table the user sees comes from a structured
  tool artifact that doesn't pass through the model. Priya sees her beneficiaries'
  real phone numbers; the model sees `[REDACTED]`.

We proved both with a behavioral test — a scripted fake model that *records* what
it was shown, asserting the model saw masked text while the artifact kept the raw
rows. "The middleware is configured" and "the model never saw the number" are
different claims; only the second one matters.

## A war story: the day the agent could only make three tool calls

After shipping the PII middleware, chat died in production with
`GraphRecursionError` after exactly three tool calls. Nothing about the agent had
changed — except that in LangGraph, **every middleware hook is a graph node**, and
every node transition counts against the recursion limit.

Our stack had quietly grown to five before-model hooks and three after-model hooks
(retry limiter, three PII rules, dynamic prompt, history trim, tool-result
clearing). One model-plus-tool cycle went from ~4 graph steps to ~10. The
recursion limit that comfortably allowed a dozen tool calls now allowed three.

The fix was one constant — but the lesson earned a regression test: a scripted
seven-tool discovery turn that must complete under the production recursion limit
with the full production middleware stack attached. If someone adds a middleware,
that test fails before an NGO's chat does. Frameworks bill you in units you didn't
know existed; find the meter.

## Scoped chat: the same agent, fenced

The second surface we shipped is dashboard-scoped chat: open a dashboard, click
"Ask about this dashboard," and the agent answers **only from the tables behind
that dashboard's charts**.

The mechanism is a `scope` on the chat session, re-resolved **every turn**: walk
the dashboard's components → charts and KPIs → their `schema.table` pairs → an
allowlist. Re-resolving per turn (instead of freezing at session create) means a
chart added mid-conversation is in scope for the very next question, and a deleted
dashboard degrades to a friendly error instead of a stale answer.

Enforcement is three-layered, and the layers can't disagree:

1. the **system prompt** tells the agent what this dashboard is about (so it
   interprets "how are the districts doing?" against the right tables),
2. the **discovery tools** only list allowed tables (so the agent doesn't waste
   attempts on tables it can't use),
3. the **guard** rejects any SQL referencing a table outside the allowlist —
   fail-closed, so even a confused agent can't cross the fence.

The prompt makes the agent behave well; the guard makes misbehavior impossible.
Never rely on the first without the second.

## Memory and streaming

Conversation memory is LangGraph's Postgres checkpointer — the graph state itself,
keyed by a thread id, is the source of truth. History replay for the UI reads the
same state through the same artifact contract as the live stream, so the two can
never drift apart.

Streaming is one translation layer (`turn_runner`) that consumes the graph's event
stream and emits a typed WebSocket protocol:

```
{"type": "token", "text": ...}                        the answer, as it's written
{"type": "tool_start", "tool": ..., "label": ...}     "Running query…"
{"type": "tool_end", "tool": ..., "status": ...}
{"type": "message_complete", "message": ..., "result_table": ..., "charts": ...}
{"type": "validation", "verdict": ..., "caveat": ...} the audit, after the answer
```

Two details we'd keep in any rebuild. First, **only the agent's model node streams
tokens to the user** — the router, reflection, and audit also produce tokens, and
without that filter their internal chatter leaks into the answer box. Second,
tools return **content and artifact separately**: the model gets a compact string
("120 rows, showing first 20"), the UI gets the full structured table. The model
never re-echoes tabular data, which saves tokens and eliminates transcription
errors — and one module owns artifact parsing, so the live stream, the audit, and
history replay read tool results identically.

Every turn also writes an audit row — question, SQL executed, tools called,
tokens, latency, router verdict, validator verdict. That table has earned its
disk space several times over: it's where debugging starts, where cost tracking
lives, and where eval candidates come from.

## Evals: the part that changed how we work

Everything above is architecture — reasonable engineers could build it in a month
and still not know if the agent is any good. The eval harness is what turned
"seems fine in the demo" into numbers we'd defend.

### Execution-verified, not vibes-verified

Each golden item is a question plus a hand-written **gold SQL** — and the runner
**executes both** the gold SQL and whatever the agent wrote, comparing actual
result sets. Not string similarity, not "did it run," not a judge's opinion:
do the two queries return the same answer from the same warehouse?

```json
{"question": "How many enrollments are currently active?",
 "expected_intent": "data_question",
 "gold_sql": "SELECT COUNT(*) FROM test_ngo.enrollments WHERE status = 'Active'",
 "tags": ["false-zero-bait", "canary"]}
```

The comparison is deliberately forgiving of *presentation* — agents add context
columns, return full rankings where the gold says `LIMIT 1`, format labels
differently — and strict on *substance*: wrong numbers, wrong rows, empty results.
Every forgiveness rule exists because a real run false-failed a correct answer,
and each is codified with a regression test. Which matters, because:

### Your first eval run measures your dataset, not your agent

Our second dataset came from a real partner dashboard's question list — 14
questions, first run: **8/14**. Reading the failures, only *one* was the agent
being wrong. The rest: a gold answer that forgot to exclude a placeholder
`'Unknown'` row (the agent correctly excluded it — **the eval caught a bug in our
own answer key**), absence questions scored against a numeric gold when the right
answer is prose, and comparison rules too strict about labels and rankings. After
fixing the *items*, with zero agent changes: **13/14**.

If you take one thing from this post: budget calibration time for your eval
dataset itself. The first run's failures are almost all questions about your
questions.

### LLM judges: measured, then demoted

We also wired three LLM judges (via autoevals): answer faithfulness, expectation
matching, and a SQL-equivalence judge that looks at the two queries as text. Then
we measured the SQL judge against the execution-based metric it duplicates.

Across three full runs: the judge agreed with execution on **10 of 31 items — and
all 21 disagreements were the judge false-failing SQL that provably returns
identical results.** Not one false-pass. Agents write structurally different
queries than humans; a judge squinting at text sees "different query," while the
warehouse sees the same rows.

So the policy wrote itself, with evidence attached: **hard metrics gate; judges
inform.** A judge score never vetoes a merge. The faithfulness judge earns its
seat differently — it catches narration drift on questions that have no gold SQL —
and it runs on a different model family than the agent, so they don't share blind
spots. But the moment a judge disagrees with an executed comparison, the execution
wins.

### A flaky eval item is a finding, not noise

One question — *"total achieved in Q3 versus Q4?"* — fails differently on every
run: an empty result set one day, a router detour to clarification the next, a
UNION with the wrong date window the third. Three runs, three failure modes, same
item.

The instinct is to "fix the flake." The flake *is* the signal: the underlying
table stores dates as TEXT with labels like `'Q3 (Oct-Dec 2025)'`, and the agent
has no reliable way to discover that. We tagged the item as a canary and made it
the acceptance test for the next architecture investment.

### The loop, end to end

Datasets are JSONL in git (the source of truth); a management command seeds them
to Langfuse (the scoreboard) and runs them through the **real** production graph
against the dev warehouse. Runs are named after the change being tested, so the
runs tab reads like a changelog. A full judged run costs ~$1.50; a tagged canary
subset ~30¢. Offline unit tests cover the runner itself with a scripted model at
zero API cost.

Current state, replicated across reruns on both datasets: **12/12 and 13/14**,
with the one persistent failure being the canary described above — a known
weakness with a planned fix, which is exactly what an eval suite is for.

## What's next: context beats scaffolding

The evals point somewhere specific. The agent's remaining failures aren't
reasoning failures — they're *context* failures: it doesn't know that `quarter`
holds `'Q3 (Oct-Dec 2025)'`, or that `status` is `'Active'` not `'active'`, until
it burns tool calls discovering it.

So the next iteration is a build-time **semantic layer**: per-table cards
(columns, grain, date ranges) plus **value profiles** — the top distinct values of
every low-cardinality column — computed by deterministic sync jobs and injected as
context before the loop starts. Alongside it: an `EXPLAIN` dry-run in the guard,
structured error correction (classify the failure, attach the missing context to
the retry — because we've seen that raw-error retries repeat the same mistake),
and a read-only warehouse role beneath the guard, so even a guard bug can't write.

We considered and rejected a bigger rewrite — replacing the agent loop with a
fixed plan→generate→validate pipeline. The industry pattern we'd have been
following solves a thousands-of-tables problem; our orgs have dozens. Our own
evals say the loop isn't the weak part. And a plan whose acceptance test is
"the canary item stabilizes" is a much smaller bet than an architecture rewrite
justified by a diagram. Measure, don't guess — the eval harness is what makes
that a real engineering discipline instead of a slogan.

---

*Dalgo is open source (AGPL-3.0) — the code in this post lives in
[`DDP_backend/ddpui/core/ai`](https://github.com/DalgoT4D/DDP_backend), including
the eval harness and both golden datasets. If your NGO wrestles with data
plumbing, come say hi at [dalgo.org](https://dalgo.org).*
