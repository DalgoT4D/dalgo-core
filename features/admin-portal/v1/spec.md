# Platform Admin Portal — v1

**Scoped from**: ../spec.md
**Version**: v1
**Status**: Draft
**Date**: 2026-07-02

> **Acronyms used in this doc:** NGO (non-governmental organization — Dalgo's partner customers) · M&E (monitoring & evaluation — the NGO team that tracks program outcomes).

> **Who uses this:** Dalgo employees only. NGO staff (Sarah, Priya, James) never see it. The org-Admin's own Settings area (invite my team, edit my org) is a *different* feature — access-control v2 (`features/access-control/v2/spec.md`).

---

## Scope for this iteration

v1 is the **support-and-onboarding console**: one cross-org view, the power to fix any org's users, the power to create and pause orgs, held by a small fixed group of Dalgo staff, with every action recorded.

### What's included

- **Org directory + health** — one list of every org with health signals; click through to org detail.
- **Cross-org user management** — on any org: resend invite, change role, remove user, add user. Records only — no seeing the NGO's data.
- **Org lifecycle** — create an org (shell + invite first Admin), suspend, reactivate, archive.
- **Platform-admin access** — a small fixed list of Dalgo staff. One superadmin manages that list. Flat, no tiers.
- **Action log** — every portal action recorded (who, what, target, when); viewable and filterable.
- **Server-side gating** — a non-platform-admin is refused at the server, not just hidden in the UI.

### What's deferred to later versions

| Deferred item | Where it goes | Why deferred |
|---|---|---|
| **Impersonation** ("view as" / "log in as" an NGO user) | v2 | Staff would see an NGO's real data — needs an audit + consent story first. |
| **Usage / adoption metrics** (active orgs, logins, at-risk NGOs) | v2 | Not blocking day-one support/onboarding. Hangs off the v1 directory once it exists. |
| **Tiered platform roles** (support vs ops vs superadmin powers) | v2+ | v1's flat staff list is safe for a ~5-person team. |
| **Deep warehouse/pipeline provisioning at create-org** | v2+ | v1 create-org makes the org shell + invites the first Admin. Warehouse setup uses the org's existing setup flow — v1 does not reimplement Airbyte/dbt provisioning. |
| **Hard delete / data purge of an org** | Later | Destructive and donor-compliance-sensitive. v1 stops at archive (soft). |
| **Billing / plan management** beyond a plan-tier label | Later | Out of the support/onboarding core. |
| **Bulk actions** | Later | Not needed at ~20 orgs. |

---

## Problem Statement

**The rule:** The Dalgo team runs ~20 partner NGOs but has no single place to see or manage them — every support and onboarding task means a database console, a Django shell, or asking the NGO to do it themselves.
**Example:** Akshara (an NGO) emails "Priya can't log in." Meera (Dalgo support) has no screen showing Akshara's users — she opens a database console and re-triggers Priya's invite by hand. Onboarding a new NGO is the same: a developer runs setup commands manually.
**Why it matters:** A small team can't scale support and onboarding across 20+ NGOs on database consoles and tribal knowledge. Every manual task is slow, risky, and needs an engineer — so non-engineers can't help at all.

---

## Target Users

| Persona | Real-world context | What they do in v1 |
|---------|-------------------|-------------------|
| **Meera** — Dalgo Support | First responder to NGO tickets; not always an engineer. | Find any org's users; resend invite, change role, remove, add. |
| **Arjun** — Dalgo Onboarding / Ops | Brings NGOs on; offboards ones that leave. | Create an org; suspend, reactivate, archive one. |
| **Ravi** — Dalgo Superadmin | Owns platform governance and security. | Manage the platform-admin staff list; review the action log. |

NGO-side personas — **Sarah** (org Admin), **Priya** (Analyst), **James** (Member) — do **not** use this portal.

---

## Success Metrics

| Metric | Baseline (today) | Target |
|--------|-----------------|--------|
| Median time to resolve "user can't log in" | Hours (engineer + DB console) | Under 5 minutes (Meera self-serves) |
| Routine user/org tasks needing an engineer | ~All | Near zero |
| Time to create a new org shell | Manual, developer-run | Minutes, done by a non-engineer |
| Cross-org health visibility | None | All orgs + failing pipelines in one view |
| Platform actions with an accountable record | 0% | 100% |

---

## User Flows

### Flow A — See all orgs, drill into one

```
open portal
  -> Org directory: every org (name, users, warehouse, last sync, status)
  -> filter (e.g. status = FAILING)
  -> click an org -> Org detail (users + health + lifecycle actions)
```
**Empty state:** no orgs yet → empty directory with a "Create org" call to action.

### Flow B — Fix a stuck NGO user

```
Org detail -> Users tab -> find user
  -> resend invite | change role | remove | add user
  -> confirm -> row updates -> action logged
```
**Error path:** action fails → clear message, nothing changed.

### Flow C — Create an org

```
Org directory -> "Create org"
  -> org name, plan tier, first Admin email
  -> confirm -> org shell created + first Admin invited
  -> org appears in directory -> action logged
```
Warehouse connection is completed later in the org's own setup flow (not in this dialog).

### Flow D — Suspend / reactivate / archive

```
Org detail -> lifecycle menu
  -> Suspend    -> type org name to confirm -> users can't log in; pipelines paused; data kept
  -> Reactivate -> org returns to Active
  -> Archive    -> type org name to confirm -> leaves active list; data kept
```

### Flow E — Manage platform staff (superadmin only)

```
Portal -> Platform Staff
  -> list platform admins -> add by email | remove
  -> confirm -> action logged
```

---

## User Stories

### Meera (Support)

**Story 1 — See every org and its health**
**As** Meera, **I want** one directory of all orgs with health signals, **so that** I can triage without a database.

**Acceptance criteria:**
- [ ] Directory lists every org with: name, user count, warehouse type, last pipeline run time, status (Active / Suspended / Failing).
- [ ] I can sort and filter by status.
- [ ] "Failing" = the org's most recent pipeline run failed; visible without opening the org.
- [ ] Clicking an org opens its detail view.
- [ ] Empty state (no orgs) shows a "Create org" action.

**Story 2 — Manage any org's users**
**As** Meera, **I want** to act on any org's users, **so that** I resolve access tickets in minutes.

**Acceptance criteria:**
- [ ] The org's Users tab shows every user with role, status (invited / active), last active.
- [ ] I can resend an invitation to a user who never accepted.
- [ ] I can change a user's role (within that org's role model) and remove a user.
- [ ] I can add a new user to the org with a role.
- [ ] I cannot see the NGO's data (dashboards, warehouse rows) — user records only.
- [ ] Every action writes an action-log entry.

