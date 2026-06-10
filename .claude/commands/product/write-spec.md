# Write a Feature Spec

## Input: $ARGUMENTS

Write a new feature spec from an idea, or scope a versioned iteration from an existing spec.

## What a spec IS — and is NOT

A spec is a **Product Requirements Document (PRD)**. It captures the **what** and the **why** from a user/product perspective. It does **not** capture the **how**.

**Belongs in a spec:**
- The user problem and who has it
- User flows / user stories / acceptance criteria
- Scope: what's in, what's out, and why
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

The only acceptable engineering-adjacent content in a spec is a **Dependencies** line that names *other features* a version depends on (e.g. "Requires: Metric primitive from features/metrics_kpis/v1"). Not technologies.

## Process

### Step 1: Parse Input & Determine Mode

**Mode A — New Spec** (default):
- `$ARGUMENTS` is an inline feature description (e.g. `"scheduled report emails"`)
- Or `$ARGUMENTS` is a file path to notes/requirements to read as input
- Creates `features/{feature-name}/spec.md`

**Mode B — Scope a Version**:
- `$ARGUMENTS` points to an existing feature folder (e.g. `features/metrics_kpis`)
- Or `$ARGUMENTS` points to an existing spec (e.g. `features/metrics_kpis/spec.md`)
- Creates `features/{feature-name}/v{N}/spec.md`

To determine mode: check if `$ARGUMENTS` matches an existing `features/` folder or spec. If yes, Mode B. Otherwise, Mode A.

---

## Mode A: New Spec (full vision)

### Check for Existing Work
Search `features/` for an existing folder with a similar feature name.
- If a related spec exists, inform the user and ask whether to update or create new.

### Write the Spec
Use the senior-product-manager agent approach:

1. **Understand the idea** — Parse the input, identify the core problem being solved.
2. **Research context** — Search the codebase for related features, check existing features.
3. **Pressure-test from user perspective** — Apply comprehension, confidence, workflow, trust, and independence tests for NGO users.
4. **Grill open questions with the user until resolved.** As you draft, list every product question that's unclear (default behavior, edge cases, UX of disputed flows, what's in vs out, ambiguous wording in the input). Ask them, in batches via `AskUserQuestion` where useful. Do NOT save the spec until every open question is either answered, explicitly deferred to a later version with rationale, or has an explicitly chosen default written into the spec. The final spec contains no "Open Questions" section.
5. **Structure the spec** with these sections (product-only — no engineering content):
   - Problem Statement — What problem, for whom?
   - Target Users — Which Dalgo persona(s)?
   - Success Metrics — User/business outcomes to measure.
   - User Stories / User Flows — As a [role], I want [thing], so that [outcome]. With acceptance criteria written as user-visible behavior.
   - Scope — What's IN for MVP, what's OUT for later, and why.
   - Handoff Checklist — Is the product surface clear enough for engineering to plan against?

### Save
Save to: `features/{feature-name}/spec.md`

This is the **PM's original spec** — the full vision. Use snake_case feature name. Create the directory if needed.

### Print Next Step
```
Spec saved to: features/{feature-name}/spec.md

Next steps:
1. Review with the team
2. Scope a v1: /product/write-spec features/{feature-name}
3. Then plan: /engineering/plan-feature features/{feature-name}/v1/spec.md
```

---

## Mode B: Scope a Version

### Read the Original Spec
- Read `features/{feature-name}/spec.md` (the PM's full vision)

### Determine Version Number
- Check which versions already exist (`v1/`, `v2/`, etc.)
- If previous versions exist, read their `spec.md` files to understand what's already been scoped
- New version = next sequential number

### Scope the Iteration
From the original spec, identify what to include in this version:

1. **If this is v1**: Pick the smallest subset that delivers end-to-end value. Focus on the core user story. Defer nice-to-haves.
2. **If this is v2+**: Pull from the "Out of Scope" items of previous versions, or from remaining items in the original spec not yet covered.

For each version, consider:
- What's the smallest shippable slice?
- Does it deliver standalone value to users?
- Are there dependencies on previous versions?
- What's the logical ordering?

### Write the Versioned Spec
Create `features/{feature-name}/v{N}/spec.md` with:

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

## User Stories / User Flows (scoped)

### Story 1: [Title]
**As a** [role], **I want** [capability], **so that** [outcome].

**Acceptance Criteria** (written as user-visible behavior, not implementation):
- [ ] [Criterion 1]
- [ ] [Criterion 2]

## Dependencies
- Requires: [other features or versions this depends on — not technologies]
- Enables: [what future versions this unblocks]
```

**No Open Questions section.** Before saving, grill the user on every unclear product decision (channel multi-select rules, default behavior on edge cases, what each picker shows, what's in vs deferred). Resolve each one — either an explicit answer baked into the spec, or an explicit deferral added to "What's deferred to later versions" with rationale.

### Print Next Step
```
Scoped version saved to: features/{feature-name}/v{N}/spec.md

Next: /engineering/plan-feature features/{feature-name}/v{N}/spec.md
```

---

## Guidelines
- **A spec describes user-visible behavior, not implementation.** No data models, API endpoints, libraries, services, or code architecture. If it could change based on engineering choices without changing what the user sees, it doesn't belong in the spec.
- Be specific, not generic. Name real user roles, real workflows, real data.
- Scope ruthlessly for MVP. Move nice-to-haves to "Out of Scope" explicitly.
- Think in user workflows, not isolated features.
- Each version should be independently shippable — users get value even if v2 never happens.
- Don't over-scope v1. Ship a thin slice fast rather than a thick slice late.
- Explicitly list what's deferred and why — makes scoping v2 easier.
- If the original spec is small enough for one iteration, v1/spec.md can be a near-copy with tightened acceptance criteria.
- If the original spec already contains engineering content (data models, technical scope sections), do NOT carry it forward into the versioned spec. Strip it. Engineering content belongs in `plan.md`, not `spec.md`.
