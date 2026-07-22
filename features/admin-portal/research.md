# Admin Portal — Research

**Date:** 2026-07-22 · **Tracking:** Issue #1254
**Spec:** `features/admin-portal/spec.md`

**Acronyms:** JWT (the signed login token) · claim (a named field inside the token) · cookie (a value the browser stores per host and re-sends) · host-only cookie (bound to the exact host that set it, no `domain=`) · FK (foreign key) · CRUD (create, read, update, delete) · N+1 (one query that fans out into many) · PII (personally identifiable information).

> This is a **fresh read** of DDP_backend and webapp_v2 as of 2026-07-22. Every file/line below was re-verified today. It covers the five surfaces the portal touches: the existing admin portal, the auth system (for the independent admin session), notifications, feature flags, and the Airbyte/pipeline read paths — plus the frontend shell. Pre-existing bugs found along the way are listed at the end and are **not** fixed here.

---

## 1. What already exists — the shipped admin portal

Organization onboarding and user management are built and merged, backend and frontend.

**Backend** — `ddpui/api/admin_api.py`:
- `admin_router = Router()` (`:33`), logger `CustomLogger("ddpui")` (`:31`). Mounted at `/api/v1/admin/` in `ddpui/routes.py:119`.
- Every route is decorated `@platform_admin_required` (`ddpui/auth.py:63-80`). Org CRUD: `GET/POST /orgs`, `GET/PUT /orgs/{id}`, `POST /orgs/{id}/deactivate|reactivate` (`:112-179`). User management: list users, invite, change role, deactivate/reactivate, removal-impact, delete user, cancel invitation (`:259-453`).
- Business logic lives in `ddpui/core/admin/admin_service.py` (logger `CustomLogger("ddpui.core.admin")`, `:25`). Its docstring states the convention: handlers stay thin (**parse → call service → convert → return**); the service "knows nothing about HTTP" and returns models/primitives (`:1-11`).

**Frontend** — `webapp_v2`:
- Admin routes render through `components/client-layout.tsx:58-70`: `pathname.startsWith('/admin')` → `AuthGuard > AdminGuard > AdminLayout`.
- `components/admin/AdminLayout.tsx`: nav = Home, Organizations (live), **Notifications and Feature Flags are `disabled: true` placeholders** (`:19-24`); "Back to Dalgo" link → `href="/"` (`:78`).
- `components/admin/AdminGuard.tsx`: reads `is_platform_admin` from the `/api/currentuserv2` SWR cache (`:33`, `data[0].is_platform_admin` `:37`); non-admin bounce → `router.replace('/')` (`:41`).
- Pages under `app/admin/`: `page.tsx` (dashboard, with Notifications/Feature-Flags stat cards as `comingSoon`), `organizations/page.tsx`, `organizations/new/page.tsx`, `organizations/[id]/page.tsx`. Data hooks in `hooks/api/useAdminPortal`.

> **Takeaway:** the portal's org/user work is done and does not get re-planned. The new work re-homes it behind the independent admin login and adds Notifications, Feature Flags, and the Airbyte/Pipeline view.

---

## 2. Auth system — the load-bearing surface for the independent admin session

### 2.1 How login and cookies work today

`ddpui/api/user_org_api.py`:
- `post_login_v2` (`:598-636`) authenticates via `CustomTokenObtainSerializer` and sets two cookies by literal name — `access_token` (`:617-624`) and `refresh_token` (`:627-634`) — each `httponly`/`secure`/`samesite` from settings, `path="/"`, **no `domain=`** (so host-only, bound to the backend/API host), **no `max_age`** (session cookies; the JWT `exp` governs validity).
- `post_logout` (`:187-205`) blacklists each token's `jti` in Redis then `delete_cookie` both by name.
- `post_token_refresh_v2` (`:639-666`) reads `refresh_token`, re-sets a fresh `access_token`.

### 2.2 The auth middleware and the platform-admin gate

