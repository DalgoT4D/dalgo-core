# Implementation Plan — Admin Portal v1 (all four features)

**Status:** Draft v1 — for engineering review
**Spec:** `features/admin-portal/v1/spec.md`
**Research:** `features/admin-portal/v1/research.md`
**Date:** 2026-07-10
**Owner:** Veekshitha Nelluru (DMP 2026) · Issue #1254

**Acronyms:** HLD (High-Level Design) · LLD (Low-Level Design) · FK (foreign key — a DB column pointing at another row) · RBAC (role-based access control) · JWT (the signed login token) · SWR (a React data-fetching hook) · OrgUser (the row linking one user to one org, with their role) · PII (personally identifiable information).

> **Read this first.** Everything in Dalgo today is **single-org** — every user/org action reads the caller's own org from the `x-dalgo-org` header. This portal is **cross-org**: a Dalgo ops person acts on orgs they don't belong to. So the heart of this plan is a **new, platform-admin-gated, org-parameterized API layer** that reuses the existing org/user core functions. See research §2.

---

## 1. Overview

**What we're building:** An in-app `/admin` section, visible only to platform admins, where the Dalgo ops team onboards orgs and manages the users inside any org — no engineer, no database console.

**Scope of this plan:** all four v1 features, as four tracks.

| Track | Feature | Status |
|---|---|---|
| **A** | Org Onboarding + user management | **Shipped** (M1–M4). One scoped change outstanding: entry & landing — §9. |
| **B** | Broadcast Notifications | Planned — §10 |
| **C** | Feature Flags per Org | Planned — §11 |
| **D** | Airbyte & Pipelines (read-only) | Planned — §12 |

Tracks B, C, and D are independent of one another and can be sequenced in any order. All three depend on Track A's shipped admin shell and platform-admin guard.

**Services affected:**

| Service | Role in this feature |
|---|---|
| DDP_backend (Django + Django Ninja) | New admin API, the platform-admin guard, `Org.is_active` + per-org user active field, `/currentuserv2` change |
| webapp_v2 (Next.js 15) | The `/admin` section, admin sidebar, AdminGuard, admin hooks + screens |
| prefect-proxy | **Not touched** in Week 1 |

**Scope decisions confirmed with the team (2026-07-10):**

| Decision | Choice |
|---|---|
| Org retire | **Deactivate only** (reversible). Permanent delete deferred. |
| Deactivate user | **Per-org** active flag (new schema on OrgUser). |
| Remove user with content | **Keep cascade, warn first** (show dashboards/charts that will be deleted). |
| Create org | **Create the org, then invite** its first admin on the Users tab. |

> **Spec reconciliation:** The spec's Story 7 / Flow F / "Delete Org" dialog described **permanent delete** as Week 1. The team chose **deactivate-only** for Week 1, so permanent delete and its cascade dialog move to a later slice. Recommend updating the spec to match (noted in §8).

---

## 2. Blast Radius

Primary entities changed: **Organization** and **OrgUser** (from `docs/domain-map.md`). Organization is consumed by *every* other entity (all data is org-scoped); OrgUser is consumed by content via `created_by`. Below is every 1-hop and 2-hop surface and its confirmed status.

| Surface | Hop | Why affected | Status | Notes |
|---|---|---|---|---|
| **Organization** | 0 | Create / edit / deactivate | **In scope** | New `is_active` field; deactivate blocks login. Delete deferred. |
| **OrgUser** | 0 | Invite / role / deactivate / remove | **In scope** | New per-org active field; cross-org via new endpoints. |
| **Invitation** | 1 | Cancel a pending invite | **In scope** | Cancel = delete row; scope by org in the new endpoint. |
| **Dashboard** | 1 | `created_by` CASCADE — deleted when its creator is removed | **In scope (warn)** | Remove-user dialog shows the count. No FK change in v1. |
| **Chart** | 1 | `created_by` CASCADE — deleted when its creator is removed | **In scope (warn)** | Same warning path as Dashboard. |
| **ReportSnapshot** | 1 | `created_by` SET_NULL — orphaned, not deleted | **In scope (note)** | Safe; just note the inconsistency. |
| **Login / auth (all app surfaces)** | 1 | Deactivating an org or a per-org user must block access | **In scope** | Enforced at JWT permission-load. See §5. |
| Warehouse, Source, Transform, Pipeline, Data Quality | 2 | Torn down by org **delete** cascade | **Deferred** | Only relevant to permanent delete, which is deferred. |
| Notification, NotificationRecipient | 1 | Broadcast notifications | **In scope — Track B** | New admin authoring path + persisted audience. Existing consumption surface unchanged. See §10. |
| OrgFeatureFlag | 1 | Feature-flag toggles | **In scope — Track C** | Model already exists; adds a write path only. **Not** OrgPreferences or OrgPlans — see §11.2. |
| Airbyte connection status / Prefect run history | 2 | Airbyte & Pipelines viewer | **In scope — Track D** | Read-only, org-parameterized reads. Two live side-effect hazards — see §12.3. |
| Share link, Metric, KPI, Explore, Alert | 2+ | — | **Not affected** | Metric/KPI models don't exist in this repo. Others are downstream of content this feature doesn't render; the portal manages user/org records, not their data. |

> **The rule:** The portal manages **records** (orgs, users, invites), not an NGO's **data** (dashboards' contents, warehouse rows).
> **Example:** Meera can remove Priya from Akshara, but the portal never shows Akshara's "Field Performance" dashboard's numbers.
> **Why it matters:** It keeps the cross-org blast radius small — the only content the portal can destroy is via the remove-user cascade, which is gated behind a counted warning.

