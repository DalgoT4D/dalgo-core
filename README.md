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
├── prototypes/
│   └── {feature-name}/
│       └── brief.md             # PM's prototype brief (spike)
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

### Spike Track (PM or Anyone)

Quick validation with NGO partners before committing engineering time. PM owns this end-to-end.

| | |
|---|---|
| **Run** | `/product/prototype "feature idea"` or `/product/prototype path/to/notes.md` |
| **Saves to** | `prototypes/{feature-name}/brief.md` |
| **Then** | Optionally builds prototype code with `# PROTOTYPE` markers |
| **Review** | Team review before showing to users |
| **After testing** | Validated → `/product/write-spec` to promote. Didn't work → archive & move on. |

<img width="483" height="88" alt="Screenshot 2026-04-21 at 12 53 17 PM" src="https://github.com/user-attachments/assets/1a3135cf-bf03-4b1b-8a07-4ed7d3024d32" />

```mermaid
---
title: Spike Track
---
flowchart TD
    A["Idea or NGO request"] --> B(["/product/prototype"])
    B --> |"brief.md"| C{"Build?"}
    C --> |Yes| D["Team review"]
    C --> |No| E["Share brief"]
    D --> F["Test with NGO"]
    E --> F
    F --> G{Works?}
    G --> |Yes| H(["/product/write-spec"])
    G --> |No| I["Archive"]

    style A fill:#f3f4f6,stroke:#6b7280,color:#000
    style B fill:#dbeafe,stroke:#3b82f6,color:#000,stroke-width:2px
    style C fill:#fff,stroke:#6b7280,color:#000
    style D fill:#fff,stroke:#6b7280,color:#000
    style E fill:#fff,stroke:#6b7280,color:#000
    style F fill:#fff,stroke:#6b7280,color:#000
    style G fill:#fff,stroke:#6b7280,color:#000
    style H fill:#dbeafe,stroke:#3b82f6,color:#000,stroke-width:2px
    style I fill:#fef3c7,stroke:#f59e0b,color:#000
```

### Engineering Track

Production-quality implementation for confirmed features. Engineering owns this. All artifacts in `workdocs/`.

```mermaid
---
title: Engineering Track
---
flowchart TD
    A["Idea or validated spike"] --> B(["/product/write-spec"])
    B --> |"spec.md"| C["Scope version"]
    C --> |"v1/spec.md"| D(["/engineering/plan-feature"])
    D --> |"plan.md"| E["Review & iterate"]
    E --> F(["/engineering/execute-plan"])
    F --> |"code"| G(["/engineering/ship-checklist"])
    G --> H(["/engineering/review-pr"])
    H --> I["Merge + Deploy"]
    I --> J{Next?}
    J --> |Bug| K(["/engineering/debug-issue"])
    J --> |v2| C

    style A fill:#f3f4f6,stroke:#6b7280,color:#000
    style B fill:#dbeafe,stroke:#3b82f6,color:#000,stroke-width:2px
    style C fill:#fff,stroke:#6b7280,color:#000
    style D fill:#dbeafe,stroke:#3b82f6,color:#000,stroke-width:2px
    style E fill:#fff,stroke:#6b7280,color:#000
    style F fill:#dbeafe,stroke:#3b82f6,color:#000,stroke-width:2px
    style G fill:#dbeafe,stroke:#3b82f6,color:#000,stroke-width:2px
    style H fill:#dbeafe,stroke:#3b82f6,color:#000,stroke-width:2px
    style I fill:#d1fae5,stroke:#10b981,color:#000
    style J fill:#fff,stroke:#6b7280,color:#000
    style K fill:#dbeafe,stroke:#3b82f6,color:#000,stroke-width:2px
```

### When to use which

| | Spike | Engineering |
|---|---|---|
| **Confidence** | "I think this might work" | "We know we need this" |
| **Goal** | Validate with an NGO user | Ship to production |
| **Time** | Hours | Days |
| **Workspace** | `prototypes/` | `workdocs/` |
| **Command** | `/product/prototype` | `/product/write-spec` → `/engineering/*` |

---

## Commands Reference

### Product Commands

#### `/product/prototype`
Quick spike — validate an idea with NGO partners before committing to a full spec.

```
/product/prototype "let users bookmark their favorite dashboard charts"
```
**Output:** `prototypes/{feature-name}/brief.md` (1-page brief with problem, scope, quick plan)
**Optionally:** builds the prototype code with `# PROTOTYPE` markers
**Next step:** Test with NGO → if validated, `/product/write-spec "{feature name}"`

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

Agents are specialized personas that Claude invokes automatically when the context matches. Agents use skills as reference material for their decisions.

| Agent | What It Does | Skills Used |
|-------|-------------|-------------|
| **debugger** | Diagnoses bugs across the full stack — Django backend, Next.js frontend, or cross-cutting. | `backend-architecture`, `frontend-architecture` |
| **senior-product-manager** | Product strategy and feature specs. Prioritization, roadmap, build-vs-buy, spec writing. | None — uses its own evaluation framework |
| **ux-design-expert** | UI/UX design using Dalgo's design system (Shadcn, teal brand, Tailwind). | `design-review` (patterns.md for design system reference) |
| **ngo-data-platform-consultant** | Evaluates features as "Priya" — a non-technical NGO program manager. | None — uses its own NGO persona framework |

---

## Skills

| Skill | What It Does |
|-------|-------------|
| **design-review** | Combined UX expert + NGO user evaluation of UI components or screenshots. |
| **tal-lens** | Tal Raviv's technology philosophy — demystify, build first, anti-hype, clarity over cleverness. |

---

## Common Workflows

### Spike (idea to validation)
```
/product/prototype "feature idea"
# test with NGO partner...
# if validated:
/product/write-spec "feature idea"
```

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
