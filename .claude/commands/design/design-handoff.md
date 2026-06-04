# Design Handoff

## Input: $ARGUMENTS

Bridge a feature spec into Figma designs, then produce `design.md` so engineering can start.

**Accepts:**
- A spec file path: `features/access-control/v1/spec.md`
- A versioned folder: `features/access-control/v1/`
- A feature folder: `features/access-control/` (selects the highest version with a `spec.md`)
- A feature name: `access-control` (same as feature folder)

**Flags:**
- `--brainstorm` — 2–3 rough layout variants per screen on an "Explorations" page. No prototype, no `design.md`. Use when direction is still open.
- `--draft` — One lo-fi wireframe per screen, one feedback round. No prototype wiring. Use when iterating on layout.
- _(default, no flag)_ — Full-fidelity frames, prototype wired, `design.md` written. Use when design is settled and you're producing the engineering handoff.

---

## Phase 0: Setup

### 1. Parse mode
- Argument contains `--brainstorm` → **Brainstorm mode**
- Argument contains `--draft` → **Draft mode**
- No flag → **Ship mode**

Strip the flag from `$ARGUMENTS` before locating the spec.

### 2. Read the constitution
Read `.claude/constitution.md` — these rules govern every phase and every agent spawned.
Do not proceed until this file is loaded.

### 3. Locate the spec
From the cleaned `$ARGUMENTS`, resolve the spec using these rules in order:

1. **Ends in `.md`** — use it directly as the spec file.
2. **Ends in `/v{N}/` or is a versioned folder** — look for `spec.md` inside it.
3. **Feature folder or feature name** — list all `v{N}/` subdirectories inside
   `features/{name}/`, sort by version number descending, and use the `spec.md`
   from the highest version that contains one. If no versioned folder exists,
   fall back to `features/{name}/spec.md`.

Derive `{feature_name}` and `{version}` (e.g. `v1`, `v2`) from the resolved path.

### 4. Resolve the Figma file key
Look for `features/{feature_name}/{version}/design.md`. If it exists, find the line:
```
file_key: {key}
```
Use that key.

If `design.md` doesn't exist or has no `file_key`, create a new Figma file:
- Use `create_new_file` with the name `"{Feature Name} — {Version}"` (e.g. `"Access Control — v1"`)
- Create `features/{feature_name}/{version}/design.md` with just the file key recorded:

```markdown
# {Feature Name} — Design ({Version})

**Status:** In progress

## Figma

file_key: {key}
```

---

## Phase 1: Read & Extract

### 1. Read the spec
Load the spec file. Read it in full.

### 2. Extract UI surfaces
Parse the spec for every user-facing screen, flow, modal, or component that needs designing:
- Explicit screen names ("User management page", "Invite modal")
- User stories implying a UI ("As an admin, I want to assign roles...")
- State changes requiring visual design (empty, error, success states)
- Shared components (badges, selectors, inline controls)

For each surface extract:
- **Purpose:** what the user accomplishes
- **Persona:** which Dalgo user type (admin, PM, analyst, viewer)
- **Key decisions:** things needing a designer's judgment before building
- **Dependencies:** does this screen reference another surface?

### 3. Load design standards
Read `.claude/skills/design-review/patterns.md` and `.claude/skills/design-review/checklist.md`
into the orchestrator context. These are passed to agents in full — do not paste excerpts.

---

## Phase 1.5: User Flow Extraction (skip in brainstorm mode)

For each surface, map the full user journey. This becomes the basis for prototype connections.

For each surface, produce a flow block:

```
Screen: {Screen Name}

Entry points:
- {How the user arrives — e.g. "clicks 'Invite user' button on User management page"}
- {Alternative entry — e.g. "redirected here after accepting email invite"}

Happy path:
1. {Step 1}
2. {Step 2}
3. {Step 3}

Branch points:
- {Condition} → {Screen or state}
- {Condition} → {Screen or state}

Exit points:
- Success → {target screen or state}
- Cancel → {target screen or state}
- Error → {stays / redirects to X}
```

Group screens into **scenarios** — named end-to-end journeys:
- e.g. "Invite a new team member" → Invite modal → Success state → User management table

Each scenario becomes a named prototype flow in Figma.

---

## Phase 2: Async Brief

### 1. Check for an existing brief
Look for `features/{feature_name}/{version}/design-brief.md`.

**If it exists and has content below any `Your direction:` line:** Read it, extract designer
direction per surface, and continue directly to Phase 2.9.

**If it's missing or blank:** Write the brief file (step 2) and stop.

### 2. Write the brief file
Create `features/{feature_name}/{version}/design-brief.md`:

```markdown
# Design Brief — {Feature Name} {Version}

**Status:** Awaiting designer input
**Generated:** {date}

Fill in your direction below each surface, then re-run:
`/design:design-handoff {spec path}`

Leave a section blank to let me use best judgment for an NGO audience
(I'll tag those decisions `[NEEDS CLARIFICATION]` in the output).

---

{for each surface:}

## Surface: {Screen Name}

**Who uses it:** {persona}
**What it does:** {purpose}

**Decisions needed:**
- {Decision 1}
- {Decision 2}

**Reference design (if any):**

**Your direction:** <!-- fill in here -->

---
```