---

## 3. High-Level Design (HLD)

### 3.1 The one big idea: a cross-org admin API

```
Browser (/admin/*)                         DDP_backend
──────────────────                         ───────────
AdminGuard (client)  ──JWT + request──►  @platform_admin_required   ← NEW guard
  hides link, bounces                       reads UserAttributes.is_platform_admin
  non-admins                                     │ not admin → 403
        │                                        ▼
        │                              /api/v1/admin/orgs/{id}/...   ← NEW router
        ▼                                        │  takes org_id explicitly
  useAdminPortal hooks ───────────────►  reuses create_organization(),
  (org_id in the URL, not the header)      invite_user_v1(), delete_orguser_v1()
                                           but on the TARGET org, not request.orguser.org
```

> **The rule:** The admin endpoints are gated by the global `is_platform_admin` flag and take the target org in the URL — not the `x-dalgo-org` header.
> **Example:** `GET /api/v1/admin/orgs/42/users` returns org 42's users because Arjun is a platform admin, even though Arjun has no OrgUser row in org 42.
> **Why it matters:** The existing `@has_permission` system can't express "works across all orgs" (research §2). This new layer is the only correct way to do cross-org.

### 3.2 New / changed API endpoints

All under `/api/v1/admin/`, all gated by the new `@platform_admin_required`. Reuse existing core functions, passing the target `Org` explicitly.

| Method | Endpoint | Reuses | Purpose |
|---|---|---|---|
| GET | `/api/v1/admin/orgs` | new query | List all orgs (name, plan, user count, active) |
| POST | `/api/v1/admin/orgs` | `create_organization` + `create_org_plan` | Create an org (name, slug, viz_url, plan) |
| GET | `/api/v1/admin/orgs/{id}` | new query | Org detail (Overview facts) |
| PUT | `/api/v1/admin/orgs/{id}` | new update | Edit org basic details |
| POST | `/api/v1/admin/orgs/{id}/deactivate` | new | Set `is_active=False` (reversible) |
| POST | `/api/v1/admin/orgs/{id}/reactivate` | new | Set `is_active=True` |
| GET | `/api/v1/admin/orgs/{id}/users` | list-users query | List an org's users + pending invites |
| POST | `/api/v1/admin/orgs/{id}/users/invite` | `invite_user_v1` (org-param variant) | Invite a user to the org |
| PUT | `/api/v1/admin/orgs/{id}/users/{ouid}/role` | role-change logic | Change a user's role |
| POST | `/api/v1/admin/orgs/{id}/users/{ouid}/deactivate` | new (per-org flag) | Deactivate a user **in this org only** |
| POST | `/api/v1/admin/orgs/{id}/users/{ouid}/reactivate` | new | Reactivate in this org |
| GET | `/api/v1/admin/orgs/{id}/users/{ouid}/removal-impact` | count query | Count dashboards/charts that removal would delete |
| DELETE | `/api/v1/admin/orgs/{id}/users/{ouid}` | `delete_orguser_v1` (org-param variant) | Remove user from org (cascades content) |
| DELETE | `/api/v1/admin/orgs/{id}/invitations/{iid}` | new (org-scoped) | Cancel a pending invitation |
| GET | `/api/v1/admin/stats` | new | Dashboard counts: total orgs, total users |

**Changed existing endpoint:** `GET /currentuserv2` (`user_org_api.py:62`) — add `is_platform_admin` to `OrgUserResponse` so the client can render the entry link + AdminGuard.

> **Deferred endpoints (do not build in Week 1):** `DELETE /orgs/{id}` (permanent delete), notifications, feature flags, Airbyte/pipeline reads.

### 3.3 External-service touchpoints

- **Create org** calls Airbyte (`setup_airbyte_workspace_v1`) — slow, can fail; UI needs loading + error states (research §3).
- **Deactivate org** is DB-only in Week 1 (flag flip + login block). No Airbyte/Prefect call.
- **Prefect-proxy:** untouched.

---

## 4. Low-Level Design (LLD)

### 4.1 Data model changes (DDP_backend)

**Migration A — `Org.is_active`:**
```python
# ddpui/models/org.py  (class Org, near line 123)
is_active = models.BooleanField(default=True)
```
- Migration backfills all existing orgs to `True`.
- Index not required (low row count — tens of orgs).

**Migration B — per-org user active flag on OrgUser:**
```python
# ddpui/models/org_user.py  (class OrgUser, near line 69)
is_active = models.BooleanField(default=True)   # per-(user, org); distinct from User.is_active
```
> **The rule:** This new flag is per-org; it does **not** touch `User.is_active`.
> **Example:** Deactivating Priya in Akshara sets *Akshara's* OrgUser row `is_active=False`; her Bhumi OrgUser row stays `True`, so she still logs into Bhumi.
> **Why it matters:** It fixes the global-logout footgun (research §4) — the whole reason the team chose the per-org design.

- Backfill: set `OrgUser.is_active = user.is_active` on migrate, so existing globally-disabled users start disabled everywhere (safe default), then per-org divergence happens going forward.
- Surface `is_active` in the users-list response (`from_orguser`, `orguserhelpers.py:28`) as the row's Status.

**No FK changes in v1.** Dashboard/Chart `created_by` stay `CASCADE` (team chose "accept + warn").

