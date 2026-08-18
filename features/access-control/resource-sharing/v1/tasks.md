# Resource Sharing — Tasks

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## M1 — Access control engine (backend)

- [x] **1a** Fix Analyst floor default → `AccessLevel.EDIT` in `OrgPreferences` + backfill migration
- [x] **1b** Add `KPI = "kpi"` to `ResourceType` enum (`models/resource_share.py`)
- [x] **1b** Add KPI to `RTYPES` in `shareable_types.py`
- [x] **1c** Add `parent` self-FK (nullable, CASCADE) to `ResourceShare` + migration
- [x] **1c** Fix `_grants_map` in `access_control.py` — `max_access_level` across all user + group rows; replace user-overrides-group with true max
- [x] **1c** Add `max_access_level(*levels)` utility to `models/resource_share.py`; use in `_grants_map`, `get_user_access`, `get_user_access_map`
- [x] **1c** Add `sync_dashboard_cascade(dashboard)` to `resource_share.py` — full sync of cascade children (create missing, update level, delete stale) for all direct shares on a dashboard
- [x] **1c** `resource_share.add_grants` — call `sync_dashboard_cascade` after writing concrete dashboard shares
- [x] **1c** `resource_share.update_grant` — call `sync_dashboard_cascade` when share is a dashboard share
- [x] **1c** Hook `sync_dashboard_cascade` into `dashboard_native_api.py` wherever `tabs` is saved
- [x] **1d** Replace `_require_owner_or_admin` with `_require_edit_or_admin` on all grant endpoints (`access_api.py`)
- [x] **1e** `ChartService.list_charts` — add `orguser` param; apply `accessible_filter`; annotate `access_level` via `get_user_access_map`
- [x] **1e** `charts_api.py list_charts` — pass `orguser`; include `access_level` in `ChartResponse`
- [x] **1e** `ReportService.list_snapshots` — add `orguser` param; apply `accessible_filter`; annotate `access_level`
- [x] **1e** `report_api.py list_snapshots` — pass `orguser`; include `access_level` in `SnapshotResponse`
- [x] **1e** `webapp_v2/types/charts.ts` — add `access_level?: 'view' | 'edit'`
- [x] **1e** `webapp_v2/types/reports.ts` — add `access_level?: 'view' | 'edit'`
- [x] **1e** `app/charts/page.tsx` — gate edit/share buttons on `chart.access_level === 'edit'` instead of role permission
- [x] **1e** `app/reports/page.tsx` — gate edit/delete/share buttons on `report.access_level === 'edit'`
- [x] **1f** Add `CascadeSourceSchema` to `resource_share_schema.py`
- [x] **1f** Update `ShareRowSchema` — add `cascade_sources`, make `share_id: Optional[int]`
- [x] **1f** Rewrite `list_grants` — group by principal, compute effective max, populate `cascade_sources`
- [x] **1g** Add `is_private = BooleanField(default=False)` to Dashboard, Chart, Report, KPI models + migration
- [x] **1g** Update `accessible_filter` in `access_control.py` — exclude private resources from floor-based access
- [x] **1g** Update `get_user_access` — skip floor fallback when `is_private=True` and no grant exists
- [x] **1g** Update `get_user_access_map` — skip floor fallback per resource when `is_private=True` and no grant exists
- [x] **1g** Add `PATCH /api/access/{rtype}/{resource_id}/private` endpoint — requires owner or Edit; clears public share token when setting `is_private=True`
- [x] **1h** Floor hierarchy validation in `org_preferences_api.py` PUT handler — reject if `default_member_level` rank > `default_analyst_level` rank

---

## M2 — ~~Cascade removal warning API~~ — dropped

Generic confirmation dialog in the frontend only; no backend API needed.

---

## M3 — Ownership transfer API (backend)

- [x] Add `TransferOwnershipPayload` schema to `resource_share_schema.py`
- [x] Implement `POST /api/access/{rtype}/{resource_id}/transfer-ownership` in `access_api.py`
- [x] Transfer logic in `ownership.py` — validate caller is owner/Admin; validate recipient has effective Edit via `get_user_access`; update `created_by`

---

## M4 — Request access (backend)

- [x] Add `AccessRequest` model (`models/resource_share.py` or new file)
- [x] Write migration for `AccessRequest` table
- [x] `POST /api/access/{rtype}/{resource_id}/request-access` — create request
- [x] `GET /api/access/{rtype}/{resource_id}/request-access` — list pending requests (Edit-holders only)
- [x] `POST /api/access/{rtype}/{resource_id}/request-access/{id}/respond` — approve/decline
- [x] Resource detail endpoints — return 403 (not 404) when resource exists but caller lacks access; 404 only for genuinely missing resources
- [x] `get_user_access` returns `AccessLevel.NO_ACCESS` (was `None`) when resource exists but caller has no access; `has_access` decorator uses this to raise 403 for no-access, 404 only for missing
- [x] Reuse `is_creator_or_admin` inside `get_user_access` (was duplicating the owner + admin checks); fix circular import by moving `ownership.py` off `ddpui.auth`
- [x] Notify resource owner when a new access request is created (email + in-app via `create_notification`) — includes requester email, role, requested level, note, and a deep link to open the share modal
- [x] Notify requester when their request is approved (email + in-app, with resource link)
- [x] Notify requester when their request is declined (email + in-app, with resource link)
- [x] `_resource_url` helper builds frontend URLs per rtype; KPI special-cased to `/kpis?openShare=true&kpiId={id}` since there's no `/kpis/{id}` route

---

## M5 — Invitation promotion + cleanup (backend)

- [x] Invitation promotion in `orguserfunctions.py` — on acceptance, update `ResourceShare` + `OrgUserGroupMember` rows
- [x] Group delete cleanup — `post_delete` signal on `OrgUserGroup` to delete orphan `ResourceShare` rows
- [x] Resource delete cleanup — in delete handlers for Dashboard, Chart, Report, KPI: delete `ResourceShare` + `AccessRequest` rows

