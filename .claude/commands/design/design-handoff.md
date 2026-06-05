# Design Handoff

## Input: $ARGUMENTS

Bridge a feature spec into Figma designs with designer input, then update the spec so engineering can start.

Accepts:
- A spec file path: `features/rbac/v1/spec.md`
- A feature folder: `features/rbac/v1/`
- A feature name: `rbac` (looks for `features/rbac/v1/spec.md`)

Flags:
- `--auto` — skip designer input, generate all surfaces autonomously (for prototyping only)

---

## Phase 1: Read & Extract

### 1. Read the spec
Load the spec file from `$ARGUMENTS`. If a folder is given, look for `spec.md` inside it. If only a feature name is given, check `features/{name}/v1/spec.md` then `features/{name}/spec.md`.

### 2. Extract UI surfaces
Parse the spec for every user-facing screen, flow, modal, or component that needs designing. Look for:
- Explicit screen names ("User management page", "Invite modal")
- User stories that imply a UI ("As an admin, I want to assign roles...")
- State changes that need visual design (empty states, error states, success states)
- Shared components mentioned (badges, selectors, inline controls)

For each surface, extract:
- **Purpose:** what the user accomplishes on this screen
- **Persona:** which Dalgo user type interacts with it (admin, PM, field staff)
- **Key decisions:** things that need a designer's judgment before the screen can be built
- **Dependencies:** does this screen reference another surface?

### 3. Load patterns
Read `.claude/skills/design-review/patterns.md` and `.claude/skills/design-review/checklist.md` — these are the design standards all generated frames must pass.

---

## Phase 1.5: User Flow Extraction

For each surface extracted above, map the full user journey through that screen. This becomes the basis for prototype connections wired in Figma after frames are created.

For each surface, produce a flow block:

```
**Screen: {Screen Name}**
Entry points:
- {How the user arrives — e.g. "clicks 'Invite user' button on User management page"}
- {Alternative entry — e.g. "redirected here after accepting email invite"}

Happy path:
1. {Step 1 — e.g. "User sees modal with Name, Email, Role fields"}
2. {Step 2 — e.g. "User fills in details and clicks 'Send invite'"}
3. {Step 3 — e.g. "Success toast shown, modal closes, user appears in table"}

Branch points:
- {Condition → Screen} e.g. "Email already exists → inline field error (stays on modal)"
- {Condition → Screen} e.g. "Last admin demotion attempt → blocked with error banner"
- {Condition → Screen} e.g. "Cancel / Esc → dismiss modal, no change"

Exit points:
- Success → {target screen or state}
- Cancel → {target screen or state}
- Error → {stays on screen / redirects to X}
```

Group screens into **scenarios** — named end-to-end journeys a user might take:
- e.g. "Invite a new team member" → Invite modal → Success state → User management table
- e.g. "Change a user's role" → User table → Role selector → Confirm modal → Updated table
- e.g. "Remove a user" → User table → Delete confirm → Empty state (if last user)

Each scenario becomes a **named prototype flow** in Figma.

Store the extracted flows and scenarios for use in Phase 3 (Figma agent prompts) and Phase 3.5 (prototype wiring).

---

## Phase 2: Design Brief (skip if `--auto`)

Present the extracted surfaces to the designer in this format:

```
I found {N} screens to design for {Feature Name}.

Before I generate anything in Figma, I need your direction on a few things:

---

**Screen 1: {Screen Name}**
Who uses it: {persona}
What it does: {purpose}
Decisions needed:
- {Decision 1 — e.g. "Inline role edit or separate modal?"}
- {Decision 2 — e.g. "What happens when you demote the last admin?"}
- {Decision 3 — e.g. "Any reference design or existing Dalgo screen to match?"}

---

**Screen 2: {Screen Name}**
...

---

Reply with your direction for each screen. You can:
- Answer the decisions ("Screen 1: inline edit, block last-admin demotion")
- Skip a screen ("skip Screen 3 — not needed for v1")
- Add context ("reference the existing Reports share modal for Screen 2")
- Point to inspiration ("Screen 4 should look like Notion's permission picker")

I won't generate anything until you reply.
```

