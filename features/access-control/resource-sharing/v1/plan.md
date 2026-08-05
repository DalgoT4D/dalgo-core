# Resource Sharing — Implementation Plan

## Context
The resource sharing spec (features/access-control/resource-sharing/spec.md) is fully locked. The DB schema and core infrastructure (models, grants API, groups API, share modal, Settings > Access) are already built. This plan covers everything still needed to bring the feature to spec.

---

## Current state snapshot

### Backend — built
| What | Where |
|---|---|
| ResourceShare, OrgUserGroup, OrgUserGroupMember models | `ddpui/models/resource_share.py`, `org_user.py` |
| OrgPreferences floor fields (`default_analyst_level`, `default_member_level`, `allow_public_sharing`) | `ddpui/models/org_preferences.py` |
| `access_control.py` — floor + direct grants (no cascade yet) | `ddpui/core/access/access_control.py` |
| Grants API: CRUD `GET/POST/PATCH/DELETE /api/access/{rtype}/{resource_id}/grants` | `ddpui/api/access_api.py` |
| Groups API: CRUD + members `GET/POST/PUT/DELETE /v1/organizations/user_groups/…` | `ddpui/api/user_org_api.py` |
| Org floor settings API `GET/PUT /api/orgpreferences/` | `ddpui/api/org_preferences_api.py` |
| Public links — Dashboard + Report | `ddpui/api/dashboard_native_api.py`, `report_api.py` |
| shareable_types registry — Dashboard, Chart, Report | `ddpui/core/access/shareable_types.py` |
| Pending email → Invitation flow | `ddpui/core/access/resource_share.py` |

### Frontend — built
| What | Where |
|---|---|
| Share modal (full: users/groups/emails, permission picker, pending invites, public toggle) | `components/ui/share-modal.tsx` |
| Settings > Access — People, Groups, Roles tabs | `components/settings/access/AccessPage.tsx` + tab components |
| Groups management (create/edit/delete dialogs) | `components/settings/access/Create/EditGroupDialog.tsx` |
| Roles tab — org floor 3-way toggle + Allow public sharing toggle | `components/settings/access/RolesTab.tsx` |
| API hooks | `hooks/api/useAccess.ts` |
| Public link views | `app/share/dashboard/[token]/`, `app/share/report/[token]/` |
| Dashboard + Chart sharing (share modal wired) | `dashboard-native-view.tsx`, `charts/page.tsx` |

---

## What's missing / broken

### Backend gaps
1. **Analyst floor default is "view" — spec requires "edit"** (`OrgPreferences.default_analyst_level` model default)
2. **KPI not in shareable_types** — KPI model ID: `ddpui/models/metric.py` KPI class; must be added to `ResourceType` enum and `RTYPES` dict
3. **Cascade missing** — `access_control.py` doesn't account for parent dashboard shares on Chart/KPI resources; cascade rows not created on dashboard share write
4. **Chart list and Report list don't apply `accessible_filter`** — `ChartService.list_charts` and `ReportService.list_snapshots` are not orguser-scoped
5. **Re-sharing gate is owner-or-admin only** — spec says Edit-holders should also be able to re-share; `access_api.py` uses `_require_owner_or_admin` for all grant endpoints
6. **Cascade removal warning API** — no endpoint to preview which users/charts would be affected before removing Edit from a dashboard grant
7. **Ownership transfer API** — no endpoint
8. **Request access** — no model, no API
9. **Invitation promotion on acceptance** — ResourceShare rows with `invitation_id` are not updated when the invited user accepts (joins as OrgUser)
10. **Orphan cleanup** — ResourceShare rows not deleted when a resource or group is deleted

### Frontend gaps
1. **KPI sharing** — no ShareModal on the KPI page
2. **Cascade removal warning dialog** — no confirmation before removing Edit from a dashboard
3. **Ownership transfer UI** — not in share-modal.tsx
4. **Request access flow** — NoAccess screen is a stub (`components/common/NoAccess.tsx` has no request button)
5. **Access requests section** — share modal doesn't show pending requests for the owner to approve/decline
6. **Bulk Share** — charts and dashboards have bulk-delete but no bulk-share
7. **Visual access badges** — resource list items don't display View/Edit/Owner badges

