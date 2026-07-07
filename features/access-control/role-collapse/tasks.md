# Tasks — Access Control v2 (RBAC)

**Plan:** [plan.md](./plan.md) · **Research:** [research.md](./research.md)
**Branch:** `feature/rbac` (both code repos) · **Worktrees:** `../.dalgo-worktrees/rbac/{DDP_backend,webapp_v2}`
**Started:** 2026-06-17

## Resolved open questions (2026-06-17)
- **Q3 (Member-as-owner delete):** No special handling. Members have no `can_delete_*` slug, so the `@has_permission` decorator returns 403 *before* `can_delete_resource()` runs. Helper stays owner-or-admin as written.
- **Q5 (org-defaults toggles):** **Deferred to Spec B.** M4 does NOT add the two `OrgPreferences` fields or their toggles — Settings consolidation + Admin-only gating only.
- Q1/Q2/Q4/Q6: proceed on plan's recommendation; note in PR.

---

## Milestone 1: Role collapse + permission remap (backend) ✓
- [x] RED: write post-migrate assertion tests (slugs exist, super-admin pk1 untouched, AM+PM→admin, member gains view slugs, analyst loses infra-write keeps infra-view)
- [x] Update `seed/001_roles.json` + `seed/003_role_permissions.json` for the 3 roles
- [x] Data migration: remap OrgUser roles + permission deltas + `set_roles_and_permissions_in_redis()` + reverse
- [x] GREEN: tests pass
- [x] Commit (`ed4d862b`)

## Milestone 2: Analyst read-only / Member hidden on Data + DQ + Explore (frontend) ✓
- [x] Confirm DQ + Explore slugs trimmed for Analyst in M1 seed
- [x] Add `visibleToRoles` to `NavItemType`; tag items (Impact/KPIs/Data → admin+analyst; Billing/UserMgmt → admin); extend filter in `getNavItems`
- [x] Hide pipeline Run button for users without `can_run_pipeline` (was disabled; now hidden unless pipeline actively running)
- [x] Tests (6 nav filter assertions) + commit (`d205aa1`)
- **Note:** All other affordance hiding (create/edit/delete) already worked via existing `hasPermission()` calls + M1 seed changes removing write slugs from Analyst/Member.

## Milestone 3: Sidebar + route gating + No Access page (frontend) ✓
- [x] `visibleToRoles` system added in M2 (combined)
- [x] `NoAccess` component (`components/no-access.tsx`)
- [x] `DataSectionGuard` wrapper (`components/data-section-guard.tsx`) — renders NoAccess for Member
- [x] Route guards on all 6 Data section pages: pipeline, ingest, transform, orchestrate, explore, data-quality
- [x] Grep-replace old slug strings (`account-manager` → `admin`) in 2 test files
- [x] Tests + commit (`a62d772`)

## Milestone 4: Settings consolidation (frontend + minor backend) — org-defaults DEFERRED ✓
- [x] Settings IA pages; gate Billing + User Management Admin-only (`<RoleGuard allowedRoles={['admin']}>`)
- [x] (org-defaults toggles + OrgPreferences fields: SKIPPED per Q5)
- [x] Commit (`603b0f1`)

## Milestone 5: Ownership — owner column, backfill, owner-or-admin delete (backend) ✓
- [x] Schema migration + backfill (oldest-active-Admin fallback) — migration 0166
- [x] `can_delete_resource()` helper in `core/ownership.py`; wired into 5 delete services
- [x] Existing tests updated (other_orguser/orguser2 → analyst role; new error message assertions)
- [x] Commit (`dc516439`)

## Milestone 6: Settings > Users invite surface (frontend) ✓
- [x] Invite dialog already uses `useRoles()` → `/api/data/roles` → level-capped 3 roles
- [x] User Management page already Admin-only via `<RoleGuard>` (M4)
- [x] Backend invite endpoint: `@has_permission(["can_create_invitation"])` — only admin has this slug
- [x] Backend role-level cap: `invited_role.level > orguser.new_role.level` → 400
- [x] Test: InviteUserDialog shows exactly 3 roles, no legacy roles, submits uuid
- [x] Commit (`7601275`)

## Milestone 7: Browser testing with Playwright MCP (post-build) ✓
- [x] Admin: all nav items visible; Settings shows Billing + User Management + About; User Management page accessible with correct role table (Admin/Analyst/Member)
- [x] Analyst: Impact/KPIs/Data visible; Settings shows About only; /settings/billing → NoAccess; /settings/user-management → NoAccess; /pipeline → accessible
- [x] Member: Impact/KPIs/Data hidden from nav; Settings shows About only; /pipeline → NoAccess; /settings/billing → NoAccess; /settings/user-management → NoAccess
- [x] M1 role migration confirmed live: pipeline@testngo.org shows as "Admin" (was pipeline-manager); guest@testngo.org shows as "Member" (was guest)

## Nav fix + Analyst read-only verification ✓
- [x] Remove `visibleToRoles` from Impact and KPIs — visible to all roles including member
- [x] Update `main-layout.test.tsx` assertions to match new spec
- [x] Browser-verified (analyst): Impact + KPIs in nav ✓; Data section accessible; Orchestrate/Ingest/Pipeline = read-only, no create/edit/delete buttons ✓

## Pre-merge ✓
- [x] Full test suite green in both repos (backend: 1969 passed; frontend: 1407 passed)
- [x] Two PRs opened, backend first, cross-linked, merge order stated
  - Backend: https://github.com/DalgoT4D/DDP_backend/pull/1414
  - Frontend: https://github.com/DalgoT4D/webapp_v2/pull/331
- [ ] Remove worktrees after merge
