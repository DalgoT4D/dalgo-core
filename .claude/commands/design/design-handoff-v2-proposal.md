# Design Handoff v2 — Architecture Proposal

**Status:** Proposal under refinement — architecture decisions partly settled (see Decisions); not yet implemented
**Author:** Design tooling research, June 2026
**Supersedes design of:** `.claude/commands/design/design-handoff.md`
**Next gate:** Confirm the two open recommendations, then rewrite the command to v2

---

## Why revisit this

The current `design-handoff.md` is a solid 7-phase pipeline, but it was written before the
mechanisms it needs actually existed, and three rounds of research surfaced both correctness
bugs and structural gaps.

### Correctness bugs (the command would not run today)
- **Wrong Figma file key.** Hardcodes `v8BYFkebTGQNuiRrCXWssa` (an old shared "Canvas" file
  with 4 unrelated sections). The real Metrics design work lives in `lSXpuOg6n0qXXwvMjOfU7G`.
- **Non-existent MCP tool names.** Phase 3 references `mcp__figma__get_metadata`; the real
  tools are `mcp__<server-id>__get_metadata` / `use_figma` / `get_screenshot`.
- **Ghost dependency.** Every per-feature `FIGMA.md` says "read `~/Dalgo/FIGMA.md` first" —
  that file does not exist in the repo.

### Structural gaps (confirmed against industry practice)
- **Designers are treated as approvers, not authors.** Claude reads the spec and asks
  questions; the designer answers. Real design is visual and iterative — sketch, see, react,
  revise. There is no loop and no brainstorm mode.
- **Patterns are pasted into prompts.** `{paste relevant excerpts from patterns.md}` is manual,
  inconsistent, and the source of cross-frame drift.
- **Design decisions land in the wrong file.** Output is a `## Design` section appended to
  `spec.md`; in the Metrics feature, decisions then leaked into `tasks.md` as "v2 overrides."
  There is no single design source of truth.
- **Review runs once, at the end.** Phase 4 produces a list of problems for a human to fix
  manually, rather than looping until the design passes.
- **Phase 2 hard-blocks the session.** The designer must be present in chat; thinking time and
  generation time are coupled.

---

## What the research changed

Full notes are in the session; the load-bearing findings:

1. **Figma shipped native Skills (Mar 24, 2026)** — markdown files that make a design system
   machine-readable, loaded by the canvas agent automatically. This is exactly what
   `patterns.md` / `FIGMA.md` are doing by hand. *We should publish, not paste.*
2. **Spec-driven dev converged on a 3-file split** (Kiro: `requirements.md` / `design.md` /
   `tasks.md`; spec-kit: `spec.md` / `plan.md` / `tasks.md`). `design.md` is a first-class,
   human-reviewed, **gated** phase — not an appendix to the spec.
3. **The "constitution" pattern** (spec-kit) — one always-loaded, immutable-principles file
   that governs every phase. Dalgo's NGO constraints are a constitution scattered across files.
4. **Anthropic's evaluator-optimizer loop** — generate → evaluate against criteria → feed back
   → repeat. We have the criteria (`checklist.md`) but run it once instead of in a loop.
5. **Nobody has solved spec→design.** Even Kiro/spec-kit explicitly punt on UX methodology.
   This command is novel work, not catch-up — worth getting right.

---

## Decisions (resolved June 2026)

| # | Decision | Choice | Consequence |
|---|----------|--------|-------------|
| 1 | Feature → Figma file mapping | **One file per feature** | Reuse comes from the published Skill, not from scouting other features. Scout's job narrows to "design-system baseline + this feature's internal state." Phase 0 creates the file on first run and records its key in `design.md`. |
| 2 | Constitution location | **New `.claude/constitution.md`** | Canonical and top-level. `patterns.md`, `checklist.md`, and `CLAUDE.md` point to it instead of restating rules. Loaded by design **and** engineering workflows. |
| 3 | Frame naming standard *(recommended)* | **`S{n} · {Screen Name}` + `S{n}-{State}` for states** | One convention so Scout and the prototype wiring can resolve frames by name. Ends the Metrics-file mix of `–` / `·` / `-`. |
| 4 | Brainstorm storage *(recommended)* | **Same feature file, separate "Explorations" page** | Rejected variants stay out of the handoff surface but remain recoverable. No throwaway files to track. |

Decisions 3 and 4 are recommendations — flag if you'd rather decide differently; nothing else
depends on them being settled today.

