# Platform Admin Portal v1 — Implementation Plan (Draft v1)

**Spec:** `features/admin-portal/v1/spec.md` (full vision: `features/admin-portal/spec.md`)
**Research:** `features/admin-portal/v1/research.md`
**Date:** 2026-07-02
**Status:** Draft — for engineering review.

> Acronyms: HLD (high-level design) · LLD (low-level design) · JWT (JSON Web Token — the signed login token) · FK (foreign key) · RBAC (role-based access control) · PII (personally identifiable information) · PR (pull request).

---

## 1. Overview

A **Dalgo-staff, cross-org portal** to run the platform: see every org's health, manage any org's users, create/suspend/reactivate/archive orgs, all held by a small fixed group of platform admins, with every action logged.

**Services affected:**

| Service | Role in this feature |
|---|---|
| **DDP_backend** (Django + Ninja) | The bulk — new cross-org API, org status, audit log, suspend cascade. |
| **webapp_v2** (Next.js) | The `/platform` portal UI, gated to platform admins. |
| **prefect-proxy** (FastAPI) | Pause/resume an org's Prefect deployments on suspend/reactivate. |

---

## 2. Blast Radius

**Primary entities changed:** `Organization` (new `status` — active/suspended/archived), `OrgUser` (cross-org management, reusing existing flows). **New:** a platform-admin enforcement tier and a `PlatformAuditLog`.

The load-bearing insight from the domain map: an org has activity that could continue past a login block. But a code read (research §5) **corrected two assumptions** — the cron-Alert and scheduled-report features I worried about **do not exist yet**. The one real no-login exposure is **public share links**.

> ⚠️ **Planner default — confirm on review.** The user stepped away during the blast-radius questions. Suspend cascade is set to **in-scope** as the safe default.

| Surface | Hop | Why affected | Status | Notes |
|---|---|---|---|---|
| **Pipeline** | 1 | Suspend pauses the org's Prefect deployments (active step) | **in-scope** | Spec states pipelines pause. prefect-proxy touch. Loop `OrgDataFlowv1` → `set_deployment_schedule("inactive")`. |
| **Share link** (Dashboard + Report public) | 1–2 | Public tokens serve NGO data with **no login** — the real exposure vector | **in-scope** ⚠️ | Suspended/archived org's public links return "unavailable". Gate in `public_api.py`. |
| **OrgUser** | 1 | Cross-org role change / remove / invite | **in-scope (reused)** | Reuses `orguserfunctions.py`; no new per-org behavior. |
| **Alert (pipeline-failure notification)** | 1 | Prefect-failure webhook notifies on run failure | **unaffected (moot)** | The `features/alerts` cron feature is **not shipped**. Real notifications fire only on a pipeline run — and suspend pauses pipelines, so none run. Defensive gate at `webhook_functions.py:213` only. |
| **Report email** | 1 | On-demand send only — **no scheduler exists** | **unaffected (moot)** | Sending requires a logged-in user, which suspend blocks. Defensive gate at `report_tasks.py` task entry. |
| **Notification** | 2 | Pipeline paused → fewer run notifications | **unaffected (indirect)** | Downstream of paused pipelines; no change to Notification itself. |
| **Dashboard / Chart / Metric / KPI** (content) | 1–2 | Owned by OrgUsers whose roles the portal can change | **unaffected** | Portal never renders NGO content (no impersonation in v1). Role/remove reuse existing per-org handling. |
| **Warehouse** | 1 | Org-scoped, but suspend doesn't touch warehouse data | **unaffected** | Data retained on suspend/archive; never queried by the portal. |
| **Explore / Data Quality** | 1 | Org-scoped surfaces | **unaffected** | Not rendered in the portal; no cross-org exposure. |

**Not listed = not affected.** Source, Transform, and the analytics builders are internal to an org and are neither rendered nor mutated by the portal.

---

## 3. High-Level Design (HLD)

### 3.1 The core decision — a separate cross-org authorization path

**The rule:** The portal does not use the normal `x-dalgo-org`-scoped request path. It uses a new `platform` API router whose auth checks the `is_platform_admin` flag on the logged-in user and takes the target org as an explicit parameter.
**Example:** Meera calls `GET /api/platform/orgs`. There's no `x-dalgo-org` header — the endpoint returns *all* orgs because Meera's `is_platform_admin` is true. To act on Akshara she calls `POST /api/platform/orgs/akshara/users/{id}/resend`, passing the org in the path.
**Why it matters:** It keeps cross-org power in one isolated, auditable place, instead of bolting a bypass onto the single-org middleware that guards every NGO's data.

