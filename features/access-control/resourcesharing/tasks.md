# Tasks — Resource Sharing (Layer 1: Content)

**Plan:** [plan.md](./plan.md) · **Research:** [research.md](./research.md)
**Branch:** `feature/resource-sharing` (stacked on `feature/rbac`) · **Worktrees:** `../.dalgo-worktrees/resource-sharing/{DDP_backend,webapp_v2}`
**Execution mode:** subagent-driven (experiment — fresh implementer per task + task review; evaluating vs the inline default in `executing-feature-plans`)
**Started:** 2026-07-07

**Slicing note:** `ResourceShare` model moved from M2 into M1-T2 — the resolver's `principal_match_q`/`accessible_filter` contract needs the grants table to be testable. M2 keeps the endpoints + UI.

**Setup note:** a broken pre-plan attempt (old "floor" naming, missing `models/sharing.py`) was found uncommitted in the backend worktree — stashed as `aborted pre-SDD resource-sharing attempt`.

## Milestone 1 — General access + owner + resolver (backend)
- [ ] T1: Models + migrations 0168+ — `general_audience`/`general_level`/`owner` on Dashboard/ReportSnapshot/Metric/KPI/Alert; `owner` on Chart; `created_by` CASCADE→SET_NULL ×5; OrgPreferences +3 fields; backfills; `can_delete_resource()` owner-first
- [ ] T2: `ResourceShare` model + `RESOURCE_TYPES` table (`core/sharing/shareable_types.py`) + resolver (`core/sharing/access_resolver.py`: `effective_permission`, `principal_match_q`, `accessible_filter`) — pure-function truth-table tests; writes go in `core/sharing/sharing_actions.py` (one file, per plan §4.0)
- [ ] T3: Wire `accessible_filter` into the 5 list services (dashboards/reports/alerts/metrics/kpis); query-count tests; charts list unchanged
- [ ] T4: Chart data access context — `?dashboard_id=` on chart data/detail; Member standalone → 403; `run_chart_query` seam

## Milestone 2 — Grants + share modal core + badges
- [ ] T5: `/api/access/{rtype}/{id}` GET + `/grants` POST/DELETE + `/general` PUT (narrow warn-and-offer); seed slugs migration (Redis-key delete)
- [ ] T6: Frontend — `useResourceAccess` hook + ShareModal people-rows + General-access row + `PERMISSIONS` const; badges + "Shared with you"

## Milestone 3 — Groups
- [ ] T7: `UserGroup`/`UserGroupMember` (org app) + `/api/groups` CRUD + membership + collision
- [ ] T8: Frontend — `app/settings/groups` page; group rows in ShareModal

## Milestone 4 — Invites + pending + expiry
- [ ] T9: `Invitation.expires_at` + both activation paths + resend refresh + cleanup task + non-Admin→Member cap
- [ ] T10: Frontend — paste emails, invite-role picker, pending chips

## Milestone 5 — Public links global + kill switch
- [ ] T11: `allow_public_sharing` checks (2 toggles + all public renders) + Access-Mgmt settings + org-default picker; unify reports onto ShareModal

## Milestone 6 — Ownership transfer
- [ ] T12: `/owner` endpoint + transfer modal row

## Milestone 7 — Alerts
- [ ] T13: group recipients expanded at fire time; trigger-context notification

## Milestone 8 — Comments re-gate
- [ ] T14: relax create to View + resolver-View; moderation via resolver-Edit; `CommentPopover` capability prop

## Milestone 9 — Request-access
- [ ] T15: `AccessRequest` + endpoints + owner notification
- [ ] T16: Frontend — 403 intercept + request-access screen

## Milestone 10 — Bulk
- [ ] T17: `/api/access/bulk` + multi-select bars on Dashboards/Reports/Alerts

## Milestone 11 — Verify
- [ ] T18: backfill verification; full suites; final whole-branch review; **ask user** before Playwright browser pass
