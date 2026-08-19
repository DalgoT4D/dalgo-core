# Admin Portal — Implementation Plan

**Status:** Milestone 1 shipped; Milestones 2–4 for engineering review
**Date:** 2026-07-22 · **Revised:** 2026-07-26 (independent session reversed to a shared session) · 2026-08-19 (dropped the read-count notification endpoint and org/user deactivate — see §2, §3.3, §4.3, §7) · **Tracking:** Issue #1254
**Spec:** `features/admin-portal/spec.md` · **Research:** `features/admin-portal/research.md`

**Acronyms:** HLD (High-Level Design) · LLD (Low-Level Design) · JWT (the signed login token) · claim (a named field inside the token) · cookie (a value the browser stores per host and re-sends) · host-only cookie (bound to the exact host that set it, no `domain=`) · FK (foreign key) · CRUD (create, read, update, delete) · PII (personally identifiable information) · N+1 (one query that fans out into many).

> **One-paragraph summary.** The admin portal ships organization onboarding, user management, an admin sign-in screen, and sign-out at `insights.dalgo.org/admin`. Access control is **one shared product session plus a server-side platform-admin check on every admin route** — an earlier independent-session design was built and then reversed (§3.2). What remains to build is **broadcast notifications**, **per-org feature flags**, and a **read-only Airbyte/pipeline view**. The portal stays a **path (`/admin`) inside the existing production deployment** — no new domain, no separate app or port.

---

## 1. Overview

**Feature summary:** Complete the admin portal. Onboarding, user management, sign-in, and sign-out are **shipped** (Milestone 1). What remains is broadcast notifications, per-org feature flags, and a read-only Airbyte/pipeline debugging view.

**Where it lives:** `insights.dalgo.org/admin` — a path inside the current production deployment. `insights.dalgo.org` is already live for NGO customers, so **there is no domain, DNS, or hosting to provision.**

**Services affected:**

| Service | Role |
|---|---|
| DDP_backend (Django + Django Ninja) | Shipped: the `@platform_admin_required` gate and `GET /admin/currentuser`. To build: admin endpoints for notifications, feature flags, and the Airbyte/pipeline read view. |
| webapp_v2 (Next.js 15) | Shipped: admin sign-in screen, `AdminGuard`, sidebar sign-out. To build: Notifications, Feature flags, Airbyte/Pipelines screens; un-disable the placeholder nav items. |
| prefect-proxy | Not touched (pipeline data is read from the DB, not the proxy). |
| Infra / DNS / TLS | **Nothing** — the host is already live. |

---

## 2. Blast Radius

Traversed from `docs/domain-map.md`. The portal **operates** entities but changes almost none of their data models. The one additive data change is on Notification.

| Surface | Hop | Why affected | Status |
|---|---|---|---|
| **Organization** | 0 | Onboarding — create + edit only | **Existing (shipped).** No change. No deactivate, no delete — `Org.is_active` was removed from the codebase 2026-08-19, and delete was never built. |
| **OrgUser** | 0 | User management — invite, role change, remove, cancel invite; removal orphans owned content | **Existing (shipped).** Removal warning already built. No deactivate — `OrgUser.is_active` was removed from the codebase 2026-08-19. |
| **Notification** | 0 | Broadcasts create Notification + NotificationRecipient rows | **In scope (new).** Additive fields to record audience for history (§4.1). No audit-trail field, no read-count field — both explicitly out of scope. |
| **OrgUser (as recipient)** | 1 | A broadcast is delivered to OrgUsers in-app + email | **In scope.** Reuses the existing delivery path (research §3). |
| **Source / Warehouse / Transform / Pipeline / Data Quality** | 0–1 | Read-only Airbyte/pipeline view reads connection + run status/logs | **In scope (new), read-only.** No data-model change; safety work required (research §5). |
| **Chart / Dashboard / Metric / KPI / ReportSnapshot / Share link** | 2+ | — | **Not affected.** The portal never creates or edits analytics entities. Only indirect tie: removing an OrgUser orphans `created_by` on Chart/Dashboard/ReportSnapshot — existing shipped behavior with a warning. |
| **Alert** | 2 | — | **Not affected.** Alerts deliver directly to email/Slack and are decoupled from Notification (domain map). Broadcasts do not touch Alerts. |
| **Feature flags (platform config, not a domain-map entity)** | — | Toggling a flag changes which product surfaces (e.g. Reports, Data Quality) an org sees | **In scope (new).** Changes visibility, not data. Per-org on/off only (spec). |