### 4.2 Auth: the platform-admin guard

New decorator, mirroring `@has_permission` (`ddpui/auth.py:30-51`):
```python
# ddpui/auth.py
def platform_admin_required(view):
    def wrapper(request, *args, **kwargs):
        ua = UserAttributes.objects.filter(user=request.orguser.user).first()
        if not (ua and ua.is_platform_admin):
            raise HttpError(403, "platform admin access required")
        return view(request, *args, **kwargs)
    return wrapper
```
- The JWT still authenticates the human; the guard adds the cross-org check.
- Applied to **every** `/api/v1/admin/*` endpoint.

**Login enforcement for deactivated org / user** — in the middleware that loads permissions (`auth.py:140-142`, permission-load step):
```
resolve OrgUser for x-dalgo-org
  → if OrgUser.is_active is False  → treat as no access (empty permissions / 403)
  → if OrgUser.org.is_active is False → same
```
> **The rule:** A deactivated org or a per-org-deactivated user gets no permissions loaded, so every gated endpoint 403s.
> **Example:** After Arjun deactivates Akshara, Sarah (Akshara Admin) logs in and every Akshara API call returns 403 — she can't use the app for that org. Her Bhumi access is unaffected.
> **Why it matters:** Deactivation must be enforced server-side, not by hiding UI — otherwise a deactivated org's users keep working via direct API calls.

### 4.3 API design — request/response shapes (Django Ninja schemas)

Example, create org:
```python
class AdminCreateOrgSchema(Schema):
    name: str
    slug: str | None = None        # slugified from name if omitted
    viz_url: str | None = None
    base_plan: str = "Free Trial"  # OrgPlanType

class AdminOrgSchema(Schema):       # response
    id: int
    name: str
    slug: str
    base_plan: str
    is_active: bool
    user_count: int
```
Error codes: `400` (duplicate slug / invalid email), `403` (not platform admin, from the guard), `404` (org/user not found), `502` (Airbyte provisioning failed on create).

Removal-impact response (drives the warning dialog):
```python
class RemovalImpactSchema(Schema):
    dashboards_deleted: int
    charts_deleted: int
    reports_orphaned: int
```
Counts come from `Dashboard.objects.filter(created_by=ou).count()` etc.

### 4.4 Backend logic — reuse, don't rewrite

| New admin endpoint | Reuses | Change needed |
|---|---|---|
| Create org | `create_organization` (`orgfunctions.py:19`) + `create_org_plan` | none — pass the schema through |
| Invite user | `invite_user_v1` (`orguserfunctions.py:205`) | extract an org-param variant: `invite_user_to_org(target_org, inviter, payload)` so it doesn't read `request.orguser.org` |
| Remove user | `delete_orguser_v1` (`orguserfunctions.py:179`) | org-param variant keyed on `target_org` |
| Change role | `post_modify_orguser_role` logic (`user_org_api.py:342`) | org-param variant |
| Deactivate user | new | set `OrgUser.is_active` (not `User.is_active`) |

> **The rule:** Refactor the org-scoped core functions to accept a target org, then call them from both the existing single-org endpoints and the new admin endpoints.
> **Example:** `invite_user_to_org(org=Akshara, inviter=Arjun, payload=...)` is called by the admin portal; the old `invite_user_v1` becomes a thin wrapper passing `request.orguser.org`.
> **Why it matters:** One code path for "invite a user" keeps the invite-cap and validation rules identical in both surfaces — no drift.

**Invite cap note:** the cap (`orguserfunctions.py:220-222`, inviter level ≥ invitee level) assumes an inviter role. A platform admin creating invites has no org role in the target org. Decision for the org-param variant: **a platform admin may invite at any role** (Admin/Analyst/Member) — the cap check is skipped when the caller is a platform admin. (Flagged as a confirm in §8.)

### 4.5 Frontend components (webapp_v2)

**Shell change (the gotcha from research §6):**
```
components/client-layout.tsx
   add branch:  pathname.startsWith('/admin')
                  → <AuthGuard><AdminLayout>{children}</AdminLayout></AuthGuard>
```
- `AdminLayout` = new component with the admin sidebar (Home, Organizations, Notifications, Feature Flags). Notifications + Feature Flags render as "coming soon" placeholders.
- `AdminGuard` (inside AdminLayout or wrapping it): reads `is_platform_admin` from the auth store; if false, `router.replace('/')`.

**Nav link** — in `getNavItems()` (`main-layout.tsx:91-231`), append an "Admin Portal" item with `hide: !isPlatformAdmin`, thread `isPlatformAdmin` into the call (mirrors the `hide: !isFeatureFlagEnabled(...)` pattern at `:130`).

**New pages / components:**

| Path | Mirrors | Purpose |
|---|---|---|
| `app/admin/page.tsx` | `kpis/kpi-page.tsx` card grid | Dashboard: stat cards + recent orgs |
| `app/admin/organizations/page.tsx` | `UsersTable.tsx` | Orgs list: search + status filter |
| `app/admin/organizations/new/page.tsx` | existing forms | Create-org form |
| `app/admin/organizations/[id]/page.tsx` | tabs pattern | Org detail: Overview / Users / Airbyte(placeholder) / Pipelines(placeholder) |
| `components/admin/AdminLayout.tsx` | `main-layout.tsx` | Admin sidebar shell |
| `components/admin/AdminGuard.tsx` | `auth-guard.tsx` | Client redirect for non-admins |
| `components/admin/OrgUsersTable.tsx` | `UsersTable.tsx` | Org-parameterized users table |
| `components/admin/InviteUserDialog.tsx` | `settings/.../InviteUserDialog.tsx` | Invite (takes org id) |
| `components/admin/ChangeRoleDialog.tsx` | inline role edit | Change role |
| `components/admin/RemoveUserDialog.tsx` | `DeleteUserDialog.tsx` | Remove — shows deletion count |
| `hooks/api/useAdminPortal.ts` | `useUserManagement.ts` | SWR hooks calling `/api/v1/admin/*` |

