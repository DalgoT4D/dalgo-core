# Implementation Plan — Admin Portal v1.1 (Separate app + independent admin session)

**Status:** Draft v2 — for engineering review
**Parent version:** `features/admin-portal/v1/spec.md` · `features/admin-portal/v1/plan.md` · `features/admin-portal/v1/research.md`
**Research:** `features/admin-portal/v1.1/research.md`
**Date:** 2026-07-22
**Owner:** Veekshitha Nelluru (DMP 2026) · Issue #1254

**Acronyms:** HLD (High-Level Design) · LLD (Low-Level Design) · JWT (the signed login token) · claim (a named field carried inside the signed token, e.g. `session`) · cookie (a value the browser stores per host and re-sends) · host-only cookie (a cookie bound to the exact host that set it, with no `domain=`) · `APP_MODE` (a runtime env var telling one build whether it is serving the main app or the admin app) · OrgUser (the row linking one user to one org) · `@platform_admin_required` (the server decorator gating every admin route on `is_platform_admin`).

> **Read this first.** v1 is **already built and merged** — the `/admin` pages, `AdminGuard`, `AdminLayout`, the `@platform_admin_required` guard, the `admin_router` at `/api/v1/admin/*`, and `is_platform_admin` on the login response and `/currentuserv2` all exist (v1 research §1). This slice does **not** build portal features. It makes the admin portal a **genuinely separate application** on its own hostname (`insights.dalgo.org`; `localhost:3002` locally) with its **own independent login session**, distinct from the main app's.
>
> **Scope change from Draft v1 (2026-07-22).** The earlier draft delivered this as a *redirect*: same session, Host-routing in middleware, a login branch that sent admins to the admin host. **That approach is replaced entirely.** There is now **no redirect-on-login logic anywhere**. A Super Admin navigates directly to the admin app's URL, signs in there against a **separate cookie and session**, and a valid main-app session does **not** grant admin access. This is real backend authentication work, sized and tested with the same rigor as v1's M1–M4.

---

## 1. Overview

**Enhancement summary:** Stand the admin portal up as its **own app entry point** — its own port locally (`localhost:3002`, main app unchanged on `localhost:3001`) and its own domain in staging/prod (`insights.dalgo.org`) — reusing the existing v1 `/admin` pages and components as-is. Entry is a **separate, independent login** at that URL, backed by a **distinct admin session cookie** the backend issues and enforces separately from the main app. Remove the in-app "Admin Portal" sidebar link from the main app (D2).

**Parent version:** v1 shipped the portal as a path (`/admin`) *inside* the normal app, entered via a sidebar link, gated client-side by `AdminGuard` and server-side by `@platform_admin_required`. See `features/admin-portal/v1/plan.md`.

**What changes vs Draft v1 of this enhancement:**

| Draft v1 (replaced) | This draft |
|---|---|
| Redirect-on-login branches admins to the admin host | **No redirect anywhere.** Admin navigates to the admin URL directly. |
| One build, Host-header routing in `middleware.ts` | One build, **runtime `APP_MODE`** selects main vs admin app at the server layout; no Host-routing. |
| Shared session carries over silently (D3 "unresolved", §8 Q6) | **Separate `admin_access_token` cookie + session**, issued and enforced by the backend. D3 resolved. |
| "No backend code" | **Real backend auth work:** admin login/logout/refresh/currentuser endpoints, an admin auth middleware, an admin token claim. No DB migration. |

**Decisions confirmed with the team:**

