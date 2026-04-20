# Dalgo Team Skills & Agents System — Implementation Plan

## Context

The Dalgo team (developers, PMs, design) uses Claude Code across multiple repos. Today the tooling covers the middle of the feature lifecycle well (plan → build → review) but has gaps at the beginning (idea → spec handoff), end (ship quality gate, monitoring), and cross-cutting concerns (debugging, design review). The goal is a connected system where outputs from one stage feed into the next, and team members don't need to memorize which agent to invoke.

## Three Types of Tools — When to Use Each

| Type | Location | Purpose | Invocation | Examples |
|------|----------|---------|------------|----------|
| **Agents** | `.claude/agents/*.md` | Persistent personas with memory. Build institutional knowledge across sessions. | Invoked automatically by Claude when context matches the agent description | `codebase-feature-reviewer`, `backend-debugger` |
| **Commands** | `.claude/commands/*.md` | Procedural workflows — "do this sequence of steps." Take `$ARGUMENTS` input, follow steps, produce output. | User invokes with `/command-name <args>` | `/plan-feature`, `/execute-plan`, `/ship-checklist` |
| **Skills** | `.claude/skills/name/SKILL.md` | Thinking frameworks / evaluation lenses — "look at this through these lenses." Can bundle supporting files (checklists, templates, examples) in the skill directory. | User invokes with skill name, or Claude applies contextually | `tal-lens`, `design-review` |

**Rule of thumb:**
- If it needs **memory** and a **persona** → Agent
- If it's a **step-by-step workflow** with inputs/outputs → Command
- If it's a **perspective shift** or **evaluation framework** → Skill

## What Exists Today (Keep As-Is)

| Type | Name | Audience | Status |
|------|------|----------|--------|
| Agent | `codebase-feature-reviewer` | Dev | Keep |
| Agent | `senior-product-strategist` | PM | Keep |
| Agent | `ngo-data-platform-advisor` | PM/Design | Keep |
| Agent | `ux-design-expert` | Design | Keep |
| Command | `/plan-feature` | Dev | Modify (minor) |
| Command | `/execute-plan` | Dev | Modify (minor) |
| Skill | `tal-lens` (Product/ only) | PM | Promote to workspace |
| System | Product/ AGENTS.md + workflows | PM | Keep in Product/ |
| Config | All CLAUDE.md files | All | Keep |

---

## Phase 1: Cleanup Dead Artifacts

Remove duplicates and empty files that cause confusion about which version is canonical.

| Action | File | Reason |
|--------|------|--------|
| Delete | `webapp_v2/.claude/agents/codebase-feature-reviewer.md` | 0-byte empty file, workspace-level agent is canonical |
| Delete | `webapp_v2/.claude/agent-memory/codebase-feature-reviewer/` | Empty dir, workspace-level memory is canonical |
| Delete | `dalgo-ai-gen/.claude/commands/plan-feature.md` | Duplicate of workspace-level version |
| Delete | `dalgo-ai-gen/.claude/commands/execute-plan.md` | Duplicate of workspace-level version |

---

## Phase 2: Promote tal-lens to Workspace Level (as a Skill)

**Create:** `.claude/skills/tal-lens/SKILL.md`

This is a **thinking framework**, not a procedural workflow — so it stays as a skill. Generalize beyond AI-only evaluation. Keep the 6 core principles (demystify, hands-on first, anti-hype, context over prompts, expose failures, open knowledge) and the 4-component decomposition framework (Model/Context/Tools/UX → generalized to Core Tech/Data Architecture/Integration Points/UX). Make it applicable to any feature or technology decision.

**Source:** Copy from `Product/.claude/skills/tal-lens/SKILL.md`, then:
- Replace AI-specific framing with general technology framing
- Keep all 6 principles intact (they apply universally)
- Generalize the decomposition framework labels
- Add a note at top of `Product/.claude/skills/tal-lens/SKILL.md`: "Superseded by workspace-level `tal-lens` skill"

---

## Phase 3: New Agents (3 total)