`ddpui/auth.py`:
- `CustomJwtAuthMiddleware` (`:111-235`) reads the `access_token` **cookie by literal name at `:115`**; 498 on expiry (`:125`), 401 otherwise (`:127`); decodes the JWT, checks the Redis `blacklisted_jti:{jti}` list (`:145-149`), loads `request.user` (`:159`) and `request.orguser` (narrowed by the `x-dalgo-org` header, `:161-164`), sets `request.permissions/orguser/token`.
- `platform_admin_required` (`:63-80`) reads **only `request.orguser`** — it does not read any token itself. It queries `UserAttributes` and checks `is_platform_admin` (`:75-76`). So whichever middleware authenticated the request decides which cookie was required.

### 2.3 Where a new claim goes, and how the token is minted

`CustomTokenObtainSerializer.get_token` (`ddpui/auth.py:241-271`) already stamps a custom claim (`token["orguser_role_key"] = ...`, `:270`) onto the RefreshToken; SimpleJWT propagates it to the access token. `CustomTokenRefreshSerializer.validate` (`:278-300`) re-mints via `CustomTokenObtainSerializer.get_token(user)` (`:297`), so **a new claim added at `:270` automatically survives refresh** — no second edit. The middleware reads claims from `token_payload` (`:153-156`) — the place to consume a new claim.

### 2.4 Token lifetime and cookie settings

`ddpui/settings.py`:
- `SIMPLE_JWT` (`:323-331`): access `JWT_ACCESS_TOKEN_EXPIRY_MINUTES` (default 30), refresh `JWT_REFRESH_TOKEN_EXPIRY_DAYS` (default 7), signing key `JWT_SECRET_KEY` (falls back to `SECRET_KEY`).
- Cookies (`:341-344`): `COOKIE_SECURE=True`, `COOKIE_SAMESITE="Lax"` in production else `"None"`, `COOKIE_HTTPONLY=True`.

### 2.5 The precedent for a second auth surface

`ddpui/routes.py`: the global authed API is `src_api = NinjaAPI(..., auth=auth.CustomJwtAuthMiddleware())` (`:32-38`). A **second, unauthenticated** `public_api = NinjaAPI(...)` already exists (`:122-128`) for `/api/v1/public/`. So multiple NinjaAPI instances with different auth is an established pattern. Django Ninja also allows router-level `auth=` that overrides the API default.

### 2.6 `is_platform_admin`

`ddpui/models/org_user.py`: `UserAttributes.is_platform_admin` is a global per-User boolean (`:31`, default False). Surfaced by `/currentuserv2` (`ddpui/api/user_org_api.py:94-96`, emitted `:150`). No migration needed — the flag exists.

### 2.7 Frontend auth details that matter

- `lib/api.ts`: base URL `NEXT_PUBLIC_BACKEND_URL` (`:5`); every call sends `credentials: 'include'` (`:87`); org header `x-dalgo-org` from `localStorage.selectedOrg` (`:39-46`). **The refresh trigger is HTTP 401, not 498** (`:91`) — there is no `498` handling in `lib/`. On 401 it calls `POST /api/v2/token/refresh` once, else hard-navigates to `/login`.
- **`is_platform_admin` has two read paths:** `hooks/api/usePermissions.ts` reads it synchronously from the Zustand `authStore` (`isPlatformAdmin`, `:20`) — used by the main sidebar; `AdminGuard`/`AuthGuard` read it from the `/api/currentuserv2` SWR cache. Keep these consistent when the admin session lands.

---

## 3. Notifications — for broadcast notifications

### 3.1 Models — `ddpui/models/notifications.py`

- `Notification` (`:5-14`): `author` (**EmailField**), `message`, `email_subject`, `timestamp`, `urgent`, `scheduled_time`, `sent_time`. **No** field stores the audience — audience is resolved to recipient ids at create time and discarded. No `read_status`/`task_id` on `Notification`. No audit fields.
- `NotificationRecipient` (`:17-25`): FK `notification` (CASCADE), FK `recipient` (OrgUser, CASCADE), `read_status` (bool), `task_id` (per-recipient Celery id). **Read counts come from here** (`read_status`).

