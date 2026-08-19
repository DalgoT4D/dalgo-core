# Admin Portal — Product Spec

**Status:** Draft — for team review
**Date:** 2026-07-22 · **Revised:** 2026-07-26 (sign-in reworked to a shared session; sign-out added) · 2026-08-19 (org/user deactivate removed — see note below; notifications scope drops read tracking and an audit trail) · **Tracking:** Issue #1254

**Acronyms:** NGO (non-governmental organization) · CRUD (create, read, update, delete).

> **What this is.** A single place for the Dalgo operations team to run the platform — onboard NGOs, manage their users, message them, turn features on or off per org, and look at their data pipelines to debug — without an engineer running commands by hand.
>
> **Where it lives.** The portal is a section of the existing Dalgo product, reached at `insights.dalgo.org/admin`. `insights.dalgo.org` is the live production address NGO customers already use today; `staging-app.dalgo.org` is its staging counterpart. The portal is **not** a separate website — it is a protected area inside the same product, entered through its own sign-in.

---

## Problem Statement

Every platform-level action at Dalgo today needs an engineer. Creating an NGO account, inviting that NGO's staff, sending an announcement, enabling a feature for one partner, or checking why a partner's data sync failed — each means a developer running a management command or reading server logs by hand.

That is manageable at ~20 partner NGOs. It does not survive the jump to 50+. Every new partner adds routine operational work that only engineers can do, so engineering becomes the bottleneck for growth, and non-engineering operations staff cannot help.

> **The rule:** routine platform operations should be done by the operations team in a screen, not by engineers on a command line.
> **Example:** Today, onboarding the NGO "Akshara" means an engineer runs a create-org command and an invite command. It should mean Meera, on the operations team, filling in a form.
> **Why it matters:** if only engineers can operate the platform, the platform can only grow as fast as engineering has spare time — which is the opposite of what a growing partner base needs.

---

## Target Users

The portal's users are the **Dalgo platform operations team** — staff who work *across all* NGOs, not inside one. This is a different kind of user from the NGO staff who use the main product.

| Persona | Who they are | What they need from the portal |
|---|---|---|
| **Meera — Platform Operations Lead** | Dalgo staff. Onboards partners, manages accounts, sends announcements, controls feature rollout. Comfortable with software, not an engineer. | Do all routine account, user, notification, and feature-flag work herself. |
| **Arjun — Support Engineer** | Dalgo staff. First responder when a partner reports "my data didn't update." | Look at any org's pipeline and sync status/logs to diagnose, without touching that org's account. |

**Two meanings of "admin" — keep them separate.**

> **The rule:** a **platform admin** is Dalgo operations staff who can act across every NGO. An org **Admin** is a role *inside a single NGO* (alongside Analyst and Member). They are unrelated.
> **Example:** Meera is a platform admin — she can open any NGO. Sarah is the org Admin for Akshara — she can only manage Akshara. Sarah is not a platform admin and can never reach the portal.
> **Why it matters:** the portal is only ever for platform admins. Being an org Admin grants nothing here.

NGO staff (like Sarah) are **affected** by the portal — they receive its broadcasts and have features toggled for them — but they are not its users.

---

## Success Metrics

| Outcome | How we'll know |
|---|---|
| Routine operations need no engineer | A new NGO can be onboarded, its users managed, and an announcement sent with **zero** engineering tickets. |
| The platform scales past 50 partners without proportional engineering load | Onboarding and account work per new partner takes roughly the same operations effort at 50 partners as at 20, and does not add engineering effort. |
| Faster onboarding | Time from "we have a new partner" to "their first user is invited" drops from an engineer-scheduled task to same-day self-service. |
| Faster support triage | Support can answer "why didn't this org's data update?" by looking at the portal, instead of asking an engineer to read logs. |
| Safer feature rollout | A new feature can be turned on for one partner to beta-test, with no code release. |

---

## Access & Authentication

The portal always shows its **own sign-in screen**. That screen is a deliberate front door — but it is **not** what keeps people out. The real protection is a platform-admin check the server runs on **every single admin action**.

```
Meera opens insights.dalgo.org/admin
  → the ADMIN sign-in screen always appears (even if she is already signed into Dalgo)
  → she signs in with her normal Dalgo credentials
       → the system checks she has platform-admin privilege
             yes → she enters the portal
             no  → she is refused on the sign-in screen and never gets in
  → every action she takes is re-checked for platform-admin privilege, on the server
```

