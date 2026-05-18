# Automation Context — Metrics & KPIs Project Automation

**Date generated:** 2026-04-30
**Purpose:** Hand this file to a new chat to build the Cowork automations defined in Step 5 of the project planning session.

---

## What we want to build

Three Cowork automations for the Metrics & KPIs Linear project, in priority order:

1. **Weekly status update** — runs Mon + Thu, pulls Linear data, drafts + posts a status update
2. **Milestone gate check** — manual trigger before gate meetings, checks ticket health per milestone
3. **Kickoff setup skill** — reusable skill to scaffold a new feature project from a spec file

---

## Linear project details

| Field | Value |
|-------|-------|
| Project name | Metrics & KPIs |
| Project ID | `315c6f2b-ffb0-46c4-9973-ad462d8f62f4` |
| Project URL | https://linear.app/dalgo/project/metrics-and-kpis-1a6c9c02918e |
| Linear MCP ID | `d34dfeae-0807-4d19-bb74-a50b5f5deb12` |

### Milestones (name → ID mapping needed)
Run `list_milestones` with project ID to get current milestone IDs. As of Apr 30:
- M0 — Spec & alignment (target Apr 30) ✅ Done
- M1 — Design (target May 5)
- M2 — Build (target May 15) — engineering to populate
- M3 — Internal dogfood (target May 17)
- M4 — Customer test (target May 22) — cohorts: ATECF, Bhumi, Antarang, Baala
- M5 — Feedback resolved (target May 26)
- M6 — Docs & enablement (target May 28)
- M7 — GA (target May 30)
- M8 — Adoption review (target Jun 15)

### Labels in use
- `feat:metrics`, `feat:kpis`, `feat:annotations`, `feat:instrumentation`
- `ATECF`, `Bhumi`, `Antarang`, `Baala`
- Existing: `Bug`, `Design`, `Spec`, `Test`, `Public Launch`

### Team members
- **PM:** Abhishek Nair (Abhishek on Linear)
- **Engineering lead:** Ishan
- **Design:** Noopur
- **Customer ops:** Anusha
- **Engineering org:** 4 engineers total (Ishan + 3)

---

## Automation 1: Weekly Status Update

### Trigger
- Monday 9:00 AM IST
- Thursday 5:00 PM IST

### Logic
1. Call `list_milestones(project: "315c6f2b-ffb0-46c4-9973-ad462d8f62f4")` → get all milestones + targets
2. Call `list_issues(project: "315c6f2b-ffb0-46c4-9973-ad462d8f62f4")` → get all issues with status, milestone, labels
3. Compute:
   - Issues per milestone by status (Todo / In Progress / Done / Cancelled)
   - Issues without milestone linkage (flag as ⚠️)
   - Issues in "In Progress" for >5 days (flag as 🔴)
   - Issues without any feat: label (flag as 🔴)
4. Read risk register doc ID `6f6bc5b5-db27-4473-b089-87e4f7599252` via `get_document` → extract active risks with score ≥ 5
5. Draft status update body using the template below
6. **Either** post via `save_status_update` automatically, **or** present to Abhishek in Cowork for 1-click approval before posting

### Status update template
```
# Week [N] — [Date]

## Summary
[2-sentence health summary based on milestone progress]

## What's done since last update
[bullet list from issues moved to Done since last update]

## What's happening next
[bullet list: next 3–5 key actions or milestones]

## Risks
[from risk register: only items with score ≥ 5, formatted as R1 🔴 / R2 🟡 etc.]

## Milestone status
| Milestone | Target | Status |
|-----------|--------|--------|
[row per milestone, status = ✅ Done / 🟡 In progress / ⬜ Not started / 🔴 At risk]

*Next update: [next scheduled date]*
```

### Health determination
- `onTrack`: all active milestones on schedule, no 🔴 risks escalated
- `atRisk`: any active milestone has >20% of issues in In Progress with <3 days to target OR any 🔴 risk unmitigated
- `offTrack`: milestone target passed with open issues OR 🚨 risk active

---

## Automation 2: Milestone Gate Check

### Trigger
Manual — Abhishek runs before each milestone gate meeting

