# dalgo-core

Central repo for AI-assisted development workflows, specs, plans, and Claude Code configuration for the Dalgo platform.

## Repo Structure

```
dalgo-core/
├── .claude/
│   ├── agents/          # Specialized AI agents (auto-invoked by context)
│   ├── commands/        # Slash commands (step-by-step workflows)
│   └── skills/          # Evaluation lenses / thinking frameworks
├── workdocs/
│   └── {feature-name}/  # Each feature gets its own folder
│       ├── spec.md      # Feature specification
│       ├── plan.md      # Implementation plan
│       └── tasks.md     # Execution progress checkpoint
├── DDP_backend -> ../DDP_backend   (symlink, gitignored)
└── webapp_v2 -> ../webapp_v2       (symlink, gitignored)
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
/write-spec                              →  workdocs/{name}/spec.md
 │
 ▼
/plan-feature workdocs/{name}/spec.md    →  workdocs/{name}/plan.md
 │
 ▼
/execute-plan workdocs/{name}/plan.md    →  code changes + workdocs/{name}/tasks.md
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
```
**Output:** `workdocs/{feature-name}/spec.md`
**Next step:** `/plan-feature workdocs/{feature-name}/spec.md`

### `/plan-feature`
Create a detailed implementation plan from a spec — architecture, affected services, API design, testing strategy.

```
/plan-feature workdocs/scheduled-reports/spec.md
```
**Output:** `workdocs/{feature-name}/plan.md`
**Next step:** `/execute-plan workdocs/{feature-name}/plan.md`

### `/execute-plan`
Implement a feature following the plan. Creates a checkpoint file to track progress across sessions.

```
/execute-plan workdocs/scheduled-reports/plan.md
```
**Creates:** `workdocs/{feature-name}/tasks.md` for progress tracking
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
| **senior-product-manager** | Product strategy and feature specs, grounded in Dalgo's reality — 20+ NGOs, small team, tight budgets, open-source. Handles prioritization, roadmap, build-vs-buy, and writing structured specs. |
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
/plan-feature workdocs/{name}/spec.md
/execute-plan workdocs/{name}/plan.md
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