> **The rule:** one Dalgo account, one session. The admin screen is the doorway; the server-side platform-admin check on every admin action is the lock.
> **Example:** Sarah is the org Admin for Akshara — not a platform admin. She is signed into Dalgo in one tab and opens `/admin` in another. She still sees the admin sign-in. Her password is correct, so the sign-in itself succeeds — and she is then told she is not a platform admin and kept out. If she hand-crafted a direct request to an admin action, the server refuses that too.
> **Why it matters:** the portal can create orgs, message every user, and read every partner's pipeline data. That power must be guarded by a check that cannot be skipped, not by which screen someone happens to open.

**The sign-in screen always appears.**

> **The rule:** `/admin` shows the sign-in screen every time, whether or not you already have a Dalgo session.
> **Example:** Meera is already signed into Dalgo working in a demo org. She opens `/admin` and is asked to sign in again. Doing so simply re-issues her session — nothing is lost and nothing breaks.
> **Why it matters:** entering the portal stays a deliberate act, and it makes plain *which* account you are about to operate the platform as.

**One shared session.**

> **The rule:** the portal and the normal product share a single session. Signing in at the admin screen signs you in everywhere; signing out of the portal signs you out everywhere.
> **Example:** Meera finishes her admin work and clicks "Log out" in the portal sidebar. Her normal Dalgo session in the demo org ends at the same moment — she is signed out of both.
> **Why it matters:** for operations staff on a shared machine, one "Log out" that genuinely ends everything is safer than two sessions that expire independently and leave one quietly open.

One consequence worth knowing: signing in at the admin screen **replaces** whatever session you already had.

> **Example:** Meera is signed in as herself, then signs into the portal using a shared ops account. The normal product now shows the ops account too — not Meera.

For a platform admin who also uses the normal product, the portal offers a plain link back to the main product, and a **"Log out"** control in its sidebar.

---

## Current Build Status

This spec describes the whole portal, but not all of it is new work.

| Capability | Status |
|---|---|
| Organization onboarding + user management | **Built and shipped** — described here as existing product behavior. |
| Admin sign-in + platform-admin gate | **Built and shipped.** Signs in through the shared product login; the platform-admin check runs server-side on every admin action. |
| Sign out of the portal | **Built and shipped.** A "Log out" control in the portal sidebar; ends the shared session everywhere. |
| Broadcast notifications | **Not yet built.** |
| Per-org feature flags | **Not yet built.** |
| Airbyte & pipeline read-only view | **Not yet built.** |

> **Note on an earlier direction.** An earlier draft of this spec described a *separate* admin session — its own login cookie, independent of the normal product. That was built first and then deliberately reversed after review, because a second session added real complexity (a second cookie, a second refresh path, two ways to be signed out) without adding protection the server-side platform-admin check did not already give. The shared-session model above is what ships.
>
> **Note on org/user status, corrected 2026-08-19.** `Org.is_active` and `OrgUser.is_active` — the fields a deactivate/reactivate toggle would have needed — were fully removed from the codebase on 2026-08-19: the model fields, the migration, and the auth-time enforcement that read them are all gone. There is no reversible "pause this org" or "pause this user" control left. Deactivation had been built into the admin API earlier, then deliberately removed; delete was never built at all — it was always a deferred item. What's actually available is described below.

---

## User Flows

Each flow is written as a path through the product: entry → steps → exit, with the important alternate and error paths.

### Flow 1 — Sign in to the portal *(shipped)*

```
Entry: someone opens insights.dalgo.org/admin
  → the admin sign-in screen ALWAYS appears, even with an existing Dalgo session
  → enter normal Dalgo credentials
       valid + platform admin        → enter the portal home
       valid but NOT a platform admin → signed in, but refused entry with a clear
                                        message; the portal never opens
       invalid credentials            → normal "wrong email or password" error
Exit: inside the portal, or refused.
```

Note the middle branch: a non-admin with a correct password **is** signed into Dalgo (one shared session), they are simply not let into the portal. Every admin action would refuse them anyway.

### Flow 1a — Sign out of the portal *(shipped)*

```
Entry: portal sidebar → "Log out"
  → the shared session ends — portal AND normal product
  → back at the admin sign-in screen
       network failure → still signed out locally, still returned to the sign-in screen
Exit: signed out of Dalgo entirely.
```

