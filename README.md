# dalgo-core

Central repo for AI-assisted development workflows, specs, plans, and Claude Code configuration for the Dalgo platform.

## Repo Structure

```
dalgo-core/
├── .claude/
│   ├── agents/              # Specialized AI agents (auto-invoked by context)
│   ├── commands/
│   │   ├── product/         # PM commands
│   │   └── engineering/     # Engineering commands
│   └── skills/              # Evaluation lenses / thinking frameworks
├── workdocs/
│   └── {feature-name}/
│       ├── spec.md              # PM's original spec (full vision)
│       ├── v1/
│       │   ├── spec.md          # Engineering's scoped iteration
│       │   ├── research.md      # Codebase & external research
│       │   ├── plan.md          # Implementation plan (HLD, LLD, security, milestones)
│       │   └── tasks.md         # Execution progress checkpoint
│       └── v2/
│           └── ...              # Next iteration
├── DDP_backend -> ../DDP_backend   (symlink, gitignored)
└── webapp_v2 -> ../webapp_v2       (symlink, gitignored)
```

## Three Types of Tools

| Type | Location | Purpose | How to Use |
|------|----------|---------|------------|
| **Commands** | `.claude/commands/{product,engineering}/` | Step-by-step workflows with inputs and outputs | `/product/command` or `/engineering/command` |
| **Agents** | `.claude/agents/` | Specialized personas invoked by context | Claude picks the right agent automatically |
| **Skills** | `.claude/skills/` | Evaluation lenses — shift how Claude looks at a problem | Invoke by name (e.g. `/design-review`) |

---

## Feature Lifecycle

### The Full Flow

```
PM has feature idea
 │
 ▼
/product/write-spec "feature idea"
 │                                   →  workdocs/{name}/spec.md (full vision)
 ▼
/product/write-spec workdocs/{name}
 │                                   →  workdocs/{name}/v1/spec.md (scoped iteration)
 ▼
/engineering/plan-feature workdocs/{name}/v1/spec.md
 │                                   →  workdocs/{name}/v1/research.md
 │                                   →  workdocs/{name}/v1/plan.md (HLD, LLD, security, milestones)
 ▼
Engineer reviews plan, iterates      →  "revise the HLD", "change the API design", etc.
 │
 ▼
/engineering/execute-plan workdocs/{name}/v1/plan.md
 │                                   →  workdocs/{name}/v1/tasks.md (progress tracking)
 │                                   →  code changes across DDP_backend, webapp_v2
 ▼
/engineering/ship-checklist          →  pre-merge quality gate (read-only)
 │
 ▼
Push + /engineering/review-pr        →  structured code review
 │
 ▼
Merge + Deploy
 │
 Bug in prod?  →  /engineering/debug-issue "error or Sentry URL"
 │
 Ready for v2? →  /product/write-spec workdocs/{name} (next iteration)
```

### PM vs Engineering Handoff

| Step | Who | Command | Output |
|------|-----|---------|--------|
| Write full spec | PM | `/product/write-spec "idea"` | `workdocs/{name}/spec.md` |
| Scope an iteration | PM or Eng | `/product/write-spec workdocs/{name}` | `workdocs/{name}/v1/spec.md` |
| Plan implementation | Engineering | `/engineering/plan-feature` | `workdocs/{name}/v1/plan.md` |
| Iterate on plan | Engineering | Conversation | Updates to `plan.md` |
| Execute | Engineering | `/engineering/execute-plan` | Code + `tasks.md` |
| Quality gate | Engineering | `/engineering/ship-checklist` | Pass/fail report |
| Review | Engineering | `/engineering/review-pr` | Structured review |

---

## Commands Reference

### Product Commands

#### `/product/write-spec`
Two modes in one command:

**Mode A — New spec** (from an idea):
```
/product/write-spec "scheduled report emails for dashboard owners"
```
**Output:** `workdocs/{feature-name}/spec.md` (full vision)