> **The rule:** The admin hooks put the org id **in the URL**, not the `x-dalgo-org` header.
> **Example:** `useSWR('/api/v1/admin/orgs/42/users', apiGet)` fetches org 42's users regardless of which org is selected in `localStorage`.
> **Why it matters:** The existing user-mgmt hooks are current-org-bound (research §6); reusing them would show the wrong org's users.

### 4.6 Data flow — remove a user (the riskiest action)

```
Meera clicks "Remove" on Priya (org 42)
  → GET /api/v1/admin/orgs/42/users/{priya}/removal-impact
  → dialog: "This will also delete 3 dashboards and 5 charts Priya created"
  → Meera confirms
  → DELETE /api/v1/admin/orgs/42/users/{priya}
  → delete_orguser_to_org(org=42, target=priya)  (hard delete; CASCADE fires)
  → row disappears from OrgUsersTable
```

---

## 5. Security Review

| Area | Finding / plan |
|---|---|
| **Authorization** | Every `/api/v1/admin/*` endpoint carries `@platform_admin_required` (reads `UserAttributes.is_platform_admin`). This is the *only* thing standing between an org Admin and cross-org data — it must be on every route. Add a test that a non-platform-admin gets 403 on each. |
| **Two layers** | Client AdminGuard is UX only (hides link, redirects). Real enforcement is the backend guard. Never rely on the client. |
| **Input validation** | All inputs via Django Ninja schemas (Pydantic): org name/slug, email, role uuid, plan enum. Reject duplicate slug (`400`), invalid email (`400`). |
| **Multi-tenant leak** | The whole point of the guard: without it, org-id-in-URL endpoints would let any authenticated user read any org. The guard + org-id lookups (404 on missing) are the isolation. Test cross-org access is refused. |
| **Sensitive data / PII** | The portal shows user emails and roles (PII) — already visible to org Admins today, now to platform admins across orgs. No new secret exposure (create-org handles Airbyte creds server-side via existing `create_organization`; nothing new surfaced to the client). |
| **Deactivation enforcement** | Deactivated org/user must be blocked at permission-load (§4.2), not just hidden. Test: a user in a deactivated org gets 403 on a normal app endpoint. |
| **Injection** | No raw SQL; all via the ORM. Counts use `.filter().count()`. |
| **Destructive action** | Remove-user cascades deletes. Guardrail: the counted warning + explicit confirm. Permanent org delete is deferred, so the heaviest destructive path isn't exposed in Week 1. |
| **Rate limiting** | Low-traffic internal tool (a handful of ops users). No new throttling needed beyond existing app defaults. |

---

## 6. Testing Strategy

**Backend (pytest):**
- Guard: non-platform-admin → 403 on every `/api/v1/admin/*` route; platform admin → 200.
- Org-scoped correctness: `GET /admin/orgs/42/users` returns org 42's users when the caller belongs to org 7 (proves cross-org via the guard, not the header).
- Create org: happy path creates Org + OrgPlans; duplicate slug → 400; Airbyte failure → rollback, nothing persisted (mock `setup_airbyte_workspace_v1`).
- Deactivate org: sets `is_active=False`; a user in that org then gets 403 on a normal endpoint (permission-load enforcement).
- Per-org user deactivate: Priya in Akshara `is_active=False` does **not** change her Bhumi OrgUser or `User.is_active`.
- Remove user: removal-impact count matches actual dashboards/charts; delete cascades them; reports orphaned (SET_NULL).
- Invite via admin: platform admin can invite as Admin/Analyst/Member (cap skipped); invitation row created with correct `invited_by.org`.
- Cancel invite: scoped to the target org (does not hit the loose global delete path).

**Frontend (Vitest + Playwright):**
- Vitest: `getNavItems` hides the Admin link when `isPlatformAdmin` is false; AdminGuard redirects a non-admin.
- Playwright E2E: a non-admin typing `/admin` is bounced to `/`; a platform admin sees the admin sidebar, creates an org, opens it, invites a user, and sees the row appear.

**Edge cases:** empty state (no orgs → zero counts + create CTA); org with only pending invites; removing the last Admin of an org (allow, but note); deactivating an already-inactive org (idempotent).

**Test data:** two orgs (Akshara, Bhumi), one shared user (Priya) in both, one platform admin (Arjun), one org Admin (Sarah) for the negative-authorization tests.

---

## 7. Milestones

Each milestone is independently shippable and reviewable as one PR.

#### Milestone 1: Platform-admin gate + client can see it
- **Deliverable:** The backend guard exists and `/currentuserv2` tells the client who's a platform admin. No portal yet.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] Add `@platform_admin_required` in `ddpui/auth.py`.
  - [ ] Add `is_platform_admin` to `OrgUserResponse` + `get_current_user_v2`.
  - [ ] Auth store + `useUserPermissions` expose `isPlatformAdmin`.
  - [ ] Backend tests: guard 403/200.
