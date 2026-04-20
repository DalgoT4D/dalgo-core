# dalgo-core

Central repo for AI-assisted development workflows, specs, plans, and Claude Code configuration for the Dalgo platform.

## Repo Structure

```
dalgo-core/
├── .claude/
│   ├── agents/          # Specialized AI agents
│   ├── commands/        # Slash commands (dev workflows)
│   └── skills/          # Reusable evaluation lenses
├── specs/               # Feature specifications
├── plans/               # Implementation plans
```

## Dev Workflows

These are the main workflows for building features on Dalgo, from idea to merge.

### 1. Write a Spec

Turn a rough feature idea into a structured spec with user stories, scope, and success metrics.

```
/write-spec "scheduled report emails for dashboard owners"
```

Or from a file:
```
/write-spec specs/scheduled-reports_spec.md
```

**Output**: `specs/{feature-name}_spec.md`

### 2. Plan the Implementation

Create a detailed implementation plan from a spec — covering architecture, affected services, API design, and testing strategy.

```
/plan-feature specs/scheduled-reports_spec.md
```

**Output**: `plans/{feature-name}_plan.md`

### 3. Execute the Plan

Implement the feature following the plan, with checkpointing and validation.

```
/execute-plan plans/scheduled-reports_plan.md
```

Creates a `{feature_name}_tasks.md` checkpoint file to track progress across sessions.

### 4. Debug an Issue

Diagnose a bug from a Sentry URL, error message, or behavior description. Automatically classifies as backend or frontend and applies the right debugging methodology.

```
/debug-issue https://sentry.io/issues/DALGO-123/
/debug-issue "500 error on /api/v1/organizations/ endpoint"
/debug-issue "dashboard shows stale data after chart update"
```

### 5. Review a PR

Structured code review checking service-specific conventions, security, testing, and breaking changes.

```
/review-pr 142
/review-pr https://github.com/DalgoT4D/DDP_backend/pull/142
```

### 6. Ship Checklist

Pre-merge quality gate — runs lint, tests, migration checks, and scans the diff for common issues. Read-only, does not modify code.

```
/ship-checklist
```

## Agents

Agents are specialized personas that Claude invokes automatically based on context. You can also reference them explicitly.

| Agent | When It's Used |
|-------|---------------|
| **backend-debugger** | Diagnosing Django/Python bugs in DDP_backend. Knows the layer architecture, Celery, Redis pitfalls, Airbyte/Prefect integration. |
| **frontend-debugger** | Diagnosing Next.js/React bugs in webapp_v2. Knows SWR cache patterns, Zustand, cookie-based JWT, hydration issues. |
| **spec-writer** | Writing structured feature specs. Pressure-tests ideas from the NGO user perspective. |
| **senior-product-strategist** | Product strategy grounded in Dalgo's reality — 20+ NGOs, small team, tight budgets, open-source. |
| **ux-design-expert** | UI/UX design decisions using Dalgo's design system (Shadcn, teal brand, Tailwind). Designs for non-technical NGO users. |
| **ngo-data-platform-advisor** | Evaluates features as "Priya" — a non-technical NGO program manager. Flags jargon, complexity, and abandonment risk. |

## Skills

Skills are reusable evaluation lenses that can be applied to any context.

| Skill | What It Does |
|-------|-------------|
| **design-review** | Combined UX + NGO user evaluation of UI components or screenshots. Includes a checklist and pattern library. |
| **tal-lens** | Applies Tal Raviv's technology philosophy — demystify, build first, anti-hype, clarity over cleverness. |

## Typical Development Flows

### New Feature (idea to code)
```
/write-spec "feature idea"     →  specs/{name}_spec.md
/plan-feature specs/{name}_spec.md  →  plans/{name}_plan.md
/execute-plan plans/{name}_plan.md  →  code changes
/ship-checklist                →  pre-merge validation
```

### Bug Fix
```
/debug-issue "error description or Sentry URL"  →  diagnosis + fix proposal
# implement the fix
/ship-checklist                                 →  pre-merge validation
```

### PR Review
```
/review-pr 142  →  structured review with blocking/suggestions/nitpicks
```

### Design Feedback
```
/design-review  →  UX + NGO user evaluation of a component or screenshot
```