### 3a. `backend-debugger` agent

- **File:** `.claude/agents/backend-debugger.md`
- **Model:** opus
- **Memory:** project
- **Audience:** Developers
- **Purpose:** Diagnoses backend bugs given a Sentry issue, error message, or behavior description

**System prompt design:**
- Persona: Senior SRE / backend engineer who has debugged hundreds of Django production issues
- Knows the Dalgo layer architecture (API → Core → Schema → Model) from `DDP_backend/.claude/CLAUDE.md`
- Uses Sentry MCP tools (`get_sentry_resource`, `search_issues`, `analyze_issue_with_seer`) when a Sentry URL is provided
- 4-phase methodology:
  1. **Gather** — Read the error, check Sentry, identify affected endpoint/service
  2. **Hypothesize** — Trace the code path through layers, form 2-3 hypotheses
  3. **Isolate** — Narrow to specific function/query/condition, verify with code reading
  4. **Fix** — Propose minimal diff, assess regression risk, recommend test case
- Records past bugs and root cause patterns in agent memory (builds pattern library over time)
- Knows about common Dalgo-specific pitfalls: Redis cache with no TTL, bare `except:` in auth.py, no chart data caching, new warehouse client per request

### 3b. `frontend-debugger` agent

- **File:** `.claude/agents/frontend-debugger.md`
- **Model:** opus
- **Memory:** project
- **Audience:** Developers
- **Purpose:** Diagnoses frontend bugs in webapp_v2

**System prompt design:**
- Persona: Senior frontend engineer specialized in Next.js 15 / React 19 debugging
- Knows the webapp_v2 patterns from `webapp_v2/CLAUDE.md` (SWR, Zustand, cookie-based auth, Radix UI)
- Uses VS Code diagnostics (`mcp__ide__getDiagnostics`) when available
- Same 4-phase methodology as backend-debugger but frontend-specific:
  1. **Gather** — Read the error, check browser console context, identify component tree
  2. **Hypothesize** — Is it SWR stale cache? Auth redirect loop? Component state? Hydration mismatch?
  3. **Isolate** — Trace through component hierarchy, check hooks, verify data flow
  4. **Fix** — Propose minimal diff following webapp_v2 patterns
- Knows common webapp_v2 gotchas: SWR stale cache on navigation, `typeof window` checks, org context header, token refresh delays

### 3c. `spec-writer` agent

- **File:** `.claude/agents/spec-writer.md`
- **Model:** sonnet
- **Memory:** project
- **Audience:** PMs (primary), anyone starting a feature
- **Purpose:** Turns rough feature ideas into structured specs that feed into `/plan-feature`

**System prompt design:**
- Persona: Senior technical PM who bridges business requirements and engineering
- Reads from the dalgo-ai-gen planning directory to understand existing spec patterns
- References the ngo-data-platform-advisor's evaluation rubric (comprehension/confidence/workflow/trust/independence tests) to pressure-test from the user perspective
- Output structure:
  1. **Problem Statement** — What problem are we solving and for whom?
  2. **Target Users** — Which persona(s) benefit? Reference Dalgo's NGO user base
  3. **Success Metrics** — How do we measure this worked?
  4. **User Stories** — As a [role], I want [thing], so that [outcome]. With acceptance criteria.
  5. **Scope** — What's IN for MVP, what's OUT for later
  6. **Data Model Implications** — Which repos/services are likely affected?
  7. **Open Questions** — What needs to be decided before planning?
  8. **Handoff Checklist** — Is this spec ready for `/plan-feature`?
- Saves output to `dalgo-ai-gen/dalgo_mds/specs/{feature-name}_spec.md`
- Records recurring user needs and feature patterns in agent memory

---

## Phase 4: New Commands (4) and New Skills (1)

### 4a. `/write-spec` command