### 3.2 Audience, create, schedule, cancel — `ddpui/core/notifications/notifications_functions.py`

- Audience enum `SentToEnum` (`ddpui/schemas/notifications_api_schemas.py:8-16`): `ALL_USERS`, `ALL_ORG_USERS`, `SINGLE_USER`. The spec's two audiences map to `ALL_USERS` (whole platform) and `ALL_ORG_USERS` (one org).
- `get_recipients(sent_to, org_slug, user_email, manager_or_above, superset_clients)` (`:25-71`) → `(error, list_of_orguser_ids)`. **Recipient-count preview = `len()` of this list.**
- `create_notification(NotificationDataSchema)` (`:114-172`) creates the `Notification`, fans out `NotificationRecipient` rows via `handle_recipient`, and sends one Discord message per distinct org.
- `handle_recipient(recipient_id, scheduled_time, notification)` (`:75-110`): if `scheduled_time` set → `schedule_notification_task.apply_async(..., eta=scheduled_time)` and stores `task_id`; else sends now and emails via SES if the user opted in (`enable_email_notifications`).
- Celery task `schedule_notification_task` (`ddpui/celeryworkers/moretasks.py:18-34`).
- Cancel: `delete_scheduled_notification(notification_id)` (`:354-381`) refuses if already sent (`:361-362`), revokes each recipient's Celery task (`:367-370`), deletes.

### 3.3 The working vs. broken create path

- **Working:** the management command `create_notification.py` and `delivery.py` both build a full `NotificationDataSchema` (with `email_subject`) and call `create_notification`.
- **Broken + ungated:** the HTTP `POST /api/notifications/` route (`ddpui/api/notifications_api.py:15`) builds a plain dict **without `email_subject`** and passes it to `create_notification` (which does attribute access and requires `email_subject`) — so it fails. And notification routes carry **no `@has_permission`** gate (only the global JWT), so any authenticated user could hit them. See bugs list.

> **Takeaway for the plan:** build the admin broadcast on the **service functions** (`get_recipients`, `create_notification`, `schedule_notification_task`, `delete_scheduled_notification`), under new `@platform_admin_required` admin routes — do **not** extend the broken/ungated `/api/notifications/` HTTP path.

### 3.4 Reusable frontend

`components/notifications/NotificationRow.tsx` is **props-only** and encapsulates rendering: it **linkifies URLs** in message text (`renderMessageWithLinks`, `:19-40`, `target="_blank" rel="noopener noreferrer"`), truncates at 300 chars, styles urgent/read. Reusable read-only in an admin history view. `hooks/api/useNotifications.ts` is org-scoped (hits `/api/notifications/*`), so admin history needs its own hooks against the admin endpoints.

---

## 4. Feature flags — for per-org on/off

### 4.1 Model — `ddpui/models/org.py`, `OrgFeatureFlag` (`:344-375`)

`org` FK (**nullable — null = global**, CASCADE), `flag_name`, `flag_value` (bool). `unique_together (org, flag_name)` plus a partial unique constraint so there's one global row per flag. **No audit fields** (`created_at`/`updated_at`/`changed_by`).

### 4.2 Util — `ddpui/utils/feature_flags.py`

- Registry `FEATURE_FLAGS` (`:4-12`) — 7 flags: `DATA_QUALITY`, `USAGE_DASHBOARD`, `EMBED_SUPERSET`, `LOG_SUMMARIZATION`, `AI_DATA_ANALYSIS`, `DATA_STATISTICS`, `REPORTS`.
- `enable_feature_flag(flag_name, org)` (`:15-37`) and `disable_feature_flag(flag_name, org)` (`:40-62`) — validate against the registry; **disable writes a `False` row** (there is **no delete/clear-override path**).
- `is_feature_flag_enabled(flag_name, org)` (`:65-71`) returns the exact row's value or **`None` with no global fallback**. `get_all_feature_flags_for_org(org)` (`:74-103`) **does** merge global defaults + org overrides.
- Read endpoint: `GET /api/organizations/flags` (`ddpui/api/user_org_api.py:563-574`), gated `@has_permission(["can_view_flags"])`. **There is no HTTP endpoint to set/enable/disable** — that is CLI-only (`manage_feature_flags.py`).