- **Acceptance:** A platform admin's `/currentuserv2` returns `is_platform_admin: true`; a stub `/api/v1/admin/ping` returns 200 for admins, 403 for everyone else.

#### Milestone 2: The `/admin` shell (guarded, empty)
- **Deliverable:** `/admin` renders the admin sidebar for platform admins; non-admins are bounced. Dashboard shows real total-orgs / total-users counts.
- **Services:** webapp_v2, DDP_backend (`/admin/stats`)
- **Key tasks:**
  - [ ] `/admin` branch in `client-layout.tsx` + `AdminLayout` + `AdminGuard`.
  - [ ] "Admin Portal" nav link gated by `isPlatformAdmin`.
  - [ ] `GET /api/v1/admin/stats` + dashboard stat cards (Total Orgs, Total Users; Notifications Sent / Feature Flags ON render as "coming soon" placeholders).
  - [ ] Playwright: non-admin bounced from `/admin`.
- **Acceptance:** Arjun sees the link and the dashboard with correct counts; Sarah sees no link and is redirected from `/admin`.

#### Milestone 3: Organizations — list, create, edit, deactivate
- **Deliverable:** Full org lifecycle minus permanent delete.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] Migration A: `Org.is_active` + backfill.
  - [ ] Deactivate/reactivate enforcement at permission-load.
  - [ ] Admin endpoints: list, create, detail, edit, deactivate, reactivate.
  - [ ] Orgs list page (search + status filter), create-org form, org detail Overview tab, recent-orgs table links.
  - [ ] Tests: create rollback on Airbyte failure; deactivate blocks login.
- **Acceptance:** Arjun creates "Bhumi," edits it, deactivates it (Bhumi users get 403), reactivates it.

#### Milestone 4: Users tab — invite, role, deactivate, remove, cancel invite
- **Deliverable:** Cross-org user management inside an org.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] Migration B: `OrgUser.is_active` + backfill + surface in list.
  - [ ] Org-param variants of invite / role-change / remove; per-org deactivate/reactivate; org-scoped cancel-invite; removal-impact count.
  - [ ] Org detail Users tab: table (Email, Role, Status incl. Pending), Invite / Change Role / Remove (with count warning) dialogs.
  - [ ] Tests: per-org deactivate isolation; removal cascade + count; admin invite cap skip.
- **Acceptance:** Meera invites a user to Akshara, changes their role, deactivates them in Akshara only, removes another user after seeing the deletion warning, and cancels a pending invite.

> **Track A (M1–M4) is shipped.** Outstanding Track A work: entry & landing (§9).
> **Tracks B, C, D** are planned in §10–§12 — mutually independent, sequenced by team priority.
> **Still deferred, not planned in v1:** permanent org delete + cascade dialog; in-portal management of who is a platform admin; backend enforcement of feature flags (§11.1).

---

## 8. Open Questions & Risks

**Open questions (need a team answer before the affected milestone):**

| # | Question | Affects | Default if unanswered |
|---|---|---|---|
| 1 | When a platform admin invites into an org, confirm the **invite cap is skipped** (admin may invite as any role). | M4 | Skip the cap for platform admins. |
| 2 | Backfill for Migration B: start `OrgUser.is_active` from `User.is_active` (globally-disabled users start disabled in all orgs)? | M4 | Yes — safe default. |
| 3 | Dashboard "Notifications Sent" / "Feature Flags ON" cards while those features are deferred — render as disabled "coming soon" tiles? | M2 | Yes — placeholders keep the mockup layout. |
| 4 | Org "edit" — which fields are editable (name, slug, viz_url, plan)? Slug is used in URLs/Airbyte; is it safe to change? | M3 | Allow name, viz_url, plan; **lock slug** post-create until confirmed. |
| 5 | Removing the **last Admin** of an org — allow, or block? | M4 | Allow, but surface a note. |

**Risks:**

| Risk | Mitigation |
|---|---|
| **The guard is the only cross-org wall.** A missing decorator on one route leaks every org's data. | Central router-level enforcement + a test that iterates all admin routes asserting 403 for non-admins. |
| **Create-org calls Airbyte** — slow/failure surface. | Real loading + error UI; backend already rolls back on Airbyte failure. |
| **Remove-user deletes dashboards/charts** (CASCADE kept). | Counted warning + explicit confirm. Revisit switching `created_by` to SET_NULL in a later slice. |
| **Deactivation enforcement missed** would let a deactivated org keep working via API. | Enforce at permission-load, not UI; explicit test. |
| **Spec drift:** spec still lists permanent delete as Week 1. | Update `spec.md` Story 7 / Flow F to mark permanent delete deferred (recommended follow-up). |

---

## 9. Track A change — entry & landing

**This is a change to shipped code, not a new feature.** M1–M4 are live: `AdminGuard`, `AdminLayout`, `useAdminPortal`, the nav link, and the org-detail tabs all exist. This track modifies three existing files and generalizes one existing endpoint.

### 9.1 Problem

A Super Admin lands on the normal app on every sign-in and must click "Admin Portal" each time. Login hardcodes the destination (`app/login/page.tsx:63`), as does the root route (`app/page.tsx`). Nothing consults `is_platform_admin`, and `AuthGuard` captures no return URL (`components/auth-guard.tsx:90`), so a deep link into `/admin` bounces through login and lands on the normal app.

### 9.2 Approach — generalize the existing resolver

Dalgo already resolves where a user should land (research §9). We extend that from *which dashboard* to *which section*, rather than adding a parallel mechanism.

