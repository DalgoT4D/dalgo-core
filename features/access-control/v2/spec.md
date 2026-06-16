# Dalgo Access Control — Role System (v2)

**Status:** Draft for review
**Owner:** Product
**Engineering:** Engineering (model + delivery)
**Design:** Design (Settings IA)
**Reviewers:** Engineering, Leadership
**Date:** 2026-06-16
**Scoped from:** `../v1/access-control-spec-A-role-system-2026-06-02.md` (Spec A — Role System)
**Pairs with:** Spec B — Resource Sharing (floor, direct shares, inheritance, share modal, groups, alerts, comments, **and ownership transfer**). This spec ships first; Spec B follows.

> **What changed from v1 (Spec A):** ownership **transfer** is removed from this scope and deferred to Spec B. Ownership still ships here as a primitive — creator = owner, owner-only delete, and Admin = effective owner — but the ability to **reassign** an owner (owner-initiated or Admin override) now lands with Spec B, alongside the share UI that exercises it. Everything else from Spec A is preserved.

---

## 1. Overview

Dalgo's current access model has four roles (Account Manager > Pipeline Manager > Analyst > Guest) where role is tangled with function: the role a user holds silently determines what they can do to content, infrastructure has write access it shouldn't, and there is no concept of who owns a resource. This makes it impossible to onboard a large viewing audience safely or to reason about "who can do what" cleanly.

This spec resets the foundation. It defines **three roles — Admin / Analyst / Member** — and draws a hard line: **role governs only sidebar visibility and capability on Data infrastructure. It does not cap function on content resources.** Whether a user can View or Edit a dashboard, chart, or report is grant-driven and lands in Spec B, working identically for every role.

This spec is self-contained and shippable in a sprint. It delivers the role tiers, the sidebar/route gating, the consolidated Settings information architecture, the ownership primitive (minus transfer), and the Settings > Users invite surface. It also *states* the invitation and re-sharing policies that govern the grant model, but those policies only become functional when Spec B ships the share modal and grant engine (see §10, §13).

---

## 2. Goals & Non-goals

### 2.1 Goals

1. Collapse four roles to three (Admin / Analyst / Member) with a clean, documented capability map.
2. Decouple role from function: role controls sidebar + Data-infra capability only.
3. Gate the sidebar and routes by role so users never see modules they can't use.
4. Remove Analyst write access to Data infrastructure (read-only); hide it entirely from Members.
5. Consolidate all settings (warehouse details, themes, org defaults, users, groups) under one Settings area with admin-only globals.
6. Introduce **ownership** as a first-class primitive (creator = owner; Admin = effective owner; owner-only delete). **Transfer is deferred to Spec B.**
7. Ship the **Settings > Users** invite surface (create a user with a role, no resource grant required) and define the invitation role-tier rules.
8. Migrate existing users cleanly.

### 2.2 Non-goals (deferred to Spec B)

**Ownership transfer** (owner-initiated reassignment and Admin override), visibility floor (audience × permission), direct shares, public-link per-resource toggle, hybrid inheritance + embed/broadening warnings, the share modal UI, groups creation/management UX, alerts, comments, and resource taxonomy detail. This spec references these only at the boundary (§13).

---

## 3. Problem Statement

The current role model has structural gaps:

1. **Too many roles, and role caps function.** Four tiers where the tier silently dictates what a user can do to content. A "Guest" can't be given edit on a single dashboard; an "Analyst" is assumed to edit everything. Function should be grant-driven, not role-derived.
2. **Analyst has infrastructure write.** An M&E officer can break pipelines, transforms, or orchestration. Source/transform/orchestration permissioning was never designed.
3. **No ownership.** No record of who created a resource, no owner-only delete, no governance escape hatch. Deletion is ambiguous when staff leave. (Reassigning ownership when staff leave is the *transfer* capability — defined in Spec B; this spec establishes the owner record and owner-only delete that transfer will later operate on.)
4. **Settings scattered.** Warehouse details, themes, users, and org configuration live in different places with inconsistent gating.
5. **Sidebar not role-gated cleanly.** Users see nav items and Create buttons they can't use.
6. **Lowest tier ("Guest") is broken and poorly named.** It doesn't convey "internal consumer," and its permissions don't work.

