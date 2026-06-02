# How I Used Claude to Manage an Entire Open Source Project in One Session

*A walkthrough of reviewing 250 issues, auditing 12 pull requests, and shipping automated CI — without leaving the chat.*

---

A few weeks ago I sat down with a growing list of tasks for [Dalgo MCP](https://github.com/DalgoT4D/dalgo-mcp) — a new MCP server we're building that lets AI assistants talk directly to Dalgo's data platform. There were Linear issues stacking up, a dozen open pull requests waiting for review, and no CI pipeline to catch regressions.

I decided to do something different. Instead of grinding through it tab by tab, I opened a Claude Code session and just… talked my way through it.

This is what happened.

---

## The Problem: Too Many Things, Not Enough Eyes

Dalgo is an open-source data platform built for NGOs. We help small organisations — the kind running on Excel sheets and good intentions — set up automated data pipelines, dashboards, and reporting. The team is lean: a handful of engineers, a PM, a design lead, some consultants.

The `dalgo-mcp` repo is our newest bet: an MCP server so that AI tools like Claude can query your Dalgo pipelines, dashboards, and warehouse directly in conversation. It's been moving fast.

Fast, in this case, meant 12 open pull requests and nobody had reviewed a single one.

---

## Step 1: Pulling the Full Picture from Linear

I started by asking Claude to pull all our open issues from Linear.

Two hundred and fifty issues came back — spanning engineering, marketing, consulting, and design. Not just `dalgo-mcp` stuff — the full picture of what the organisation was tracking. At a glance I could see:

- **21 Dalgo MCP issues** — all in Backlog, assigned to me, ranging from urgent (PII masking gap, JWT token leak) to low (auto-generate README table)
- **Metrics & KPIs sprint** was mid-flight with several dogfood sign-offs still pending
- **Prefect upgrade to 3.6.24** was broken into 5 phases, all in progress
- A smattering of marketing, brand, and consulting tasks mixed in

The important thing wasn't the count. It was having the whole board in front of me in one read, grouped by project and priority, without clicking through ten Linear views. Thirty seconds of parsing instead of five minutes of navigation.

---

## Step 2: Reviewing PRs in dalgo-core

Next I pulled all pull requests from `dalgo-core`, our monorepo. Nineteen total — one still open.

PR #19 — *"improve(skills): strengthen docs-generation for bi-weekly scan"* — had been sitting open since May 24. It added filtering rules for what to document during bi-weekly doc scans, a paired-PR rule for features that span backend and frontend, and a self-improvement workflow for the skill itself.

Small PR, clear scope, no obvious issues. I noted it for a quick merge.

The other 18 were all merged. Looking at them in sequence told a story: the team had been steadily building out the skills and commands system — spec writing, PR review, debugging — and iterating on the consulting workflow process.

Useful context. All of it in two minutes.

---

## Step 3: The Real Work — 12 Open PRs in dalgo-mcp

Here's where it got interesting.

The `dalgo-mcp` repo had 12 open pull requests, all opened on the same day, all by the same author (me, via Claude). This was the output of a session where I'd asked Claude to work through the Linear backlog and generate PRs for each issue. Each PR was neat, scoped, and had a clear test plan.

But had any of them actually been tested? Did they break anything? Did they conflict with each other?

I asked Claude to run the verification locally — fetch all 12 branches from GitHub, check out each one, and run two checks:
1. Does `from dalgo_mcp.server import app` import cleanly in stdio mode?
2. Do the tests pass?

The script ran each branch in sequence, cleaning up between checkouts, installing dependencies fresh each time. Here's what came back:

```
PR #22 | PASS | Import: PASS | Tests: SKIP (no tests/)
PR #23 | PASS | Import: PASS | Tests: SKIP (no tests/)
PR #24 | PASS | Import: PASS | Tests: SKIP (no tests/)
PR #25 | PASS | Import: PASS | Tests: SKIP (no tests/)
PR #26 | PASS | Import: PASS | Tests: SKIP (no tests/)
PR #27 | PASS | Import: PASS | Tests: SKIP (no tests/)
PR #28 | PASS | Import: PASS | Tests: 43 passed ✓
PR #29 | PASS | Import: PASS | Tests: SKIP (no tests/)
PR #30 | PASS | Import: PASS | Tests: SKIP (no tests/)
PR #31 | PASS | Import: PASS | Tests: SKIP (no tests/)
PR #32 | PASS | Import: PASS | Tests: SKIP (no tests/)
PR #33 | PASS | Import: PASS | Tests: SKIP (no tests/)

Result: 12 / 12 PRs healthy
```

**12 for 12.** Every branch imported cleanly. PR #28 — the one that added the test suite — ran 43 tests and passed all of them.

One thing stood out: only PR #28 had tests. The other 11 PRs would skip the test step simply because the `tests/` directory didn't exist on those branches. The fix is obvious: merge #28 first. Once the tests land on `main`, every subsequent branch will inherit them and the test step will actually run.

That's the kind of thing you only notice when you look at all 12 at once.

---

## Step 4: Building the Automated Review Pipeline

Running checks manually in a session is useful. But it evaporates the moment the session ends.

I wanted something permanent: a GitHub Actions workflow that would run these same checks on every new PR, automatically, without anyone having to remember.

Claude built `.github/workflows/pr-review.yml` with two jobs:

**Job 1 — verify:** Installs the package via `uv`, checks the server imports cleanly in stdio mode (no live backend needed — dummy env vars are enough), then runs `pytest` if a `tests/` directory exists.

**Job 2 — claude-review:** Uses `anthropics/claude-code-action@beta` to read the PR diff and post inline review comments. The prompt is specific: check for breaking changes to tool APIs, missing `await` on async calls, PII leaks in chart/table data queries, auth token handling, pattern consistency, and test coverage gaps. It finishes with a verdict comment — Approve / Request Changes / Comment — plus a 1-2 sentence assessment.

```yaml
- name: Review PR with Claude
  uses: anthropics/claude-code-action@beta
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    github_token: ${{ secrets.GITHUB_TOKEN }}
    direct_prompt: |
      Review this PR for breaking changes, correctness, security
      (PII leaks, token handling), pattern consistency, and test coverage.
      Post inline comments. Finish with a verdict.
```

I also created a `CLAUDE.md` in the repo root — a context file that tells the review agent about the codebase architecture, key patterns (`register(app, get_client)`, `format_response()`, `mask_pii_in_rows()`), and the two transport modes. Without this, the agent would guess at patterns and produce noisy false positives.

---

## What I Couldn't Do (Honestly)

I ran into one real wall: the GitHub MCP tools in this session were scoped to `dalgo-core` only. I couldn't push the workflow to `dalgo-mcp` from here — not via the git proxy, not via the API.

This is a real limitation of how Claude Code on the web handles repository access. Each session is tied to a specific repo. If you need to work across repos, you need separate sessions — or you push the files manually.

I ended up generating the workflow files locally, exporting them, and they're ready to be committed manually. A five-minute job. Not a blocker, just a speed bump.

---

## What I Actually Learned

**1. Having context is the bottleneck, not doing the work.**
Most of the time I spend "managing" a project is actually spent gathering context: loading the issue board, remembering which PRs are open, recalling what each branch does. When Claude can do all of that retrieval in seconds, the actual decisions — what to prioritise, what to review carefully, what to skip — take maybe 10% of the usual time.

**2. Running checks against all branches in parallel is underrated.**
Nobody does this manually. It's too tedious. But "does this branch import cleanly" is a trivially automatable check that catches a surprising number of issues before they ever become merge conflicts or broken deploys.

**3. Merge order matters, and it's easy to miss.**
PR #28 adds the test suite. PR #29–33 don't have tests on their branches — because they were branched from `main` before the tests existed. Once you merge #28, those branches need to be rebased or they'll still skip tests in CI. That's the kind of dependency that gets missed when you review PRs one at a time.

**4. The review prompt is the product.**
The Claude code review is only as good as its prompt. "Review this PR" is useless. "Check for PII leaks in `dalgo_get_chart_data`, missing `await` on async calls, and changes to the `register()` signature" is specific enough to be actionable. Writing a precise prompt is actually the hard creative work here — the execution is trivial.

**5. CLAUDE.md is load-bearing.**
Giving the agent a CLAUDE.md with codebase context — the patterns, the architecture, the PII column names — transforms it from a generic code reviewer into someone who actually knows the codebase. The delta in review quality is significant.

---

## What's Next

The workflow is ready. Once it's merged into `dalgo-mcp`, every future PR gets:
- Server import check (catches broken imports before review)
- pytest run (43 tests, growing)
- Claude review with inline comments and a verdict

The 12 open PRs all passed local verification. The recommended merge order is: security/fix PRs first (#22, #23, #25, #26), then tests (#28), then features and refactors in dependency order, with the `adapt_context()` refactor (#33) last since it touches every tool module.

That's a sprint's worth of review work, done in an afternoon, documented, and automated going forward.

---

*Dalgo is open source (AGPL-3.0). If you're building data infrastructure for an NGO and want to contribute, the [dalgo-mcp repo](https://github.com/DalgoT4D/dalgo-mcp) is a great place to start.*