> **The rule:** the portal moves and manages things; it does not change what analytics entities *are*. So the blast radius is auth + notifications + config + read-only pipeline views — the analytics data model is untouched.
> **Example:** Meera turns `REPORTS` off for Akshara. Akshara's users stop seeing the Reports nav item. No Chart, Dashboard, or ReportSnapshot row changes.
> **Why it matters:** it bounds review to auth correctness, notification blast radius, and the read-only-view safety issues — there is no risk to any NGO's analytics data from this work.

**No unaddressed surfaces.** Every domain-map entity above has a status the spec already decides; none is silently included or excluded.

**Corrected 2026-08-19.** Two things are confirmed absent from this blast radius, not merely unmentioned: (1) org/user deactivation — `Org.is_active`/`OrgUser.is_active` were removed from the codebase entirely, so no entity in this table carries a reversible suspend state; (2) an audit trail or read/unread tracking on broadcasts — neither `Notification` nor `NotificationRecipient` gains a field for either, and no admin route exposes `NotificationRecipient.read_status`.

---

## 3. High-Level Design (HLD)

### 3.1 One deployment, one path, one shared session — **BUILT**

```
Browser                         insights.dalgo.org  (one existing deployment, webapp_v2)
───────                         ┌─────────────────────────────────────────────────────────┐
insights.dalgo.org/…      ───►  │ client-layout: normal product  (AuthGuard > MainLayout)   │
insights.dalgo.org/admin  ───►  │ client-layout: /admin  (AdminGuard > AdminLayout)         │
                                │   /admin/login is public — the form ALWAYS renders        │
                                └─────────────────────────────────────────────────────────┘
        │ one login, used by both screens
        │ POST /api/v2/login/
        │ Set-Cookie access_token + refresh_token   (host-only on the API host)
        ▼
      ┌──────────────────────────── DDP_backend (api host) ─────────────────────────────┐
      │ CustomJwtAuthMiddleware  reads access_token → ALL APIs, normal and admin alike   │
      │ /api/v1/admin/*          additionally @platform_admin_required on every route    │
      └──────────────────────────────────────────────────────────────────────────────────┘
```

One cookie, one session, one deployment, no new host. The admin API is reached with the same `access_token` as everything else — what separates it is the per-route platform-admin check, not a different credential.

### 3.2 Where the boundary actually lives — **BUILT**

> **The rule:** the security boundary is `@platform_admin_required` on every admin route, checked against the database on every request. The admin sign-in screen is a doorway, not a lock.
> **Example:** Sarah is the org Admin for Akshara — not a platform admin. She is signed into the normal product, so her `access_token` is valid and the admin API authenticates her fine. Every `/api/v1/admin/*` route then refuses her with 403, because `UserAttributes.is_platform_admin` is False.
> **Why it matters:** the check is re-read from the database per request, so revoking someone's platform-admin flag locks them out within one request — no waiting for a session to expire.

Four things this design does, each server-side:

1. **Shared login.** The admin screen posts to the existing `POST /api/v2/login/`. No admin-specific login endpoint exists.
2. **Privilege decided from the login response.** That endpoint's body carries `is_platform_admin` (from `lookup_user()`). The admin sign-in screen refuses a non-admin locally rather than navigating; the backend would refuse them at every route regardless.
3. **Every admin route gated.** `admin_router` is a bare `Router()` inheriting the API-wide `CustomJwtAuthMiddleware`, exactly like the other 24 routers. Authority comes from `@platform_admin_required` on each route.
4. **One identity endpoint kept.** `GET /api/v1/admin/currentuser` returns `{email, is_platform_admin}` for the frontend guard, gated by `@platform_admin_required` only.

> **The rule:** `/admin/currentuser` was kept rather than reusing the normal `/api/currentuserv2`.
> **Example:** Meera is a platform admin whose org role is Member. `currentuserv2` is gated on the per-org `can_view_orgusers` permission, which she does not hold — reusing it would lock her out of the portal she is entitled to run. It also returns a *list* of OrgUsers, not one identity.
> **Why it matters:** a 20-line endpoint avoids coupling portal access to an unrelated per-org permission.

**Reversed from an earlier draft.** This plan previously specified an *independent* admin session — `AdminJwtAuthMiddleware`, an `admin_access_token` cookie, a `session="admin"` JWT claim, admin-only login/logout/refresh endpoints, and `JWT_ADMIN_*` lifetimes. That was built (commits `aa81d3a0`…`2530c3f4`) and then **removed** in `eca9865f` / `d1227c0`. The reason: it doubled the auth surface — a second cookie, a second refresh path, two independent ways to be logged out — while the actual protection was always `@platform_admin_required`. Everything named in this paragraph is **moot**; see §8.