---

## 4. Personas → Role Mapping

| Persona | Real-world context | New role |
|---|---|---|
| **M&E Lead** | Owns the org's data setup, onboards staff, manages users and billing | **Admin** |
| **Implementation Partner** | Builds/operates pipelines and transforms; may serve multiple NGOs | **Admin** *(migrated from Pipeline Manager — see §11.3)* |
| **M&E Officer** | Creates dashboards/charts to track program outcomes | **Analyst** |
| **Program Staff / Funder** | Checks specific dashboards; may be external; doesn't create content | **Member** |
| **Leadership** | Wants exec-level summaries; can't navigate a full BI tool | **Member** |

Typical org shape: 1–5 editors (M&E Lead / Implementation Partner / M&E Officer bucket) and 30+ consumers (Program Staff / Funder / Leadership bucket).

---

## 5. The Role Model

### 5.1 Three roles

**Admin > Analyst > Member.** The hierarchy is used only for (a) gating which role a user may invite others as (§9) and (b) sidebar/Data-capability scope below. It does **not** rank function on content resources.

### 5.2 Core principle: role is decoupled from function

A role answers two questions only:

1. **What sidebar items and routes can this user reach?**
2. **What can this user do in the Data-infrastructure section** (Ingest / Transform / Warehouse / Pipelines / Orchestration)?

A role does **not** answer "can this user view or edit dashboard X." That is decided entirely by grants on the resource (Spec B) and applies identically to a Member, an Analyst, or an Admin. A Member with an Edit grant can edit and re-share; an Analyst with no grant on a private resource cannot see it. Admin is the only exception, by virtue of being effective owner everywhere (§6).

### 5.3 Sidebar visibility map

