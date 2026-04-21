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
│   └── {feature-name}/
│       ├── spec.md              # PM's original spec (full vision)
│       ├── v1/
│       │   ├── spec.md          # Engineering's scoped iteration
│       │   ├── research.md      # Codebase & external research
│       │   ├── plan.md          # Implementation plan (HLD, LLD, milestones)
│       │   └── tasks.md         # Execution progress checkpoint
│       └── v2/
│           └── ...              # Next iteration
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

### The Full Flow

```
PM has feature idea
 │
 ▼
/write-spec "feature idea"           →  workdocs/{name}/spec.md (full vision)
 │
 ▼
Engineering scopes v1
 │
 ▼
/scope-version workdocs/{name}       →  workdocs/{name}/v1/spec.md (scoped iteration)
 │
 ▼
/plan-feature workdocs/{name}/v1/spec.md
 │                                   →  workdocs/{name}/v1/research.md
 │                                   →  workdocs/{name}/v1/plan.md (HLD, LLD, security, milestones)
 ▼
Engineer reviews plan, iterates      →  "revise the HLD", "change the API design", etc.
 │
 ▼
/execute-plan workdocs/{name}/v1/plan.md
 │                                   →  workdocs/{name}/v1/tasks.md (progress tracking)
 │                                   →  code changes across DDP_backend, webapp_v2
 ▼
/ship-checklist                      →  pre-merge quality gate (read-only)
 │
 ▼
Push + /review-pr                    →  structured code review
 │
 ▼
Merge + Deploy
 │
 Bug in prod?  →  /debug-issue "error or Sentry URL"
 │
 Ready for v2? →  /scope-version workdocs/{name} (next iteration)
```

### PM vs Engineering Handoff

| Step | Who | Tool | Output |
|------|-----|------|--------|
| Write full spec | PM | `/write-spec` | `workdocs/{name}/spec.md` |
| Scope an iteration | Engineering | `/scope-version` | `workdocs/{name}/v1/spec.md` |
| Plan implementation | Engineering | `/plan-feature` | `workdocs/{name}/v1/plan.md` |
| Iterate on plan | Engineering | Conversation | Updates to `plan.md` |
| Execute | Engineering | `/execute-plan` | Code + `tasks.md` |
| Quality gate | Engineering | `/ship-checklist` | Pass/fail report |
| Review | Engineering | `/review-pr` | Structured review |

---

## Commands Reference

### `/write-spec`
PM command. Turn a rough feature idea into a structured spec — the full vision with all user stories and scope.

```
/write-spec "scheduled report emails for dashboard owners"
```
**Output:** `workdocs/{feature-name}/spec.md`
**Next step:** Engineering scopes a v1 with `/scope-version`

### `/scope-version`
Engineering command. Break the PM's full spec into a scoped iteration for implementation.

```
/scope-version workdocs/scheduled-reports
```
**Output:** `workdocs/{feature-name}/v1/spec.md` (or v2, v3, etc.)
**Next step:** `/plan-feature workdocs/{feature-name}/v1/spec.md`

### `/plan-feature`
Engineering command. Generate an implementation plan with HLD, LLD, security review, and milestones.

```
/plan-feature workdocs/scheduled-reports/v1/spec.md
```
**Output:** `workdocs/{feature-name}/v1/plan.md` + `research.md`
**Next step:** Review, iterate, then `/execute-plan workdocs/{feature-name}/v1/plan.md`

The plan is a **draft** — engineers iterate on it: "revise the API design", "add a caching layer", "split milestone 2". Claude updates `plan.md` in place.

### `/execute-plan`
Engineering command. Implement the feature following the plan, with checkpointing.

```
/execute-plan workdocs/scheduled-reports/v1/plan.md
```
**Creates:** `workdocs/{feature-name}/v1/tasks.md` for progress tracking
**Next step:** `/ship-checklist`

### `/debug-issue`
Diagnose a bug from a Sentry URL, error message, or behavior description.

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
Pre-merge quality gate. Runs lint, tests, migration checks, and scans the diff for common issues. Read-only.

```
/ship-checklist
```

---

## Agents

Agents are specialized personas that Claude invokes automatically when the context matches.

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
/scope-version workdocs/{name}
/plan-feature workdocs/{name}/v1/spec.md
# iterate on plan...
/execute-plan workdocs/{name}/v1/plan.md
/ship-checklist
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
```

### Next Iteration of a Feature
```
/scope-version workdocs/{name}
# creates v2/spec.md from remaining items in original spec
/plan-feature workdocs/{name}/v2/spec.md
```

---

## What's Intentionally NOT Included

| Idea | Why Not |
|------|---------|
| `/write-tests` | Test writing is part of `/execute-plan`. Separate command fragments the workflow. |
| `/deploy` | Deployment depends on CI/CD infrastructure that varies per environment. |
| `/estimate` | Effort estimation needs team velocity context Claude can't reliably provide. |
| Repo-level agents | Workspace-level agents already read all repos via symlinks. |
| Research agent | Research is a step within `/plan-feature`, saved as `research.md`. Doesn't need a separate persona. |