---

## Cascade design — self-FK on ResourceShare

Dashboard stores inner chart/KPI IDs in `Dashboard.tabs` (JSONField). Scanning that JSON on every read is O(n dashboards) — too expensive. Instead, cascade is **materialized** in `ResourceShare` via a self-referential FK.

### Schema change
```python
# ddpui/models/resource_share.py
parent = models.ForeignKey(
    'self',
    null=True, blank=True,
    on_delete=models.CASCADE,   # delete parent → children auto-deleted
    related_name='children'
)
```

One new migration required.

### Row anatomy

| id | rtype | resource_id | principal | level | parent_id |
|---|---|---|---|---|---|
| 1 | dashboard | D1 | User X | edit | NULL ← direct |
| 2 | chart | C1 | User X | edit | 1 ← cascade |
| 3 | chart | C2 | User X | edit | 1 ← cascade |
| 4 | dashboard | D2 | User X | view | NULL ← direct |
| 5 | chart | C1 | User X | view | 4 ← cascade from 2nd dashboard |

- Rows 2 & 3 created automatically when Row 1 is created.
- Removing Row 1 (dashboard share) → DB CASCADE auto-deletes Rows 2 & 3.
- Updating Row 1 level → also update `ResourceShare.objects.filter(parent=row1).update(access_level=new_level)`.
- Chart C1 appears in Rows 2 and 5 (two dashboards). Effective = max → Edit.

### JSON parse helper (write-time only, not read-time)

```python
def _inner_ids_from_dashboard(dashboard) -> dict:
    """Parse tabs JSON once at write-time → {chart_ids: [...], kpi_ids: [...]}"""
    chart_ids, kpi_ids = [], []
    for tab in (dashboard.tabs or []):
        for comp in tab.get("components", {}).values():
            cfg = comp.get("config", {})
            if comp.get("type") == "chart" and cfg.get("chartId"):
                chart_ids.append(int(cfg["chartId"]))
            elif comp.get("type") == "kpi" and cfg.get("kpiId"):
                kpi_ids.append(int(cfg["kpiId"]))
    return {"chart_ids": list(set(chart_ids)), "kpi_ids": list(set(kpi_ids))}
```

Lives in `ddpui/core/access/resource_share.py`. Called only when a dashboard share is created/updated, or when a chart/KPI is added to/removed from a dashboard.

### Triggers for cascade row maintenance

| Event | Action |
|---|---|
| Dashboard share **created** | `_inner_ids_from_dashboard(dashboard)` → create child rows for all chart/KPI IDs |
| Dashboard share **level updated** | `ResourceShare.objects.filter(parent=share).update(access_level=new_level)` |
| Dashboard share **deleted** | DB CASCADE handles children automatically |
| Chart/KPI **added to dashboard** | For each existing dashboard share, create one child row pointing at the new component |
| Chart/KPI **removed from dashboard** | Delete child rows where `parent_id IN [dashboard's share IDs]` for that component ID |

The last two events are hooked into the dashboard update/tile API (wherever `dashboard.tabs` is saved).

### `list_grants` — one row per principal, backend-resolved

`list_grants(org, rtype, resource_id)` fetches all `ResourceShare` rows for the given resource (direct + cascade), groups them by `(principal_type, principal_id)` in Python, and returns **one `ShareRowSchema` per principal** with:
- `access_level` = max level across all rows for that principal
- `share_id` = the direct share row's ID if one exists (used by frontend for PATCH/DELETE); `None` if the principal only has cascade rows
- `cascade_sources` = list of `{dashboard_id, dashboard_title}` for each cascade row