```
sign-in
  → AuthGuard: authentication + org selection resolve   (unchanged)
  → landing resolution: which SECTION?                  (extended)
       explicit destination requested?  → honor it, stop
       recorded preference = admin      → /admin
       recorded preference = app        → normal app landing
       none                             → normal app landing
  → within the normal app, existing dashboard-level landing resolution runs as today
```

> **The rule:** section resolution sits *above* the existing dashboard resolution and never replaces it. An admin resolved into the normal app still gets their personal landing dashboard.
> **Why it matters:** it keeps one mechanism. Two independent "where should this user land" systems would eventually disagree.

**Persistence:** the preference is stored server-side alongside the existing landing preference on `OrgUser`, and is written when the user crosses sections via "Admin Portal" or "Back to Dalgo" — no separate setting. Deliberately **not** localStorage: `authStore.logout()` calls `localStorage.clear()` (`stores/authStore.ts:94`), so a client-side preference would reset on explicit logout but survive token expiry (research §9).

**Care required — shared endpoint.** `GET /api/dashboards/landing-page/resolve` is consumed today by `/impact` (`app/impact/page.tsx:19-62`). Generalizing it must be **additive**: existing response fields keep their meaning, the section field is additive, and `/impact` behavior is unchanged when the caller is not a platform admin. Existing resolver tests must pass untouched.

### 9.3 Code changes

| File | Change |
|---|---|
| `dashboard_native_api.py:599` (resolver) | Additive: return the resolved section alongside the existing dashboard fields |
| `models/org_user.py` | Additive field for the section preference, defaulting to "app"; migration backfills existing rows to the default (so current behavior is preserved for everyone) |
| new: set-section endpoint | Records the section on crossing; platform-admin only |
| `components/auth-guard.tsx` | After auth + org selection resolve, apply section resolution — honoring an explicit destination first |
| `components/client-layout.tsx:58` | Unchanged routing branch; consumes the canonical admin accessor |
| `app/login/page.tsx:63`, `app/page.tsx` | Stop hardcoding the destination; defer to resolution |
| `hooks/api/usePermissions.ts:20`, `components/admin/AdminGuard.tsx:37` | **Canonicalize** `is_platform_admin` to one accessor (research §10.2) |

### 9.4 Acceptance criteria

- [ ] A Super Admin whose last section was the portal signs in and lands on `/admin` without clicking through.
- [ ] A Super Admin whose last section was the normal app lands on the normal app, with their existing personal landing dashboard resolution intact.
- [ ] A Super Admin with no recorded preference (first-ever sign-in) lands on the normal app.
- [ ] A deep link to any page — in either section — lands on that page; resolution does not override it. Explicitly covered: a shared dashboard link followed by a portal-preferring admin.
- [ ] Crossing sections via "Admin Portal" / "Back to Dalgo" updates the preference; the next sign-in reflects it.
- [ ] A non-admin is unaffected: same landing behavior as before this change, verified against the existing `/impact` tests.
- [ ] The admin shell never flashes before admin status is known, and no redirect is issued and then undone.
- [ ] `is_platform_admin` is read through exactly one accessor; a test asserts no second read path exists.

### 9.5 Risks

| Risk | Mitigation |
|---|---|
| **AuthGuard timing.** Resolving before `currentOrg` is set fires against a half-hydrated store (`auth-guard.tsx:152-154`) — the most likely way this breaks. Symptom is intermittent and environment-dependent: a wrong-section flash, or a redirect that undoes itself. | Resolution runs only after auth **and** org selection resolve. Explicit test for the slow-`/currentuserv2` case; assert no navigation occurs while resolving. |
| **Shared-endpoint regression.** The resolver is on the critical path for every user's `/impact`, not just admins. | Additive-only change; existing resolver tests must pass unmodified; non-admin behavior asserted unchanged. |
| **Deep links silently swallowed.** Easy to introduce, since login already discards return URLs today. | Dedicated test: deep link → login → original destination, for both sections. |
| **Preference set on a section the user can no longer reach** (admin flag revoked while preference = admin). | Resolution falls back to the normal app whenever the user is not currently a platform admin; the stored value is advisory, never authoritative. |

---

## 10. Track B — Broadcast Notifications

**Prerequisite (blocking): notification fan-out does not scale.** `create_notification()` loops recipients with a per-recipient `OrgUser.objects.get()` (`notifications_functions.py:142-148`) and enqueues **one Celery task per recipient** when scheduled (`:88-92`). An "all users" broadcast means thousands of synchronous SES calls inside the HTTP request, or thousands of queued tasks. **Track B depends on this being fixed first and does not attempt to fix it inline** — batching / single fan-out task / `bulk_create`, tracked as its own item.

*(A pre-existing authorization gap on the current notifications endpoints is tracked separately and is not a dependency of this track.)*

### 10.1 HLD

```
/admin/notifications  →  GET/POST /api/v1/admin/notifications/…   ← new, @platform_admin_required
                              │
                              ├─ reuses get_recipients()  (all three scopes already implemented)
                              ├─ reuses create_notification() fan-out  ← after the prerequisite lands
                              └─ writes persisted audience/scope       ← new column
                                        │
                       existing end-user surface (page, bell, unread count) — UNCHANGED
```

> **The rule:** the broadcast feature adds an *authoring* surface only. Delivery and consumption already work.

### 10.2 Scope

