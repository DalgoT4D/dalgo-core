# Access Control — Role System (Spec A) — v2

**Scoped from**: `../v1/access-control-spec-A-role-system-2026-06-02.md` (the authoritative Spec A draft)
**Version**: v2
**Status**: Draft for engineering
**Date**: 2026-06-15

> **Why v2 and not v1?** The `v1/` folder holds an earlier, superseded design — four roles
> (Account Manager / Pipeline Manager / Analyst / Viewer) with access grants coupled to roles.
> Spec A resets that foundation. This v2 spec is the version engineering should build.
>
> **One-line glossary** (terms used throughout):
> - **Role** — Admin, Analyst, or Member. Controls sidebar visibility and Data-infrastructure access *only*.
> - **Grant** — a per-resource View/Edit permission (e.g. "Priya can Edit the Field Performance dashboard"). Grants are **Spec B**, not this spec.
> - **Owner** — the user who created a resource; the only one (besides an Admin) who can delete it.
> - **Data infrastructure** — the Ingest / Transform / Warehouse / Pipelines / Orchestration section. The technical plumbing, not the dashboards.
> - **IA (Information Architecture)** — how settings pages are grouped and labelled.

---

## Scope for this iteration

### What's included
- **Three roles** — collapse the four current roles down to Admin / Analyst / Member, with a documented capability map.
- **Role decoupled from function** — a role decides what you *see* (sidebar) and what you can do in *Data infrastructure*. It does **not** decide whether you can view or edit a dashboard.
- **Sidebar + route gating** — hide nav items a role can't use; redirect direct-URL access to a hidden route.
- **Data-infra capability gates** — Analyst is read-only on Ingest/Transform/Warehouse/Pipelines/Orchestration; Member can't see that section at all.
- **Settings consolidation** — one Settings area, with org-wide globals gated to Admins.
- **Ownership primitive** — every content resource records an owner; only the owner (or an Admin) can delete it; ownership can be transferred.
- **Settings > Users invite surface** — an Admin can create a user, assign a role, change it, or delete the user. No resource grant attached.
- **Migration + comms** — map existing users to the new roles and tell affected users what changed.

### What's deferred to Spec B (the next slice)
- The **share modal** and the per-resource **View/Edit grant** engine.
- Visibility floor (audience × permission), direct shares, public-link per-resource toggle, inheritance.
- Groups create/manage UX, alerts, comments, resource taxonomy.
- **Why deferred:** Spec A is shippable in a sprint on its own. Grants are a larger build and depend on the ownership primitive and permission resolver that Spec A lands first.

> **Boundary note:** Spec A *states* the invitation rules (§ User Stories 7) and the
> "sharing = Edit grant" policy, but those only become *functional* when Spec B ships the
> share modal. Until then, only an Admin can invite people, via Settings > Users.

---

## Problem Statement

Dalgo's current access model has four roles — Account Manager > Pipeline Manager > Analyst > Guest — and the role is tangled up with what a user can *do* to content. Six things are broken:

| # | Problem | Concrete example |
|---|---|---|
| 1 | **Too many roles, and the role caps function** | A "Guest" can't be given Edit on a single dashboard. An "Analyst" is assumed to edit everything. |
| 2 | **Analyst has infrastructure write** | Priya (M&E Officer, Analyst) can accidentally break a pipeline or a dbt transform. |
| 3 | **No ownership** | When an editor leaves the org, nobody knows who owns their dashboards or who may delete them. |
| 4 | **Settings scattered** | Warehouse credentials, themes, and user management live in different places with inconsistent gating. |
| 5 | **Sidebar not role-gated** | James (a funder) sees "Ingest" and "Transform" nav items he can never use. |
| 6 | **Lowest tier is broken and badly named** | "Guest" doesn't say "internal consumer," and its permissions don't actually work. |

The net effect: an NGO **can't safely onboard a large viewing audience** (30+ program staff, funders, leadership) or reason cleanly about "who can do what."

---

## Target Users

Dalgo orgs are shaped like a pyramid: **1–5 editors** at the top, **30+ consumers** at the base. The new roles map onto that shape.

