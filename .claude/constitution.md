# Dalgo — Product Constitution

Non-negotiables. Every design and engineering decision must honour these.
Files that restate these rules should reference this file instead.

Referenced by: `.claude/skills/design-review/patterns.md` · `.claude/skills/design-review/checklist.md`
· `.claude/commands/design/design-handoff.md` · `.claude/commands/engineering/plan-feature.md`

---

## Users

Dalgo users are non-technical program managers, data coordinators, and field staff at small NGOs.
Assume:
- No SQL knowledge, no data engineering background
- Slow internet (2G/3G common in the field)
- Old devices (budget Android phones and laptops from 2018–2020)
- Small teams — often one person manages the whole data workflow
- English may not be their first language

## Data Access Rules

- **Never expose SQL** to non-admin users — not in UI copy, not in error messages, not in logs
- **Never expose schema or table names** (e.g. `public.beneficiary_data`) to non-admin users
- **Never expose internal code or stack traces** in user-facing messages
- Admin-only fields must be **visually locked**: lock icon + "Contact your admin to change this"

## Language & Copy

- **Sentence case on all interactive labels** — "Create pipeline" not "CREATE PIPELINE"
- **No internal acronyms** in user-facing copy — not RAG, blast radius, dbt, ELT, ETL
- **No jargon** without a plain-English explanation alongside it
- Error messages must state **what went wrong AND what to do next**
- Success messages must be **specific** ("Report sent to 3 recipients" not "Done")
- Loading states must be **specific** ("Syncing data..." not "Loading...")

## Design Standards

- Performance over visual richness — every added element must earn its place
- Progressive disclosure — hide advanced options until the user needs them
- Smart defaults — minimise required user input
- Every screen must communicate its purpose within 5 seconds
- Every destructive action requires explicit confirmation
- Every empty state must have a message and a primary action CTA
- Multi-tenant — users must only ever see their own organisation's data

## Platform

- Open source (AGPL-3.0) — no proprietary dependencies without team approval
- ~20 partner NGOs, budget-constrained — no features requiring expensive infrastructure
