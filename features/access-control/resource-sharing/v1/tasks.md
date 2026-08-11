# Resource Sharing — Tasks

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## M1 — Access control engine (backend)

- [x] **1a** Fix Analyst floor default → `AccessLevel.EDIT` in `OrgPreferences` + backfill migration
- [ ] **1b** Add `KPI = "kpi"` to `ResourceType` enum (`models/resource_share.py`)
- [ ] **1b** Add KPI to `RTYPES` in `shareable_types.py`
- [x] **1c** Add `parent` self-FK (nullable, CASCADE) to `ResourceShare` + migration
- [ ] **1c** Fix `_grants_map` in `access_control.py` — take max per (principal, resource), not last-write-wins
- [ ] **1c** `resource_share.add_grants` — after dashboard share created, create child rows for inner charts/KPIs via `_inner_ids_from_dashboard`
- [ ] **1c** `resource_share.update_grant` — after dashboard share level updated, propagate to child rows
- [ ] **1c** Add `sync_cascade_rows(dashboard, old_tabs, new_tabs)` helper in `resource_share.py`
- [ ] **1c** Hook `sync_cascade_rows` into dashboard update API (`dashboard_native_api.py`) wherever `tabs` is saved
- [ ] **1d** Replace `_require_owner_or_admin` with `_require_edit_or_admin` on all grant endpoints (`access_api.py`)
- [ ] **1e** `ChartService.list_charts` — add `orguser` param; apply `accessible_filter`; annotate `access_level` via `get_user_access_map`
- [ ] **1e** `charts_api.py list_charts` — pass `orguser`; include `access_level` in `ChartResponse`
- [ ] **1e** `ReportService.list_snapshots` — add `orguser` param; apply `accessible_filter`; annotate `access_level`
- [ ] **1e** `report_api.py list_snapshots` — pass `orguser`; include `access_level` in `SnapshotResponse`
- [ ] **1e** `webapp_v2/types/charts.ts` — add `access_level?: 'view' | 'edit'`
- [ ] **1e** `webapp_v2/types/reports.ts` — add `access_level?: 'view' | 'edit'`
- [ ] **1e** `app/charts/page.tsx` — gate edit/share buttons on `chart.access_level === 'edit'` instead of role permission
- [ ] **1e** `app/reports/page.tsx` — gate edit/delete/share buttons on `report.access_level === 'edit'`
- [ ] **1f** Add `CascadeSourceSchema` to `resource_share_schema.py`
- [ ] **1f** Update `ShareRowSchema` — add `cascade_sources`, make `share_id: Optional[int]`
- [ ] **1f** Rewrite `list_grants` — group by principal, compute effective max, populate `cascade_sources`
- [x] **1g** Add `is_private = BooleanField(default=False)` to Dashboard, Chart, Report, KPI models + migration
- [ ] **1g** Update `accessible_filter` in `access_control.py` — exclude private resources from floor-based access
- [ ] **1g** Update `get_user_access` — skip floor fallback when `is_private=True` and no grant exists
- [ ] **1g** Update `get_user_access_map` — skip floor fallback per resource when `is_private=True` and no grant exists
- [ ] **1g** Add `PATCH /api/access/{rtype}/{resource_id}/private` endpoint — requires owner or Edit; clears public share token when setting `is_private=True`
- [ ] **1h** Floor hierarchy validation in `org_preferences_api.py` PUT handler — reject if `default_member_level` rank > `default_analyst_level` rank

---

## M2 — ~~Cascade removal warning API~~ — dropped

Generic confirmation dialog in the frontend only; no backend API needed.

---

## M3 — Ownership transfer API (backend)

- [ ] Add `TransferOwnershipPayload` schema to `resource_share_schema.py`
- [ ] Implement `POST /api/access/{rtype}/{resource_id}/transfer-ownership` in `access_api.py`
- [ ] Transfer logic in `ownership.py` — validate caller is owner/Admin; validate recipient has effective Edit via `get_user_access`; update `created_by`

---