**One deliberate consequence.** Signing in at `/admin/login` replaces the normal product session, because there is only one.

> **Example:** Meera is signed in as herself, then signs into the portal as a shared ops account. The normal product now shows the ops account. Accepted as correct for a single-session model.

### 3.3 New endpoints (all under `/api/v1/admin/`, all behind the admin session)

| Area | Endpoint(s) |
|---|---|
| Session — **BUILT** | `GET /currentuser` only. Sign-in uses the shared `POST /api/v2/login/`; sign-out uses the shared `POST /api/logout/`. The admin-specific `login` / `logout` / `token/refresh` routes an earlier draft specified were built and then removed (`eca9865f`). |
| Notifications | `GET /notifications` (history), `POST /notifications/preview` (recipient count), `POST /notifications` (create/schedule), `DELETE /notifications/{id}` (cancel scheduled) |
| Feature flags | `GET /flags/catalog`, `GET /orgs/{org_id}/flags`, `PUT /orgs/{org_id}/flags/{flag_name}` (on/off), `DELETE /orgs/{org_id}/flags/{flag_name}` (clear) |
| Airbyte/Pipelines (read-only) | `GET /orgs/{org_id}/connections`, `GET /orgs/{org_id}/connections/{cid}/sync-history`, `GET /orgs/{org_id}/connections/{cid}/jobs/{job_id}/logs`, `GET /orgs/{org_id}/pipelines`, `GET /orgs/{org_id}/pipelines/{dep_id}/runs`, `GET /orgs/{org_id}/pipelines/runs/{flow_run_id}/logs` |

### 3.4 External-service integrations

- **Notifications** reuse the existing delivery path: SES email (opted-in users) + one Discord message per org + in-app rows (research §3.2). No new integration.
- **Airbyte/Prefect** are **read from the app database** (`AirbyteJob`, `PrefectFlowRun`) for lists/history; **raw logs** are the only live external fetch, gated by org ownership (§4.3). No writes to Airbyte or Prefect.

---

## 4. Low-Level Design (LLD)

### 4.1 Data model

| Change | Where | Migration |
|---|---|---|
| **None** for the admin session | nothing stored; the shared session cookie is reused as-is | No |
| **Notification: add `scope` + `target_org`** | `ddpui/models/notifications.py` | **Yes — additive, nullable.** `scope = CharField(null=True)` (`"all_users"` / `"all_org_users"`), `target_org = FK(Org, null=True, SET_NULL)`. Records what a broadcast targeted so history can show it (today the audience is resolved to ids and discarded — research §3.1). Backfill leaves existing rows NULL = "audience unknown (legacy)". |
| **None** for feature flags | `OrgFeatureFlag` already has per-org rows; on/off uses `enable/disable_feature_flag` | No |
| **None** for Airbyte/pipeline | read-only | No |

### 4.2 Backend — the admin access model — **BUILT**

There is **no admin session code**. The portal reuses the product's login, and every admin route carries the platform-admin gate. What was actually built:

| Piece | Where | What it does |
|---|---|---|
| Router | `admin_api.py` — `admin_router = Router()` | Bare router inheriting the API-wide `CustomJwtAuthMiddleware`, same as all 24 siblings. No bespoke auth. |
| Gate | `@platform_admin_required` on every route (`ddpui/auth.py:63-80`) | Re-reads `UserAttributes.is_platform_admin` from the database per request. Signed-out → 401; signed-in non-admin → 403. |
| Identity | `GET /api/v1/admin/currentuser` | Returns `{email, is_platform_admin}` for `AdminGuard`. Kept rather than reusing `currentuserv2` (see §3.2). |
| Sign-in | shared `POST /api/v2/login/` | Unchanged product endpoint. Its response body already carries `is_platform_admin` via `lookup_user()`. |
| Sign-out | shared `POST /api/logout/` | Unchanged product endpoint: blacklists both token JTIs in Redis, deletes both cookies. |

**One backend fix was needed** (`eca9865f`), and it improves the normal product too:

> **The rule:** a wrong password must answer 401, not 500.
> **Example:** Meera fat-fingers her password at `/admin/login`. `CustomTokenObtainSerializer` is a DRF (Django REST Framework) serializer, so it raises DRF's `AuthenticationFailed`. These are Ninja views, not DRF views, so DRF's own handler never runs — the exception fell through to the catch-all handler and became a **500**. A new `drf_authentication_failed_handler` in `ddpui/routes.py` maps it to the 401 it already declares.
> **Why it matters:** the sign-in form shows a clean "wrong email or password" instead of a server error, and genuine faults stop being buried under a pile of false 500s in Sentry.