---

## M6 — Cascade removal warning + KPI sharing + Private toggle (frontend)

- [x] Cascade confirmation dialog in `share-modal.tsx` — static generic warning triggered when downgrading/removing Edit on a dashboard (no API call needed)
- [x] Add ShareModal to KPI page (`app/kpis/`) with `rtype="kpi"`
- [x] Private toggle in `share-modal.tsx` — calls `PATCH /api/access/{rtype}/{resource_id}/private`; hides public sharing toggle when Private is on
- [x] Floor hierarchy enforcement in `RolesTab.tsx` — disable Member floor options that exceed Analyst's current floor

---

## M7 — Ownership transfer UI (frontend)

- [x] Add "Transfer Ownership" option to permission dropdown in share modal (owner/Admin only)
- [x] Ownership transfer confirmation dialog in `share-modal.tsx`
- [x] Add `transferOwnership` to `hooks/api/useAccess.ts`
- [x] Update `ShareRow` type in `types/access.ts` — add `cascade_sources: CascadeSource[]`, make `share_id: Optional<number>`

---

## M8 — Request access UI (frontend)

- [x] Redesign `NoAccess.tsx` — add "Request Access" button + request modal (level + note); handles 403 response from resource detail endpoints
- [x] Add request-access hooks to `hooks/api/useAccess.ts`
- [x] Add "Access Requests" section to share modal (`share-modal.tsx`) — visible to Edit-holders; approve/decline actions
- [x] `lib/api.ts` attaches `.status` to thrown errors so callers can distinguish 403 from other failures
- [x] Dashboard router (`app/dashboards/[id]/page.tsx`) renders `NoAccess` when the native API returns 403 (was falling through to the generic "Error Loading Dashboard" card)
- [x] `useOpenShareDeepLink` hook — reads `?openShare=true` on the URL, clears it (and any listed extras) on close so a refresh doesn't reopen the modal
- [x] Auto-open share modal from notification deep link on dashboard (`DashboardNativeView`), chart (`ChartDetailClient`), report (`ReportShareMenu`), and KPI list (`kpi-page.tsx` — matches `kpiId` param to a loaded row)

---

## M9 — Access badges (frontend)

- [x] Add `<AccessBadge>` component to `components/ui/`
- [x] Apply access badge to dashboard list (`dashboard-list-v2.tsx`)
- [x] Apply access badge to chart list (`app/charts/page.tsx`)
- [x] Apply access badge to reports list

Note: bulk-share (originally scoped to this milestone) was dropped from v1. See M15 for the removal.

---

## M10 — Nav restructure: Alerts + Metrics under Data (frontend)

Per `spec.md` §"Metrics & Alerts Governance": Metrics and Alerts live under the **Data** section in the sidebar, and Members must see them read-only.

Root cause: Data section had `visibleToRoles: DATA_SECTION_ROLES` (excludes Member). So Metrics was already invisible to Members despite the spec saying they should see it read-only; Alerts was top-level as a workaround.

Fix: loosen the Data parent (visible to all), push `DATA_SECTION_ROLES` onto each staff-only child (Overview, Ingest, Transform, Orchestrate, Explore, Quality); Metrics + Alerts stay unrestricted.

- [x] Move `Alerts` nav item into `Data.children` in `components/main-layout.tsx`
- [x] Remove the top-level `Alerts` entry
- [x] Drop `visibleToRoles` from Data parent
- [x] Add `visibleToRoles: DATA_SECTION_ROLES` to each staff-only Data child
- [x] Metrics + Alerts left unrestricted (backend `can_view_metrics` / `can_view_alerts` already granted to all 4 roles in the seed data — no seed change needed)

---

## M11 — Floor label rebrand (frontend only)

Rename the 3 floor options in `Settings > Access > Roles` — UI-only. Backend / API / DB continue to use `no_access` / `view` / `edit` internally.

- [x] `no_access` → "Create only"
- [x] `view` → "Create & View"
- [x] `edit` → "Create & Edit"
- [x] Update `LEVEL_LABEL` map in `components/settings/access/RolesTab.tsx`
- [x] Update spec.md to use new labels while noting underlying levels unchanged

---

## M12 — Tests (backend)

**Files:** `ddpui/tests/api_tests/test_access_api.py` (new), `ddpui/tests/api_tests/test_public_report_api.py` (stale fixture repaired + gate tests added)

### Story-by-story coverage vs test-spec

| Story | Status | Notes |
|---|---|---|
| 1 — Floor settings (F01-F09, A01-A09) | ✅ 16/18 | F08/F09 (non-Admin auth on prefs endpoint) skipped |
| 2 — Share dashboard (G01-G26, B01-B08) | ⚠️ 8/26 grants CRUD; 0/8 grant+floor max | Missing: group grants, cross-org, no_access grant reject, upsert, pending invite in list, PATCH non-existent, DELETE non-existent |
| 3 — Cascade (C01-C09, H01-H07, G12-G14, G18, G23, Q13) | ⚠️ 12/21 | Materialization + core enforcement + Q13 done. Missing: C04/C08/C09, H04, G13/G14/G18/G23 (some redundant with covered tests) |
| 4 — Chart in multiple dashboards (C03, H07, G14) | ⚠️ 2/3 | C03 + H07 done via cascade tests. G14 (two sources in list) pending |
| 5 — Member + No Access floor (B01, B03, E01-E03, E07, Q11) | ✅ 6/6 (Q11 covered under Story 16) |
| 6 — Private toggle (D01-D12, I01-I08) | ✅ 16/20 | D01-D12 done, I01/I02/I03/I05 done via general-access tests. Missing: I04, I06-I08 |
| 7 — Public link (O01-O09, Q03) | ✅ 9/10 | O07 skipped (routing note, no behavior) |
| 8 — Transfer ownership (K01-K11) | ✅ 9/11 | K08 (self no-op), K09 (cross-org) missing |
| 9 — Request access (L01-L21) | ✅ 18/21 | 3 skipped (L02/L06/L08 trivially covered by other tests) |
| 10 — External invite (M01-M04) | ✅ 4/4 |
| 11 — Cascade removal warning | N/A | Frontend-only |
| 12 — Groups (B05, B06, C08, G03, Q06-Q08) | ⚠️ 5/7 | Q07 (rename authz gap) + Q08 (Member visibility gap) marked xfail; bugs flagged in M13 |
| 13 — Bulk share (Q09) | 🚫 removed from v1 (see M15) | |
| 14 — Orphan cleanup (N01-N06) | ✅ 6/6 | Delete endpoints inline-clean ResourceShare + AccessRequest for all 4 rtypes + group |
| 15 — Comments on Reports (P01-P06) | ✅ 6/6 (audited + fixed 1 stale + added P03) |
| 16 — Edge cases (Q01, Q02, E04-E06, Q11) | ✅ 6/6 | |
| `has_access` HTTP semantics | ❌ 0 | Header of test-spec — 404 vs 403 semantics across all resource-detail endpoints |
| Allow public sharing runtime gate | ✅ 4/4 | Not story-scoped but critical — covered in `test_public_report_api.py::TestAllowPublicSharingGate` |


