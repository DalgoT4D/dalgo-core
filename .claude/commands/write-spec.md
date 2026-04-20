# Write a Feature Spec

## Input: $ARGUMENTS

Turn a feature idea into a structured spec document.

## Process

### Step 1: Parse Input
- If `$ARGUMENTS` looks like a file path (contains `/` or ends in `.md`/`.txt`), read it as input.
- Otherwise, treat `$ARGUMENTS` as an inline feature description.

### Step 2: Check for Existing Specs
Search `dalgo-ai-gen/dalgo_mds/specs/` for existing specs on similar topics.
- If a related spec exists, inform the user and ask whether to update the existing spec or create a new one.
- Avoid creating duplicate specs for the same feature area.

### Step 3: Write the Spec
Use the spec-writer agent approach to produce a structured spec:

1. **Understand the idea** — Parse the input, identify the core problem being solved.
2. **Research context** — Search the codebase for related features, check existing planning docs at `dalgo-ai-gen/dalgo_mds/claude/planning/`.
3. **Pressure-test from user perspective** — Apply comprehension, confidence, workflow, trust, and independence tests for NGO users.
4. **Structure the spec** with these sections:
   - Problem Statement — What problem, for whom?
   - Target Users — Which Dalgo persona(s)?
   - Success Metrics — How to measure success?
   - User Stories — As a [role], I want [thing], so that [outcome]. With acceptance criteria.
   - Scope — What's IN for MVP, what's OUT for later?
   - Data Model Implications — Which repos/services affected?
   - Open Questions — What needs deciding before planning?
   - Handoff Checklist — Is this ready for `/plan-feature`?

### Step 4: Save the Spec
Save to: `dalgo-ai-gen/dalgo_mds/specs/{feature-name}_spec.md`

Use a kebab-case feature name derived from the core feature concept.

### Step 5: Print Next Step
After saving, print:

```
Spec saved to: dalgo-ai-gen/dalgo_mds/specs/{feature-name}_spec.md

When ready for implementation planning, run:
/plan-feature dalgo-ai-gen/dalgo_mds/specs/{feature-name}_spec.md
```

## Guidelines
- Be specific, not generic. Name real user roles, real workflows, real data.
- Scope ruthlessly for MVP. Move nice-to-haves to "Out of Scope" explicitly.
- Think in user workflows, not isolated features.
- Reference existing codebase patterns where relevant.
- If the idea is too vague, ask clarifying questions before writing the spec.