### Flow 2 — Onboard a new organization *(already shipped)*

```
Entry: portal home → Organizations → "New organization"
  → fill in name, address slug, visualization URL, plan → create
       success → the new org appears in the list, ready for users
       name/slug problem → inline validation error, nothing created
  → open the new org → invite its first user (see Flow 3)
Exit: a new org exists with its first user invited.
```

### Flow 3 — Manage users in an organization *(already shipped)*

```
Entry: Organizations → open an org → Users tab
  → invite a user (email + role: Admin, Analyst, or Member)
  → change an existing user's role
  → remove a user from the org
  → cancel an invitation that hasn't been accepted yet
       removing a user warns first if it would leave their created content without an owner
Exit: the org's members and pending invitations reflect the change.
```

### Flow 4 — Send a broadcast notification *(not yet built)*

```
Entry: portal → Notifications → "New broadcast"
  → write the message (subject + body), mark urgent if needed
  → choose the audience: everyone on the platform, OR everyone in one chosen org
  → the portal shows how many people this will reach
  → choose: send now, or schedule for a later date/time
  → confirm
       send now → recipients get it in their in-app notifications; those with email
                  notifications enabled also get an email
       scheduled → it is queued for the chosen time and shows as "Scheduled"
       empty audience (0 people) → blocked, nothing sends
Exit: the broadcast is sent, or queued as scheduled.
```

### Flow 5 — Review and manage sent broadcasts *(not yet built)*

```
Entry: Notifications → history
  → see past and scheduled broadcasts: message, audience, when, and how many recipients
  → cancel a scheduled broadcast that hasn't sent yet
       a broadcast that has already sent cannot be cancelled or unsent
Exit: the admin knows what was sent, to whom, and when.
```

> **Explicitly excluded.** This version has no read/unread tracking (no "N people have read this") and no audit trail of who sent or scheduled a broadcast. See Scope → Deferred.

### Flow 6 — Turn a feature on or off for an org *(not yet built)*

```
Entry: Organizations → open an org → Feature flags tab (or a portal-wide feature-flags view)
  → see the list of toggleable features and whether each is on or off for THIS org
  → flip a feature on or off for this org
       the change applies only to this org; other orgs are unaffected
Exit: the chosen features are on/off for that org.
```

### Flow 7 — View an org's Airbyte connections and sync logs *(not yet built)*

```
Entry: Organizations → open an org → Airbyte tab
  → see the org's data connections, each with its latest sync status and timing
  → open a connection → see its sync history and the full logs for a run
       read-only: no create, edit, delete, or trigger anywhere on this screen
Exit: the admin has seen the connection health and logs, changed nothing.
```

### Flow 8 — View an org's pipeline runs and logs *(not yet built)*

```
Entry: Organizations → open an org → Pipelines tab
  → see the org's pipeline run history with status and timing
  → open a run → see its full logs
       read-only throughout
Exit: the admin has diagnosed the run, changed nothing.
```

---

## User Stories

### Platform Operations Lead (Meera)

- **As a platform admin, I want the portal to have its own sign-in screen and a server-side privilege check, so that entering it is deliberate and non-admins can never operate it.** *(shipped)*
  - Acceptance: `/admin` always shows its own sign-in, even with an existing Dalgo session; a non–platform-admin who signs in correctly is still refused entry; the server refuses every admin action from anyone lacking the platform-admin flag, including a hand-crafted direct request.

- **As a platform admin, I want to sign out from inside the portal, so that I can end my session on a shared machine without hunting for the normal product's menu.** *(shipped)*
  - Acceptance: a "Log out" control in the portal sidebar ends the shared session everywhere and returns me to the admin sign-in; if the network call fails I am still signed out locally rather than left in a signed-in-looking screen.

- **As a platform admin, I want to create and edit organizations, so that I can onboard partners without an engineer.** *(shipped)*
  - Acceptance: I can create an org (name, slug, visualization URL, plan) and edit it; the slug cannot be changed after creation. There is no deactivate and no delete for an org.

- **As a platform admin, I want to manage the users inside any org, so that I can set up and maintain partner teams.** *(shipped)*
  - Acceptance: I can invite a user at any role (Admin, Analyst, Member), change a role, remove a user from the org, and cancel a pending invitation; removing a user warns me before it orphans content they created. There is no deactivate for a user.