Response schemas (in `ddpui/schemas/access/resource_share_schema.py`):
```python
class CascadeSourceSchema(Schema):
    dashboard_id: int
    dashboard_title: str

class ShareRowSchema(Schema):
    share_id: Optional[int]        # direct share row ID; None = cascade-only
    principal_type: str
    principal_id: Optional[int]
    email: Optional[str]
    label: str
    role_or_group: Optional[str]
    access_level: str              # effective max across direct + cascade
    status: str                    # active | pending
    cascade_sources: list[CascadeSourceSchema]  # empty = direct-only
```

Frontend impact (additive changes to existing files):
- `webapp_v2/types/access.ts` — add `cascade_sources: CascadeSource[]` to `ShareRow`
- `webapp_v2/components/ui/share-modal.tsx` — `cascade_sources.length > 0` → show "via Dashboard X"; disable level dropdown

### `_grants_map` fix in access_control.py

Currently user rows overwrite each other (last write wins). With multiple cascade rows per resource, change to **take max across all rows** for the same `(principal_type, principal_id, resource_id)`:

```python
# Before (wrong with cascade):
user_levels[row.resource_id] = row.access_level

# After:
current = user_levels.get(row.resource_id)
if current is None or LEVEL_RANK[row.access_level] > LEVEL_RANK[current]:
    user_levels[row.resource_id] = row.access_level
```

---

## Milestones

### M1 — Access control engine: cascade + KPI + list filters + bugs (backend)

**All logic fixes before any new features.**

#### 1a. Fix Analyst floor default
- `ddpui/models/org_preferences.py`: change `default_analyst_level` default from `AccessLevel.VIEW` to `AccessLevel.EDIT`
- Write a data migration to backfill existing `OrgPreferences` rows unconditionally (feature not yet live)

#### 1b. Add KPI to shareable_types
- `ddpui/models/resource_share.py`: add `KPI = "kpi"` to `ResourceType` enum
- `ddpui/core/access/shareable_types.py`: import `KPI` model from `ddpui.models.metric` and add `ResourceType.KPI: {"model": KPI}` to `RTYPES`

#### 1c. Cascade — schema change + write-time materialization
- **Migration**: add `parent` FK to `ResourceShare` (nullable, CASCADE)
- **`_grants_map` fix**: change user-level assignment from overwrite to max
- **`resource_share.add_grants`**: after creating/updating a dashboard share, call `_inner_ids_from_dashboard` and create/update child rows for all chart/KPI IDs
- **`resource_share.update_grant`**: after updating a dashboard share level, run `ResourceShare.objects.filter(parent=share).update(access_level=new_level)`
- **`resource_share.remove_grant`**: DB CASCADE handles children — no extra code needed
- **Dashboard update API hook** (`ddpui/api/dashboard_native_api.py`): when `tabs` is saved, diff old vs. new component IDs and create/delete child rows. Helper: `sync_cascade_rows(dashboard, old_tabs, new_tabs)` in `ddpui/core/access/resource_share.py`

#### 1d. Fix re-sharing gate in access_api.py
Replace `_require_owner_or_admin` on grant endpoints with:
```python
def _require_edit_or_admin(orguser, resource, rtype, action):
    level = get_user_access(orguser, rtype, resource.pk)
    if level != AccessLevel.EDIT:
        raise HttpError(403, f"Edit access required to {action}")
```

#### 1e. Apply accessible_filter to Chart and Report list APIs

**Charts:**
- `ddpui/core/charts/charts_service.py` — `list_charts`: add `orguser` param; apply `accessible_filter(orguser, ResourceType.CHART)`; annotate `access_level` via `get_user_access_map`
- `ddpui/api/charts_api.py` — pass `orguser`; include `access_level` in `ChartResponse`

**Reports:**
- `ddpui/core/reports/report_service.py` — `list_snapshots`: add `orguser` param; apply `accessible_filter(orguser, ResourceType.REPORT)`; annotate `access_level`
- `ddpui/api/report_api.py` — pass `orguser`; include `access_level` in `SnapshotResponse`