**Wait for designer reply before proceeding.** Do not spawn any Figma agents until the designer has responded.

### Parse designer reply
Read the reply and map each direction to its surface:
- Extract copy/label decisions ("use 'Full access' not 'Admin'")
- Note referenced screens or external inspiration
- Note skipped surfaces
- Note any specific layout preferences ("single-step modal", "use the existing empty state pattern")

---

## Phase 3: Generate Designs in Figma

### 1. Determine Figma page name
Use `"{Feature Name} Designs"` as the page name (e.g. "RBAC Designs"). Check if it already exists using `mcp__figma__get_metadata` on file key `v8BYFkebTGQNuiRrCXWssa`.

### 2. Spawn one Figma agent per surface (in parallel)
For each surface (excluding skipped ones), spawn an agent with this context:

```
You are a UX designer for Dalgo — an open-source data platform for non-technical NGO program managers.

Feature: {Feature Name}
Screen: {Screen Name}
Persona: {persona}
Purpose: {purpose}

Designer direction:
{designer's direction for this screen}

User flow for this screen:
{paste the flow block from Phase 1.5 for this surface — entry points, happy path, branch points, exit points}

Scenario(s) this screen belongs to:
{list scenario names from Phase 1.5 that include this screen}

Dalgo Design System:
- Primary color: #00897B (teal)
- Font: Anek Latin
- Icons: Lucide 16px
- Cards: 1px border, 8px radius, 16px padding
- Spacing: 4px grid, 24px page padding
- Primary CTA: ghost variant, teal background (#00897B), white text
- Secondary: outline button
- Sentence case on all buttons ("Cancel" not "CANCEL")
- Status colors: green #16a34a (on track), amber #d97706 (at risk), red #dc2626 (off track)
- Never expose SQL, schema table names, or code to non-admin users
- Lock icon + "Contact admin to change" for admin-only fields

Key patterns to follow:
{paste relevant excerpts from patterns.md for this surface type}

Figma file: v8BYFkebTGQNuiRrCXWssa
Page: {page name}
Frame name: "{Screen Name}"
Frame size: 1440×900px
Position: x={calculated offset}, y=0

Instructions:
1. Invoke the /figma-use skill first — mandatory before calling use_figma
2. Create the frame on the "{page name}" page (create the page if it doesn't exist)
3. Name the frame exactly as "{Screen Name}" — this name is used to wire prototype connections in the next phase
4. After creating, call get_screenshot on the created node and verify it matches the brief
5. Return the node ID, frame name, and a one-line description of what was built
```

Position frames left to right with 100px gaps: x=0, x=1540, x=3080, etc.

### 3. Collect node IDs
Wait for all agents to complete. Collect the node ID, frame name, and description for each frame.

---

## Phase 3.5: Wire Prototype Connections

Using the user flows and scenarios from Phase 1.5, add prototype connections between frames in Figma. This turns the static frames into a navigable, clickable prototype.

### 1. Build the connection map
For each scenario, map out every connection:

```
Scenario: {Scenario Name}
Connections:
- From: {Frame Name} | Trigger: {element clicked — e.g. "'Send invite' button"} → To: {Frame Name}
- From: {Frame Name} | Trigger: {"Cancel" button click} → To: {Frame Name}
- From: {Frame Name} | Trigger: {error condition} → To: {Frame Name}
```

### 2. Invoke `/figma-use` skill
Mandatory before calling `use_figma` for prototype wiring.

### 3. Add connections via `use_figma`
For each connection in the map, use `use_figma` to:
- Select the trigger element on the source frame (button, link, overlay area)
- Add a prototype interaction: `On click → Navigate to → {target frame node ID}`
- For overlays/modals: use `Open overlay` instead of Navigate
- For back/cancel flows: use `Navigate to` with `Back` or the specific target frame

Wire all connections in one `use_figma` call per scenario where possible.

### 4. Set starting frames per scenario
For each scenario, mark the first frame as the **starting point** of that named flow in Figma:
- Use `use_figma` to set the flow start frame with the scenario name as the flow label
- This creates named flows in Figma's prototype panel (e.g. "Invite a new team member")