### Ownership transfer — spec §"Ownership transfer" lines 269–274 ✅
- [x] Owner can transfer to Analyst (Edit floor) — `test_owner_can_transfer_to_analyst_with_floor_edit`
- [x] Admin (not owner) can transfer — `test_admin_can_transfer_ownership_even_when_not_owner`
- [x] Owner → Member with direct Edit share succeeds — `test_owner_can_transfer_to_member_with_direct_edit_share`
- [x] Non-owner-non-admin blocked (spec line 270) — `test_non_owner_non_admin_cannot_transfer`
- [x] Recipient without Edit → 400 (spec line 271) — `test_transfer_to_recipient_without_edit_fails`
- [x] Non-existent recipient → 400 — `test_transfer_to_nonexistent_user_fails`
- [x] Previous owner's direct shares unchanged (spec line 273) — `test_previous_owner_direct_shares_unchanged_after_transfer`
- [x] `created_by` updated after transfer — `test_transfer_updates_created_by`

### Candidates endpoint (`GET /candidates`) ✅
- [x] 403 for non-owner-non-admin — `test_candidates_403_for_non_owner_non_admin`
- [x] Returns all org users with correct effective access levels — `test_candidates_returns_all_org_users_with_access_levels`
- [x] Direct Edit share promotes Member to Edit — `test_candidates_direct_edit_share_promotes_member`
- [x] Private resource bypasses floor — `test_candidates_private_resource_bypasses_floor`

### General access endpoint (`PATCH /general-access`) — spec §"Private toggle" line 263 ✅
- [x] Everyone → Private flips `is_private` — `test_everyone_to_private_sets_is_private`
- [x] Everyone → Public generates token + timestamps — `test_everyone_to_public_generates_token_and_timestamps`
- [x] **Public → Private clears token** (spec line 263) — `test_public_to_private_clears_token_spec_line_263`
- [x] Public → Everyone preserves token dormant + sets `public_disabled_at` — `test_public_to_everyone_keeps_token_dormant`
- [x] **Private → Everyone does NOT re-enable public** (spec line 263) — `test_private_to_everyone_does_not_reenable_public_spec_line_263`
- [x] Public request on chart → 400 (unsupported rtype) — `test_public_on_chart_fails_400`
- [x] Public blocked when `allow_public_sharing=False` → 403 — `test_public_blocked_when_org_disallows`
- [x] Non-Edit user cannot change mode → 403 — `test_non_edit_holder_cannot_change_mode`
- [x] Idempotent same-mode call — `test_idempotent_no_state_change`

### Public API `allow_public_sharing` runtime gate ✅
- [x] Dashboard 404 when org disallows — `TestAllowPublicSharingGate::test_dashboard_hidden_when_org_disallows`
- [x] Dashboard 200 when org allows — `test_dashboard_visible_when_org_allows`
- [x] Report 404 when org disallows — `test_report_hidden_when_org_disallows`
- [x] X-Render-Secret bypasses the org toggle (server-side PDF) — `test_render_secret_bypasses_org_toggle`

### Story 3 — Cascade (materialization + enforcement + read layer) ✅
- [x] **H01** Dashboard share creates cascade rows for inner chart + KPI — `test_H01_dashboard_share_materializes_cascade_rows`
- [x] **H02** Dashboard share level update propagates to cascade children — `test_H02_dashboard_share_level_update_propagates_to_children`
- [x] **H03** ON DELETE CASCADE — removing parent deletes children — `test_H03_deleting_parent_share_deletes_cascade_children`
- [x] **H05** Chart removed from tabs → cascade rows deleted on re-sync — `test_H05_chart_removed_from_tabs_deletes_cascade_row`
- [x] **H06** Direct grant survives when chart removed from dashboard — `test_H06_direct_grant_survives_when_chart_removed_from_dashboard`
- [x] **C01** Dashboard Edit share → Edit on inner chart — `test_C01_dashboard_edit_share_gives_edit_on_inner_chart`
- [x] **C02** Dashboard View share → View on inner chart — `test_C02_dashboard_view_share_gives_view_on_inner_chart`
- [x] **C05** No-access floor + cascade → chart visible — `test_C05_no_access_floor_plus_cascade_visible`
- [x] **C06** Deleting dashboard share → chart no_access — `test_C06_deleting_dashboard_share_removes_chart_access`
- [x] **C07** KPI cascade identical to chart cascade — `test_C07_kpi_cascade_same_as_chart`
- [x] **G12** Cascade-only row → `share_id=None`, `cascade_sources` populated — `test_G12_cascade_only_row_shows_share_id_null_and_source`
- [x] **C03** (Story 4) Chart in two dashboards → effective = max — `test_C03_chart_in_two_dashboards_effective_access_is_max`
- [x] **H07** (Story 4) Delete one dashboard share → still accessible via other — `test_H07_chart_in_two_dashboards_survives_one_share_deletion`
- [x] **Q13** PATCH cascade row rejected — `test_Q13_patch_directly_on_cascade_row_rejected`

