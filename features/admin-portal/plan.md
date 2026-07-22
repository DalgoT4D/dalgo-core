# Admin Portal — Implementation Plan

**Status:** Draft — for engineering review
**Date:** 2026-07-22 · **Tracking:** Issue #1254
**Spec:** `features/admin-portal/spec.md` · **Research:** `features/admin-portal/research.md`

**Acronyms:** HLD (High-Level Design) · LLD (Low-Level Design) · JWT (the signed login token) · claim (a named field inside the token) · cookie (a value the browser stores per host and re-sends) · host-only cookie (bound to the exact host that set it, no `domain=`) · FK (foreign key) · CRUD (create, read, update, delete) · PII (personally identifiable information) · N+1 (one query that fans out into many).

> **One-paragraph summary.** The admin portal already ships organization onboarding and user management at `insights.dalgo.org/admin`. This plan adds the rest of the spec: an **independent admin sign-in** (its own cookie + session, separate from the normal product), **broadcast notifications**, **per-org feature flags**, and a **read-only Airbyte/pipeline view**. The portal stays a **path (`/admin`) inside the existing production deployment** — no new domain, no separate app or port. The **independent session is the foundational new work**; the three feature areas build on top of it.

---

## 1. Overview

**Feature summary:** Complete the admin portal — give it its own login/session, and add broadcast notifications, per-org feature flags, and a read-only Airbyte/pipeline debugging view. Organization onboarding and user management are already shipped (research §1) and are re-homed behind the new admin session, not rebuilt.

**Where it lives:** `insights.dalgo.org/admin` — a path inside the current production deployment. `insights.dalgo.org` is already live for NGO customers, so **there is no domain, DNS, or hosting to provision.**

**Services affected:**

| Service | Role |
|---|---|
| DDP_backend (Django + Django Ninja) | The admin session (new cookie + JWT claim + dedicated auth middleware), and the admin endpoints for notifications, feature flags, and the Airbyte/pipeline read view. |
| webapp_v2 (Next.js 15) | Admin sign-in screen; wire the admin session; new admin screens (Notifications, Feature flags, Airbyte/Pipelines tabs); un-disable the placeholder nav items. |
| prefect-proxy | Not touched (pipeline data is read from the DB, not the proxy). |
| Infra / DNS / TLS | **Nothing** — the host is already live. |

---

## 2. Blast Radius

Traversed from `docs/domain-map.md`. The portal **operates** entities but changes almost none of their data models. The one additive data change is on Notification.

| Surface | Hop | Why affected | Status |
|---|---|---|---|
| **Organization** | 0 | Onboarding CRUD | **Existing (shipped).** No change. |
| **OrgUser** | 0 | User management; removal orphans owned content | **Existing (shipped).** Removal warning already built. |
| **Notification** | 0 | Broadcasts create Notification + NotificationRecipient rows | **In scope (new).** Additive fields to record audience for history (§4.1). |
| **OrgUser (as recipient)** | 1 | A broadcast is delivered to OrgUsers in-app + email | **In scope.** Reuses the existing delivery path (research §3). |
| **Source / Warehouse / Transform / Pipeline / Data Quality** | 0–1 | Read-only Airbyte/pipeline view reads connection + run status/logs | **In scope (new), read-only.** No data-model change; safety work required (research §5). |
| **Chart / Dashboard / Metric / KPI / ReportSnapshot / Share link** | 2+ | — | **Not affected.** The portal never creates or edits analytics entities. Only indirect tie: removing an OrgUser orphans `created_by` on Chart/Dashboard/ReportSnapshot — existing shipped behavior with a warning. |
| **Alert** | 2 | — | **Not affected.** Alerts deliver directly to email/Slack and are decoupled from Notification (domain map). Broadcasts do not touch Alerts. |
| **Feature flags (platform config, not a domain-map entity)** | — | Toggling a flag changes which product surfaces (e.g. Reports, Data Quality) an org sees | **In scope (new).** Changes visibility, not data. Per-org on/off only (spec). |