#### 1f. Update `list_grants` + ShareRowSchema
- Add `CascadeSourceSchema` and update `ShareRowSchema` with `cascade_sources`, `share_id: Optional[int]`
- Rewrite `list_grants` in `resource_share.py` to group by principal, compute effective max, populate `cascade_sources` (resolve parent row → Dashboard title)

---

### M2 — Cascade removal warning API (backend)

New endpoint: `GET /api/access/dashboard/{dashboard_id}/cascade-impact`

Query params: `principal_type` (user|group), `principal_id` (int)

Logic (`ddpui/core/access/resource_share.py`):
1. Fetch the dashboard; 404 if missing or not in org
2. Get inner chart + KPI IDs from `_inner_ids_from_dashboard`
3. For each inner resource, check if the principal has Edit via OTHER paths (other dashboard grants or direct grants). If none → would lose Edit
4. Return `{ "affected_charts": [...names...], "affected_kpis": [...names...], "affected_users": [...emails if group...] }`

Response schema: `CascadeImpactSchema` in `ddpui/schemas/access/resource_share_schema.py`

---

### M3 — Ownership transfer API (backend)

New endpoint: `POST /api/access/{rtype}/{resource_id}/transfer-ownership`

Body: `{ "to_orguser_id": int }`

Logic (`ddpui/core/access/ownership.py`):
1. Verify caller is current owner or Admin
2. Fetch `to_orguser` — must be same org
3. Check recipient's org floor = Edit (read `OrgPreferences` for their role)
4. `resource.created_by = to_orguser; resource.save()`
5. Old owner's ResourceShare rows untouched — effective access recalculates automatically

Add `TransferOwnershipPayload` schema to `ddpui/schemas/access/resource_share_schema.py`.

---

### M4 — Request access (backend)

**New model** `AccessRequest`:
```
org, resource_type, resource_id, requester (FK OrgUser), requested_level, status ("pending"|"approved"|"declined"), note, created_at, updated_at
```
Write migration.

**New endpoints** in `ddpui/api/access_api.py`:
- `POST /api/access/{rtype}/{resource_id}/request-access` — 409 if user already has access or pending request exists
- `GET /api/access/{rtype}/{resource_id}/request-access` — list pending requests; requires Edit or owner
- `POST /api/access/{rtype}/{resource_id}/request-access/{req_id}/respond` — body `{ "decision": "approved"|"declined", "granted_level": "view"|"edit" }`; if approved → call `add_grants`

---

### M5 — Invitation promotion + cleanup on delete (backend)

**Invitation promotion** (`ddpui/core/orguserfunctions.py`, invitation acceptance function):
```python
ResourceShare.objects.filter(org=org, invitation=invitation).update(
    principal_type="user", principal_id=new_orguser.id, invitation=None
)
OrgUserGroupMember.objects.filter(invitation=invitation).update(
    orguser=new_orguser, invitation=None
)
```

**Cleanup on group delete** — Django `post_delete` signal on `OrgUserGroup`:
- Delete `ResourceShare` rows where `principal_type="group", principal_id=group.id`

**Cleanup on resource delete** — in delete API handlers for Dashboard, Chart, Report, KPI:
- `ResourceShare.objects.filter(org=org, resource_type=rtype, resource_id=str(resource.id)).delete()`
- `AccessRequest` rows for that resource too

---

### M6 — Cascade removal warning + KPI sharing (frontend)

**Cascade warning in share-modal.tsx:**
- Hook `useCascadeImpact(dashboardId, principalType, principalId)` in `hooks/api/useAccess.ts`
- When `rtype === "dashboard"` and an existing grant's Edit is being downgraded or removed, call the cascade-impact API; if affected resources exist, show confirmation dialog before applying
- Dialog: "Removing Edit for [name] on this dashboard will also remove their Edit access on [N] inner charts: [Chart A, Chart B, ...]. Continue?"

**KPI sharing:**
- Add `ShareModal` to the KPI page with `rtype="kpi"` (needs M1 backend)
- File: relevant KPI detail/list component under `app/kpis/`

---

