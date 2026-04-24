# Spike: Quick Prototype

## Input: $ARGUMENTS

Fast-track a feature idea to something testable with NGO partners.

## What the PM runs

```
/product/prototype "let users bookmark dashboard charts"
```

## What it produces

```
prototypes/{feature-name}/
└── brief.md          ← 1-page prototype brief
```

## When to use

- You want to test an idea with a partner NGO before writing a full spec
- The goal is validation in hours, not a production feature
- The feature does NOT touch auth, billing, or data deletion

---

## Process

### 1. Parse the idea

`$ARGUMENTS` is either:
- An inline idea in quotes (e.g. `"show data freshness on dashboard"`)
- A file path to rough notes

From the input, identify:
- **Problem** — one sentence
- **User** — which NGO role (program manager, data coordinator, admin)
- **Validation** — how will we know it works?

### 2. Quick codebase scan

Fast, targeted — not a deep analysis:
- Where does this feature naturally live in the code?
- Existing UI/API to hook into?
- Similar pattern to reuse?

### 3. Write the brief

Save to: `prototypes/{feature-name}/brief.md`

```markdown
# Prototype: {Feature Name}

**Date**: {date}
**Status**: Prototype — not production-ready
**Goal**: Validate {what} with {which NGO/user type}

## Problem
{1-2 sentences. What pain does this solve? How do users handle it today?}

## What We're Building
{3-5 bullet points. Be concrete — "user clicks X, sees Y" not "enable data-driven insights"}

## What We're NOT Building
{2-3 things explicitly out of scope}

## How We'll Know It Works
- [ ] {User can do X without help}
- [ ] {User understands what Y means}
- [ ] {User prefers this over their current Excel workflow}

## Quick Plan
1. **{Step}**: {what to do} → {what works after this}
2. **{Step}**: {what to do} → {what works after this}

### Where It Lives
- **Backend**: {file/module, or "no backend changes"}
- **Frontend**: {file/component, or "no frontend changes"}
- **Pattern to follow**: {existing similar feature}

## Shortcuts We're Taking
- {e.g., "Hardcoded to one org"}
- {e.g., "No error handling for edge case X"}
- {e.g., "No tests — will add when promoting"}
```

### 4. Stop and ask

Print:

```
Brief saved to: prototypes/{feature-name}/brief.md

What next?
1. Build it — I'll implement the quick plan
2. Revise — tell me what to change
3. Done — I'll build it myself
```

Wait for the PM's response.

### 5. Build (only if PM says go)

- Follow the Quick Plan steps in order
- Keep changes minimal
- Skip tests unless asked

When done, print:

```
Prototype built.

Files changed:
- {file}: {what changed}

Try it: {steps to test the feature}

Next:
- Validated? → /product/write-spec "{feature name}"
- Didn't work? → delete prototype code + prototypes/{feature-name}/
```

---

## Guidelines

- **One page max.** If the brief is longer, the scope is too big — split it.
- **Smallest testable thing.** What's the minimum that validates the idea?
- **Plain language.** Write so a PM can share the brief directly with the NGO partner.
- **Document every shortcut.** Makes promotion to full feature smooth.