**Removed, not built** — an earlier draft of this section specified all of the following. Each was built and then deleted; none exists in the codebase:

| Moot item | Removed in |
|---|---|
| `AdminJwtAuthMiddleware` (subclass reading `admin_access_token`, requiring a `session="admin"` claim) | `eca9865f` |
| `admin_access_token` / `admin_refresh_token` cookies | `eca9865f` |
| `admin_service.issue_admin_session` / `refresh_admin_session` | `eca9865f` |
| `POST /admin/login/`, `POST /admin/logout/`, `POST /admin/token/refresh` | `eca9865f` |
| `JWT_ADMIN_ACCESS_TOKEN_EXPIRY_MINUTES`, `JWT_ADMIN_REFRESH_TOKEN_EXPIRY_HOURS` | `eca9865f` |
| The cookie-name constant extraction in `CustomJwtAuthMiddleware` | Kept — the base class still uses it; it simply no longer has a subclass. |

### 4.3 Backend — the three feature areas

**Notifications** (build on the service functions; do **not** use the broken/ungated HTTP route — research §3.3). **`Notification` and `NotificationRecipient` are reused exactly as they exist today — no new model, no new fields beyond `scope`/`target_org` (§4.1), re-verified in research.md 2026-08-19:**
- `POST /notifications/preview` → `len(get_recipients(...))` only. **Never return the recipient list** (would leak a cross-org email roster).
- `POST /notifications` → build a proper `NotificationDataSchema` (with `email_subject`, and **`author` derived server-side** from `request.orguser.user`, not client input) → `create_notification`; persist `scope`/`target_org`; block a 0-recipient audience.
- `DELETE /notifications/{id}` → `delete_scheduled_notification` (refuses if already sent).
- `GET /notifications` (history) → a **new admin query** (do not extend `get_notification_history`, which has a `FieldError` bug — research §7); returns audience, time, and recipient count only. **No read-count endpoint** — `NotificationRecipient.read_status` is not surfaced by the admin portal (spec, corrected 2026-08-19).

**Feature flags** (per-org on/off — `OrgFeatureFlag` is reused exactly as it exists today, no new model, re-verified in research.md 2026-08-19, research §4):
- `GET /flags/catalog` → the `FEATURE_FLAGS` registry (ends the Python/TS duplication). `GET /orgs/{id}/flags` → `get_all_feature_flags_for_org`. `PUT /orgs/{id}/flags/{name}` → `enable_feature_flag`/`disable_feature_flag` (validated against the registry). `DELETE` → clear the org row (a small new `clear_org_flag` in `utils/feature_flags.py`, since only a "write False" path exists today). No migration; no audit fields (out of scope per spec).

**Airbyte/pipeline read-only view** — the safety work is the point (research §5):
- **Connections list:** add `cleanup: bool = True` to `get_connections`/`get_one_connection` and skip the `delete_airbyte_connections.delay(...)` dispatch when `False` (`airbytehelpers.py:532-536`, `:553-555`); the admin view passes `cleanup=False`. **Guard the warehouse deref** (`:489`) — return `warehouse_name=None` when the org has no warehouse.
- **Sync history:** reuse `get_sync_job_history_for_connection` (safe, DB-backed, paginated).
- **Pipelines:** reuse the `PipelineService.get_pipelines(org)` join pattern; runs via `get_flow_runs_by_deployment_id_v1` with a **pre-scoped** deployment-id set (`OrgDataFlowv1.filter(org=target_org)`).
- **Full raw logs** (spec choice): `get_logs_for_job` / flow-run logs, but **only after** resolving `job_id → OrgTask.org` and `flow_run_id/deployment_id → OrgDataFlowv1.org` and confirming it equals `org_id` from the URL. Avoid `recurse_flow_run_logs` and the two unguarded history endpoints (research §5.1).
- Every route takes `org_id` in the **URL** (never the `x-dalgo-org` header) and carries an `AdminReadMeta` (`data_as_of`, `source`, `partial`) so the UI labels freshness honestly.

### 4.4 Frontend