### Still-pending in Story 3/4
- [ ] C04 (cascade + permissive floor → max) — trivially covered by C03 + max logic
- [ ] C08 (group cascade — same for group members) — depends on group tests
- [ ] C09 (`accessible_filter` cascade includes chart)
- [ ] H04 (chart added to tabs → new cascade row per existing share)
- [ ] G13 (direct + cascade merged → one row at max level)
- [ ] G14 (two cascade sources listed when chart in two dashboards)
- [ ] G18 (PATCH dashboard share → cascade children reflect new level — covered by H02, but also as API test)
- [ ] G23 (Delete dashboard share → chart inaccessible — covered by C06)

### Story 7 — Public link (O01-O09, Q03) ✅ 9/10
- [x] **O01** Public link enabled + org allow → anonymous 200 — `test_O01_dashboard_with_public_link_and_org_allow_returns_200`
- [x] **O02** Resource public link disabled → anonymous 404 — `test_O02_dashboard_public_link_disabled_returns_not_found`
- [x] **O03** Org toggle off → existing links 404 — `TestAllowPublicSharingGate::test_dashboard_hidden_when_org_disallows`
- [x] **O04** Org toggle back on → tokens still valid — `test_O04_org_toggle_off_then_on_token_still_valid`
- [x] **O05** Private=True + active link → link cleared → 403/404 — `test_access_api.py::test_public_to_private_clears_token_spec_line_263`
- [x] **O06** Private=False after link cleared → link NOT restored — `test_access_api.py::test_private_to_everyone_does_not_reenable_public_spec_line_263`
- [x] **O08** Enable public on Chart → 400/404 — `test_access_api.py::test_public_on_chart_fails_400`
- [x] **O09** Enable public when org disallows → 403 — `test_access_api.py::test_public_blocked_when_org_disallows`
- [x] **Q03** Public dashboard inner chart metadata → anonymously visible — `test_Q03_public_dashboard_inner_chart_metadata_accessible_anonymously`

**Skipped: O07** (authenticated user opens public URL → normal permission resolution). This is a routing note — anonymous endpoints don't do auth, so an authenticated caller hitting a public URL still gets the public response. No behavior to test.

### Story 10 — External user invite → promotion (M01-M04) ✅ 4/4
- [x] **M01** Pending ResourceShare promoted on accept — `test_M01_pending_resource_share_promoted_on_invite_accept`
- [x] **M02** Pending group membership promoted on accept — `test_M02_pending_group_membership_promoted_on_invite_accept`
- [x] **M03** Promoted share gives effective access — `test_M03_promoted_share_gives_effective_access`
- [x] **M04** Pending invite appears in grants list with status=pending — `test_M04_pending_invite_appears_in_grants_list_with_pending_status`

### Story 15 — Comments on Reports (P01-P06) ✅ audited + 2 gaps filled
- [x] **P01** View-holder creates comment — covered by `test_report_permissions.py::test_super_admin_can_create_comment` + guest denied tests
- [x] **P02** View-holder reads comments — covered by `test_guest_can_list_comments`
- [x] **P03** Edit-holder moderates → deletes another user's comment — `test_comment_service_mutations.py::TestDeleteComment::test_edit_holder_can_moderate_P03` (new)
- [x] **P04** View-holder cannot delete another user's comment — `TestDeleteComment::test_view_holder_non_author_raises_P04` (fixed from stale test that asserted admin also can't delete — that's no longer true after P03)
- [x] **P05** Anonymous cannot comment — no anonymous comment endpoint exists (by design)
- [x] **P06** No-access user tries — covered by has_access decorator + existing guest denied tests

### Story 5 — Member + No-access floor (B01, B03, E01-E03, E07) ✅ 6/6
- [x] **B01** Edit grant + no-access floor → Edit — `test_B01_edit_grant_on_no_access_floor_returns_edit`
- [x] **B03** View grant + no-access floor → View — `test_B03_view_grant_on_no_access_floor_returns_view`
- [x] **E01** No-access floor, no grants, not owner → empty list — `test_E01_no_floor_no_grants_no_ownership_empty_list`
- [x] **E02** No-access floor + direct grant → only granted resource — `test_E02_no_floor_direct_grant_shows_only_granted`
- [x] **E03** No-access floor + owner → own resource visible — `test_E03_no_floor_owner_sees_own_resources`
- [x] **E07** No-access floor + cascade grant → chart visible — `test_E07_no_floor_cascade_grant_shows_chart`

### Story 12 — Groups (B05, B06, C08, G03, Q06-Q08) ✅ 5/7 (2 xfail — bugs found)
- [x] **B05** User in group with Edit + no-access floor → Edit — `test_B05_user_in_group_edit_grant_no_access_floor_gets_edit`
- [x] **B06** User in two groups (Edit + View) → max Edit — `test_B06_user_in_two_groups_gets_max_level`
- [x] **C08** Group dashboard share → cascade to members — `test_C08_group_dashboard_share_cascades_to_members`
- [x] **G03** Owner adds grant for a group — `test_G03_owner_adds_grant_for_group`
- [x] **Q06** Member cannot create a group — `test_Q06_member_cannot_create_group`
- 🐛 **Q07** Non-creator Analyst rename bug — **xfail**, see M13
- 🐛 **Q08** Group visibility by role bug — **xfail**, see M13