> **The rule:** the portal moves and manages things; it does not change what analytics entities *are*. So the blast radius is auth + notifications + config + read-only pipeline views — the analytics data model is untouched.
> **Example:** Meera turns `REPORTS` off for Akshara. Akshara's users stop seeing the Reports nav item. No Chart, Dashboard, or ReportSnapshot row changes.
> **Why it matters:** it bounds review to auth correctness, notification blast radius, and the read-only-view safety issues — there is no risk to any NGO's analytics data from this work.

**No unaddressed surfaces.** Every domain-map entity above has a status the spec already decides; none is silently included or excluded.

---

## 3. High-Level Design (HLD)

### 3.1 One deployment, one path, two independent sessions

```
Browser                         insights.dalgo.org  (one existing deployment, webapp_v2)
───────                         ┌─────────────────────────────────────────────────────────┐
insights.dalgo.org/…      ───►  │ client-layout: normal product  (AuthGuard > MainLayout)   │
insights.dalgo.org/admin  ───►  │ client-layout: /admin  (AuthGuard? no → admin sign-in →   │
                                │                 AdminGuard > AdminLayout)                 │
                                └─────────────────────────────────────────────────────────┘
        │ normal login                                   │ admin login
        │ POST /api/v2/login/                             │ POST /api/v1/admin/login/
        │ Set-Cookie access_token                         │ Set-Cookie admin_access_token
        ▼ (host-only on API host)                         ▼ (host-only on API host, claim session=admin)
      ┌──────────────────────────── DDP_backend (api host) ─────────────────────────────┐
      │ CustomJwtAuthMiddleware   reads access_token       → normal product APIs         │
      │ AdminJwtAuthMiddleware    reads admin_access_token  → /api/v1/admin/* (all)       │
      │   + requires session=admin claim                     @platform_admin_required     │
      └──────────────────────────────────────────────────────────────────────────────────┘
```

A browser signed into both sends **both** cookies to the API host on every request. The admin API honors **only** `admin_access_token` with the `session=admin` claim; the normal `access_token` authenticates nothing under `/api/v1/admin/*`. Two independent sessions, one deployment, no new host.

### 3.2 The independent admin session — the main new work

> **The rule:** the separate sign-in is a real boundary because the backend requires a distinct session artifact, not because `/admin` looks different.
> **Example:** Sarah (org Admin, not a platform admin) is signed into the normal product. She opens `/admin`; her `access_token` is sent but the admin API ignores it, so she gets the admin sign-in and — lacking platform-admin privilege — is refused there.
> **Why it matters:** a separate screen over the shared cookie would be theatre, bypassable by calling the API directly.

Five requirements, each met server-side:

1. **Distinct login → distinct cookie.** New `POST /api/v1/admin/login/` verifies credentials **and** `is_platform_admin=True` before issuing anything, then sets `admin_access_token` + `admin_refresh_token` (new cookie names) carrying a `session="admin"` claim. The normal `/api/v2/login/` is untouched.
2. **Gate reads the admin cookie only.** `admin_router` gets router-level `auth=AdminJwtAuthMiddleware()`, which reads `admin_access_token` and rejects a token without `session="admin"`. A normal `access_token` alone authenticates nothing admin.
3. **Non-admin refused at sign-in.** Correct password but not a platform admin → 403, **no cookie set**. Refused at the door.
4. **Independent logout.** `POST /api/v1/admin/logout/` clears only the `admin_*` cookies; the normal logout clears only the normal cookies.
5. **Shorter lifetime** (higher-privilege surface): admin access **15 min**, refresh **8 hours** (vs 30 min / 7 days), via new env vars. `POST /api/v1/admin/token/refresh` mirrors the normal refresh on the admin cookie.

`@platform_admin_required` stays as-is and re-checks `is_platform_admin` from the database on every admin request (research §2.2), so a revoked flag mid-session fails closed.

### 3.3 New endpoints (all under `/api/v1/admin/`, all behind the admin session)

