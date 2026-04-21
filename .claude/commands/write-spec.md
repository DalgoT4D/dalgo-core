# Write a Feature Spec

## Input: $ARGUMENTS

Turn a feature idea into a structured spec document.

## Process

### Step 1: Parse Input
- If `$ARGUMENTS` looks like a file path (contains `/` or ends in `.md`/`.txt`), read it as input.
- Otherwise, treat `$ARGUMENTS` as an inline feature description.

### Step 2: Check for Existing Work
Search `workdocs/` for an existing folder with a similar feature name.
- If a related spec exists, inform the user and ask whether to update the existing spec or create a new one.
- Avoid creating duplicate specs for the same feature area.

### Step 3: Write the Spec
Use the senior-product-manager agent approach to produce a structured spec:

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
   - Handoff Checklist — Is this ready for `/plan-feature`?

### Step 4: Save the Spec
Save to: `workdocs/{feature-name}/spec.md`

This is the **PM's original spec** — the full vision. Engineering will later break this into versioned iterations (`v1/spec.md`, `v2/spec.md`) scoped for shippable chunks.

Use a kebab-case or snake_case feature name. Create the directory if it doesn't exist.

### Step 5: Print Next Step
After saving, print:

```
Spec saved to: workdocs/{feature-name}/spec.md

Next steps for engineering:
1. Review the spec and scope a v1 iteration
2. Create workdocs/{feature-name}/v1/spec.md with the scoped-down version
3. Run: /plan-feature workdocs/{feature-name}/v1/spec.md
```

## Guidelines
- Be specific, not generic. Name real user roles, real workflows, real data.
- Scope ruthlessly for MVP. Move nice-to-haves to "Out of Scope" explicitly.
- Think in user workflows, not isolated features.
- Reference existing codebase patterns where relevant.
- If the idea is too vague, ask clarifying questions before writing the spec.
