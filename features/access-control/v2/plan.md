# Access Control — Role System (Spec A) — Implementation Plan (v2)

**Status:** Draft v1 — for engineering review. Tell me what to revise.
**Spec:** [`spec.md`](./spec.md) (scoped from `../v1/access-control-spec-A-role-system-2026-06-02.md`)
**Research:** [`research.md`](./research.md)
**Date:** 2026-06-15

> **Acronyms:** RBAC (role-based access control), FK (foreign key), IA (information architecture),
> DQ (data quality), HLD (high-level design), LLD (low-level design), SES (AWS email service).
>
> **One-line glossary:**
> - **Role** — `admin` / `analyst` / `member` (+ internal `super-admin`). Gates sidebar + Data-infra only.
> - **Owner** — the user who created a content resource; only they or an Admin may delete it.
> - **Grant** — a per-resource View/Edit permission. **Spec B, not this plan.**
> - **Re-seed** — updating the `Role` / `Permission` / `RolePermission` rows that live in `seed/*.json`.

---

## 1. Overview

Collapse Dalgo's four org-facing roles into three (**Admin / Analyst / Member**), decouple role from
content function, gate the sidebar and routes by role, consolidate Settings, and add an **owner** to
each content resource. Per-resource sharing (grants) is deferred to Spec B.

**Services affected:**

| Service | Touched? | What |
|---|---|---|
| **DDP_backend** (Django + Django Ninja) | ✅ | Role re-seed + migration, owner column + backfill, owner-only delete, Org-defaults storage, invite role-tier cap, server-side role gating |
| **webapp_v2** (Next.js 15 + React 19) | ✅ | Role-filtered sidebar, route guard + No Access page, Settings IA, Settings > Users (transfer), Analyst read-only Data, interim Member view-only |
| **prefect-proxy** (FastAPI) | ❌ | No change — it has no user-role concept; orchestration gating is enforced in DDP_backend's pipeline/orgtask endpoints |

---

## 2. Blast Radius

Traversed from the primary entities — **OrgUser / Role** (role collapse + gating), the **`owner`
column** on content, and **OrgPreferences** (org-defaults). Every 1-hop and 2-hop consumer from the
domain map is listed, with its confirmed status.

| Surface | Hop | Why affected | Status | Notes |
|---|---|---|---|---|
| **OrgUser / Role / RolePermission** | 0 | The change itself — 4→3 roles, re-seed permissions | **in scope** | `super-admin` excluded from collapse (research §1) |
| **Source / Ingest** | 1 | Data-infra capability gate | **in scope** | Analyst read-only, Member hidden |
| **Transform (dbt)** | 1 | Data-infra capability gate | **in scope** | Analyst read-only, Member hidden |
| **Warehouse** | 1 | Data-infra capability gate | **in scope** | Analyst read-only, Member hidden. Warehouse is a *tab* in `/ingest`, not a route |
| **Pipeline** | 1 | Data-infra capability gate | **in scope** | Analyst read-only, Member hidden |
| **Orchestration / OrgTask** | 1 | Data-infra capability gate | **in scope** | Analyst read-only, Member hidden |
| **Data Quality check** | 1 | Not named in spec; confirmed Data-infra | **in scope** | Analyst read-only, Member hidden. Stays feature-flagged (confirmed 2026-06-15) |
| **Dashboard** | 1 | Content gating + gets `owner` | **in scope** | Owner + owner-only delete; interim Member View-only |
| **Chart** | 1 | Content gating + gets `owner` | **in scope** | Owner + owner-only delete; interim Member View-only |
| **ReportSnapshot (Report)** | 1 | Content gating + gets `owner` | **in scope** | Owner (`SET_NULL`) + owner-only delete; interim Member View-only |
| **Metric** | 1 | `app/metrics/` not in spec map | **in scope (gating only)** | Visible to all, Member View-only interim. **No `owner` column** — deferred (confirmed 2026-06-15) |
| **KPI** | 2 (via Dashboard/Metrics) | Same module as Metric | **in scope (gating only)** | Follows Metrics gating. No `owner` column — deferred |
| **Explore** | 1 | `app/explore/` not in spec map | **in scope** | Analyst + Admin only; hidden from Member (confirmed 2026-06-15) |
| **Alert** | 1 | In spec sidebar map (all roles) | **partially in scope** | Nav visible to all roles. **No `owner` column** (deferred) — Alerts is a parallel in-progress spec |
| **OrgPreferences / Organization** | 1 | New org-defaults fields | **in scope** | `default_visibility_floor`, `allow_public_sharing` (inert) |
| **Invitation** | 1 | Role-tier cap on invite | **in scope** | Reuse existing flow; cap by inviter role |
| **Notification** | 2 | Delivery to OrgUser | **unaffected** | Role collapse doesn't change delivery; recipients keyed by OrgUser, not role |
| **Share link (public)** | 2 | `is_public` + token views | **unaffected (this version)** | Unauthenticated views — no role applies. Per-resource public toggle + the inert "allow public sharing" global are **Spec B** |
| **Per-resource grants (View/Edit)** | — | The sharing engine | **out of scope** | **Spec B.** Spec A builds the seam (owner column + resolver extension point) but no grant model |