### Arjun (Onboarding / Ops)

**Story 3 — Create an org**
**As** Arjun, **I want** to create an org from the portal, **so that** onboarding doesn't need a developer.

**Acceptance criteria:**
- [ ] I create an org by entering: org name, plan tier, first Admin email.
- [ ] The org shell is created and the first Admin is invited as that org's Admin.
- [ ] The new org appears in the directory immediately.
- [ ] Warehouse setup is NOT part of this dialog — it's completed in the org's own setup flow afterward.
- [ ] Creation writes an action-log entry.
- [ ] Creating an org with a name that already exists is rejected with a clear message.

**Story 4 — Suspend, reactivate, archive**
**As** Arjun, **I want** to change an org's lifecycle state safely, **so that** pausing or offboarding doesn't mean editing data by hand.

**Acceptance criteria:**
- [ ] Suspend: the org's users can no longer log in, and its scheduled pipelines are paused. Data is retained.
- [ ] Reactivate: a suspended org returns to Active; its users can log in again.
- [ ] Archive: the org leaves the active directory list; its data is retained (recoverable).
- [ ] Suspend and archive require typing the org's name to confirm; the confirm button stays disabled until the name matches.
- [ ] Each lifecycle change writes an action-log entry.

### Ravi (Superadmin)

**Story 5 — Control who is a platform admin**
**As** Ravi, **I want** to manage the Dalgo staff who can reach the portal, **so that** cross-org access stays tightly held.

