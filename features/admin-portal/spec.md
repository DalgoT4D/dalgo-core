# Platform Admin Portal — Feature Spec

**Status**: Draft (full vision)
**Date**: 2026-07-02
**Owner**: Dalgo platform team

> **Acronyms used in this doc:** NGO (non-governmental organization — Dalgo's partner customers) · M&E (monitoring & evaluation — the NGO team that tracks program outcomes) · SLA (service-level agreement — the response time the Dalgo team promises).

> **What this is NOT:** This is the *Dalgo staff* portal for running the platform across every NGO. It is **not** the org-Admin Settings area (invite my own team, edit my org name) — that lives in the **access-control v2** spec (`features/access-control/v2/spec.md`, the Settings > Users / Groups / Warehouse area gated to an org's own Admin). See [Dependencies](#dependencies) for the boundary.

---

## Problem Statement

**The rule:** The Dalgo team runs ~20 partner NGOs but has no single place to see or manage them — every support and onboarding task means opening the database, a Django shell, or asking the NGO to do it themselves.
**Example:** An NGO called Akshara emails "Priya can't log into Dalgo." Today Meera (Dalgo support) has no screen that shows Akshara's users. She opens a database console, finds Priya's invite row by hand, and re-triggers it via a script. Onboarding a brand-new NGO is the same story — a developer runs setup commands by hand.
**Why it matters:** A small team can't scale support and onboarding across 20+ NGOs on database consoles and tribal knowledge. Every manual task is slow, error-prone, and needs an engineer — so non-engineers on the team can't help at all.

The specific gaps this portal fixes:

| # | Gap today | Who feels it |
|---|-----------|-------------|
| 1 | No cross-org view. You can't see all NGOs, their health, or which ones are failing, in one place. | Whole Dalgo team |
| 2 | Support tasks need a database console or a script. Non-engineers can't help a stuck NGO user. | Meera (support) |
| 3 | Onboarding a new NGO is a manual, developer-only setup. | Arjun (onboarding) |
| 4 | No safe way to suspend an NGO (offboarding, non-payment) without hand-editing data. | Arjun (onboarding) |
| 5 | No record of who on the Dalgo team did what to which NGO. | Ravi (superadmin) |

---

## Target Users

The users of this portal are **Dalgo employees only**. NGO staff (Sarah, Priya, James) never see it and never know it exists.

| Persona | Real-world context | What they need from the portal |
|---------|-------------------|-------------------------------|
| **Meera** — Dalgo Support | First responder to NGO support tickets. Not always an engineer. | Find any NGO's users; resend an invite, reset access, change a role, remove someone. |
| **Arjun** — Dalgo Onboarding / Ops | Brings new NGOs onto the platform; offboards ones that leave. | Create a new org, suspend an org, reactivate it, archive it. |
| **Ravi** — Dalgo Superadmin | Owns platform governance and security. Manages the Dalgo staff list. | See everything; control who is a platform admin; review the action log. |

**The NGO-side personas (for contrast — these people do NOT use the portal):**

| Persona | Role in their NGO | Where they work instead |
|---------|-------------------|------------------------|
| **Sarah** | Org Admin at one NGO | Her own **Settings > Users** (access-control v2), not this portal. |
| **Priya** | Analyst / M&E Officer | The main Dalgo app for her org. |
| **James** | Member / viewer | The main Dalgo app, view-only. |

---

## Success Metrics

| Metric | Baseline (today) | Target |
|--------|-----------------|--------|
| Median time to resolve a "user can't log in" ticket | Hours (needs an engineer + DB console) | Under 5 minutes (Meera self-serves) |
| Support tasks that require an engineer | ~All user/org tasks | Near zero for routine user + org actions |
| Time to onboard a new NGO's org shell | Manual, developer-run (varies) | Minutes, done by a non-engineer |
| Cross-org health visibility | None | Every platform admin can see all orgs + failing pipelines in one view |
| Platform actions with an accountable record | 0% | 100% (every action logged: who, what, when) |

---

## User Flows

Written as paths through the product, independent of who walks them.

### Flow A — See all orgs and drill into one

```
open portal
   -> Org directory: table of every org (name, users, warehouse, last sync, status)
   -> sort/filter (e.g. status = FAILING)
   -> click an org
   -> Org detail: users list + health panel + lifecycle actions
```

**Alternate / empty:** brand-new platform with no orgs yet → directory shows an empty state with a "Create org" call to action.

### Flow B — Fix a stuck NGO user (support)

```
Org directory -> open the org -> Users tab
   -> find the user by name/email
   -> choose an action: resend invite | change role | remove user | add user
   -> confirm -> action runs -> row updates -> entry written to the action log
```

**Error path:** the action fails (e.g. the org's warehouse is unreachable) → a clear error explains what failed and that nothing was changed.

### Flow C — Onboard a new NGO

```
Org directory -> "Create org"
   -> enter org name, plan tier, warehouse type
   -> enter the first Admin's email
   -> confirm
   -> org is created + first Admin is invited (as that org's Admin)
   -> new org appears in the directory -> action logged
```

### Flow D — Suspend / reactivate / archive an org

```
Org detail -> lifecycle menu
   -> Suspend  -> confirm (typed org name) -> org users can no longer log in; data + pipelines paused
   -> Reactivate -> org returns to active
   -> Archive  -> confirm (typed org name) -> org removed from the active list, data retained
```

**Guardrail:** suspend, archive, and any destructive action require typing the org name to confirm — no single-click destruction.

### Flow E — Manage who is a platform admin (superadmin only)

```
Portal -> Platform Staff
   -> list current platform admins
   -> add a Dalgo staff member by email | remove one
   -> confirm -> action logged
```

**Guardrail:** only the superadmin sees this screen. A platform admin cannot add or remove other platform admins.

---

## User Stories

### Meera (Dalgo Support)

**Story 1 — See every org and its health**
**As** Meera, **I want** one directory of all NGOs with health signals, **so that** I can triage without asking anyone or opening a database.

**Acceptance criteria:**
- [ ] The directory lists every org with: name, user count, warehouse type, last pipeline run time, and a status (Active / Suspended / Failing).
- [ ] I can sort and filter (e.g. show only Failing, or only Suspended).
- [ ] "Failing" means the org's most recent pipeline run failed; the signal is visible without opening the org.
- [ ] Clicking an org opens its detail view.

**Story 2 — Manage any org's users**
**As** Meera, **I want** to act on any NGO's users, **so that** I can resolve access tickets in minutes.

**Acceptance criteria:**
- [ ] In an org's Users tab I see every user with role, status (invited / active), and last active time.
- [ ] I can resend an invitation to a user who never accepted.
- [ ] I can change a user's role and remove a user.
- [ ] I can add a new user to the org with a role.
- [ ] I cannot see the NGO's actual data (dashboards, warehouse rows) — only user records. Seeing-as-the-user is out of scope (see [Scope](#scope)).
- [ ] Every action I take is recorded in the action log.

### Arjun (Dalgo Onboarding / Ops)

**Story 3 — Create a new org**
**As** Arjun, **I want** to create an org from the portal, **so that** onboarding a new NGO doesn't need a developer.

**Acceptance criteria:**
- [ ] I can create an org by entering: org name, plan tier, and warehouse type.
- [ ] I enter the first Admin's email; that person is invited as the new org's Admin.
- [ ] The new org appears in the directory immediately.
- [ ] Creation is recorded in the action log.

**Story 4 — Suspend, reactivate, and archive an org**
**As** Arjun, **I want** to change an org's lifecycle state safely, **so that** offboarding or pausing an NGO doesn't mean hand-editing data.

**Acceptance criteria:**
- [ ] I can suspend an org: its users can no longer log in, and its pipelines are paused. Data is retained.
- [ ] I can reactivate a suspended org back to Active.
- [ ] I can archive an org: it leaves the active directory list but its data is retained.
- [ ] Suspend, archive, and any destructive action require typing the org's name to confirm.
- [ ] Each lifecycle change is recorded in the action log.

### Ravi (Dalgo Superadmin)

**Story 5 — Control who is a platform admin**
**As** Ravi, **I want** to manage the Dalgo staff who can reach this portal, **so that** cross-org access stays tightly held.

**Acceptance criteria:**
- [ ] I can see the list of current platform admins.
- [ ] I can add or remove a platform admin by email.
- [ ] Only I (the superadmin) can see and use the Platform Staff screen; ordinary platform admins cannot.
- [ ] Adding/removing a platform admin is recorded in the action log.

**Story 6 — Review the action log**
**As** Ravi, **I want** a record of every platform action, **so that** cross-org power is accountable.

**Acceptance criteria:**
- [ ] Every portal action (user change, org lifecycle change, staff change) writes a log entry: who, what, which org/user, and when.
- [ ] I can view the log and filter it by org, by actor, and by action type.
- [ ] Log entries cannot be edited or deleted from the portal.

### All platform admins

**Story 7 — The portal is invisible to NGOs**
**As** a platform admin, **I want** the portal to be completely hidden from NGO users, **so that** an org Admin like Sarah never sees or reaches platform tooling.

**Acceptance criteria:**
- [ ] No NGO user (Admin, Analyst, or Member) sees any link, nav item, or route to the portal.
- [ ] A non-platform-admin who somehow reaches a portal URL is denied — the server refuses, not just the UI hiding it.

---

## UI Surface

**Where it lives:** a dedicated Dalgo-staff portal, separate from any single NGO's app. Only platform admins can reach it. (Whether it's a separate address or a gated section is an engineering choice — the spec only requires it be invisible and inaccessible to NGO users.)

| Surface | What it shows | Key states |
|---------|--------------|-----------|
| **Org directory** | Table of all orgs: name, users, warehouse, last sync, status. Sort + filter. "Create org" button. | Empty (no orgs), populated, filtered, loading, error. |
| **Org detail** | One org's Users tab + health panel + lifecycle menu (suspend / reactivate / archive). | Loading, active org, suspended org, archived org, error. |
| **Create-org flow** | Form: org name, plan tier, warehouse type, first Admin email. | Default, validating, success, error (e.g. name taken). |
| **User action dialogs** | Resend invite / change role / remove / add user, with confirmation. | Default, confirm, success, error. |
| **Destructive confirmations** | Suspend / archive: require typing the org name. | Default, name-mismatch (button disabled), confirmed. |
| **Platform Staff** (superadmin only) | List of platform admins; add/remove by email. | Populated, add, remove, error. Hidden entirely from non-superadmins. |
| **Action log** | Chronological record: actor, action, target org/user, time. Filterable. | Empty, populated, filtered, loading. |

---

## Scope

### In scope — v1

- **Org directory + health** — one list of all orgs with health signals; drill into org detail.
- **Cross-org user management** — view and act on any org's users: resend invite, change role, remove, add. Records only — no seeing the NGO's data.
- **Org lifecycle** — create (with first-Admin invite), suspend, reactivate, archive.
- **Platform-admin access model** — a small, fixed list of Dalgo staff as platform admins; one superadmin manages that list. Flat (no tiers).
- **Action log** — every platform action recorded (who, what, when), viewable and filterable. Included in v1 because a cross-org admin tool is unsafe without accountability, and the log is cheap next to the actions it guards.
- **Server-side gating** — the portal is refused to any non-platform-admin at the server, not just hidden in the UI.

### Out of scope — deferred to later versions

| Deferred item | Why deferred | Likely version |
|---------------|-------------|---------------|
| **Impersonation ("view as" / "log in as" an NGO user)** | Sensitive — staff would see an NGO's real data. Needs an audit + consent story before it's safe. | v2 |
| **Usage / adoption metrics** (active orgs, logins, dashboards created, at-risk NGOs) | Valuable but not blocking day-one support/onboarding. Best built once the directory exists to hang it on. | v2 |
| **Tiered platform roles** (e.g. support can reset users but not provision orgs) | v1's flat staff list is simpler and safe for a ~5-person team. Add tiers when the team grows. | v2+ |
| **Hard delete / data purge of an org** | Destructive and donor-compliance-sensitive. v1 stops at archive (soft). Purge needs a dedicated compliance flow. | Later |
| **Billing / plan management beyond a plan-tier label** | Out of the support/onboarding core. | Later |
| **Bulk actions** (suspend many orgs, bulk user import) | Not needed at 20 orgs. | Later |

---

## Dependencies

- **Relationship to access-control (`features/access-control/v2/spec.md`):** That feature owns the **org-Admin** Settings area — an NGO Admin (Sarah) inviting *her own* team, roles Admin/Analyst/Member, groups, warehouse config. This portal is the **Dalgo-staff, cross-org** layer above it.
  - **Boundary rule:** when this portal invites or changes a user inside an org, it uses that org's own role model (whatever access-control defines at the time). This portal does not add new *org-level* roles; it defines a separate *platform-admin* tier that only Dalgo staff hold.
- **Requires:** the concept of an Org and its users/roles (already in the platform). The action log and the platform-admin tier are new to this feature.
- **Enables:** v2 impersonation and usage-metrics both hang off the org directory this version builds.

---

## Handoff Checklist

- [x] Problem clearly defined with concrete, named examples.
- [x] Target users identified — and it's explicit that NGO users never touch this.
- [x] Success metrics defined and measurable.
- [x] User flows written persona-agnostic; user stories persona-driven with acceptance criteria.
- [x] UI surface enumerated with states.
- [x] Scope split cleanly into v1 vs deferred, each with a reason.
- [x] Boundary with access-control v2 stated explicitly to prevent overlap.
- [x] No open questions left — impersonation, metrics, tiers, and hard-delete are all resolved as deferred with rationale.
- [ ] Team review of the v1 slice before scoping `v1/spec.md`.