| Persona | Real-world context | New role |
|---|---|---|
| **Sarah** (M&E Lead) | Owns the org's data setup, onboards staff, manages users and billing | **Admin** |
| **Raj** (Implementation Partner) | Builds and operates pipelines and transforms; may serve several NGOs | **Admin** *(migrated from Pipeline Manager — see Migration)* |
| **Priya** (M&E Officer) | Creates dashboards and charts to track program outcomes | **Analyst** |
| **James** (Program Staff / Funder) | Checks specific dashboards; may be external; creates nothing | **Member** |
| **Leadership** | Wants exec summaries; can't navigate a full BI tool | **Member** |

The most underserved persona today is **James (Member)** — there's no safe way to give him access without showing him everything or nothing.

---

## The Role Model (the core idea)

**The rule:** A role answers only two questions — (1) what sidebar items and routes can this user reach, and (2) what can they do in Data infrastructure. It does **not** decide whether they can view or edit a dashboard.

**Example:** James is a Member. Whether James can open the "Field Performance" dashboard is decided by a *grant* on that dashboard (Spec B), not by the fact that he's a Member. A Member with an Edit grant can edit and re-share; an Analyst with no grant on a private dashboard can't even see it.

**Why it matters:** If we tied "can edit content" to the role tier, Members could never be given edit — wrong for an NGO where most users are Members. Decoupling keeps role about *navigation and infrastructure*, and content permission about *grants*.

The one exception: **Admin is effective owner of every resource** (governance escape hatch — see Ownership).

### Sidebar visibility map

