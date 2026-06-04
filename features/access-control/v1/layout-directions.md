# Layout Directions — Access Control v1

**Status:** Awaiting designer picks
**Spec:** access-control-spec-A-role-system-2026-06-02.md
**Generated:** 2026-06-04

All surfaces below are `[NEEDS CLARIFICATION]` — designer did not fill in `design-brief.md`.
Variants generated using best judgment for a non-technical NGO audience.

**To pick a variant:** Add `→ build this` after the variant heading, or note your direction
below each surface. Then re-run: `/design:design-handoff features/access-control/v1/`

---

## Surface 1: Sidebar — Role-Adaptive Navigation

Designer direction: [NEEDS CLARIFICATION] — using best judgment

### Variant A — Single frame with role switcher

Layout: Standard app shell (224px sidebar, 60px header). A role-switcher dropdown sits at the
top of the sidebar below the org logo. Nav items below it react to the selected role — items
the role can't reach vanish entirely. One Figma frame, but requires prototype interaction to
demonstrate all three states.

Key elements:
- Org logo + name at top (header area of sidebar)
- Role dropdown: "Viewing as: Admin ▾" — useful for design review
- Nav items in order: Dashboards, Charts, Reports, Alerts, (separator), Data, Pipelines,
  (separator), Settings
- Member view: Data, Pipelines, Settings, and Create buttons all hidden
- Active item: left border accent in brand-primary, background brand-primary-light
- Settings: pinned at bottom of nav rail, separated by a divider

Copy: Nav labels sentence case — "Dashboards", "Charts", "Reports", "Alerts", "Data", "Pipelines", "Settings"
Trade-off: The role switcher is convenient for demos and review but adds a UI element that
wouldn't exist in production. Requires interaction to show all three role states.

### Variant B — Three separate frames (Admin / Analyst / Member) ← Recommended

Layout: Three separate 1440×900 frames in Figma, one per role, side by side. Each shows the
sidebar in that role's exact state — Admin sees everything, Analyst sees Data (read-only badge)
and Pipelines but no Users in Settings, Member sees only content items. No role switcher UI.
Role chip shown in the sidebar footer (user avatar + name + role badge).

Key elements:
- Frame 1 (Admin): All nav items. "Settings" at bottom. User footer: avatar + "Admin" chip in
  brand-primary.
- Frame 2 (Analyst): Data items present (read-only badge on the Data section label), Pipelines
  present. Settings visible — only Groups accessible. User footer: "Analyst" chip in grey.
- Frame 3 (Member): Dashboards, Charts, Reports, Alerts only. No Create buttons on content
  pages. No Data, no Pipelines, no Settings. User footer: "Member" chip in grey.
- Active item style: 3px left border in brand-primary, bg brand-primary-light (teal tint),
  label in brand-primary.
