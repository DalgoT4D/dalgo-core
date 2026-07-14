# Chat with Data: why our agent needed more than MCP

A few months ago, someone on the team asked a simple question: why not just let Claude
talk to our MCP server directly? No LangGraph, no custom pipeline, just an agent calling
tools. It's a fair question, and for about a day it felt like the right answer. Then I
tried to build a real feature on top of it — for an NGO program manager named Priya who
wants to ask "how many farmers enrolled in Maharashtra last month?" and get a straight
answer. That's when the gaps showed up. This post is the approach I landed on because of
them.

Three terms, in plain words, since the whole post leans on them. **MCP** (Model Context
Protocol) is a standard way to expose tools — "here's a function called
`get_table_data`, here's what it takes and returns" — so any AI model can discover and
call them. **LangGraph** is a library for wiring model calls and code into a graph of
steps, where *you* decide the order instead of the model. A **checkpoint** is the saved
state of a conversation, written to our Postgres database after every step, so a chat
can be resumed, replayed, or debugged later.

## What we're building

Chat with Data is a chat page in Dalgo, our open-source data platform for NGOs. A
program manager types a question in plain English. An agent looks at her organisation's
warehouse, writes a safe, read-only SQL query, streams back an answer, and can spin up
charts and dashboards from the result. Simple to describe. Much harder to make reliable.

*[screenshot: the chat page answering a question, with tool-progress chips]*

## Why pure MCP wasn't enough

MCP is genuinely great at one thing: defining tools and letting any LLM discover and
call them. Our Dalgo MCP server already exposes tools like listing tables or fetching
table data, and in a raw chat session an agent can call those directly and get real
answers. No framework needed.

But the moment you ask a follow-up — "show me the same for last month" — it falls
apart. MCP calls are stateless: each one is a fresh request with no memory of what came
before. And there's no way to make something *always* happen. If you want every SQL
query checked for a stray `DELETE` before it runs, or a cap on tool calls so the agent
can't loop forever, MCP gives you no lever. The model decides everything, including
things you never want it deciding.

That's the core issue. MCP answers "how does a tool get registered and called." It says
nothing about "what must always happen regardless of what the model wants." For that I
needed an orchestration layer on top — which is where LangGraph came in.

## Building the TurnGraph

I started with a single agent and a tool loop (list tables, get details, run SQL,
done). It worked, but everything — small talk included — went through the same
expensive model call. So I built the TurnGraph: a graph that wraps the agent, where
each stage is a node with one job, checkpointed in Postgres so every turn is replayable.

```
question ──► route_node ──┬─ small talk / vague ──► cheap reply, turn ends
                          │
                          └─ real data question
                                   │
                          retrieve_context_node   (empty seat — see "what's next")
                                   │
                              sql_agent           the tool loop, mounted as one box
                                   │
                             validate_node        checks the answer, never blocks it
                                   │
                        tokens stream to the browser
```

Each node earns its place by solving something pure MCP left unsolved.

**route_node** exists because not every message deserves the expensive agent. One cheap
model call decides: small talk, a vague question that needs clarifying, or a real data
question. It *fails open* — if the call breaks, the turn falls through to the real
question path instead of dying. Without a step that runs before the agent, you're
paying full agent cost for "thanks!" and hoping the model routes itself.

**casual_reply_node and clarify_node** end those turns without waking the agent. They
live inside the graph, not as special cases in application code, so the exchange
checkpoints naturally — a follow-up like "no, I meant Kerala" still has memory of what
was clarified.

**retrieve_context_node** is deliberately empty today — a reserved seat for injecting
knowledge about the tables before the agent starts guessing. Pre-processing that must
always run before the model sees the question is exactly what MCP has no concept of.
The seat exists now so the capability slots into a proven position later, instead of
forcing a rewrite.

**sql_agent** is the original agent, mounted inside the bigger graph as if it were a
single step. That boundary is deliberate: the pipeline around it is mine to rewire; the
agent's own loop only grows through its tool registry. It's what let me build all of
this without touching the agent, the WebSocket consumer, or a line of frontend code.

**validate_node** always runs last on the data path, and only ever looks at the current
turn — so a bad verdict from turn one can't leak into turn two. It's the guardrail MCP
can't give you: something that checks every answer, rather than trusting the model to
grade its own work.

The part that mattered most wasn't the routing — it was visibility. Every stage is a
named node with its own timing in traces, replayable from the checkpoint. "Where did
this turn spend its time" used to mean reading logs and guessing. Now it's a query.

## The day the agent could only make three tool calls

One war story, because it's the sharpest lesson in the whole build. After we added PII
masking (more on that below), chat died in production with a recursion error after
exactly three tool calls. Nothing about the agent had changed.

The cause: in LangGraph, **every middleware hook is secretly a graph node**, and every
node transition counts against the graph's step limit. Our stack had quietly grown to
eight hooks — a retry cap, three PII rules, a dynamic prompt, history trimming, tool
result cleanup. One think-then-act cycle went from ~4 steps to ~10, and a limit that
comfortably allowed a dozen tool calls now allowed three.

The fix was one constant. The lesson earned a permanent test: a scripted seven-tool
conversation that must complete under the production limit with the full middleware
stack attached. If anyone adds a hook, that test fails before an NGO's chat does.
Frameworks bill you in units you didn't know existed — find the meter.

## Three checks, three different jobs

It's easy to hear "the thing that catches bad SQL" and assume it's one thing. It's
three, and only some are allowed to stop a turn:

| Check | When | Who | Can it block? |
|---|---|---|---|
| **Guard** | before every query | plain code, parsing the SQL | yes — rejects unsafe SQL outright |
| **Reflection** | before complex queries only | a small model | yes — sends the SQL back for revision |
| **Audit** (validate_node) | after the answer is built | a small model | no — adds a caveat, never blocks |

