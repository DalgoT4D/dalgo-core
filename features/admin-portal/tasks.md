# Admin Portal — Execution Tasks

**Plan:** `features/admin-portal/plan.md` · **Spec:** `features/admin-portal/spec.md`
**Started:** 2026-07-22 · **Last updated:** 2026-07-26
**Branch (both repos):** `feature/admin-portal-m4-users` — carries the shipped portal; **not yet in `main`, not yet pushed**.

> **Why this file was rewritten.** Its previous version tracked a Milestone 1 built around an **independent admin session** — a second login cookie for the portal. That session was built (backend `aa81d3a`, `c53ad124`, `aaedf594`, `2530c3f`; frontend `dccc3ee`, `3e9d995`, `9618d37` — all real commits, still in history) and then **deliberately removed** on 2026-07-26. Those commits are now history, not current state, so the checklist described a system that no longer exists. Everything below reflects what is actually in the code.

**Acronyms:** DRF (Django REST Framework) · JWT (the signed login token) · CI (continuous integration).

---

## Environment

| Thing | Where |
|---|---|
| Dev database | Postgres `dalgo` @ `localhost:5433` (container `dalgo-postgres`), 189 migrations applied |
| Redis | `localhost:6379` (container `dalgo-redis`) |
| Backend | `http://localhost:8002` |
| Frontend | `http://localhost:3001` (`next dev --turbopack -p 3001`) |
| Admin sign-in | `http://localhost:3001/admin/login` |

**Dev test accounts** — local database rows only. No fixture, no migration, nothing committed to any repo.

| Email | Password | Platform admin? | Org / role |
|---|---|---|---|
| `test-admin@dalgo.test` | `TestAdmin@123` | Yes | `admin-dev` / super-admin |
| `test-user@dalgo.test` | `TestUser@123` | No | `test` / member |

Remove with `User.objects.filter(email__in=[...]).delete()` — that cascades their `OrgUser` and `UserAttributes` rows.

---

## Milestone 1 — Admin access model ✅ SHIPPED 2026-07-26

**What shipped:** an admin sign-in screen and a sign-out control over the **shared** product session, with `@platform_admin_required` on every admin route as the enforced boundary. Not an independent session — see `plan.md` §3.2 for why that was reversed.

### Backend — DDP_backend

- [x] **`869af4af`** — convention and duplication cleanup
  - [x] Deleted `AdminInviteUserSchema` (field-identical to `NewInvitationSchema`) and `AdminLoginSchema` (field-identical to `LoginPayload`); the endpoints now take the existing schemas
  - [x] Added `AdminInvitationSchema.from_model()`, collapsing two duplicated inline mappings
  - [x] `create_org()` takes the schema the API validated; the payload widening moved into the service
  - [x] Added `admin_service.invite_user` / `change_orguser_role` / `remove_orguser` so the API no longer calls `orguserfunctions` directly
  - [x] `response=` typing on four untyped routes; `_get_org_or_404` moved above its first call site
- [x] **`eca9865f`** — removed the independent session, added the error-mapping fix
  - [x] Deleted `AdminJwtAuthMiddleware`, the `admin_access_token` / `admin_refresh_token` cookies, `issue_admin_session`, `refresh_admin_session`, the admin `login` / `logout` / `token/refresh` routes, three session exception classes, and both `JWT_ADMIN_*` settings
  - [x] `admin_router = Router()` — inherits the API-wide middleware, matching all 24 sibling routers
  - [x] Kept `GET /admin/currentuser`, gated by `@platform_admin_required` only
  - [x] Added `drf_authentication_failed_handler` in `routes.py`: a wrong password now returns **401** instead of the **500** it used to. This fixes the normal product login too, not only the admin one.

### Frontend — webapp_v2

- [x] **`d1227c0`** — sign in through the shared login
  - [x] `/admin/login` posts to `POST /api/v2/login/`, reads `is_platform_admin` from the response, and refuses a non-admin locally without navigating
  - [x] Removed `adminAwareRefreshEndpoint`; **kept** `adminAwareLoginPath`, so an admin 401 still lands on `/admin/login` rather than the product login
  - [x] Corrected the now-wrong docstrings in `AdminGuard`, `useAdminSession`, and `client-layout`
- [x] **`968435a`** — sign out
  - [x] "Log out" row in the `AdminLayout` sidebar footer, beside "Back to Dalgo"
  - [x] Full shared logout, reusing `POST /api/logout/`, `useAuthStore().logout()`, `ANALYTICS_EVENTS.USER_LOGGED_OUT`, and the `header.tsx:99-111` handler shape — no new logout logic
  - [x] Redirect uses an explicit `router.replace('/admin/login')`, **not** the reactive `isAuthenticated` pattern from `header.tsx`: nothing sets `isAuthenticated` true inside the portal, so that pattern would have bounced a signed-in admin out on mount

### Tests