- **As a platform admin, I want to send an announcement to everyone or to one org, so that I can communicate maintenance, outages, and news.**
  - Acceptance: I can pick "whole platform" or one org; I see the recipient count before sending; I can send now or schedule for later; recipients see it in-app and (if opted in) by email; the audience can never be silently empty.

- **As a platform admin, I want to see what I've broadcast, so that I have a record of what was sent, to whom, and when.**
  - Acceptance: a history lists sent and scheduled broadcasts with audience, time, and recipient count; I can cancel a scheduled one before it sends; a sent one cannot be unsent. There is no read/unread tracking and no audit trail of who sent or scheduled it.

- **As a platform admin, I want to turn a feature on or off for a single org, so that I can beta-test with one partner before a wider rollout.**
  - Acceptance: I can set each toggleable feature on or off per org; the change affects only that org; no code release is needed.

### Support Engineer (Arjun)

- **As a support engineer, I want to see any org's connection and sync status with full logs, so that I can diagnose "my data didn't update" myself.**
  - Acceptance: I can view an org's connections, sync history, and complete run logs, read-only; I cannot create, edit, delete, or trigger anything.

- **As a support engineer, I want to see any org's pipeline run history and full logs, so that I can find why a run failed.**
  - Acceptance: I can view runs and their complete logs, read-only.

### NGO staff (affected, not users — e.g. Sarah)

- **As an NGO user, I want platform announcements to reach me where I already see notifications, so that I don't miss maintenance or outage notices.**
  - Acceptance: a broadcast to my org (or the whole platform) appears in my normal in-app notifications, and by email if I have email notifications on — the same place as any other Dalgo notification.

- **As an NGO user, I must never be able to reach the portal, so that platform-wide controls stay with Dalgo operations.**
  - Acceptance: opening the portal address shows me the admin sign-in and refuses me; no admin action is possible with my normal account.

---

## UI Surface

Where the portal lives and the screens it introduces. (Screens for onboarding and user management already exist; the rest are new.)

| Surface | New? | Purpose | Key states |
|---|---|---|---|
| Admin sign-in screen (`insights.dalgo.org/admin`) | Exists | Portal front door; signs in through the shared product login | empty, submitting, refused (not a platform admin), error (bad credentials) |
| Portal home | Exists | Landing overview after sign-in | loading, populated |
| Organizations list | Exists | All orgs, with quick status | loading, empty, populated |
| Organization detail | Exists (gains new tabs) | One org's Overview and Users; **new** Feature flags, Airbyte, and Pipelines tabs | loading, populated, per-tab empty/error |
| New / edit organization form | Exists | Create and edit an org | empty, validation error, saving, saved |
| Users tab (within an org) | Exists | Invite / role / remove / cancel invite | loading, empty, populated, confirm-remove warning |
| Notifications — composer | New | Write, target, preview count, send or schedule | empty, count-loading, confirm, sent, scheduled, blocked-empty-audience |
| Notifications — history | New | Sent + scheduled broadcasts (audience, time, recipient count — no read counts) | loading, empty, populated |
| Feature flags — per org (and a portal-wide view) | New | Toggle features on/off per org | loading, populated |
| Airbyte tab (within an org) | New | Connections, sync status, full logs — read-only | loading, empty, error/partial, populated |
| Pipelines tab (within an org) | New | Run history + full logs — read-only | loading, empty, error/partial, populated |

**Navigation.** The portal has its own left-hand navigation: Home, Organizations, Notifications, Feature flags. Airbyte and Pipelines live as tabs inside an organization, because they are always viewed in the context of one org.

**Read-only surfaces look read-only.**
> **The rule:** the Airbyte and Pipelines screens show status and logs with no action buttons at all — no pause, trigger, edit, or delete.
> **Example:** Arjun opens Akshara's Pipelines tab, reads the failed run's logs, and there is simply nothing on the screen to click that would change anything.
> **Why it matters:** these screens exist to diagnose, not to operate. Absent buttons prevent an accidental change to a partner's live pipeline.

---

## Scope

### In this version

