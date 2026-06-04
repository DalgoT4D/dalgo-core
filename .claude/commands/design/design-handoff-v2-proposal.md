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
2. **P1 — constitution + Figma Skill:** extract the constitution; publish patterns as a Skill;
   drop pattern-pasting from the agent prompt.
3. **P1 — `design.md` ownership:** switch Phase 6 to write `design.md`; leave a spec.md pointer.
4. **P2 — modes + async brief:** add `--brainstorm` / `--draft`; move the brief to a file with
   `[NEEDS CLARIFICATION]` tagging.
5. **P2 — agent topology:** add Scout, the evaluator loop, and the consistency spot-check with
   a fixed frame-agent return schema.

---

## Still open

The four questions from the first draft are now resolved in **Decisions** above (file strategy
and constitution location chosen; naming and brainstorm-storage recommended). What remains
before the command rewrite:

1. **Confirm the two recommendations** (naming standard, brainstorm storage) — or override them.
2. **Skill authoring:** publishing `patterns.md` as a Figma Skill is the one step that depends
   on Figma's native Skills mechanism. We should confirm the workspace has it enabled and decide
   whether the Skill is authored in Figma or generated from `patterns.md` in-repo.
3. **Engineering buy-in on the constitution:** `plan-feature` / `execute-plan` pointing at the
   same `.claude/constitution.md` is a cross-team change — worth a nod from engineering before
   we wire it in.