**Why some surfaces are NOT affected:**
- **Notification** — keyed to OrgUser recipients; collapsing roles doesn't rename or delete users, so no delivery path breaks.
- **Share link (public)** — these are token-based, unauthenticated views; there is no logged-in role to gate. The global "allow public sharing" toggle ships inert (stored, not read) this version.

---

## 3. High-Level Design (HLD)

### 3.1 How the pieces fit

```
                         ┌──────────────────────────────────────────┐
   re-seed (migration)   │  Role / Permission / RolePermission rows  │
   admin/analyst/member  │  (seed/*.json, cached in Redis)           │
                         └───────────────┬──────────────────────────┘
                                         │ read on every request
   login → /api/currentuserv2            ▼
        ↳ new_role_slug + permissions[]  @has_permission([...])  ← server-side lock
                 │                          (DDP_backend endpoints)
                 ▼
        auth store (Zustand)
                 │
     ┌───────────┴────────────┐
     ▼                        ▼
 getNavItems()          route guard
 .filter(visibleToRoles) (redirect / No Access)   ← frontend UX (hide, not lock)
```

### 3.2 Two layers of enforcement (state it once, apply everywhere)

**The rule:** the server is the lock; the frontend is the affordance.

**Example:** James (Member) gets no "Ingest" nav item (frontend hides it) **and** the ingest write
endpoints return 403 to him (`@has_permission`). If we only hid the nav, a crafted API call would
still write.

**Why it matters:** role gating that lives only in React is not access control — it's decoration.

### 3.3 Data flow — owner-only delete

```
DELETE /api/dashboards/{id}
   → fetch Dashboard (org=request.orguser.org)        # multi-tenant filter
   → allow if: requester == owner
              OR requester.role in {admin, super-admin}
   → else HttpError(403, "Only the owner or an admin can delete this")
```

The frontend mirrors this: the Delete item in the dashboard/chart/report dropdown only renders for
the owner or an Admin.

### 3.4 New / modified endpoints

| Method + path | New? | Purpose | Permission |
|---|---|---|---|
| `POST /api/dashboards/{id}/transfer-owner` | new | Reassign owner (owner or Admin) | owner-or-admin check |
| `POST /api/charts/{id}/transfer-owner` | new | Same for charts | owner-or-admin check |
| `POST /api/reports/{id}/transfer-owner` | new | Same for reports | owner-or-admin check |
| `GET /api/org/preferences` | extend | Return new org-defaults fields | existing |
| `PUT /api/org/preferences` | extend | Store org-defaults (inert) | Admin-only slug |
| `DELETE` on dashboard/chart/report | modify | Add owner-or-admin guard | owner-or-admin check |
| `POST` invite (existing) | modify | Confirm role-tier cap for 3 roles | existing cap at `orguserfunctions.py:217-218` |

No new endpoints for the role collapse itself — it's migration + re-seed.

### 3.5 Key design decisions & trade-offs

| Decision | Choice | Trade-off |
|---|---|---|
| Add new role slugs vs rename | **New slugs** (`admin`, `member`); migrate users; keep `analyst` | One grep-replace of frontend slug strings vs silent breakage on rename (research §2) |
| Resolver for Spec B | Keep slug-based `@has_permission` now; add a thin **owner check** + documented extension point | Don't build the grant engine early; just don't block it |
| Org-defaults home | Extend `OrgPreferences` | Avoids a parallel settings table (research §7) |
| Settings > Users | Extend existing UI | Re-skin, not rebuild (research §8) |

---

## 4. Low-Level Design (LLD)

### 4.1 Data model

**New roles (seed + migration).** Levels drive the invite hierarchy (research §3).

```
admin       level 3   (← Account Manager + Pipeline Manager)
analyst     level 2   (unchanged slug; permissions tightened)
member      level 1   (← Guest)
super-admin (internal; untouched)
```

**`owner` FK on three content models** — mirror the existing `created_by` definition in each model:

