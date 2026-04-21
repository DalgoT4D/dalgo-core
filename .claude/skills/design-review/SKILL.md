---
name: design-review
description: Apply a combined UX design expert and NGO user evaluation lens to any UI component, screenshot, or interface description. Use when reviewing UI for usability, accessibility, and suitability for non-technical NGO users.
---

# Design Review Skill

Evaluate UI through two simultaneous lenses: professional UX design standards and the perspective of a non-technical NGO program manager. For Dalgo, you almost always need both perspectives since the platform serves non-technical NGO users.

## How to Use

Provide one or more of:
- A component file path (e.g., `webapp_v2/components/dashboard/dashboard-list.tsx`)
- A screenshot path
- A description of the UI to review

## Evaluation Process

### Step 1: Understand the Context
- Read the component code or view the screenshot
- Identify what the user is trying to accomplish with this UI
- Note which user persona(s) would interact with it

### Step 2: Apply the UX Design Expert Lens

Evaluate against Dalgo's design standards using `checklist.md` in this skill directory. Compare component usage, spacing, colors, and patterns against `patterns.md`.

### Step 3: Apply the NGO User Lens

Evaluate from the perspective of a non-technical NGO program manager:

**Comprehension Test**
- Can a user understand what this screen does within 5 seconds?
- Is the purpose of every button/action clear without documentation?
- Are there any technical terms that should be replaced with plain language?

**Confidence Test**
- Does the user feel confident about what will happen when they click a button?
- Are consequences of actions explained upfront (e.g., "This will send emails to 3 recipients")?
- Is there an undo or way back for reversible actions?

**Daily Workflow Test**
- Does this support the user's actual daily workflow?
- Is the most common action the easiest to reach?
- How many clicks to accomplish the primary task?

**Trust Test**
- Does the UI communicate reliability?
- Are success/failure states clear and specific?
- Does error messaging help the user recover, or just report failure?

**Independence Test**
- Can the user figure this out without training or documentation?
- Are smart defaults provided?
- Is progressive disclosure used (simple first, advanced options expandable)?

**Jargon Alert**
- Flag any technical terms: "schema", "pipeline", "orchestrate", "transform", "ingest", "sync"
- Suggest user-friendly alternatives where possible

### Step 4: Produce Combined Report

Structure your output as:

#### Design Assessment
Summary of UX design findings with specific file references and line numbers.
Priority: Critical / Important / Nice-to-Have

#### User Assessment
Summary of NGO user perspective findings.
Priority: Blocks Adoption / Confuses Users / Could Be Simpler

#### Combined Recommendations
Prioritized, actionable list combining both perspectives. Lead with items that are both design issues AND user experience issues.

Refer to `patterns.md` in this skill directory for established Dalgo UI patterns to compare against.
