# Building and Shipping an MCP Server for NGO Data Infrastructure

*How we used Claude Code to manage 250 issues, audit 12 pull requests, ship automated CI — and what it taught us about running MCP servers in production.*

---

A few weeks ago I sat down with a growing list of tasks for [Dalgo MCP](https://github.com/DalgoT4D/dalgo-mcp) — a new MCP server we're building that lets AI assistants talk directly to Dalgo's data platform. There were Linear issues stacking up, a dozen open pull requests waiting for review, no CI pipeline, and a longer-term question I'd been putting off: what does it actually take to run an MCP server in production?

I decided to tackle all of it in one session using Claude Code. This is what happened — and what I learned about the gap between "it works on my machine" and production-ready AI tooling.

---

## What Dalgo MCP Does

[Dalgo](https://github.com/DalgoT4D/DDP_backend) is an open-source data platform built for NGOs. We help small organisations — the kind running on Excel sheets and good intentions — set up automated data pipelines, dashboards, and reporting.

The MCP server is our newest layer: instead of logging into a dashboard to check if a pipeline ran or to query your data warehouse, you ask Claude. The server exposes ~50 tools that let an AI assistant list pipelines, trigger syncs, browse schemas, query charts, create reports, and search documentation — all through the Model Context Protocol.

It's built on [FastMCP](https://github.com/jlowin/fastmcp) in Python, with two transport modes: `stdio` for Claude Desktop and `streamable-http` for the Anthropic MCP connector.

---

## Part 1: Managing the Project with Claude

### Pulling 250 Issues from Linear

The session started with pulling our full issue board. Two hundred and fifty issues came back across engineering, marketing, consulting, and design. At a glance:

- **21 Dalgo MCP issues** — Backlog, ranging from urgent (PII masking gap, JWT token leak) to low (auto-generate README table)
- **Metrics & KPIs sprint** mid-flight with several sign-offs pending
- **Prefect 3.6.24 upgrade** broken into 5 phases, all in progress

The value wasn't the count. It was having the whole board in one read, without clicking through ten views. Thirty seconds of parsing instead of five minutes of navigation.

### Auditing 12 Open PRs

The `dalgo-mcp` repo had 12 open pull requests — all generated in a prior session where Claude had worked through the Linear backlog and created a PR per issue. Each was scoped and documented. None had been verified.

Rather than reading diffs manually, I asked Claude to fetch all 12 branches and run two checks on each:
1. Does `from dalgo_mcp.server import app` import cleanly?
2. Do the tests pass?

```
PR #22 | PASS | Import: PASS | Tests: SKIP
PR #23 | PASS | Import: PASS | Tests: SKIP
PR #24 | PASS | Import: PASS | Tests: SKIP
PR #25 | PASS | Import: PASS | Tests: SKIP
PR #26 | PASS | Import: PASS | Tests: SKIP
PR #27 | PASS | Import: PASS | Tests: SKIP
PR #28 | PASS | Import: PASS | Tests: 43 passed ✓
PR #29 | PASS | Import: PASS | Tests: SKIP
PR #30 | PASS | Import: PASS | Tests: SKIP
PR #31 | PASS | Import: PASS | Tests: SKIP
PR #32 | PASS | Import: PASS | Tests: SKIP
PR #33 | PASS | Import: PASS | Tests: SKIP

Result: 12 / 12 PRs healthy
```

**12 for 12.** All branches imported cleanly. PR #28 ran 43 tests — all passed.

One thing only became visible by looking at all 12 at once: only PR #28 had tests. The other 11 would skip the test step because `tests/` didn't exist on their branches. The fix is obvious — merge #28 first — but it's exactly the kind of dependency that gets missed when you review PRs one at a time.

### Shipping Automated CI

Running checks manually evaporates when the session ends. I wanted something permanent: a GitHub Actions workflow that runs on every new PR.

Claude built `.github/workflows/pr-review.yml` with two jobs:

**Job 1 — verify:** Installs via `uv`, checks the server imports cleanly in stdio mode with dummy env vars (no live backend needed), then runs `pytest` if tests exist.

**Job 2 — claude-review:** Uses `anthropics/claude-code-action@beta` to read the PR diff and post inline review comments with a specific prompt — check for breaking tool API changes, missing `await`, PII leaks, auth token handling, pattern consistency, and test coverage gaps.

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

A `CLAUDE.md` in the repo root gives the review agent codebase context — architecture, key patterns, PII column names. Without it, the agent guesses and produces noisy false positives.

---

## Part 2: What It Actually Takes to Run MCP in Production

This is where the session shifted from project management to architecture. After shipping the CI workflow, I asked: *what's actually missing before this can go to production?*

The answer has five layers.

### Layer 1: Security

The most immediate gaps were data security.

**PII masking is incomplete.** Our warehouse tools already mask sensitive columns (`name`, `email`, `phone`, `aadhaar`). But chart data queries — `dalgo_get_chart_data` — returned rows unmasked. One of the 12 PRs (#22) fixes this. It's the first one to merge.

**Debug mode leaks tokens.** Our `DebugRequestMiddleware` logs full request headers and bodies. In debug mode, `Authorization: Bearer <token>` goes to stdout. `DALGO_DEBUG=false` must be enforced in production, and your log aggregator shouldn't be capturing raw stdout either.

**Credentials in env vars.** In stdio mode, `DALGO_USERNAME` and `DALGO_PASSWORD` live in environment variables. Fine for local dev. For production, these need to come from AWS Secrets Manager or Vault — not a `.env` file on a server.

**Input sanitization.** Tool parameters flow directly into API query strings. Basic length limits and character validation need to be added before exposing the server publicly.

### Layer 2: Reliability

**No retry logic.** The `DalgoClient` has zero retry handling. A transient 500 from the Dalgo API fails immediately. Exponential backoff with 2 retries is the minimum.

**Hardcoded timeout.** `httpx.AsyncClient(timeout=60.0)` — some dbt runs legitimately take longer. This needs to be configurable via `DALGO_REQUEST_TIMEOUT`.

**No graceful shutdown.** Under Kubernetes, a missing `SIGTERM` handler means in-flight requests get killed mid-response. A drain handler is essential before EKS deployment.

**JWT memory leak.** The `_token_clients` dict caches one client per JWT token — and never evicts. Under real load, this is an OOM waiting to happen. PR #23 adds TTL-based eviction using the JWT `exp` claim.

### Layer 3: Observability

Without observability, debugging production issues is blind.

**Structured logging.** `logging.basicConfig()` outputs plain text. Production log aggregators work better with JSON. One formatter change in `server.py` and you get structured logs with timestamps, levels, and tool names in a format that Datadog or CloudWatch can actually query.

**Health endpoint.** PR #31 adds `/health` with uptime, active token clients, and tool count. This is the minimum for a Kubernetes liveness probe.

**Sentry.** The MCP server needs its own DSN and the `httpx` integration so API errors are captured automatically — not just logged to stdout.

**Per-tool call logging.** PR #31 also adds a logging middleware that records tool name, duration, and success/failure on every MCP call. These numbers — which tools are called most, which ones fail most — are what you need when something breaks at 2am.

### Layer 4: The Gateway Layer

This is the part that most MCP implementations skip until it's too late.

Right now, our MCP server is connected directly to the Dalgo API. That works for one org, one AI client, and one engineer. It starts breaking down when:

- Multiple orgs share the same server
- Different teams need different tool access
- You want to track which AI client is generating which API cost
- You need to enforce rate limits per user

The solution is an **MCP gateway** — a control plane that sits between AI clients and MCP servers. Instead of agents connecting directly to tools, all requests pass through a central layer that handles:

- **Tool discovery** — which tools exist, which tools *this client* can see
- **Access control** — org-level and user-level permission policies
- **Rate limiting** — per-client request budgets and quotas
- **Observability** — unified logs across all tool calls, not fragmented per-server
- **Cost tracking** — which org is generating which API load

Think of it the way API gateways work for microservices. You don't expose internal services directly — you route through a gateway that enforces policy. MCP at scale needs the same pattern.

For Dalgo, this means we eventually want per-org tool visibility (org A shouldn't see org B's pipelines in tool descriptions), per-user rate limits, and a unified audit trail across all MCP interactions. Today we have none of that. It's fine for early access. It's not fine for 20 production NGO orgs.

### Layer 5: Deployment Infrastructure

**Dockerfile.** There isn't one. Before EKS, we need a minimal image:

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
RUN uv sync --no-dev
ENV DALGO_TRANSPORT=streamable-http
EXPOSE 8080
CMD ["uv", "run", "dalgo-mcp"]
```

**CORS.** If the server is called from browser-based MCP clients, CORS needs to be configured explicitly — not inherited from FastMCP defaults.

**Integration tests.** The 43 unit tests mock the HTTP client. They won't catch API contract changes between `dalgo-mcp` and the Django backend. We need at least one integration test per tool category running against staging.

---

## The Merge Order That Matters

When you have 12 PRs all touching the same codebase, merge order is architecture. Here's ours:

| Order | PR | Reason |
|-------|-----|--------|
| 1 | #22 — PII masking in chart data | Live security risk |
| 2 | #23 — JWT TTL eviction | Live memory leak |
| 3 | #25 — Typed error hierarchy | Foundation for everything above |
| 4 | #26 — Output truncation | Reliability — pipeline logs fill context windows |
| 5 | #28 — Unit tests | Tests must land before refactors |
| 6 | #31 — Health + logging | Observability before any public exposure |
| 7 | #24, #27, #29, #30 | Features and tooling |
| 8 | #32 — Centralize params | Safe after tests are in |
| 9 | #33 — `adapt_context()` | Most invasive refactor — last |

---

## What I Actually Learned

**Context is the bottleneck, not execution.** Most of the time I spend "managing" a project is gathering context — loading the issue board, remembering what each PR does. When that retrieval takes seconds instead of minutes, the actual decisions take 10% of the usual time.

**Run all your branches at once.** Nobody does this manually. But "does this branch import cleanly" catches a surprising number of issues before they become broken deploys. It takes one script and five minutes.

**The review prompt is the product.** "Review this PR" produces noise. "Check for PII leaks in `dalgo_get_chart_data`, missing `await` on async calls, and changes to the `register()` signature" produces actionable findings. The specificity is the hard work — Claude does the execution.

**CLAUDE.md is load-bearing.** A context file with the codebase's patterns, architecture, and domain-specific column names transforms an AI reviewer from a generic linter into something that actually knows your codebase.

**MCP governance is infrastructure, not an afterthought.** The jump from "it works" to "it's production-ready" in MCP is mostly about access control, observability, and rate limiting — not the tool implementations themselves. Those concerns belong at an infrastructure layer (a gateway), not scattered across tool modules.

---

## What's Next

The CI workflow is ready to merge. The 12 PRs are verified. The production checklist is clear.

The longer-term work — gateway layer, per-org tool visibility, structured audit trails — is what separates an MCP server that works in a demo from one that 20 NGOs can rely on for their data operations.

That's the work worth doing.

---

*Dalgo is open source (AGPL-3.0). The MCP server is at [github.com/DalgoT4D/dalgo-mcp](https://github.com/DalgoT4D/dalgo-mcp). If you're building data infrastructure for social-impact organisations and want to contribute, PRs are open.*