The **one-file-per-feature** choice also retires the ghost `~/Dalgo/FIGMA.md` dependency: the
cross-feature shared reference is now the **constitution + the design-system Skill**, not a
parent file. Each feature keeps a small `FIGMA.md` that extends the Skill with feature-specific
notes (screen list, file key, canvas positions).

---

## Proposed architecture

### Principle 1 — Designer drives; the command serves

Replace the question-and-answer brief with three intent-led modes:

| Mode | Invocation | Output | When |
|------|-----------|--------|------|
| **Brainstorm** | `--brainstorm` | 2–3 rough variants per open screen, side-by-side in an "Explorations" section. No prototype, no spec change. | Direction is open; designer wants options |
| **Draft** | `--draft` | Lo-fi wireframes, one feedback round per frame, in-place revision. | Direction is chosen; iterating on layout |
| **Ship** (default) | _(none)_ | Full-fidelity frames, prototype wired, `design.md` written, ready for engineering. | Design is settled; producing the handoff |

Variants-by-default in brainstorm matches where every serious tool landed (Google Stitch ships
2–3; Figma First Draft previews multiple themes). A single output asked "does this work?" is
behind the curve.

### Principle 2 — Design system as a Figma Skill, not pasted text

- Publish `patterns.md` + the visual half of `checklist.md` as a **Figma Skill** the canvas
  agent loads automatically (native mechanism as of Mar 2026).
- Frame agents stop receiving pasted excerpts. The prompt points at the skill; the agent reads
  what it needs as it works.
- This is also what shrinks the cross-frame consistency problem at the source — agents sharing
  one skill drift far less, so a consistency check becomes a spot-check rather than a full pass.

### Principle 3 — A constitution governs every phase

Create `.claude/constitution.md` holding Dalgo's non-negotiables, today scattered across
`CLAUDE.md` and `patterns.md`:

- Never expose SQL, schema/table names, or code to non-admin users
- Users are non-technical NGO staff on slow internet and old devices
- Sentence case on buttons; no internal acronyms (RAG, blast radius) in UI copy
- Admin-only fields are visually locked

It is **canonical**: `patterns.md`, `checklist.md`, and `CLAUDE.md` reference it rather than
restate the rules, so there is no drift. Both the design agents **and** the review checklist
load it. To keep it useful for engineering too, the design-handoff and the engineering
`plan-feature` / `execute-plan` flows should all point at the same file — one source of truth
for "what Dalgo will never ship."

### Principle 4 — Own `design.md`, don't append to `spec.md`

Adopt the Kiro split. The handoff produces a gated `features/{name}/v1/design.md` — the design
source of truth — containing screens, node IDs, flows, decisions, and known issues. `spec.md`
keeps a one-line pointer to it. Engineering reads `design.md`; nothing leaks into `tasks.md`.

### Principle 5 — Review is an evaluator loop, not a final report

Restructure Phase 4 as evaluator-optimizer: the review agent checks each frame against
`checklist.md` + constitution, and **feeds failures back to the frame agent** until it passes
(bounded retries). Frames arrive already-passing instead of arriving with a to-do list.

### Principle 6 — Async brief; mark ambiguity, don't block

Replace the blocking Phase 2 with the spec-kit pattern:
- Write the brief to `features/{name}/v1/design-brief.md`. The designer edits it on their own
  time, in their own editor.
- Re-running detects a filled-in brief and continues.
- Where direction is genuinely missing, the command **generates anyway and tags the frame /
  decision with `[NEEDS CLARIFICATION]`** rather than halting the whole run.

---

## Design System Integration

The canonical design system lives in `DalgoT4D/dalgo-design-system` (a separate repo), as two
CSS files that are the **single source of truth** for all visual decisions:

- **`tokens.css`** — CSS custom properties for color, typography, spacing, radii, shadow, z-index,
  and transitions. All prefixed `--color-*`, `--font-*`, `--space-*`, `--spacing-*`, `--radius-*`,
  `--shadow-*`, `--z-*`, `--transition-*`.
- **`components.css`** — 24 components, all values referencing `var(--*)` — zero hardcoded values.

### What `patterns.md` gets wrong today

`patterns.md` is the current source of design truth inside the command. It has three specific
contradictions with `tokens.css` and one policy conflict with `components.css`:

| # | patterns.md says | Design system says | Fix |
|---|------------------|--------------------|-----|
| 1 | Uses Shadcn token names (`--primary`, `text-muted-foreground`) | Tokens are `--color-brand-primary`, `--color-text-secondary`, etc. | Replace all token references |
| 2 | "24px page padding" | `--spacing-page-x` (horizontal, 32px); `--spacing-page-y` (vertical, 28px) | Update padding rule to match named tokens |
| 3 | "Lucide icons at 16px (h-4 w-4) everywhere" | Icon sizes are context-specific per component | Replace blanket rule with per-context guidance |
| 4 | "Sentence case on buttons" (constitution rule) | `.btn { text-transform: uppercase }` in `components.css` | **Needs a decision** — is casing set in code (uppercase) or copy (sentence case)? |