| Suite | Result |
|---|---|
| Backend admin (`test_admin_api.py` + `test_admin_service.py`) | 40 tests |
| `test_auth.py` | 11 — 9 existing plus 2 ported from the deleted `test_admin_auth.py` |
| Backend full unit suite (less `integration_tests`) | 2233 passed, 2 skipped |
| `test_user_org_api.py` | 69 passed, **unmodified** — proves the shared login and invite paths are unharmed |
| Frontend admin scope | 113 passed across 13 suites |
| Frontend full suite (`--maxWorkers=2`) | 1337 passed, 4 skipped |

> **Why the two ported tests matter.** Deleting `test_admin_auth.py` would have removed the only coverage of `CustomJwtAuthMiddleware.__call__` — the cookie path that maps a malformed token to 401 and an expired one to 498. `test_auth.py` had none, and that code runs on every authenticated request. Both tests were moved there and retargeted at the normal `access_token`.

**Deployment note.** `eca9865f` (backend) and `d1227c0` (frontend) are a **breaking pair**: the backend deletes the admin login/logout/refresh routes and the frontend is what stops calling them. They must ship together. `968435a` depends on `d1227c0`, so it cannot go first either.

---

## Milestone 2 — Broadcast notifications ⬜ NOT STARTED

Per `plan.md` §7. Additive `scope` + `target_org` migration on `Notification`; admin routes built on the existing service functions (count-only preview, server-derived author, cancel, history, read counts); composer and history screens; un-disable the nav item.

## Milestone 3 — Per-org feature flags ⬜ NOT STARTED

Per `plan.md` §7. Catalog / per-org read / set / clear endpoints; a small `clear_org_flag` helper; a per-org Flags tab plus a portal-wide matrix; un-disable the nav item.

## Milestone 4 — Airbyte & pipeline read-only view ⬜ NOT STARTED

Per `plan.md` §7. The safety work is the point: `cleanup=False` so listing connections dispatches no deletions, a warehouse-deref guard, org-ownership resolution before any bare-id log fetch, and no polling.

---

## Known issues found while building Milestone 1 — not fixed

Each was found in passing and deliberately left alone. Each deserves its own ticket.

| # | Issue | Evidence |
|---|---|---|
| 1 | **Backend `reports/` tests are order-dependent flakes.** `TestGetThreadContext` and `TestFetchComments` fail with a *different set of names* on each run. | Three runs produced three different failing sets. The `reports/` directory passes 173/173 in isolation on this branch but fails 3 at HEAD. Both paths sort on `created_at` with no tiebreaker (`mention_service.py:222`, `comment_service.py:63`), so comments created in the same tick tie and the database returns them in arbitrary order. |
| 2 | **Frontend suite times out under default parallelism.** | Two consecutive runs on an identical tree gave 19 then 11 failures across different charts / dashboard / connectors / pipeline / transform suites. Those suites pass in isolation (51 tests, 9s) while taking 28–62s each under load. `--maxWorkers=2` returns the true baseline. Likely to bite CI. |
| 3 | **Stale migration bytecode after the renumber in `5222d791`.** | Anyone still holding `0161_org_is_active.py`, `0162_orguser_is_active.py`, or `0163_invitation_invited_in_org.py` (renumbered to `0169`–`0171`) will hit a duplicate-column error on `migrate`. Delete the stale files and their `__pycache__/*.pyc`. |
| 4 | **A platform admin belonging to no org cannot use the portal.** | `CustomJwtAuthMiddleware` loads `request.orguser` and `@platform_admin_required` reads it. Pre-existing and unchanged by this work — see `plan.md` §8 Q5. Untested and unfixed; we assume every platform admin belongs to at least one org. |
| 5 | **`is_platform_admin` now has three frontend read paths** — the Zustand store (normal sidebar), the `/admin/currentuser` SWR call (AdminGuard), and the `/api/v2/login/` response body (sign-in screen). | All three read the same server-side flag, and the server re-checks it per request, so a disagreement is a stale-UI bug rather than an access hole. Worth consolidating. |
| 6 | **`git stash` is unsafe in `webapp_v2` while the dev server is running.** | It fails partway on locked `.swc/plugins` and `components/__tests__/`, leaving a stash entry and an aborted `pop`. Hit once here; recovered by checking the working tree, confirming the stash was byte-identical to it, then dropping it. |

---

## Held for a frontend dependency check

From the backend duplication audit. Deliberately **not** applied, because each changes a wire contract `webapp_v2` reads:

- Renaming `AdminInvitationSchema.invited_role_slug` to the established `invited_new_role_slug`
- Renaming `RemovalImpactSchema` → `AdminRemovalImpactSchema` for module consistency
- The `id=0` stub invitation returned when an invitee already has a platform account — a client cannot currently tell "invited" from "added directly" except by that undocumented sentinel

---

## Log

- **2026-07-22** — setup; branch `feature/admin-portal-m4-users`; environment verified; independent-session Milestone 1 built (backend `aa81d3a`…`2530c3f`, frontend `dccc3ee`…`9618d37`).
- **2026-07-26** — duplication/convention audit → `869af4af`. Independent session reversed → `eca9865f` (backend), `d1227c0` (frontend). Sidebar sign-out added → `968435a`. Spec, plan, research, and this file updated to match.