| Area | Endpoint(s) |
|---|---|
| Session | `POST /login/` (auth=None), `POST /logout/`, `POST /token/refresh` (auth=None), `GET /currentuser` |
| Notifications | `GET /notifications` (history), `POST /notifications/preview` (recipient count), `POST /notifications` (create/schedule), `DELETE /notifications/{id}` (cancel scheduled), `GET /notifications/{id}/recipients` (read counts) |
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
| **None** for the admin session | cookie + JWT claim only | No |
| **Notification: add `scope` + `target_org`** | `ddpui/models/notifications.py` | **Yes — additive, nullable.** `scope = CharField(null=True)` (`"all_users"` / `"all_org_users"`), `target_org = FK(Org, null=True, SET_NULL)`. Records what a broadcast targeted so history can show it (today the audience is resolved to ids and discarded — research §3.1). Backfill leaves existing rows NULL = "audience unknown (legacy)". |
| **None** for feature flags | `OrgFeatureFlag` already has per-org rows; on/off uses `enable/disable_feature_flag` | No |
| **None** for Airbyte/pipeline | read-only | No |

### 4.2 Backend — the admin session (per the shipped admin-portal conventions)

Business logic goes in the **service** (`ddpui/core/admin/admin_service.py`, logger `"ddpui.core.admin"`); the endpoint only sets cookies (the one HTTP concern). This matches the service's own documented convention (research §1).

```python
# admin_service.py (pseudo) — returns primitives, no HTTP
def issue_admin_session(username, password) -> tuple[dict | None, str | None]:
    # 1. authenticate credentials (CustomTokenObtainSerializer / Django auth)
    # 2. verify UserAttributes.is_platform_admin is True → else (None, "not a platform admin")
    # 3. mint token with session="admin" claim + admin lifetimes
    # returns ({"access":..., "refresh":...}, None) or (None, error)
```

- **`AdminJwtAuthMiddleware`** (`ddpui/auth.py`): subclass `CustomJwtAuthMiddleware`, overriding only the cookie name (`admin_access_token`) and adding a `session == "admin"` claim check. To subclass cleanly, extract the literal `"access_token"` in `CustomJwtAuthMiddleware.__call__` (`auth.py:115`) into a class attribute — a **non-behavioral** change, regression-proven (§6). Everything else (orguser loading, 498/401, blacklist) is inherited, so `@platform_admin_required` works unchanged.
- **The `session="admin"` claim** is stamped in `CustomTokenObtainSerializer.get_token` alongside `orguser_role_key` (`auth.py:270`); it survives refresh automatically (research §2.3). Use an admin-scoped mint path so the normal login token does **not** carry it.
- **Router wiring:** `admin_router = Router(auth=AdminJwtAuthMiddleware())` (replaces the bare `Router()` at `admin_api.py:33`). Router-level auth overrides the global `src_api` default (research §2.5). `login` and `token/refresh` set `auth=None`. **Every existing org/user route is now behind the admin session** — the shipped portal is re-homed, not rebuilt.
- **Endpoints** added to `admin_api.py` (logger `"ddpui"`): login (auth=None; 401 bad creds, **403 non-admin, no cookie**, else set `admin_*` cookies), logout (`{"success": 1}` to match the neighbor style at `admin_api.py:435`), `token/refresh` (auth=None), `currentuser` (typed response with `is_platform_admin`).
- **Settings** (`ddpui/settings.py`): `JWT_ADMIN_ACCESS_TOKEN_EXPIRY_MINUTES` (15), `JWT_ADMIN_REFRESH_TOKEN_EXPIRY_HOURS` (8) — following the existing `JWT_*_EXPIRY_*` shape (research §2.4). Reuse the existing cookie flags; **no `domain=`** (host-only, same as the normal cookies).

### 4.3 Backend — the three feature areas