### Story 16 — Edge cases (Q01, Q02, E04-E06, Q11) ✅ 6/6
- [x] **Q01** Edit cascade does not confer delete — `test_Q01_cascade_edit_does_not_confer_delete`
- [x] **Q02** Derived Edit (cascade only) confers re-share rights — `test_Q02_cascade_edit_confers_reshare_rights`
- [x] **E04** Floor=View → all non-private resources returned — `test_E04_floor_view_returns_all_non_private_resources`
- [x] **E05** Floor=View + private → private excluded — `test_E05_private_resource_excluded_from_floor_only_list`
- [x] **E06** Admin → all resources including private — `test_E06_admin_sees_all_resources_including_private`
- [x] **Q11** `accessible_filter` handles created_by=None without error — `test_Q11_accessible_filter_handles_orphan_created_by`

### Story 1 — Floor settings + access engine (F01-F09, A01-A09) ✅ 16/18
- [x] **F01** Valid Member=View, Analyst=Edit — `test_F01_valid_member_view_analyst_edit`
- [x] **F02** Both No Access (equal) — `test_F02_valid_both_no_access`
- [x] **F03** Both View (equal) — `test_F03_valid_both_view`
- [x] **F04** Both Edit (equal) — `test_F04_valid_both_edit`
- [x] **F05** Invalid Analyst=NoAccess < Member=View → 400 — `test_F05_invalid_member_view_analyst_no_access`
- [x] **F06** Invalid Analyst=View < Member=Edit → 400 — `test_F06_invalid_member_edit_analyst_view`
- [x] **F07** Invalid Analyst=NoAccess < Member=Edit → 400 — `test_F07_invalid_member_edit_analyst_no_access`
- [x] **A01** Analyst default floor Edit → Edit — `test_A01_analyst_gets_edit_from_default_floor`
- [x] **A02** Member default floor View → View — `test_A02_member_gets_view_from_default_floor`
- [x] **A03** Member floor=NoAccess → no_access — `test_A03_member_no_access_floor_returns_no_access`
- [x] **A04** Analyst floor=NoAccess → no_access — `test_A04_analyst_no_access_floor_returns_no_access`
- [x] **A05** Admin bypasses floor → Edit — `test_A05_admin_always_gets_edit_regardless_of_floor`
- [x] **A06** Missing OrgPreferences → model defaults — `test_A06_missing_orgpreferences_defaults_to_model_defaults`
- [x] **A07** Creator bypasses floor → Edit — `test_A07_creator_always_gets_edit_regardless_of_floor`
- [x] **A08** Floor change is immediate — `test_A08_floor_change_takes_immediate_effect`
- [x] **A09** Missing resource returns None (distinct from no_access) — `test_A09_missing_resource_returns_none_not_no_access`

**Skipped:** F08, F09 (non-Admin cannot PUT/GET) — depends on `@has_permission("can_manage_access_defaults")` decorator, which the `mock_request` seeds correctly; would only test the decorator wiring, not spec-critical.

### Story 6 — Private toggle enforcement (D01-D12) ✅ 12/12
- [x] **D01** Private + View floor → no_access — `test_D01_private_plus_view_floor_no_access`
- [x] **D02** Private + Edit floor → no_access (floor still bypassed) — `test_D02_private_plus_edit_floor_no_access`
- [x] **D03** Private + direct Edit grant → Edit — `test_D03_private_plus_direct_edit_grant_gives_edit`
- [x] **D04** Private + direct View grant → View — `test_D04_private_plus_direct_view_grant_gives_view`
- [x] **D05** Private + cascade Edit → Edit — `test_D05_private_plus_cascade_edit_grant_gives_edit`
- [x] **D06** Owner sees own private resource → Edit — `test_D06_private_plus_owner_edit`
- [x] **D07** Admin sees any private resource → Edit — `test_D07_private_plus_admin_edit`
- [x] **D08** `accessible_filter` excludes private when floor-only — `test_D08_accessible_filter_excludes_private_when_only_floor`
- [x] **D09** `accessible_filter` includes private with direct grant — `test_D09_accessible_filter_includes_private_with_direct_grant`
- [x] **D10** `accessible_filter` includes private via cascade — `test_D10_accessible_filter_includes_private_via_cascade`
- [x] **D11** `accessible_filter` includes private when owner — `test_D11_accessible_filter_includes_private_when_owner`
- [x] **D12** `get_user_access_map` returns None for private without access — `test_D12_get_user_access_map_private_no_grant_is_none`

### Story 9 — Request access (L01-L21) ✅ 18/21
- [x] **L01** No-access user requests View → 201, request created — `test_L01_no_access_user_can_request_view`
- [x] **L03** User with access → 409 — `test_L03_user_with_access_cannot_request`
- [x] **L04** Duplicate pending → 409 — `test_L04_duplicate_pending_request_rejected`
- [x] **L05** Missing resource → 404 — `test_L05_request_on_missing_resource_returns_404`
- [x] **L07** Owner lists pending — `test_L07_owner_lists_pending_requests`
- [x] **L09** View-holder cannot list → 403 — `test_L09_view_only_holder_cannot_list_requests`
- [x] **L10** No pending → empty list — `test_L10_empty_list_when_no_pending`
- [x] **L11** Approve → grant created + request approved — `test_L11_approve_creates_grant`
- [x] **L12** Approve with downgrade to View — `test_L12_approve_can_downgrade_to_view`
- [x] **L13** Decline → no grant + request declined — `test_L13_decline_creates_no_grant`
- [x] **L14** View-holder cannot respond → 403 — `test_L14_view_holder_cannot_respond`
- [x] **L15** Respond to nonexistent → 404 — `test_L15_respond_to_nonexistent_request`
- [x] **L16** Respond to already-decided → 409 — `test_L16_respond_to_already_decided_request`
- [x] **L17** Create → owner notified (email + in-app) — `test_L17_owner_notified_on_new_request`
- [x] **L18** Approve → requester notified — `test_L18_requester_notified_on_approve`
- [x] **L19** Decline → requester notified — `test_L19_requester_notified_on_decline`
- [x] **L20** Orphan resource → owner notification skipped, request lands — `test_L20_orphan_resource_skips_owner_notification`
- [x] **L21** Notification failure doesn't fail the API — `test_L21_notification_failure_does_not_fail_api_call`

