# Engineering Harness Evolution Plan

**Status:** Active
**Owner:** Engineering
**Started:** 2026-06-05

## What This Is

An iterative plan to improve the Dalgo engineering agent harness — the system of commands,
agents, skills, and repo knowledge that allows Claude Code to ship features autonomously.

Inspired by: [OpenAI Harness Engineering (Feb 2026)](https://openai.com/index/harness-engineering/)

The core thesis: **the discipline is in the scaffolding, not the code.** Human effort shifts
to designing environments, encoding constraints mechanically, and building feedback loops
that let agents catch their own failures.

---

## Experiment 0: Command vs Agent Orchestration

**Question:** Does the orchestrator mode (command vs agent) affect output quality?

- **Command mode** (`/engineering/ship-feature`) — runs in the current session, carries
  prior conversation context, user sees every step, natural pause points for confirmation.
- **Agent mode** (`/engineering/ship-feature-bg`) — spawns fresh with zero prior context,
  purely state-driven from pipeline.md, can run in background.

### How to run the comparison

Run both on equivalent features and record the metrics below.

```
# Command mode
/engineering/ship-feature features/report-scheduling/v1/spec.md

# Agent mode  
/engineering/ship-feature-bg features/{comparable-feature}/v1/spec.md
```

Both write `Mode: command` / `Mode: agent` into pipeline.md so results are distinguishable.

### Metrics to capture per run

| Metric | Command run | Agent run |
|--------|------------|-----------|
| Human interventions | | |
| Validate attempts | | |
| Design review attempts | | |
| Did orchestrator read files it shouldn't? | | |
| Did it make a decision based on stale session context? | | |
| Time to PR (minutes) | | |
| PR quality (blocking review findings by human) | | |
| Blast radius misses | | |

### What we're looking for

- **Command advantage:** Orchestrator "remembers" earlier conversation context — useful when
  the user clarified something before running the pipeline. Natural UX.
- **Agent advantage:** Starts clean — no risk of session drift, no stale assumptions from
  earlier in the conversation, deterministic from pipeline.md state alone.
- **Key failure mode to watch:** Does the command orchestrator make a wrong decision because
  it's drawing on something said 50 messages ago that's now stale?

Record findings below after running both.

### Results

*(fill in after running)*

**Command mode run:**
- Feature: 
- Date:
- Human interventions:
- Validate attempts:
- Observations:

**Agent mode run:**
- Feature:
- Date:
- Human interventions:
- Validate attempts:
- Observations:

**Verdict:**

---

## Harness Health Metrics

Measure these on every feature shipped through either pipeline:

| Metric | What it measures | Where recorded |
|--------|-----------------|----------------|
| **Human interventions** | How many times did a human step in? | `pipeline.md` → `Human interventions:` |
| **Validate retry count** | Attempts before validate-spec passed | `pipeline.md` → `Validate attempts:` |
| **First-pass quality** | Did validate-spec pass on attempt 1? | Boolean per feature |
| **Blast radius misses** | Surfaces not in spec that planner surfaced | Count in plan.md Blast Radius section |
| **Agent-review catch rate** | % of PR findings caught before human review | Once self-review is added (Iteration 2) |

---

## Iteration 0: Baseline (measure before changing anything)

**Goal:** Establish a baseline with the current pipeline. Ship one feature end-to-end
and record the metrics above.

**Test feature:** `features/report-scheduling/v1` — has a complete `plan.md` already.

```
/engineering/ship-feature features/report-scheduling/v1/spec.md
```

Record: human interventions, validate retries, what went wrong, time to PR.

---

## Iteration 1: Context Architecture

**Hypothesis:** Agents make better decisions when deep knowledge is always-discoverable
from the repo (not skill-gated), and when prior decisions are recorded.

### 1a. Decision Log in Plans

Add `## Decision Log` to `plan-feature` output template. Every blast radius call,
architecture choice, and scope decision gets timestamped with rationale.

**Why:** When the engineer agent starts fresh, the decision log is the only way prior
reasoning survives across sessions.

Format:
```markdown
## 9. Decision Log
| Date | Decision | Rationale | Alternatives considered |
|------|----------|-----------|------------------------|
```

### 1b. Expand docs/ knowledge base

Move deep architecture knowledge from `.claude/skills/` (skill-gated) into `docs/`
(always-discoverable). Create:

- `docs/DESIGN.md` — design principles, system-level philosophy
- `docs/SECURITY.md` — multi-tenancy, auth patterns, org-scoping, PII
- `docs/RELIABILITY.md` — what must never fail, degradation strategies
- `docs/FRONTEND.md` — component patterns, state management, layout conventions

Skill files become thin pointers to these docs.

**Test:** Ask engineer agent to implement an org-scoped endpoint without explicitly
invoking the backend-architecture skill. Does it get org-scoping right from docs/SECURITY.md?

---

## Iteration 2: Self-Review Gate

**Hypothesis:** Most blocking PR issues can be caught agent-to-agent before a human sees
the PR.

Add a self-review sub-agent spawn between validate and docs in ship-feature. Agent
reviews its own diff, fixes blocking findings, loops up to 2 times.

**Test:** Plant three deliberate violations (missing @has_permission, hardcoded hex,
console.log). Does self-review catch all three before PR opens?

**Success criteria:** Agent-review catches ≥80% of blocking issues human would have found.

---

## Iteration 3: Mechanical Enforcement

**Hypothesis:** Rules encoded as linters (not docs) force compliance at write-time.
Lint error messages written as agent prompts let the engineer self-correct.

**Backend (ruff):**
- `Import inside function body at {file}:{line}. Move to top of file.`
- `Bare except at {file}:{line}. Catch specific exception type.`

**Frontend (ESLint):**
- `Avoid 'any' type at {file}:{line}. Define an interface or use 'unknown'.`
- `Hardcoded color at {file}:{line}. Use CSS variable (var(--color-primary)).`
- `Use toastSuccess/toastError from lib/toast.ts instead of raw toast() at {file}:{line}.`

**Test:** Validate-spec first-pass rate should increase vs baseline.

---

## Iteration 4: Quality Tracking + Garbage Collection

**What to build:**
- `docs/quality-tracker.md` — grades per feature domain (test coverage, architecture compliance, known debt)
- `docs/tech-debt-tracker.md` — specific known issues, owner, priority
- Recurring doc-gardening agent (weekly, via `/schedule`) — scans for stale docs and drift, opens cleanup PRs

**Test:** Plant a TODO with no issue reference. Does the gardening agent surface it
in the next scheduled run?

---

## Iteration 5: Application Legibility

**What to build:**
- Per-worktree boot script — starts full stack in isolation
- Verify skill integrated into ship-feature validate step
- Agent can observe whether UI renders — not just whether tests pass

**Test:** Ship a feature where tests pass but UI has a runtime error (missing API field).
Does the verify step catch it before PR?

---

## Backlog

- Linear integration — agent picks up a ticket and runs the full pipeline
- Log/metrics access — LogQL + PromQL wired into verify step
- Automated PR triage — flag stale PRs older than 48h