**Notifications** (build on the service functions; do **not** use the broken/ungated HTTP route — research §3.3):
- `POST /notifications/preview` → `len(get_recipients(...))` only. **Never return the recipient list** (would leak a cross-org email roster).
- `POST /notifications` → build a proper `NotificationDataSchema` (with `email_subject`, and **`author` derived server-side** from `request.orguser.user`, not client input) → `create_notification`; persist `scope`/`target_org`; block a 0-recipient audience.
- `DELETE /notifications/{id}` → `delete_scheduled_notification` (refuses if already sent).
- `GET /notifications` (history) → a **new admin query** (do not extend `get_notification_history`, which has a `FieldError` bug — research §7); `GET /notifications/{id}/recipients` → read counts from `NotificationRecipient.read_status`.

**Feature flags** (per-org on/off — model already supports it, research §4):
- `GET /flags/catalog` → the `FEATURE_FLAGS` registry (ends the Python/TS duplication). `GET /orgs/{id}/flags` → `get_all_feature_flags_for_org`. `PUT /orgs/{id}/flags/{name}` → `enable_feature_flag`/`disable_feature_flag` (validated against the registry). `DELETE` → clear the org row (a small new `clear_org_flag` in `utils/feature_flags.py`, since only a "write False" path exists today). No migration; no audit fields (out of scope per spec).

**Airbyte/pipeline read-only view** — the safety work is the point (research §5):
- **Connections list:** add `cleanup: bool = True` to `get_connections`/`get_one_connection` and skip the `delete_airbyte_connections.delay(...)` dispatch when `False` (`airbytehelpers.py:532-536`, `:553-555`); the admin view passes `cleanup=False`. **Guard the warehouse deref** (`:489`) — return `warehouse_name=None` when the org has no warehouse.
- **Sync history:** reuse `get_sync_job_history_for_connection` (safe, DB-backed, paginated).
- **Pipelines:** reuse the `PipelineService.get_pipelines(org)` join pattern; runs via `get_flow_runs_by_deployment_id_v1` with a **pre-scoped** deployment-id set (`OrgDataFlowv1.filter(org=target_org)`).
- **Full raw logs** (spec choice): `get_logs_for_job` / flow-run logs, but **only after** resolving `job_id → OrgTask.org` and `flow_run_id/deployment_id → OrgDataFlowv1.org` and confirming it equals `org_id` from the URL. Avoid `recurse_flow_run_logs` and the two unguarded history endpoints (research §5.1).
- Every route takes `org_id` in the **URL** (never the `x-dalgo-org` header) and carries an `AdminReadMeta` (`data_as_of`, `source`, `partial`) so the UI labels freshness honestly.

### 4.4 Frontend

- **Admin sign-in:** new `app/admin/login/page.tsx`; add `/admin/login` to the public-route handling in `components/client-layout.tsx` so it renders without the normal `AuthGuard`. It calls `POST /api/v1/admin/login/`; on 403 shows "not a platform admin"; on success renders `/admin`.
- **AdminGuard:** read identity from **`GET /api/v1/admin/currentuser`** (admin cookie), not `/api/currentuserv2` (`AdminGuard.tsx:33`); non-admin bounce → the admin sign-in, not `/`.
- **Back-link:** `AdminLayout` "Back to Dalgo" (`:78`) stays a link to the normal product (`/`) — a convenience link, independent sessions (spec).
- **Notifications:** new `app/admin/notifications/page.tsx` (history table + "New broadcast"); composer with audience (whole platform / one org), recipient-count preview, send-now/schedule, cancel; reuse the props-only `NotificationRow` for rendering (research §3.4). Un-disable the nav item (`AdminLayout.tsx:22`).
- **Feature flags:** new `app/admin/feature-flags/page.tsx` (per-org matrix) + a Flags tab on org detail; un-disable the nav item (`AdminLayout.tsx:23`). Serve the catalog from `/flags/catalog` rather than the hand-maintained TS enum.
- **Airbyte/Pipelines:** two new tabs on `app/admin/organizations/[id]/page.tsx`; reuse props-only presentational components (`sync-status-cell`, `log-card`, `connection-row`); **no polling** (`refreshInterval: 0`); surface `data_as_of`.
- **Refresh handling:** admin API calls reuse `lib/api.ts`, whose refresh trigger is **401** (research §2.7); the admin refresh must point at `/api/v1/admin/token/refresh`.