Item 4 is a conflict between the UI constitution rule and the CSS implementation. The most likely
intent: `.btn` sets uppercase as a CSS default that the design system overrides per variant;
`patterns.md` / the constitution should govern copy, not override CSS `text-transform`. Resolution
needed before rewriting the Figma Skill prompt.

### Missing tokens (gaps in tokens.css)

RAG status colors — used extensively throughout the app — are **not in `tokens.css`**:

- on-track (green)
- at-risk (amber)
- off-track (red)
- stale (grey)

These are referenced in multiple features and need to be added to the design system repo before
the Figma Skill can be authoritative. Until then, they should be documented in `patterns.md` as
a pending addition.

### Component families (basis for tiered loading)

`components.css` contains 24 components, grouped into two tiers for context management:

**Tier 1 — always load (layout skeleton, ~5 components)**

Every screen shares these; they go into the Figma Skill's always-available section:

| Component | Role |
|-----------|------|
| Reset | CSS baseline |
| Page Shell | Fixed header + scrollable content pattern |
| Header | Top bar, org switcher |
| Sidebar | Left nav rail |
| Nav Items | Active/hover states |

**Tier 2 — load per frame (component families, ~19 components)**

Frame agents request only what their surface needs. Group by screen archetype:

| Family | Components | Typical surfaces |
|--------|-----------|-----------------|
| Data display | Table, Pagination, Action Buttons | List screens, data grids |
| Input | Forms (label, input, select, tags, frequency, toggle, tabs) | Create/edit flows |
| Overlay | Modal, Empty State | Dialogs, zero-state screens |
| Status/card | Badge Pill, Badge/Avatar, Step Indicator, Card | Dashboards, pipeline status |
| Specialist | Chart Type Icons, Header Org | Analytics screens, multi-org flows |

The frame agent prompt declares which family it needs; the orchestrator loads only those component
definitions into the agent's context. This keeps each agent's prompt under ~4k tokens for the
design system portion.

### How patterns.md should change

`patterns.md` should become a **Tailwind/Shadcn mapping document**: it translates design-system
token names into the framework-specific class names used in `webapp_v2`. It should not restate
spacing values or hex codes — those live in `tokens.css`. Structure:

```
# patterns.md (after fix)

Source of truth: DalgoT4D/dalgo-design-system (tokens.css + components.css)
This file maps design-system tokens → Tailwind / Shadcn class names for webapp_v2.

## Token mapping
--color-brand-primary    → bg-teal-600 / text-teal-600
--spacing-page-x         → px-12 (48px) [verify against tokens.css]
--spacing-page-y         → py-7 (28px) [verify against tokens.css]
...

## Constitution reference
Non-negotiables are in .claude/constitution.md — not restated here.
```

### Figma Skill authoring plan

The Figma Skill is a markdown file that Figma's canvas agent loads automatically. Its content
should be generated **from** `tokens.css` + `components.css`, not from `patterns.md`:

1. **Tier 1 section** — universal layout tokens (colors, spacing, radii, shadows)
2. **Tier 2 sections** — one section per component family; each references component CSS rules
   translated into Figma property names (fills, auto-layout padding, corner radius, etc.)
3. **Constitution section** — Dalgo's non-negotiable UX rules, imported from `.claude/constitution.md`

Authoring question (still open): is the Skill file authored manually in Figma, or generated by a
script that reads `tokens.css` → outputs Figma Skill markdown? The script approach is more
maintainable but requires confirming Figma's native Skills format.

---

## Agent topology (Anthropic orchestrator-workers + evaluator)

```
design-handoff (orchestrator)
  │
  ├─ Scout (runs once)            establishes the design-system baseline from the Skill, then
  │                               reads THIS feature's file via get_metadata. Empty file (first
  │                               run) → start at x=0. Re-run → screenshots existing frames for
  │                               internal consistency, returns rightmost free x-position.
  │
  ├─ Frame agents (parallel)      one per surface; load the Figma Skill; consume Scout's
  │   └─ return a FIXED schema:   context; create the frame
  │      {node_id, frame_name, screenshot, decisions[], needs_clarification[]}
  │
  ├─ Evaluator (loop)             checklist + constitution per frame → feeds failures back to
  │                               the owning frame agent until pass or retry budget hit
  │
  └─ Consistency spot-check       screenshots all final frames; flags nav/header/footer drift
                                  (small now that all agents shared one Skill)
```