### M7 — Ownership transfer UI (frontend)

In `components/ui/share-modal.tsx`:
- If current user is owner or Admin: add "Transfer Ownership" as third option in the permission dropdown for any "People with access" row
- On select: show confirmation dialog
- On confirm: call `POST /api/access/{rtype}/{resource_id}/transfer-ownership`; refresh grants list

Add `transferOwnership(rtype, resourceId, toOrguserId)` to `hooks/api/useAccess.ts`.

---

### M8 — Request access UI (frontend)

**NoAccess screen** (`components/common/NoAccess.tsx`):
- Replace stub with proper screen + "Request Access" button → small modal (View/Edit radio + note + Submit)
- After submit: show "Request sent" state
- API: `POST /api/access/{rtype}/{resource_id}/request-access`

**Requests section in share modal** (`components/ui/share-modal.tsx`):
- Collapsible "Access Requests" section (owner/Edit-holders only)
- Pending requests: requester email, requested level, note, Approve / Decline
- API: `GET` + `POST /api/access/{rtype}/{resource_id}/request-access/{id}/respond`

---

### M9 — Bulk Share + Access badges (frontend)

**Bulk Share:**
- `app/charts/page.tsx`: add "Share" to bulk-action bar; open share modal applying to all selected IDs; show "Shared N of M — K skipped" toast
- `components/dashboard/dashboard-list-v2.tsx`: same for dashboards

**Visual access badges:**
- Add `<AccessBadge level="view|edit|owner" />` component to `components/ui/`
- Apply to: `dashboard-list-v2.tsx`, `app/charts/page.tsx`, reports list

---

### M10 — Tests (backend)

Files: `ddpui/tests/core/test_access_control.py` (new), `ddpui/tests/api/test_access_api.py` (new)

**access_control.py unit tests:**
- Floor only — Analyst gets "edit", Member gets "view"
- Direct grant overrides floor upward; grant + floor takes max
- Group grant — user in group gets group's level
- Cascade — dashboard share propagates to inner chart
- Cascade + direct view grant → Edit (max)
- Admin → always "edit"
- NO_ACCESS explicit grant with permissive floor → None (invisible)
- `accessible_filter` with NO_ACCESS floor — only owned/shared resources visible

**Grants API integration tests:**
- POST adds; GET lists; PATCH changes level; DELETE removes
- Edit-holder (non-owner) can call POST/PATCH/DELETE; View-holder gets 403

**Cascade impact API tests:**
- Two inner charts; user has Edit via dashboard only → both in affected list
- User also has direct Edit on one chart → that chart excluded

**Ownership transfer tests:**
- Owner → Analyst (Edit floor): succeeds
- Owner → Member (View floor): 400 blocked
- Non-owner: 403

**Request access tests:**
- No access → 201; already has access → 409; duplicate pending → 409
- Owner approves → grant created; declines → status updated

---

## Verification checklist (end-to-end)

1. **Floor**: Analyst floor = No Access → can't see dashboards. Floor = Edit → sees all.
2. **Direct share**: Share dashboard with Member (floor = No Access). Member sees dashboard + inner charts; unshared Member sees nothing.
3. **Cascade - edit**: Share dashboard at Edit. Recipient can open inner charts from /charts and edit them.
4. **Cascade removal warning**: Remove Edit from dashboard grant → dialog lists affected inner charts before applying.
5. **KPI sharing**: KPI share modal opens; grants work; KPI appears in recipient's KPI list.
6. **Ownership transfer**: Transfer dashboard → old owner drops to floor; new owner manages shares.
7. **Request access**: No-access Member opens link → request form → submits → owner sees in share modal → approves → Member gains access.
8. **Bulk share**: Select 5 dashboards → Share → applied to all; 2 without Edit skipped with count shown.
9. **Public link toggle off**: Turning off org toggle makes all existing public links inaccessible immediately.
10. **Invitation promotion**: External email invited via share modal → accepts → ResourceShare row promoted to new OrgUser (no longer pending).
