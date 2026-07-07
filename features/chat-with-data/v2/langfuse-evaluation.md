# Chat with Data — Evaluation with Langfuse

**Date:** 2026-07-07
**Context:** Langfuse tracing shipped on `feature/chat-with-data` (DDP_backend
`6a912acf`) — one trace per turn, generations per model call, spans per tool
call, joined to `ChatWithDataTurnAudit` via `request_uuid`. This doc covers the
next layer: using Langfuse's **evaluation framework** on top of those traces.
Companion to [plan.md](./plan.md) (v2 Phase 1 includes the result validator).

**Licensing:** everything below — scores, LLM-as-a-judge, annotation queues,
datasets/experiments, prompt management — is in the **free self-hosted OSS
version**. Enterprise adds only governance (project RBAC, retention management).

---

## The four mechanisms

### 1. Scores — the foundation (wire first)

**The rule:** a score is a labeled verdict attached to a trace
(`{name, value, comment}`); every other evaluation feature consumes scores.
**Example:** the turn where Priya asked "how many farmers enrolled?" gets
`result_validation = 0` with comment "counts visit rows, not unique farmers".
**Why it matters:** without scores, traces are just logs; with them, quality
becomes a queryable metric.

Two producers, both already designed:

- **Result validator** (v2 plan Phase 1): the post-execution Haiku check pushes
  its verdict onto the trace:

  ```python
  langfuse.score(
      trace_id=trace_id,            # exposed by LangfuseTurnHandler
      name="result_validation",
      value=1 if verdict == "ok" else 0,
      comment=caveat,
  )
  ```

- **User feedback**: 👍/👎 buttons on each answer bubble → small REST endpoint →
  `langfuse.score(trace_id, name="user_feedback", value=...)`.

Dashboards this unlocks: warn-rate per org over time; do users thumb-down the
turns the validator flagged (validator calibration); did a prompt change move
either number.

### 2. LLM-as-a-Judge — evaluators running inside Langfuse

Configured in the UI (judge prompt + trace filter + Anthropic key); Langfuse
runs them server-side against incoming traces — zero backend code.

**The rule:** keep the in-app validator for anything the *product* needs (the
amber caveat Priya sees, the audit column); use Langfuse judges for extra
dimensions that only annotate traces.
**Example judges for us:** plain-language clarity ("understandable to a
non-technical reader?"), hallucination spot-checks on a 10% sample, tone.
**Why it matters:** new quality dimensions become UI configuration, not
deploys — and sampling controls their cost.

### 3. Annotation queues — humans label the suspects

Create a queue with a rubric (`correct / wrong-grain / wrong-filter /
wrong-value`), auto-feed it every validator `warn` and every 👎, and review
each trace with the SQL and result in view.

**Why it matters:** this is how a labeled ground-truth set accumulates as a
side effect of debugging — no spreadsheets — and it is the only way to learn
whether the LLM validator itself can be trusted (LLM-judging-LLM shares blind
spots; humans anchor it).

### 4. Datasets + experiments — regression testing for prompt changes

**The rule:** no prompt/model/middleware change ships without an experiment run
against the golden dataset.
**Example:** "run 47 passed 44/47 vs run 46's 41/47 — here are the three
regressions" replaces "the prompt feels better".

Flow:

1. **Dataset:** 20–30 golden questions against the dev org's warehouse with
   expected outcomes ("counts distinct farmers", "filters May 2026"). Seed
   manually + one-click "add to dataset" from annotation-queue items.
2. **Experiment runner:** a management command (sibling of the REPL) that loops
   dataset items through `run_turn`, links each trace to its dataset item, and
   scores it (exact-match where the expected number is known; judge otherwise).
3. **Compare runs side by side** in the Langfuse UI before merging.

---

## Rollout order

| Step | Effort | Unlocks |
|---|---|---|
| Expose `trace_id` from handler; validator pushes `result_validation` score | small (validator is v2 Phase 1) | Warn-rate dashboards |
| 👍/👎 endpoint + chat UI buttons → `user_feedback` score | ~half a day | Real user signal, validator calibration |
| Annotation queue on warns + thumbs-down | UI config only | Ground truth accumulates |
| Dataset + experiment management command | ~a day | Regression-tested prompt changes |
| Langfuse LLM-judge on a trace sample | UI config only | Clarity/hallucination dimensions |

The first two belong in v2 Phase 1 alongside the validator; the rest follow
once real traces exist.

---

## Constraints to remember

- We use the **langfuse v2 SDK** (dbt 1.8 pins `protobuf<5`; the v3/OTel SDK
  needs protobuf 5). All scoring/dataset APIs used here exist in v2. When dbt
  is upgraded, migrating to v3 touches only `observability.py`.
- Traces contain prompts **and query results** — production orgs require a
  self-hosted Langfuse inside the deployment (consent covers Anthropic, not an
  extra third party).
- Score identities stay opaque (`orguser.id`, `session.id`) — never emails.