### 4.5 Integration points

- Frontend ↔ backend: cookie-based, `credentials: 'include'`. The admin screens call `/api/v1/admin/*`; the browser attaches the `admin_access_token` cookie.
- Backend ↔ external: notifications reuse SES/Discord; Airbyte/Prefect are read from the DB except raw logs (gated live fetch).

---

## 5. Security Review

| Area | Finding / plan |
|---|---|
| **Independent session is server-enforced** | The boundary is the `admin_access_token` cookie + `session="admin"` claim + `AdminJwtAuthMiddleware` on `admin_router`, not the `/admin` path. A normal `access_token` authenticates nothing admin. |
| **Non-admin refused pre-cookie** | `POST /admin/login/` verifies `is_platform_admin` before issuing any cookie → 403, no session (spec requirement). |
| **Flag revoked mid-session** | `@platform_admin_required` re-reads `UserAttributes.is_platform_admin` per request (`auth.py:75-76`) — a revoked admin is locked out within one request. |
| **The one shared-auth touch** | Extracting the cookie-name constant in `CustomJwtAuthMiddleware` is non-behavioral and **regression-proven byte-for-byte** (§6). |
| **Broadcast is the highest-reach action** | Every admin route is `@platform_admin_required` behind the admin session. Author is **server-derived** (not the client-supplied `author` the current schema takes — research §3.3). Mandatory recipient-count preview + confirm; a 0-recipient audience is blocked. |
| **Message rendering / stored XSS** | `NotificationRow` linkifies URLs and now renders admin-authored content to every user (research §3.4). Confirm escaping before enabling send. |
| **Notification data exposure** | `/preview` returns a **count only** — never the recipient list. Read-count report is per-notification, no inline emails. |
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

**Backend — admin session (Milestone 1):**
- `issue_admin_session`: admin creds → token with `session="admin"` + admin lifetimes; non-admin creds → `(None, error)`, no token; bad creds → error.
- `POST /admin/login/`: admin → 200 + `Set-Cookie admin_access_token`; **non-admin → 403, no Set-Cookie**; bad password → 401.
- `AdminJwtAuthMiddleware`: admin cookie+claim → admits, `request.orguser` set; **a bare normal `access_token` → 401 on every `/api/v1/admin/*`**; admin cookie without the claim → 401.
- `logout` clears only `admin_*`; `token/refresh` works on the admin cookie only; lifetimes expire at 15 min / 8 h.
- **REGRESSION (gates the cookie-name extraction):** the existing `test_user_org_api.py` auth suite (login v1/v2, logout, refresh, `CustomJwtAuthMiddleware`) passes **unchanged**; explicit asserts that `/api/v2/login/` still sets a cookie named `access_token` with the same flags and the normal flow still 401/refreshes exactly as before. The existing `test_admin_api.py` (403-for-non-admins) stays green, now behind the admin session.

**Backend — feature areas:**
- Notifications: preview returns a count matching `len(get_recipients)` and **never** the list; author is server-derived (a client-supplied `author` is ignored); `scope`/`target_org` persist and show in history; cancel refuses an already-sent notification; read counts match `NotificationRecipient`.
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

#### Milestone 1: Independent admin session (foundational)
- **Deliverable:** a real, server-enforced admin sign-in; the existing org/user portal re-homed behind it; the normal product's auth proven unchanged.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] Extract the cookie-name constant in `CustomJwtAuthMiddleware`; add the byte-for-byte main-auth **regression test**.
  - [ ] `AdminJwtAuthMiddleware` (subclass; `admin_access_token` + `session="admin"` claim); admin-scoped mint + `JWT_ADMIN_*` settings.
  - [ ] `admin_service.issue_admin_session`; admin `login`/`logout`/`token/refresh`/`currentuser` endpoints; `admin_router = Router(auth=AdminJwtAuthMiddleware())`.
  - [ ] Frontend: `app/admin/login/page.tsx`; `/admin/login` public in `client-layout`; `AdminGuard` → `/api/v1/admin/currentuser`; admin refresh → `/api/v1/admin/token/refresh`.
  - [ ] Tests + isolation tests per §6.
