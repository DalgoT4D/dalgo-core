# Research — Admin Portal v1 (Week 1: Org Onboarding + User Management)

**For:** `features/admin-portal/v1/plan.md`
**Date:** 2026-07-10
**Scope:** net-new findings from a direct read of DDP_backend and webapp_v2. This repo has **no** `backend-architecture/landmarks.md` or `frontend-architecture/landmarks.md`, so the reusable file:line facts live here.

**Acronyms:** FK (foreign key — a DB column pointing at another table's row) · RBAC (role-based access control — who can do what, decided by their role) · JWT (JSON web token — the signed login token) · SWR (a React data-fetching/caching hook) · OrgUser (the row linking one user to one org, carrying their role there).

> The whole feature turns on one fact: **everything in Dalgo today is single-org.** Every user/org function reads the caller's own org from the `x-dalgo-org` request header. A cross-org admin portal needs new, platform-admin-gated, org-parameterized endpoints. The rest of this file is the evidence for that and the pieces we can reuse.

---

## 1. Who is a "platform admin" — and why nothing enforces it yet

There are **two different "admin" concepts** in the codebase. They are easy to confuse.

| Concept | Where it lives | Scope | What it gates today |
|---|---|---|---|
| `UserAttributes.is_platform_admin` | `ddpui/models/org_user.py:31` (per-`User`) | **Global** (cross-org) | **Nothing.** Set by a command; read only into the login payload. |
| `super-admin` **role** (slug `super-admin`, level 5, pk 1) | `seed/001_roles.json:7`, `OrgUser.new_role` | **One org** (per OrgUser row) | Maps to the most permission slugs, via `@has_permission`. |

> **The rule:** The portal's gate is `UserAttributes.is_platform_admin` — a global boolean on the user, not the org-scoped `super-admin` role.
> **Example:** Arjun (Dalgo ops) has `is_platform_admin = True`, so he can act across Akshara and Bhumi. Sarah is `super-admin` **inside Akshara only** — that's an org role, and it does not let her touch Bhumi.
> **Why it matters:** If we gated the portal on the `super-admin` role, we'd be gating on a per-org role that can't express "works across all orgs." The global flag is the correct hook.

Key facts:
- `is_platform_admin` is toggled only by the management command `ddpui/management/commands/manage-user-attributes.py:23` (`--enable/--disable is_platform_admin`). No UI sets it. (Spec confirms managing the platform-admin set is out of scope for v1.)
- It is surfaced today only inside `lookup_users` (`ddpui/core/orguserfunctions.py:72`), which feeds the `POST /login/` response — **not** `/currentuserv2`.
- Grep across `ddpui/api/` for `is_platform_admin` as an authorization check → **no hits.** The field exists and is displayed but grants no power. This is the plumbing v1 must build.
- Django `is_superuser`/`is_staff` are **not used anywhere** (grep: no matches). Not a mechanism here.
- Sibling flag `UserAttributes.can_create_orgs` **does** gate org creation today (`user_org_api.py:547`).

---

## 2. The single-org obstacle (the core design driver)

**The rule:** No user/org function or endpoint accepts a target org. The acting org is chosen by the `x-dalgo-org` header in auth middleware (`ddpui/auth.py:62-64`, `:140-142`), then everything reads `request.orguser.org`.
**Example:** When Meera calls "list users," the backend returns users of whatever org her `x-dalgo-org` header names — it cannot list Bhumi's users unless Meera is herself an OrgUser of Bhumi.
**Why it matters:** A platform admin is usually **not** an OrgUser of the org they're fixing. So the portal cannot reuse the existing endpoints as-is; it needs endpoints that take an explicit `{org_id}` and are gated by `is_platform_admin` instead of by an org role.

Auth flow today:
```
login → JWT → CustomJwtAuthMiddleware.authenticate (auth.py:176-188)
            → picks the OrgUser for the x-dalgo-org header (auth.py:140-142)
            → loads that role's permission slugs into request.permissions (Redis-backed)
            → @has_permission(["can_..."]) (auth.py:30-51) checks the slug set
```
`@has_permission` only tests permission slugs for **one** org. It cannot express cross-org authority — that check is net-new.

---

## 3. Org model + lifecycle (what create / deactivate / delete map to)

**Org model** — `ddpui/models/org.py:123`.

| Field | Present? | Note |
|---|---|---|
| `name`, `slug` | ✅ | `slug` max_length 20, nullable |
| `viz_url`, `viz_login_type` | ✅ | the visualization/Superset URL |
| `airbyte_workspace_id`, `website` | ✅ | |
| `is_active` / status | ❌ | **No active/inactive field. "Deactivate org" is net-new schema.** |
| `plan` | ❌ on Org | lives on `OrgPlans` (OneToOne, `related_name="org_plans"`, `ddpui/models/org_plans.py:19`); `base_plan` ∈ {"Free Trial","Dalgo","Internal"}; `Org.base_plan()` reads it (`org.py:224`) |

**Create an org** — three entry points, all built on one core function:
- Core: `create_organization(payload: CreateOrgSchema)` — `ddpui/core/orgfunctions.py:19`. Takes `name, viz_url, website`; slugifies the name; **provisions an Airbyte workspace** (`setup_airbyte_workspace_v1`) and rolls back (`org.delete()`) if Airbyte fails. Plan is a separate call: `create_org_plan(payload, org)` (`orgfunctions.py:51`).
- API: `POST /v1/organizations/` — `post_organization_v1` (`ddpui/api/user_org_api.py:539`), gated `@has_permission(["can_create_org"])` **plus** an extra `UserAttributes.can_create_orgs is True` check (`:546-548`).
- Command: `createorganduser` (`ddpui/management/commands/createorganduser.py`) — creates org + user + OrgUser + sets `email_verified`/`can_create_orgs`. This is the bootstrap path in the README.

> **The rule:** Creating an org is not just a DB insert — it calls Airbyte to make a workspace.
> **Example:** When Arjun creates "Bhumi," the backend also spins up Bhumi's Airbyte workspace; if Airbyte is down, the org is rolled back and nothing is created.
> **Why it matters:** The create-org endpoint can be slow and can fail on an external service. The UI needs a real loading + error state, not an optimistic insert.

**Deactivate an org** — does **not** exist. No `is_active` field, no login enforcement. This is net-new: add the field + block login/API for users of a deactivated org.

**Delete an org** — exists, but it's heavy and has **no API**:
- `OrgCleanupService.delete_org()` — `ddpui/services/org_cleanup_service.py:349`. Cascade order: Prefect orchestrate pipelines → dbt/transform layer (+ GitHub repo, secrets) → warehouse (+ Airbyte connections/destinations, secrets) → Airbyte workspace → OrgUsers → EDR pipelines → Prefect blocks → org dir on disk → `org.delete()`.
- Only reachable via the `deleteorg` management command (`--yes-really`, else dry-run). No endpoint.
- Invitations aren't cleaned explicitly — they rely on DB `CASCADE` from `Invitation.invited_by` / `Org` FKs.

> **The rule:** Deleting an org tears down external systems (Airbyte, Prefect, secrets manager, files), not just database rows — and it's irreversible.
> **Example:** Deleting "Akshara" removes its Airbyte workspace, its Prefect deployments, its warehouse credentials, and its files on disk. There is no undo.
> **Why it matters:** This is why v1 ships **deactivate (reversible)** first and defers permanent delete. Wrapping `delete_org()` in a click needs strong guardrails.

---

## 4. User management (functions, endpoints, and the "active" trap)

All in `ddpui/core/orguserfunctions.py` and `ddpui/api/user_org_api.py`. All single-org (`request.orguser.org`).

| Action | Core fn / API | Location | Notes |
|---|---|---|---|
| Invite user | `invite_user_v1(orguser, payload)` | `orguserfunctions.py:205` | org = `orguser.org`; API `POST /v1/organizations/users/invite/` (`user_org_api.py:469`, `can_create_invitation`) |
| Change role | inline in `update_orguser_v1` / `post_modify_orguser_role` | `orguserfunctions.py:164`, `user_org_api.py:342` | `POST /organizations/user_role/modify/` (`can_edit_orguser_role`) |
| Deactivate user | `update_orguser_v1` with `payload.active` | `orguserfunctions.py:168-169` | **flips `User.is_active` — GLOBAL across every org** |
| Remove from org | `delete_orguser_v1(requestor, payload)` | `orguserfunctions.py:179` | hard-deletes the OrgUser row (`:200`); `POST /v1/organizations/users/delete` (`can_delete_orguser`) |
| List org users | — | `user_org_api.py:228` | `GET /organizations/users` (`can_view_orgusers`), includes inactive |
| Cancel invite | inline | `user_org_api.py:519` | `DELETE /users/invitations/delete/{id}` (`can_delete_invitation`) — **already lacks org scoping** |
| Invite cap | `if invited_role.level > orguser.new_role.level: reject` | `orguserfunctions.py:220-222` | inviter can invite at their level or below |

- **Invitation model** — `ddpui/models/org_user.py:142`. Fields: `invited_email`, `invited_by` (FK OrgUser, CASCADE), `invited_on`, `invite_code` (uuid string), `invited_new_role` (FK Role). **No status/expiry column** — "pending" just means the row still exists; "cancel" = delete the row; the org is derived via `invited_by.org`.
- **OrgUser model** — `ddpui/models/org_user.py:69`. **No `active` field.** "Active" is read from `User.is_active` (`orguserhelpers.py:28`). So per-org deactivation (your chosen design) requires a **new field on OrgUser** (e.g. `is_active`), plus surfacing it in the user list and enforcing it at login/permission-load.
- **`/currentuserv2`** — `get_current_user_v2` (`user_org_api.py:62`) returns `List[OrgUserResponse]` (one per org). Schema `OrgUserResponse` (`org_user.py:127`) does **not** include `is_platform_admin`. v1 must add it so the client can render the entry link + guard.

---

## 5. Removing a user can delete content (the cascade the spec missed)

`created_by` / `last_modified_by` FKs point at OrgUser. Because "remove from org" hard-deletes the OrgUser row, `on_delete` decides content fate:

| Content | FK behavior | Effect of removing the creator |
|---|---|---|
| Dashboard (`models/dashboard.py:116`) | `created_by` **CASCADE** | **Dashboard is deleted** |
| Chart (`models/visualization.py:60`) | `created_by` **CASCADE** | **Chart is deleted** |
| ReportSnapshot (`models/report.py:74`) | `created_by` **SET_NULL** | orphaned (kept) |
| Metric / KPI | — | **models do not exist in this repo** (grep: no `class Metric`/`class KPI`) |

> **The rule (your decision — "accept + warn"):** Removing a user still cascade-deletes their dashboards and charts; the confirm dialog must show the count first.
> **Example:** Removing Priya from Akshara deletes the 3 dashboards and 5 charts she created. The dialog says "This will also delete 3 dashboards and 5 charts" before Meera confirms.
> **Why it matters:** Silent deletion of an NGO's dashboards would be a trust disaster. The count query + warning is a hard requirement, not polish.

---

## 6. Frontend shell, auth signal, and reusable pieces (webapp_v2)

**Where the sidebar is decided — not the App Router.**
```
app/layout.tsx (root; no sidebar)
   └─ components/client-layout.tsx  ← branches on pathname
        ├─ public route  → bare
        └─ else          → <AuthGuard><MainLayout>{children}</MainLayout></AuthGuard>
                                           └─ MainLayout owns the sidebar
```
- `find app -name layout.tsx` → only `app/layout.tsx` + a no-op `app/change-password/layout.tsx`. Top-level sections (`app/dashboards/`, `app/settings/*`) have **no per-section layout**.
> **The rule:** A route-group `layout.tsx` will **not** replace the sidebar — the sidebar choice lives in `client-layout.tsx`'s pathname branch.
> **Example:** To make `/admin/*` show the admin sidebar instead of the app nav, add an `/admin` branch in `client-layout.tsx` that renders `<AuthGuard><AdminLayout>{children}</AdminLayout></AuthGuard>`.
> **Why it matters:** Copying the "just add a layout.tsx" pattern would silently keep the normal sidebar. This is the one architectural gotcha in the frontend.

**Nav link** — `NavItemType` (`components/main-layout.tsx:42-49`) has `hide?` but **no role field**. `getNavItems()` (`:91-231`) builds the array; render filters `.filter(item => !item.hide)`. Add an "Admin Portal" item and gate it with `hide: !isPlatformAdmin`, mirroring the existing `hide: !isFeatureFlagEnabled(...)` pattern (`:130`).

**Auth / platform-admin on the client:**
- `middleware.ts` does **no** auth gating (only iframe headers for `/share/*`). The guard is client-side; the backend must be the real enforcer.
- `stores/authStore.ts` OrgUser (`:15-25`) exposes `new_role_slug`, `permissions[]` — but **no platform-admin flag** (grep: none). Two existing de-facto signals used inconsistently: `new_role_slug === 'super-admin'` and `hasPermission('can_create_org')`. v1 should add a clean `is_platform_admin` to the currentuserv2 payload and use that.
- `useUserPermissions()` (`hooks/api/usePermissions.ts`) → `hasPermission/hasAnyPermission/hasAllPermissions`.

**API client** — `lib/api.ts`: `apiGet/apiPost/apiPut/apiDelete` (`:192-215`) via `apiFetch` (cookie auth, auto 401-refresh, injects `x-dalgo-org` from `localStorage.selectedOrg`). Canonical usage = SWR + hook-per-domain, e.g. `hooks/api/useUserManagement.ts` (`useSWR('/api/organizations/users', apiGet)`). Mirror this with a new `hooks/api/useAdminPortal.ts`.

**Reusable UI (all current-org-bound — need org-parameterized variants):**

| Need | Best example to mirror | Reuse note |
|---|---|---|
| Stat-card grid | `components/kpis/kpi-page.tsx`, `app/impact/page.tsx` | compose shadcn `Card`; no prebuilt metric tile |
| Searchable/filterable table | `components/settings/user-management/UsersTable.tsx` | popover filters + sort; strongest table pattern |
| Invite dialog | `components/settings/user-management/InviteUserDialog.tsx` | posts `{invited_email, invited_role_uuid}` |
| Destructive confirm | `components/settings/user-management/DeleteUserDialog.tsx` | shadcn `AlertDialog`, `bg-destructive` |

> **The rule:** The existing user-management components are hardcoded to the current org (they rely on the `x-dalgo-org` header, not an org param).
> **Example:** `UsersTable` calls `/api/organizations/users` with no org id — it can only ever show the logged-in org's users.
> **Why it matters:** They're a **visual** template to copy, not a drop-in. The admin portal needs its own hooks that call the new org-scoped admin endpoints.

---

## 7. Multi-service impact

| Service | Touched? | What |
|---|---|---|
| **DDP_backend** | ✅ heavily | new `is_platform_admin` guard + decorator; new `/api/v1/admin/*` router with `{org_id}` params reusing `create_organization` / user fns; `Org.is_active` migration + login enforcement; `OrgUser` per-org active field; surface `is_platform_admin` in `/currentuserv2` |
| **webapp_v2** | ✅ | `/admin` branch in `client-layout.tsx` + `AdminLayout`; AdminGuard; conditional nav link; `useAdminPortal` hooks; org-parameterized copies of the user-mgmt UI |
| **prefect-proxy** | ❌ | no user model, no role logic. Deactivate/delete org already flow through DDP_backend's cleanup service, which calls the proxy — but no proxy code change for Week 1. |

Validation: backend = pytest (guard rejects non-platform-admin with 403; org-scoped endpoints act on the right org; deactivate blocks login). Frontend = Vitest for guard/nav logic + Playwright for "non-admin never sees the link and is bounced from `/admin`."

---

## 8. Latent bugs noticed (not in scope, but flag to the team)

- `is_demo` appears to always evaluate False after the `is_demo`/`type` column removal (enums `OrgType` vs `OrgPlanType` never share a value). Seen at `user_org_api.py:124`, `airbyte_api.py:59+`.
- `ddpui/core/orguserfunctions.py:94` still calls `Org.objects.filter(type=OrgType.DEMO)`, but `Org` no longer has a `type` field → would raise `FieldError` if reached (dead demo-signup path).
- `DELETE /users/invitations/delete/{id}` (`user_org_api.py:519`) has no org scoping — any caller with the permission can cancel any org's invitation by id. The admin portal should not rely on this loose behavior; its own cancel endpoint should scope by org.
