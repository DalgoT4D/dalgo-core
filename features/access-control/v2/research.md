# Access Control — Role System (Spec A) — Research (v2)

**For:** `plan.md` in this folder.
**Date:** 2026-06-15
**Scope:** net-new findings only. Codebase *locations* (file paths, line ranges) live in
`.claude/skills/backend-architecture/landmarks.md` and `.../frontend-architecture/landmarks.md` —
this file does not repeat them. Read those first.

> **Acronyms used here:** RBAC (role-based access control), FK (foreign key),
> IA (information architecture), DQ (data quality), SES (AWS Simple Email Service).

---

## 1. The current role model has FIVE roles, not four

The spec talks about "four roles" (Account Manager / Pipeline Manager / Analyst / Guest). The
seed data has a **fifth**: `super-admin` (see `seed/001_roles.json`, per backend landmarks).

**The rule:** `super-admin` is a Dalgo-internal staff role, not an org-facing role. The collapse
to three roles is about the **four org-facing roles**; `super-admin` stays untouched.

**Example:** A Dalgo support engineer with `super-admin` keeps full cross-org access after this
migration. Sarah (an org's Account Manager) becomes `admin`. The two are unrelated.

**Why it matters:** A migration that maps "all roles → 3" would wipe out `super-admin` and lock
Dalgo staff out of support tooling. The migration must explicitly **exclude** `super-admin`.

Resulting role set after migration: `super-admin` (internal), `admin`, `analyst`, `member`.

---

## 2. The collapse is a re-seed + data migration, not a code enum

There is no Python `Enum` of roles to edit. Roles are **rows** in the `Role` table, seeded from
`seed/001_roles.json`, and each role's powers are `RolePermission` rows seeded from
`seed/003_role_permissions.json` (see backend landmarks → "Auth, roles, permissions").

So "collapse four roles to three" means three coordinated changes:

| Change | Where |
|---|---|
| Add `admin` + `member` roles; keep `analyst`, `super-admin` | `seed/001_roles.json` + migration |
| Re-point each `OrgUser.new_role` FK | data migration (template: `0137_update_landing_page_permissions.py`) |
| Re-seed which permission slugs each role holds | `seed/003_role_permissions.json` + migration |

**The rule:** prefer **new slugs** (`admin`, `member`) over renaming existing slugs
(`account-manager` → `admin`).

**Example:** the frontend hardcodes slug strings like `'account-manager'` and `'guest'` in places.
If we rename the slug, every hardcoded check silently breaks. If we add new slugs and migrate
users onto them, we can grep-and-replace the frontend strings in one pass.

**Why it matters:** backend landmarks explicitly warn — *"when the backend role-slug enum changes,
search frontend for hardcoded slug strings; none should remain after a migration."*

---

## 3. Role hierarchy uses the `Role.level` integer

`Role` has a `level` field (backend landmarks). The invite role-tier rule (Admin can invite
anyone; Analyst/Member can invite Member only) is enforced today by a comparison at
`ddpui/core/orguserfunctions.py:217-218` ("inviter's role level ≥ invitee's role level").

**The rule:** set levels so `admin > analyst > member`, and the existing inviter-≥-invitee check
keeps working with no new logic.

**Example:** give `admin` level 3, `analyst` level 2, `member` level 1. When Priya (analyst,
level 2) tries to invite someone as analyst (level 2), `2 ≥ 2` would pass — so the check needs to
be **strictly greater for elevation**, or analyst's invite options must be capped to `member` in
the API. Confirm the operator (`>=` vs `>`) during implementation — this is the one subtle spot.

**Why it matters:** the spec says only Admins may *elevate* (invite as Analyst/Admin). A loose
`>=` would let an Analyst invite another Analyst, which violates §9.1 of the spec
(Analyst can invite as Member only).

---

## 4. Ownership backfill source already exists: `created_by`

Every content model already has a `created_by` FK to OrgUser (backend landmarks → "Content models").
So the `owner` backfill has a clean source.

```
owner = created_by   (if set)
owner = oldest active Admin in the org   (if created_by is null)
```

**Scoped to three models this version** (per the v2 scope decision):

| Model | `created_by` location | Add `owner`? |
|---|---|---|
| Dashboard | `models/dashboard.py:111` | ✅ |
| Chart | `models/visualization.py:60` | ✅ |
| ReportSnapshot | `models/report.py:65-70` (`SET_NULL`) | ✅ |
| Metric | `models/metric.py:62-63` | ❌ deferred |
| KPI | `models/metric.py:117` | ❌ deferred |

**Watch-out:** ReportSnapshot's `created_by` is `on_delete=SET_NULL`, so some snapshots may already
have a null creator. Those fall straight to the "oldest active Admin" fallback. The owner FK on
ReportSnapshot should also be `SET_NULL` (an owner can leave the org) — match the existing pattern.

---

## 5. Owner-only delete has ONE chokepoint per layer

**Backend:** the delete endpoint for each resource (Django Ninja `@router.delete`). Add a single
guard: `requester is owner OR requester.role in (admin, super-admin)`.

**Frontend:** the dropdown menu item in each list/actions component is the single place delete is
triggered (frontend landmarks → "Resource delete + share affordances"). Gate the menu item there;
don't scatter checks.

**The rule:** an Edit grant never includes delete — only owner or Admin deletes.

**Example:** Priya shares the "Field Performance" dashboard with Anjali at edit-level (Spec B
concept; in Spec A interim, Anjali is an Analyst who can edit). Anjali can rename it but the Delete
item is hidden/disabled for her — only Priya (owner) or Sarah (admin) sees an active Delete.

**Why it matters:** if delete is gated only in the UI, a direct API call bypasses it. Gate
server-side; mirror it in the UI for affordance.

---

## 6. Frontend has NO role-based gating today — three gaps to fill

From frontend landmarks:

1. **Sidebar:** `getNavItems()` filters on `item.hide`, driven by feature flags + a
   `PRODUCTION_HIDDEN_ITEMS` env array. **No role filtering exists.** Plan: extend `NavItemType`
   with `visibleToRoles?: Role[]` and filter by the user's `new_role_slug` from the auth store.
2. **Route gating:** `middleware.ts` only handles iframe embedding for public-share routes.
   `auth-guard.tsx` redirects unauthenticated users to `/login` but does **no role check**.
   Plan: add a role-aware guard (redirect to first accessible page, or a new No Access page).
3. **Permission gating:** today it's ad-hoc (inline `hasPermission(...)` checks, `disabled={...}`
   on buttons). **No central `<PermissionGate>`.** This feature touches many gated surfaces, so
   the landmark's own advice applies: add `components/permission-gate.tsx` once.