### Logic
1. Accept milestone name as input (e.g. "M2" or "Build")
2. Fetch all issues for that milestone
3. Check:
   - [ ] All issues are Done or Cancelled (or explicitly deferred with a comment)
   - [ ] No open bugs with severity = Urgent or High
   - [ ] Next milestone's scaffold tickets exist (at least 1 issue in next milestone)
   - [ ] Risk register: no new 🔴/🚨 risks added since last check
4. Output: gate checklist as text, with pass/fail per item
5. Post as a comment on the milestone's "gate" ticket (each milestone has one — look for title containing "Gate" or "Milestone review")

---

## Automation 3: Kickoff Setup Skill

### When to use
At the start of any new feature project. Input: a spec file (markdown) + a short answers file. Output: Linear project scaffolded with milestones, labels, tickets, risk register, and Week 0 status update.

### Input format (answers file)
```yaml
project_name: "Feature Name"
linear_team: "Dalgo"
pm: "Abhishek"
eng_lead: "Ishan"
design_lead: "Noopur"
customer_ops: "Anusha"
customer_cohorts: ["ATECF", "Bhumi"]
design_target: "2026-MM-DD"
build_target: "2026-MM-DD"
customer_test_target: "2026-MM-DD"
ga_target: "2026-MM-DD"
adoption_review_target: "2026-MM-DD"
feature_areas: ["feature-a", "feature-b"]  # becomes feat: labels
```

### Steps
1. Parse spec file → extract user stories, scope in/out, dependencies
2. Parse answers file → dates, team, cohorts
3. Create Linear project with description (using `save_project`)
4. Create milestones M0–M8 with computed dates
5. Create feat: labels + customer cohort labels
6. Create scaffold tickets (one per lifecycle activity, same structure as Metrics & KPIs project)
7. Create risk register document (populate with standard risk template, pre-fill any obvious risks from spec)
8. Post Week 0 status update

### Reference project
The Metrics & KPIs project (ID: `315c6f2b-ffb0-46c4-9973-ad462d8f62f4`) is the canonical example. Use its ticket structure as the template.

Milestone ticket categories:
- M0: Spec alignment, WBS workshop, kick-off
- M1: Design review gate
- M2: (empty — engineering populates from WBS)
- M3: Dogfood test plan, internal testing, bug triage
- M4: Per-cohort customer test tickets (one per cohort), debrief aggregation
- M5: Feedback triage, fixes, sign-off
- M6: Docs (overview, how-tos), training materials, help article
- M7: GA checklist, feature flag rollout, announcement
- M8: Adoption review (usage data, NPS pulse, lessons learned)

---

## Key MCP tools to use

| Tool | Purpose |
|------|---------|
| `list_milestones` | Get milestone IDs and targets |
| `list_issues` | Get all issues with status/labels/milestone |
| `list_comments` | Get comments on specific issues (for debrief aggregation) |
| `get_document` | Read the risk register |
| `save_document` | Update the risk register |
| `save_status_update` | Post project status update |
| `save_issue` | Create or update tickets |
| `save_milestone` | Create milestones |
| `save_project` | Create a new Linear project |
| `get_status_updates` | Read previous updates (use project ID, not slug) |

**Important:** `get_status_updates` requires the project UUID (`315c6f2b-ffb0-46c4-9973-ad462d8f62f4`), NOT the slug (`metrics-and-kpis-1a6c9c02918e`). Slugs return empty results.

---

## Cowork scheduled task format

To create the Monday status update task:
```
Task name: Metrics & KPIs — Weekly status update
Schedule: Every Monday at 9:00 AM IST (03:30 UTC)
Instructions: [paste Automation 1 logic above]
```

---

## Notes from planning session (apply to automation design)

- **Lessons from Reports project audit:**
  - 87% of issues were unlabeled → automation should flag issues without feat: labels
  - 22/84 issues had no milestone → automation should flag orphaned issues
  - Customer test tickets went stale (42 days, 0 comments) → gate check should flag issues with >7 days since last comment in M4
  - Mega-ticket anti-pattern: one issue (DALGO-878) accumulated all feedback → automation should flag issues with >10 comments as potential mega-tickets

- **Eng and PM spec are being re-aligned:** Engineering is rebuilding their spec based on PM spec. Annotations, inline creation, blast-radius dialog, and reference counts are now in scope for May 15.

- **Feature flag:** GA rollout is feature-flagged. Risk register R6 covers flag state inconsistencies.