- **File:** `.claude/commands/write-spec.md`
- **Audience:** PM
- **Input:** `$ARGUMENTS` = feature idea description or path to notes file
- **What it does:**
  1. Check if `$ARGUMENTS` is a file path — if so, read it. Otherwise treat as inline description.
  2. Check `dalgo-ai-gen/dalgo_mds/specs/` for existing specs on similar topics (avoid duplicates)
  3. Orchestrate the `spec-writer` agent to produce the spec
  4. Save to `dalgo-ai-gen/dalgo_mds/specs/{feature-name}_spec.md`
  5. Print: "Spec saved. When ready for implementation planning, run: `/plan-feature <spec-path>`"
- **Connects to:** Output feeds into `/plan-feature`

### 4b. `/debug-issue` command

- **File:** `.claude/commands/debug-issue.md`
- **Audience:** Developers
- **Input:** `$ARGUMENTS` = Sentry issue URL, error message, or bug description
- **What it does:**
  1. If input looks like a Sentry URL → fetch issue details via `mcp__plugin_sentry_sentry__get_sentry_resource`
  2. Determine if backend or frontend issue based on:
     - Stack trace language (Python → backend, JavaScript/TypeScript → frontend)
     - URL patterns (api/ endpoints → backend, page routes → frontend)
     - If unclear, check both
  3. Delegate to `backend-debugger` or `frontend-debugger` agent
  4. Output: diagnosis report with root cause, affected files, fix proposal, suggested test
  5. If fix is complex: "This fix is non-trivial. Consider running `/plan-feature` to create a proper implementation plan."
- **Connects to:** Large fixes can loop back into `/plan-feature`

### 4c. `/review-pr` command

- **File:** `.claude/commands/review-pr.md`
- **Audience:** Developers (reviewer role)
- **Input:** `$ARGUMENTS` = GitHub PR URL or PR number
- **What it does:**
  1. Fetch PR details and diff using `gh pr view` and `gh pr diff`
  2. Identify which repos/services are affected by the diff
  3. For backend changes: Check compliance with `DDP_backend/.claude/CLAUDE.md` patterns (layer architecture, exception handling, schema validation, no local imports)
  4. For frontend changes: Check compliance with `webapp_v2/CLAUDE.md` patterns (component structure, SWR hooks, data-testid, TypeScript strictness, page layout)
  5. Check for: missing tests, security concerns (hardcoded secrets, SQL injection, XSS), missing error handling, breaking API changes
  6. Output: structured review with severity levels (blocking / suggestion / nitpick)
- **Does NOT auto-post to GitHub** — outputs the review for the developer to use

### 4d. `/ship-checklist` command

- **File:** `.claude/commands/ship-checklist.md`
- **Audience:** Developers (before merge)
- **Input:** `$ARGUMENTS` = branch name (optional, defaults to current branch)
- **What it does:**
  1. `git diff main...HEAD --stat` to identify changed files
  2. For each affected repo, run the appropriate checks:
     - **DDP_backend:** `uv run pytest` for changed test files, lint check
     - **webapp_v2:** `npm test` for changed components, `npm run lint`, `npm run format:check`
  3. Scan diff for common issues:
     - `any` type usage in TypeScript
     - Missing `data-testid` on new interactive elements
     - Hardcoded secrets or API keys
     - Missing Django migrations for model changes
     - Console.log statements left in code
  4. Output: pass/fail checklist with details on failures
  5. All checks are read-only — does not modify code or auto-fix

### 4e. `design-review` skill (NOT a command)

- **File:** `.claude/skills/design-review/SKILL.md`
- **Type:** Skill (evaluation lens, not a procedural workflow)
- **Audience:** Design, PM, Developers implementing UI
- **Input:** Component file path, screenshot path, or description of UI to review
- **Why a skill:** This is a dual-lens evaluation framework, not a step-by-step procedure. It shifts how Claude evaluates UI — applying two perspectives simultaneously. The skill directory can also hold supporting files:
  - `SKILL.md` — The main evaluation framework
  - `checklist.md` — Reusable accessibility + usability checklist
  - `patterns.md` — Reference of Dalgo's established UI patterns (from ux-design-expert memory)