- **Acceptance:** a platform admin signs in at `/admin` independently; a non-admin is refused (403, no cookie); every `/api/v1/admin/*` rejects a bare normal cookie; the normal-product auth suite passes unchanged; the shipped org/user flows work behind the admin session.

#### Milestone 2: Broadcast notifications
- **Deliverable:** platform admins compose, preview, send/schedule, cancel, and review broadcasts with read counts.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] Migration: additive `scope` + `target_org` on `Notification`.
  - [ ] Admin routes on the service functions: `preview` (count only), create (author server-derived, persists scope/target_org), cancel, history, read counts.
  - [ ] Frontend: `app/admin/notifications/*` composer + history (reuse `NotificationRow`); un-disable the nav item; confirm message-escaping.
  - [ ] Tests per §6.
- **Acceptance:** Meera sends to one org, sees "reaches 42 people", it appears in those users' notifications, and the history shows audience + read count; a scheduled broadcast can be cancelled before it sends; a 0-recipient audience is blocked.

#### Milestone 3: Per-org feature flags
- **Deliverable:** platform admins turn each feature on/off per org.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] Admin endpoints: catalog, per-org read, set on/off, clear; small `clear_org_flag` in `utils/feature_flags.py`.
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
| Q1 | **Admin session lifetime** — 15 min / 8 h (proposed) or match the normal app (30 min / 7 days)? | M1 | 15 min / 8 h. |
| Q2 | **Close the pre-existing ungated `/api/notifications/*` gap (research bug #2)** as part of this work, or track separately? | M2 | Track separately; the admin path is independent and gated. |
| Q3 | **Full raw logs contain potential PII/secrets** — is platform-admin-only, read-only, org-scoped access acceptable, or should logs be summarized/redacted? (Spec chose full logs.) | M4 | Full logs, platform-admins only, as specced. |
| Q4 | **Connection listing:** `cleanup=False` param on the shared function (proposed) vs a new read-only lister? | M4 | `cleanup=False` param with the regression test. |
| Q5 | **Do all platform admins have ≥1 OrgUser row?** A zero-org admin can mint an admin token but then 401s on admin calls (the middleware loads `request.orguser`). | M1 | Assume yes; fast-follow to tolerate no-org admins if any exist. |

**Risks:**

| Risk | Mitigation |
|---|---|
| The cookie-name extraction changes normal-product auth. | Byte-for-byte regression test gates it (§6); it is a constant lift, no logic change. |
| Admin session mistaken for "just a login screen" over the shared cookie. | Enforcement is the dedicated middleware + claim, tested by "bare normal cookie → 401 on every admin route". |
| A broadcast is irreversible and platform-wide. | Mandatory preview count + confirm; author server-derived; 0-recipient blocked; escaping confirmed. |
| The read-only view triggers deletions or crashes on live orgs. | `cleanup=False` (asserted zero dispatches) + warehouse-deref guard, both regression-tested. |
| Cross-tenant leak via bare-id log fetches. | Resolve every id to the URL's `org_id` before fetching; wrong-org → 404 test. |
| `is_platform_admin` has two frontend read paths (store vs SWR) — they could disagree. | The admin shell reads the admin `currentuser`; keep the normal sidebar on the store; note the split in the PR. |

---

## Next

Draft v1 saved. Review the plan and tell me what to revise — architecture, scope, milestones, anything. When ready, run `/engineering/execute-plan features/admin-portal/plan.md` to implement (Milestone 1 first — the independent admin session with the normal-auth regression proof).