## M4 — Request access (backend)

- [x] Add `AccessRequest` model (`models/resource_share.py` or new file)
- [x] Write migration for `AccessRequest` table
- [ ] `POST /api/access/{rtype}/{resource_id}/request-access` — create request
- [ ] `GET /api/access/{rtype}/{resource_id}/request-access` — list pending requests (Edit-holders only)
- [ ] `POST /api/access/{rtype}/{resource_id}/request-access/{id}/respond` — approve/decline
- [ ] Resource detail endpoints — return 403 (not 404) when resource exists but caller lacks access; 404 only for genuinely missing resources

---

## M5 — Invitation promotion + cleanup (backend)

- [ ] Invitation promotion in `orguserfunctions.py` — on acceptance, update `ResourceShare` + `OrgUserGroupMember` rows
- [ ] Group delete cleanup — `post_delete` signal on `OrgUserGroup` to delete orphan `ResourceShare` rows
- [ ] Resource delete cleanup — in delete handlers for Dashboard, Chart, Report, KPI: delete `ResourceShare` + `AccessRequest` rows

---

## M6 — Cascade removal warning + KPI sharing + Private toggle (frontend)

- [ ] Cascade confirmation dialog in `share-modal.tsx` — static generic warning triggered when downgrading/removing Edit on a dashboard (no API call needed)
- [ ] Add ShareModal to KPI page (`app/kpis/`) with `rtype="kpi"`
- [ ] Private toggle in `share-modal.tsx` — calls `PATCH /api/access/{rtype}/{resource_id}/private`; hides public sharing toggle when Private is on
- [ ] Floor hierarchy enforcement in `RolesTab.tsx` — disable Member floor options that exceed Analyst's current floor

---

## M7 — Ownership transfer UI (frontend)

- [ ] Add "Transfer Ownership" option to permission dropdown in share modal (owner/Admin only)
- [ ] Ownership transfer confirmation dialog in `share-modal.tsx`
- [ ] Add `transferOwnership` to `hooks/api/useAccess.ts`
- [ ] Update `ShareRow` type in `types/access.ts` — add `cascade_sources: CascadeSource[]`, make `share_id: Optional<number>`

---

## M8 — Request access UI (frontend)

- [ ] Redesign `NoAccess.tsx` — add "Request Access" button + request modal (level + note); handles 403 response from resource detail endpoints
- [ ] Add request-access hooks to `hooks/api/useAccess.ts`
- [ ] Add "Access Requests" section to share modal (`share-modal.tsx`) — visible to Edit-holders; approve/decline actions

---

## M9 — Bulk share + access badges (frontend)

- [ ] Add `<AccessBadge>` component to `components/ui/`
- [ ] Apply access badge to dashboard list (`dashboard-list-v2.tsx`)
- [ ] Apply access badge to chart list (`app/charts/page.tsx`)
- [ ] Apply access badge to reports list
- [ ] Add bulk Share action to chart list (`app/charts/page.tsx`)
- [ ] Add bulk Share action to dashboard list (`dashboard-list-v2.tsx`)

---

## M10 — Tests (backend)

- [ ] `ddpui/tests/core/test_access_control.py` — floor, direct grants, cascade max, admin override, accessible_filter with NO_ACCESS floor, Private toggle bypasses floor
- [ ] `ddpui/tests/api/test_access_api.py` — grants CRUD, Edit-holder re-share, View-holder 403
- [ ] Cascade impact API tests — affected charts/KPIs with no other Edit path; direct Edit excludes from warning
- [ ] Ownership transfer tests — owner → Analyst (Edit floor) succeeds; owner → Member with direct Edit share succeeds; owner → Member with no Edit share → 400; non-owner → 403
- [ ] Request access tests — no access → 201; already has access → 409; duplicate pending → 409; owner approves → grant created; declines → status updated
- [ ] Private toggle tests — private resource invisible to floor-based access; explicit grantee still has access; turning private on clears public link
- [ ] Floor hierarchy validation tests — Member floor > Analyst floor → 400
