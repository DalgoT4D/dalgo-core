# dalgo-core

Central repo for AI-assisted development workflows, specs, plans, and Claude Code configuration for the Dalgo platform.

## Repo Structure

```
dalgo-core/
├── .claude/
│   ├── agents/          # Specialized AI agents (auto-invoked by context)
│   ├── commands/        # Slash commands (step-by-step workflows)
│   └── skills/          # Evaluation lenses / thinking frameworks
├── specs/               # Feature specifications
├── plans/               # Implementation plans
```

## Three Types of Tools

| Type | Location | Purpose | How to Use |
|------|----------|---------|------------|
| **Commands** | `.claude/commands/` | Step-by-step workflows with inputs and outputs | `/command-name <args>` |
| **Agents** | `.claude/agents/` | Specialized personas invoked by context | Claude picks the right agent automatically, or you can reference them |
| **Skills** | `.claude/skills/` | Evaluation lenses — shift how Claude looks at a problem | Invoke by name (e.g. `/design-review`) |

---

## Feature Lifecycle

The full journey from idea to production, with each tool connected to the next:

```
Idea
 │
 ▼
/write-spec                    →  specs/{name}_spec.md
 │
 ▼
/plan-feature specs/{name}_spec.md   →  plans/{name}_plan.md
 │
 ▼
/execute-plan plans/{name}_plan.md   →  code changes + {name}_tasks.md
 │
 ▼
/ship-checklist                →  pre-merge quality gate (read-only)
 │
 ▼
Push + Create PR
 │
 ▼
/review-pr 142                 →  structured code review
 │
 ▼
Merge + Deploy
 │
 Bug in prod?
 │
 ▼
/debug-issue "error or Sentry URL"  →  diagnosis + fix proposal
 │
 small fix → direct PR
 large fix → loop back to /plan-feature
```

**Cross-cutting (usable at any stage):**
- `/design-review` — UX + NGO user evaluation of any UI
- `/tal-lens` — critical thinking framework for any technology decision

---

## Commands Reference

### `/write-spec`
Turn a rough feature idea into a structured spec with problem statement, user stories, scope, and success metrics.

```
/write-spec "scheduled report emails for dashboard owners"
/write-spec specs/scheduled-reports_spec.md
```
**Output:** `specs/{feature-name}_spec.md`
**Next step:** `/plan-feature specs/{feature-name}_spec.md`

### `/plan-feature`
Create a detailed implementation plan from a spec — architecture, affected services, API design, testing strategy.

```
/plan-feature specs/scheduled-reports_spec.md
```
**Output:** `plans/{feature-name}_plan.md`
**Next step:** `/execute-plan plans/{feature-name}_plan.md`

### `/execute-plan`
Implement a feature following the plan. Creates a checkpoint file to track progress across sessions.

```
/execute-plan plans/scheduled-reports_plan.md
```
**Creates:** `{feature_name}_tasks.md` for progress tracking
**Next step:** `/ship-checklist`

### `/debug-issue`
Diagnose a bug from a Sentry URL, error message, or behavior description. Classifies as backend/frontend/cross-cutting automatically.

```
/debug-issue https://sentry.io/issues/DALGO-123/
/debug-issue "500 error on /api/v1/organizations/"
/debug-issue "dashboard shows stale data after chart update"
```

### `/review-pr`
Structured code review — checks service-specific conventions, security, testing, and breaking changes.

```
/review-pr 142
/review-pr https://github.com/DalgoT4D/DDP_backend/pull/142
```
**Does NOT auto-post to GitHub** — outputs the review for you to use.

### `/ship-checklist`
Pre-merge quality gate. Runs lint, tests, migration checks, and scans the diff for common issues. Read-only — does not modify code.

```
/ship-checklist
```

---

## Agents

Agents are specialized personas that Claude invokes automatically when the context matches. You don't need to remember which one to call.

| Agent | What It Does |
|-------|-------------|
| **debugger** | Diagnoses bugs across the full stack — Django backend, Next.js frontend, or cross-cutting. Traces issues across service boundaries. |
| **spec-writer** | Writes structured feature specs. Pressure-tests ideas from the NGO user perspective (comprehension, confidence, workflow, trust, independence). |
| **senior-product-strategist** | Product strategy grounded in Dalgo's reality — 20+ NGOs, small team, tight budgets, open-source. Feature prioritization, roadmap, build-vs-buy. |
| **ux-design-expert** | UI/UX design using Dalgo's design system (Shadcn, teal brand, Tailwind). Designs for non-technical NGO users on slow connections and old devices. |
| **ngo-data-platform-consultant** | Evaluates features as "Priya" — a non-technical NGO program manager. Flags jargon, complexity, and abandonment risk. Rates likelihood of users going back to Excel. |

---

## Skills

Skills are evaluation lenses — they shift how Claude thinks about a problem.

| Skill | What It Does |
|-------|-------------|
| **design-review** | Combined UX expert + NGO user evaluation of UI components or screenshots. Includes an accessibility checklist and Dalgo UI pattern library. |
| **tal-lens** | Tal Raviv's technology philosophy — demystify, build first, anti-hype, clarity over cleverness. For evaluating any technology decision. |

---

## Common Workflows

### New Feature (idea → code → merge)
```
/write-spec "feature idea"
/plan-feature specs/{name}_spec.md
/execute-plan plans/{name}_plan.md
/ship-checklist
# push + create PR
/review-pr <pr-number>
```

### Bug Fix
```
/debug-issue "error description or Sentry URL"
# implement the fix
/ship-checklist
```

### Design Feedback
```
/design-review
# evaluates a component through both UX and NGO user lenses
```

### PR Review
```
/review-pr 142
```

### Evaluate a Technology Decision
```
/tal-lens
# applies critical thinking framework to any tool/approach/architecture choice
```

---

## What's Intentionally NOT Included

| Idea | Why Not |
|------|---------|
| `/write-tests` | Test writing is part of `/execute-plan`. Separate command fragments the workflow. |
| `/deploy` | Deployment depends on CI/CD infrastructure that varies per environment. |
| `/estimate` | Effort estimation needs team velocity context Claude can't reliably provide. |
| Repo-level agents | Workspace-level agents already read all repos. Repo-level agents fragment knowledge. |
