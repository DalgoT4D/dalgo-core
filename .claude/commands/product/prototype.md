# Quick Prototype

## Input: $ARGUMENTS

Rapidly prototype a feature idea for testing with NGO partners. This skips the full spec/plan pipeline and gets to something testable fast.

**Use this when**: You want to validate an idea with a partner NGO before investing in a full spec. The goal is a working prototype in hours, not a production feature.

**Don't use this when**: The feature touches auth, billing, data deletion, or other sensitive areas. Use the full `/product/write-spec` → `/engineering/plan-feature` pipeline instead.

## Process

### Step 1: Understand the Idea (2 min)

Parse `$ARGUMENTS` — this is either:
- An inline idea (e.g. `"let users bookmark dashboard charts"`)
- A file path to rough notes or a conversation transcript

Identify:
- **The problem** — one sentence, what pain does this solve?
- **The user** — which NGO role cares? (program manager, data coordinator, admin)
- **The test** — how would an NGO user tell us if this works?

### Step 2: Quick Codebase Scan (3 min)

Do a fast, targeted search — not a deep analysis:
- Where in the codebase does this feature naturally live?
- Is there existing UI/API surface to hook into?
- Any similar pattern already implemented that we can reuse?

Keep notes brief. No separate research file needed.

### Step 3: Write the Prototype Brief

Create a single-page brief. This is NOT a spec — it's a napkin sketch with just enough structure to build from.

Save to: `prototypes/{feature-name}/brief.md`

Use this template:

```markdown
# Prototype: {Feature Name}

**Date**: {date}
**Status**: Prototype — not production-ready
**Goal**: Validate {what} with {which NGO/user type}

## Problem (1-2 sentences)
{What pain does this solve? How do users handle it today?}

## What We're Building
{3-5 bullet points describing what the prototype does. Be concrete — "user clicks X, sees Y" not "enable data-driven insights"}

## What We're NOT Building
{2-3 things that are explicitly out of scope for the prototype}

## How We'll Know It Works
{2-3 concrete validation criteria — things you'd ask the NGO user after testing}
- [ ] {User can do X without help}
- [ ] {User understands what Y means}
- [ ] {User says "this is better than what I do in Excel"}

## Quick Plan
{Ordered list of implementation steps. Each step should be small and independently testable.}

1. **{Step}**: {what to do} → {what's working after this step}
2. **{Step}**: {what to do} → {what's working after this step}
3. ...

### Where It Lives
- **Backend**: {file/module path, or "no backend changes"}
- **Frontend**: {file/component path, or "no frontend changes"}
- **Pattern to follow**: {link to similar existing feature in codebase}

## Prototype Shortcuts (tech debt we're accepting)
{List the corners we're deliberately cutting. This makes it explicit and easier to clean up later.}
- {e.g., "Hardcoded to one org for now"}
- {e.g., "No error handling for edge case X"}
- {e.g., "Skipping unit tests — will add when promoting to full feature"}

## Next Steps After Validation
- If it works: promote to full spec with `/product/write-spec "{feature name}"`
- If it doesn't: document what we learned in this file and archive
```

### Step 4: Ask Before Building

After saving the brief, print:

```
Prototype brief saved to: prototypes/{feature-name}/brief.md

Ready to build? Options:
1. Build it now — I'll implement the quick plan above
2. Revise — tell me what to change in the brief
3. Just the brief — I'll stop here, you'll build it manually
```

Wait for the user's response before proceeding to implementation.

### Step 5: Build (if user says go)

If the user says to build:

1. Follow the Quick Plan steps in order
2. After each step, briefly confirm what's done
3. Keep changes minimal — this is a prototype, not production code
4. Mark shortcuts explicitly with `# PROTOTYPE` comments in code so they're easy to find later
5. Don't write tests unless the user asks — prototype velocity matters more

When done, print:

```
Prototype built. Changes:
- {file1}: {what changed}
- {file2}: {what changed}

Test it by: {concrete steps to try the feature}

When you've validated with users:
- Promote to full feature: /product/write-spec "{feature name}"
- Or discard: delete the prototype code and prototypes/{feature-name}/
```

## Guidelines

- **Speed over polish.** A working prototype today beats a perfect spec next week.
- **One page max.** If the brief is longer than one page, the scope is too big — split it.
- **Real words, not jargon.** Write the brief so a PM can share it with the NGO partner.
- **Smallest testable thing.** What's the minimum that validates the idea? Build that.
- **Explicit shortcuts.** Every corner cut should be documented so promotion to full feature is smooth.
- **No gold-plating.** If you're adding error handling "just in case," you're over-building.