```
Dalgo staff browser
   │  JWT (same login as everyone)
   ▼
/api/platform/*   ──►  PlatformAdminAuth
                         │  is_platform_admin == True ?  ── no ──► 403
                         │  (superadmin routes also need is_superuser)
                         ▼ yes
                       endpoint(org_slug in path) ──► service fn ──► PlatformAuditLog write
```

### 3.2 Two gates, both already present

| Gate | Backed by | Guards |
|---|---|---|
| **Platform admin** | `UserAttributes.is_platform_admin` (exists) | the whole `/api/platform` router |
| **Superadmin** | Django `User.is_superuser` (exists, unused today) | Platform Staff add/remove only |

No new role or flag is invented — both already exist in the codebase (research §2).

### 3.3 Suspend cascade — gate at execution, pause at action

**The rule:** Suspending sets `Org.status = suspended`. Three points do the real work — login block, an active Prefect pause, and a public-share gate. Two more are cheap defensive no-ops.

```
suspend(org)
  ├─ Org.status = suspended
  └─ pause all OrgDataFlowv1 deployments   (prefect-proxy)   ← active step

execution points then check status:
  login/token       → reject if suspended            (umbrella)
  public share view → "unavailable" if suspended     ← the real no-login exposure
  pipeline webhook  → skip notify   (moot: no run happens while paused — defensive)
  report send task  → skip send     (moot: needs login — defensive)
```

**Why only these:** research §5 found no cron-Alert feature and no scheduled-report feature exist. The only thing that serves NGO data without a login is a **public share link**, so that gate is the one that matters; the rest follow from "no login + no pipeline runs."

**Reactivate** reverses: `status = active`, resume deployments. **Archive** = the suspend cascade + excluded from the active directory list; data retained and recoverable.

### 3.4 New / changed endpoints (all under `/api/platform`)