Print:
```
Brief written to features/{feature_name}/{version}/design-brief.md

Open it in your editor, fill in direction for each surface, then re-run:
/design:design-handoff {spec path}
```

**Stop here.** Do not spawn any Figma agents.

### 3. Parse a completed brief
When re-running and the brief has responses, extract direction per surface.
Where a `Your direction:` field is blank or missing, note that surface as `[NEEDS CLARIFICATION]`
and generate using best judgment for a non-technical NGO audience.

---

## Phase 2.9: Scout

Spawn a Scout agent with this prompt:

```
You are reading a Figma file to establish baseline context for frame agents.

Figma file key: {file_key}

1. Call get_metadata on the file. Collect all existing frames: their names, node IDs, and x positions.
2. If the file has no frames, return next_x = 0.
3. If frames exist, call get_screenshot on each and note which belong to this feature.
   Return the rightmost x position across all frames + 100px gap as next_x.
4. Return this exact JSON:
{
  "file_key": "{file_key}",
  "existing_frames": [{"name": "...", "node_id": "...", "x": 0}],
  "next_x": 0,
  "notes": "any relevant observations about canvas state"
}
```

Wait for Scout to complete before spawning frame agents.

---

## Phase 3: Generate Designs in Figma

### Mode behaviour

| Mode | Page | Fidelity | Variants | Prototype |
|------|------|----------|----------|-----------|
| Brainstorm | "Explorations" | Rough wireframe | 2–3 per surface | No |
| Draft | "Designs" | Lo-fi wireframe | 1 per surface | No |
| Ship | "Designs" | Full-fidelity | 1 per surface | Yes |

### Frame naming
- Ship / Draft: `S{n} · {Screen Name}` (e.g. `S1 · User Management`)
- Brainstorm variants: `S{n}a · {Screen Name}`, `S{n}b · {Screen Name}`, `S{n}c · {Screen Name}`
- States: `S{n}-{State}` (e.g. `S1-Empty`, `S1-Error`)

### Frame agent prompt
Spawn one agent per surface in parallel. Each **must** return this fixed JSON schema — no other format:

```json
{
  "node_id": "string",
  "frame_name": "string",
  "screenshot_url": "string",
  "decisions": ["string"],
  "needs_clarification": ["string"]
}
```

Agent prompt template:

```
You are a UX designer for Dalgo — an open-source data platform for non-technical NGO program
managers. Users are non-technical, on slow internet and old devices. Simplicity matters more
than visual richness.

Feature: {Feature Name}
Screen: {Screen Name}
Persona: {persona}
Purpose: {purpose}
Mode: {brainstorm | draft | ship}

Designer direction:
{direction from design-brief.md, or "[NEEDS CLARIFICATION] — use best judgment for NGO audience"}

User flow for this screen:
{flow block from Phase 1.5}

Design standards — read and apply in full:
{full content of patterns.md}

Constitution — never violate these rules:
{full content of .claude/constitution.md}

Figma file key: {file_key}
Page: {page name — "Explorations" for brainstorm, "Designs" for draft/ship}
Frame name: {frame name per naming convention above}
Frame size: 1440×900px
Position: x={scout.next_x + (surface_index × 1540)}, y=0

{brainstorm only: create 2–3 variants at x offsets of 0, 1540, 3080 from your starting position}

Steps:
1. Load skill://figma/figma-use/SKILL.md before calling use_figma — this is mandatory.
2. Create the page if it does not exist.
3. Create the frame at the specified position with the specified name.
4. After creating, call get_screenshot on the created node.
5. Record any design decisions made (label choices, layout choices, copy decisions).
6. Record anything that needs the designer's input as [NEEDS CLARIFICATION].
7. Return the fixed JSON schema — node_id, frame_name, screenshot_url, decisions[], needs_clarification[].
```

### Collect results
Wait for all agents. Validate every response matches the fixed schema before proceeding.
If an agent returns malformed output, re-prompt it once requesting the correct JSON.

---

## Phase 3.5: Wire Prototype Connections (ship mode only)

### 1. Build the connection map
Using flows and scenarios from Phase 1.5:

```
Scenario: {Scenario Name}
Connections:
- From: {Frame Name} | Trigger: {element} → To: {Frame Name}
- From: {Frame Name} | Trigger: Cancel → To: {Frame Name}
- From: {Frame Name} | Trigger: {error} → To: {Frame Name}
```

### 2. Add connections via use_figma
Load skill://figma/figma-use/SKILL.md first (mandatory before calling use_figma).

For each connection:
- Select the trigger element on the source frame
- Add interaction: `On click → Navigate to → {target frame node ID}`
- Overlays / modals: use `Open overlay` instead of Navigate
- Back / cancel flows: `Navigate to` with the specific target frame node ID

### 3. Set flow start frames
For each scenario, mark the first frame as the starting point in Figma's prototype panel,
labelled with the scenario name (e.g. "Invite a new team member").