> **Takeaway:** the spec chose **per-org on/off** (no global default management). The model + `enable/disable_feature_flag` already support per-org on/off. The new work is **HTTP admin endpoints** to set them + a UI. No migration is required for on/off; audit fields are out of scope per the spec.

### 4.3 Reusable frontend

`hooks/api/useFeatureFlags.ts`: `FeatureFlagKeys` enum (`:5-13`, mirrors the backend registry) and a 5-minute-deduped SWR read of `/api/organizations/flags` (`:26-49`). This is the **org-user read side**; a platform-admin management UI is a separate surface.

---

## 5. Airbyte & pipeline read paths — the danger map for the read-only view

> **The rule:** the cross-org view must be **passively read-only**. Two of the obvious functions are not safe.
> **Why it matters:** one dispatches real deletions; one crashes on half-onboarded orgs; several take bare ids with no org check and would leak one org's data into another org's view.

### 5.1 Do NOT call from a read-only view

- **`airbytehelpers.get_connections(org)` (`:312`)** — for connections missing/deprecated in Airbyte it dispatches `delete_airbyte_connections.delay(...)` (`:532-536`): a real background deletion. It also dereferences `warehouse.name` (`:489`) after a `.first()` that can be `None` (`:389`) — an `AttributeError` for any org without a warehouse.
- **`airbytehelpers.get_one_connection(org, connection_id)` (`:541`)** — same delete dispatch on a deprecated connection (`:553-555`).
- **`prefect_service.get_flow_runs_by_deployment_id(deployment_id)` (`:443`)** — writes new `PrefectFlowRun` rows.
- **`prefect_service.recurse_flow_run_logs(...)` (`:669`)** — unbounded `while True` paging; per-run N+1 fan-out.
- Pipeline log-history endpoints `pipeline_api.py:259` and `:273` — the latter checks only `orguser.org is None`, **not** that the org owns the `deployment_id`.

### 5.2 Safe to build on (DB-backed, no side effects)

- `get_sync_job_history_for_connection(org, connection_id, limit, offset)` (`airbytehelpers.py:676`) — DB-backed on `AirbyteJob`, paginated, org-scoped via `OrgTask`.
- `get_flow_runs_by_deployment_id_v1(deployment_ids=[...], limit, offset)` (`prefect_service.py:483`) — DB-only, no writes; takes bare ids, so **the caller must pre-scope the id set to the target org**.
- `PipelineService.get_pipelines(org)` (`core/orchestrate/pipeline_service.py:356`) and `get_pipeline_details(org, deployment_id)` (`:425`) — org-scoped at the `OrgDataFlowv1` query.

### 5.3 Bare-id functions — must resolve to the target org first

- `airbyte_service.get_logs_for_job(job_id)` (`:1080`) — bare int job id, no org check.
- `prefect_service.get_flow_run_logs*` (`:571`, `:582`) — bare flow-run id.

> Because the spec chose **full raw logs**, these are needed — but each must be gated: resolve `job_id → AirbyteJob.config_id → OrgTask.org` and `flow_run_id/deployment_id → OrgDataFlowv1.org`, and confirm it equals the target org, **before** fetching.

### 5.4 Model join facts (neither table has a direct Org FK)

- `AirbyteJob` (`ddpui/models/airbyte.py:37`): reach the org via `config_id == OrgTask.connection_id → OrgTask.org`. Freshness: `update_or_create` + a periodic reconcile Celery task.
- `PrefectFlowRun` (`ddpui/models/flow_runs.py:8`): reach the org via `deployment_id == OrgDataFlowv1.deployment_id → OrgDataFlowv1.org` (the `orguser` FK is nullable, only set on user-triggered runs). Freshness: webhook-written + a reconcile sweep.

### 5.5 Single-org baselines (regression anchors)

