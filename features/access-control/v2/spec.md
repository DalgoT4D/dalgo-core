# Access Control — v2: Role System (Spec A, minus ownership transfer)

**Scoped from**: ../v1/access-control-spec-A-role-system-2026-06-02.md (the "Spec A: Role System" doc)
**Version**: v2
**Status**: Draft
**Date**: 2026-06-16
**Pairs with**: Spec B — Resource Sharing (share modal, grants, groups CRUD, inheritance, **and ownership transfer**). v2 ships first; Spec B follows.

> **Acronyms used in this doc:** RBAC (role-based access control — who can do what, decided by their role) · IA (information architecture — how the Settings menu is organized) · FK (foreign key — a database column that points at another table's row) · M&E (monitoring & evaluation — the NGO team that tracks program outcomes).

---

## Scope for this iteration

This version is the **role-system foundation** from Spec A. It resets Dalgo's access model from four tangled roles to three clean ones, gates the sidebar and routes by role, consolidates Settings, and introduces **ownership** as a database primitive.

The one change from Spec A: **we do not build ownership *transfer* in this version.** Owners are still recorded, owner-only delete still holds, and an Admin is still the effective owner everywhere — but the ability to *reassign* an owner (owner-initiated or via an Admin override screen) is deferred to Spec B, where the share UI it naturally belongs to gets built.

### What's included

- **Three roles** — Admin / Analyst / Member — replacing the old four (Account Manager / Pipeline Manager / Analyst / Guest).
- **Role decoupled from function — with one cap.** A role decides (1) what sidebar items and routes you can reach and (2) what you can do in the Data-infrastructure section. For content (dashboards, charts, reports, alerts), function is grant-driven (Spec B) for Analysts and Admins. **The one exception: a Member is always view-only on content and can never create, edit, or delete anything.** A grant can change *which* resources a Member sees — never raise a Member above View.
- **Sidebar + route gating** by role. Items you can't use are hidden, not greyed. A "No Access" page catches direct-URL attempts.
- **Data-infrastructure capability gates.** Analyst is read-only on Ingest / Transform / Warehouse / Pipelines / Orchestration. Member can't see the Data section at all.
- **Member is a permanent view-only tier.** A Member can only view — never create, edit, delete, or share anything, on any feature. This is a hard role cap, not a v2-interim state, and no Spec B grant can lift it.
- **Settings consolidation.** All configuration moves under one Settings area, with org-wide globals gated to Admin.
- **Org-defaults controls, shipped inert.** The toggles render and save their value; nothing *reads* that value until Spec B.
- **Ownership primitive (no transfer).** Every content resource gets an `owner` column, backfilled on migration. Owner-only delete is enforced. Admin acts as effective owner everywhere.
- **Settings > Users invite surface.** An Admin can create a user, assign a role, change a role, and delete a user. No resource grant is attached here — it's pure platform onboarding.
- **Migration** of existing users to the new roles (no staged communication plan — see Migration & Transition).

### What's deferred to later versions

| Deferred item | Where it goes | Why deferred |
|---|---|---|
| **Ownership transfer** (reassign owner; Admin override screen) | Spec B | Per the user's call for this iteration — it belongs with the share UI, which is a Spec B surface. Recording owners is enough for v2; reassigning them isn't needed yet. |
| Resource grants (View/Edit per resource) | Spec B | The whole grant engine is Spec B. |
| Share modal | Spec B | Primary day-to-day invite + share path. |
| Visibility floor, public-link toggle, inheritance, broadening warnings | Spec B | Consume the inert Org-defaults controls v2 ships. |
| Groups CRUD UX | Spec B | v2 only reserves the Settings IA slot and role-scoping. |
| Alerts, comments, resource taxonomy detail | Spec B | Out of the role-system foundation. |

---

## Problem Statement

**The rule:** Dalgo's current four-role model ties role to function, so you can't cleanly answer "who can do what."
**Example:** A "Guest" can't be given edit on a single dashboard, and an "Analyst" is assumed to edit *everything* — including pipelines an M&E officer should never touch. There's no record of who owns a resource, so when a staff member leaves, deletion and reassignment are ambiguous.
**Why it matters:** NGOs want to onboard 30+ viewers (program staff, funders, leadership) safely. Today the platform shows them everything or nothing, and there's no governance escape hatch.

The specific gaps v2 fixes:

1. **Too many roles, and role caps function.** Four tiers where the tier silently dictates content access. Function should be grant-driven (Spec B), not role-derived.
2. **Analyst has infrastructure write.** An M&E officer can break pipelines, transforms, or orchestration.
3. **No ownership.** No creator record, no owner-only delete, no governance escape hatch.
4. **Settings scattered.** Warehouse details, themes, users, and org config live in different places with inconsistent gating.
5. **Sidebar not role-gated cleanly.** Users see nav items and Create buttons they can't use.
6. **Lowest tier ("Guest") is broken and poorly named.** It doesn't convey "internal consumer," and its permissions don't work.

---

## Target Users (Personas → Role)

| Persona | Real-world context | New role |
|---|---|---|
| **M&E Lead** | Owns the org's data setup, onboards staff, manages users and billing | **Admin** |
| **Implementation Partner** | Builds/operates pipelines and transforms; may serve multiple NGOs | **Admin** *(migrated from Pipeline Manager — see Migration)* |
| **M&E Officer** | Creates dashboards/charts to track program outcomes | **Analyst** |
| **Program Staff / Funder** | Checks specific dashboards; may be external; doesn't create content | **Member** |
| **Leadership** | Wants exec-level summaries; can't navigate a full BI tool | **Member** |

Typical org shape: 1–5 editors (M&E Lead / Implementation Partner / M&E Officer) and 30+ consumers (Program Staff / Funder / Leadership).

---

## The Role Model

### Core principle: role is decoupled from function (with a Member cap)

**The rule:** For Analysts and Admins, a role does *not* decide whether you can view or edit a given dashboard — that's grant-driven (Spec B). Role decides only what you can reach in the sidebar and what you can do in the Data section. **The exception: a Member is always view-only on content** — no create, edit, or delete, ever, on any resource.
**Example:** Priya (Analyst) can be given Edit on the "Field Performance" dashboard while an Analyst colleague gets only View on the same one — their role doesn't decide that, the grant does. But Anjali (Member) can only ever *view* "Field Performance," even if someone tries to grant her Edit. A grant can change *which* dashboards Anjali sees; it can never let her change one.
**Why it matters:** It lets an NGO have 30 Members who each see exactly what's shared with them — as pure consumers — while Analysts and Admins still get flexible, grant-driven editing.

### Three roles

**Admin > Analyst > Member.** The hierarchy is used only for (a) capping which role a user may invite others as and (b) sidebar / Data-section scope. It does **not** rank function on content.

### Sidebar visibility map

| Role | Sidebar items visible | Data infrastructure | Settings access |
|---|---|---|---|
| **Admin** | All — Dashboards, Charts, Reports, Alerts, Data (Ingest/Transform/Warehouse), Pipelines/Orchestration, Settings | Full edit | Full |
| **Analyst** | Dashboards, Charts, Reports, Alerts, Data (read-only), Pipelines/Orchestration (read-only) | Read-only | Groups (only those they're in or created). **Users page hidden** — Analysts invite only via the share modal (Spec B). |
| **Member** | Dashboards, Charts, Reports, Alerts | Hidden | Groups (only those they're in) |

Rules that govern this table:

- **Hidden, not greyed.** A role that can't use an item doesn't see it. Direct-URL access to a hidden route redirects to the first accessible page, or to a "No Access" page if none applies.
  - *Example:* James (Member) types `/pipelines` into the address bar. He's redirected to Dashboards — he never sees a greyed-out Pipelines screen.
- **Members see no Create/Edit/Delete/Share buttons** on content pages — they are view-only by role (see "Member is a view-only tier" below).
- **Profile page** doesn't exist in the product today. If added later, all roles see it.

### Data-infrastructure capability gates

| Section | Admin | Analyst | Member |
|---|---|---|---|
| Ingest (sources) | Full edit | Read-only | Hidden |
| Transform (dbt) | Full edit | Read-only | Hidden |
| Warehouse | Full edit | Read-only | Hidden |
| Pipelines / Orchestration | Full edit | Read-only | Hidden |

**The rule:** Analyst gets read-only on all Data sections; Member gets nothing.
**Example:** Priya (Analyst) opens Pipelines to understand how the data she reports on is built. She can read the flow but sees no Edit, Run, or Delete buttons. James (Member) has no Pipelines item in his sidebar at all.
**Why it matters:** Source / transform / orchestration permissioning was never designed for fine-grained sharing. Read-only for Analyst and hidden for Member is the safe default; finer infra permissioning is explicitly out of scope for now.

### Member is a view-only tier (permanent)

**The rule:** A Member can only ever **view**. No create, no edit, no delete — on content (dashboards, charts, reports, alerts) and on everything else. The Data section is hidden from Members entirely. This holds permanently, not just in the v2 interim, and it is not overridable by any Spec B grant.
**Example:** James is a Member. He opens the "Field Performance" dashboard and reads it, changes filters, exports a PDF. He sees no "New dashboard", no "Edit", no "Delete", no "Share" button anywhere in the product. Even if an Analyst tries to give James an Edit grant in Spec B, the most James can get is View.
**Why it matters:** Members are the 30+ consumers in a typical org (program staff, funders, leadership). Keeping them strictly view-only makes them safe to onboard in bulk and means Spec B's grant logic only has to decide *which* resources a Member sees, never *what* they can do to them.

| Action | Admin | Analyst | Member |
|---|---|---|---|
| View content | ✅ | ✅ (per grant in Spec B) | ✅ (per grant in Spec B) |
| Create / edit / delete content | ✅ | ✅ (per Edit grant in Spec B) | ❌ never |
| Re-share content | ✅ | ✅ (with Edit grant) | ❌ never |
| Data section | Full edit | Read-only | Hidden |

---

## Ownership (first-class primitive — no transfer in v2)

**The rule:** Every content resource records its creator as `owner`. Only the owner (or an Admin acting as effective owner) can delete it. An Admin can view, edit, delete, and re-share any resource regardless of grants.
**Example:** Priya creates the "Field Performance" dashboard, so she's its owner. Another Analyst with an Edit grant can change it but can't delete it — delete is owner-only. Sarah (Admin) can delete it if needed, as a governance action.
**Why it matters:** It gives the org a clean delete rule and a governance escape hatch for when staff leave, without silently broadening who can do what.

What ships in v2 vs. what waits:

| Ownership capability | v2 | Spec B |
|---|---|---|
| `owner` column on every content resource | ✅ | — |
| Backfill owner from creator metadata (fallback: oldest active Admin) | ✅ | — |
| Owner-only delete, enforced server-side | ✅ | — |
| Admin = effective owner override in the permission check | ✅ | — |
| **Transfer / reassign ownership (owner-initiated or Admin override)** | ❌ **deferred** | ✅ |

**The deferral, concretely:** In v2 there is no "Transfer ownership" button anywhere — not on the resource menu, not in Settings > Users. If an owner leaves the org before Spec B ships, an Admin still has full effective-owner powers over their resources (view, edit, delete, and later re-share), so nothing is stuck. The only thing you can't yet do is *permanently reassign* the `owner` field to a new person; that arrives with Spec B's share UI.

**Data model:** every content resource carries an `owner` (FK to user). Migration backfills owner from existing creator metadata where available; where it isn't, the resource is assigned to the **oldest active Admin** in the org.

---

## Settings Consolidation (Information Architecture)

All configuration lives under a single **Settings** area, split into **org-wide globals (Admin only)** and **personal/group scope (all roles, scoped)**.

| Settings section | Contents | Who sees it |
|---|---|---|
| **Warehouse / Data connection** | Warehouse details, credentials | Admin only |
| **Appearance** | Themes | Admin only (org-wide) |
| **Org defaults** | Default visibility floor, "allow public sharing" toggle (default on) | Admin only — *controls render and save here in v2; the behavior they drive ships in Spec B* |
| **Users** | User list (role, status, last active), invite, role change, delete user | Admin only |
| **Groups** | Group list + membership management | Admin: all. Analyst: groups they're in or created. Member: groups they're in. *(Group CRUD detail in Spec B; v2 reserves the IA slot and role-scoping.)* |

Notes:

- **Org defaults ships inert.** The toggles are present and persist their value, but nothing consumes that value until Spec B. "Allow public sharing" defaults **on**.
  - *Example:* Sarah (Admin) flips "Allow public sharing" off in v2. The toggle saves her choice, but because no sharing engine exists yet, the choice has no effect until Spec B reads it.
- **Note vs. Spec A:** Spec A's Users section listed an "ownership-transfer override." That control is **removed from v2** and moves to Spec B along with the rest of transfer.

---

## What ships in v2 vs. activates with Spec B

| Capability | Ships & functions in v2 | Activates with Spec B |
|---|---|---|
| Three-role tiers + hierarchy | ✅ | — |
| Sidebar + route gating | ✅ | — |
| Data-infra capability gates | ✅ | — |
| Settings IA + Users page + Org-defaults controls (inert) | ✅ | Org-defaults *behavior* |
| Ownership: owner column, owner-only delete, Admin effective-owner | ✅ | — |
| **Ownership transfer** | ❌ | ✅ |
| Settings > Users invite (create user with a role, no resource grant) | ✅ | — |
| Invitation role-tier rules | Documented as policy | Enforced in the share-modal entry point |
| Sharing-capability decoupling | Documented as policy | Functional when grants + share modal ship |

**The seam:** an Admin can onboard people with roles via Settings > Users the day v2 ships. Resource-level sharing, re-sharing, the share-modal invite path, **and ownership transfer** all light up with Spec B.

---

## Invitation Rules (policy in v2; enforced in Spec B's share modal)

**The rule:** The role you can invite someone *as* is capped by your own role. Anyone can invite as Member; only Admins can elevate.

| Inviter | Can invite as |
|---|---|
| **Admin** | Admin, Analyst, or Member |
| **Analyst** | Member only |
| **Member** | Member only |

**Example:** Priya (Analyst) shares a dashboard and types in a new email. She can only bring that person in as a Member. To make someone an Analyst or Admin, Sarah (Admin) has to do it.

**Entry points:**

1. **Settings > Users (ships in v2).** Admin-only page. The only invite surface live when v2 ships alone. No resource grant attached.
2. **Share modal (Spec B).** The day-to-day invite path. Analyst's Settings > Users page stays hidden — Analysts invite only through the share modal, which is why that path is essential to the Analyst onboarding story and lands in Spec B.

**Note on Members:** the "Member → Member only" row is a theoretical cap. In practice a Member never reaches an invite surface — Settings > Users is Admin-only, and the Spec B share modal requires an Edit grant to share, which a Member can never hold. So functionally, Members don't invite anyone.

**Interim note:** until Spec B ships, only Admins can invite (via Settings > Users), because the share-modal path doesn't exist yet. That's acceptable for the transitional window.

---

## Sharing Capability Decoupled from Role (policy in v2; functional in Spec B)

**The rule:** Among Analysts and Admins, the ability to re-share a resource comes from holding an Edit grant on it — not from the role itself. Members are capped to View, so a Member can never re-share.
**Example:** Priya (Analyst) holds an Edit grant on the "Field Performance" dashboard, so she can add the "Funders" group to it. Another Analyst with only View on that dashboard cannot re-share it. Anjali (Member) can never re-share, because she can never hold more than View.
**Why it matters:** It keeps "can I edit or share this" tied to the grant for the editor tiers, while keeping Members as clean, view-only consumers.

- A user with only View cannot re-share.
- A re-sharer caps to their own level: Edit can grant View or Edit; View can grant nothing.
- Members hold only View, so they fall in the "cannot re-share" case by construction.

---

## Migration & Transition

### Role mapping (locked)

| Current role | Migrates to | Net change |
|---|---|---|
| Account Manager | **Admin** | Renamed; capabilities preserved + ownership/governance formalized |
| Pipeline Manager | **Admin** | **Escalation** — gains user management, billing, org governance (see risk note) |
| Analyst | **Analyst** | Loses Data-infra **write** → read-only. No change to content function (was never role-capped). |
| Guest | **Member** | Renamed; broken permissions fixed. Sees all content View-only in the interim (see Interim Behavior). |

### Risk note — PM → Admin (wholesale, confirmed)

Wholesale Pipeline-Manager → Admin is **confirmed** by Product. It is a privilege escalation: Implementation Partners are often external and may serve multiple NGOs, and as Admins they gain user management, billing visibility, governance override, and effective ownership of every resource. No forced post-migration review ships; any Admin can downgrade an inherited Admin via Settings > Users. Flagged for leadership/security *awareness* at rollout, not as a blocker.

---

## Interim vs. End-State Behavior (the v2 → Spec B window)

Because v2 ships before the grant model, content visibility behaves differently in the window between the two.

| Role | Content visibility in interim (v2 live, Spec B not) | End state (Spec B live) |
|---|---|---|
| **Admin** | Sees and can edit/delete everything (effective owner) | Unchanged |
| **Analyst** | Sees all content; edit per current behavior | View/Edit per grants (+ floor) |
| **Member** | **Sees all *content* resources (Dashboards/Charts/Reports/Alerts) at View only. No create/edit/delete. Data section hidden.** | Sees only resources covered by floor + direct grants — **still View only, never Edit**. Data section hidden. |

**Why interim Members see everything (View-only):** rather than show a new Member an empty product on day one (no grants exist yet), they get read-only visibility across content until Spec B narrows it to what's actually shared with them. This avoids the "logged in, see nothing" cliff.

**The Data section is never visible to a Member** — interim or end state. The narrowing at Spec B launch (content lists shrinking to granted-only) is expected behavior, not a regression.

---

## User Stories (scoped)

### Story 1: Four roles collapse to three

**As an** Admin (Sarah), **I want** the role model reduced to Admin / Analyst / Member, **so that** I can reason about "who can do what" cleanly.

**Acceptance Criteria:**
- [ ] Role enum is `admin`, `analyst`, `member` (four-role enum retired).
- [ ] Migration maps AM→admin, PM→admin, analyst→analyst, guest→member.
- [ ] Role drives only sidebar visibility, Data-section capability, and Settings gating — never content View/Edit.
- [ ] No function-by-role logic is introduced anywhere in the content layer.

### Story 2: Analyst loses Data-infrastructure write

**As an** Admin (Sarah), **I want** Analysts to be read-only on Ingest/Transform/Warehouse/Pipelines/Orchestration, **so that** an M&E officer can't accidentally break data infrastructure.

**Acceptance Criteria:**
- [ ] Analyst has no write on any Data section (server-enforced).
- [ ] Analyst sees Data sections rendered read-only (no Create/Edit/Delete/Run affordances).
- [ ] Member sees no Data section at all.
- [ ] Existing Analyst users keep full dashboard/chart/report building; only their infra access drops to read-only.

### Story 3: Sidebar and routes reflect my role

**As a** Member (James), **I want** to see only nav items I can use, **so that** the interface isn't cluttered with options I can't access.

**Acceptance Criteria:**
- [ ] Sidebar items are hidden (not greyed) when the role can't use them.
- [ ] Member sees only Dashboards, Charts, Reports, Alerts.
- [ ] Direct URL to a hidden route redirects to the first accessible page.
- [ ] A "No Access" page (with org Admin contact) shows when no accessible page applies.

### Story 4: Settings consolidated under one area

**As an** Admin (Sarah), **I want** warehouse, appearance, org defaults, users, and groups under one Settings area, **so that** I'm not hunting across the product for configuration.

**Acceptance Criteria:**
- [ ] All configuration lives under Settings, organized per the IA table.
- [ ] Org-wide globals (Warehouse, Appearance, Org defaults, Users) are Admin-only.
- [ ] Analyst/Member see only Groups, scoped to their membership (Analyst also sees groups they created).
- [ ] Org-defaults controls render and persist their value but are not consumed yet.
- [ ] Fewer than 5 "where did setting X go?" tickets in the first 2 weeks.

### Story 5: Ownership is recorded and enforced (no transfer yet)

**As an** Admin (Sarah), **I want** every resource to have an owner and owner-only delete, **so that** deletion is unambiguous and I have a governance escape hatch when staff leave.

**Acceptance Criteria:**
- [ ] Every content resource has an `owner` (FK to user).
- [ ] Migration backfills owner from creator metadata; un-attributable resources go to the oldest active Admin.
- [ ] Only the owner (or an Admin as effective owner) can delete a resource. Edit grants do not include delete.
- [ ] Admin effective-owner override is honored in the permission check.
- [ ] **No transfer-ownership UI ships** anywhere in v2 (resource menu or Settings). Reassignment is deferred to Spec B.

### Story 6: Admin onboards users via Settings > Users

**As an** Admin (Sarah), **I want** to create a user with a role and manage them, **so that** I can onboard my team the day v2 ships, before the share modal exists.

**Acceptance Criteria:**
- [ ] Settings > Users lists users with role, status, and last active.
- [ ] Admin can invite a user and assign Admin / Analyst / Member.
- [ ] Only Admins can assign Analyst/Admin tiers (role-tier gating enforced server-side).
- [ ] Admin can change a user's role and hard-delete a user.
- [ ] No resource grant is attached at invite (pure platform onboarding).
- [ ] The Users page is hidden for Analyst and Member.

### Story 7: Member is view-only everywhere

**As an** Admin (Sarah), **I want** Members to be strictly view-only across the whole product, **so that** I can onboard 30+ consumers (program staff, funders, leadership) without any risk of them changing or deleting anything.

**Acceptance Criteria:**
- [ ] A Member has no create, edit, delete, or share affordance on any content page (dashboards, charts, reports, alerts) — view and export only.
- [ ] The Data section (Ingest/Transform/Warehouse/Pipelines/Orchestration) is hidden from Members entirely.
- [ ] Server-side checks reject any create/edit/delete/share request from a Member, regardless of payload — the UI hiding is not the only guard.
- [ ] The view-only cap is permanent: it is enforced independent of any future Spec B grant. A Member with a grant sees more *resources*, never gains a higher *permission level*.

---

## Technical Scope

### DDP_backend (Django + Django Ninja)

| Change | Impact |
|---|---|
| Role enum | Collapse four roles to three (`admin`, `analyst`, `member`). Migration maps AM→admin, PM→admin, analyst→analyst, guest→member. |
| Analyst infra permissions | Remove write on Ingest/Transform/Warehouse/Pipelines/Orchestration; grant read-only. |
| Ownership | Add `owner` (FK to user) on every content resource. Backfill from creator metadata; fallback to oldest active Admin. Owner-only delete enforced server-side. Admin effective-owner override in the permission check. **No transfer endpoint in v2.** |
| Settings / org config | Consolidate config endpoints; add Org-defaults storage (`default_visibility_floor`, `allow_public_sharing` default true) — stored but not yet consumed (Spec B reads them). |
| Invite (Settings > Users) | Create-user-with-role endpoint; only Admins may assign Analyst/Admin tiers; delete user; role change. No resource-grant payload. |
| Route/permission gating | Server-side capability checks per role for Data-infra and Settings endpoints. |
| Member view-only cap | Server-side: reject any create/edit/delete/share request from a Member on any resource. The permission resolver caps a Member's effective level at View regardless of grants, so the cap survives into Spec B. |
| Hooks for Spec B | Permission resolver structured to accept resource grants later; `owner` consumed by Spec B's share/delete/**transfer** logic. |

### webapp_v2 (Next.js 15 + React 19)

| Change | Impact |
|---|---|
| Sidebar (`main-layout.tsx`) | `useUserPermissions()` filter by role; hide, don't grey. |
| Route middleware | Role-based guards + No Access page. |
| Settings | Re-IA per the IA table; Admin-only globals; Org-defaults controls (inert). |
| Settings > Users | Invite / role change / delete-user. **No ownership-transfer action** (deferred). |
| Data section | Read-only mode for Analyst; hidden for Member. |
| Member view-only UI | Members see no create/edit/delete/share affordances anywhere; content renders view-only. In v2, content lists show all resources (interim); Spec B narrows *which* resources show, but the view-only level never changes. |

### Migration scripts

- Role remap (AM/PM→admin, analyst→analyst, guest→member).
- Owner backfill + un-attributable triage list (fallback: oldest active Admin).
- Analyst infra-permission downgrade.
- No resource-share migration and **no ownership-transfer plumbing** in v2 (both are Spec B).

---

## Success Metrics

| Metric | Baseline | Target |
|---|---|---|
| Roles in the model | 4 | 3 |
| Analyst-caused infra (pipeline/transform/warehouse) breakages | Possible | Zero (write removed) |
| Resources with an assigned owner post-migration | 0% | 100% (after triage) |
| "Where did setting X go?" tickets post-Settings-consolidation | n/a | < 5 in first 2 weeks |
| Orgs that downgraded any inherited (PM→Admin) account | n/a | Monitor — signal on whether the escalation was unwanted |

---

## Open Questions

1. **Org-defaults controls shipping inert** — confirm with Engineering whether to render them in v2 or hold the entire Org-defaults section for Spec B, to avoid shipping non-functional toggles.
2. **Owner-left-org before Spec B** — confirmed acceptable that an Admin's effective-owner powers cover this gap until transfer ships. No action needed unless an org hits it in the window.

---

## Dependencies

- **Requires:** nothing — v2 is independently shippable end-to-end.
- **Note:** no user-facing communication plan ships with v2 — migration runs without a staged comms rollout. Re-evaluate at Spec B if needed.
- **Enables:** Spec B (Resource Sharing). Spec B depends most on two pieces v2 lands: the `owner` column and the Admin effective-owner override. Spec B also builds the share modal, the grant engine, groups CRUD, **and ownership transfer**, and consumes the inert Org-defaults controls.

---

## Implementation Order

```
1. Role enum collapse + migration (AM/PM→Admin, Analyst→Analyst, Guest→Member)   → backend, independent
2. Analyst infra-permission downgrade + Data read-only/hidden rendering           → backend + frontend
3. Sidebar + route gating + No Access page                                        → frontend
4. Settings consolidation IA + Org-defaults controls (inert)                      → frontend + backend
5. Ownership: owner column, backfill, owner-only delete, Admin override           → backend + frontend
   (NOTE: no transfer — deferred to Spec B)
6. Settings > Users invite surface                                                → backend + frontend
```

v2 is independently shippable end-to-end. Resource-level sharing, the share modal, grant-driven content function, **and ownership transfer** arrive with Spec B; until then, content visibility follows the Interim Behavior table.