| Method + path | Does | Gate |
|---|---|---|
| `GET /orgs` | Directory: all orgs + health signals | platform admin |
| `GET /orgs/{slug}` | Org detail (metadata + health, no NGO content) | platform admin |
| `POST /orgs` | Create org shell + invite first Admin | platform admin |
| `POST /orgs/{slug}/status` | Suspend / reactivate / archive | platform admin |
| `GET /orgs/{slug}/users` | List the org's users | platform admin |
| `POST /orgs/{slug}/users` | Add user with a role | platform admin |
| `POST /orgs/{slug}/users/{id}/role` | Change role (within org's role model) | platform admin |
| `POST /orgs/{slug}/users/{id}/resend` | Resend invite | platform admin |
| `DELETE /orgs/{slug}/users/{id}` | Remove user | platform admin |
| `GET /staff` · `POST /staff` · `DELETE /staff/{id}` | List / add / remove platform admins | **superadmin** |
| `GET /audit-log` | Filterable action log | platform admin |

### 3.5 External services

- **prefect-proxy** — the only external touch: pause/resume an org's deployments on suspend/reactivate. Reuses Dalgo's existing proxy client (research §5).
- **Airbyte / dbt / warehouse** — untouched in v1. Create-org does **not** provision a warehouse (deferred); suspend does not delete warehouse data.

---

## 4. Low-Level Design (LLD)

### 4.1 Data model

**`Org` (modify — `DDP_backend/ddpui/models/org.py:123`)**

```python
class OrgStatus(models.TextChoices):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"

# new fields on Org
status = models.CharField(max_length=20, choices=OrgStatus.choices, default=OrgStatus.ACTIVE)
status_changed_at = models.DateTimeField(null=True, blank=True)
status_reason = models.TextField(null=True, blank=True)
```

Migration: add fields + **backfill every existing org to `active`** (data migration). Do not overload the existing `OrgType` enum (that's plan type — research §3).

**`PlatformAuditLog` (new model)**

```python
class PlatformAuditLog(models.Model):
    actor = models.ForeignKey(User, on_delete=models.PROTECT)      # the Dalgo staff member
    action = models.CharField(max_length=64)                        # e.g. "org.suspend", "user.resend_invite"
    target_org = models.ForeignKey(Org, null=True, on_delete=models.SET_NULL)
    target_email = models.CharField(max_length=254, null=True)      # user target (email, survives deletion)
    metadata = models.JSONField(default=dict)                       # before/after, reason, etc.
    created_at = models.DateTimeField(auto_now_add=True)
```

Append-only: no update/delete API. `on_delete=SET_NULL` on org so the log survives an archived/deleted org.

**Platform admin / superadmin:** no new model — `UserAttributes.is_platform_admin` (exists) + `User.is_superuser` (exists).

### 4.2 API design

- New module `DDP_backend/ddpui/api/platform_api.py` with its own `Router`, mirroring the existing Ninja pattern in `ddpui/api/user_org_api.py`.
- **`PlatformAdminAuth`** — a Django-Ninja auth class (subclass the existing JWT auth used in `auth.py`) that, after authenticating the user, asserts `UserAttributes.objects.get(user=...).is_platform_admin`. Fails closed → 403. A `require_superuser` dependency adds the `is_superuser` check for `/staff` routes.
- **Request/response schemas** — Pydantic schemas in `platform_api.py`: `OrgDirectoryRow`, `OrgDetail`, `CreateOrgRequest {name, plan_tier, first_admin_email}`, `OrgStatusRequest {action: suspend|reactivate|archive, reason}`, `AuditLogRow`. Validate email fields; validate `action` against an enum; reject unknown org slug with 404.
- **Error codes:** 401 (not logged in), 403 (not platform admin / not superuser), 404 (org/user not found), 409 (create-org name taken; illegal status transition e.g. reactivate an active org), 422 (bad payload).

### 4.3 Backend logic

| Concern | Approach | Reuse |
|---|---|---|
| Directory + health | `Org.objects.all()` annotated with user count, warehouse type (`OrgWarehouse`), last run + fail state (from `OrgDataFlowv1` / flow-run records) | new aggregation query |
| User actions | Build org context from path slug, call existing service fns | **`ddpui/core/orguserfunctions.py`** (invite/resend/delete/role) |
| Create org | Wrap the logic behind the `createorganduser` command + `POST /v1/organizations/` | existing org-create + invite |
| Status change | Set status, write timestamp/reason, pause/resume deployments, write audit log | new `platform_service.py` |
| Suspend cascade gates | Add `org.status == active` checks at the 5 execution points (research §5) | see §4.5 |
| Audit log | One helper `record_platform_action(actor, action, org, target_email, metadata)` called by every write endpoint | new |

### 4.4 Frontend components

- New route group `webapp_v2/app/platform/`:
  - `platform/orgs/page.tsx` — directory table (sort/filter by status).
  - `platform/orgs/[slug]/page.tsx` — detail: Users tab + health panel + lifecycle menu.
  - `platform/staff/page.tsx` — superadmin only.
  - `platform/audit-log/page.tsx` — filterable log.
- **Reuse** `components/settings/user-management/*` (tables, `InviteUserDialog`, `DeleteUserDialog`) and `components/settings/organizations/CreateOrgDialog.tsx`, parameterized by org slug.
- **New** `components/platform/` for the directory, health panel, lifecycle menu, and typed-name destructive confirm dialog.
- **Route guard:** a `platform/layout.tsx` that checks `is_platform_admin` from the auth store and renders "not found" otherwise. The portal never appears in `main-layout.tsx` sidebar for NGO users.
- **API hooks:** `hooks/api/usePlatform.ts` calling `/api/platform/*` (no `x-dalgo-org` header on these calls).

### 4.5 Integration points (suspend cascade)

Each gets an `org.status == active` guard (exact refs from research §5):

```
1. Login/token (primary) ── ddpui/auth.py:147 (CustomJwtAuthMiddleware) ── reject suspended
   Login/token (legacy)  ── ddpui/auth.py:69  (CustomAuthMiddleware)
2. Public share (real)   ── public_api.py:1049 (report resolver) + per-endpoint dashboard
                            gates (:94,:144,:197,:381,:463,:476,:568,:621,:895,:958)
                            → add a shared dashboard-token helper; "unavailable" if suspended
3. Prefect pause (active) ── loop OrgDataFlowv1.filter(org, dataflow_type="orchestrate")
                            → prefect_service.set_deployment_schedule(deployment_id,"inactive")
                            (pattern: management/commands/refresh_deployment_schedule.py:19-46)
4. Webhook notify (defensive) ── webhook_functions.py:213  ── skip if org suspended
5. Report send (defensive)    ── report_tasks.py task entry ── skip if org suspended
```

**No "pause all schedules" helper exists** — the loop over `OrgDataFlowv1` is net-new code (small).

---

## 5. Security Review

**The portal is the highest-privilege surface in Dalgo — cross-tenant by design. Security is the feature, not an add-on.**

| Concern | Assessment |
|---|---|
| **AuthN / AuthZ** | Every `/api/platform` route uses `PlatformAdminAuth` (checks `is_platform_admin`). `/staff` routes additionally require `is_superuser`. Fails closed. UI hiding is secondary — the server refuses. |
| **The `x-dalgo-org` bypass** | Platform endpoints intentionally step outside single-org scoping. Risk: a regression that exposes this path to non-platform-admins. Mitigation: one shared auth class, unit-tested to 403 a normal OrgUser; no per-endpoint ad-hoc checks. |
| **Input validation** | Pydantic schemas validate every payload. Org slug → 404 if unknown. Role changes validated against the org's role model. Emails validated. Status action validated against an enum + legal-transition check. |
| **Data access control** | v1 exposes **metadata and user records only** — never warehouse rows or rendered dashboards (no impersonation). Endpoints must not join through to NGO content. |
| **Sensitive data / PII** | User emails are PII and appear in the directory, user tabs, and audit log. No new storage of credentials/tokens. Audit log stores emails (not passwords). |
| **Injection** | No raw SQL — ORM annotations only for the directory. No user input reaches a query string. |
| **External calls** | prefect-proxy calls reuse the existing authenticated proxy client; no new secrets. Responses validated before use. |
| **Abuse / rate limiting** | Audience is ~5 staff, so abuse risk is low, but destructive actions (suspend/archive) require a typed org-name confirmation client-side **and** are recorded in the audit log server-side. Consider a light rate limit on create-org. |
| **Accountability** | Every write action writes a `PlatformAuditLog` row (append-only). This is the primary control against insider misuse. |

---

## 6. Testing Strategy

**Unit (pytest — DDP_backend)**
- `PlatformAdminAuth`: a normal OrgUser → 403; a platform admin → 200; a platform admin on `/staff` without `is_superuser` → 403.
- `Org.status` migration: every pre-existing org backfills to `active`.
- Each cascade gate: suspended org → login rejected; every public dashboard + report share endpoint → "unavailable"; defensive webhook/report-send gates no-op. (Assert the shared `resolve_public_dashboard` helper is used by all public dashboard endpoints so none is missed.)
- Status transitions: reactivate-an-active-org → 409; archive keeps data.
- Audit log: every write endpoint records exactly one row with actor/action/target.
- User actions reuse `orguserfunctions` and behave identically to the per-org path.

**Integration / cross-service**
- Suspend Akshara → assert (a) its users get 401 on login, (b) its Prefect deployments are paused via the proxy, (c) a public share token for it returns unavailable.
- Reactivate → deployments resume, login works.

**Frontend (Vitest + Playwright)**
- Vitest: `platform/layout` guard renders "not found" when `is_platform_admin` is false.
- Playwright E2E: an NGO user (Priya) cannot reach `/platform` (server 403 + no nav entry); a platform admin (Meera) sees the directory and resolves a user; typed-name confirm blocks suspend until the name matches.

**Edge cases**
- Create-org with a duplicate name → 409.
- Removing a user who owns content (existing per-org orphaning behavior applies — unchanged).
- Suspending an org that has no pipelines / no warehouse (no crash).
- Platform admin suspends an org they themselves belong to as an OrgUser → they must not lock *themselves* out of the portal (portal access is by `is_platform_admin`, not org membership — verify).

**Test data:** ≥2 orgs (one with pipelines + a public share + an alert, one bare), a platform-admin user, a superuser, and a normal OrgUser.

---

## 7. Milestones

Each milestone is independently shippable and PR-sized. The audit-log model lands in M1 so every later action writes to it.

#### Milestone 1: Platform foundation + security boundary
- **Deliverable:** The `/api/platform` router exists with `PlatformAdminAuth`, a `whoami` endpoint, the `PlatformAuditLog` model, and a gated empty `/platform` portal shell in the frontend. Nothing cross-org yet — but the boundary is real.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] `PlatformAdminAuth` auth class + `require_superuser` dependency
  - [ ] `platform_api.py` router with `GET /platform/whoami`
  - [ ] `PlatformAuditLog` model + migration + `record_platform_action` helper
  - [ ] `app/platform/layout.tsx` route guard on `is_platform_admin`; portal absent from NGO sidebar
- **Acceptance:** A platform admin loads an empty portal; Priya (NGO user) gets 403 on `/api/platform/whoami` and sees no portal link.

#### Milestone 2: Org directory + health (read-only)
- **Deliverable:** The directory lists all orgs with health signals; org detail shows metadata + health (read-only).
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] `GET /platform/orgs` + `GET /platform/orgs/{slug}` with annotated health (users, warehouse, last run, fail state)
  - [ ] Directory table (sort/filter by status) + detail page + empty state
