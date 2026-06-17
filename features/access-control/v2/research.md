# Research — Access Control v2 (Role System)

**For:** `features/access-control/v2/plan.md`
**Date:** 2026-06-17
**Scope:** net-new findings only. Where something already lives in `backend-architecture/landmarks.md` or `frontend-architecture/landmarks.md`, this file points there instead of repeating it.

Acronyms: FK (foreign key — a DB column pointing at another table's row) · RBAC (role-based access control) · IA (information architecture) · DQ (data quality).

---

## 1. The real role + permission data (grounds the migration)

Read directly from `DDP_backend/seed/001_roles.json` and `ddpui/models/role_based_access.py` on 2026-06-17.

There are **5 roles today, not 4.** The fifth is `super-admin`.

| pk | name | slug | level | v2 fate |
|---|---|---|---|---|
| 1 | Super User | `super-admin` | 5 | **untouched** (confirmed with user — internal Dalgo staff role) |
| 2 | Account Manager | `account-manager` | 4 | → `admin` |
| 3 | Pipeline Manager | `pipeline-manager` | 3 | → `admin` |
| 4 | Analyst | `analyst` | 2 | → `analyst` (loses infra write) |
| 5 | Guest | `guest` | 1 | → `member` |

**The rule:** `Role.level` (a `SmallIntegerField`) is the number that drives the invite cap — an inviter can invite at their level or below.
**Example:** today Account Manager (level 4) can invite a Guest (level 1) because 4 ≥ 1. After v2, Admin (level 4) can invite Member (level 1) the same way.
**Why it matters:** if we reuse levels, the new three roles need sensible level values so the existing cap check keeps working. Proposed: `admin`=4, `analyst`=2, `member`=1, `super-admin`=5 (unchanged).

**Net-new gotcha for Spec B (not v2):** the invite cap at `ddpui/core/orguserfunctions.py:217-218` is "inviter level ≥ invitee level". With `analyst`=2, that check would let an Analyst invite another Analyst (2 ≥ 2). The spec wants Analyst → Member only. This does **not** bite in v2 because the only invite surface in v2 is Settings > Users, which is Admin-only. Flag it for Spec B's share-modal invite path.

**Permission count:** `seed/002_permissions.json` now has **85 slugs** (the backend landmark said "~74" — stale; updated landmark in the same change as this research).

---

## 2. Ownership: what exists today vs. what the spec wants

**There is no `owner` field on any content model.** All five carry only `created_by` (FK to OrgUser) + `last_modified_by`. Landmark "Content models" section has the line numbers.

The delete handlers are where this gets interesting. The Explore pass found that **delete is already creator-gated for three resources, ungated for two, and has no Admin override anywhere:**

| Resource | Delete API route | Service fn | Current ownership check |
|---|---|---|---|
| Dashboard | `ddpui/api/dashboard_native_api.py:142-157` (`can_delete_dashboards`) | `services/dashboard_service.py:396` | **`created_by != orguser` → blocked** (line 422) |
| Chart | `ddpui/api/charts_api.py:1190-1203` (`can_delete_charts`) | `services/chart_service.py:225` | **`created_by != orguser` → blocked** (line 243) |
| ReportSnapshot | `ddpui/api/report_api.py:193-207` (`can_delete_dashboards`) | `core/reports/report_service.py:735` | **`created_by != orguser` → blocked** (line 753) |
| Metric | `ddpui/api/metric_api.py:204-217` (`can_delete_metrics`) | `core/metric/metric_service.py:279` | **none** — only checks chart/KPI references |
| KPI | `ddpui/api/kpi_api.py:135-148` (`can_delete_kpis`) | `core/kpi/kpi_service.py:310` | **none** — only checks dashboard usage |

Two consequences for the plan:

**The rule:** Today, even an Account Manager **cannot** delete a dashboard someone else created — the check is "are you the creator", with no Admin escape hatch.
**Example:** Priya (Analyst) creates "Field Performance". Sarah (Account Manager) tries to delete it today → blocked, because she isn't `created_by`. v2's "Admin = effective owner" rule is a *new* power, not a tightening.
**Why it matters:** the ownership milestone is partly a *fix* (add Admin override) and partly *consistency* (Metric/KPI have no check at all). It is not purely additive.

**Role slug inside an endpoint** is read as `request.orguser.new_role.slug` (example at `ddpui/api/user_org_api.py:119`). That's the hook for the Admin-override check: `owner_id == orguser.id OR orguser.new_role.slug == "admin"`.

---

## 3. Permission resolution path (how "Member view-only" is actually enforced)

Already in the backend landmark (Auth section), summarized here for the plan's security review:

```
login / token refresh
   → CustomJwtAuthMiddleware.authenticate (auth.py:176-188)
   → reads role's permission slugs from Redis (auth.py:81-91)
   → request.permissions  (a set of slugs)
   → @has_permission(["can_edit_dashboards"]) (auth.py:30-51) checks the set
```

**The rule:** a role can do X only if X's permission slug is in its RolePermission rows. "Member view-only" = the `member` role simply has no `can_create_*` / `can_edit_*` / `can_delete_*` / `can_share_*` slugs.
**Example:** James (Member) calls `POST /api/dashboards/` → `@has_permission(["can_create_dashboards"])` fails because `can_create_dashboards` isn't in his Redis permission set → 403.
**Why it matters:** most of "Member is view-only" and "Analyst read-only on infra" is **data, not code** — it's which rows exist in `seed/003_role_permissions.json` + the remap migration. The only genuinely new server code is the owner-or-admin delete check (§2).

**Redis cache:** any role/permission migration must call `set_roles_and_permissions_in_redis()` at the end of its forward function (backend landmark, Migration conventions), or the new permissions won't take effect until next deploy.

---

## 4. Frontend gating today (what the sidebar/route work builds on)

All in the frontend landmark; the load-bearing facts for the plan:

- **Sidebar** `components/main-layout.tsx` `getNavItems()` (lines 91-231). `NavItemType` has a `hide?: boolean`; render filters `.filter(item => !item.hide)`. **No role-based filtering exists yet** — today `hide` is driven by feature flags + a `PRODUCTION_HIDDEN_ITEMS` env array. Add `visibleToRoles?: Role[]` to `NavItemType`.
- **No auth gating in `middleware.ts`** today (it only handles iframe embedding). Route-role guards are net-new; the existing per-page pattern is the inline guard in `app/dashboards/[id]/page.tsx:18-42`.
- **`useUserPermissions()`** (`hooks/api/usePermissions.ts`) reads `permissions[]` from the Zustand auth store, populated from `/api/currentuserv2`. The OrgUser shape already includes `new_role_slug` — so role is available client-side without new plumbing.
- **No central `<PermissionGate>`** exists. This feature touches many gated surfaces → the landmark explicitly recommends adding `components/permission-gate.tsx` rather than spreading inline checks.
- **Settings IA is sparse today:** only `billing`, `user-management`, `about` routes exist. Warehouse / Appearance / Org-defaults / Groups slots are **empty** — they're new pages.
- **Users management is already substantial** (`components/settings/user-management/UserManagement.tsx` + `InviteUserDialog.tsx` + tables + delete dialog). Settings > Users in v2 is **re-skin/extend, not rebuild**.
- **Warehouse is a tab inside `/ingest`, not its own route** — matters for both nav gating and the Settings "Warehouse" section (the Settings warehouse page is config/credentials, distinct from the ingest warehouse tab).

When the role slugs change, grep the frontend for hardcoded `'account-manager'`, `'pipeline-manager'`, `'guest'` — none should survive the migration.

---

## 5. Org-defaults storage (where the inert toggles live)

Backend landmark (Org config section): `OrgPreferences` model (`ddpui/models/org_preferences.py:7-39`, OneToOne with Org) + its API (`ddpui/api/org_preferences_api.py:28-80`). Existing fields are toggles like `llm_optin`, `enable_discord_notifications`.

**The rule:** new org-level toggles go on `OrgPreferences`, not a new table.
**Example:** `default_visibility_floor` and `allow_public_sharing` (default true) become two new `OrgPreferences` columns + two fields on its schema. The Settings UI reads/writes them; nothing else consumes them in v2.
**Why it matters:** avoids a parallel `org_settings` table that Spec B would then have to reconcile.

---

## 6. Blast-radius decisions confirmed with the user (2026-06-17)

| Surface | Decision | Effect on plan |
|---|---|---|
| Metrics & KPIs | **In scope** — treat as content | `owner` column + owner-or-admin delete + Member view-only + role-gated `/metrics` nav. Closes the Metric/KPI delete-check gap from §2. |
| Data Quality + Explore | **Gate like Data** | Analyst read-only, Member hidden, on `app/data-quality/` and `app/explore/`. |
| `super-admin` | **Untouched** | Migration must not rename/remap pk 1. Only pks 2–5 change. |
| Billing | **Keep, Admin-only** | `app/settings/billing` folds into consolidated Settings as Admin-only; no behavior change beyond gating. |

---

## 7. Multi-service impact

- **DDP_backend** — the bulk: role remap migration, permission seed changes, `owner` column migration + backfill, owner-or-admin delete helper, two `OrgPreferences` fields, Settings/invite endpoints already mostly exist.
- **webapp_v2** — sidebar role filtering, route guards + No Access page, Settings re-IA + new pages, `<PermissionGate>`, hardcoded-slug cleanup.
- **prefect-proxy** — **not touched.** Role/permission logic lives entirely in DDP_backend; prefect-proxy has no user model. Pipelines being read-only for Analyst is enforced at the DDP_backend API layer, not in the proxy.

Validation per service: backend = pytest (role migration + permission + delete-override unit tests, see plan §6); frontend = Vitest for nav/guard logic + Playwright E2E for "Member sees only 4 nav items / Analyst can't edit infra".