Two guardrails from Anthropic's guidance:
- **Fixed return schema** across parallel frame agents, so the orchestrator's fan-in never has
  to reconcile formats.
- **"Add agents only when simpler solutions fall short."** Scout and Evaluator earn their place
  (they fix named failure modes). The Consistency spot-check stays deliberately thin.

---

## Proposed phase flow

| Phase | Current | Proposed |
|-------|---------|----------|
| 0 | — | Resolve mode (`brainstorm`/`draft`/`ship`); load constitution; look up this feature's Figma file key in `design.md` — **create the file if missing** (`create_new_file`) and record the key |
| 1 | Read spec, extract surfaces | _unchanged_ |
| 1.5 | Extract user flows | _unchanged (skipped in brainstorm)_ |
| 2 | **Blocking** designer brief | **Async** brief file; mark `[NEEDS CLARIFICATION]`, continue |
| 2.9 | — | **Scout**: read canvas, return shared context |
| 3 | Frame agents (pasted patterns) | Frame agents load **Figma Skill**; fixed return schema; variants in brainstorm |
| 3.5 | Wire prototype | _unchanged (skipped in brainstorm/draft)_ |
| 4 | Review once → report | **Evaluator loop** → frames return passing |
| 3.9 | — | **Consistency** spot-check |
| 5 | Designer sign-off | _unchanged_ |
| 6 | Append `## Design` to spec.md | Write/own **`design.md`**; spec.md gets a pointer |
| 7 | Signal readiness | _unchanged_ |

---

## Migration / sequencing

P0 fixes are independent of the bigger redesign and can ship immediately:

1. **P0 — make it runnable:** remove the hardcoded Figma file key (look up / create per-feature
   instead), fix MCP tool names, and retire the ghost `~/Dalgo/FIGMA.md` dependency (replace
   with constitution + Skill references).
2. **P0 — fix patterns.md:** correct the three token contradictions (token names, page padding,
   icon sizes) so that agents reading it today get accurate information. Reframe it as a
   Tailwind/Shadcn mapping doc — no pixel values, no hex codes, a reference to `tokens.css`
   as source of truth.
3. **P1 — add missing RAG tokens to dalgo-design-system:** open a PR to `tokens.css` adding
   `--color-status-on-track`, `--color-status-at-risk`, `--color-status-off-track`,
   `--color-status-stale`. Until merged, document interim values in `patterns.md`.
4. **P1 — constitution:** extract the constitution from `CLAUDE.md` / `patterns.md`; resolve
   the button-casing conflict before writing it. Point `patterns.md` and `checklist.md` at it.
5. **P1 — Figma Skill:** author the Skill from `tokens.css` (Tier 1 universal tokens) and
   `components.css` (Tier 2 component families). Drop pattern-pasting from agent prompts.
6. **P1 — `design.md` ownership:** switch Phase 6 to write `design.md`; leave a spec.md pointer.
7. **P2 — modes + async brief:** add `--brainstorm` / `--draft`; move the brief to a file with
   `[NEEDS CLARIFICATION]` tagging.
8. **P2 — agent topology:** add Scout, the evaluator loop, and the consistency spot-check with
   a fixed frame-agent return schema.

---

## Still open

The four questions from the first draft are now resolved in **Decisions** above (file strategy
and constitution location chosen; naming and brainstorm-storage recommended). What remains
before the command rewrite:

1. **Confirm the two recommendations** (naming standard, brainstorm storage) — or override them.
2. **Button casing conflict:** `components.css` sets `text-transform: uppercase` on `.btn`;
   the constitution rule says "sentence case on buttons." Needs a decision: does the CSS
   govern (uppercase always), does copy govern (sentence case, CSS overridden per variant),
   or is this a design-system bug to fix upstream?
3. **RAG status tokens:** `on-track` / `at-risk` / `off-track` / `stale` color tokens are
   missing from `tokens.css`. Need to be added to `DalgoT4D/dalgo-design-system` before the
   Figma Skill can be authoritative for status screens.
4. **Skill authoring approach:** should the Figma Skill file be authored manually in Figma, or
   generated by a script that reads `tokens.css` → outputs Skill markdown? Script is more
   maintainable. Also need to confirm the Figma workspace has native Skills enabled.
5. **Engineering buy-in on the constitution:** `plan-feature` / `execute-plan` pointing at the
   same `.claude/constitution.md` is a cross-team change — worth a nod from engineering before
   we wire it in.