- Hover style: bg surface-hover (#f5f7f8), no border change.

Copy: Same sentence-case nav labels. Footer shows "Priya M. · Admin" style.
Trade-off: More frames, but unambiguously shows all three role states for both design review
and engineering spec. Best for static handoff.

**Recommended:** Variant B — Three separate frames are the clearest reference for engineers
and the clearest demonstration of "hide, don't grey" for all three roles. No interactive
assumption required.

---

## Surface 2: No Access Page

Designer direction: [NEEDS CLARIFICATION] — using best judgment

### Variant A — Full-page blank (no shell)

Layout: Centered content on a plain bg (#f8fafb) with no sidebar or header. Lock icon (48px),
heading "You don't have access to this page", subtext "Contact your administrator to request
access", admin name + email as a mailto link, and a "Go to dashboards" CTA button.

Key elements: Lock icon, heading, subtext, admin contact card (name + email), single CTA
Copy: "You don't have access to this page. Contact [Admin Name] at [email] to request access."
    CTA: "Go to dashboards"
Trade-off: Clean and unambiguous, but disorients users because they lose the nav context and
can't see where else to go.

### Variant B — In-shell (sidebar + header visible) ← Recommended

Layout: Normal app shell (Member's sidebar: Dashboards, Charts, Reports, Alerts; 60px header
with org name and user avatar). Main content area shows the no-access message centred in the
remaining space. The user can still navigate to pages they do have access to.

Key elements:
- Sidebar shows only the Member's permitted items (so they can immediately navigate away)
- Header shows current page breadcrumb: "Data › Ingest" (wherever they tried to go)
- Centered content block: Lock icon (40px), heading, subtext, admin contact, CTA
- Admin contact card: name + email, displayed as a subtle card (border, border-radius-md)
- CTA: primary button "Go to dashboards"

Copy: Heading: "You don't have access to this page"
    Body: "This section isn't available for your account. Contact [Admin Name] ([email]) if
    you think you need access."
    CTA: "Go to dashboards"
Trade-off: Slightly more complex to render (requires shell), but far better for NGO users who
are disoriented by a blank full-page error. They can see the nav and recover immediately.

**Recommended:** Variant B — Keeping the shell visible is essential for low-technical-literacy
users. A full-page blank is a dead end; in-shell gives an immediate recovery path.

---

## Surface 3: Settings — Restructured IA

Designer direction: [NEEDS CLARIFICATION] — using best judgment

### Variant A — Left sub-navigation within Settings ← Recommended

Layout: Settings is a full-page takeover replacing the main content area (sidebar still
visible). A secondary nav rail (180px) sits inside Settings on the left, listing the sections
(Warehouse, Appearance, Org Defaults, Users, Groups). Admin sees all five; Analyst and Member
see only Groups. Clicking a section loads it in the right content area (the remaining width).

Key elements:
- "Settings" as the page heading in the header area
- Secondary nav: vertically stacked text links with active-state styling matching the main nav
- Warehouse, Appearance, Org Defaults, Users: Admin-only — completely hidden from other roles
- Groups: visible to all (scoped content per role)
- Org Defaults section: toggles rendered but visually inert (greyed, labelled "Coming soon")
- Active section: brand-primary left border, brand-primary-light background (matches main nav)

Copy: Section labels: "Warehouse", "Appearance", "Org defaults", "Users", "Groups"
    Org Defaults note: "These settings will take effect when resource sharing is enabled."
Trade-off: Uses more horizontal space than tabs, but scales well as Settings grows. Familiar
pattern to NGO users who have seen Google Workspace or Notion Settings.

### Variant B — Horizontal tabs

Layout: Settings page with horizontal tabs at the top: [Warehouse] [Appearance] [Org Defaults]
[Users] [Groups]. Non-admin tabs hidden. Content below tabs.

Key elements: Standard tab bar, content area beneath.
Copy: Same section labels.
Trade-off: Simpler, less real estate. But breaks when section count grows or labels get long.
Harder to scan at a glance than a vertical list.

### Variant C — Slide-over panel from right

Layout: Settings opens as a right-side panel (640px wide) over the current page. The
underlying page is dimmed. Secondary nav inside the panel.

Key elements: Panel header "Settings", close button (×), secondary nav + content.
Copy: Same.
Trade-off: Panel approach keeps context (user sees what page they were on) but is a non-
standard pattern for a Settings area with multiple sections and complex forms. Scroll behavior
inside panels is awkward on low-resolution laptops (common in field). Not recommended.

**Recommended:** Variant A — Left sub-nav is the established pattern for multi-section settings.
It's predictable for NGO users, scales gracefully, and matches Dalgo's existing sidebar
navigation style.

---

## Surface 4: Settings > Users

Designer direction: [NEEDS CLARIFICATION] — using best judgment

### Variant A — Table with inline role dropdown ← Recommended

Layout: Full-page layout (Settings shell, left sub-nav active on "Users"). Fixed header with
"Users" title, "Invite user" CTA (top right). Scrollable table below: Name, Email, Role,
Status, Last active columns. Role column is an inline dropdown chip — click to change.
"Pending" badge inline in Status column (not a separate tab).

Key elements:
- Page header: "Users" (text-3xl, bold) + subtext "Manage who has access to your organisation"
- Invite user: primary CTA button (top right)
- Table columns: Name + avatar, Email, Role (chip/dropdown), Status (Active/Pending badge),
  Last active (relative time: "3 days ago")
- Role chip colours: Admin = brand-primary background, Analyst = grey, Member = grey
- Row hover: bg surface-hover; row action menu (⋯) on hover — shows "Delete user"
- Delete: shows confirmation dialog before proceeding; if user owns resources, shows transfer
  step first
- Pending invites: shown in same table, Status = "Pending" chip in amber

Copy: Heading: "Users" · Subheading: "Manage who has access to your organisation"
    Role chips: "Admin", "Analyst", "Member"
    Status chips: "Active" (green), "Pending" (amber)
    Delete confirmation: "Delete [Name]? This will remove their access to Dalgo."
Trade-off: Inline role change is fast for small teams (typical NGO: 5–15 users). Keeps the
admin on the same page with minimal navigation.

### Variant B — Table with edit-user modal

Layout: Same table, but role column is read-only text. "Edit" icon in each row opens a modal
with Name, Email, Role fields. Delete is a separate action in the row menu.

Key elements: Same table, edit modal for role change.
Trade-off: More clicks for a role change, but provides a more deliberate flow if orgs are
concerned about accidental role changes. Slightly higher friction for small frequent updates.

**Recommended:** Variant A — Inline dropdown is the right call for small NGO teams. Faster
admin experience, less navigation, and the confirmation step on delete handles the "accidental"
risk for the only truly destructive action.

---

## Surface 5: Invite User Modal

Designer direction: [NEEDS CLARIFICATION] — using best judgment

### Variant A — Single form with inline role descriptions ← Recommended

Layout: Shadcn Dialog (max-w-md). Title "Invite user". Three fields: Name, Email, Role
(dropdown). Role dropdown options include a short description below each role name. Submit
sends the invite email immediately. Success: toast notification + modal closes. If email
already exists: inline error below the Email field.

Key elements:
- Modal title: "Invite user"
- Name field (optional — they can fill it themselves)
- Email field (required, validated inline)
- Role dropdown with descriptions:
    Admin — Full access, can manage users and settings
    Analyst — Can build dashboards; read-only on data infrastructure
    Member — Can view content shared with them
- Submit CTA: "Send invite" (primary button)
- Cancel: text link "Cancel" or secondary button
- Duplicate email: "A user with this email already exists. View their profile →"
- Loading state on submit: "Sending..." with spinner
- Success: toast "Invite sent to priya@partner.org"

Copy: Modal title: "Invite user"
    Email label: "Email address"
    Role label: "Role"
    CTA: "Send invite" / "Cancel"
Trade-off: Single-step form keeps it simple. Role descriptions inline help the Admin make the
right choice without leaving the modal.

### Variant B — Two-step modal (user info → role select)

Layout: Step 1 collects name + email; Step 2 is a full role-picker with detailed descriptions
and capability tables. Progress dots at top. "Next →" / "← Back" / "Send invite".

Trade-off: More deliberate — good if Admins regularly make wrong role choices. But adds
friction that most small NGO admins don't need. Better suited as an onboarding flow for first
few invites, not day-to-day user management.

**Recommended:** Variant A — Single form. Role descriptions inside the dropdown give enough
context. Two-step adds unnecessary length for an admin who already knows their team.

---

## Surface 6: Ownership Transfer

Designer direction: [NEEDS CLARIFICATION] — using best judgment

### Variant A — Modal with user search ← Recommended

Layout: Shadcn Dialog (max-w-md). Triggered from either entry point: resource action menu
(owner or Admin) or Settings > Users delete flow (Admin transfers before deletion).

Entry point 1 (resource action menu): "Transfer ownership" option in the ⋯ menu on a resource.
Entry point 2 (delete user): After Admin clicks "Delete [Name]", if user owns resources, a
blocking step shows the transfer modal before deletion can proceed.

Modal layout:
- Title: "Transfer ownership" (Entry 1) or "Transfer [Name]'s resources" (Entry 2)
- Resource name shown (Entry 1) or list of owned resources (Entry 2 — if >5, show count + scroll)
- "New owner" field: searchable user picker (type to search org members)
- Warning callout: "The new owner will be able to delete this resource."
- CTA: "Transfer" (primary) / "Cancel"
- Entry 2 blocking: "You must transfer all resources before deleting this user." Transfer CTA
  changes to "Transfer and delete" after all resources are assigned.

Copy: Title: "Transfer ownership" / "Transfer [Name]'s resources before deleting their account"
    Warning: "The new owner will be able to delete this resource. This cannot be undone."
    Entry 2 CTA: "Transfer and delete account"
Trade-off: Modal with search scales to any org size. The blocking step on user deletion
ensures no resources become ownerless.

### Variant B — Inline resource-list with per-row owner picker

Layout: Inside the delete confirmation, a full-page list of the user's resources with a
dropdown per resource to assign a new owner. "Confirm all transfers → Delete user" CTA at
bottom.

Trade-off: More visual control for large resource sets, but overwhelming for the typical NGO
admin who just needs to hand off a few dashboards. The modal (Variant A) with a search picker
is more appropriate.

**Recommended:** Variant A — Modal with user search is clean and works for both entry points.
Blocking transfer before deletion is the right default — no orphaned resources.

---

## Surface 7: Data Section — Analyst Read-Only State

Designer direction: [NEEDS CLARIFICATION] — using best judgment

### Variant A — Remove all write actions (no indicator)

Layout: Analyst visits e.g. "Ingest" page. It renders normally — table of sources, filters —
but no "Add source" button, no edit icons on rows, no delete. The absence of controls
communicates read-only implicitly.

Trade-off: Cleanest UI. But Analysts who expect to see write controls will assume the page is
broken, not that they lack permission. No positive confirmation of their access level.

### Variant B — "Read only" badge + remove write actions ← Recommended

Layout: Page header area includes a small "Read only" chip (text-xs, grey, with lock icon)
next to the page title. All Create/Edit/Delete affordances removed. Applies uniformly to all
Data sub-sections (Ingest, Transform, Warehouse, Pipelines, Orchestration).

Key elements:
- Page title: "Ingest" (text-3xl, bold) + "Read only" chip (Lock icon 12px + "Read only" text,
  bg: color-surface, border: color-border, text: color-text-secondary, radius-sm)
- No "Add source" button in the header CTA area
- No edit/delete icons on table rows
- Row hover still shows row-hover bg (table is still readable/interactive for reading)
- Tooltip on the badge (hover): "Your role has read-only access to data infrastructure"

Copy: Badge: "Read only"
    Tooltip: "Your role has read-only access. Contact your admin to make changes."
Trade-off: Persistent badge gives Analysts clear confirmation of their access level. Removes
ambiguity between "broken page" and "intentional read-only". One badge design, applied
uniformly — no need to design each sub-section differently.

### Variant C — Dismissible banner at top of section

Layout: Amber/info-tinted banner pinned below the header: "You have read-only access to Data
infrastructure. Contact your admin to request edit access. [Dismiss ×]"

Trade-off: Most explicit, but feels like an error state for a permanent role property. Analysts
would dismiss it immediately and then wonder again why there are no edit buttons. Noisy for
everyday use.

**Recommended:** Variant B — Badge is the right middle ground. Removes all write actions
cleanly (no confusion about broken UI) while giving a persistent, non-intrusive indication of
why. Apply identically to all Data sub-sections — no per-section variation needed.

---

## Surface 8: Migration Changelog Modal

Designer direction: [NEEDS CLARIFICATION] — using best judgment

### Variant A — One modal, conditional content per role ← Recommended

Layout: Shadcn Dialog (max-w-md). Shown once on first login after migration. Content block
varies by role — same modal structure, different copy. Dismiss button only ("Got it"). No
"Don't show again" toggle (it's already one-time only).

Role: Admin
- Title: "Your Dalgo just got an upgrade"
- Bullet 1: "We've simplified to three roles: Admin, Analyst, and Member"
- Bullet 2: "Your full access is unchanged — you now have formal user management in Settings"
- Bullet 3: "Find all configuration under Settings, including the new Users page"
- CTA: "Go to Settings" (primary) + "Dismiss" (secondary)

Role: Analyst
- Title: "A few things have changed"
- Bullet 1: "You can still build dashboards, charts, and reports as before"
- Bullet 2: "Your access to edit data pipelines and sources is now read-only"
- Bullet 3: "If you need to make pipeline changes, contact your admin"
- CTA: "Dismiss" (single CTA — they go to dashboards)

Role: Member (previously Guest)
- Title: "Welcome to the new Dalgo"
- Bullet 1: "Your account has been updated — everything should look familiar"
- Bullet 2: "You can view all dashboards, charts, and reports"
- Bullet 3: "Your admin controls what you have access to"
- CTA: "Go to dashboards" (primary) + "Dismiss"

Key elements:
- Modal icon: a small Dalgo logo or generic "update" sparkle icon (not an error icon)
- 3 bullets max — no long prose, no tables
- Role-specific CTA helps orient each user
- No "Learn more" link (adds complexity; the bullets cover what matters)

Copy: As above, per role.
Trade-off: One modal component, three content variants. Simple to implement and maintain.
Copy is short enough to hold per-role in a single component.

### Variant B — Three distinct modal designs

Layout: Separate modal designs for Admin, Analyst, Member. Enables more visual differentiation
(e.g., Admin gets a richer design with Settings screenshot).

Trade-off: Triple the design and engineering work for marginal benefit. The content difference
is copy-level, not layout-level — Variant A handles it cleanly.

**Recommended:** Variant A — One modal, three content variants. Short bullet lists, role-
specific CTA. No "Learn more" — the 3 bullets capture everything the user needs to know.

---

## Summary Table

| # | Surface | Recommended | Notes |
|---|---------|-------------|-------|
| 1 | Sidebar — Role-Adaptive Nav | Variant B — Three frames | One per role, footer chip |
| 2 | No Access Page | Variant B — In-shell | Shell visible, recovery CTA |
| 3 | Settings IA | Variant A — Left sub-nav | Full-page takeover, secondary nav |
| 4 | Settings > Users | Variant A — Inline role dropdown | Fast for small teams |
| 5 | Invite User Modal | Variant A — Single form + role descriptions | Simple, inline descriptions |
| 6 | Ownership Transfer | Variant A — Modal + user search | Blocking step on user delete |
| 7 | Data Section (Analyst) | Variant B — Read-only badge | Badge + remove write actions |
| 8 | Migration Changelog | Variant A — Conditional content per role | 3 bullets, role-specific CTA |

To proceed to Figma, either:
- Accept all recommendations: "build the recommended variants"
- Override specific surfaces: "go with Variant C for surface 3, recommended for the rest"

Then re-run: `/design:design-handoff features/access-control/v1/`
(without --brainstorm — the picks will be read from this file)