**The rule:** server-side gating is the real lock; frontend hiding is for clean UX.

**Example:** James (Member) has no "Ingest" nav item (frontend hide) **and** the ingest write
endpoints reject his calls with 403 (backend `@has_permission`). Both layers, not one.

---

## 7. Org-defaults storage: extend `OrgPreferences`, don't make a new table

Backend landmarks → "Org config + preferences": `OrgPreferences` is a OneToOne with Org and
already holds toggles like `llm_optin`, `enable_discord_notifications`.

**The rule:** add `default_visibility_floor` and `allow_public_sharing` (default `true`) as new
fields on `OrgPreferences`. Do not introduce a parallel `org_settings` table.

**Inert in this version:** the API stores and returns these values; nothing reads them until
Spec B's floor + public-sharing model ships. The edit endpoint needs an Admin-only permission
(reuse the existing `can_edit_*` pattern, e.g. a new `can_edit_org_defaults` slug or the existing
org-settings permission — confirm during implementation).

---

## 8. Settings > Users is mostly re-skin, not rebuild

Frontend landmarks → "Users management (already substantial)": `UserManagement.tsx` already has the
invite dialog (email + role dropdown), users table (edit role / delete user), invitations table,
and delete dialog, consuming `can_create_invitation`, `can_edit_orguser`, `can_delete_orguser`.

**What's net-new for this version:**
- Cap the invite role dropdown by the inviter's role (Admin sees all three; Analyst/Member would
  see Member only — though in Spec A the Users page is Admin-only, so practically the dropdown
  shows all three to the only people who can reach it).
- Surface an **ownership-transfer** action (Admin override) — new UI, no existing equivalent.
- Hard delete already exists (`DeleteUserDialog` + `can_delete_orguser`) — no new lifecycle work.

---

## 9. Data Quality, Explore, Metrics — confirmed gating decisions (2026-06-15)

These three surfaces were not named in Spec A's sidebar map. Confirmed with the user during planning:

| Surface | Route | Decision |
|---|---|---|
| Metrics & KPIs | `app/metrics/` | Treat like content — visible to all roles; Member sees it View-only in the interim. **No owner column** this version. |
| Explore | `app/explore/` | Analyst + Admin only; **hidden from Member** (it's a building tool, not a consumption surface). |
| Data Quality | `app/data-quality/` | Part of the Data-infra bucket — Analyst read-only, Member hidden. Stays feature-flagged. |

**Note on Explore:** it's a Superset surface. "Hidden from Member" is a nav + route gate on the
Dalgo side; confirm there's no separate Superset-level access path that bypasses it.

---

## 10. Redis permission cache must be cleared after the migration

Backend landmarks → "Auth, roles, permissions" + "Migration conventions": role→permission mapping
is cached in Redis (`set_roles_and_permissions_in_redis()`), and there's a per-user
`orguser_role:{id}` cache populated on login/token-refresh.

**The rule:** call `set_roles_and_permissions_in_redis()` at the end of the role/permission data
migration's forward function, and expect per-user caches to refresh on next login/token-refresh.

**Example:** right after migration, Priya's browser may still hold an old token whose cached
permissions include infra write. Until her token refreshes, the **server-side** `@has_permission`
check (reading the re-seeded RolePermission rows via the cleared Redis cache) is what actually
blocks her infra writes. This is another reason server-side gating is the real lock.

---

## 11. Multi-tenant safety reminder (carry into every new endpoint)

Backend landmarks → "API conventions": every endpoint filters by `org=request.orguser.org`, and
resource fetches must include `org=` in the filter, never just `pk=id`.

This applies to all net-new endpoints here: ownership-transfer, org-defaults read/write, and any
role-change path. An ownership transfer must verify both the resource **and** the new owner belong
to the requester's org.

---

## Open items for the plan's "Open Questions" section
- Invite-gating operator (`>=` vs `>`) for the analyst-can't-elevate rule (see §3 above).
- Exact permission slug for editing Org-defaults (new slug vs reuse existing).
- Whether deprecated roles (`account-manager`, `pipeline-manager`, `guest`) are deleted after
  migration or kept as tombstones for rollback safety.
