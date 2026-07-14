# Design Brief — Access Control (Spec A) v1

**Status:** Awaiting designer input
**Spec:** access-control-spec-A-role-system-2026-06-02.md
**Generated:** 2026-06-04

Fill in your direction below each surface, then re-run:
`/design:design-handoff features/access-control/v1/access-control-spec-A-role-system-2026-06-02.md`

Leave a section blank to let me use best judgment for an NGO audience
(I'll tag those decisions `[NEEDS CLARIFICATION]` in the output).

---

## Surface 1: Sidebar — Role-Adaptive Navigation

**Who uses it:** All roles — Admin, Analyst, Member (each sees a different set of items)
**What it does:** The left navigation rail that hides — not greys — items the user's role can't reach.

**Capability map from spec (§5.3):**
| Item | Admin | Analyst | Member |
|------|-------|---------|--------|
| Dashboards, Charts, Reports, Alerts | ✅ | ✅ | ✅ |
| Data (Ingest / Transform / Warehouse) | ✅ Edit | ✅ Read-only | ❌ Hidden |
| Pipelines / Orchestration | ✅ Edit | ✅ Read-only | ❌ Hidden |
| Settings | ✅ Full | Groups only | Groups only |
| Create buttons on content pages | ✅ | ✅ | ❌ Hidden |

**Decisions needed:**
- Should the three role states be shown as one Figma frame with a role toggle, or three separate frames (Admin / Analyst / Member)?
- Does the sidebar have any visual indicator of the user's current role (badge, label in the footer area)?
- Where does the "Settings" item live — bottom of nav rail or grouped with the main items?
- What does the active state look like vs. hover state? Any reference to follow?

**Reference design (if any):**

**Your direction:** <!-- fill in here -->

---

## Surface 2: No Access Page

**Who uses it:** Any user who navigates directly to a URL they don't have role access to (e.g., a Member trying to reach `/ingest`)
**What it does:** Blocks unauthorized direct URL access; redirects from route middleware. Shows the org Admin contact.

**Decisions needed:**
- What information is shown? The spec says "org Admin contact" — should this be name + email, or just "contact your administrator"?
- Is there a "Go to home" / "Back to dashboard" CTA?
- Should this feel like a 404 (full-page blank) or an in-app message within the shell (sidebar still visible)?
- Do we need separate states for "no access to this specific thing" vs. "you're not logged in" vs. "this doesn't exist"?

**Reference design (if any):**

**Your direction:** <!-- fill in here -->

---

## Surface 3: Settings — Restructured IA

**Who uses it:** Admin (full), Analyst (Groups section only), Member (Groups they're in only)
**What it does:** The consolidated Settings area with Admin-only globals (Warehouse, Appearance, Org defaults, Users) and shared-but-scoped sections (Groups).

**Settings sections from spec (§7):**
- Warehouse / Data connection (Admin only)
- Appearance / Themes (Admin only)
- Org defaults: default visibility floor + "allow public sharing" toggle (Admin only — inert until Spec B)
- Users (Admin only)
- Groups (scoped per role)

**Decisions needed:**
- How is Settings navigation structured? Left sidebar within Settings, tabs, or a single scrollable page with sections?
- How are Admin-only sections presented to non-Admins — completely hidden, or visible with a lock and "Admin only" label?
- The Org defaults section ships inert (toggles don't do anything until Spec B). Do we render the toggles greyed/disabled, or skip that section entirely in Spec A?
- Should Settings be a full-page takeover (replaces main content area) or a slide-over panel?

**Reference design (if any):**

**Your direction:** <!-- fill in here -->

---

## Surface 4: Settings > Users

**Who uses it:** Admin only
**What it does:** Full user management — view all org users, invite new ones, change roles, delete users, and trigger ownership transfer.

**Table columns from spec:** Name, Email, Role (Admin/Analyst/Member), Status (active/pending), Last active

**Actions available:**
- Invite user (CTA → modal)
- Change a user's role (dropdown or edit flow)
- Delete user (destructive — with confirmation)
- Transfer ownership of resources when deleting a user who owns things

**Decisions needed:**
- Is role change done inline (dropdown in the table row) or via an edit modal?
- Does the delete user action check for owned resources first and prompt a transfer before deletion, or is it a single confirmation?
- Should pending invites (invited but not yet accepted) appear in the same table or a separate "Pending" tab/section?
- What does the empty state look like when there are no other users yet?
- Is ownership transfer triggered from here (on delete) or does it exist separately on resources? The spec mentions both — should this brief only cover the Settings > Users entry point?

**Reference design (if any):**

**Your direction:** <!-- fill in here -->

---

## Surface 5: Invite User Modal

**Who uses it:** Admin (inviting new users directly without a resource share)
**What it does:** Creates a new platform user and assigns them a role. No resource grant at this stage — pure onboarding. Only Admins can assign Analyst or Admin roles; Analyst/Member tier is the max others can grant (but this modal is Admin-only anyway).

**Fields:** Name, Email, Role (Admin / Analyst / Member dropdown)

**Decisions needed:**
- Does the modal send an email invite immediately on submit, or is it just account creation?
- What is the success state — toast only, or does the modal show a confirmation before closing?
- Should the role dropdown show a description of each role to help the Admin choose (e.g., "Analyst — can build dashboards, read-only access to data infrastructure")?
- If the email is already in the system, what happens?

**Reference design (if any):**

**Your direction:** <!-- fill in here -->

---

## Surface 6: Ownership Transfer

**Who uses it:** Resource owner (self-initiated transfer) or Admin (override for governance or when a user leaves)
**What it does:** Reassigns the owner of a resource from one user to another.

**Two entry points from spec:**
1. Resource action menu (owner or Admin acts on a specific resource)
2. Settings > Users (Admin triggers when deleting a user who owns resources)

**Decisions needed:**
- Should this be a modal or an inline action? If modal: how is the new owner selected (user picker / search, or dropdown)?
- Does this need a confirmation step before completing, given that ownership grants delete rights to the new owner?
- For the Settings > Users entry point (deleting a user): is the transfer a blocking step before deletion completes, or optional?
- Is the resource-menu entry point in scope for Spec A design, or just the Settings > Users entry point? (The spec mentions both but only Settings > Users ships functionally in Spec A)

**Reference design (if any):**

**Your direction:** <!-- fill in here -->

---

## Surface 7: Data Section — Analyst Read-Only State

**Who uses it:** Analyst browsing Data infrastructure (Ingest / Transform / Warehouse / Pipelines / Orchestration)
**What it does:** The Analyst can see the Data section but cannot create, edit, or delete anything. All write actions are removed.

**Decisions needed:**
- How is read-only conveyed to the Analyst? Options: (a) remove Create/Edit/Delete buttons entirely, (b) show them greyed with a tooltip "You have read-only access", (c) show a banner at the top of the page
- Is there a persistent indicator that they're in read-only mode (e.g., a small "Read only" badge near the page title)?
- Does this apply uniformly to all Data sub-sections (Ingest, Transform, Warehouse, Pipelines), or does each section look slightly different?
- Should we design the read-only state for one representative Data section (e.g., Ingest) and note that it applies to all, or design each?

**Reference design (if any):**

**Your direction:** <!-- fill in here -->

---

## Surface 8: Migration Changelog Modal

**Who uses it:** All users on their first login after the migration runs
**What it does:** Explains what changed in the role model. Content differs per role — Admins, Analysts, and Members see different summaries.

**Key changes to communicate per role:**
- **Admin:** New three-role model; they keep full access; Settings has moved
- **Analyst:** Loses Data infra write access → read-only; content access unchanged
- **Member:** Replaces "Guest"; now sees all content as View-only in the interim

**Decisions needed:**
- Is this one modal with conditional content per role, or three distinct modal designs?
- Should the modal show the full change list, or a condensed 2–3 bullet summary with a "Learn more" link?
- Is there a "Don't show again" option, or just a dismiss button (one-time only)?
- Should the modal include a CTA — e.g., "Go to Settings" for Admins, "Go to Dashboards" for Members?

**Reference design (if any):**

**Your direction:** <!-- fill in here -->

---

## Shared Components (no direction needed — will follow patterns.md)

These will be implemented per existing design standards without needing your input:
- **Role badge/chip** — Admin / Analyst / Member displayed as a small pill in the user table
- **Admin-lock treatment** — lock icon + "Contact your admin to change this" for locked fields
- **Permission-gated empty states** — when a section is hidden for a role, it simply isn't rendered (no greyed placeholder)