**Skipped (trivially covered):** L02 (Edit-level request, same code path as L01), L06 (cross-org, same 404 branch as L05), L08 (Edit-holder lists, same auth gate as owner)

### Story 14 — Orphan cleanup (N01-N06) ✅
- [x] **N01** Dashboard delete → ResourceShare + AccessRequest cleaned — `test_N01_dashboard_delete_removes_all_grants_and_requests`
- [x] **N02** Chart delete → ResourceShare + AccessRequest cleaned — `test_N02_chart_delete_removes_all_grants`
- [x] **N03** Report delete → ResourceShare + AccessRequest cleaned — `test_N03_report_delete_removes_all_grants_and_requests`
- [x] **N04** KPI delete → ResourceShare + AccessRequest cleaned — `test_N04_kpi_delete_removes_all_grants`
- [x] **N05** Group delete → group-share rows cleaned — `test_N05_group_delete_removes_group_share_rows`
- [x] **N06** Group member removed → member loses group-derived access — `test_N06_group_member_removed_loses_group_access`

### Grants CRUD — spec §"Roles" line 261 (re-sharing rules) ✅
- [x] `GET /grants` populates `owner` field with email + role_name — `test_grants_response_populates_owner_field`
- [x] `owner=null` on orphan resource — `test_grants_response_owner_null_on_orphan`
- [x] `caller_is_owner=True` when caller is the owner — `test_grants_caller_is_owner_true_for_owner`
- [x] `caller_is_owner=False` for admin who isn't the owner — `test_grants_caller_is_owner_false_for_admin_not_owner`
- [x] View-holder gets 403 on list — `test_grants_403_for_view_only_holder`
- [x] `general_access` state embedded in response — `test_grants_includes_general_access_state`
- [x] `POST /grants` adds user principal share row — `test_add_user_grant_creates_share_row`
- [x] **Edit-holder (non-owner, non-admin) can re-share** (spec line 261) — `test_edit_holder_can_reshare_spec_line_261`
- [x] View-holder cannot add grants → 403 — `test_view_holder_cannot_add_grants`
- [x] `PATCH /grants/{id}` changes access level — `test_update_grant_changes_access_level`
- [x] View-holder cannot update grant → 403 — `test_view_holder_cannot_update_grant`
- [x] `DELETE /grants/{id}` removes share row — `test_remove_grant_deletes_share_row`
- [x] View-holder cannot delete grant → 403 — `test_view_holder_cannot_remove_grant`

### Bugs found + fixed while writing tests
- [x] `_org_floor` fallback returned `View` for missing OrgPreferences row, diverging from model defaults (`Analyst=Edit`, `Member=View`). Fixed: use in-memory `OrgPreferences()` instance so field defaults apply uniformly. Same fix applied to `get_access_map_for_resource` and `_general_access_state`.
- [x] Stale fixture in `test_public_report_api.py::public_snapshot` used deleted `toggle_report_sharing` — migrated to unified `update_general_access` endpoint.

### Still to do
- [ ] `ddpui/tests/core/test_access_control.py` — unit tests for `get_user_access`, `get_user_access_map`, `accessible_filter` (floor, direct grants, cascade max, admin override, NO_ACCESS floor edge cases, Private toggle bypasses floor)
- [ ] Request access tests — POST creates, duplicate → 409, approve/decline flows
- [ ] Notification tests — owner notified on create; requester notified on approve/decline; failure isolation; orphan skips owner
- [ ] Private toggle enforcement tests — private resource invisible to floor-based access; explicit grantee still has access (already partially covered above, but needs enforcement-side coverage)
- [ ] Floor hierarchy validation — Member floor > Analyst floor → 400 (in org preferences update)
- [ ] Audit log — fires only on `is_public` change, not on private/everyone toggle
- [ ] Pending-email grants (invite flow) — `POST /grants` with `pending_grants`, creates `Invitation`, promotes on acceptance
- [ ] Group grants — `POST /grants` with `principal_type=group`, cascade to members

---

## M13 — Follow-ups (uncovered / discovered during testing)

- [x] **Spec docs** — updated `test-spec.md` (has_access semantics section, A03/A04/A08/C06/D01/D02 expected values, Story 9 notification rows L17-L21, deep-link frontend behavior) and `spec.md` (EffectivePermission "invisible" language)
- [x] **Story 15 P03** — Edit-holder can moderate (delete) another user's comment on a report; `comment_service.py:delete_comment` now allows author OR any Edit-holder on the parent report. `update_comment` intentionally stays author-only (rewriting others' words is not moderation).
- [ ] **Story 4** — verify (manually or via test) chart in multiple dashboards → effective access = max
- [ ] **Story 16 Scenario 2** — verify direct-grant + higher-cascade blocks the direct-grant downgrade with the correct toast message
- [ ] **Story 14** — resource / group delete orphan-cleanup: manual verification or dedicated test
- [ ] **`has_permission` decorator returns 404 on 403** — `auth.py:40-59` has `try/except:` that catches its own `HttpError(403, "not allowed")` and re-raises as `HttpError(404, UNAUTHORIZED)`. Semantically wrong: unauthorized should be 403, not 404. Frontend can't distinguish "missing" from "not permitted". Discovered while writing Q01. Fix: remove the outer `try/except` and let the 403 propagate.
- [ ] **Group edit endpoints missing creator/admin check** — spec line 206: "Only the group's creator and Admins can edit (membership, rename) or delete a group." Only `delete_user_group` has this check. `rename_user_group`, `add_user_group_members`, `remove_user_group_member` all skip it. Any Analyst with `can_edit_user_group` can currently rename/modify another Analyst's group. Test: `test_Q07_non_creator_analyst_cannot_rename_another_analysts_group` (xfail, strict). Fix: add `is_creator_or_admin(orguser, group)` gate to those 3 endpoints.
- [ ] **Members can't view any groups** — `list_user_groups` is gated on `can_view_user_groups`; Member role lacks it → get 404 UNAUTHORIZED. Spec line 206 says "Member sees only their own groups" implying they CAN see groups they're in. Test: `test_Q08_group_visibility_by_role` (xfail, strict). Decide: (a) grant Members the perm + add visibility filter, or (b) update spec to say Members can't view.
- [ ] **`test_report_permissions.py` pre-existing failures** — RESOLVED by agent-parallel `positional → kwargs` conversion (see M14).