- **Admin sign-in — BUILT:** `app/admin/login/page.tsx`; `/admin/login` is public in `components/client-layout.tsx`, so the form **always renders**, session or not. It posts to the shared `POST /api/v2/login/`, reads `is_platform_admin` from the response, and refuses a non-admin locally without navigating.
- **AdminGuard — BUILT:** reads identity from `GET /api/v1/admin/currentuser`. Signed-out (401) and signed-in-non-admin (403) both arrive as "error, no data" and are treated identically — bounce to `/admin/login`.
- **Sign-out — BUILT (`968435a`):** a "Log out" row in the `AdminLayout` sidebar footer, beside "Back to Dalgo". It reuses the normal app's handler shape verbatim (`components/header.tsx:99-111`): `POST /api/logout/` in a `try/catch`, then `trackEvent(USER_LOGGED_OUT)`, then `useAuthStore().logout()`. No admin-specific logout endpoint, store method, or analytics event was added.
  - The redirect deliberately does **not** copy `header.tsx:113-117`, which reacts to `isAuthenticated` going false. Nothing sets `isAuthenticated` **true** inside the portal (only `/login` and `AuthGuard` do, and `/admin` is outside both), so that reactive redirect would fire on mount and bounce a signed-in admin straight out. An explicit `router.replace('/admin/login')` after `logout()` achieves the same end state.
- **Back-link:** `AdminLayout` "Back to Dalgo" stays a link to `/`. With one shared session it is now literally just navigation.
- **Token refresh — BUILT:** admin routes refresh through the same `POST /api/v2/token/refresh` as everything else. `lib/api.ts` keeps only `adminAwareLoginPath`, so an unrecoverable 401 on an admin route lands on `/admin/login` rather than the product login.
- **Notifications:** new `app/admin/notifications/page.tsx` (history table + "New broadcast"); composer with audience (whole platform / one org), recipient-count preview, send-now/schedule, cancel; reuse the props-only `NotificationRow` for rendering (research §3.4). Un-disable the nav item (`AdminLayout.tsx:22`).
- **Feature flags:** new `app/admin/feature-flags/page.tsx` (per-org matrix) + a Flags tab on org detail; un-disable the nav item (`AdminLayout.tsx:23`). Serve the catalog from `/flags/catalog` rather than the hand-maintained TS enum.
- **Airbyte/Pipelines:** two new tabs on `app/admin/organizations/[id]/page.tsx`; reuse props-only presentational components (`sync-status-cell`, `log-card`, `connection-row`); **no polling** (`refreshInterval: 0`); surface `data_as_of`.

### 4.5 Integration points

- Frontend ↔ backend: cookie-based, `credentials: 'include'`. The admin screens call `/api/v1/admin/*`; the browser attaches the ordinary `access_token` cookie, the same one the normal product uses.
- Backend ↔ external: notifications reuse SES/Discord; Airbyte/Prefect are read from the DB except raw logs (gated live fetch).

---

## 5. Security Review