`airbyte_api.py` list/detail/sync-history (`:451-546`) and `pipeline_api.py` flows list/detail (`:64-101`) — all `@has_permission([...])`, scoped to `request.orguser.org`. Their behavior must stay unchanged.

---

## 6. Frontend shell — what the portal plugs into

- **Run/build:** `package.json` dev/start hard-pin **port 3001** (`:9`, `:11`), not env-parameterizable via the scripts. `next.config.ts`: `output: 'standalone'`, **no basePath, no redirects, no multi-zone**; rewrites are PostHog-only.
- **Shell routing:** `app/layout.tsx` is a **server component** but passes **only `children`** to `ClientLayout`. `components/client-layout.tsx` branches purely on `pathname.startsWith(...)` — public routes (`:14`), `/share|/public` (`:32-43`), `/admin` (`:58-70`), else main app. **No Host-header/subdomain logic anywhere.**
- **Middleware:** `middleware.ts` matches **only** `/share/dashboard/*` and `/share/report/*` (`:30`) to strip frame headers. It does not read the Host header and does no auth.
- **Login:** `app/login/page.tsx` calls `apiPost('/api/v2/login/')` and redirects to `/impact` (`:65`); it does not read the response body.
- **Sidebar:** `components/main-layout.tsx:230-236` — the "Admin Portal" item, `hide: !isPlatformAdmin` (from `useUserPermissions`). `getNavItems` is an exported pure function with a unit test at `components/__tests__/getNavItems.test.ts`.
- **Reusable presentational components (props-only, safe read-only):** `components/connections/sync-status-cell.tsx`, `components/pipeline/log-card.tsx`, `components/connections/connection-row.tsx` (aside from a `useSyncLock` import). **Own their fetching (heavier to reuse):** `components/pipeline/orchestrate/pipeline-run-history.tsx` (paginated `apiGet`) and the `TaskRunRow` leaf inside `components/pipeline/logs-table.tsx` (SWR summary polling).

---

## 7. Pre-existing bugs found (flagged, NOT fixed here)

| # | Bug | Location | Consequence |
|---|---|---|---|
| 1 | HTTP `POST /api/notifications/` builds notification data without `email_subject` and passes a dict where a schema is expected | `notifications_api.py:27-33` → `notifications_functions.create_notification` | The HTTP create path is effectively broken/unused. |
| 2 | Notification routes carry **no `@has_permission`** gate (only the global JWT) | `notifications_api.py` (all routes), `routes.py:101` | Any authenticated user can hit `POST /api/notifications/`. A real authorization gap. |
| 3 | `get_notification_history` filters `Notification.read_status`, a field that does not exist | `notifications_functions.py:182-183` | Would raise `FieldError`; currently masked because the API hardcodes `read_status=None`. |
| 4 | `disable_feature_flag` success prints the failure message (checks `result is False`, but success returns `True`) | `manage_feature_flags.py:107-110` | Cosmetic — the DB write still succeeds. |
| 5 | `delete_scheduled_notification` deletes the parent before the (CASCADE-removed) recipients; would `AsyncResult("").revoke()` on immediate rows | `notifications_functions.py:367-373` | Harmless/dead code. |

> Bug #2 (ungated notification routes) is a genuine security gap. The plan builds the admin broadcast on a **separate, `@platform_admin_required` admin path** and does not depend on the broken HTTP route — but the plan's Open Questions flag whether to close bug #2 as part of this work.

---

## 8. Net-new for the plan (summary)

| Surface | New work | Migration? |
|---|---|---|
| Independent admin session | New admin cookie + JWT session claim + dedicated admin auth middleware + admin login/logout/refresh/currentuser; re-gate the existing `admin_router` behind it | **No** (cookie + claim) |
| Broadcast notifications | Admin routes on the service functions; additive fields to record audience for history | **Yes** (additive, nullable) |
| Per-org feature flags | Admin HTTP endpoints (set on/off, clear) + UI; the model already supports per-org rows | **No** |
| Airbyte/pipeline read view | Read-only admin endpoints built on the **safe** primitives; neutralize the destructive `get_connections` path; org-ownership gate for bare-id log fetches | **No** |