**Mode B — Scope a version** (from an existing spec):
```
/product/write-spec workdocs/scheduled-reports
```
**Output:** `workdocs/{feature-name}/v1/spec.md` (or v2, v3, etc.)
**Next step:** `/engineering/plan-feature workdocs/{feature-name}/v1/spec.md`

### Engineering Commands

#### `/engineering/plan-feature`
Generate an implementation plan with HLD, LLD, security review, and milestones.

```
/engineering/plan-feature workdocs/scheduled-reports/v1/spec.md
```
**Output:** `workdocs/{feature-name}/v1/plan.md` + `research.md`

The plan is a **draft** — engineers iterate on it through conversation. Claude updates `plan.md` in place.

#### `/engineering/execute-plan`
Implement the feature following the plan, with checkpointing.

```
/engineering/execute-plan workdocs/scheduled-reports/v1/plan.md
```
**Creates:** `workdocs/{feature-name}/v1/tasks.md` for progress tracking
**Next step:** `/engineering/ship-checklist`

#### `/engineering/debug-issue`
Diagnose a bug from a Sentry URL, error message, or behavior description.

```
/engineering/debug-issue https://sentry.io/issues/DALGO-123/
/engineering/debug-issue "500 error on /api/v1/organizations/"
```

#### `/engineering/review-pr`
Structured code review — checks service-specific conventions, security, testing, breaking changes.

```
/engineering/review-pr 142
/engineering/review-pr https://github.com/DalgoT4D/DDP_backend/pull/142
```
Does NOT auto-post to GitHub — outputs the review for you to use.

#### `/engineering/ship-checklist`
Pre-merge quality gate. Runs lint, tests, migration checks, scans diff for common issues. Read-only.

```
/engineering/ship-checklist
```

---

## Agents

Agents are specialized personas that Claude invokes automatically when the context matches.

| Agent | What It Does |
|-------|-------------|
| **debugger** | Diagnoses bugs across the full stack — Django backend, Next.js frontend, or cross-cutting. |
| **senior-product-manager** | Product strategy and feature specs. Prioritization, roadmap, build-vs-buy, spec writing. |
| **ux-design-expert** | UI/UX design using Dalgo's design system (Shadcn, teal brand, Tailwind). |
| **ngo-data-platform-consultant** | Evaluates features as "Priya" — a non-technical NGO program manager. |

---

## Skills

| Skill | What It Does |
|-------|-------------|
| **design-review** | Combined UX expert + NGO user evaluation of UI components or screenshots. |
| **tal-lens** | Tal Raviv's technology philosophy — demystify, build first, anti-hype, clarity over cleverness. |

---

## Common Workflows

### New Feature (idea to merge)
```
/product/write-spec "feature idea"
/product/write-spec workdocs/{name}
/engineering/plan-feature workdocs/{name}/v1/spec.md
# iterate on plan...
/engineering/execute-plan workdocs/{name}/v1/plan.md
/engineering/ship-checklist
/engineering/review-pr <pr-number>
```

### Bug Fix
```
/engineering/debug-issue "error description or Sentry URL"
# implement the fix
/engineering/ship-checklist
```

### Design Feedback
```
/design-review
```

### Next Iteration
```
/product/write-spec workdocs/{name}
# creates v2/spec.md from remaining items in original spec
/engineering/plan-feature workdocs/{name}/v2/spec.md
```

---

## What's Intentionally NOT Included

| Idea | Why Not |
|------|---------|
| `/write-tests` | Test writing is part of `/engineering/execute-plan`. |
| `/deploy` | Deployment depends on CI/CD that varies per environment. |
| `/estimate` | Effort estimation needs team velocity context Claude can't provide. |
| Repo-level agents | Workspace-level agents read all repos via symlinks. |
| Research agent | Research is a step within `/engineering/plan-feature`, saved as `research.md`. |