| Capability | Notes |
|---|---|
| Admin sign-in + platform-admin gate | Already shipped. The portal has its own sign-in screen, which always appears; it authenticates through the shared product login, and platform-admin privilege is verified on every admin action server-side. Sign-out from the portal ends the shared session everywhere. |
| Organization onboarding | Already shipped. Create and edit orgs. No deactivate or delete — `Org.is_active` was removed from the codebase (2026-08-19), and delete was never implemented. |
| User management within an org | Already shipped. Invite, change role (Admin / Analyst / Member), remove from org, cancel invitations. No deactivate — `OrgUser.is_active` was removed from the codebase (2026-08-19). |
| Broadcast notifications | New. Anyone with platform-admin access can send. Whole-platform or single-org audience; mandatory recipient-count preview + confirm before anything sends; send now or schedule; cancel a scheduled one; in-app + email delivery; history of past and scheduled broadcasts. No audit trail, no read/unread tracking. |
| Per-org feature flags | New. Turn each toggleable feature on or off, independently per org. |
| Airbyte & pipeline view (read-only) | New. Per-org connection status, sync history, pipeline runs, and full logs. No changes of any kind. |

### Deferred to a later version

| Deferred item | Why |
|---|---|
| A global default for feature flags (set once, override per org) | This version toggles each org independently. A platform-wide default with per-org inheritance is a larger model; deferred until per-org toggling proves the need. |
| Warehouse credential management / key rotation | Sensitive and higher-risk; a separate effort. |
| Platform health dashboard (cross-org metrics) | Wider analytics surface; out of the operational-tasks core. |
| Pipeline controls (pause / resume / cancel / trigger) | This version is strictly read-only for pipelines and connections; controls are a separate, higher-risk step. |
| Superset (visualization tool) management | Out of the operational-tasks core for this version. |
| Advanced analytics and bulk operations | Not part of the routine-operations problem this version solves. |
| Read/unread tracking on broadcasts (e.g. "38 of 42 have read this") | Explicitly dropped. Adds a UI surface and a report with no clear demand yet; the underlying data (`NotificationRecipient.read_status`) exists in the codebase for the main product's notification list, but the admin portal does not expose it. |
| An audit trail of admin actions (who sent a broadcast, who toggled a flag, when) | Explicitly dropped. This version relies on the platform-admin gate on every action, not on a record of who did what; a general audit log is a separate, larger effort. |

> **The rule:** this version replaces the engineer-run command line for **routine** operations; anything sensitive (credentials) or operational-with-consequences (pipeline controls) stays out.
> **Example:** Arjun can *see* that Akshara's sync failed and read the logs, but he cannot *re-run* it from the portal — re-running is deferred.
> **Why it matters:** shipping the read-and-manage core fast is more valuable than waiting to also ship the risky write actions.

---

## Dependencies

Names other product areas this portal relies on or enables — not technologies.

**Requires:**
- **Organization and user management** — already shipped; the onboarding and Users flows are this existing capability, surfaced in the portal.
- **The existing user notification experience** — the in-app notification area and email notifications that NGO users already have. Broadcasts are delivered through that same experience, so recipients see them where they see everything else.

**Enables:**
- A future **platform health dashboard** (cross-org status at a glance) can build on the per-org Airbyte/pipeline views.
- Future **pipeline controls** can extend the read-only Airbyte/Pipelines tabs once the read-only view is trusted.

---

## Handoff Checklist

- [x] The problem and who has it are stated (operations bottleneck as partners scale 20 → 50+).
- [x] Personas are named and distinct (platform operations lead; support engineer; affected NGO staff), and "platform admin" vs org "Admin" is disambiguated.
- [x] Every capability has user flows and acceptance criteria in user-visible terms.
- [x] The access model is specified as behavior: an always-shown sign-in screen over one shared session, server-side verification on every admin action, refusal for non-admins, and a full shared sign-out.
- [x] Build status is explicit per capability (onboarding, sign-in, and sign-out shipped; notifications, feature flags, and the Airbyte/pipeline view still to build).
- [x] Scope is bounded: what's in, what's deferred, and why.
- [x] The four product forks are resolved: notifications = in-app + email with schedule/cancel, no audit trail or read tracking; feature flags = per-org on/off; Airbyte/pipeline view = full logs, read-only.
- [x] Location is fixed: a path (`insights.dalgo.org/admin`) inside the existing production deployment — no separate domain to provision.
- [ ] Team review of this spec before engineering planning begins.

---

## Next

Spec saved to: `features/admin-portal/spec.md`

Onboarding, user management, admin sign-in, and sign-out are all **shipped**. The remaining work is Broadcast notifications, Per-org feature flags, and the read-only Airbyte/pipeline view — planned as Milestones 2–4 in `features/admin-portal/plan.md`.
