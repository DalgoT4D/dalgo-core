# Write a Feature Spec

## Input: $ARGUMENTS

Write a feature spec. `$ARGUMENTS` is one of:
- An inline feature description (e.g. `"scheduled report emails"`)
- A file path to notes/requirements to read as input
- A path to an existing feature folder or spec (e.g. `features/metrics_kpis` or `features/metrics_kpis/spec.md`)

There is **one flow**. The command auto-detects what to do from the input (see Step 1). You do not pick a mode.

## What a spec IS — and is NOT

A spec is a **Product Requirements Document (PRD)**. It captures the **what** and the **why** from a user/product perspective. It does **not** capture the **how**.

**Belongs in a spec:**
- The user problem and who has it
- User flows, user stories, and acceptance criteria
- The UI surface the feature touches
- Scope: what's in, what's out, and why
- Dependencies on other features
- Success metrics (user/business outcomes)

**A spec does NOT have an "Open Questions" section.** Open product questions must be **grilled with the user and resolved** before the spec is saved. The spec is the answer, not the question list. If a question can't be answered yet, either (a) explicitly defer that capability to a later version and add it to "What's deferred," or (b) state the chosen default in the spec and move on. Never leave ambiguity for engineering to resolve.

**Does NOT belong in a spec** (these live in `plan.md`, written by `/engineering/plan-feature`):
- Data models, schemas, tables, columns, field types
- API endpoints, routes, request/response shapes
- Specific libraries, frameworks, services, queues, workers
- Code-level architecture (modules, classes, files)
- Migration steps, infrastructure choices, deployment notes
- "Technical Scope" or "Engineering Implementation" sections naming repos/services
- Any sentence that prescribes *how* the thing will be built

If you catch yourself writing `Alert` model fields, FK relationships, "Celery beat job," or "FastAPI endpoint" — stop. That's plan content. The spec describes user-visible behavior; engineering decides the implementation.

The only acceptable engineering-adjacent content in a spec is the **Dependencies** section, which names *other features* a version depends on (e.g. "Requires: Metric primitive from features/metrics_kpis/v1"). Not technologies.

## Process

### Step 1: Parse input & determine output target

Resolve `$ARGUMENTS` to decide where the spec goes. This is automatic — branch only on whether a source spec already exists:

1. Check whether `$ARGUMENTS` matches an existing `features/` folder or an existing `spec.md`.
2. **If no existing spec is found** → this is a **new feature**. You will write the full-vision spec at `features/{feature-name}/spec.md`. Use snake_case for the feature name; create the directory if needed.
3. **If an existing spec is found** → you are **scoping the next version**. Read the original `features/{feature-name}/spec.md` (and any existing `v1/`, `v2/` … specs) to see what's already been scoped, then write the next sequential version at `features/{feature-name}/v{N}/spec.md`.

Before writing in either case, search `features/` for related work and tell the user if something similar already exists — ask whether to update it or create new.

### Step 2: Write the spec

Use the senior-product-manager agent approach:

1. **Understand the idea** — Parse the input, identify the core problem being solved. If scoping a version, identify the smallest subset that delivers end-to-end value; for v2+, pull from the prior versions' deferred items or remaining items in the original spec.
2. **Research context** — Search the codebase and `features/` for related features and prior versions.
3. **Pressure-test from the user perspective** — Apply comprehension, confidence, workflow, trust, and independence tests for NGO users.
4. **Grill open questions with the user until resolved.** As you draft, list every product question that's unclear (default behavior, edge cases, UX of disputed flows, what's in vs out, ambiguous wording in the input). Ask them in batches via `AskUserQuestion` where useful. Do NOT save the spec until every open question is either answered, explicitly deferred to a later version with rationale, or has an explicitly chosen default written into the spec. The final spec contains no "Open Questions" section.

### Step 3: Structure the spec

Write these sections (product-only — no engineering content). The same structure applies whether this is a new full-vision spec or a scoped version; a scoped version simply narrows each section to what's in this iteration and records what's deferred.

- **Problem Statement** — What problem, for whom?
- **Target Users** — Which Dalgo persona(s)?
- **Success Metrics** — User/business outcomes to measure.
- **User Flows** — The end-to-end paths through the product, written independently of persona. Each flow: entry point → steps → exit, including the key alternate and error paths. Describe the flow itself, not who is walking it.
- **User Stories** — Persona-based, derived from the personas in Target Users. `As a [persona], I want [capability], so that [outcome].` Group stories by persona. Each story carries acceptance criteria written as user-visible behavior (not implementation).
- **UI Surface** — The screens, pages, modals, components, and entry points the feature introduces or changes; where it lives in the product (routes / navigation); and the key states each surface has (empty, loading, error, populated). Describe what's visible, not how it's built.
- **Scope** — What's IN for this iteration, what's OUT for later, and why.
- **Dependencies** — Other features or versions this depends on, and what it enables. Names features, never technologies (e.g. "Requires: Metric primitive from features/metrics_kpis/v1"; "Enables: alert digest in v2").
- **Handoff Checklist** — Is the product surface clear enough for engineering to plan against?

For a scoped version, lead with a short header and a scope block:

```markdown
# {Feature Name} — v{N}

**Scoped from**: ../spec.md
**Version**: v{N}
**Status**: Draft

## Scope for this iteration

### What's included
- [Capability 1 — from original spec's user story X]
- [Capability 2]

### What's deferred to later versions
- [Deferred item] — [reason for deferral]
```

### Step 4: Save

- New feature → `features/{feature-name}/spec.md` (the PM's original full vision).
- Scoped version → `features/{feature-name}/v{N}/spec.md`.

If the original spec already contains engineering content (data models, technical scope sections), do NOT carry it forward — strip it. Engineering content belongs in `plan.md`.

### Step 5: Print next step

For a new spec:
```
Spec saved to: features/{feature-name}/spec.md

Next steps:
1. Review with the team
2. Scope a v1: /product/write-spec features/{feature-name}
3. Then plan: /engineering/plan-feature features/{feature-name}/v1/spec.md
```

For a scoped version:
```
Scoped version saved to: features/{feature-name}/v{N}/spec.md

Next: /engineering/plan-feature features/{feature-name}/v{N}/spec.md
```

## Guidelines
- **A spec describes user-visible behavior, not implementation.** No data models, API endpoints, libraries, services, or code architecture. If it could change based on engineering choices without changing what the user sees, it doesn't belong in the spec.
- Keep User Flows persona-agnostic and User Stories persona-driven — the flows are the paths, the stories are who needs them and why.
- Be specific, not generic. Name real user roles, real workflows, real data, real screens.
- Scope ruthlessly for MVP. Move nice-to-haves to "Out of Scope" / "What's deferred" explicitly, with reasons.
- Think in user workflows, not isolated features.
- Each version should be independently shippable — users get value even if the next version never happens.
- Don't over-scope v1. Ship a thin slice fast rather than a thick slice late.
- If the original spec is small enough for one iteration, v1/spec.md can be a near-copy with tightened acceptance criteria.