```python
# ddpui/models/dashboard.py  (and visualization.py, report.py)
owner = models.ForeignKey(
    OrgUser, on_delete=models.SET_NULL, null=True, blank=True,
    related_name="owned_dashboards",   # owned_charts / owned_reports
)
```

Use `SET_NULL` so an owner leaving the org doesn't cascade-delete content (matches ReportSnapshot's
existing `created_by` behavior — research §4).

**`OrgPreferences` new fields** (inert this version):

```python
# ddpui/models/org_preferences.py
default_visibility_floor = models.CharField(max_length=32, null=True, blank=True)
allow_public_sharing     = models.BooleanField(default=True)
```

### 4.2 Migrations (all need a reverse function — research + backend landmarks)

| # | Migration | Type | Template |
|---|---|---|---|
| M-a | Add `admin` + `member` roles; set levels | data | `0137_update_landing_page_permissions.py` |
| M-b | Re-seed RolePermission for the 3 roles (analyst loses infra write; member gets content-view) | data | `0137...` |
| M-c | Re-point `OrgUser.new_role`: AM→admin, PM→admin, analyst→analyst, guest→member; **skip super-admin** | data | `0137...` |
| M-d | Add `owner` column to Dashboard / Chart / ReportSnapshot | schema | `0063_permission_role_rolepermission.py` |
| M-e | Backfill `owner = created_by`, else oldest active Admin | data | `0137...` |
| M-f | Add `OrgPreferences.default_visibility_floor` + `allow_public_sharing` | schema | `0063...` |

End every role/permission data migration's forward function with
`set_roles_and_permissions_in_redis()` (research §10). Use `apps.get_model(...)`, never direct imports.

**Analyst permission downgrade (M-b detail).** Remove `can_create_*` / `can_edit_*` / `can_delete_*`
for sources, pipelines, dbt, orchestration, warehouse, data-quality. **Keep** the matching
`can_view_*` slugs. Member keeps only content-view slugs (`can_view_dashboards`, `can_view_charts`,
`can_view_reports`, plus metrics view) and no infra slugs.

### 4.3 API design

**Ownership transfer (representative):**

```
POST /api/dashboards/{id}/transfer-owner
Body:  { "new_owner_id": <orguser_id> }
Guard: requester == dashboard.owner OR requester.role in {admin, super-admin}
Check: new_owner.org == request.orguser.org   # multi-tenant (research §11)
200:   { "owner": <orguser_id> }
403:   "Only the owner or an admin can transfer ownership"
404:   dashboard not in requester's org
```

Schemas go in `ddpui/schemas/` as Ninja `Schema` classes; errors via `raise HttpError(...)`.

### 4.4 Backend logic

- **Owner-or-admin helper** — one function reused by every delete + transfer endpoint:
  `can_delete_or_transfer(orguser, resource) -> bool`. This is the Spec-B seam: later it also
  consults grants, but the call sites don't change.
- **Invite cap** — verify the existing level comparison at `orguserfunctions.py:217-218` enforces
  *strictly* that Analyst/Member can invite Member only (research §3 — confirm `>` vs `>=`).

### 4.5 Frontend components

| Component | Change | Location (frontend landmarks) |
|---|---|---|
| `NavItemType` | Add `visibleToRoles?: Role[]` | `components/main-layout.tsx:48` |
| `getNavItems()` | Filter by `new_role_slug` from auth store | `main-layout.tsx:91-231` |
| Route guard | New role-aware guard → redirect to first accessible page | extend `components/auth-guard.tsx` |
| `NoAccessPage` | New component with org-admin contact | `app/no-access/` (new) |
| `<PermissionGate>` | New central wrapper (>3 gated surfaces) | `components/permission-gate.tsx` (new) |
| Data section views | Read-only mode for Analyst (no Create/Edit/Delete affordances) | ingest / transform / pipeline / orchestrate / data-quality pages |
| Resource dropdowns | Gate Delete by owner-or-admin | dashboard/chart/report list + actions components |
| Ownership transfer UI | New action in resource menu + Settings > Users | `UserManagement.tsx` + resource actions |
| Settings IA | Add Warehouse / Appearance / Org-defaults / Groups slots; Admin-only globals | `app/settings/` (slots empty today) |
| Org-defaults controls | Render + persist; inert | new Settings page |
| Interim Member view | Content lists render all resources View-only | dashboard/chart/report/metrics list pages |

### 4.6 Integration points

- Frontend reads role from `/api/currentuserv2` → `new_role_slug` in the auth store; `useUserPermissions()` already exposes `hasPermission(slug)`.
- After migration, search-and-replace hardcoded slug strings (`'account-manager'`, `'pipeline-manager'`, `'guest'`) in webapp_v2 (research §2).

