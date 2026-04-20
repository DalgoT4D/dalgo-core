# Dalgo Core — Claude Code Guide

Dalgo is an open-source data platform for NGOs. It replaces manual Excel/Google Sheets workflows with automated data ingestion (Airbyte), transformation (dbt), orchestration (Prefect), and visualization (Superset + custom dashboards).

## Repositories

| Repo | Tech | CLAUDE.md |
|------|------|-----------|
| `DDP_backend/` | Django + Django Ninja | `DDP_backend/.claude/CLAUDE.md` |
| `webapp_v2/` | Next.js 15, React 19, Shadcn UI | `webapp_v2/CLAUDE.md` |
| `prefect-proxy/` | FastAPI | — |
| `dalgo-ai-gen/` | AI/ML services | — |

## Development Workflow

Commands chain together — each step's output feeds into the next:

```
/write-spec "feature idea"     → specs/{name}_spec.md
/plan-feature specs/{name}     → plans/{name}_plan.md
/execute-plan plans/{name}     → implements the code
/ship-checklist                → pre-merge quality gate
/review-pr <PR#>               → structured code review
/debug-issue <Sentry URL>      → diagnose production bugs
```

## Skills (evaluation lenses)

Use these at any point in the workflow:

- **tal-lens** — Evaluate technology decisions. Demystify, reject hype, expose how things actually work.
- **design-review** — Review UI through two lenses simultaneously: UX design standards + NGO user perspective.

## Key Constraints

- Users are non-technical NGO staff (program managers, data coordinators, field staff)
- ~20 partner NGOs, ~₹2L/year budgets, small engineering team
- Users on slow internet and old devices — performance and simplicity matter
- Open source (AGPL-3.0)
