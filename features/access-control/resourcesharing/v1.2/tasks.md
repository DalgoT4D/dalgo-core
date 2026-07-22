# v1.2 Execution Ledger — DASHBOARD-ONLY PILOT

Started 2026-07-22. Owner decision: implement the v1.2 design (permission-FK
grants + decorator gates + flat pool) **for dashboards only** — "lets do only
the changes for dashboard now then we can see." Other rtypes keep the current
gates.py / resolver path untouched.

Branch: `feature/resource-sharing` (backend, PR #1433 — push authorized).
Base: fb43f807. Webapp: NO changes needed for the pilot (resolver returns
"edit" for Member-with-edit-grant on dashboards → existing `user_permission`
field drives affordances).

## Pilot scope decisions (deltas from v1.2 plan, all reversible at full rollout)

- Schema lands as NEW migration 0180 on the branch (same "window" — PRs
  unmerged, prod never saw 0170+; in-place edits of 0170 not needed).
- `ResourceShare.granted_permission` FK (nullable, PROTECT, db_column
  `permission_id`) ADDED; varchar `permission` KEPT (other rtypes still read
  it). Dual-write via `save()` sync; FK-null falls back to varchar in the
  pool. Varchar drop + non-null happen at full rollout.
- `AccessRequest.requested_permission_id` FK: DEFERRED to full rollout
  (additive migration, no window pressure).
- `Permission.implies_id` DB column: DEFERRED — implication (edit ⊇ view)
  derived in code from RTYPE_LEVEL_SLUG (same single source; avoids
  seed-load-order coupling in migrations/tests).
- **DISCOVERED GAP**: seeds have NO `can_view_reports`/`can_edit_reports`
  (only `can_share_reports`) → RTYPE_LEVEL_SLUG covers 5 of 6 rtypes; report
  grants backfill to NULL FK. Full rollout must add report slugs first.
- **Delete stays owner-gated in-body** (service-level owner check). Flat pool
  would widen delete to every Analyst (role carries `can_delete_dashboards`
  org-wide) — flagged to user; ownership is a separate axis in the pilot.
- **The Member flip IS in the pilot, dashboards only**: new registry flag
  `member_edit_grants` (dashboard=True, others False); resolver Member
  grant-cap becomes conditional on it. Report/alert keep the cap; chart/kpi/
  metric unaffected (member_sharing=False excludes grants entirely).
- Member re-share open decision: NOT touched (share-modal/re-share endpoints
  keep PERMISSION_RANK; §4.2 of plan is full-rollout work).
- H1 unique constraint: NOT bundled (pending_email null-key semantics need
  their own design; still a tracked review fix).

## Tasks

- [x] T1 permission_map.py: RTYPE_LEVEL_SLUG + implied-closure + cached
      Permission id/slug lookup + completeness tests (7 passed)
- [x] T2 migration 0180: granted_permission FK (db_column permission_id,
      PROTECT, nullable) + backfill; save() dual-write; 5 tests incl.
      update_or_create upgrade sync + ProtectedError
- [x] T3 registry flag member_edit_grants (dashboard=True) + conditional
      resolver cap; dashboard cap test flipped on purpose (cites §5),
      report still-capped test added (41 resolver tests green)
- [x] T4 decorators.py: extract_resource + has_resource_permission +
      build_permission_pool; 17 tests (Ishan case, 404 wall, 403 wording,
      positional binding, decoration-time slug/rtype validation, 2-query pin).
      **DESIGN CORRECTION found by test**: role slugs must NOT pool (would
      give every Member view on every dashboard) — §3.3 of plan amended;
      pool = grants ∪ floors ∪ owner/admin only, closed under implication
- [x] T5 dashboard_native_api sweep: 12 instance routes on ②③ stack
      (get, coverage, update, duplicate, 3 locks, 4 filters, 2 share);
      ① → view-slug on edit routes; delete/landing/list untouched.
      586 sharing+dashboard tests green; 1 flip (invited-Member pending
      edit grant now resolves edit — test updated, cites §5)
- [x] T6 full backend suite 2821 passed / 31 skipped, 0 failures; commits
      95326dae (pilot) + 78972e8f (user_permission field) pushed to PR #1433
- [x] T7 sandbox live check (2026-07-22, migrated 0180, backend restarted):
      Member+edit-grant GET/PUT dashboard A → 200; PUT B (floor view only)
      → 403 exact wording; GET B → 200 via member_level=view floor (sandbox
      org default — correct); DELETE → 404 unauthorized (Layer 2, delete
      untouched); grant row carried granted_permission__slug=
      can_edit_dashboards (FK dual-write live through the real share
      endpoint); detail GET reports user_permission=edit. Probe dashboards
      cleaned up.

## Scope addition discovered during T7 (committed)

The webapp's edit affordances gate on the ROLE slug — a Member with an edit
grant could edit via API but never saw the editor. Fix: detail/update
responses now carry `user_permission` (read off the pool ③ attached — zero
extra queries; lists deliberately excluded), and the webapp widens
`canEdit = roleSlug || user_permission === 'edit'` in the edit page (denied
screen now waits for the fetch) and the detail view's Edit button. Webapp
commit 3aeaf1bc on PR #347; tsc baseline identical (131 both ways), 51
dashboard jest tests green. List-menu Edit items stay role-gated (list
payloads carry no per-row pool level) — Members with grants enter via the
detail page; full-rollout item.

CLOSED 2026-07-22 — dashboard pilot complete and live in sandbox.
Backend fb43f807 → 78972e8f (PR #1433), webapp → 3aeaf1bc (PR #347).

## Post-close owner revisions (2026-07-22, all pushed)

- 20bfb34c: 0180 backfill REMOVED (owner call) — migration is additive-only;
  save() sync + the varchar fallback in the gate cover null-FK rows.
- 1d77c3e0: decorators.py dissolved — ② ③ moved into auth.py beside
  @has_permission (sharing imports deferred to decoration time to dodge the
  auth↔sharing import cycle); pool builder renamed
  build_permission_pool → get_resource_permissions and moved into
  access_resolver.py beside effective_permission. Full suite 2822 green;
  sandbox restarted on 1d77c3e0.
