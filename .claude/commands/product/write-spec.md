# Write a Feature Spec

## Input: $ARGUMENTS

Write a new feature spec from an idea, or scope a versioned iteration from an existing spec.

## Process

### Step 1: Parse Input & Determine Mode

**Mode A — New Spec** (default):
- `$ARGUMENTS` is an inline feature description (e.g. `"scheduled report emails"`)
- Or `$ARGUMENTS` is a file path to notes/requirements to read as input
- Creates `workdocs/{feature-name}/spec.md`

**Mode B — Scope a Version**:
- `$ARGUMENTS` points to an existing feature folder (e.g. `workdocs/metrics_kpis`)
- Or `$ARGUMENTS` points to an existing spec (e.g. `workdocs/metrics_kpis/spec.md`)
- Creates `workdocs/{feature-name}/v{N}/spec.md`

To determine mode: check if `$ARGUMENTS` matches an existing `workdocs/` folder or spec. If yes, Mode B. Otherwise, Mode A.

---

## Mode A: New Spec (full vision)

### Check for Existing Work
Search `workdocs/` for an existing folder with a similar feature name.
- If a related spec exists, inform the user and ask whether to update or create new.

### Write the Spec
Use the senior-product-manager agent approach:

1. **Understand the idea** — Parse the input, identify the core problem being solved.
2. **Research context** — Search the codebase for related features, check existing workdocs.
3. **Pressure-test from user perspective** — Apply comprehension, confidence, workflow, trust, and independence tests for NGO users.
4. **Structure the spec** with these sections:
   - Problem Statement — What problem, for whom?
   - Target Users — Which Dalgo persona(s)?
   - Success Metrics — How to measure success?
   - User Stories — As a [role], I want [thing], so that [outcome]. With acceptance criteria.
   - Scope — What's IN for MVP, what's OUT for later?
   - Technical Implications — Which repos/services affected?
   - Open Questions — What needs deciding before planning?
   - Handoff Checklist — Is this ready for engineering?

### Save
Save to: `workdocs/{feature-name}/spec.md`

This is the **PM's original spec** — the full vision. Use snake_case feature name. Create the directory if needed.

### Print Next Step
```
Spec saved to: workdocs/{feature-name}/spec.md

Next steps:
1. Review with the team
2. Scope a v1: /product/write-spec workdocs/{feature-name}
3. Then plan: /engineering/plan-feature workdocs/{feature-name}/v1/spec.md
```

---

## Mode B: Scope a Version

### Read the Original Spec
- Read `workdocs/{feature-name}/spec.md` (the PM's full vision)

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
Create `workdocs/{feature-name}/v{N}/spec.md` with:

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

## User Stories (scoped)

### Story 1: [Title]
**As a** [role], **I want** [capability], **so that** [outcome].

**Acceptance Criteria:**
- [ ] [Criterion 1]
- [ ] [Criterion 2]

## Technical Scope
- **DDP_backend**: [what changes in this version]
- **webapp_v2**: [what changes in this version]

## Dependencies
- Requires: [any prerequisites or previous version completion]
- Enables: [what future versions this unblocks]
```

### Print Next Step
```
Scoped version saved to: workdocs/{feature-name}/v{N}/spec.md

Next: /engineering/plan-feature workdocs/{feature-name}/v{N}/spec.md
```

---

## Guidelines
- Be specific, not generic. Name real user roles, real workflows, real data.
- Scope ruthlessly for MVP. Move nice-to-haves to "Out of Scope" explicitly.
- Think in user workflows, not isolated features.
- Each version should be independently shippable — users get value even if v2 never happens.
- Don't over-scope v1. Ship a thin slice fast rather than a thick slice late.
- Explicitly list what's deferred and why — makes scoping v2 easier.
- If the original spec is small enough for one iteration, v1/spec.md can be a near-copy with tightened acceptance criteria.