### 5. Collect wiring results
For each scenario, confirm:
- All connections were added successfully
- Flow start frame is set
- Note any connections that could not be wired (e.g. element not found in frame) for manual follow-up

---

## Phase 4: Design Review

For each created frame, run the design review checklist from `.claude/skills/design-review/checklist.md`. Specifically check:

**Content & Copy:**
- [ ] Sentence case on all buttons
- [ ] No SQL, schema names, or code visible to non-admin users
- [ ] No internal acronyms (RAG, blast radius) in UI copy
- [ ] Placeholder text uses "e.g." not "Choose"

**NGO User Specific:**
- [ ] Screen purpose clear in 5 seconds
- [ ] Creation flows are user-task-first (not data-model-first)
- [ ] Admin-only fields are visually locked (lock icon)

**Blast Radius (if applicable):**
- [ ] "Used By" count shown if entity has dependents
- [ ] Edit modal shows amber impact banner if entity is shared
- [ ] Delete confirmation lists dependents as links when Used By > 0

**Status & KPI (if applicable):**
- [ ] RAG color is dominant visual signal (not just a text label)
- [ ] Trend language is unambiguous

Produce a review table:

```
| Screen | Node ID | Issues | Status |
|--------|---------|--------|--------|
| User management table | 11900:63 | None | ✅ Ready |
| Invite user modal | 11901:63 | "Admin" label → "Full access" | ⚠ Fix needed |
```

---

## Phase 5: Designer Sign-off

Present the review results and ask:

```
Designs are ready on the "{page name}" Figma page.

Review summary:
{review table}

{if issues exist}
{N} screen(s) need attention before I update the spec:
- {Screen}: {issue} → Suggested fix: {fix from patterns.md}

Options:
1. Fix the issues and regenerate the flagged frames
2. Accept as-is and note the issues in the spec for engineering to handle
3. Revise a specific frame ("redo Screen 2 with X change")
```

Wait for designer response before updating the spec.

---

## Phase 6: Update the Spec

Append a `## Design` section to the spec file:

```markdown
## Design

**Status:** {Ready for engineering / Pending fixes}
**Figma page:** {URL to page}
**Last updated:** {date}

### Screens

| Screen | Node ID | Figma Link | Status |
|--------|---------|-----------|--------|
| {Screen Name} | {node_id} | [View →]({figma_url}) | ✅ Ready |

### User Flows & Prototype

| Scenario | Starting Frame | Prototype Link | Connections |
|----------|---------------|----------------|-------------|
| {Scenario Name} | {Frame Name} | [Preview →]({figma_prototype_url}) | {N} wired |

### Design Decisions

Decisions made during design brief that engineering must implement:
- **Role labels:** Use "Full access / Can edit / Can view only" — not "Admin/Editor/Viewer"
- **Last-admin protection:** Block role change that would remove the last org admin; show inline error
- {other decisions from designer replies}

### Known Issues

{if any screens were accepted with issues}
- {Screen}: {issue} — to be resolved in v2

### Design Checklist

- [ ] All screens reviewed against patterns.md
- [ ] NGO user lens applied
- [ ] Blast radius handled where applicable
- [ ] Designer has signed off
```

---

## Phase 7: Signal Readiness

Print:

```
Design gate complete. Spec updated at {spec path}.

{N} screens designed → {M} passed review → {K} issues noted

Next: /engineering/plan-feature {spec path}
```

If there are unresolved issues, print:

```
⚠ Design gate has {K} open issue(s). Resolve before engineering starts,
or run with known issues and track them in the spec.

Next: /engineering/plan-feature {spec path}
```

---

## Quality Checklist

- [ ] Designer was given a brief and responded before any generation started (unless `--auto`)
- [ ] Every screen has a node ID and was verified with a screenshot
- [ ] User flows extracted for every surface (entry points, happy path, branches, exits)
- [ ] Screens grouped into named scenarios
- [ ] Prototype connections wired for all scenarios
- [ ] Named flow start frames set per scenario in Figma prototype panel
- [ ] Design review was run against the updated checklist
- [ ] Designer signed off (or explicitly accepted issues)
- [ ] Spec `## Design` section is complete with node IDs, scenario table, decisions, and known issues
- [ ] Next step printed clearly