- **What it does:**
  1. Read the component code or view the screenshot
  2. Apply two evaluation lenses simultaneously:
     - **UX Design Expert lens:** Design patterns, accessibility (WCAG AA), responsiveness, component choices, spacing/typography against webapp_v2 design system
     - **NGO User lens:** Comprehension test, confidence test, daily workflow test, trust test, independence test, jargon alert
  3. Combine into a single report with sections:
     - Design Assessment (from ux-design-expert perspective)
     - User Assessment (from ngo-data-platform-advisor perspective)
     - Combined Recommendations (prioritized, actionable)
- **Why combined:** For Dalgo, you almost always need both perspectives since the platform serves non-technical NGO users

---

## Phase 5: Modify Existing Commands

### 5a. Modify `/plan-feature`

**File:** `.claude/commands/plan-feature.md`

**Changes:**
1. Add a "Pre-check" step before the existing research process:
   ```
   Before starting research, check if a spec exists at:
   dalgo-ai-gen/dalgo_mds/specs/{feature-name}_spec.md
   If found, use it as the primary input alongside the feature file.
   ```
2. Merge the PRP confidence scoring (1-10) from the dalgo-ai-gen version into the quality checklist
3. Add to the output section: "Next: Run `/execute-plan <plan-path>` to implement"

### 5b. Modify `/execute-plan`

**File:** `.claude/commands/execute-plan.md`

**Changes:**
1. Add a step 6 after "Complete":
   ```
   6. **Pre-merge check**
      - Suggest running `/ship-checklist` before committing
      - Print: "Implementation complete. Run `/ship-checklist` to verify before merge."
   ```

---

## Final File Tree

```
.claude/
├── settings.json                              # (existing) Sentry plugin
├── settings.local.json                        # (existing) permissions
│
├── agents/                                    # PERSONAS WITH MEMORY (auto-invoked)
│   ├── codebase-feature-reviewer.md           # (existing) Dev code review
│   ├── senior-product-strategist.md           # (existing) PM strategy
│   ├── ngo-data-platform-advisor.md           # (existing) NGO user perspective
│   ├── ux-design-expert.md                    # (existing) Design expert
│   ├── backend-debugger.md                    # NEW — backend bug diagnosis
│   ├── frontend-debugger.md                   # NEW — frontend bug diagnosis
│   └── spec-writer.md                         # NEW — feature spec writing
│
├── commands/                                  # PROCEDURAL WORKFLOWS (/command-name)
│   ├── plan-feature.md                        # (modified) add spec pre-check
│   ├── execute-plan.md                        # (modified) add ship-checklist suggestion
│   ├── write-spec.md                          # NEW — PM spec writing workflow
│   ├── debug-issue.md                         # NEW — bug triage from Sentry/description
│   ├── review-pr.md                           # NEW — PR review workflow
│   └── ship-checklist.md                      # NEW — pre-merge quality gate
│
├── skills/                                    # EVALUATION LENSES / FRAMEWORKS
│   ├── tal-lens/
│   │   └── SKILL.md                           # NEW — promoted from Product/, generalized
│   └── design-review/
│       ├── SKILL.md                           # NEW — combined UX + user evaluation lens
│       ├── checklist.md                       # NEW — accessibility + usability checklist
│       └── patterns.md                        # NEW — Dalgo UI patterns reference
│
└── agent-memory/                              # PERSISTENT KNOWLEDGE
    ├── codebase-feature-reviewer/MEMORY.md    # (existing, populated)
    ├── senior-product-strategist/MEMORY.md    # (existing, empty)
    ├── ngo-data-platform-advisor/MEMORY.md    # (existing, empty)
    ├── ux-design-expert/MEMORY.md             # (existing, populated)
    ├── backend-debugger/MEMORY.md             # NEW
    ├── frontend-debugger/MEMORY.md            # NEW
    └── spec-writer/MEMORY.md                  # NEW
```

---

## Artifact Flow