---

## 5. Security Review

| Concern | Assessment |
|---|---|
| **Auth on new endpoints** | Transfer-owner + org-defaults endpoints must use the owner-or-admin guard / Admin-only slug. No endpoint relies on frontend hiding. |
| **Server-side role gating** | The re-seed is the primary control: Analyst losing infra-write slugs means `@has_permission` returns 403 on infra writes regardless of UI. Verify each infra module's write routes carry the right slug. |
| **Input validation** | Transfer-owner body validated via Ninja `Schema`; `new_owner_id` must resolve to an OrgUser **in the same org**. |
| **Multi-tenant safety** | Every new fetch includes `org=request.orguser.org` (backend landmarks). Ownership transfer validates both resource and new owner belong to the requester's org (research §11). |
| **Privilege escalation (PM→Admin)** | Known, Product-confirmed (spec §11.3). Not a code vuln, but the migration grants real power — call out in release notes; Admins can downgrade individually. |
| **Cache staleness** | Stale Redis/per-user permission caches could briefly let an Analyst write infra post-migration. Mitigated by `set_roles_and_permissions_in_redis()` at migration end + token refresh; server check is authoritative (research §10). |
| **Sensitive data** | Warehouse credentials remain Admin-only in Settings; this plan tightens (not loosens) who can reach them. |
| **Injection** | No raw SQL added; all queries via Django ORM. |
| **Rate limiting** | Transfer-owner is low-frequency, Admin/owner-only — no new throttling needed. |

---

## 6. Testing Strategy

### Unit tests (pytest + pytest-django; template `test_dashboard_native_api.py`)
- Role migration: after `loaddata`, exactly `super-admin`, `admin`, `analyst`, `member` exist; AM/PM users land on `admin`, guest on `member`.
- Analyst permission set: has `can_view_*` infra slugs, lacks every infra `can_create/edit/delete`.
- Member permission set: content-view only; no infra slugs.
- Owner-only delete: owner → 200; non-owner Analyst → 403; Admin non-owner → 200; super-admin → 200.
- Ownership transfer: owner → 200; Admin → 200; non-owner → 403; cross-org `new_owner_id` → rejected.
- Backfill: `owner == created_by` where set; null `created_by` → oldest active Admin.
- Invite cap: Analyst inviting as Analyst → rejected; Admin inviting as Admin → allowed.
- Reverse migrations run clean (rollback).

### Frontend unit tests (Vitest)
- `getNavItems()` returns the right nav set per `new_role_slug` (Admin all; Analyst no Settings>Users; Member content-only, no Explore, no Data).
- `<PermissionGate>` shows/hides children by role.

### Integration / E2E (Playwright; `e2e/*.spec.ts`)
- Log in as each role → assert sidebar contents and that direct URL to a hidden route redirects (Member → `/dashboards`; no access → No Access page).
- Analyst opens a Data page → no Create/Edit/Delete buttons.

### Edge cases
- User with the legacy `guest` slug cached in an old token (pre-refresh) — server still blocks correctly.
- ReportSnapshot with null `created_by` (its FK is `SET_NULL`) → backfill to oldest Admin.
- Org with **no** active Admin during backfill (degenerate) — define fallback (flag for triage; see Open Questions).

---

## 7. Milestones

Ordered to match the spec's implementation order; each is independently shippable and reviewable.

#### Milestone 1: Role collapse + permission re-seed
- **Deliverable:** four org roles become three; users migrated; permission sets re-seeded; `super-admin` untouched.
- **Services:** DDP_backend.
- **Key tasks:**
  - [ ] Add `admin` + `member` roles with levels (M-a); keep `analyst`, `super-admin`.
  - [ ] Re-seed RolePermission: Analyst infra-write removed, Member content-view only (M-b).
  - [ ] Migrate `OrgUser.new_role` (M-c), excluding `super-admin`.
  - [ ] Call `set_roles_and_permissions_in_redis()`; implement reverse functions.
  - [ ] Unit tests for role/permission sets + rollback.
- **Acceptance:** tests green; a migrated AM user resolves to `admin`, a guest to `member`; Analyst can't write infra server-side.

#### Milestone 2: Analyst read-only Data + Member hidden
- **Deliverable:** Data section (Ingest/Transform/Warehouse/Pipelines/Orchestration/DQ) renders read-only for Analyst, hidden for Member; server rejects Analyst writes.
- **Services:** DDP_backend (verify slugs) + webapp_v2.
- **Key tasks:**
  - [ ] Confirm every infra write route carries a `can_create/edit/delete` slug.
  - [ ] Read-only rendering (hide Create/Edit/Delete affordances) on each Data page.
  - [ ] Hide Data nav for Member.