| Area | Finding / plan |
|---|---|
| **The boundary is the per-route gate, not the path or a cookie** | Every `/api/v1/admin/*` route carries `@platform_admin_required`, which re-reads `is_platform_admin` from the database per request. A signed-in non-admin is authenticated but refused 403 on every route. The `/admin` path and its sign-in screen protect nothing on their own — by design, and stated plainly so no reviewer mistakes the screen for the lock. |
| **Non-admin gets a session but no portal** | With one shared login, a non-admin with a correct password IS signed into Dalgo — they simply cannot enter the portal or call any admin route. The sign-in screen refuses them client-side from `is_platform_admin`; the server refuses them regardless. Accepted trade-off of a single session. |
| **Flag revoked mid-session** | `@platform_admin_required` re-reads `UserAttributes.is_platform_admin` per request (`auth.py:75-76`) — a revoked admin is locked out within one request. |
| **Shared-auth touches** | Two, both proven by the normal-product suite passing unmodified: the cookie-name constant in `CustomJwtAuthMiddleware` (non-behavioral, retained), and the new `AuthenticationFailed → 401` handler in `routes.py`, which changes a wrong password from 500 to 401 for the normal login as well as the admin one. |
| **Broadcast is the highest-reach action** | Every admin route is `@platform_admin_required` behind the admin session. Author is **server-derived** (not the client-supplied `author` the current schema takes — research §3.3). Mandatory recipient-count preview + confirm; a 0-recipient audience is blocked. |
| **Message rendering / stored XSS** | `NotificationRow` linkifies URLs and now renders admin-authored content to every user (research §3.4). Confirm escaping before enabling send. |
| **Notification data exposure** | `/preview` returns a **count only** — never the recipient list. No read-count report exists — dropped from scope, no inline emails. |
| **Pre-existing ungated notification routes (bug #2)** | The admin path is separate and gated; but the existing `/api/notifications/*` routes lack `@has_permission` (research §7). Flagged in §8 — decide whether to close it here. |
| **Feature flags are not a security boundary** | A flag hides UI only; underlying APIs stay callable. `flag_name` is validated against the registry. No reviewer should treat a flag as access control. |
| **Airbyte read path — destructive side effect** ⚠️ | `get_connections`/`get_one_connection` dispatch real deletions (research §5.1). The admin view **must** pass `cleanup=False`; a test asserts zero dispatches while the existing path still dispatches. |
| **Airbyte read path — crash on half-onboarded orgs** ⚠️ | Unguarded `warehouse.name` deref (`airbytehelpers.py:489`). Guarded to return `None`. |
| **Multi-tenant leak — bare-id functions** ⚠️ | `get_logs_for_job`, `get_flow_runs_by_deployment_id_v1`, flow-run log fetches take bare ids with no org check (research §5.3). The admin routes resolve every id to the URL's `org_id` before fetching; a wrong-org id returns 404, not data. |
| **Raw logs may contain PII / secrets** | Full logs are in scope (spec). Access is platform-admins only, read-only, and org-scoped. Note the exposure in §8. |
| **Self-inflicted load** | No polling on admin routes (`refreshInterval: 0`); pagination on lists; the N+1/unbounded log functions are excluded by name (research §5.1). |
| **Freshness not mistaken for live** | `AirbyteJob`/`PrefectFlowRun` are reconcile-backed; `AdminReadMeta.data_as_of` is surfaced so a stale view is not read as "healthy/empty". |

---

## 6. Testing Strategy

**Backend — admin access model (Milestone 1) — DONE, 40 tests:**
- **The gate:** a signed-in non-admin gets 403 from `get_admin_currentuser` and every other admin route; a platform admin resolves identity. This is the whole security boundary, so it is tested directly rather than through a session artifact.
- **Router shape:** `admin_router.auth is NOT_SET` (it inherits the API-wide middleware) and **no** route opts out with `auth=None`. This is the regression guard against anyone re-binding a bespoke session onto the router.
- **The login contract the frontend depends on:** `POST /api/v2/login/` returns `is_platform_admin: true` for an admin and `false` for a normal user. `post_login_v2` has no `response=` schema (it must return a `JsonResponse` to set cookies), so nothing else pins this key — without these two tests, dropping it from `lookup_user()` would silently break the admin sign-in.
- **Error mapping:** a wrong password raises DRF's `AuthenticationFailed`, and `drf_authentication_failed_handler` turns it into 401 rather than the previous 500.
- **Cookie-path coverage, ported not lost:** when `test_admin_auth.py` was deleted, its two tests covering `CustomJwtAuthMiddleware.__call__` — malformed cookie → 401, expired cookie → 498 — were **moved into `test_auth.py`** and retargeted at the normal `access_token`. `test_auth.py` had no coverage of that path, and it is live on every authenticated route. Both now assert the message as well as the status.
- **REGRESSION:** `test_user_org_api.py` (69 tests: login v1/v2, logout, refresh, invite) passes **unmodified**. It exercises the normal login and invite paths the portal now shares.

**Frontend — sign-in and sign-out (Milestone 1) — DONE:**
- The sign-in page posts to `/api/v2/login/`; a **successful** login for a non-admin is refused locally on `is_platform_admin` and does not navigate (the non-admin case is a resolved request now, not a rejected one).
- Sign-out calls the shared `/api/logout/`, never an admin-specific route; it clears the store, tracks the event, and lands on `/admin/login`; and a **failed** network call still signs the user out locally rather than stranding them in a signed-in-looking shell.

**Backend — feature areas:**
- Notifications: preview returns a count matching `len(get_recipients)` and **never** the list; author is server-derived (a client-supplied `author` is ignored); `scope`/`target_org` persist and show in history; cancel refuses an already-sent notification. No read-count test — that endpoint is out of scope.
- Feature flags: `PUT` on/off writes the org row; `DELETE` clears it; unknown `flag_name` → 400; the existing `GET /api/organizations/flags` and `test_feature_flags` stay green.
- Airbyte/pipeline: **`cleanup=False` dispatches zero deletions** (mock + assert 0) while `cleanup=True` still dispatches; warehouse-null returns `warehouse_name=None`; a wrong-org `deployment_id`/`job_id` → 404; external timeout → `partial:true`, not 500; the existing single-org endpoints (research §5.5) behave unchanged.

**Frontend (Jest + Playwright):**
- `client-layout` treats `/admin/login` as public; `AdminGuard` reads `/api/v1/admin/currentuser` and bounces a non-admin to the admin sign-in; `getNavItems` still hides "Admin Portal" for non-admins.
- Composer blocks submit before a preview count resolves; audience maps to the right `SentToEnum`.
- Playwright: admin signs in independently; a normal session does not grant `/admin`; broadcast compose→preview→confirm→appears in history; a non-admin is refused; the reused v1 org/user flows still work behind the admin session.
- **Session isolation:** signing into the admin portal does not sign you into the normal product, and logging out of one leaves the other signed in.

**Test data:** one platform admin who is also an OrgUser (Meera in a demo org); one plain org Admin (Sarah in Akshara) for the negative path; one org with no warehouse and one mid-onboarding pipeline for the read-view edge cases.

---

## 7. Milestones

Each milestone is one reviewable PR set (backend PR first where both are touched). **No milestone provisions `insights.dalgo.org` — it is already live.** Organization onboarding is **existing** and is not a milestone.

#### Milestone 1: Admin access model — **SHIPPED 2026-07-26**

- **Deliverable:** an admin sign-in screen and sign-out over the **shared** product session, with `@platform_admin_required` as the enforced boundary on every admin route.
- **Services:** DDP_backend, webapp_v2

**Shipped in four commits** (all local on `feature/admin-portal-m4-users`, not yet pushed):

| Commit | Repo | What it did |
|---|---|---|
| `869af4af` | DDP_backend | Convention/duplication cleanup ahead of the rework: deleted two schemas that duplicated existing ones (`AdminInviteUserSchema` → `NewInvitationSchema`, `AdminLoginSchema` → `LoginPayload`), added `AdminInvitationSchema.from_model()`, moved the org-payload widening into the service, routed the invite / role-change / remove endpoints through `admin_service` wrappers, typed four untyped routes. |
| `eca9865f` | DDP_backend | **The reversal.** Removed `AdminJwtAuthMiddleware`, the `admin_access_token`/`admin_refresh_token` cookies, `issue_admin_session`/`refresh_admin_session`, the admin `login`/`logout`/`token/refresh` routes, the three session exception classes, and the `JWT_ADMIN_*` settings. Kept `GET /admin/currentuser`. Added the `AuthenticationFailed → 401` handler. |
| `d1227c0` | webapp_v2 | Sign-in switched to `POST /api/v2/login/` with the platform-admin check read from the response; removed the admin-aware refresh routing; kept `adminAwareLoginPath` so an admin 401 still lands on `/admin/login`. |
| `968435a` | webapp_v2 | Added the sidebar **"Log out"** control — full shared logout, reusing the normal app's endpoint, store method, analytics event, and handler shape. |

> **Note on commit ordering.** `eca9865f` (backend) and `d1227c0` (frontend) are a **breaking pair** — the backend deletes the admin login/logout/refresh routes and the frontend is what stops calling them. They must deploy together. `968435a` depends on `d1227c0`, so it cannot ship ahead of the backend either.

- **Acceptance — met:** a platform admin signs in at `/admin/login` and enters the portal; a non-admin who signs in correctly is refused entry and gets 403 from every admin route; `test_user_org_api.py` passes unmodified (69 tests), proving the shared login and invite paths are unharmed; a wrong password now returns 401 instead of 500.
- **Not done, deliberately:** no separate admin session. See §3.2 for why it was reversed.

#### Milestone 2: Broadcast notifications
- **Deliverable:** platform admins compose, preview, send/schedule, cancel, and review broadcasts. No read tracking, no audit trail (spec, corrected 2026-08-19).
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] Migration: additive `scope` + `target_org` on `Notification`. Reuses the existing `Notification`/`NotificationRecipient` models as-is — no new model.
  - [ ] Admin routes on the service functions: `preview` (count only), create (author server-derived, persists scope/target_org), cancel, history (audience, time, recipient count — no read-count endpoint).
  - [ ] Frontend: `app/admin/notifications/*` composer + history (reuse `NotificationRow`); un-disable the nav item; confirm message-escaping.
  - [ ] Tests per §6.
