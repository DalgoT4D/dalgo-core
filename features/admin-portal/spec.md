# Admin Portal — Product Spec

**Status:** Draft — for team review
**Date:** 2026-07-22 · **Tracking:** Issue #1254

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

The portal has its **own sign-in, separate from the normal product login**. Being signed into Dalgo as a regular user does not let you into the portal, and being signed into the portal does not sign you into the normal product.

```
Meera opens insights.dalgo.org/admin
  → she sees the ADMIN sign-in screen (separate from the normal Dalgo login)
  → she signs in with her credentials
       → the system checks she has platform-admin privilege
             yes → she enters the portal
             no  → she is refused right at the sign-in screen
  → every action she takes is re-checked for platform-admin privilege
```

> **The rule:** entering the portal is a deliberate, separate sign-in. A normal Dalgo session never counts as portal access, and the check happens on the server for every admin action — not just in the screen.
> **Example:** Sarah (org Admin, not a platform admin) is signed into Dalgo in one tab. She opens `insights.dalgo.org/admin` in another. She is still shown the admin sign-in, and when she tries her credentials she is refused, because she is not a platform admin. Even if she crafted a direct request to an admin action, the server refuses it.
> **Why it matters:** the portal can create orgs, message every user, and read every partner's pipeline data. That power must sit behind its own verified door, not be a side effect of any ordinary login.

**Independent sessions.**

> **The rule:** signing out of the portal does not sign you out of the normal product, and vice versa. The two sessions are separate.
> **Example:** Meera also belongs to a demo org as a normal user. She signs out of the portal at the end of the day; her normal Dalgo session in the demo org is untouched.
> **Why it matters:** operations staff who also use the product normally should not have the two roles bleed into each other.

For a platform admin who also uses the normal product, the portal offers a plain link back to the main product. It is a convenience link, not a shared session.

---

## Current Build Status

This spec describes the whole portal, but not all of it is new work.

| Capability | Status |
|---|---|
| Organization onboarding + user management | **Already built and shipped** — described here as existing product behavior. |
| Independent admin sign-in | **Not yet built.** |
| Broadcast notifications | **Not yet built.** |
| Per-org feature flags | **Not yet built.** |
| Airbyte & pipeline read-only view | **Not yet built.** |

---

## User Flows

Each flow is written as a path through the product: entry → steps → exit, with the important alternate and error paths.

### Flow 1 — Sign in to the portal *(not yet built)*

```
Entry: someone opens insights.dalgo.org/admin
  → admin sign-in screen (separate from the normal login)
  → enter credentials
       valid + platform admin → enter the portal home
       valid but NOT a platform admin → refused at the sign-in screen with a clear message
       invalid credentials → normal "wrong email or password" error
Exit: inside the portal, or refused.
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
  → deactivate or remove a user
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
  → see past and scheduled broadcasts: message, audience, when, how many recipients,
    and how many have read it
  → cancel a scheduled broadcast that hasn't sent yet
       a broadcast that has already sent cannot be cancelled or unsent
Exit: the admin knows what was sent, to whom, and how many read it.
```

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

- **As a platform admin, I want to sign in through a portal-only login, so that portal access is deliberate and never a by-product of an ordinary Dalgo session.**
  - Acceptance: the portal shows its own sign-in; a normal Dalgo session does not grant entry; a non–platform-admin is refused at sign-in; the server refuses any admin action that does not come from a verified platform-admin session, even a direct one.

- **As a platform admin, I want to create and edit organizations, so that I can onboard partners without an engineer.** *(shipped)*
  - Acceptance: I can create an org (name, slug, visualization URL, plan), edit it, and deactivate/delete it; the slug cannot be changed after creation.

- **As a platform admin, I want to manage the users inside any org, so that I can set up and maintain partner teams.** *(shipped)*
  - Acceptance: I can invite a user at any role (Admin, Analyst, Member), change a role, deactivate/remove a user, and cancel a pending invitation; removing a user warns me before it orphans content they created.

- **As a platform admin, I want to send an announcement to everyone or to one org, so that I can communicate maintenance, outages, and news.**
  - Acceptance: I can pick "whole platform" or one org; I see the recipient count before sending; I can send now or schedule for later; recipients see it in-app and (if opted in) by email; the audience can never be silently empty.

- **As a platform admin, I want to see what I've broadcast and how many read it, so that I have a record and can judge reach.**
  - Acceptance: a history lists sent and scheduled broadcasts with audience, time, recipient count, and read count; I can cancel a scheduled one before it sends; a sent one cannot be unsent.

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
| Admin sign-in screen (`insights.dalgo.org/admin`) | New | Portal-only login | empty, submitting, refused (not a platform admin), error (bad credentials) |
| Portal home | Exists | Landing overview after sign-in | loading, populated |
| Organizations list | Exists | All orgs, with quick status | loading, empty, populated |
| Organization detail | Exists (gains new tabs) | One org's Overview and Users; **new** Feature flags, Airbyte, and Pipelines tabs | loading, populated, per-tab empty/error |
| New / edit organization form | Exists | Create and edit an org | empty, validation error, saving, saved |
| Users tab (within an org) | Exists | Invite / role / deactivate / remove / cancel invite | loading, empty, populated, confirm-remove warning |
| Notifications — composer | New | Write, target, preview count, send or schedule | empty, count-loading, confirm, sent, scheduled, blocked-empty-audience |
| Notifications — history | New | Sent + scheduled broadcasts with read counts | loading, empty, populated |
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
| Independent admin sign-in | New. Portal-only login; platform-admin privilege verified at sign-in and on every admin action; sessions separate from the normal product. |
| Organization onboarding | Already shipped. Full CRUD on orgs (create, edit, deactivate/delete). |
| User management within an org | Already shipped. Invite, change role (Admin / Analyst / Member), deactivate/remove, cancel invitations. |
| Broadcast notifications | New. Whole-platform or single-org audience; recipient count before send; send now or schedule; cancel a scheduled one; in-app + email delivery; history with read counts. |
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
- [x] The access model is specified as behavior: separate sign-in, separate session, server-side verification on every admin action, refusal for non-admins.
- [x] Build status is explicit per capability (onboarding shipped; the rest and the independent login new).
- [x] Scope is bounded: what's in, what's deferred, and why.
- [x] The four product forks are resolved: notifications = in-app + email with schedule/cancel + read-count history; feature flags = per-org on/off; Airbyte/pipeline view = full logs, read-only.
- [x] Location is fixed: a path (`insights.dalgo.org/admin`) inside the existing production deployment — no separate domain to provision.
- [ ] Team review of this spec before engineering planning begins.

---

## Next

Spec saved to: `features/admin-portal/spec.md`

Next: `/engineering/plan-feature features/admin-portal/spec.md` — produces `research.md` (a fresh read of the current DDP_backend and webapp_v2 code) and `plan.md` (with the mandatory Blast Radius step against `docs/domain-map.md`). The independent admin sign-in is the main piece of new backend work; onboarding and user management are already-shipped context, not new milestones.
