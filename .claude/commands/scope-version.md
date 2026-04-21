# Scope a Version from the Original Spec

## Input: $ARGUMENTS

Break the PM's original spec into a scoped engineering iteration.

## Process

### Step 1: Parse Input
- `$ARGUMENTS` should be a feature folder path (e.g. `workdocs/metrics_kpis`)
- Read the original `spec.md` in that folder

### Step 2: Determine Version Number
- Check which versions already exist (`v1/`, `v2/`, etc.)
- If previous versions exist, read their `spec.md` files to understand what's already been scoped
- New version = next sequential number

### Step 3: Scope the Iteration
From the original spec, identify what to include in this version:

1. **If this is v1**: Pick the smallest subset that delivers end-to-end value. Focus on the core user story. Defer nice-to-haves.
2. **If this is v2+**: Pull from the "Out of Scope" items of previous versions, or from remaining items in the original spec that haven't been covered yet.

For each version, consider:
- What's the smallest shippable slice?
- Does it deliver standalone value to users?
- Are there dependencies on previous versions?
- What's the logical ordering?

### Step 4: Write the Versioned Spec
Create `workdocs/{feature-name}/{version}/spec.md` with:

```markdown
# {Feature Name} — {Version}

**Scoped from**: ../spec.md
**Version**: {v1/v2/v3}
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

### Step 5: Print Next Step
After saving, print:

```
Scoped version saved to: workdocs/{feature-name}/{version}/spec.md

Next: Run /plan-feature workdocs/{feature-name}/{version}/spec.md
```

## Guidelines
- Each version should be independently shippable — users get value even if v2 never happens.
- Don't over-scope v1. It's better to ship a thin slice fast than a thick slice late.
- Explicitly list what's deferred and why — this makes scoping v2 easier later.
- If the original spec is already small enough for one iteration, just create v1/spec.md as a near-copy with acceptance criteria tightened.