**Acceptance criteria:**
- [ ] I can see the list of current platform admins.
- [ ] I can add or remove a platform admin by email.
- [ ] Only the superadmin sees and uses the Platform Staff screen; ordinary platform admins cannot.
- [ ] Add/remove writes an action-log entry.

**Story 6 — Review the action log**
**As** Ravi, **I want** a record of every platform action, **so that** cross-org power is accountable.

**Acceptance criteria:**
- [ ] Every portal action (user change, org lifecycle change, staff change) logs: actor, action, target org/user, timestamp.
- [ ] I can view the log and filter by org, actor, and action type.
- [ ] Log entries cannot be edited or deleted from the portal.

### All platform admins

**Story 7 — The portal is invisible to NGOs**
**As** a platform admin, **I want** the portal hidden from NGO users, **so that** an org Admin like Sarah never sees platform tooling.

**Acceptance criteria:**
- [ ] No NGO user (any org role) sees a link, nav item, or route to the portal.
- [ ] A non-platform-admin who reaches a portal URL directly is refused by the server, not just by hidden UI.

---

## UI Surface

**Where it lives:** a dedicated Dalgo-staff portal, separate from any single NGO's app, reachable only by platform admins. (Separate address vs. gated section is an engineering choice — the spec only requires it be invisible and inaccessible to NGO users.)

| Surface | What it shows | Key states |
|---------|--------------|-----------|
| **Org directory** | Table of all orgs: name, users, warehouse, last sync, status. Sort + filter. "Create org" button. | Empty, populated, filtered, loading, error. |
| **Org detail** | One org's Users tab + health panel + lifecycle menu. | Loading, active, suspended, archived, error. |
| **Create-org dialog** | Org name, plan tier, first Admin email. | Default, validating, success, name-taken error. |
| **User action dialogs** | Resend / change role / remove / add, with confirm. | Default, confirm, success, error. |
| **Destructive confirmations** | Suspend / archive: type the org name. | Default, name-mismatch (disabled), confirmed. |
| **Platform Staff** (superadmin only) | Platform-admin list; add/remove by email. | Populated, add, remove, error. Hidden from non-superadmins. |
| **Action log** | Actor, action, target, time. Filterable. | Empty, populated, filtered, loading. |

---

## Dependencies

- **Relationship to access-control (`features/access-control/v2/spec.md`):** that feature owns the *org-Admin* Settings area (an NGO Admin managing her own team). This portal is the *Dalgo-staff, cross-org* layer above it.
  - **Boundary rule:** when this portal invites or changes a user inside an org, it uses that org's own role model (whatever access-control defines at the time). This portal does not add new org-level roles; it defines a separate *platform-admin* tier that only Dalgo staff hold.
- **Requires:** the existing Org and user/role concepts. The platform-admin tier, org lifecycle state, and the action log are new in this version.
- **Enables:** v2 impersonation and usage metrics, both of which hang off the v1 org directory.

---

## Handoff Checklist

- [x] v1 scope is a clean subset of the full vision, with deferrals recorded and reasoned.
- [x] Problem, users, and success metrics stated with named examples.
- [x] Flows persona-agnostic; stories persona-driven with tightened acceptance criteria.
- [x] UI surface enumerated with states.
- [x] Boundary with access-control v2 stated to prevent overlap.
- [x] No open questions — every product decision is resolved or explicitly deferred.
- [ ] Team review before planning.

---

## Next

`/engineering/plan-feature features/admin-portal/v1/spec.md`
