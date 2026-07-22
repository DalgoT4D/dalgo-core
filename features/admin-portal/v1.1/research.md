# Research — Admin Portal v1.1 (Domain-based entry: insights.dalgo.org)

**Date:** 2026-07-21 · **Owner:** Veekshitha Nelluru (DMP 2026) · Issue #1254
**Parent:** `features/admin-portal/v1/research.md`

> v1 is built and merged. This slice moves the portal's front door to its own hostname. The whole question is auth and routing, so that is what this file covers.

---

## 1. What v1 already provides

`/admin` pages, `AdminGuard`, `AdminLayout`, sidebar link, `@platform_admin_required`, `/api/v1/admin/*`, and `is_platform_admin` on both the login response and `/currentuserv2`. Nothing here needs rebuilding.

---

## 2. Current routing

`middleware.ts` matches only `/share/dashboard/:path*` and `/share/report/:path*` — neither `/` nor `/admin/*`. Host-header branching is net-new; the matcher must widen.

---

## 3. Where the session actually lives ← the load-bearing finding

`POST /api/v2/login/` sets both cookies **without `domain=`** (`ddpui/api/user_org_api.py:617-634`):

```python
response.set_cookie("access_token",  token_data["access"],  ..., path="/")   # no domain=
response.set_cookie("refresh_token", token_data["refresh"], ..., path="/")   # no domain=
```

A cookie set with no `domain=` is **host-only**, bound to the host that set it — **the backend/API host**. It is *not* on `app.dalgo.org` and *not* on `insights.dalgo.org`. Frontends never hold it. They call the API with `credentials: 'include'` (`webapp_v2/lib/api.ts:23`) and the browser attaches it based on the API host.

---

## 4. Does insights.dalgo.org share the session today? — **Yes, automatically**

### 4.1 SameSite

`COOKIE_SAMESITE = "Lax" if ENVIRONMENT == "production" else "None"` (`settings.py:343`), `COOKIE_SECURE = True` (`:342`).

SameSite is evaluated on the **registrable domain** (eTLD+1). `insights.dalgo.org` → `api.dalgo.org` are both under `dalgo.org` ⇒ **same-site**.

| Environment | SameSite | Cookie sent from insights? |
|---|---|---|
| production | `Lax` | ✅ same-site request |
| staging / non-prod | `None` + `Secure` | ✅ sent even cross-site |

### 4.2 CORS — already configured

`https://insights.dalgo.org` is already in `CORS_ALLOWED_ORIGINS` (`DDP_backend/.env.template:9`), with `CORS_ALLOW_CREDENTIALS = True` and `CORS_ALLOW_ALL_ORIGINS = False` (`settings.py:72-81`).

> **Conclusion:** a Super Admin already logged into the main app who visits `insights.dalgo.org/admin` is **authenticated silently**, in every environment. No second login occurs. The original D3 described this accurately.

### 4.3 Why "scope the cookie to app.dalgo.org" is not available

The lever assumes a frontend-scoped cookie. There isn't one — the session is a host-only cookie on the **API** host, shared by every allowed frontend origin. Narrowing frontend scope is not a thing that can be done, because the frontends never held it.

Forcing a real second login therefore needs a **distinct session artifact**:

| Option | Shape | Note |
|---|---|---|
| Separate admin cookie | Admin-login endpoint issues e.g. `admin_access_token`; `@platform_admin_required` requires it | Clearest boundary; most work |
| Step-up re-auth | Password re-entry at insights mints a short-lived admin-audience token | Good if the app session should still count for identity |
| Cookie `path=` partitioning | Scope to `/api/v1/admin` | **Not recommended** — `/currentuserv2`, needed by AuthGuard *and* AdminGuard, falls outside the path |

> **The rule:** a login screen that does not change what the backend accepts is not an access boundary.
> **Why it matters:** a frontend-only form leaves the user authenticated to the API throughout and is bypassable by calling it directly — friction without protection.

---

## 5. Front-end lines this slice touches

`app/login/page.tsx:63` · `app/page.tsx:9-12` · `components/admin/AdminLayout.tsx:77` (`/` back-link) · `components/admin/AdminGuard.tsx:40-43` (`router.replace('/')` bounce) · `components/main-layout.tsx:230-236` (sidebar item) · `middleware.ts` matcher.

---

## 6. Inherited from v1, still true

A platform admin with **zero** OrgUser rows cannot use the API at all — `CustomJwtAuthMiddleware` 401s (`ddpui/auth.py:160-164, 235`). Every Super Admin must be a member of ≥1 active org. Relevant to plan §8 Q1.