| Role | Sidebar items visible | Data infrastructure | Settings access |
|---|---|---|---|
| **Admin** | All — Dashboards, Charts, Reports, Alerts, Data (Ingest/Transform/Warehouse), Pipelines/Orchestration, Settings | Full edit | Full |
| **Analyst** | Dashboards, Charts, Reports, Alerts, Data (read-only), Pipelines/Orchestration (read-only) | Read-only on Ingest/Transform/Warehouse + Pipelines/Orchestration | Groups (only those they're in or created). Users page **hidden** — invite only via share modal (Spec B). |
| **Member** | Dashboards, Charts, Reports, Alerts | Hidden | Groups (only those they're in) |

Notes:
- Sidebar items are **hidden, not greyed**, when a role can't use them. Direct-URL access to a hidden route redirects to the first accessible page (or a "No Access" page where none applies).
- Members do not see Create buttons on content pages (no Data access → can't build content anyway; hidden cleanly).
- Profile page does not exist in the current product. When/if added, all roles see it.

### 5.4 Module-level capability gates (Data infrastructure)

| Section | Admin | Analyst | Member |
|---|---|---|---|
| Ingest (sources) | Full edit | Read-only | Hidden |
| Transform (dbt) | Full edit | Read-only | Hidden |
| Warehouse | Full edit | Read-only | Hidden |
| Pipelines / Orchestration | Full edit | Read-only | Hidden |

Rationale: source/orchestration/transform permissioning is not designed for finer-grained sharing. Analyst gets read-only visibility (they need to understand the data they report on); Member gets nothing. Finer infra permissioning is explicitly **out of scope for V1** and will be revisited.

### 5.5 Settings access per role

Detailed IA in §7. Summary: Admin sees all of Settings including org-wide globals; Analyst and Member see only Groups scoped to groups they're in (Analyst also sees ones they created). The Users page is Admin-only.

---

## 6. Ownership (first-class primitive)

Ownership is introduced here as a primitive and exercised throughout Spec B.

- **Creator = owner.** Every resource records its creator as owner at creation.
- **Owner-only delete.** Only the owner (or an Admin acting as effective owner) can delete a resource. Edit grants do not include delete.
- **Admin = effective owner on every resource.** Governance escape hatch: an Admin can view, edit, delete, re-share, and change role on any resource regardless of grants. Used for governance and recovery, not silent broadening.

**Transfer is deferred to Spec B.** Reassigning ownership — owner-initiated, or by Admin override when an editor leaves the org — is **not** in scope here. This spec lands the `owner` record, owner-only delete, and the Admin effective-owner override; Spec B adds the transfer action and its UI on top of that record. Until Spec B ships, the only way to change an owner is through normal Admin governance (an Admin can act as effective owner on the resource); there is no explicit "transfer owner" action.

Data model: every content resource carries an `owner` (user) column. Migration backfills owner from existing creator metadata where available; where it isn't, the resource is assigned to the **oldest active Admin** in the org.

---

## 7. Settings Consolidation / Information Architecture

All configuration lives under a single **Settings** area. Items split into **org-wide globals (Admin only)** and **personal/group scope (all roles, scoped)**.

| Settings section | Contents | Who sees it |
|---|---|---|
| **Warehouse / Data connection** | Warehouse details, credentials | Admin only |
| **Appearance** | Themes | Admin only (org-wide) |
| **Org defaults** | Default visibility floor, "allow public sharing" global toggle (default on) | Admin only — *referenced by Spec B; the toggles render here, the behavior they control ships in Spec B* |
| **Users** | User list (role, status, last active), invite, role change, delete user | Admin only |
| **Groups** | Group list + membership management | Admin: all. Analyst: groups they're in or created. Member: groups they're in. *(Group CRUD detail in Spec B; this spec reserves the IA slot and role-scoping.)* |

Notes:
- The **Org defaults** section physically ships here (the controls are part of Settings IA), but the floor and public-sharing behaviors they govern are inert until Spec B. The toggles are present and persist their value; nothing consumes that value until Spec B.
- "Allow public sharing" global defaults **on**.
- The **ownership-transfer override** that Spec A originally placed in Settings > Users is **deferred to Spec B** — the Users page in this spec does not include a transfer-ownership action. It ships with the rest of the transfer capability in Spec B.

---

## 8. Ownership & Capability — what ships here vs. activates with Spec B

To keep the ship-order honest (this spec ships roles + sidebar + Settings + ownership-minus-transfer only):

| Capability | Ships & functions here | Activates with Spec B |
|---|---|---|
| Three-role tiers + hierarchy | ✅ | — |
| Sidebar + route gating | ✅ | — |
| Data-infra capability gates | ✅ | — |
| Settings IA + Users page + Org-defaults controls (inert) | ✅ | Org-defaults *behavior* |
| Ownership (owner column, owner-only delete, Admin effective-owner) | ✅ | — |
| **Ownership transfer** (reassign owner; Admin override) | — | ✅ |
| **Settings > Users invite** (create user with a role, no resource grant) | ✅ | — |
| Invitation role-tier rules (§9) | Documented as policy | Enforced in the **share-modal** entry point (Spec B) |
| Sharing-capability decoupling (§10) | Documented as policy | Functional when grants + share modal ship (Spec B) |

This is the seam: an Admin can onboard people with roles via Settings > Users the day this ships. Resource-level sharing, re-sharing, the share-modal invite path, and ownership transfer light up with Spec B.

---

## 9. Invitation Rules

### 9.1 Role-tier gating

The role a user can invite others as is capped by the inviter's own role:

| Inviter | Can invite as |
|---|---|
| **Admin** | Admin, Analyst, Member |
| **Analyst** | Member only |
| **Member** | Member only |

**Anyone can invite as Member.** Only Admins can elevate — i.e., invite a new user as Analyst/Admin or promote an existing user's role. Analysts and Members can bring people in, but only at Member tier. This holds in both entry points.

### 9.2 Entry points

1. **Settings > Users (ships here).** Admin-only page. Admin creates a user, assigns a role, optionally deletes the user or changes their role later. No resource grant is attached here — this is pure platform onboarding. This is the only invite surface live when this ships alone.
2. **Share modal (Spec B).** The primary day-to-day invite path, attached to a resource share. Any user can invite as Member from here; Analyst/Admin invites gated per §9.1. **Analyst's Settings > Users page stays hidden** — Analysts invite only through the share modal, which is why the share-modal path is essential to the Analyst onboarding story and lands in Spec B.

### 9.3 Interim note

Until Spec B ships, only Admins can invite (via Settings > Users), because the share-modal path doesn't exist yet. This is acceptable for the transitional window — Admins onboard the initial user base; broad self-service sharing arrives with Spec B.

---

## 10. Sharing Capability Decoupled from Role

Stated here as policy; functional with Spec B.

- **Sharing capability = Edit on the resource.** Anyone with an Edit grant on a resource can re-share it — including a Member who holds an Edit grant. A user with only View cannot re-share.
- **Re-sharer caps to their own permission level.** Someone with Edit can grant up to Edit (View or Edit); someone with View cannot grant at all.
- **Inviter's role caps the role tier** of any new platform invitation created during a share (per §9.1).
- Role never independently grants or caps the ability to share content. It only caps the *role tier* of new invitations.

---

## 11. Migration & Transition

### 11.1 Role mapping (locked)

| Current role | Migrates to | Net change |
|---|---|---|
| Account Manager | **Admin** | Renamed; capabilities preserved + ownership/governance formalized |
| Pipeline Manager | **Admin** | **Escalation** — gains user management, billing, org governance (see §11.3 risk) |
| Analyst | **Analyst** | Loses Data-infra **write** → read-only. No change to content function (was never role-capped). |
| Guest | **Member** | Renamed; broken permissions fixed. Sees all content View-only in the interim (§12). |

### 11.2 Migration note — PM → Admin (decision: wholesale, confirmed)

Wholesale PM→Admin is **confirmed** by Product. Recorded here for transparency: it is a privilege escalation. Implementation partners (the Implementation Partner persona) are frequently external and may serve multiple NGOs; as Admins they gain user management, billing visibility, governance override, and effective ownership of every resource in the org. The locked context MD had originally scoped this as "default Analyst, Admin upgrade per case" — that is now overridden. No forced post-migration review step ships; if an org finds the escalation unwanted, any Admin can downgrade an inherited Admin individually via Settings > Users. Flagged for leadership/security *awareness* at rollout, not as a blocker.

---

## 12. Interim vs. End-State Behavior (the v2 → Spec B window)

Because this ships before the grant model, content visibility behaves differently in the window between the two specs:

| Role | Content visibility in interim (this live, Spec B not) | End state (Spec B live) |
|---|---|---|
| **Admin** | Sees and can edit/delete everything (effective owner) | Unchanged |
| **Analyst** | Sees all content; edit per current behavior | View/Edit per grants (+ floor); content function fully grant-driven |
| **Member** | **Sees all *content* resources (Dashboards/Charts/Reports/Alerts) at View only. No Edit, no Create. Data section stays hidden.** | Sees only resources covered by floor + direct grants; Edit where granted. Data section still hidden. |

The interim Member behavior is a deliberate transitional choice: rather than show new Members an empty product on day one (no grants exist yet), they get read-only visibility across **content** until Spec B's resource-level grants narrow it to what's actually shared with them. This avoids the "logged in, see nothing" cliff and mirrors today's Guest-sees-content expectation while the targeted-sharing surface is built.

**The Data section (Ingest/Transform/Warehouse/Pipelines/Orchestration) is never visible to a Member — interim or end state.** The interim broadening applies only to content lists, not to data infrastructure. The narrowing at Spec B launch (content lists shrinking to granted-only) is expected behavior, not a regression, and must be communicated as such.

---

## 13. Scope & Boundary Handshake with Spec B

### 13.1 In this spec

Three-role definition and hierarchy · sidebar visibility map · route gating + No Access page · Data-infra capability gates (Analyst read-only, Member hidden) · Settings consolidation IA + Org-defaults controls (inert) · Users page + Settings invite surface · ownership primitive (owner column, owner-only delete, Admin effective owner) · invitation role-tier rules (policy) · sharing-capability decoupling (policy) · migration + comms.

### 13.2 In Spec B (referenced, not defined here)

**Ownership transfer** (owner-initiated + Admin override, plus the resource-menu and Settings UI) · two-axis floor (audience minimum-role × View/Edit) + org-default · direct shares · public-link per-resource toggle · hybrid inheritance + embed/broadening warnings · share modal · groups CRUD · alerts · comments · resource taxonomy · pending-invite state + 30-day expiry · resource-share migration + one-time auto-extend.

### 13.3 The seam

- **This spec defines** what role each invite produces and what capabilities a role grants (sidebar + Data infra). **Spec B defines** the per-resource permission picker (View/Edit) — independent of role.
- **Ownership** is a primitive established here (owner column, owner-only delete, Admin effective owner); Spec B references it for the share UI and **adds the transfer action** (owner-initiated + Admin override) on top of the owner record.
- **Settings > Org defaults** (default floor, public-sharing toggle) render in this spec's Settings IA but their behavior is consumed by Spec B's floor model.
- **Invitation rules + sharing-capability** are stated as policy here and enforced functionally in Spec B's share modal.

---

## 14. UI Surface

- **Sidebar (`main-layout.tsx`):** filter nav items by role-derived permissions; hide, don't grey.
- **Route middleware:** permission-based guards; unauthorized direct URL → first accessible page or No Access page.
- **No Access page:** new component; shows org Admin contact.
- **Settings IA:** restructured into the §7 sections with Admin-only gating on globals.
- **Settings > Users:** user list (role, status, last active), invite (Analyst/Admin tiers Admin-only), role change (Admin), delete user (Admin). *(No ownership-transfer action — deferred to Spec B.)*
- **Data section:** read-only rendering for Analyst (no Create/Edit/Delete affordances); hidden for Member.

> The **Ownership transfer UI** (resource-menu action + Settings override) that Spec A listed here is **deferred to Spec B**.

---

## 15. Technical Implications

### 15.1 DDP_backend (Django + Django Ninja)

| Change | Impact |
|---|---|
| Role enum | Collapse four roles to three (`admin`, `analyst`, `member`). Migration maps AM→admin, PM→admin, analyst→analyst, guest→member. |
| Analyst infra permissions | Remove write on Ingest/Transform/Warehouse/Pipelines/Orchestration; grant read-only on Ingest/Transform/Warehouse; hide Pipelines/Orchestration. |
| Ownership | Add `owner` (FK to user) on every content resource. Backfill from creator metadata; fallback to oldest active Admin. Owner-only delete enforced server-side. Admin effective-owner override in the permission check. **No transfer endpoint — that ships with Spec B.** |
| Settings / org config | Consolidate config endpoints; add Org-defaults storage (`default_visibility_floor`, `allow_public_sharing` default true) — stored but not yet consumed (Spec B reads them). |
| Invite (Settings > Users) | Create-user-with-role endpoint; only Admins may assign Analyst/Admin tiers; delete user; role change (Admin). No resource-grant payload here. |
| Route/permission gating | Server-side capability checks per role for Data-infra and Settings endpoints. |
| Hooks for Spec B | Permission resolver structured to accept resource grants later; `owner` consumed by Spec B share/delete logic and the transfer action. |

### 15.2 webapp_v2 (Next.js 15 + React 19)

| Change | Impact |
|---|---|
| Sidebar | `useUserPermissions()` filter by role. |
| Route middleware | Role-based guards + No Access page. |
| Settings | Re-IA per §7; Admin-only globals; Org-defaults controls (inert). |
| Settings > Users | Invite/role/delete-user. *(Ownership transfer deferred to Spec B.)* |
| Data section | Read-only mode for Analyst; hidden for Member. |
| Interim Member view | Content lists render all resources View-only until Spec B grant gating ships. |

### 15.3 Migration scripts

- Role remap (AM/PM→admin, analyst→analyst, guest→member).
- Owner backfill + un-attributable triage list.
- Analyst infra-permission downgrade.
- No resource-share migration here (that's Spec B). No ownership-transfer migration (transfer ships with Spec B).

---

## 16. Success Metrics

| Metric | Baseline | Target |
|---|---|---|
| Roles in the model | 4 | 3 |
| Analyst-caused infra (pipeline/transform/warehouse) breakages | Possible | Zero (write removed) |
| Resources with an assigned owner post-migration | 0% | 100% (after triage) |
| "Where did setting X go?" support tickets post-Settings-consolidation | n/a | < 5 in first 2 weeks |
| Orgs that downgraded any inherited (PM→Admin) account post-migration | n/a | Monitor — signal on whether the escalation was unwanted |

---

## 17. Decisions & Open Questions

### 17.1 Resolved

1. **Ownership transfer deferred to Spec B** (this revision). The owner record, owner-only delete, and Admin effective-owner override ship here; reassignment (owner-initiated + Admin override) and its UI ship with Spec B. Until then, an Admin acting as effective owner is the only way to operate on a resource whose owner has left.
2. **PM→Admin** — wholesale mapping **confirmed** (§11.3). No forced review step; per-user downgrade available post-migration.
3. **Owner backfill fallback** — un-attributable resources assigned to the **oldest active Admin** (§6, §11.2). No separate "review ownership" triage step.
4. **Analyst Data access** — **read-only confirmed** (Ingest/Transform/Warehouse + Pipelines/Orchestration). Analysts can read orchestration; they cannot edit infra.
5. **User lifecycle** — this spec ships **hard delete** of users (Admin only), not just deactivation.
6. **Interim Member scope** — Members get interim View-only on **content only**; the **Data section stays hidden** interim and end-state (§12).

### 17.2 Still open

1. **Settings > Org-defaults controls shipping inert** — confirm with Engineering whether to render them here or hold the entire Org-defaults section for Spec B to avoid shipping non-functional toggles.
2. **Deleting a user who owns resources, before transfer exists.** With transfer deferred to Spec B, confirm the interim behavior when an Admin hard-deletes a user who owns content: reassign those resources to the oldest active Admin (mirroring the backfill fallback), or block the delete until Spec B's transfer ships. Recommend reassign-to-oldest-Admin to keep user delete unblocked.

---

## 18. Implementation Order

```
1. Role enum collapse + migration (AM/PM→Admin, Analyst→Analyst, Guest→Member)  → backend, independent
2. Analyst infra-permission downgrade + Data read-only/hidden rendering          → backend + frontend
3. Sidebar + route gating + No Access page                                       → frontend
4. Settings consolidation IA + Org-defaults controls (inert)                     → frontend + backend
5. Ownership: owner column, backfill, owner-only delete, Admin override          → backend + frontend
   (transfer deferred to Spec B)
6. Settings > Users invite surface                                               → backend + frontend
```

This spec is independently shippable end-to-end. Resource-level sharing, the share modal, ownership transfer, and grant-driven content function arrive with Spec B; until then, content visibility follows §12.

---

## 19. Engineering Notes

- Role decoupling is the core idea: do **not** reintroduce function-by-role anywhere in the content layer. The only role-driven capability checks are sidebar visibility, Data-infra access, and Settings gating.
- Build the permission resolver here so resource grants slot in later without rework (Spec B extends, doesn't replace).
- The `owner` column and Admin effective-owner override are the two pieces Spec B depends on most — land them solidly here. **Model `owner` as a mutable FK** so Spec B's transfer action is a write to the existing column, not a schema change.
- Org-defaults storage ships now, consumption later — keep the read path stubbed for Spec B.
```
