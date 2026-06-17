---
name: prd-generator
description: 'Transform messy ideas into structured PRDs that get stakeholder alignment before engineering starts building. Use when: write prd, product requirements, requirements document, feature spec.'
effort: high
---

# PRD Generator

Transform messy ideas into structured PRDs that get stakeholder alignment before engineering starts building.

## Output

Save to `work/specs/outputs/YYYY-MM-DD-HHmm/prd-[feature].md` (use the current UTC timestamp; create a fresh run folder per invocation).

**Critical:** ALWAYS save via the `Write` tool. Never use bash heredoc (`cat > file <<EOF`), `echo >`, or any shell-based file write. The customer plugin's PostToolUse sync hook only fires on `Write|Edit|MultiEdit` — bash file-writes silently skip artifact sync, so the PRD never reaches mySecond.

**Every artifact MUST start with this literal YAML frontmatter block. Copy verbatim — do not paraphrase. Replace bracketed placeholders only; do NOT add prose before the opening `---`.**

```yaml
---
id: [generate via the `ulid` npm package — NOT crypto.randomUUID()]
type: prd
title: "[human-readable artifact title]"
created_at: [ISO-8601 UTC, e.g. 2026-04-27T20:30:00Z, from `new Date().toISOString()`]
skill: prd-generator
---
```

Optional fields you MAY emit when known: `product`, `work_area: specs`, `created_by`, `derived_from` (paths consumed), `related`, `supersedes`, `tags`. See `.claude/state/frontmatter-schema.md` for the full schema.

## When to Use This Skill
- Starting a new feature from scratch
- Formalizing something you've been discussing verbally
- Getting alignment before engineering starts work

## What You'll Need
- Clear description of the problem you're trying to solve
- Evidence that this problem is real (research, data, feedback)
- Initial thoughts on approach (optional)

## Process

### Step 1: Check Your Context
First, read the user's context files to understand what you already know (`context/product.md`, `personas.md`, etc.). If they just downloaded Second, these might be empty — that's fine, I'll ask for what I need.

What to look for:
- `context/product.md` — Is this feature already on the roadmap? What's the current state?
- `context/personas.md` — Who experiences this problem? What do we know about their pain?
- `context/company.md` — Does this align with strategic priorities?
- `context/competitors.md` — Do competitors have this? Is it table stakes?

**Tell the user what you found.** For example:
> "I found 'Workload Balancer' in your product roadmap — it's marked as Planned for Q2. Your PM persona (Jordan) mentions finding out about overloaded team members only when deadlines slip. Let me use this context for the PRD."

This helps users understand that Second is reading their files and getting smarter over time.

### Step 2: Problem Clarification
With context in hand, ask only what's missing. Don't re-ask things you already know.

**Critical inputs (ask if missing):**
1. What problem are you trying to solve?
2. Who experiences this problem?

**Grounding rule:** The Evidence section must use verbatim quotes or specific data from provided sources. Extract exact customer language, support ticket counts, or usage metrics BEFORE writing the problem statement. Never invent quotes or fabricate data — use "⚠️ Assumed" markers instead.

**JTBD verbatim rule:** When the Personas section references a persona's Job To Be Done and `personas.md` contains a direct JTBD statement for that persona, quote it verbatim. Paraphrase only when citing multiple passages or when no direct statement exists. Paraphrased JTBDs read vaguer than the real thing the user wrote — always prefer the real words.

**Nice-to-have (generate with assumptions if missing):**
3. How do you know it's a real problem? (evidence)
4. Why is it important to solve now?

**If context is thin, prompt for uploads:**
When you don't have enough context to write a solid PRD, offer to help the user add more:
> "I don't have much context about your users. Do you have any of these I could look at?
> - User research or interview notes
> - Support tickets or feedback
> - Analytics or usage data
>
> You can drop files in your `context/` folder or paste them here."

This teaches users how to make Second smarter over time.

If you have enough from context files, say so:
> "Based on your personas and product docs, I have enough to draft this PRD. I'll flag any assumptions."

### Step 3: Success Criteria
Define what success looks like with BOTH lagging and leading indicators:

**Lagging Indicators** (post-launch outcomes):
- What behavior or metric should change?
- How will you measure if this worked?
- What's the target and timeframe?

**Leading Indicators** (pre-launch signals):
- What early signals predict success before launch?
- Examples: Internal dogfooding usage → predicts adoption, Beta support tickets → predicts quality, Time-to-value in onboarding → predicts retention

**Important:** If you don't have actual metrics, don't make them up. Instead:
- Mark them as `[PLACEHOLDER — need actual baseline]`
- Or ask: "What metric would tell you this worked? Do you have a current baseline?"

### Step 4: Dependencies Check
Before diving into solution, identify what this feature depends on:
- **Feature dependencies** — Does this require other features/systems to exist first?
- **Team dependencies** — Do we need work from other teams (design, eng, legal)?
- **External dependencies** — Third-party APIs, vendor integrations, compliance?

Flag the **critical path** — which dependency would block launch if delayed?

### Step 5: Solution Exploration
Once the problem is clear:
- What's your proposed approach?
- Include 2-3 concrete user stories to illustrate the solution
- What's explicitly OUT of scope?
- What are the key risks or assumptions?

### Step 6: Risk Assessment (Value/Usability/Feasibility/Viability)
Evaluate risks across four dimensions (check ✅ when validated, leave ⬜ if still uncertain):

