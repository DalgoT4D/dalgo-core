# Research — Platform Admin Portal v1

**For:** `features/admin-portal/v1/plan.md`
**Date:** 2026-07-02
**Scope:** net-new findings only — things specific to a *cross-org, Dalgo-staff* portal. Where a fact already lives in `features/access-control/v2/research.md` (auth flow, role model, sidebar contract, migration conventions), this file points there instead of repeating it.

> Acronyms: FK (foreign key — a DB column pointing at another table's row) · JWT (JSON Web Token — the signed login token) · RBAC (role-based access control) · PII (personally identifiable information).

> **Note:** the backend/frontend `landmarks.md` files referenced by the planning command do **not** exist in this repo. The equivalent facts came from `access-control/v2/research.md` plus two Explore passes on 2026-07-02.

---

## 1. The load-bearing constraint: the whole API is single-org

**The rule:** Every authenticated API request is scoped to exactly one org by the `x-dalgo-org` request header. `CustomAuthMiddleware` (`DDP_backend/ddpui/auth.py:62`) reads that header, resolves `request.orguser` from `(user, org)`, and loads `request.permissions` from Redis for *that* org.
**Example:** When Priya's browser calls `GET /api/organizations/users`, it sends `x-dalgo-org: akshara`. The middleware builds `request.orguser` for Akshara only — she can never see another org's data through the normal API.
**Why it matters:** A cross-org portal **cannot** ride the normal request path. It needs a separate authorization path that (a) authenticates the Dalgo staff user, (b) checks a *platform* flag, and (c) takes the target org as an explicit parameter, not the header. This is the single biggest design decision in the plan (see HLD).

---

## 2. The platform-admin concept already half-exists

**The rule:** There is already a platform-vs-org distinction — three boolean flags on the user, spanning all orgs.
**Where:** `DDP_backend/ddpui/models/org_user.py` — `UserAttributes` has `is_platform_admin`, `is_consultant`, `can_create_orgs`. Added in migration `ddpui/migrations/0047_userattributes_is_platform_admin.py`.

| Flag | Set by | Read by today |
|---|---|---|
| `is_platform_admin` | `management/commands/manage-user-attributes.py` only | surfaced read-only in the current-user payload (`ddpui/core/orguserfunctions.py:72`) |
| `is_consultant` | same command | same |
| `can_create_orgs` | same command | gates org creation |

**Gaps this feature fills:**
- There is **no `@has_permission`-style gate keyed on `is_platform_admin`** and **no platform API router**. The flag is set and displayed but never *enforces* anything. This feature adds the enforcement layer.
- **Superadmin gate:** Django's built-in `User.is_superuser` is unused in app logic today (no `is_staff`/`is_superuser` references anywhere in `ddpui/`). It's the natural, already-present gate for the "one superadmin who manages the platform-admin list" — no new flag needed.

- **Legacy `AdminUser`** model (`DDP_backend/ddpui/models/admin_user.py`) exists but is essentially unused. **Do not** build on it — build on `UserAttributes.is_platform_admin`.
- **No Django admin** is configured (`admin.site.register` appears nowhere). This portal is not a Django-admin skin.

---

## 3. Org has no lifecycle/status field (suspend/archive is greenfield)

**The rule:** The `Org` model has no status, no soft-delete, no suspended state.
**Where:** `DDP_backend/ddpui/models/org.py:123` — `Org` fields are `name`, `slug`, `airbyte_workspace_id`, `dbt` (FK), `viz_url`, `viz_login_type`, `website`, `queue_config`, `created_at`, `updated_at`. Deletion today is a **hard delete** via the `deleteorg` management command.

- `OrgType` enum exists (`org.py:21`: `SUBSCRIPTION` / `TRIAL` / `DEMO`) but that's *plan type*, not lifecycle — and plan lives in `models/org_plans.py` (`OrgPlan`), read via `Org.base_plan()`. Do not overload `OrgType` for suspend/archive.
- **Net:** add a new `status` field (`active` / `suspended` / `archived`) + timestamps to `Org`, migration backfills every existing org to `active`.

Related per-org models (matter for the directory's health signals and the suspend cascade): `OrgWarehouse` (`org.py:229`), `OrgDataFlowv1` (Prefect deployments), `OrgPrefectBlockv1`, `OrgFeatureFlag`.

---

## 4. Cross-org operations today = management commands only

**The rule:** Every cross-org action is a Django management command run by a developer — there is no runtime UI or API for any of it.
**Where:** `DDP_backend/ddpui/management/commands/` —

| Command | What the portal replaces it with |
|---|---|
| `createorganduser.py` | "Create org" flow (org shell + first-Admin invite) |
| `deleteorg.py` | Archive (soft) — hard delete stays a command in v1 |
| `addusertoorg.py` | "Add user" in the org's Users tab |
| `manage-user-attributes.py` | "Platform Staff" add/remove (sets `is_platform_admin`) |
| `create-system-orguser.py` | (not in v1 scope) |

Cross-org iteration (`Org.objects.all()`) otherwise appears only in Celery batch jobs (`celeryworkers/tasks.py`, `fetch_and_sync_airbyte_jobs.py`) — background, not an admin surface.

**Reuse, don't rewrite:** the per-org user functions in `DDP_backend/ddpui/core/orguserfunctions.py` (invite, resend, delete, role change) already exist and are permission-gated in `ddpui/api/user_org_api.py` (invite `:469`, resend `:504`, delete `:288`, role change `:342`, org create `:539`). The portal's user actions should call these service functions with an **explicit org** built from the path param, rather than reimplementing them.

---

## 5. Suspend-cascade integration points (pinned 2026-07-02)

**Two assumptions from the spec were wrong** — confirmed by direct code read:

- **There is no cron Alert feature.** The `features/alerts` spec is not shipped. No `alert.py` model, no warehouse-query eval task. Dalgo's real "alerts" are **Prefect pipeline-failure notifications** fired from a webhook (`ddpui/core/webhooks/webhook_functions.py:213`, `notify_users_about_failed_run`), not a schedule. Since suspend pauses the pipelines, they won't run → won't fail → won't notify. Gating the webhook is belt-and-suspenders, not the main lever.
- **There are no scheduled report emails.** No celery-beat report task exists (`celeryworkers/tasks.py:1257` `setup_periodic_tasks` has none). Reports email **on-demand only** via `report_tasks.py:19 send_report_email_task`, triggered by `report_api.py:290` — a path that requires a logged-in user, which suspend already blocks.

**So the genuinely load-bearing cascade is three points, not five:**

| # | Point | Exact location | Gate |
|---|---|---|---|
| 1 | **Login / token (JWT — primary)** | `ddpui/auth.py:94` `CustomJwtAuthMiddleware.authenticate`; org resolved 140-143; add gate at **line 147** before `request.orguser = orguser` (192) | reject if `org.status != active` |
| 1b | Login / token (legacy DB-token) | `ddpui/auth.py:54` `CustomAuthMiddleware.authenticate`; add gate at **line 69** (org resolved 62-65) | same |
| 2 | **Prefect deployment pause** (active step) | loop `OrgDataFlowv1.objects.filter(org=org, dataflow_type="orchestrate")` → `prefect_service.set_deployment_schedule(deployment_id, "inactive")` (`ddpprefect/prefect_service.py:543`; proxy side `prefect-proxy/proxy/service.py:1164`). Pattern to copy: `management/commands/refresh_deployment_schedule.py:19-46` | pause on suspend, `"active"` on reactivate |
| 3 | **Public share render** (the real no-login exposure) | Reports: single choke point `ddpui/api/public_api.py:1049` `_get_public_report_snapshot`. Dashboards: **no shared resolver** — each endpoint does its own `Dashboard.objects.get(public_share_token=...)`; gate points at `public_api.py` `:94, :144, :197, :381, :463, :476, :568, :621, :895, :958` (add a shared helper). | return "unavailable" if org suspended/archived |

**Defensive extras (cheap, not load-bearing):**
- Pipeline-failure webhook: gate `webhook_functions.py:213` (early-return if org not active).
- On-demand report send: gate `report_tasks.py:~35` (task entry, after loading snapshot/orguser).

**Design stance:** the **public-share gate** is the one that matters most — it's the only path that serves NGO data with no login. Pausing Prefect deployments is the active resource-saving step. Login-block is the umbrella. The alert/report gates are defensive no-ops given the above.

**Prefect pause detail:** there is **no** "pause all of an org's schedules" helper today — you loop `OrgDataFlowv1` yourself. `deployment_id` lives on `OrgDataFlowv1`.

---

## 6. Frontend: where the portal plugs in

From `access-control/v2/research.md` §4 and the earlier inventory:

- **Sidebar** `webapp_v2/components/main-layout.tsx` `getNavItems()` (lines 91–231). No role-based filtering exists yet. The portal must **not** appear here for NGO users — gate on `is_platform_admin`.
- **`middleware.ts`** handles only iframe embedding today — no auth guard. The portal route guard is net-new; a layout-level `is_platform_admin` check is the simplest.
- **Auth store** `webapp_v2/stores/authStore.ts` holds the current-user payload; `is_platform_admin` is already in that payload (§2). So the client can gate on it without new plumbing — but **server-side refusal is the real control**, UI hiding is secondary.
- **Reuse:** `webapp_v2/components/settings/user-management/` (`UserManagement.tsx`, `UsersTable.tsx`, `InvitationsTable.tsx`, `InviteUserDialog.tsx`, `DeleteUserDialog.tsx`) and `components/settings/organizations/CreateOrgDialog.tsx` — adapt to take an explicit org, don't rebuild.
- **New area:** a `app/platform/` route group (directory, org detail, staff, audit log) rendered only for platform admins.

---

## 7. Multi-service impact

| Service | Touched? | What |
|---|---|---|
| **DDP_backend** | Yes (bulk) | New `platform` API router + `PlatformAdminAuth` auth class; `Org.status` migration; `PlatformAuditLog` model; suspend-cascade gates; reuse of orguser/org-create service fns. |
| **webapp_v2** | Yes | New `app/platform/` area, route guard, API hooks; reuse of user-management + create-org components. |
| **prefect-proxy** | **Yes** (new vs. access-control, which didn't touch it) | Pausing/resuming an org's Prefect deployments on suspend/reactivate goes through the proxy. |

**Validation per service:** backend = pytest (auth-class gating, status migration + backfill, each cascade gate, audit-log writes); frontend = Vitest for the route guard + Playwright E2E for "NGO user cannot reach `/platform`, platform admin can"; cross-service = an integration test that suspends an org and asserts login blocked + deployments paused.

---

## 8. Open technical risks (feed the plan's §8)

- **Auth bypass surface:** a whole new authorization path that steps outside `x-dalgo-org` is the highest-risk part. It must fail closed — no platform endpoint reachable without `is_platform_admin`.
- **Cascade completeness:** every outward-facing send must be gated, or a suspended org leaks. The §5 list must be provably complete (grep for every warehouse-querying scheduled task).
- **Login-block blast:** rejecting login by org status must not lock out platform admins themselves or break the accept-invite path.
- **Hard delete still a command:** v1 archive is soft; the existing `deleteorg` hard-delete command stays out of the portal (donor-compliance).