---

## M14 — CI test cleanup (backend + frontend)

### Backend — positional-arg failures fixed via 6 parallel agents ✅

Root cause: several endpoints adopted the `@has_access(...)` decorator that reads `resource_id` from `kwargs` only. Tests calling endpoints with positional args (`func(request, id)`) failed with `HttpError(400, "missing resource id for {rtype}")`.

Files fixed (~80 tests total, converted to `func(request, id_kwarg=id)`):

- [x] `test_charts_api.py` — 4 tests fixed, 41/41 passing
- [x] `test_dashboard_native_api.py` — 10 tests fixed, 40/40 passing
- [x] `test_kpi_api.py` — 9 tests fixed, 17/17 passing
- [x] `test_report_api.py` — 19 tests fixed, 31/31 passing
- [x] `test_report_permissions.py` — 19 tests fixed, 36/36 passing
- [x] `test_comment_api.py` — 26/28 fixed; 2 semantic-drift stales also updated:
  - `test_snapshot_not_found` — was expecting 400, updated to 404 per `has_access` decorator spec §"HTTP status semantics"
  - `test_delete_other_forbidden` — was using Admin (Edit-holder, now moderates per Story 15 P03); replaced with Analyst + View-only floor to still exercise the "View-holder cannot moderate" branch

### Backend — service-signature drift ✅

`ReportService.list_snapshots` and `KPIService.list_kpis` gained a required `orguser` parameter (for `accessible_filter` integration). Tests calling them without `orguser` failed with `TypeError`.

- [x] `test_report_service.py::TestListSnapshots` — 6 tests updated to pass `orguser`
- [x] `test_kpi_service.py::TestKPICRUD::test_list_kpis*` — 3 tests updated to pass `orguser`

### Backend CI now green ✅

- Before: 90 failed, 2 errors, 2336 passed
- After: **0 failed, 0 errors, 2436 passed**, 2 skipped, 2 xfailed (Q07 + Q08 bug docs)
- Coverage: 64% (CI gate `--fail-under=55` → passes)

### Frontend — stale test cleanup ✅

Root cause: several endpoints/hooks were removed when public/private consolidated into `PATCH /general-access`; some tests still referenced them.

- [x] `hooks/__tests__/useReports.test.ts` — removed 6 stale sharing tests (`updateReportSharing`, `getReportSharingStatus` no longer exist)
- [x] `components/reports/__tests__/ReportShareModal.test.tsx` — **deleted**; every test used old `getShareStatus` / `updateSharing` props that no longer exist on `ShareModal`. Rewriting requires mocking ~6 hooks (`useResourceGrants`, `useAccessRequests`, `usePeople`, `useUserGroups`, `useRoles`, `useAuthStore`) — flagged as follow-up gap
- [x] `components/reports/__tests__/reports-page.test.tsx` — added `access_level: 'edit'` to `createMockSnapshot` (Delete menu item is now gated on it); extended `next/navigation` mock with `usePathname` + `useSearchParams` (rendering `ReportShareMenu` needed them)
- [x] `components/__tests__/main-layout.test.tsx` — updated 2 stale assertions:
  - Data section now visible to Members (per resource-sharing spec §"Metrics & Alerts Governance")
  - "User Management" nav renamed to "Access" and gated on `ACCESS_PAGE_ROLES` (includes Analyst)

### Frontend — pre-existing flake fixed ✅

- [x] `components/dashboard/__tests__/text-element-unified.test.tsx::flushes active rich-text changes` — was dropping first 2 chars of typed text on CI. Fixed by switching `fireEvent.click` → `user.click` (properly awaits focus) and adding a microtask yield before typing so ProseMirror can attach key handlers. Not caused by resource-sharing work.

### Frontend follow-ups

- [ ] **`ReportShareModal.test.tsx` rewrite** — the new `ShareModal` (general-access section, transfer, request-access) has no unit tests. Recommend Playwright/e2e for that surface rather than mocking 6 hooks.
- [ ] **Pre-existing frontend failures (unrelated to resource-sharing):**
  - `components/charts/__tests__/DataPreview.test.tsx` × 2 — number formatting (`1,234,567.89`); locale-dependent, may pass on CI's Linux locale
  - `components/pipeline/orchestrate/__tests__/pipeline-run-history.test.tsx` — dialog close/reopen, AI summary

---

## M15 — Scope cut: remove bulk-share + 3-dot Transfer Ownership

Decision (2026-08-18): drop bulk-share entirely from v1, and remove the Transfer Ownership entry point from the list-page 3-dot menu for dashboards, charts, KPIs, and reports. Transfer lives in the row-level "…" inside the ShareModal (View / Edit / **Transfer ownership**). Alerts don't have a ShareModal, so their 3-dot Transfer entry point (currently unwired) is the intended future home for alerts.

### Spec docs updated ✅

- [x] `spec.md` — removed "Bulk sharing from resource lists" section; dropped "multi-select with bulk Share action" from the Resource list pages row of the UI Surface table
- [x] `plan.md` — removed M9 Bulk Share notes; removed frontend-gap #6 (bulk share); removed bulk-share validation-checklist scenario (renumbered)
- [x] `test-spec.md` — removed Story 13 (bulk share)
- [x] `tasks.md` — retitled M9 to "Access badges"; marked Story 13 removed in coverage matrix; deleted Story 13 improvements line from M13