| Risk Type | Question | Status |
|-----------|----------|--------|
| **Value** | Will users want this? | ⬜ |
| **Usability** | Can users figure it out? | ⬜ |
| **Feasibility** | Can we build it? | ⬜ |
| **Viability** | Does it work for the business? | ⬜ |

### Step 7: Generate PRD
Output follows this structure:
1. Context Summary (what you pulled from their files)
2. Problem Statement
3. Evidence
4. Success Criteria (Lagging + Leading Indicators)
5. Proposed Solution (with example user stories)
6. Non-Goals
7. Dependencies (Feature, Team, External + Critical Path)
8. Risks & Mitigations
9. Open Questions (with validation experiments)
10. Sign-off Checklist

## Output Template

```markdown
# PRD: [Feature Name]

**Status:** Draft | Problem Review | Solution Review | Approved
**Owner:** [PM Name]
**Last Updated:** [Date]
**Target Release:** [Date/Quarter]
**Availability:** [All users | Business tier | Pro tier | Enterprise only]
**Rationale:** [Why this tier?]

## Context
*What I found in your files:*
- **Roadmap:** [Feature status from product.md, or "Not currently on roadmap"]
- **Persona pain:** [Relevant quote or insight from personas.md]
- **Strategic fit:** [How this aligns with priorities from company.md]
- **Competitive:** [Do competitors have this? From competitors.md]

## Problem
[What problem? Who has it? In what situation?]

## Evidence
[User research, support tickets, data, quotes]

*Mark assumptions clearly:*
- ✅ **Validated:** [Evidence you have]
- ⚠️ **Assumed:** [Things you're inferring — flag for validation]

## Success Criteria

### Lagging Indicators (post-launch outcomes)
| Metric | Current | Target | Timeframe |
|--------|---------|--------|-----------|
| [Metric 1] | [Value or PLACEHOLDER] | [Value] | [When] |
| [Metric 2] | [Value or PLACEHOLDER] | [Value] | [When] |

### Leading Indicators (pre-launch signals)
| Metric | Current | Target | What This Predicts |
|--------|---------|--------|-------------------|
| [Metric 1] | [Value or PLACEHOLDER] | [Value] | [e.g., predicts adoption] |
| [Metric 2] | [Value or PLACEHOLDER] | [Value] | [e.g., predicts quality] |
| [Metric 3] | [Value or PLACEHOLDER] | [Value] | [e.g., predicts retention] |

💡 **Leading indicators help you course-correct before launch.**

## Proposed Solution

### How It Works
[High-level description of the approach]

### User Stories (Examples)
*Include 2-3 concrete user stories to illustrate the solution and help engineering understand edge cases and scope boundaries.*

**Story 1:**
- **As a** [persona]
- **I want to** [action]
- **So that** [benefit]

**Story 2:**
- **As a** [persona]
- **I want to** [action]
- **So that** [benefit]

**Story 3 (if needed):**
- **As a** [persona]
- **I want to** [action]
- **So that** [benefit]

## Non-Goals
- [What we're explicitly NOT doing]

## Dependencies

### Feature Dependencies
- **[Feature/System]**: [Why we need it] — [Status/Timeline]
- **[Feature/System]**: [Why we need it] — [Status/Timeline]

### Team Dependencies
- **[Team]**: [What we need from them] — [Timeline]

### External Dependencies
- **[Third-party/API]**: [What we need] — [Risk if delayed]

**Critical Path:** [Which dependency blocks launch if delayed?]

💡 **Flag dependencies early to avoid last-minute surprises.**

## Risks
*Risk types: V=Value, U=Usability, F=Feasibility, B=Business Viability. Impact: H=High, M=Medium, L=Low*

| Risk | Type | Impact | Mitigation |
|------|------|--------|------------|
| [Risk] | V/U/F/B | H/M/L | [Plan] |

## Open Questions
*For each unknown, suggest a validation approach to turn assumptions into testable hypotheses.*

| Question | Assumption | How to Validate | Timeline |
|----------|-----------|-----------------|----------|
| [Question 1] | [What we're assuming] | [Experiment to run] | [When we need answer] |
| [Question 2] | [What we're assuming] | [Experiment to run] | [When we need answer] |

**Example:**
| Do agencies want automated balancing or manual control? | Automated preferred | 5 user interviews + prototype test | Before sprint 1 |

## Before Finalizing
Before you ship this PRD, double-check:
- [ ] Does `competitors.md` show competitors have this? (table stakes check)
- [ ] Did you miss any recent user feedback that contradicts this approach?

## Sign-off
| Role | Name | Approved |
|------|------|----------|
| Product | | ⬜ |
| Engineering | | ⬜ |
| Design | | ⬜ |
```

## Framework Reference

This skill uses **Marty Cagan's V/U/F/V Risk Framework** from *Inspired* and *Empowered*:

- **Value Risk:** Will customers buy/use this?
- **Usability Risk:** Can users figure out how to use it?
- **Feasibility Risk:** Can engineering build it with current resources?
- **Viability Risk:** Does it work for sales, legal, finance, etc.?

The goal is to address the biggest risks BEFORE building, not after.

## Tips for Best Results

1. **Keep your context files updated** — The more I know about your product, the better this PRD will be
2. **Be honest about evidence** — "I think" is fine, just label it as assumption
3. **Non-goals are as important as goals** — They prevent scope creep
4. **Update the PRD as you learn** — It's a living document, not a contract

## Related Workflows

Have raw research and a problem statement? `/problem-to-prd` runs the full pipeline — JTBD extraction, framing, PRD, and multi-perspective review. *(available in the full PM OS)*