- **Acceptance:** Meera sends to one org, sees "reaches 42 people", it appears in those users' notifications, and the history shows audience and recipient count; a scheduled broadcast can be cancelled before it sends; a 0-recipient audience is blocked.

#### Milestone 3: Per-org feature flags
- **Deliverable:** platform admins turn each feature on/off per org.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] Admin endpoints: catalog, per-org read, set on/off, clear; small `clear_org_flag` in `utils/feature_flags.py`. Reuses `OrgFeatureFlag` as-is — no new model, no audit fields, no global-default-inheritance change.
  - [ ] Frontend: per-org Flags tab + portal-wide matrix; serve the catalog; un-disable the nav item.
  - [ ] Tests per §6 (incl. the existing `/api/organizations/flags` unchanged).
- **Acceptance:** Meera turns `REPORTS` on for Akshara only; Akshara's users see it, others unchanged; a non-admin gets 403 on every flag route.

#### Milestone 4: Airbyte & pipeline read-only view
- **Deliverable:** platform admins view any org's connections, sync history, pipeline runs, and full logs — read-only.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] `cleanup=False` on `get_connections`/`get_one_connection` + warehouse-deref guard (with the regression that `cleanup=True` still dispatches).
  - [ ] Admin read endpoints on the safe primitives; `org_id` in the URL; org-ownership resolution before any bare-id log fetch; `AdminReadMeta` on every response.
  - [ ] Frontend: Airbyte + Pipelines tabs (reuse props-only components; no polling; show `data_as_of`).
  - [ ] Tests per §6 (destructive-dispatch, warehouse-null, wrong-org 404, external-failure partial).
