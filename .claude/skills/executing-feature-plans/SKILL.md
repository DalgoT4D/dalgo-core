---
name: executing-feature-plans
description: Use when implementing a feature plan end-to-end across the Dalgo backend (DDP_backend, Django) and frontend (webapp_v2, Next.js). Triggers on "execute this plan", "implement this feature", "build this from the plan", working from a plan.md / tasks.md.
---

# Executing Feature Plans

## Overview

Implement a feature from its planning document, full-stack across `DDP_backend`
(Django + Django Ninja) and `webapp_v2` (Next.js + React), using **red-green-refactor,
one test at a time**.

**Where the code lives:** the backend and frontend are **sibling repos of `dalgo-core`**
(`../DDP_backend`, `../webapp_v2`) — not nested inside it, so their CLAUDE.md / skills /
rules do **not** auto-load. **Read both repos' CLAUDE.md before writing any code** — each
is the source of truth for that repo's run/test/lint commands and conventions. Don't guess
commands. (File access to the siblings is granted in `settings.json → additionalDirectories`.)

**Implement inline, in this one session.** Backend and frontend are tightly coupled within
a slice (an endpoint and the UI that consumes it), and tightly-coupled, shared-context work
is the documented weak spot for subagents — keep the API contract in working memory rather
than threading it across isolated contexts. Use subagents only for the **read-only bookends**
that would otherwise flood this context (see *Subagents* below).

**Core principle:** every slice of behavior is driven by a single failing test you
watched fail. No production code exists that a test didn't ask for.

## When to Use

- A `plan.md` (and usually `research.md`) exists and you're ready to write code
- The feature spans backend, frontend, or both
- You're resuming a partially-built feature (a `tasks.md` already exists)

**Not for:** writing the plan itself (use `/engineering/plan-feature`), one-line
hotfixes, or exploratory spikes you'll throw away.

## Process

### 1. Worktree first — before any code

Isolate the work in a fresh git **worktree** per code repo you'll touch — never implement
in a repo's main working tree, and never on `main`. (See `superpowers:using-git-worktrees`
for the mechanics and rationale.)

```bash
# <feature> = short kebab-case name; one line per repo you'll touch
git -C ../DDP_backend worktree add ../.dalgo-worktrees/<feature>/DDP_backend -b feature/<feature> origin/main
git -C ../webapp_v2   worktree add ../.dalgo-worktrees/<feature>/webapp_v2  -b feature/<feature> origin/main
```

All worktrees live under the dedicated root `../.dalgo-worktrees/<feature>/`, which is
writable via `settings.json → additionalDirectories`. **Do all code work inside these
worktree dirs**, not in `../DDP_backend` / `../webapp_v2`. The feature artifacts
(`plan.md` / `research.md` / `tasks.md`) stay in `dalgo-core`. After the PRs merge, clean
up with `git -C ../DDP_backend worktree remove ../.dalgo-worktrees/<feature>/DDP_backend`
(and the same for `webapp_v2`).

### 2. Load the plan and set your checkpoint

- Read the plan document and `research.md` in the same `features/{name}/{version}/` folder.
  `research.md` already holds the planner's findings — **consume it; don't re-run discovery.**
  Only investigate gaps it doesn't cover.
- Create/open `tasks.md` in that folder. It is your resume checkpoint — mark tasks
  done as you finish them. If it exists, start from the first unfinished task.
- For broad orientation across the two repos, you may offload exploration to a subagent
  (see *Subagents*) — but read the specific file you're about to mimic yourself.

### 3. Slice the work

Break each milestone into **thin vertical slices** — the smallest unit of observable
behavior. Prefer a slice that crosses the stack: one endpoint **plus the UI that consumes
it**, built back-to-back so the API contract is fresh in mind. Each slice is one
RED-GREEN-REFACTOR cycle.

### 4. Execute — red-green-refactor, one test at a time

For each slice, in order:

| Phase | Action |
|-------|--------|
| **RED** | Write a SINGLE minimal failing test. Run it locally (the repo's test command). Confirm it fails for the right reason. |
| **GREEN** | Write the minimum code to pass it. Re-run locally. |
| **REFACTOR** | Improve the code's shape, keeping the test green. |

Then the next slice. **"Red/green" is the local test run** (seconds) — never push-and-wait
on CI. Remote CI is the **final gate** before the PR (step 6), not the inner loop.

Write one test at a time — do **not** batch tests upfront. The discipline is identical in
both repos; each repo's testing skill/rules has its patterns. **Commit after each
green-and-refactored slice** (or per milestone) — `tasks.md` plus clean commits are your
resume points after an interruption.

### 5. Validate

- Ensure all touched services are running.
- Run each validation command from the plan; run the full test suite in each changed repo.
- Fix failures and re-run until everything passes.
- **UI features — browser smoke test (Playwright MCP):** with the webapp dev server up
  (`npm run dev`, port 3001), drive the new flow end-to-end through the Playwright MCP
  tools — navigate to `http://localhost:3001`, log in with the local test credentials, walk
  the new UI, and screenshot the result. A broken flow is a failing test: fix and re-run.
  - Read credentials from `.claude/test-credentials.local.json` (`local_dalgo.email` /
    `.password`). **Never hardcode credentials in this skill or in code**, and never use
    real/shared credentials — that file is local-only and gitignored.
- Optionally dispatch a code-review subagent over the milestone's diff (see *Subagents*);
  fold its findings back as new slices.

### 6. Complete & pre-merge

- Confirm every `tasks.md` item is done; re-read the plan to confirm nothing was missed.
- Run the final validation suite. Let remote CI run as the final gate.
- **Two repos → two PRs.** Push each worktree's `feature/<feature>` branch and open the
  **backend PR first** (its API must exist for the frontend to build against), cross-link
  the two PRs, and state the merge order. If they must ship together, say so in both.
- Suggest `/engineering/validate-spec` before opening the PRs.
- After both merge, remove the worktrees (`git worktree remove`, see step 1).

## Subagents — read-only bookends only

Implementation stays inline (see Overview). Subagents fit **only** where a side task would
flood this context with material you won't reference again and can be handed back as a
summary — Anthropic's documented use case for them:

- **Orient (before step 4):** dispatch an `Explore` subagent to map *where/how* a pattern
  is done across the repos and return `file:line` pointers. Use it for breadth, not to
  write code — read the specific file you're about to mimic yourself.
- **Review (after a milestone):** dispatch a code-review subagent over the diff; it returns
  findings, you turn them into slices.

**Do NOT split implementation across subagents** (e.g. one per repo). Coding is tightly
coupled, agents coordinate poorly in real time, and you'd lose the API contract while
paying ~15× the tokens for the handoffs. `tasks.md` on disk is the shared checkpoint
between any subagent and you — never route findings through memory alone.

## Red Flags — STOP

- Implementing in a repo's main working tree or on `main` (you skipped the worktree step)
- Writing code in a repo before reading its CLAUDE.md (siblings don't auto-load)
- Splitting implementation across subagents — coding is tightly coupled; keep it inline
  (subagents are for orientation/review only)
- Implementation before a failing test exists, or several tests written upfront
- "I'll just push and let CI tell me" — CI is the final gate, not the inner loop
- "Frontend is hard to test, I'll skip it" — the loop is identical in `webapp_v2`
- Marking a `tasks.md` item done with no test backing it

**Each means: stop, branch / read the repo's CLAUDE.md / write the single failing test,
watch it fail, then code.** The generic TDD rationalizations ("too simple to fail",
"tests-after is the same") are covered by `superpowers:test-driven-development`; this list
holds only the traps specific to executing a Dalgo plan across two repos.