- **Acceptance:** Meera sees every org, spots a FAILING one without opening it, and clicks into detail.

#### Milestone 3: Cross-org user management
- **Deliverable:** From an org's Users tab, resend invite / change role / remove / add — reusing existing per-org logic; every action logged.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] `GET/POST /platform/orgs/{slug}/users`, `.../role`, `.../resend`, `DELETE`
  - [ ] Reuse `orguserfunctions` with an explicit-org context
  - [ ] Adapt user-management components to a slug param; write audit rows
- **Acceptance:** Meera resends Priya's invite in Akshara; an audit-log row appears.

#### Milestone 4: Create org
- **Deliverable:** Create an org shell and invite the first Admin (no warehouse provisioning).
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] `POST /platform/orgs` wrapping org-create + first-Admin invite
  - [ ] Create-org dialog (name, plan tier, first Admin email); duplicate-name → 409
- **Acceptance:** Arjun creates an org; it appears in the directory; the first Admin gets an invite; action logged.

#### Milestone 5: Org lifecycle + suspend cascade
- **Deliverable:** Suspend / reactivate / archive, with the full cascade and typed-name confirmation.
- **Services:** DDP_backend, webapp_v2, prefect-proxy
- **Key tasks:**
  - [ ] `Org.status` field + backfill migration
  - [ ] `POST /platform/orgs/{slug}/status` with legal-transition checks
  - [ ] Login gate (`auth.py:147` + `:69`); public-share gate (`public_api.py` — shared dashboard-token helper + report resolver `:1049`)
  - [ ] Prefect pause/resume: loop `OrgDataFlowv1` → `set_deployment_schedule`
  - [ ] Defensive gates: webhook notify (`webhook_functions.py:213`), report send task
  - [ ] Typed-name destructive confirm dialog; archived orgs drop off the active list
