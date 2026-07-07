# Research — Resource Sharing (Layer 1: Content)

**For:** `features/access-control/content/plan.md`
**Date:** 2026-07-06
**Baseline:** the `feature/rbac` branch in both code repos — **not main**. Spec A (role collapse + ownership) lives on this branch; its PRs are still open (DDP_backend [#1414](https://github.com/DalgoT4D/DDP_backend/pull/1414), webapp_v2 [#331](https://github.com/DalgoT4D/webapp_v2/pull/331), both targeting main). Resource sharing stacks on top of it.

**Scope:** net-new findings only, verified by reading code on `feature/rbac` on 2026-07-06. Prior research: `../role-collapse/research.md` (Spec A) and `../dataset-access/research.md` (Layer 2).

**Acronyms:** FK (foreign key — a DB column pointing at another table's row) · RBAC (role-based access control) · TTL (cache lifetime) · IA (information architecture).

> **Stale reference note:** `role-collapse/research.md` and the project CLAUDE.md point at `.claude/skills/backend-architecture/landmarks.md` and `frontend-architecture/landmarks.md`. **Neither skill exists in dalgo-core anymore.** This file carries the load-bearing facts directly instead of pointing there.

---

## 1. What Spec A actually shipped on `feature/rbac` (backend)

### 1.1 Roles and levels — `seed/001_roles.json`

| pk | slug | level |
|---|---|---|
| 1 | `super-admin` | 5 |
| 2 | `admin` | 4 |
| 4 | `analyst` | 2 |
| 5 | `member` | 1 |

pk 3 (pipeline-manager) is gone. On existing installs the collapse runs via a **management command**, not a migration: `ddpui/management/commands/migrate_rbac_v2_roles.py` (has `--dry-run`). Fresh installs seed 3 roles directly.

**Why it matters for this plan:** our new-slug data migration must follow whatever pattern the command established, and existing installs must run the command *before* our migration lands (order matters for the role pks the seed references).

### 1.2 Ownership shipped WITHOUT an `owner` column

`ddpui/core/ownership.py` exports one function, `can_delete_resource(orguser, resource)` (line 5): allow if `resource.created_by_id == orguser.id` OR role slug is admin/super-admin. Its docstring says keying off `created_by` was deliberate — no backfill needed.

**The rule:** on this branch, "owner" *is* the creator; there is no transferable owner field anywhere.
**Example:** Anjali created "Field Performance". Priya (Analyst) cannot delete it; Admin Raj can. Nobody can hand it to Priya.
**Why it matters:** the sharing plan's ownership-transfer milestone now *introduces* `owner` for the first time (backfill = `created_by`), instead of merely extending it.

Six delete call-sites already use the helper — Dashboard (`services/dashboard_service.py:423`), Chart (`services/chart_service.py:244` single, `:284` bulk), ReportSnapshot (`core/reports/report_service.py:762`), Metric (`core/metric/metric_service.py:286`), KPI (`core/kpi/kpi_service.py:325`), Alert (`core/alerts/alert_service.py:368`).

### 1.3 `created_by` on_delete behavior (the transfer landmine)

| Model | `created_by` on_delete | File |
|---|---|---|
| Dashboard | **CASCADE** | `ddpui/models/dashboard.py:111` |
| Chart | **CASCADE** | `ddpui/models/visualization.py:60` |
| Metric | **CASCADE** | `ddpui/models/metric.py:62` |
| KPI | **CASCADE** | `ddpui/models/metric.py:122` |
| Alert | **CASCADE** | `ddpui/models/alert.py:90` |
| ReportSnapshot | SET_NULL, null=True | `ddpui/models/report.py:65-70` |

**Why it matters:** delete a departed analyst's OrgUser account and five resource types die with it — even ones transferred to someone else. The plan must flip these five to SET_NULL when it adds `owner`.

### 1.4 Permission slugs — one share slug exists, four are missing

`seed/002_permissions.json` has 85 slugs. **Only `can_share_dashboards` (pk 72) exists**; there is no `can_share_charts/reports/alerts/metrics/kpis` and no comment slug. Reports reuse the dashboard slugs throughout.

`seed/003_role_permissions.json` grants: super-admin 84 slugs, admin 83, analyst 45, member 9. Analyst has full content create/edit/delete/view **including `can_share_dashboards`**; member has view-only on all five content families (`can_view_dashboards/charts/kpis/metrics/alerts`).

### 1.5 Permission resolution + the Redis keys

```
request → CustomJwtAuthMiddleware.authenticate (ddpui/auth.py:111-195)
  → role→slugs map from Redis key env ROLE_PERMISSIONS_REDIS_KEY
      (default "dalgo_permissions_key", auth.py:131)
  → orguser→role map from key f"orguser_role:{user.id}" (auth.py:136)
  → request.permissions : set[str] (auth.py:192)
  → @has_permission([...]) (ddpui/auth.py:39) → 403 if missing
```

Rebuild helper: `set_roles_and_permissions_in_redis(redis_client, key)` at `ddpui/auth.py:63` — called lazily on cache-miss (line 187) and on login (line 216). **So a seed migration only needs to DELETE the Redis key**; the next request rebuilds it. Never call the rebuild inside a migration (Redis-less CI breaks).

Redis client: `ddpui/utils/redis_client.py:9` — `RedisClient.get_instance()` returns a raw redis-py client (native `.get/.set/.delete`, `ex=` for TTL).

---

## 2. Sharing infrastructure today: public tokens only (backend)

Confirmed greenfield: **no** `core/sharing/`, no `ResourceShare` / `UserGroup` / `AccessRequest` anywhere in `ddpui`.

What does exist — the binary public-link flow, on Dashboard (`models/dashboard.py:86-102`) and ReportSnapshot (`models/report.py:55-62`), identical field sets: `is_public`, `public_share_token` (unique, `secrets.token_urlsafe(48)`), `public_shared_at`, `public_disabled_at`, `public_access_count`, `last_public_accessed`.

| Surface | Endpoint | Gate |
|---|---|---|
| Toggle dashboard | `PUT /api/dashboards/{id}/share/` (`dashboard_native_api.py:394`) | `can_share_dashboards` |
| Toggle report | `PUT /api/reports/{snapshot_id}/share/` (`report_api.py:267`) | `can_share_dashboards` |
| Public render | `/api/v1/public/…` — separate unauthenticated NinjaAPI (`routes.py:120-126`, handlers `public_api.py:95` dashboard, `:199` chart data, `:1105` report) | token lookup only |

**There is no org-level global gating public sharing** (grepped `org.py` / `org_preferences.py`). The Admin kill switch is entirely net-new and must be checked in **both** the toggle endpoints and the public render handlers.

---

## 3. Other backend surfaces the plan touches

- **List endpoints filter by org only** — no role/creator filtering anywhere. Dashboards `dashboard_service.py:273` (API `dashboard_native_api.py:58`), Charts `chart_service.py:88` (API `charts_api.py:271`), Reports `report_api.py:54`, Metrics `metric_api.py:36`, KPIs `kpi_api.py:46`, Alerts `alert_api.py:192`. The resolver's `accessible_filter` gets wired into five of these (charts stay role-gated).
- **Chart data**: `GET /api/charts/{chart_id}/data/` (`charts_api.py:1028`, gate `can_view_charts`) already takes `dashboard_filters` (a filter payload) — but **no access-context param**. The `?dashboard_id=` *access* check is net-new and distinct from `dashboard_filters`. Also `POST /api/charts/chart-data/` (`:492`) and previews (`:537`, `:644`) serve authoring paths.
- **Invitation** (`models/org_user.py:151`): fields `invited_email, invited_by, invited_on, invite_code, invited_new_role, created_at, updated_at`. **No `expires_at`.** Core fns: `invite_user_v1` (`core/orguserfunctions.py:207`), `accept_invitation_v1` (`:281`), `resend_invitation` (`:365`). Invite cap at `orguserfunctions.py:223`: `invited_role.level > orguser.new_role.level → error`. **The 2 ≥ 2 loophole is live:** an Analyst (level 2) can invite another Analyst. Today only Admins reach the invite UI, so it doesn't bite — the share-modal invite path must add the explicit "non-Admin invites Member only" check.
- **Comments** (`models/comment.py:19` — FK snapshot, author, `is_deleted`): routes in `report_api.py` — list `:372` gated `can_view_dashboards`, **create `:399` gated `can_edit_dashboards`** (Members can't comment today), update `:427` / delete `:452` gated `can_edit_dashboards`. `CommentService` (`core/reports/comment_service.py`) is **author-only** for update/delete (`:147-148`, `:172-173`) — no admin/editor moderation exists. Delete is soft only when the thread has others' replies (`:182-185`).
- **Notification**: `create_notification(NotificationDataSchema)` at `core/notifications/notifications_functions.py:114`; models `Notification` (author is an *EmailField*, message, urgent, scheduled_time…) + `NotificationRecipient` (FK OrgUser, read_status, task_id). Reusable for share/request notices as decided.
- **OrgPreferences** (`models/org_preferences.py:7`, OneToOne with Org): only LLM/Discord fields today. API mounted at `/api/orgpreferences/` (`org_preferences_api.py`). The three sharing fields (default general audience, default level, `allow_public_sharing`) are net-new columns here.
- **Routes**: `ddpui/routes.py:96-117` mounts routers on the authenticated `src_api`. **`/api/access` and `/api/groups` prefixes are free.**
- **Migrations**: latest is **0167** (`0167_orguser_has_seen_rbac_notice.py`). New work starts at 0168.

---

## 4. What Spec A shipped on `feature/rbac` (frontend)

### 4.1 The RBAC library — `lib/rbac.tsx` (231 lines)

Exports: `ROLES` / `Role` (super-admin, admin, analyst, member) · `ADMIN_ROLES` · `DATA_SECTION_ROLES` · `PERMISSIONS` (all 85 slugs mirrored from the backend seed, incl. `CAN_SHARE_DASHBOARDS` at line 114) · `useRbac()` (lines 158-188: `{role, isLoaded, hasRole, hasPermission, hasAnyPermission, hasAllPermissions}`, reads the auth store) · `RoleGuard` (page gate, fallback `<NoAccess />`) · `PermissionGuard` (action gate, renders nothing by default).

**Gotchas:** the hook is `useRbac`, not `usePermissions` (`hooks/api/usePermissions.ts` was deleted); the component is `PermissionGuard`, not `PermissionGate`; `DataSectionGuard` from the Spec A tasks **does not exist** — data-section gating is nav-level `visibleToRoles` plus per-page `RoleGuard`. New share slugs must be added to the frontend `PERMISSIONS` const too, or `hasPermission` lookups will silently fail.

### 4.2 Auth store — `stores/authStore.ts`

`OrgUser` (lines 18-30) carries `new_role_slug`, `permissions: {slug, name}[]`, and `has_seen_rbac_notice` — all per-org, populated from `/api/currentuserv2`. `getCurrentOrgUser()` (:141) resolves by `selectedOrgSlug`. Pattern to copy for any new per-user flag.

### 4.3 Share UI today — two diverging components

| Resource | Component | What it does |
|---|---|---|
| Dashboards | `components/ui/share-modal.tsx` (`ShareModal`, entity-agnostic: props `entityId`, `getShareStatus`, `updateSharing`) | public toggle + copy link + access counts; "Organization Access (Default)" info card. Used from `dashboard-list-v2.tsx` (:470, :2023-2035) and `dashboard-native-view.tsx` (:508) |
| Reports | `components/reports/report-share-menu.tsx` (`ReportShareMenu`) → `share-via-link-dialog.tsx` + `share-via-email-dialog.tsx` | dropdown: public link dialog, or email a PDF+link |

**Why it matters:** `ShareModal` is the natural vehicle to grow into the unified people/groups/general-access modal — but reports don't use it. Unifying reports onto the extended `ShareModal` is a plan decision (recommended), not a given.

### 4.4 List pages, bulk, badges

- Routes: `app/dashboards|charts|reports|alerts|metrics|kpis/page.tsx`; the dashboards page just renders `components/dashboard/dashboard-list-v2.tsx`.
- **Multi-select/bulk exists only on Charts** (`app/charts/page.tsx` — checkbox column :50, selection state :115-132, `useBulkDeleteCharts`, bulk button ~:1061). That's the pattern to copy to Dashboards/Reports/Alerts for bulk share. Ironically charts (not shareable) is the one list that has it.
- `dashboard-list-v2.tsx` badges (:825-857): "My Landing", "Org Default", lock badges. Its **"Show only shared" filter treats shared == `is_public`** (predicate `!dashboard.is_public`, :271) — this filter's meaning changes once real sharing exists; rename/re-scope it.

### 4.5 Settings IA, invite, 403 handling

- `app/settings/`: `branding` (AdminOnly via nav + no page guard), `about` (open), `user-management` + `billing` (both `<RoleGuard roles={ADMIN_ROLES}>`). **No Groups page.**
- `InviteUserDialog` (`components/settings/user-management/InviteUserDialog.tsx`): `useRoles()` → `/api/data/roles`, renders **all** returned roles — **no client-side cap**; the cap is backend-only. The share-modal invite path needs the client-side "non-Admin → Member only" filter.
- **No 403 handling exists anywhere**: `lib/api.ts` special-cases only 498 (token refresh, single-flight) and 401 (logout, skipping `/share/*` + `/public/*` paths); a 403 throws a generic Error with no UI. `NoAccess` (`components/no-access.tsx`) is purely a client-side role-guard render — its "Contact your org Admin to request access" copy has no action behind it. The request-access screen needs a real 403 intercept on detail pages.
- API client (`lib/api.ts`): cookie-based auth (`credentials: 'include'`, no bearer header), org context via `x-dalgo-org` header from `localStorage['selectedOrg']`; helpers `apiGet/apiPost/apiPut/apiPatch/apiDelete` + `apiPublicGet/apiPublicPost`.

### 4.6 Nav + the RBAC notice pattern

`getNavItems` (`components/main-layout.tsx:94-258`): only the **Data** section (`visibleToRoles: DATA_SECTION_ROLES`) and three admin Settings items are role-filtered. **Members currently see Impact, KPIs, Charts, Dashboards, Reports, Alerts** — including a Charts nav item with no restriction (:114-119). Since charts are container-gated in the new model, Member's Charts nav (and the org-wide chart list a Member's `can_view_charts` slug currently opens) must be closed off.

`RbacNoticeCarousel` (`components/onboarding/rbac-notice-carousel.tsx`) shows once per user off `OrgUser.has_seen_rbac_notice`, persists via `PUT /api/v1/organizations/user_self/`. Reusable pattern for any future one-time sharing announcement.

---

## 5. Multi-service impact

- **DDP_backend** — the bulk: 4 new tables, `general_*` + `owner` columns on 5 models, `created_by` CASCADE→SET_NULL flip on 5 models, resolver + registry, `/api/access/*` + `/api/groups` routers, seed slugs, invite expiry, comments re-gate, kill switch, OrgPreferences fields.
- **webapp_v2** — extend `ShareModal` (and unify reports onto it), Groups settings page, badges + "Shared with you", bulk bars (copy the Charts pattern), request-access on 403, transfer modal, `PERMISSIONS` const additions, invite-role cap client-side.
- **prefect-proxy** — untouched (no user model; unchanged from Spec A analysis).

Validation per service: backend pytest (resolver truth-table, list scoping, context-gated chart data, kill switch, invite expiry); frontend Vitest (modal states, guards, badges) + Playwright pass across the three roles at the end.

---

## 6. Branch strategy fact

Spec A's PRs (#1414, #331) are open against main from `feature/rbac`. Building resource sharing as new commits **directly on `feature/rbac` would bloat those open PRs**. The plan should branch `feature/resource-sharing` off `feature/rbac` in each repo and either re-target after Spec A merges, or stack the PRs explicitly.