### 4. Record wiring results
Note any connections that could not be wired for manual follow-up.

---

## Phase 4: Evaluator Loop (skip in brainstorm mode)

For each frame, spawn an evaluator agent:

```
You are reviewing a Figma frame against Dalgo's design standards.

Frame: {frame_name} (node_id: {node_id})
Screenshot: {screenshot_url}

Review checklist:
{full content of checklist.md}

Constitution (must never be violated):
{full content of .claude/constitution.md}

Check the screenshot against every item. Return this exact JSON:
{
  "frame_name": "string",
  "passed": true or false,
  "failures": [
    {"item": "checklist item text", "issue": "what is wrong", "fix": "specific correction"}
  ]
}
```

**If failures:** Send the failure list back to the frame agent that created this frame:
```
Your frame "{frame_name}" failed design review. Fix these issues and regenerate the frame,
then return the updated JSON schema.

Failures:
{failures list}
```

**Retry limit:** 3 rounds per frame. If still failing after round 3, mark the frame:
`[REVIEW FAILED — manual fix needed]` and continue.

**If passed:** Frame is final. Record it as passing.

---

## Phase 3.9: Consistency Spot-Check

After all frames pass (or exhaust retries), spawn one consistency agent:

```
Take a screenshot of each frame listed below and compare them for visual consistency.

Frames: {list of node_ids and frame names}

Check for drift in:
- Sidebar (width, active state style)
- Header (height, element positions, org name display)
- Page padding (should be --spacing-page-x 32px horizontal, --spacing-page-y 28px vertical)
- Primary CTA button (colour, style)
- Typography (heading sizes and weights)

Return:
{"consistent": true}
— or —
{"consistent": false, "issues": [{"frames": ["S1 · ...", "S2 · ..."], "property": "...", "description": "..."}]}
```

If drift is found, note it for the designer in Phase 5. Do not auto-fix.

---

## Phase 5: Designer Sign-off

Present results:

```
Designs ready on the "{page name}" page.

| Frame | Node ID | Status |
|-------|---------|--------|
| S1 · User Management | ... | ✅ Passed |
| S2 · Invite Modal    | ... | ⚠ [NEEDS CLARIFICATION] — role picker direction not provided |
| S3 · Role Editor     | ... | 🔴 [REVIEW FAILED] — fix manually |

{if consistency issues}
Consistency issues flagged:
- S1 and S3: page padding differs

{if [NEEDS CLARIFICATION] items}
These were generated without your direction — confirm or redirect:
{list of needs_clarification items per frame, with what was assumed}

Options:
1. Approve — I'll write design.md and engineering can start
2. Revise a frame: "redo S2 with inline role picker, not a modal"
3. Brainstorm alternatives: "brainstorm S3"
```

Wait for designer response before writing `design.md`.

---

## Phase 6: Write design.md

Write `features/{feature_name}/{version}/design.md` as the engineering handoff document:

```markdown
# {Feature Name} — Design ({Version})

**Status:** Ready for engineering
**Spec:** ../spec.md
**Figma:** https://figma.com/file/{file_key}
**Last updated:** {date}

## Screens

| Screen | Frame name | Node ID | Figma link | Status |
|--------|-----------|---------|-----------|--------|
| {Screen Name} | S1 · {Screen Name} | {node_id} | [View →](https://figma.com/file/{file_key}?node-id={node_id}) | ✅ Ready |

## User Flows & Prototype

| Scenario | Starting frame | Connections wired |
|----------|---------------|-------------------|
| {Scenario Name} | S1 · {Screen Name} | {N} |

## Design Decisions

{All decisions[] collected from frame agents, deduped and attributed to screen}

## Known Issues

{Any [REVIEW FAILED] or unresolved [NEEDS CLARIFICATION] items}

## Figma

file_key: {file_key}
```

Then add a one-line pointer in `spec.md` if not already present:
```markdown
**Design:** [v{N}/design.md](v{N}/design.md)
```

---

## Phase 7: Signal Readiness

```
Design gate complete.

{N} screens designed → {M} passed review → {K} issues noted

design.md: features/{feature_name}/{version}/design.md

Next: /engineering/plan-feature features/{feature_name}/{version}/spec.md
```

If open issues remain:
```
⚠ {K} issue(s) need manual attention before engineering starts.
See design.md → Known Issues.

Next: /engineering/plan-feature features/{feature_name}/{version}/spec.md
```

---

## Quality Checklist

- [ ] Mode resolved (brainstorm / draft / ship)
- [ ] Constitution loaded before any agent was spawned
- [ ] Figma file key resolved (from `design.md` or newly created)
- [ ] Design brief written or read (session was not blocked)
- [ ] Scout ran and returned canvas state and `next_x`
- [ ] All frame agents returned the fixed JSON schema
- [ ] Evaluator loop ran for every frame (draft and ship modes)
- [ ] Consistency spot-check ran across all final frames
- [ ] Designer signed off
- [ ] `design.md` written with node IDs, decisions, known issues, and `file_key`
- [ ] `spec.md` updated with one-line pointer to `design.md`
- [ ] Next step printed clearly
