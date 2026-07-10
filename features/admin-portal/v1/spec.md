# Platform Admin Portal — v1

**Source**: Implementation Plan v1 (Veekshitha Nelluru, DMP 2026) — the reviewed team plan is the sole scope authority for this spec
**Version**: v1
**Status**: Draft
**Date**: 2026-07-10
**Owner**: Veekshitha Nelluru (DMP 2026) · Issue #1254

> **Acronyms:** NGO (non-governmental organization — Dalgo's partner customers) · ops (the Dalgo operations team that runs the platform across all NGOs).

> **What this is.** A cross-org admin section, at `/admin` inside the existing Dalgo app, for the Dalgo **ops team** to manage NGOs, users, notifications, and feature flags without an engineer running management commands. v1's scope is four features; the **Week 1 build target** is **Org Onboarding + user management**, with the other three sequenced for later.

> **What this is NOT.** This is the *Dalgo ops* portal for running the platform across every NGO. It is **not** the org-Admin Settings area where an NGO's own Admin invites their own team — that lives in access-control (`features/access-control/v2/spec.md`). See [Dependencies](#dependencies).

---

## Scope for this iteration

v1 is the cross-org admin portal defined by four features. Only Super Admins (Dalgo ops) can reach it. The everyday work it unblocks — onboard an org and manage its users with no engineer and no database console — is the **Week 1 build target**; the remaining three features are named here and sequenced for **later** in v1, not cut.

### What's included — v1's four features

| Feature | What it does | Sequencing |
|---|---|---|
| **Org Onboarding** | Create, edit, deactivate/reactivate orgs (permanent delete deferred). Invite users, change roles, deactivate users, remove users from an org, and cancel pending invitations. | **Week 1 — build target** |
| **Broadcast Notifications** | Send platform-wide or org-scoped notifications to all users. | Later |
| **Feature Flags per Org** | Toggle features ON/OFF per org without a code change. | Later |
| **Airbyte & Pipelines** | View connection status, sync logs, and pipeline run history per org. Read-only. | Later |

Across all four, two cross-cutting requirements hold from day one:

- **Admin entry point** — an "Admin Portal" link that appears in the app **only** for Super Admins, leading to a protected `/admin` section. Entering it replaces the normal app navigation with the admin sidebar.
- **Two-layer access protection** — access is enforced in the UI **and** on the server, not UI-only (see [Access model](#access-model)).

### What's out of scope for v1

These are the source plan's explicit exclusions — named so they are deferred, not silently missing:

| Out of scope | Note |
|---|---|
| Warehouse credential management | Its own effort. |
| Platform health dashboard | Its own effort. |
| Pipeline controls — pause, resume, cancel | v1's Airbyte & Pipelines view is read-only. |
| Superset management | Its own effort. |
| Bulk operations / CSV export | Not needed at current scale. |

---

## Problem Statement

**The rule:** The Dalgo ops team runs ~20 partner NGOs and is scaling toward 50+, but every administrative action — onboarding an org, fixing a user, sending a notice, flipping a feature — requires an engineer running a management command. There is no self-service UI.

**Example:** An NGO emails "our new coordinator can't log in." Today an ops teammate who isn't an engineer can't help — they hand it to engineering, who runs a command to find and re-trigger the invite. Onboarding a brand-new NGO is the same story: a developer runs setup commands by hand.

**Why it matters:** Engineer-in-the-loop for every routine action does not scale from 20 to 50+ NGOs. It is slow, error-prone, and it locks non-engineers on the ops team out of work they are otherwise ready to do.

---

## Target Users

The portal has **one persona: the Super Admin** (Dalgo ops). Access is decided by a single flag, `is_platform_admin = True`. No org-level user can reach the portal at all.

| Persona | Who they are | Can access the portal? |
|---|---|---|
| **Super Admin** | A member of the Dalgo ops team, flagged `is_platform_admin = True`. Works across **all** orgs. | ✅ Yes |

**For contrast — these org-level roles do NOT use the portal and never see it:**

| Role | Scope | Can access the portal? |
|---|---|---|
| **Admin** | One org — the NGO's own admin | ❌ No |
| **Analyst** | One org | ❌ No |
| **Member** | One org | ❌ No |

A Super Admin has cross-org reach. An org's Admin, Analyst, or Member is scoped to a single org and cannot open the admin portal — the entry link is never rendered for them, and the server refuses them.

---

## Success Metrics

The source plan states the goal — self-service for the ops team, no engineering involvement — but does not fix numeric targets. These metrics restate that goal in measurable terms; the numeric baselines/targets are to be set with the team (see the handoff note).

| Metric | Direction |
|---|---|
| Routine org and user actions that require an engineer | Drops toward zero for the Week 1 capabilities |
| A new NGO org + its first user onboarded without engineering | Becomes possible for a non-engineer |
| Cross-org visibility for the ops team (orgs, plans, user counts, status in one view) | Goes from none to always-available |
| Ops team can absorb growth from ~20 to 50+ NGOs without proportional engineering load | Supported |

---

## User Flows

Paths through the product, independent of who walks them. All flows below are for the Week 1 build target (Org Onboarding + user management); the three later features add their own flows when they are built.

### Flow A — Enter the admin portal

```
Super Admin is signed into the normal Dalgo app
  -> the "Admin Portal" link is visible in the app sidebar (only because is_platform_admin = True)
  -> click it -> land on /admin
  -> the normal app navigation is fully replaced by the admin sidebar (Home, Organizations, Notifications, Feature Flags)
```
**Denied path:** anyone who is not a Super Admin never sees the link; if they reach an `/admin` URL directly (typed, bookmarked, shared) they are redirected out in the UI and refused by the server.

### Flow B — Dashboard at a glance

```
/admin
  -> stat cards: Total Orgs, Total Users, Notifications Sent, Feature Flags ON
  -> Recent Organizations list (name, status, user count, plan)
  -> click an org -> its org detail
```

### Flow C — Browse and find an org

```
Organizations
  -> table of every org (name, plan, users, status)
  -> search by name
  -> filter
  -> click an org -> org detail
  -> "Create New Org" is available from this page
```

### Flow D — Create an org

```
Organizations -> "Create New Org"
  -> fill the create-org form
  -> confirm
  -> the new org is created and appears in the directory
```

### Flow E — Manage the users inside an org

```
Org detail -> Users tab -> list of users and pending invites (email, role, status incl. Pending)
  -> Invite user       -> enter email + role -> Send Invite
  -> Change role       -> pick a new role -> confirm
  -> Deactivate user   -> confirm -> user can no longer log in
  -> Remove user       -> confirm -> user is detached from the org
  -> Cancel invitation -> confirm -> a pending invite is withdrawn
  -> the affected row updates in place
```

### Flow F — Retire an org (deactivate / reactivate)

```
Org detail
  -> Edit          -> change the org's basic details
  -> Deactivate    -> confirm -> org becomes inactive; its users can no longer log in; data retained
  -> Reactivate    -> org returns to active; its users can log in again

```
**Guardrail:** deactivation is reversible and is the everyday "pause" action for this org — it never deletes data.

*(Deferred — later slice) Permanent delete, with a cascade-aware confirmation showing everything that would be destroyed, is not part of Week 1.)*

---

## Access model

Two layers protect the portal, and both are required — the plan calls them out by name:

| Layer | Where | Behavior |
|---|---|---|
| **AdminGuard** | Front end — wraps all `/admin/*` pages | Checks `is_platform_admin`. If not a Super Admin, redirects to `/`. The "Admin Portal" entry link is conditionally rendered, so non-admins never see it. |
| **API check** | Back end — every admin request | Checks `is_platform_admin`. If not a Super Admin, returns **403**. |

The key requirement: access is **not** UI-only hiding. A non–Super Admin who bypasses the UI is still refused by the server.

---

## User Stories

All stories are for the **Super Admin** persona and cover the Week 1 build target.

### Access & navigation

**Story 1 — Reach the portal, and only if I'm allowed**
**As** a Super Admin, **I want** an admin entry point only I can see and open, **so that** I can manage the platform while NGO users never encounter it.

**Acceptance criteria:**
- [ ] The "Admin Portal" sidebar link appears only when `is_platform_admin = True`; every other user sees no link or hint of it.
- [ ] Opening the portal takes me to `/admin` and replaces the normal app navigation with the admin sidebar (Home, Organizations, Notifications, Feature Flags).
- [ ] A non–Super Admin who navigates directly to any `/admin` URL is redirected away in the UI (AdminGuard) **and** refused by the server with a 403 — access is denied on the backend, not merely hidden.

### Dashboard

**Story 2 — See the platform at a glance**
**As** a Super Admin, **I want** a dashboard with headline numbers and recent orgs, **so that** I'm oriented the moment I arrive.

**Acceptance criteria:**
- [ ] The dashboard shows four stat cards: Total Orgs, Total Users, Notifications Sent, Feature Flags ON.
- [ ] It shows a Recent Organizations table with name, status, user count, and plan.
- [ ] Clicking an org in that table opens its detail page.

### Organizations

**Story 3 — Find any org**
**As** a Super Admin, **I want** a searchable, filterable directory of all orgs, **so that** I can get to the one I need fast.

**Acceptance criteria:**
- [ ] The directory lists every org with Name, Plan, Users, and Status, plus a per-row actions menu.
- [ ] I can search orgs by name.
- [ ] I can filter the list.
- [ ] A "Create New Org" action is available on this page.
- [ ] Clicking an org opens its detail page.

**Story 4 — Create an org**
**As** a Super Admin, **I want** to create a new org from a form, **so that** onboarding a new NGO doesn't need an engineer.

**Acceptance criteria:**
- [ ] I can create an org from the create-org form.
- [ ] The new org appears in the directory after creation.

**Story 5 — Open one org's detail**
**As** a Super Admin, **I want** a per-org page organized into tabs, **so that** I can see and act on one org in context.

**Acceptance criteria:**
- [ ] The org detail page shows the org name, a back link to the directory, and four tabs: Overview, Users, Airbyte, Pipelines.
- [ ] The **Users** tab is fully functional (Story 6).
- [ ] I can edit the org's basic details and deactivate or reactivate the org from this page (Story 7).

### Users

**Story 6 — Manage any org's users**
**As** a Super Admin, **I want** to manage the users inside any org, **so that** I can resolve access and onboarding tickets in minutes.

**Acceptance criteria:**
- [ ] The Users tab lists every user with Email, Role, and Status, including **Pending** invitations.
- [ ] I can invite a user by email with a chosen role (Invite User dialog: email field + role dropdown + Send Invite).
- [ ] I can change a user's role (Change Role dialog).
- [ ] I can deactivate a user so they can no longer log in.
- [ ] I can remove a user from the org.
- [ ] I can cancel a pending invitation.
- [ ] Each action updates the affected row in place.

### Org lifecycle

**Story 7 — Edit and deactivate an org**
**As** a Super Admin, **I want** to edit and pause an org safely, so that onboarding or offboarding an NGO doesn't mean hand-editing data.

**Acceptance criteria:**

- [ ] I can edit an org's basic details.
- [ ] I can deactivate an org: it becomes inactive, its users can no longer log in, and its data is retained. This is reversible.
- [ ] I can reactivate an inactive org back to active.

(Deferred — later slice) Permanent org delete, with a cascade-aware confirmation showing users, Airbyte connections, and pipeline runs that would be destroyed.

---

## UI Surface

**Where it lives:** a protected `/admin` section **inside the existing Dalgo app** (same login, same design system, not a separate application), reachable only by Super Admins. Entering it replaces the app's normal navigation with the admin sidebar.

### Routes

| Route | What's on the page |
|---|---|
| `/admin` | Dashboard — stat cards + recent organizations |
| `/admin/organizations` | List of all orgs with search and filters |
| `/admin/organizations/new` | Create-org form |
| `/admin/organizations/[id]` | Org detail — tabs: Overview, Users, Airbyte, Pipelines |
| `/admin/notifications` | Broadcast notifications (Later) |
| `/admin/feature-flags` | Feature flag toggles — global + per-org (Later) |

### Screens & components

| Surface | What it shows | Key states |
|---|---|---|
| **Admin entry link** | An "Admin Portal" link in the main app sidebar, visible only to Super Admins. | Visible (Super Admin) / absent (everyone else). |
| **Admin sidebar** | Persistent sidebar for `/admin/*`: Home, Organizations, Notifications, Feature Flags. Replaces the app's normal nav on entry. | — |
| **Dashboard** (`/admin`) | Four stat cards (Total Orgs, Total Users, Notifications Sent, Feature Flags ON) + Recent Organizations table (name, status, user count, plan). | Loading, populated, error. |
| **Organizations list** (`/admin/organizations`) | "Create New Org" button + search bar + table (Name, Plan, Users, Status, actions menu). | Loading, populated, filtered, error. |
| **Create org** (`/admin/organizations/new`) | Create-org form. | Default, validating, success, error. |
| **Org detail** (`/admin/organizations/[id]`) | Back link + org name + tabs Overview / Users / Airbyte / Pipelines; "Invite User" button on the Users tab; users table (Email, Role, Status incl. Pending, actions menu). | Loading, populated, error; Airbyte & Pipelines tabs correspond to the Later feature. |
| **Invite User dialog** | Email field + Role dropdown; Cancel / Send Invite. | Default, sending, success, error. |
| **Change Role dialog** | Role dropdown; Cancel / Confirm. | Default, confirming, success, error. |
| **Delete Org dialog** | Deferred — later slice. Warning icon + org name + cascade list of what will also be deleted (users, Airbyte connections, pipeline runs); Cancel / Delete Permanently. | Deferred |

### Navigation transition (entry behavior)

The standard Dalgo app sidebar (Impact, KPIs, Charts, Dashboard, Data, Settings) shows a **"👑 Admin Portal"** link at the bottom — only for `is_platform_admin` accounts. Clicking it **fully replaces** the global app navigation with the admin sidebar (Home, Organizations, Notifications, Feature Flags). The entry point is restricted to Super Admin accounts; regular users never see the link.

---

## Dependencies

- **Relationship to access-control (`features/access-control/v2/spec.md`):** that feature owns the **org-Admin Settings > Users** area, where an NGO's own Admin manages their own team using the org roles **Admin / Analyst / Member** (scoped to that one org). This portal is the **Dalgo-ops, cross-org** layer above it.
  - **Boundary rule:** when this portal invites a user or changes a role inside an org, it uses **that org's existing role model (Admin / Analyst / Member)** as defined in access-control v2. It does **not** introduce new org-level roles. The Super Admin tier it relies on — the `is_platform_admin` flag — is a **separate, Dalgo-staff-only** concept that sits outside those three org roles.
- **Requires:** the existing Org, user, invitation, and role concepts, and the existing `is_platform_admin` flag that marks a Super Admin.
- **Enables:** the three later v1 features — Broadcast Notifications, Feature Flags per Org, and the read-only Airbyte & Pipelines viewer — all hang off the org directory and org-detail surface this Week 1 slice builds.

---

## Handoff Checklist

- [x] Single Super Admin persona (`is_platform_admin = True`) defined; the three org roles (Admin / Analyst / Member) are explicitly excluded from the portal.
- [x] v1 scope stated as four features, with Org Onboarding as the Week 1 build target and the other three sequenced as Later.
- [x] Two-layer access protection captured as a requirement (AdminGuard in the UI **and** a server 403), server-enforced, not UI-only.
- [x] Route structure and UI surface enumerated per the source plan's mockups; no cards or tabs added beyond what the plan specifies.
- [x] Org deactivation is reversible; permanent delete is explicitly deferred to a later slice (not Week 1).
- [x] Boundary with access-control stated against what that spec actually defines, to prevent overlap.
- [x] "Out of scope for v1" matches the source plan exactly.
- [ ] **Team to confirm before planning** — a few points were not fixed by the source plan; each is listed for resolution below rather than invented into the spec.

### For the team to confirm (not resolved by the source plan)

- **Create-org + first user:** the plan's create-org form and the "invite user" action are separate; the create-org form's exact fields (and whether it also invites a first user) are not specified. This spec models create-org as creating the org, with user invites on the Users tab. Confirm the create form's fields (name, slug, visualization URL, plan per the issue) and whether it captures a first user.
- **Dashboard "Notifications Sent" / "Feature Flags ON" cards:** these appear in the plan's dashboard mockup, but their underlying features are sequenced as Later. Confirm whether these two cards render (e.g. as zero/placeholder) in the Week 1 build, or appear only when those features ship.
- **Overview tab contents:** the plan lists Overview as a tab but does not specify what it shows. Confirm its fields (assumed: org name, plan, status, user count).
- **Org list filter dimension:** the plan says the list has "search and filters" without naming the filter; confirm (assumed: filter by status).
- **Success-metric targets:** the plan gives no numeric baselines/targets; confirm the numbers for the metrics above.

---

## Next

`/engineering/plan-feature features/admin-portal/v1/spec.md`