The guard is deterministic and absolute: a stray `DELETE` is rejected by a parser, no
model involved. Reflection reviews a complex query's *logic* — a join that would
silently double-count — before it runs. The audit runs after Priya already has her
answer; its job is to notice when the SQL doesn't match the question (asked about
Maharashtra, never filtered by state) and surface that as a visible caveat instead of
pretending the answer is more certain than it is.

Keeping "can this block?" as the deciding question is what stopped us from letting a
slow, fuzzy check gate every turn. The same rule generalizes into one asymmetry applied
everywhere: **helpers fail open, guards fail closed.** If the router, reflection, or
audit breaks, the user still gets an answer, just with less polish. If the guard can't
parse a query, nothing executes, full stop. A broken helper should never block a real
question; a broken guard should never let a bad query through. Deciding that up front
meant never debating it mid-incident.

## Answers as a two-sided contract

One thing I didn't expect to matter so much: the shape of the answer itself. Early on
the model returned whatever prose felt natural and the frontend rendered raw markdown —
a stray link or a wall of text could show up unpredictably.

Now it's a contract with two sides that must agree. The prompt teaches the model an
answer shape: bold headline number first, structure that scales with the answer (one
fact stays a sentence; three-plus items become bullets), at most one callout, a closing
line on how it was computed. The frontend renders *only* that subset — anything outside
it (links, raw HTML) renders as plain literal text. A misbehaving output can't inject
anything, and a test pins the two sides together: change the prompt's allowed formatting
without updating the renderer, and the build fails.

## What's next: context, correction, containment

The failures we still see aren't the agent picking wrong tools or looping — the graph
handles that. They're *context* failures. Priya asks what was achieved in Q3, the agent
writes `WHERE quarter = 'Q3'`, and gets zero rows — because the column actually holds
`'Q3 (Oct-Dec 2025)'`. The loop didn't make a bad decision. It just didn't know what
the data looked like.

The tempting fix was a big rebuild: a fixed multi-stage pipeline with specialist SQL
and checker agents, and a human approving table choices — the way platforms with
thousands of tables do it. We rejected most of that, because our own eval runs didn't
support the diagnosis: both golden datasets were passing 12/12 and 13/14 on hard
metrics, and every remaining failure was a context problem. A rebuild would treat a
disease our measurements don't show. So the loop stays, and three things go around it:

**Context** means table cards. A scheduled job walks each table and records what's
actually in it — columns, row counts, date ranges, and for low-cardinality columns the
*real* distinct values. That's the piece that kills the Q3 bug: once the agent can see
what `quarter` actually contains, it writes the filter right the first time. The cards
flow in through `retrieve_context_node` — the seat that's been empty since the graph
was built, for exactly this.

**Correction** means changing what a failed query teaches. Pasting the raw database
error back tends to produce the same wrong fix again. Instead, code classifies the
failure (unknown column, bad filter value, wrong table) and attaches the *missing
context* to the retry — the real value list for a bad filter, alternative tables for a
wrong guess. Same retry cap; each retry just knows something it didn't.

**Containment** means layers under the layers. The guard already blocks anything that
isn't a single read-only SELECT — but a guard can have a bug, so underneath it we're
rolling out an actual read-only database role: even if bad SQL got through, the
credentials refuse to run it. And containment covers the model provider too: before
anything reaches a model — the user's message or rows coming back from a query — a
masking pass strips emails, card numbers, and phone numbers, and rewrites the
checkpointed state so PII never sits in a saved thread or a trace either. The one
deliberate exception: the result table Priya sees comes from the tool's structured
output, not the masked text — so she sees her organisation's real data even though the
model never did.

The part I'm most glad we did: writing down, in advance, what would make us reverse
course. If evals after this ship still show wrong-table failures, that's evidence for
the human-approval step we deferred. If a wrong-SQL class persists despite good
context, that's evidence for the pipeline rebuild — built as an experiment the eval
harness judges, not a commitment made on a hunch. Writing decision criteria before the
results exist is the only way I know to avoid talking yourself into the bigger rebuild
because it feels more thorough.

## Where the lines actually sit

If I had to draw it for someone starting fresh: **MCP** is for exposing tools to
clients you don't control — Claude, GPT, whatever a user connects. A distribution
protocol, not a brain. **LangGraph** (or anything like it) is for surfaces you own end
to end, where you need memory, retries, deterministic steps, and streaming. And the
third category people forget: **the actual guardrails** — the SQL guard, the validator
— which neither gives you for free. You write those once, as plain functions, and let
both the MCP server and the graph call the same logic.

The lesson underneath: frameworks don't remove the need to decide what must *always*
happen versus what the model gets to choose. MCP hands you a great way to expose
choices to an LLM. LangGraph hands you a great way to take some of those choices away —
deliberately, visibly, one node at a time. Every piece here, from the router that saves
money on small talk to the answer contract that keeps rendering predictable, exists
because something specific broke when I didn't have it.

And none of it stayed scoped to one feature — the real sign it was the right shape. The
same package now runs one-click report summaries, reusing the same model factory,
tracing, and failure discipline, applied differently: a helper fails silently and the
turn carries on, but if the summary itself fails, the user clicked a button and
deserves a real error, not a blank report. Building it once as shared infrastructure is
why the second feature took days instead of weeks.

---

*Dalgo is open source (AGPL-3.0) — everything here lives in
[`DDP_backend/ddpui/core/ai`](https://github.com/DalgoT4D/DDP_backend), including the
eval harness and golden datasets. If your NGO wrestles with data plumbing, come say hi
at [dalgo.org](https://dalgo.org).*