- **Acceptance:** Arjun opens Akshara's Airbyte tab and reads a failed sync's full logs; opening ten orgs issues no background polling and schedules no deletions; a wrong-org id returns 404.

---

## 8. Open Questions & Risks

**Open questions:**

| # | Question | Affects | Default if unanswered |
|---|---|---|---|
| ~~Q1~~ | ~~**Admin session lifetime** — 15 min / 8 h or match the normal app?~~ **MOOT.** There is no separate admin session, so there is no separate lifetime to choose. The portal uses the normal session's 30 min / 7 days. | — | Closed by `eca9865f`. |
| Q2 | **Close the pre-existing ungated `/api/notifications/*` gap (research bug #2)** as part of this work, or track separately? | M2 | Track separately; the admin path is independent and gated. |
| Q3 | **Full raw logs contain potential PII/secrets** — is platform-admin-only, read-only, org-scoped access acceptable, or should logs be summarized/redacted? (Spec chose full logs.) | M4 | Full logs, platform-admins only, as specced. |
| Q4 | **Connection listing:** `cleanup=False` param on the shared function (proposed) vs a new read-only lister? | M4 | `cleanup=False` param with the regression test. |
| ~~Q5~~ | ~~**Do all platform admins have ≥1 OrgUser row?**~~ **MOOT as asked** — there is no admin token to mint. The underlying constraint **remains and is unchanged**: `CustomJwtAuthMiddleware` loads `request.orguser`, and `@platform_admin_required` reads it, so a platform admin belonging to no org still cannot use the portal. Untested and unfixed. | — | Assume every platform admin has ≥1 org; fast-follow if one does not. |

**Risks:**

| Risk | Mitigation |
|---|---|
| Changes to shared auth break the normal product. | Two shared touches shipped: the cookie-name constant (non-behavioral) and the `AuthenticationFailed → 401` handler. Both gated by `test_user_org_api.py` (69 tests) passing **unmodified**. |
| The admin sign-in screen is mistaken for a security boundary. | It **is** just a screen — deliberately. The boundary is `@platform_admin_required` on every route, tested by "signed-in non-admin → 403". The docs say this plainly so no reviewer assumes the screen protects anything. |
| A broadcast is irreversible and platform-wide. | Mandatory preview count + confirm; author server-derived; 0-recipient blocked; escaping confirmed. |
| The read-only view triggers deletions or crashes on live orgs. | `cleanup=False` (asserted zero dispatches) + warehouse-deref guard, both regression-tested. |
| Cross-tenant leak via bare-id log fetches. | Resolve every id to the URL's `org_id` before fetching; wrong-org → 404 test. |
| `is_platform_admin` now has THREE frontend read paths — the Zustand store (normal sidebar), the `/admin/currentuser` SWR call (AdminGuard), and the `/api/v2/login/` response body (sign-in screen). They could disagree. | All three read the same server-side flag, and the server re-checks it per request, so a disagreement is a stale-UI bug, not an access-control hole. Worth consolidating later; noted rather than fixed. |

---

## Next

**Milestone 1 is shipped** (see §7 and `features/admin-portal/tasks.md`). Milestones 2–4 — broadcast notifications, per-org feature flags, and the read-only Airbyte/pipeline view — are unchanged by the session rework and remain as planned.

Next: review Milestones 2–4, then `/engineering/execute-plan features/admin-portal/plan.md` starting at Milestone 2.