| Role | Sidebar items visible | Data infrastructure | Settings access |
|---|---|---|---|
| **Admin** | All — Dashboards, Charts, Reports, Alerts, Data (Ingest/Transform/Warehouse), Pipelines/Orchestration, Settings | Full edit | Full |
| **Analyst** | Dashboards, Charts, Reports, Alerts, Data (read-only), Pipelines/Orchestration (read-only) | Read-only | Groups (ones they're in or created). **Users page hidden.** |
| **Member** | Dashboards, Charts, Reports, Alerts | Hidden | Groups (ones they're in) |

**Hide, don't grey.** A role that can't use a nav item doesn't see it. A direct URL to a hidden route redirects to the first page the user *can* reach, or a "No Access" page if none applies.

### Data-infrastructure capability gates

| Section | Admin | Analyst | Member |
|---|---|---|---|
| Ingest (sources) | Full edit | Read-only | Hidden |
| Transform (dbt) | Full edit | Read-only | Hidden |
| Warehouse | Full edit | Read-only | Hidden |
| Pipelines / Orchestration | Full edit | Read-only | Hidden |

**Why read-only for Analyst, not hidden:** Priya needs to *understand* the data she reports on, so she can read pipelines and transforms — but she can't change them, so she can't break them. Finer-grained infra sharing is explicitly **out of scope** for now.

---

## Ownership (first-class primitive)

**The rule:** The creator of a resource is its owner. Only the owner — or an Admin acting as effective owner — can delete it. Ownership can be transferred.

**Example:** Priya creates the "Program Outcomes" dashboard, so Priya is its owner. When Priya leaves the org, Sarah (Admin) reassigns ownership to another analyst, or deletes it. An Analyst who merely had Edit on it cannot delete it.

**Why it matters:** Without an owner, deletion and reassignment are ambiguous when staff leave — a real, recurring problem for small NGO teams.

Four ownership facts:

| Fact | Meaning |
|---|---|
| **Creator = owner** | Every resource records its creator as owner at creation. |
| **Transferable** | Owner can hand off; an Admin can override (e.g. when an editor leaves). |
| **Owner-only delete** | An Edit grant does **not** include delete. Only owner or Admin deletes. |
| **Admin = effective owner everywhere** | An Admin can view, edit, delete, re-share, and transfer any resource, for governance and recovery. |

**Data model:** every content resource gets an `owner` column (a foreign key to the user). Migration backfills the owner from existing creator metadata. Where that's missing, the resource is assigned to the **oldest active Admin** in the org.

---

## Settings Consolidation (Information Architecture)

All configuration moves under one **Settings** area. Items split into **org-wide globals (Admin only)** and **personal/group scope (all roles, scoped)**.

| Settings section | Contents | Who sees it |
|---|---|---|
| **Warehouse / Data connection** | Warehouse details, credentials | Admin only |
| **Appearance** | Themes | Admin only (org-wide) |
| **Org defaults** | Default visibility floor, "allow public sharing" toggle (default on) | Admin only — *controls render here; their behavior ships in Spec B* |
| **Users** | User list (role, status, last active), invite, role change, delete user, ownership-transfer override | Admin only |
| **Groups** | Group list + membership | Admin: all. Analyst: groups they're in or created. Member: groups they're in. *(Group CRUD detail is Spec B.)* |

> **Org defaults are inert in this spec.** The toggles appear and save their value, but nothing
> reads that value until Spec B's floor + public-sharing model ships. (This is the one open
> question below — whether to render them now or hold the whole section.)

---

## Success Metrics

| Metric | Baseline | Target |
|---|---|---|
| Roles in the model | 4 | 3 |
| Analyst-caused infra breakages (pipeline/transform/warehouse) | Possible | Zero (write removed) |
| Resources with an assigned owner post-migration | 0% | 100% (after triage) |
| "Where did setting X go?" support tickets after Settings consolidation | n/a | < 5 in first 2 weeks |
| Orgs that downgraded an inherited (PM→Admin) account post-migration | n/a | Monitor — signals whether the escalation was unwanted |

---

## User Stories

### Story 1: Admin onboards a user via Settings > Users
**As an** Admin (Sarah), **I want** to create a user and assign their role from one page, **so that** I can onboard staff the day Spec A ships, before the share modal exists.

**Acceptance Criteria:**
- [ ] Settings > Users lists every user with role, status, and last-active.
- [ ] Admin can invite a new user and assign Admin, Analyst, or Member.
- [ ] Admin can change an existing user's role.
- [ ] Admin can **hard delete** a user (not just deactivate).
- [ ] No resource grant is collected here — this is platform onboarding only.
- [ ] The Users page is **hidden** for Analyst and Member.

### Story 2: Analyst loses Data-infrastructure write
**As an** Admin (Sarah), **I want** Analysts to be read-only on Data infrastructure, **so that** an M&E officer can't accidentally break a pipeline or transform.

**Acceptance Criteria:**
- [ ] Analyst can open Ingest, Transform, Warehouse, Pipelines, Orchestration in read-only mode.
- [ ] No Create / Edit / Delete affordances render for an Analyst in those sections.
- [ ] Server rejects write calls to those endpoints from an Analyst, not just the UI.
- [ ] Analyst keeps full ability to build dashboards, charts, and reports (that's grant-driven, never role-capped).

### Story 3: Member sees a clean, usable sidebar
**As a** Member (James), **I want** to see only the nav items I can use, **so that** the product isn't cluttered with options I can't touch.

**Acceptance Criteria:**
- [ ] Member sees only Dashboards, Charts, Reports, Alerts.
- [ ] The Data section is fully hidden for a Member (interim and end-state).
- [ ] No Create buttons render on content pages for a Member.
- [ ] Items are hidden, not greyed.

### Story 4: Route gating + No Access page
**As any** user, **I want** a direct URL to a page I can't use to send me somewhere sensible, **so that** I never land on a broken or blank screen.

**Acceptance Criteria:**
- [ ] Direct URL to a hidden route redirects to the first page the user can access.
- [ ] If no page applies, a "No Access" page renders with the org Admin's contact.
- [ ] Gating is enforced server-side per role for Data-infra and Settings endpoints, not only in the UI.

### Story 5: Ownership — owner-only delete and Admin transfer
**As an** Admin (Sarah), **I want** to reassign or delete a departed editor's resources, **so that** nothing is orphaned when staff leave.

**Acceptance Criteria:**
- [ ] Every content resource has an `owner`; new resources record their creator.
- [ ] Only the owner or an Admin can delete a resource; an Edit grant alone cannot.
- [ ] Owner can transfer ownership; Admin can override-transfer any resource.
- [ ] Migration backfills `owner` from creator metadata; un-attributable resources go to the oldest active Admin.

### Story 6: Settings consolidation
**As an** Admin (Sarah), **I want** all configuration in one Settings area, **so that** I'm not hunting across the product for warehouse details vs. users vs. themes.

**Acceptance Criteria:**
- [ ] Warehouse, Appearance, Org defaults, Users, Groups all live under one Settings area.
- [ ] Org-wide globals (Warehouse, Appearance, Org defaults, Users) are Admin-only.
- [ ] Groups are scoped per role (Admin: all; Analyst: in/created; Member: in).
- [ ] Org-defaults controls render and persist their value, but nothing consumes it yet.

### Story 7: Invitation role-tier gating (policy in this spec)
**As an** Admin (Sarah), **I want** only Admins to be able to invite Analysts/Admins, **so that** privilege can't escalate without an Admin's involvement.

| Inviter | Can invite as |
|---|---|
| **Admin** | Admin, Analyst, or Member |
| **Analyst** | Member only |
| **Member** | Member only |

**Acceptance Criteria:**
- [ ] In Settings > Users (the only live invite surface in Spec A), an Admin can assign any tier.
- [ ] The rule above is documented and enforced wherever an invite is created.
- [ ] *Functional in Spec B:* Analysts/Members invite as Member via the share modal. Until Spec B, only Admins invite at all.

---

## Migration & Transition

### Role mapping (locked)

| Current role | Migrates to | Net change |
|---|---|---|
| Account Manager | **Admin** | Renamed; capabilities preserved + ownership/governance formalized |
| Pipeline Manager | **Admin** | **Escalation** — gains user management, billing, governance (see risk below) |
| Analyst | **Analyst** | Loses Data-infra **write** → read-only. Content function unchanged. |
| Guest | **Member** | Renamed; broken permissions fixed. Sees all content View-only in the interim. |

### Two changes users will notice — communicate, don't migrate silently

1. **Pipeline Manager → Admin.**
   - **Example:** Raj is an external implementation partner. After migration he's an Admin — he gains user management, billing visibility, and effective ownership of every resource.
   - **Risk:** this is a real privilege escalation. Confirmed wholesale by Product. No forced review step ships; any Admin can downgrade an inherited Admin individually via Settings > Users. Flagged for leadership/security *awareness* at rollout.

2. **Analyst loses infra write.**
   - **Example:** Priya kept dashboards but can no longer edit pipelines. If she was de-facto operating infra, her Admin can keep her as an Admin case-by-case.

**Comms timeline:**

```
T-7 days   Email + in-app banner to Admins; direct notes to current PMs and Analysts
T-0        First-login changelog modal per role; owner backfill runs
T+7 days   Monitor support for "I lost pipeline access" tickets; Admins upgrade case-by-case
```

### Interim vs. end-state behavior (the Spec A → Spec B window)

Because grants don't exist yet, content visibility behaves differently in the gap between the two specs:

| Role | Interim (Spec A live, Spec B not) | End state (Spec B live) |
|---|---|---|
| **Admin** | Sees and edits/deletes everything | Unchanged |
| **Analyst** | Sees all content; edits per current behavior | View/Edit per grants (+ floor) |
| **Member** | **Sees all content (Dashboards/Charts/Reports/Alerts) at View only. No Edit, no Create. Data stays hidden.** | Sees only resources granted to them; Edit where granted. Data still hidden. |

**Why interim Members see everything (View-only):** rather than show a new Member an empty product on day one (no grants exist yet), they get read-only visibility across content until Spec B narrows it to what's shared with them. **The narrowing at Spec B launch is expected behavior, not a regression** — and must be communicated as such. The Data section is **never** visible to a Member, interim or end-state.

---

## Technical Implications

### DDP_backend (Django + Django Ninja)

| Change | Impact |
|---|---|
| Role enum | Collapse four roles to three (`admin`, `analyst`, `member`). Migration maps AM→admin, PM→admin, analyst→analyst, guest→member. |
| Analyst infra permissions | Remove write on Ingest/Transform/Warehouse/Pipelines/Orchestration; grant read-only; (Member: hidden). |
| Ownership | Add `owner` FK on every content resource. Backfill from creator metadata; fallback to oldest active Admin. Enforce owner-only delete server-side; Admin effective-owner override in the permission check. |
| Settings / org config | Consolidate config endpoints; add Org-defaults storage (`default_visibility_floor`, `allow_public_sharing` default true) — stored but not yet consumed (Spec B reads them). |
| Invite (Settings > Users) | Create-user-with-role endpoint; only Admins assign Analyst/Admin; delete user; role change. No resource-grant payload. |
| Route/permission gating | Server-side capability checks per role for Data-infra and Settings endpoints. |
| Hooks for Spec B | Build the permission resolver so resource grants slot in later without rework; `owner` consumed by Spec B share/delete logic. |

### webapp_v2 (Next.js 15 + React 19)

| Change | Impact |
|---|---|
| Sidebar (`main-layout.tsx`) | Filter nav items by a role-derived permissions hook (e.g. `useUserPermissions()`). |
| Route middleware | Role-based guards + No Access page. |
| Settings | Re-IA per the table above; Admin-only globals; Org-defaults controls (inert). |
| Settings > Users | Invite / role change / delete user / ownership transfer. |
| Data section | Read-only mode for Analyst; hidden for Member. |
| Interim Member view | Content lists render all resources View-only until Spec B's grant gating ships. |

### Migration scripts

- Role remap (AM/PM→admin, analyst→analyst, guest→member).
- Owner backfill + un-attributable triage list (fallback: oldest active Admin).
- Analyst infra-permission downgrade.
- **No resource-share migration** in this spec — that's Spec B.

---

## Open Questions

1. **Org-defaults controls shipping inert** — confirm with Engineering whether to render the
   Org-defaults section now (toggles present but doing nothing until Spec B) or hold the whole
   section for Spec B, to avoid shipping non-functional controls. *(This is the only item still
   open; everything else below was resolved 2026-06-02.)*

### Resolved (recorded for context)
- **PM → Admin** — wholesale mapping confirmed. No forced review; per-user downgrade available after migration.
- **Owner backfill fallback** — un-attributable resources go to the oldest active Admin. No separate review step.
- **Analyst Data access** — read-only confirmed across Ingest/Transform/Warehouse + Pipelines/Orchestration.
- **User lifecycle** — Spec A ships **hard delete** of users (Admin only), not just deactivation.
- **Interim Member scope** — View-only on content only; Data section stays hidden interim and end-state.

---

## Technical Scope (summary)

- **DDP_backend**: role enum collapse + migration, Analyst infra downgrade, `owner` column + backfill + owner-only delete, consolidated config + inert Org-defaults storage, create-user-with-role endpoint, server-side role gating, a permission resolver structured to accept Spec B grants.
- **webapp_v2**: role-filtered sidebar, route guards + No Access page, re-IA'd Settings with Admin-only globals, Settings > Users (invite/role/delete/transfer), Analyst read-only Data rendering, interim Member content-View-only behavior.

## Dependencies
- **Requires:** nothing — Spec A is independently shippable end-to-end.
- **Enables:** Spec B (resource sharing) — depends on the `owner` column and the permission resolver landed here.

---

## Handoff Checklist
- [x] Problem clearly defined with specific broken behaviors
- [x] Target users identified with real personas
- [x] Success metrics defined and measurable
- [x] User stories have concrete acceptance criteria
- [x] Scope split: in-scope (Spec A) vs deferred (Spec B)
- [x] Technical implications cover both repos + migration scripts
- [x] Implementation order is independently shippable
- [ ] Org-defaults inert-vs-hold question resolved with Engineering
- [ ] Analyst infra-write removal + PM→Admin escalation communicated to affected partners

---

## Implementation Order

```
1. Role enum collapse + migration (AM/PM→Admin, Analyst→Analyst, Guest→Member)   → backend, independent
2. Analyst infra downgrade + Data read-only/hidden rendering                      → backend + frontend
3. Sidebar + route gating + No Access page                                        → frontend
4. Settings consolidation IA + Org-defaults controls (inert)                      → frontend + backend
5. Ownership: owner column, backfill, owner-only delete, Admin override, transfer → backend + frontend
6. Settings > Users invite surface + comms rollout                                → backend + frontend
```