| # | Fork | Decision |
|---|---|---|
| D1 | Deployment model | **One webapp_v2 build, two runtime processes** differentiated by `APP_MODE` (`main` \| `admin`), each on its own port/hostname. Not a second build; not Host-routing. |
| D2 | In-app `/admin` + sidebar link | **Remove from the main app.** The portal is reachable only at the admin URL. `AdminGuard` + `@platform_admin_required` stay as defense. |
| D3 | Admin authentication | **A genuinely separate, independent session.** A distinct admin-login endpoint issues an `admin_access_token` cookie (not the main app's `access_token`). `@platform_admin_required` is satisfied only by this cookie. Admin login independently verifies **valid credentials AND `is_platform_admin=True`**. Logout of one app does not affect the other. |
| D4 | Dual-role admins (also an OrgUser) | The admin app shows an **"Open Dalgo app"** link to the main app. No redirect, no lock — just a link. |
| D5 | Admin session lifetime | **Shorter than the main app**, because it is a higher-privilege surface: access **15 min**, refresh **8 hours** (one working day → daily re-auth), vs the main app's 30 min / 7 days. |

**Services affected:**

| Service | Role in this slice |
|---|---|
| DDP_backend (Django) | **Real auth work.** New admin login/logout/refresh/currentuser on `admin_router`; `AdminJwtAuthMiddleware`; an admin token claim; admin session-lifetime env vars; a one-line non-behavioral cookie-name extraction in `CustomJwtAuthMiddleware`. **No model, no migration.** |
| webapp_v2 (Next.js 15) | Runtime `APP_MODE` read in the root layout; an admin login page; admin-mode routing; admin API calls point at the admin auth endpoints; `AdminGuard`/`AdminLayout` re-pointed; sidebar link removed; new scripts + env vars. |
| prefect-proxy | Not touched. |
| Infra / DNS / TLS (ops) | `insights.dalgo.org` DNS + cert; a second deployment/process running `APP_MODE=admin` (staging + prod). |

---

## 2. Blast Radius

**This slice changes the login/auth/entry *surface* and adds a parallel auth path — it changes no product entity's data.** No Django model or migration. So the `docs/domain-map.md` product entities (Chart, Dashboard, Metric, KPI, ReportSnapshot, Alert, Share link, Notification, Source, Transform, Pipeline, Warehouse) are traversed and found **unaffected** — there is no data-model edge to propagate along. The affected surfaces are the **auth plumbing** and the **frontend app-shell selection**.

| Surface | Hop | Why affected | Status |
|---|---|---|---|
| **`CustomJwtAuthMiddleware` cookie-name** (`auth.py:115`) | 0 | Extract the hardcoded `"access_token"` to a class attribute so the admin middleware can subclass cleanly | **In scope — non-behavioral; regression-proven (M1)** |
| **`AdminJwtAuthMiddleware`** (new, `auth.py`) | 0 | Reads `admin_access_token`, requires the `session:"admin"` claim, populates `request.orguser` | **New** |
| **Admin token minting** (serializer, `auth.py`) | 0 | Stamp `session:"admin"` claim; apply admin lifetimes | **New** |
| **`admin_service.issue_admin_session()`** (new, `core/admin/admin_service.py`) | 0 | Credential auth + `is_platform_admin` check + token mint (business logic, per the admin service convention) | **New** |
| **Admin auth endpoints** (login/logout/refresh/currentuser, `admin_api.py`) | 0 | The separate session's HTTP surface; `admin_router` gains router-level admin auth | **New** |
| **Admin session env vars** (`settings.py`) | 1 | Admin access/refresh lifetimes | **New** |
| **`@platform_admin_required`** (`auth.py:63-80`) | 1 | Now reached via the admin middleware's `request.orguser`; re-checks `is_platform_admin` from the DB | **Unchanged — still the wall** |
| **Root layout → `APP_MODE`** (`app/layout.tsx` → `client-layout.tsx`) | 0 | Selects main vs admin app shell at runtime | **In scope** |
| **Admin login page** (new, webapp_v2) | 0 | The admin app's own sign-in, calling the admin login endpoint | **New** |
| **`AdminGuard`** (`components/admin/AdminGuard.tsx:33-43`) | 1 | Reads identity from the **admin** currentuser; non-admin bounce → admin login | **In scope** |
| **`AdminLayout` back-link** (`components/admin/AdminLayout.tsx:76-84`) | 1 | "Open Dalgo app" → `NEXT_PUBLIC_APP_URL` | **In scope** |
| **Sidebar "Admin Portal" link** (`components/main-layout.tsx:230-236`) | 1 | D2 removes the in-app entry | **In scope — removed** |
| **`lib/api.ts`** (`:5`, `:23`) | 1 | Admin app calls the admin auth endpoints with `credentials:'include'` | **In scope (small)** |
| **CORS / CSRF config** (`settings.py`, env) | 1 | insights is a cross-origin caller; verify per environment | **Verify (M1)** |
| **DNS / TLS + admin deployment** | 1 | `insights.dalgo.org` resolves + terminates TLS; a process runs `APP_MODE=admin` | **In scope (ops)** |
| Chart, Dashboard, Metric, KPI, ReportSnapshot, Alert, Share link, Notification, Source, Transform, Pipeline, Warehouse | 2+ | — | **Not affected** — no data-model/query change |

> **The rule:** this slice adds a *parallel auth path* and moves the portal's front door; it does not touch any product entity's data. So the blast radius is auth + app-shell plumbing, and the domain-map's data entities are untouched.
> **Why it matters:** it bounds the review to auth correctness and session isolation — there is no risk to any NGO's data, dashboards, or pipelines from this change.

---

## 3. High-Level Design (HLD)

### 3.1 Two apps, two sessions, one build

```
  ┌──────────────────────── webapp_v2 (one build) ────────────────────────┐
  │                                                                        │
  │  APP_MODE=main   → localhost:3001 / app.dalgo.org                      │
  │     app/layout.tsx (server) reads APP_MODE → passes appMode='main'     │
  │     client-layout serves: /login → MainLayout.   /admin → NOT served.  │
  │                                                                        │
  │  APP_MODE=admin  → localhost:3002 / insights.dalgo.org                 │
  │     app/layout.tsx (server) reads APP_MODE → passes appMode='admin'    │
  │     client-layout serves: admin login → AdminGuard → AdminLayout       │
  │     (reuses the v1 /admin pages/components as-is)                      │
  └────────────────────────────────────────────────────────────────────────┘
            │                                          │
   main login (POST /api/v2/login/)          admin login (POST /api/v1/admin/login/)
   Set-Cookie: access_token                  Set-Cookie: admin_access_token
   (host-only on API host)                   (host-only on API host, claim session=admin)
            │                                          │
            ▼                                          ▼
  ┌──────────────────────────── DDP_backend (one API host) ────────────────┐
  │  CustomJwtAuthMiddleware        reads  access_token          → main app │
  │  AdminJwtAuthMiddleware (new)   reads  admin_access_token +  session=admin
  │     └─ router-level auth on admin_router → every /api/v1/admin/* route  │
  │        @platform_admin_required re-checks is_platform_admin (DB)        │
  └────────────────────────────────────────────────────────────────────────┘

  A browser logged into BOTH sends BOTH cookies to the API host on every
  request. The admin API honors only admin_access_token+claim; the main
  cookie authenticates nothing on /api/v1/admin/*. Two independent sessions.
```

### 3.2 The admin session (the core of D3)

- **Distinct login endpoint.** `POST /api/v1/admin/login/` (`auth=None`) on `admin_router`. It authenticates credentials **and** verifies `is_platform_admin=True` *before issuing anything*. Wrong password → 401. Correct password, not a platform admin → **403, no cookie, no session** (refused at the login screen itself, requirement #3).
- **Distinct cookie.** On success it sets `admin_access_token` + `admin_refresh_token` (new names; same `Secure`/`HttpOnly`/`SameSite` settings as the main cookies), carrying a `session:"admin"` claim. The main app's `/api/v2/login/` and its `access_token` cookie are **byte-for-byte untouched** (requirement: don't disturb the main flow for everyone else).
- **Distinct enforcement.** `admin_router` gets router-level `auth=AdminJwtAuthMiddleware()`. That middleware reads **only** `admin_access_token` and rejects any token lacking `session:"admin"`. A valid main-app `access_token` alone therefore authenticates nothing on the admin API (requirement #2). `@platform_admin_required` stays unchanged and re-checks `is_platform_admin` from the DB (so a revoked flag mid-session fails closed).
- **Independent logout.** `POST /api/v1/admin/logout/` blacklists and deletes only the `admin_*` cookies. The main `POST /api/logout/` is untouched and deletes only the main cookies. Distinct names ⇒ logging out of one leaves the other intact (requirement #4).
- **Lifetime (D5, requirement #5).** Admin access **15 min**, refresh **8 hours** — shorter than the main app (30 min / 7 days) because admin is higher-privilege. `POST /api/v1/admin/token/refresh` (`auth=None`) mirrors the main v2 refresh on the admin cookie.
- **Admin identity.** `GET /api/v1/admin/currentuser` returns `is_platform_admin` + minimal identity via the admin cookie, so `AdminGuard` reads identity from the admin session, not the main app's `/currentuserv2`. This keeps the admin app fully decoupled from the main cookie.

> **The rule:** the separate login is a boundary only because the backend requires a distinct session artifact. The cookie name + claim + `AdminJwtAuthMiddleware` are what make it real — not the separate URL.
> **Why it matters:** a separate URL with the shared cookie would be theatre (bypassable by calling the API directly). Here the admin API rejects the main cookie outright.

### 3.3 The admin app (the "separate entry point")

- One build. The **root `app/layout.tsx` (a server component) reads `process.env.APP_MODE` at request time** and threads `appMode` down to `client-layout.tsx` as a prop. (Runtime env, not `NEXT_PUBLIC_*`, so **one build serves both modes** — no second build, no Host-routing.)
- `APP_MODE=admin`: the public route is the **admin login page** (calls `/api/v1/admin/login/`, on success renders `/admin`); every non-`/admin` path redirects to `/admin`; `AdminGuard` → `AdminLayout` wrap the reused v1 pages.
- `APP_MODE=main` (default): unchanged, except `/admin` is **not served** (redirect to home) and the "Admin Portal" sidebar link is **removed** (D2).
- **No redirect-on-login logic** — the main login does exactly what it does today. A Super Admin simply opens the admin URL.

### 3.4 External-service touchpoints

None (no Airbyte / Prefect / email). DNS/TLS for the new hostname and a second `APP_MODE=admin` process are ops tasks on the existing deployment.

---

## 4. Low-Level Design (LLD)

### 4.1 Data model

**No changes. No migration.** `UserAttributes.is_platform_admin` already exists (`ddpui/models/org_user.py`) and is read-only here. The admin session is entirely a cookie + JWT-claim mechanism.

### 4.2 Backend — the admin session

**Business logic lives in the service, per the admin-portal convention** (`core/admin/admin_service.py:1-11` docstring: handlers parse → call service → convert → return; the service "knows nothing about HTTP"). Cookie-setting is the one HTTP concern that stays in the endpoint.

**`core/admin/admin_service.py`** (logger stays `CustomLogger("ddpui.core.admin")`, `:25`):
```python
# pseudo — returns primitives, no HTTP
def issue_admin_session(username, password) -> tuple[dict | None, str | None]:
    # 1. authenticate credentials (CustomTokenObtainSerializer / Django auth)
    # 2. verify UserAttributes.is_platform_admin is True  → else ("", "not a platform admin")
    # 3. mint token with session="admin" claim + admin lifetimes
    # returns ({"access": ..., "refresh": ...}, None) or (None, error)
```

**`admin_api.py`** (logger stays `CustomLogger("ddpui")`, matching its siblings `auth.py:20` / `user_org_api.py:71` — not the dotted form; the API layer uses bare `"ddpui"`). New endpoints on the existing `admin_router`:

| Route | Auth | Body | Notes |
|---|---|---|---|
| `POST /api/v1/admin/login/` | `auth=None` | `LoginPayload` | Calls `issue_admin_session`; 401 bad creds, **403 non-admin (no cookie)**, else sets `admin_access_token` + `admin_refresh_token`. Typed `response=` schema. |
| `POST /api/v1/admin/logout/` | admin | — | Blacklists + deletes only `admin_*` cookies. Returns `{"success": 1}` (matching the admin neighbor's int form, `admin_api.py:435`). |
| `POST /api/v1/admin/token/refresh` | `auth=None` | — | Reads `admin_refresh_token`; re-sets `admin_access_token`. Mirrors the main v2 refresh. |
| `GET /api/v1/admin/currentuser` | admin | — | `is_platform_admin` + minimal identity via the admin cookie. Typed `response=` schema. |

Router wiring (`admin_api.py:33`): `admin_router = Router(auth=AdminJwtAuthMiddleware())`. Router-level auth overrides `src_api`'s global default (`routes.py:32-38`) for every existing admin route — so the mutating endpoints now require `admin_access_token`. Login/refresh override with `auth=None`. **No separate NinjaAPI instance** (retracted — `public_api` exists for *unauthenticated* endpoints; router-level auth is the conventional, lighter mechanism here).

**`auth.py`** — two touches:
1. **Extract the cookie name** (non-behavioral). `CustomJwtAuthMiddleware.__call__` currently hardcodes `request.COOKIES.get("access_token")` (`:115`). Lift to a class attribute `cookie_name = "access_token"` and reference it. Behavior identical. **Regression-proven** (§6).
2. **`AdminJwtAuthMiddleware(CustomJwtAuthMiddleware)`** — override `cookie_name = "admin_access_token"`, and after decoding assert the token carries `session == "admin"` (else 401). Inherits the existing `authenticate()` → populates `request.orguser` exactly as today, so `@platform_admin_required` works unchanged. Same structural pattern as the base (subclass of `HttpBearer`, same 498/401 handling).
3. **The `session:"admin"` claim** is stamped where the existing custom claim already goes — `CustomTokenObtainSerializer.get_token` (`auth.py:238-271`, which already sets `orguser_role_key` and survives refresh) — via an admin-scoped mint path that also applies the admin lifetimes.

**`settings.py`** — new env vars following the existing `JWT_<what>_EXPIRY_<UNIT>` shape (`:325-327`):

| Var | Default | Matches |
|---|---|---|
| `JWT_ADMIN_ACCESS_TOKEN_EXPIRY_MINUTES` | `15` | `JWT_ACCESS_TOKEN_EXPIRY_MINUTES` (MINUTES) |
| `JWT_ADMIN_REFRESH_TOKEN_EXPIRY_HOURS` | `8` | new unit HOURS (existing refresh is DAYS) — approved deviation, self-documenting for a sub-day lifetime |

Cookie settings (`COOKIE_SECURE`/`COOKIE_SAMESITE`/`COOKIE_HTTPONLY`, `:341-344`) are reused as-is for the admin cookies — **no `domain=` added**, so the admin cookie is host-only on the API host, same as the main cookie.

### 4.3 Backend config (CORS / CSRF)

- `https://insights.dalgo.org` is already in `CORS_ALLOWED_ORIGINS` (`.env.template:9`), `CORS_ALLOW_CREDENTIALS=True`. Verify each environment's deployed value; no code change.
- Confirm whether admin mutations need `CSRF_TRUSTED_ORIGINS` to include the insights origin (§8 Q3). If needed and missed, admin writes fail closed (403), not leak.

### 4.4 Frontend — the admin app

**`app/layout.tsx`** (server component — verify no `"use client"`): read `process.env.APP_MODE` (default `'main'`), pass `appMode` to `client-layout`.

**`components/client-layout.tsx`** (`:24-82`, currently branches on `pathname`): add an `appMode` branch.
- `admin`: unauthenticated → admin login page; authenticated → `AdminGuard` → `AdminLayout`; any non-`/admin` path → redirect `/admin`.
- `main`: today's behavior minus `/admin` (redirect `/admin` → home).

**Admin login page** (new, e.g. `app/admin/login/page.tsx`): `apiPost('/api/v1/admin/login/', {username, password})`; on success render `/admin`; on 403 show "not a platform admin". Reuses the existing login form components.

**`components/admin/AdminGuard.tsx`** (`:33-43`): read `is_platform_admin` from **`/api/v1/admin/currentuser`** (not `/api/currentuserv2`); non-admin bounce → the admin login page (not `/`).

**`components/admin/AdminLayout.tsx`** (`:76-84`): "Back to Dalgo" `href` → `NEXT_PUBLIC_APP_URL`, relabel **"Open Dalgo app"** (D4).

**`components/main-layout.tsx`** (`:230-236`): **remove** the "Admin Portal" nav item (D2). It is no longer conditionally hidden — it is gone; the portal is reached only at the admin URL.

**`lib/api.ts`**: no base-URL change (`:5`); admin auth calls use the same `credentials:'include'` fetch (`:23`).

**Env vars (webapp_v2):**

| Var | Local | Staging | Prod | Drives |
|---|---|---|---|---|
| `APP_MODE` | `main` / `admin` per process | `main` / `admin` per deploy | same | Which app the build serves (runtime, **not** `NEXT_PUBLIC_`). |
| `NEXT_PUBLIC_APP_URL` | `http://localhost:3001` | `https://staging-app.dalgo.org` | `https://app.dalgo.org` | "Open Dalgo app" back-link. |

**`package.json` scripts** (`:8-19`, currently `dev`/`start` hardcode `-p 3001`):
- `dev` / `start` → main app **unchanged on `-p 3001`** (`APP_MODE=main`, the existing default).
- `dev:admin` / `start:admin` → admin app on **`-p 3002`** (`APP_MODE=admin`).
- `E2E_BASE_URL` is **untouched** — the main app stays on 3001, so no CI/test-config churn.

### 4.5 Data flow — a platform admin signs in (the whole slice)

```
Arjun opens insights.dalgo.org  (APP_MODE=admin build)
  → app/layout.tsx reads APP_MODE=admin → client-layout serves the ADMIN LOGIN page
  → Arjun submits credentials → POST /api/v1/admin/login/
       backend: authenticate creds  ✔  AND is_platform_admin=True  ✔
       → Set-Cookie admin_access_token (session=admin, 15 min) + admin_refresh_token (8 h)
       (his main-app access_token, if any, is irrelevant here — different cookie)
  → /api/v1/admin/currentuser (admin cookie) → is_platform_admin:true
  → AdminGuard passes → AdminLayout + reused v1 /admin pages
  → every /api/v1/admin/* call carries admin_access_token → AdminJwtAuthMiddleware admits it
  → Arjun clicks "Open Dalgo app" → app.dalgo.org (still needs its OWN main-app login)
  → Arjun signs out of insights → admin_* cookies cleared; his main-app session (if any) untouched

Denied: Sarah (correct password, not a platform admin) → POST /api/v1/admin/login/ → 403,
        no cookie set. She never reaches /admin. A main-app session would not help her —
        the admin API rejects a bare access_token.
```

---

## 5. Security Review

| Area | Finding / plan |
|---|---|
| **Separate session is server-enforced** | The boundary is the `admin_access_token` cookie + `session:"admin"` claim + `AdminJwtAuthMiddleware`, not the hostname. Every `/api/v1/admin/*` route requires it via router-level auth. This is a real boundary, not topology. |
| **Main cookie replayed at the admin API** | Rejected. `AdminJwtAuthMiddleware` reads only `admin_access_token`; a main `access_token` (even if sent to the API host, which it is) is not read there, and would lack `session:"admin"`. |
| **Forged claim** | Not possible without the signing key. The claim rides inside the signed JWT (same `SIGNING_KEY`); tampering invalidates the signature → 401. |
| **Non-admin at the login screen** | Refused at `POST /api/v1/admin/login/` with 403 **before any cookie is issued** (requirement #3). No admin session ever exists for a non-admin. |
| **Flag revoked mid-session** | `@platform_admin_required` re-reads `UserAttributes.is_platform_admin` from the DB on every admin call (`auth.py:75-76`), so a revoked admin is locked out within one request even with a live admin cookie. |
| **Session isolation on logout** | Distinct cookie names ⇒ admin logout clears only `admin_*`; main logout clears only main cookies. Each blacklists only its own `jti` (requirement #4). |
| **Shorter admin lifetime** | 15 min / 8 h (D5) limits the exposure window on the higher-privilege surface vs the main app's 30 min / 7 days. |
| **The one main-auth touch** | Extracting the cookie-name constant in `CustomJwtAuthMiddleware` is non-behavioral and **regression-proven byte-for-byte** (§6) before merge — same discipline M3/M4 applied before every shared-code touch. |
| **Cookie exposure** | Admin cookie is host-only on the API host (no `domain=`), same as the main cookie. Not widened. |
| **CORS scope** | Only the exact insights origin(s) in `CORS_ALLOWED_ORIGINS`, one per environment; never `*` (incompatible with credentials anyway). |
| **No open redirect** | There is no login redirect. Back-links use fixed env vars, never request-derived values. |
| **Client guards remain UX-only** | `AdminGuard` hides/redirects; real protection is the backend. Kept on the admin app (D2). |
| **Zero-OrgUser platform admin** | An admin with no OrgUser row cannot authenticate to *any* API (inherited, v1 research §6) — the admin login can mint a token but subsequent admin calls 401. Surfaced as §8 Q1. |

---

## 6. Testing Strategy

**Backend — the new admin auth path (full coverage, M1):**
- `issue_admin_session`: valid admin creds → token with `session:"admin"` + admin lifetimes; valid non-admin creds → `(None, error)`, no token; bad creds → error.
- `POST /api/v1/admin/login/`: admin → 200 + `Set-Cookie admin_access_token`/`admin_refresh_token`; **non-admin → 403, no `Set-Cookie`**; bad password → 401.
- `AdminJwtAuthMiddleware`: admin cookie with claim → admits, `request.orguser` populated; **a bare main-app `access_token` (no admin cookie) → 401 on every `/api/v1/admin/*`**; admin cookie without `session:"admin"` → 401; expired admin token → 498.
- `POST /api/v1/admin/logout/`: clears only `admin_*`, blacklists the admin `jti`; a still-valid main session is unaffected.
- `POST /api/v1/admin/token/refresh`: valid `admin_refresh_token` → new `admin_access_token`; main `refresh_token` → rejected.
- Lifetime: admin access expires at 15 min (498 → refresh), admin refresh at 8 h.
- `GET /api/v1/admin/currentuser`: admin cookie → `is_platform_admin:true`; main cookie only → 401.

**Backend — REGRESSION: the main app's auth flow is byte-for-byte unchanged (M1, gating the cookie-name extraction):**
- The existing `ddpui/tests/api_tests/test_user_org_api.py` auth suite (login v1 + v2, logout, refresh, `CustomJwtAuthMiddleware`) runs **green, unchanged**, after the extraction.
- Explicit assertions that the extraction changed nothing observable: `CustomJwtAuthMiddleware.cookie_name == "access_token"`; `POST /api/v2/login/` still sets a cookie **named `access_token`** with the same `HttpOnly`/`Secure`/`SameSite`/`path` attributes as before; the middleware still authenticates a request carrying `access_token` and still 401/498s exactly as before; `POST /api/logout/` still returns `{"success": True}` and deletes `access_token`/`refresh_token`.
- The existing `test_admin_api.py` (403-for-non-admins, `/currentuserv2` surfaces the flag) stays green — the v1 admin routes still gate correctly, now behind the admin middleware.

> Same discipline M3/M4 used before every shared-code touch tonight: prove the untouched path is untouched *in tests*, not by inspection.

**Frontend (Vitest/Jest):**
- `client-layout`: `appMode='admin'` → unauthenticated renders admin login, authenticated renders `AdminGuard`→`AdminLayout`, non-`/admin` path redirects to `/admin`; `appMode='main'` → today's behavior, `/admin` redirects to home.
- `AdminGuard`: reads `/api/v1/admin/currentuser`; non-admin bounce → admin login page.
- `AdminLayout`: back-link href is `NEXT_PUBLIC_APP_URL`, labelled "Open Dalgo app".
- `getNavItems`: the "Admin Portal" item is **absent** for everyone (removed, D2) — update `components/__tests__/getNavItems.test.ts`.
- Admin login page: 403 response renders the "not a platform admin" message; success renders `/admin`.

**Frontend (Playwright):**
- `APP_MODE=admin` process: reaching insights presents the admin login; a non-admin login is refused; after admin login the reused v1 `/admin` flows (create org, invite, change role, remove-with-count) work unchanged.
- `APP_MODE=main` process: no "Admin Portal" sidebar link; `/admin` redirects to home; the main app is otherwise unchanged.
- **Session isolation:** logging into the admin app does not log you into the main app and vice-versa; logging out of one leaves the other signed in.

**Test data:** one platform admin who is also an OrgUser (Arjun in Bhumi); one platform admin with no org (for §8 Q1); one plain org Admin (Sarah) for the negative path.

---

## 7. Milestones

Each milestone is independently shippable and reviewable as one PR. Backend session first (testable with no user-visible change), then the admin app, then removal of the main-app entry, then ops cutover.

#### Milestone 1: Backend — the independent admin session
- **Deliverable:** a real, server-enforced admin session, with the main app's auth flow proven unchanged.
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Extract `cookie_name` in `CustomJwtAuthMiddleware` (non-behavioral).
  - [ ] Add the byte-for-byte main-auth **regression test** (§6) — gates the extraction.
  - [ ] `AdminJwtAuthMiddleware` (subclass; `admin_access_token` + `session:"admin"` claim).
  - [ ] Admin-scoped mint (`session:"admin"` claim + admin lifetimes); `JWT_ADMIN_*` env vars in `settings.py`.
  - [ ] `admin_service.issue_admin_session()` (creds + `is_platform_admin` + mint).
  - [ ] Admin endpoints on `admin_router`: login (`auth=None`), logout, `token/refresh` (`auth=None`), `currentuser`; set `admin_router = Router(auth=AdminJwtAuthMiddleware())`.
  - [ ] Full admin-auth test coverage (§6); verify CORS/CSRF per environment (§8 Q3).
  - [ ] Confirm §8 Q1 (do all platform admins have ≥1 OrgUser?).
- **Acceptance:** admin login issues `admin_access_token` and is refused for non-admins (403, no cookie); every `/api/v1/admin/*` rejects a bare main-app cookie; the full main-app auth suite passes **unchanged**.

#### Milestone 2: Frontend — the admin app entry point
- **Deliverable:** `insights.dalgo.org` (and `localhost:3002`) is a separate app with its own login, reusing the v1 `/admin` pages.
- **Services:** webapp_v2
- **Key tasks:**
  - [ ] Root `app/layout.tsx` reads `APP_MODE` → `appMode` prop (verify it is a server component).
  - [ ] `client-layout` `appMode` branch; admin login page; admin-mode routing.
  - [ ] `AdminGuard` → `/api/v1/admin/currentuser`, bounce → admin login; `AdminLayout` back-link → `NEXT_PUBLIC_APP_URL` ("Open Dalgo app").
  - [ ] Add `dev:admin`/`start:admin` scripts (admin :3002, `APP_MODE=admin`); `dev`/`start` (main :3001) and `E2E_BASE_URL` unchanged; `APP_MODE`/`NEXT_PUBLIC_APP_URL` in `.env.example`.
  - [ ] Vitest + Playwright per §6, including session isolation.
- **Acceptance:** on staging, `insights.staging.dalgo.org` presents the admin login; a non-admin is refused; an admin lands on `/admin` and the v1 flows work; the admin and main sessions are independent.

#### Milestone 3: Remove the in-app entry (D2)
- **Deliverable:** the main app no longer advertises or serves the portal.
- **Services:** webapp_v2
- **Key tasks:**
  - [ ] Remove the "Admin Portal" nav item (`main-layout.tsx:230-236`); update `getNavItems.test.ts`.
  - [ ] `APP_MODE=main` no longer serves `/admin` (redirect to home).
- **Acceptance:** on staging the main-app sidebar has no "Admin Portal" link; `/admin` on the main app redirects to home; from the admin app, "Open Dalgo app" returns a dual-role admin to the main app (where they authenticate separately).

#### Milestone 4: Ops — DNS/TLS + admin deployment
- **Deliverable:** `insights.dalgo.org` serves the `APP_MODE=admin` build in staging then prod.
- **Services:** Infra / DNS / TLS
- **Key tasks:**
  - [ ] `insights.<env>.dalgo.org` DNS + cert (§8 Q4).
  - [ ] A deployment/process running `APP_MODE=admin`; confirm the insights origin in each environment's `CORS_ALLOWED_ORIGINS` (+ `CSRF_TRUSTED_ORIGINS` if §8 Q3).
  - [ ] Staging validation before prod cutover.

> **Deferred / not in this slice:** anything the portal *does* (still v1); step-up re-auth or 2FA on the admin login (the separate session is the boundary here); shared SSO between the two apps.

---

## 8. Open Questions & Risks

**Open questions:**

| # | Question | Affects | Default if unanswered |
|---|---|---|---|
| Q1 | **Do all platform admins have ≥1 OrgUser row?** A zero-org admin can mint an admin token but then 401s on every admin call (inherited, v1 research §6). | M1/M2 | Assume yes; add a fast-follow to tolerate no-org platform admins if any exist. |
| Q3 | **Do any admin mutations rely on Django CSRF?** If so, `CSRF_TRUSTED_ORIGINS` must include the insights origin. | M1/M4 | Add the insights origin defensively. |
| Q4 | **Exact hostnames** for staging/prod (`insights.staging.dalgo.org` vs `staging-insights.dalgo.org`)? Drives env, DNS, cert. | M4 | `insights.<env>.dalgo.org`; confirm with ops. |

> **Resolved:** Q6 (how the second login is enforced) — **answered** by §3.2/§4.2: a distinct `admin_access_token` cookie carrying a `session:"admin"` claim, required by `AdminJwtAuthMiddleware` via router-level auth on `admin_router`, with `is_platform_admin` verified at login. This is the mechanism the earlier draft left open.

**Risks:**

| Risk | Mitigation |
|---|---|
| **The cookie-name extraction changes main-app auth behavior.** | Byte-for-byte regression test gates the change (§6); the extraction is a constant lift, no logic change. |
| **`APP_MODE` not readable client-side** (if `app/layout.tsx` were a client component or the value weren't threaded). | Read it in the **server** root layout and pass a prop; add a test that `appMode` reaches `client-layout`; verify no `"use client"` at the root. |
| **Admin session mistaken for "just a login screen"** over the shared cookie (the theatre trap the earlier draft warned about). | Enforcement is `AdminJwtAuthMiddleware` + claim, tested by "bare main cookie → 401 on every admin route". The URL is not the boundary. |
| **Zero-OrgUser platform admin** locked out after login. | §8 Q1; fast-follow if any exist. |
| **Someone relaxes `@platform_admin_required`** thinking the domain/session split replaces it. | It does not — it is still the DB-backed wall and is re-checked per request. Stated in §5. |
| **CSRF trips admin writes** from the insights origin. | §8 Q3; add `CSRF_TRUSTED_ORIGINS` defensively; fails closed (403), not a leak. |

---

## Next

Draft v2 of the enhancement plan. Review and tell me what to revise. When ready, run `/engineering/execute-plan features/admin-portal/v1.1/plan.md` to implement (M1 first — backend session with the main-auth regression proof).