### Frontend — bulk-share removal ✅

- [x] `app/charts/page.tsx` — removed `bulkShareOpen/Email/Level` state, `handleBulkShare`, selection-bar Share button, bulk-share Dialog, and unused `Dialog*` imports; kept bulk-delete
- [x] `components/dashboard/dashboard-list-v2.tsx` — removed all selection-mode state (`isSelectionMode`, `selectedDashboards`, `bulkShare*`), `exitSelectionMode`, `toggleDashboardSelection`, `handleBulkShare`, row checkbox, header "Bulk Share" button, selection bar, bulk-share Dialog
- [x] `hooks/api/useAccess.ts` — deleted `bulkAddGrant` export (no remaining callers)

### Frontend — 3-dot Transfer Ownership removal ✅

- [x] `components/dashboard/dashboard-list-v2.tsx` — removed `transferDashboard` state, `canTransfer`/`isAdmin`, `<TransferOwnershipDialog>` invocation, DropdownMenu item, `ADMIN_ROLES` import, `TransferOwnershipDialog` import
- [x] `app/charts/page.tsx` — same cleanup for `transferChart` + `canTransferChart`; removed `useAuthStore` import (unused after)
- [x] `components/kpis/kpi-page.tsx` — removed `transferKpi` state + `canTransferKpi`; dropped `onTransfer`/`canTransfer` props from `KPICardWithData`; dropped `<User> Transfer ownership` DropdownMenu item; removed `TransferOwnershipDialog`, `ADMIN_ROLES`, `useAuthStore` imports
- [x] `app/reports/page.tsx` — removed `transferSnapshot`, `canTransferSnapshot`, `isAdmin`, `TransferOwnershipDialog` invocation, DropdownMenu item, `useAuthStore` + `ADMIN_ROLES` imports
- [x] `components/ui/transfer-ownership-dialog.tsx` — component intentionally kept (future alerts 3-dot wire-up; also still consumed by `share-modal.tsx` row-level transfer flow)

### Tests ✅

- [x] Frontend jest suite — 148 / 150 suites pass, 1604 tests pass (2 failing suites are pre-existing locale-dependent flakes on macOS, unchanged by this scope cut)
- [x] Backend `test_access_api.py` — 121 passed, 2 xfail (bugs previously flagged in M13)
- No new tests referenced bulk-share or 3-dot Transfer; no test updates required

---

## M16 — Alert transfer ownership (dedicated to alert domain)

Alerts don't participate in the resource-sharing engine (no per-alert grants, no rtype registration). Transfer for alerts is a first-class alert-domain endpoint, gated on role permissions rather than resource-sharing access. Placed in the row-level 3-dot menu since alerts don't have a ShareModal.

### Backend ✅

- [x] `AlertService.transfer_ownership(alert_id, org, caller, to_orguser_id)` — creator-or-admin gate on caller; recipient must be in same org and hold `can_edit_alerts` via role; self-transfer is a no-op
- [x] `AlertService.list_transfer_candidates(alert_id, org, caller)` — same gate on caller; returns org users whose role holds `can_edit_alerts`, excluding the current owner
- [x] `POST /api/alerts/{alert_id}/transfer-ownership/` — payload `{to_orguser_id}`, returns updated `AlertResponse`, emits an `AuditLogAction.UPDATE` audit row with `transferred_to`
- [x] `GET /api/alerts/{alert_id}/transfer-candidates/` — returns `{candidates: [{orguser_id, email, role_name}]}`
- [x] Schema: `AlertListItem` + `AlertResponse` gain `created_by_email` (feeds frontend owner-or-admin gate); new `AlertTransferCandidate` / `AlertTransferCandidatesResponse` / `AlertTransferOwnershipPayload`
- [x] Query eager-load: `select_related("created_by__user")` on `get_alert` + `list_alerts`

### Frontend ✅

- [x] `hooks/api/useAlerts.ts` — `transferAlertOwnership(alertId, toOrguserId)` + `useAlertTransferCandidates(alertId)`
- [x] `components/alerts/AlertTransferOwnershipDialog.tsx` — 2-step transfer (candidate picker → confirm) modeled on the shareable-resource dialog, but tailored: no `access_level` gating, no `is_owner` filter (candidates endpoint already excludes owner)
- [x] `components/alerts/AlertsTable.tsx` — `canTransfer(a)` + `onTransfer(a)` props; Transfer Ownership 3-dot item between "Alert log" and Delete separator
- [x] `app/alerts/page.tsx` — owner-or-admin gate via `useAuthStore` + `ADMIN_ROLES`; wires the dialog
- [x] `types/alerts.ts` — `AlertListItem` + `AlertResponse` gain `created_by_email`

### Tests ✅

Backend `test_alert_api.py`: 47 passed (38 baseline + 9 new):
- [x] `test_transfer_candidates_lists_edit_alert_roles_only` — members excluded (no `can_edit_alerts`); owner excluded
- [x] `test_transfer_candidates_non_owner_analyst_forbidden` — 403 when caller is neither owner nor admin
- [x] `test_transfer_ownership_owner_can_transfer_to_analyst` — happy path
- [x] `test_transfer_ownership_admin_can_transfer_others_alert` — admin acting on someone else's alert
- [x] `test_transfer_ownership_non_owner_analyst_forbidden` — 403
- [x] `test_transfer_ownership_recipient_without_edit_alerts_rejected` — 400 (member lacks `can_edit_alerts`)
- [x] `test_transfer_ownership_unknown_recipient_rejected` — 400
- [x] `test_transfer_ownership_self_noop` — no error, `created_by` unchanged
- [x] `test_transfer_ownership_not_found` — 404

Frontend `AlertsTable.test.tsx` updated with `canTransfer` / `onTransfer` in `baseProps` and `created_by_email` on the fixture — 11 / 11 pass.