- **Acceptance:** Analyst sees Data, no write buttons, write API → 403; Member has no Data nav.

#### Milestone 3: Sidebar + route gating + No Access page
- **Deliverable:** role-filtered sidebar; direct-URL guard; No Access page; Explore hidden from Member.
- **Services:** webapp_v2.
- **Key tasks:**
  - [ ] `visibleToRoles` on `NavItemType`; filter `getNavItems()` by role.
  - [ ] Role-aware route guard → redirect to first accessible page.
  - [ ] `NoAccessPage` with org-admin contact.
  - [ ] Add central `<PermissionGate>`.
  - [ ] Replace hardcoded legacy slug strings.
- **Acceptance:** each role's sidebar matches the spec map; hidden-route URL redirects; Member can't reach Explore/Data.

#### Milestone 4: Settings consolidation + Org-defaults (inert)
- **Deliverable:** one Settings area; Admin-only globals; Org-defaults controls render + persist (inert).
- **Services:** DDP_backend + webapp_v2.
- **Key tasks:**
  - [ ] `OrgPreferences` fields + migration (M-f); extend GET/PUT preferences (Admin-only write).
  - [ ] Settings IA: Warehouse / Appearance / Org-defaults / Groups slots; Admin gating.
  - [ ] Org-defaults toggles persist; nothing consumes them.
- **Acceptance:** Admin sees all Settings; Analyst/Member see only scoped Groups; toggles save and reload.

#### Milestone 5: Ownership (column, backfill, owner-only delete, transfer, Admin override)
- **Deliverable:** Dashboard/Chart/Report have an owner; owner-only delete enforced; transfer + Admin override work.
- **Services:** DDP_backend + webapp_v2.
- **Key tasks:**
  - [ ] `owner` FK on three models (M-d); backfill (M-e).
  - [ ] `can_delete_or_transfer()` helper; wire into delete + transfer endpoints.
  - [ ] Transfer-owner endpoints (+ schemas, multi-tenant check).
  - [ ] Frontend: gate Delete by owner-or-admin; transfer UI in resource menu + Settings > Users.
- **Acceptance:** non-owner can't delete (403 + hidden UI); Admin can; transfer reassigns owner; 100% of backfilled resources have an owner.

#### Milestone 6: Settings > Users invite surface + comms
- **Deliverable:** Admin invite/role-change/delete + ownership-transfer override; invite role-tier cap confirmed; comms shipped.
- **Services:** DDP_backend + webapp_v2.
- **Key tasks:**
  - [ ] Confirm invite cap operator (`>` vs `>=`) for analyst-can't-elevate (research §3).
  - [ ] Surface ownership-transfer override in Users page.
  - [ ] T-7 emails + T-0 changelog modal + T+7 monitoring (per spec §11.2).
- **Acceptance:** Admin can onboard with any role; Analyst/Member capped to Member; affected users notified.

---

## 8. Open Questions & Risks

**Open questions** (resolve before/within implementation):
1. **Invite-cap operator** — is `orguserfunctions.py:217-218` `>` or `>=`? Must be strict enough that an Analyst can't invite an Analyst (research §3).
2. **Org-defaults edit permission** — new `can_edit_org_defaults` slug, or reuse an existing org-settings slug?
3. **Deprecated role rows** — delete `account-manager` / `pipeline-manager` / `guest` after migrating users, or keep as tombstones for rollback safety?
4. **Org with no active Admin at backfill** — what owner do un-attributable resources get if an org has zero active Admins? (degenerate but possible)
5. **Org-defaults inert-vs-hold** — spec's one open item: render the inert toggles now, or hold the whole Org-defaults section for Spec B? (Recommend render now — the IA slot is cheap and Spec B just adds the read path.)

**Risks:**
- **PM→Admin escalation** — real privilege grant (spec §11.3, Product-confirmed). Mitigation: release-note callout + per-user downgrade. Track the "orgs that downgraded" metric.
- **Cache staleness window** — brief post-migration window where old tokens carry old permissions; mitigated by Redis clear + authoritative server check (research §10).
- **Interim Member "sees all content View-only"** — at Spec B launch this **narrows** to granted-only. Expected, not a regression — must be communicated (spec §12).
- **Frontend slug drift** — missed hardcoded legacy slug string → a nav item mis-gates. Mitigation: grep audit in Milestone 3.

---

**Draft v1 saved.** Review the plan and tell me what to revise — architecture, scope, milestones, anything. When ready, run `/engineering/execute-plan features/access-control/v2/plan.md` to implement.
