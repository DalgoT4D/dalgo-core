# Dalgo Core — Claude Code Guide

Dalgo is an open-source data platform for NGOs. It replaces manual Excel/Google Sheets
workflows with automated data ingestion (Airbyte), transformation (dbt), orchestration
(Prefect), and visualization (Superset + custom dashboards).

## Repositories

| Repo | Tech | CLAUDE.md |
|------|------|-----------|
| `DDP_backend/` | Django + Django Ninja | `DDP_backend/.claude/CLAUDE.md` |
| `webapp_v2/` | Next.js 15, React 19, Shadcn UI | `webapp_v2/CLAUDE.md` |
| `prefect-proxy/` | FastAPI | — |
| `dalgo-ai-gen/` | AI/ML services | — |

## Knowledge Base

Deep reference lives in `docs/` — always accessible without loading a skill:

| File | Contents |
|------|----------|
| `docs/domain-map.md` | Product entity graph — source of truth for blast radius analysis |
| `docs/DESIGN.md` | Design principles and the "why" behind major decisions |
| `docs/SECURITY.md` | Auth patterns, org-scoping, PII, multi-tenancy rules |
| `docs/RELIABILITY.md` | What must never fail, degradation strategies |
| `docs/FRONTEND.md` | Component patterns, state management, layout conventions |
| `docs/harness-evolution.md` | Iterative plan for improving the engineering harness |
| `docs/quality-tracker.md` | Code quality grades per domain |

---

## Development Workflow

### Fast track — prototype → validate → promote

```
/product/prototype "feature idea"    → prototypes/{name}/brief.md + working build
```

Skip the full pipeline. Get something in front of NGO partners quickly.
PM artifacts live in `prototypes/`, separate from `features/`.

---

### Standard track

#### 1. Spec

```
/product/write-spec "feature idea"        → features/{name}/spec.md
/product/write-spec features/{name}       → features/{name}/v1/spec.md
```

#### 2. Ship — two modes

**Command mode** (synchronous — runs in your session, you see every step):
```
/engineering/ship-feature features/{name}/v1/spec.md
```

**Agent mode** (async — spawns in a fresh isolated context, runs in background):
```
/engineering/ship-feature-bg features/{name}/v1/spec.md
```

Both run the same pipeline. Both write to the same `pipeline.md`.
See `docs/harness-evolution.md → Experiment 0` for the comparison framework.

**Pipeline stages (both modes):**
plan (planner agent) → implement (engineer agent) → validate loop → docs → PR

State tracked in `features/{name}/{version}/pipeline.md` — re-run the same command
to resume after any interruption.

---

### Manual steps (when you want control over individual stages)

```
/engineering/plan-feature  features/{name}/v1/spec.md   → plan.md + research.md
/engineering/execute-plan  features/{name}/v1/plan.md   → implements the code
/engineering/validate-spec features/{name}/v1/spec.md   → validates implementation
/engineering/review-pr     <PR# or URL>                 → structured code review
/engineering/debug-issue   <Sentry URL or description>  → diagnose production bugs
```

---

## Agents

| Agent | What it does | Spawned by | Model |
|-------|-------------|------------|-------|
| `planner` | Produces plan.md + research.md from a spec | ship-feature / ship-feature-bg | Sonnet |
| `engineer` | Implements all plan milestones, tracks in tasks.md | ship-feature / ship-feature-bg | Opus |
| `ship-orchestrator` | Async pipeline orchestrator (agent mode) | ship-feature-bg | Sonnet |
| `debugger` | Diagnoses bugs from Sentry URL, stack trace, or description | direct | Opus |
| `senior-product-manager` | Feature strategy, specs, prioritization | direct | Sonnet |
| `ux-design-expert` | UI/UX decisions, design system | direct | Sonnet |
| `ngo-data-platform-consultant` | Priya lens — NGO user perspective | direct | Sonnet |

---

## Skills (evaluation lenses — available at any stage)

- **design-review** — UX + NGO user lens on any UI component or screen
- **backend-architecture** — patterns and templates for Django/Ninja layer architecture
- **frontend-architecture** — patterns for Next.js components, hooks, and state
- **docs-generation** — generate or update Docusaurus documentation
- **tal-lens** — technology decisions: demystify hype, expose how things actually work

---

## Feature Artifacts

Every feature lives in `features/{name}/{version}/`:

| File | Produced by | Purpose |
|------|-------------|---------|
| `spec.md` | `/product/write-spec` | What to build and why |
| `research.md` | `planner` agent | Codebase and external findings |
| `plan.md` | `planner` agent | Implementation plan with milestones |
| `tasks.md` | `engineer` agent | Milestone task checklist — resume checkpoint |
| `pipeline.md` | `ship-feature` / `ship-feature-bg` | Stage state — the orchestrator's only state |

---

## Autonomous Operation

### Git safety — never do these
- Push to `main` or merge into `main`
- Force push any branch (`--force`, `--force-with-lease`)
- Delete remote branches

### Commit policy
- Commit at the end of every work session
- Scope commits to the work performed — one logical change per commit
- Ensure tests pass before committing

### Decision making
- Proceed autonomously on implementation details when the outcome is clear
- Ask for clarification only when: requirements conflict, multiple significantly different product behaviors are possible, or the change is destructive/irreversible
- Surface blockers — do not ask for permission between steps

---

## Key Constraints

- Users are non-technical NGO staff (program managers, data coordinators, field staff)
- ~20 partner NGOs, ~₹2L/year budgets, small engineering team
- Users on slow internet and old devices — performance and simplicity matter
- Open source (AGPL-3.0)