```
PM has idea
     │
     ▼
/write-spec  ──────────────────────► dalgo_mds/specs/{name}_spec.md
     │                                        │
     │  (at any point)                        │
     │  /tal-lens to evaluate approach        │
     │  /design-review for UI features        │
     │                                        ▼
     │                               /plan-feature ──► dalgo_mds/planning/{name}_plan.md
     │                                                          │
     │                                                          ▼
     │                                                    /execute-plan
     │                                                     (implements code,
     │                                                      creates {name}_tasks.md)
     │                                                          │
     │                                                          ▼
     │                                                    /ship-checklist
     │                                                     (automated quality gate)
     │                                                          │
     │                                                          ▼
     │                                                    Push + create PR
     │                                                          │
     │                                                          ▼
     │                                                    /review-pr
     │                                                     (structured code review)
     │                                                          │
     │                                                          ▼
     │                                                    Merge + Deploy
     │                                                          │
     │                                                     Bug in prod?
     │                                                          │
     │                                                          ▼
     └─────────────────────────────────────────────────── /debug-issue
                                                           (Sentry → diagnosis → fix)
                                                                │
                                                         small fix → direct PR
                                                         large fix → /plan-feature loop
```

**Cross-cutting (usable at any stage):**
- `tal-lens` skill — evaluate any technology/feature decision
- `design-review` skill — combined UX + user perspective on any UI
- `codebase-feature-reviewer` agent — deep architectural review
- `senior-product-strategist` agent — strategic product questions
- Sentry MCP tools — available directly for ad-hoc monitoring

---

## Implementation Order

### Batch 1: Cleanup (5 min)
- Delete 4 dead artifacts (webapp_v2 empty agent, dalgo-ai-gen duplicate commands)

### Batch 2: Skills (20 min)
- Create `.claude/skills/tal-lens/SKILL.md` (generalized version, promoted from Product/)
- Create `.claude/skills/design-review/SKILL.md` (combined UX + user evaluation lens)
- Create `.claude/skills/design-review/checklist.md` (accessibility + usability checklist)
- Create `.claude/skills/design-review/patterns.md` (Dalgo UI patterns, seeded from ux-design-expert memory)
- Add deprecation note to `Product/.claude/skills/tal-lens/SKILL.md`

### Batch 3: New agents (parallel, ~30 min each)
- Create `backend-debugger.md`
- Create `frontend-debugger.md`
- Create `spec-writer.md`
- Create agent-memory directories with empty MEMORY.md files

### Batch 4: New commands (parallel, ~15-20 min each)
- Create `/write-spec`
- Create `/debug-issue`
- Create `/review-pr`
- Create `/ship-checklist`

### Batch 5: Modifications (10 min)
- Modify `/plan-feature` — add spec pre-check + confidence scoring
- Modify `/execute-plan` — add ship-checklist suggestion

### Batch 6: Verification
- Test `/write-spec` with a sample feature idea
- Test `/debug-issue` with a real Sentry issue URL
- Test `/review-pr` with an existing PR
- Test `/ship-checklist` on current branch
- Test `design-review` skill on an existing component
- Test `tal-lens` skill on a feature decision

---

## What Was Intentionally NOT Included

| Idea | Reason for exclusion |
|------|---------------------|
| `/write-tests` command | Test writing is already part of `/execute-plan`. Separate command fragments the workflow. |
| `qa-tester` agent | Testing is a dev responsibility at current team size. Separate QA persona adds overhead. |
| `/deploy` command | Deployment depends on CI/CD infrastructure that varies and shouldn't be abstracted in Claude. |
| `docs-writer` agent | Docs are generated alongside features in `/execute-plan` or in dalgo_docs directly. Rarely used standalone. |
| `/estimate` command | Effort estimation needs team velocity context Claude can't reliably provide. |
| Centralized agent registry | The `.claude/` directory structure IS the registry. A manifest creates sync overhead. |
| Repo-level agents for DDP_backend/webapp_v2 | Workspace-level agents already read all repos. Repo-level agents fragment memory and require knowing which repo you're in. |
| Sprint planning/retro tools | Too process-specific. The PM's Product/ workflow system already handles daily/weekly planning. |