- **Acceptance:** Arjun suspends Akshara → its users can't log in, pipelines pause, and its public dashboard/report links return "unavailable"; reactivate reverses it all.

#### Milestone 6: Platform staff + audit-log viewer
- **Deliverable:** Superadmin manages the platform-admin list; anyone in the portal can review the filterable audit log.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] `GET/POST/DELETE /platform/staff` (superuser-gated) wrapping the `is_platform_admin` flag
  - [ ] `GET /platform/audit-log` with filters (org, actor, action)
  - [ ] Staff page (superadmin only) + audit-log page
- **Acceptance:** Ravi adds a platform admin, then filters the audit log to Akshara and sees Arjun's suspend.

---

## 8. Open Questions & Risks

**Open questions (for review):**
1. **Suspend cascade scope** ⚠️ — the real cascade is **login block + Prefect pause + public-share gate** (the cron-Alert and scheduled-report features I first worried about don't exist — research §5). Confirm public share links should go "unavailable" on suspend. Set in-scope as the planner default because the user was away.
2. **Archive vs. suspend** — plan treats archive as "suspend cascade + hidden + recoverable." Confirm that's the intended difference.
3. **Plan tier at create-org** — is "plan tier" a free label, or must it map to an existing `OrgPlan`? Plan assumes it maps to `OrgPlan`.
4. **Directory "Failing" definition** — plan defines it as "most recent pipeline run failed." Confirm that's the right health signal (vs. staleness or a failing data-quality check).

**Risks:**
- **Auth bypass (highest):** the cross-org path must fail closed. Mitigated by one shared auth class + explicit 403 tests, but it's the part to review hardest.
- **Public-share gate has no single choke point for dashboards:** each public dashboard endpoint resolves its own token (research §5), so a missed endpoint = a leak. Mitigation: add one shared `resolve_public_dashboard(token)` helper that includes the status check, and route all ~10 endpoints through it.
- **Login-block self-lockout:** the suspended-org login reject must not block platform admins or the accept-invite path.
- **Migration:** adding `Org.status` is low-risk (additive + backfill to `active`), but it runs on production orgs — standard migration review applies.
- **prefect-proxy coupling:** pausing deployments depends on the proxy being reachable; a proxy outage during suspend should fail the action loudly (status not set) rather than half-suspend. No "pause all schedules" helper exists — it's a new loop over `OrgDataFlowv1`.

---

*Draft v1 saved. Review the plan and tell me what to revise — architecture, scope, milestones, anything. When ready, run `/engineering/execute-plan features/admin-portal/v1/plan.md` to implement.*