**Reuse unchanged:** `Notification` + `NotificationRecipient`; `get_recipients()` audience resolution including role and superset filters; SES email and Discord delivery; Celery ETA scheduling and revocation; the entire end-user consumption surface.

**Build:**
1. Admin-gated endpoints under `/api/v1/admin/notifications/` — create, list/history with org + author + sent/scheduled filters, cancel scheduled, delivery report.
2. `email_subject` on the create payload — currently unreachable over HTTP.
3. Persisted audience/scope on `Notification` — today audience is resolved to recipient IDs and discarded, so history cannot show what a broadcast targeted.
4. Server-derived author — replace the client-supplied `author` string with the authenticated actor.
5. A recipient-count preview endpoint — `get_recipients()` exists but is not exposed read-only; admins should see reach before sending.
6. Compose UI: audience selector (all users / all orgs / one org / role filter), org typeahead, message editor, urgent toggle, subject, schedule picker, confirm-with-count.
7. Delivery report UI — aggregate read-rate; the existing `/recipients` returns an unpaginated `{username, read_status}` list with no aggregation.

**Explicitly out:** recurrence (no field exists; Celery Beat + RedBeat and the alerts-dispatcher pattern at `tasks.py:1272` are the path if it's ever wanted); rich-text/HTML email (`send_html_message` exists at `awsses.py:56` but the notification path is plain-text); per-user targeting beyond the existing three scopes.

### 10.3 Blast radius

| Surface | Hop | Status |
|---|---|---|
| `Notification` | 0 | Additive columns (scope, author FK) |
| `NotificationRecipient` | 0 | Unchanged shape; volume rises sharply — see prerequisite |
| End-user notifications page / bell | 1 | **Unchanged** — broadcasts appear through the existing path |
| SES send volume | 1 | Materially increased. Bounce/complaint rate is an account-level reputation risk |
| Discord webhooks | 1 | Fires once per distinct org (`notifications_functions.py:150-158`) |
| Celery broker | 1 | Scheduled sends currently held as broker ETAs, not re-derivable from the DB if flushed |

### 10.4 Open questions

| # | Question | Default if unanswered |
|---|---|---|
| 1 | Does a broadcast respect `UserPreferences.enable_email_notifications` opt-out, or can urgent override it? | Respect opt-out always; in-app is the guaranteed channel |
| 2 | Should scheduled sends move from broker ETAs to a DB-derived dispatcher (mirroring `dispatch_due_alerts`)? | Yes — survives a broker flush |
| 3 | Is an org-scoped broadcast visible to a Super Admin who is not a member of that org? | Yes — consistent with the portal's cross-org model |
| 4 | Retention: do broadcasts age out? | No auto-deletion in v1 |

---

## 11. Track C — Feature Flags per Org

**Smallest of the three.** `OrgFeatureFlag` already exists with global/per-org override semantics, constraints, and tests (research §11.2). No new model. The read path already works end-to-end, so a toggle takes effect in-product with **no new gating code**.

### 11.1 Scope boundary — read this before implementing

> **A flag set to OFF hides UI. It does not disable the API.**
>
> There are **zero** production call sites for `is_feature_flag_enabled` — flags gate frontend rendering only. A user who knows the URL, or who calls the API directly, retains full access to a feature that is "off" for their org.
>
> **Backend enforcement is explicitly NOT in this track.** Do not describe, demo, or document this feature as a security or access-control boundary. It is a rollout and visibility tool. If "off" must mean "unavailable," that is separate work touching every gated endpoint, and it must be scoped and planned on its own.

### 11.2 HLD

```
/admin/feature-flags        ─┐
/admin/organizations/{id}   ─┴─→ GET/PUT/DELETE /api/v1/admin/…/flags   ← new write path
   (Flags tab)                          │                                  @platform_admin_required
                                        ▼
                          OrgFeatureFlag  (org=NULL → global default,
                                           org=<id> → override)          ← EXISTS, unchanged
                                        │
                     GET /api/organizations/flags → useFeatureFlags → 5 components   ← EXISTS, unchanged
```

**Do not conflate** with `OrgPreferences` (consent record with approver + date), `OrgPlans.features` JSON (commercial plan gating), or `Org.viz_url` (Superset provisioning). Three separate governance models; folding them together would be a mistake.

### 11.3 Build

1. `GET/PUT/DELETE /api/v1/admin/orgs/{org_id}/flags` + a global variant, under `@platform_admin_required`, validating `flag_name` against the registry.
2. **Serve the flag catalog.** `FEATURE_FLAGS` (`feature_flags.py:4-12`) is hardcoded in Python and hand-duplicated as a TS enum (`useFeatureFlags.ts:5-13`). Expose it so the two cannot drift.
3. **Tri-state (inherit / on / off)** — requires a delete path that does not exist: `disable_feature_flag` writes an explicit `False` row rather than deleting (`feature_flags.py:54-62`), so an override can never currently be cleared back to inheriting global.
4. `/admin/feature-flags` page (global defaults + per-org matrix) and a Flags tab on org detail. The nav item exists but is disabled and points at a 404 (`AdminLayout.tsx:22`).
5. Audit fields — `OrgFeatureFlag` has no `created_at`/`updated_at`/`changed_by`. Additive columns on the existing model, if "who turned this on" is wanted.
6. Fix or document `is_feature_flag_enabled(flag, org)`, which returns `None` with no global fallback (`:65-71`) — different semantics from the endpoint's merge, and a trap for anyone who later adds enforcement.

### 11.4 Open questions

| # | Question | Default if unanswered |
|---|---|---|
| 1 | Is up-to-5-minute propagation acceptable (`dedupingInterval`, `useFeatureFlags.ts:36`)? | Yes; revisit if ops finds it confusing |
| 2 | Tri-state, or simple on/off per org? | Tri-state — the model supports it and inherit-vs-explicit-off is a real distinction |
| 3 | Audit fields now or later? | Now — additive and cheap; retrofitting history is not possible |
| 4 | Can a Super Admin flip a **global** default from the portal, or org overrides only? | Org overrides only in v1; global stays CLI-only, as a blast-radius guard |

---

## 12. Track D — Airbyte & Pipelines (read-only)

### 12.1 HLD

```
/admin/organizations/{id}  →  GET /api/v1/admin/orgs/{org_id}/connections   ← new routes
      (Airbyte + Pipelines tabs)     .../pipelines                             @platform_admin_required
                                     .../pipelines/{deployment_id}/runs
                                            │
                          delegates to ALREADY org-parameterized services
                          (get_connections(org), PipelineService.get_pipelines(org), …)
                                            │  ← with cleanup side-effects DISABLED (§12.3)
                          data: live Airbyte + live Prefect + our AirbyteJob / PrefectFlowRun tables
```

**Why new routes are structurally required:** `request.orguser` is resolved from `x-dalgo-org` filtered to the caller's own OrgUser rows (`auth.py:160-164`). A platform admin who is not a member of the target org **cannot** reach it via the header. Org-id-in-URL is the only option — the same conclusion Track A reached.

### 12.2 Scope

**Reuse:** the eight already-`(org, …)`-parameterized service functions (research §11.3). The API layer is a thin `request.orguser.org` shim over them, so each admin route is ~5 lines — the move `admin_api.py:305, 340, 425` already made.

**Frontend — reuse presentational only:** `SyncStatusCell`, `ConnectionRow`, `LogsTable`, `LogCard`. **Do not reuse** `ConnectionsList`, `PipelineList`, `PipelineRunHistory`, `PipelineOverview` — each owns its fetching and polls every 3s indefinitely while anything is locked; `ConnectionsList` runs a second manual poll loop on top (`connections-list.tsx:54-95`). New `useAdminOrgConnections(orgId)` / `useAdminOrgPipelines(orgId)` hooks with `refreshInterval: 0`.

### 12.3 Two hazards that must be handled first

> **Hazard 1 — "read-only" is not read-only.** `get_connections(org)` fires `delete_airbyte_connections.delay(...)` for connections missing or deprecated in Airbyte (`airbytehelpers.py:532-536`); `get_one_connection` does the same (`:553-555`). **An Airbyte outage while an admin browses an org would schedule real connection deletions in that org.** The admin read path must suppress cleanup — a `cleanup=False` parameter or a separate read function. This is the single most important item in this track.

> **Hazard 2 — it crashes on exactly the orgs admins look at.** `warehouse = OrgWarehouse.objects.filter(org=org).first()` (`:389`) is dereferenced unguarded as `warehouse.name` (`:489`). Today's single-org UI never exercises this; a cross-org admin list **will** hit orgs mid-onboarding with no warehouse. Guard before shipping.

### 12.4 Cost — the reason this is read-only and paginated

No caching or retry on either client; 30s default timeouts (`airbyte_service.py:33-86`, `prefect_service.py:43-60`).

| Read | Cost |
|---|---|
| Connections list | 1 live Airbyte round-trip + ORM. **Unpaginated** |
| Pipelines list | 1 live Prefect call + ORM. **Unpaginated** |
| Sync history | DB-only (`AirbyteJob`), paginated — cheap |
| Flow-run history | **N+1 external fan-out** — 1 Prefect graph call per run **plus** 1 Airbyte call per airbyte task per run (`pipeline_api.py:287-298`). ~40 sequential HTTP calls for 10 runs × 3 connections |
| Legacy history endpoint | Unbounded log recursion (`prefect_service.py:669-689`) — **do not use** |

Mitigations: no polling on admin routes; paginate the run view and cap page size; prefer the DB-backed v1 flow-run path (pure ORM, `prefect_service.py:483-532`); treat external failure as a partial-render empty state, never a page error.

**Freshness caveat to surface in the UI:** `PrefectFlowRun` is webhook-written plus a 6-hourly reconcile (`tasks.py:1278-1282`); `AirbyteJob` is webhook-written plus a daily 2-day-window job (`:1300-1304`). If a webhook is missed, admin views can lag by hours. Label the data's provenance rather than implying real-time.

### 12.5 Open questions

| # | Question | Default if unanswered |
|---|---|---|
| 1 | Is a fleet-wide view ("all failing syncs across all orgs") in scope, or strictly per-org? | Per-org only. Fleet-wide needs joins through `OrgTask.connection_id` / `OrgDataFlowv1.deployment_id` — neither table has an `org` column — plus an index review |
| 2 | Do admins need sync **log lines** (live Airbyte, slow), or is status + history enough? | Status + history; logs behind an explicit click |
| 3 | Should the AI log-summary feature be available in the portal? | No in v1 — it polls a Celery task every 3s |
| 4 | Show a "data as of" timestamp given webhook lag? | Yes |

---

## Next

Draft v1 saved. Review the plan and tell me what to revise — architecture, scope, milestones, anything. When ready, run `/engineering/execute-plan features/admin-portal/v1/plan.md` to implement.
