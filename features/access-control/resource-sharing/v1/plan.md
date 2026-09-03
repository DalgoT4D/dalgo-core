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
11. **Private toggle missing** — no `is_private` field on resource models; `accessible_filter` doesn't handle per-resource privacy override
12. **Floor hierarchy not enforced** — no validation prevents Member floor being set above Analyst floor

### Frontend gaps
1. **KPI sharing** — no ShareModal on the KPI page
2. **Cascade removal warning dialog** — no confirmation before removing Edit from a dashboard
3. **Ownership transfer UI** — not in share-modal.tsx
4. **Request access flow** — NoAccess screen is a stub (`components/common/NoAccess.tsx` has no request button)
5. **Access requests section** — share modal doesn't show pending requests for the owner to approve/decline
6. **Visual access badges** — resource list items don't display View/Edit/Owner badges
7. **Private toggle** — not in share-modal.tsx
8. **Floor hierarchy enforcement** — Roles tab doesn't disable Member floor options that exceed Analyst's current floor

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

### Access control model — key constraints

- **`ResourceShare` rows only hold `view` or `edit`.** `no_access` is an org-floor concept only (`OrgPreferences.default_analyst_level / default_member_level`). There is no per-resource explicit deny.
- **Cascade is transparent to the access engine.** Cascade rows (`parent_id != NULL`) have the child resource's `rtype` (e.g. `rtype=chart`) and the same `principal_type/principal_id` as the parent dashboard share. `_grants_map("chart")` fetches them alongside direct chart grants in one query — it doesn't need to know about `parent_id` at all for the filter to work.
- **`accessible_filter` and `get_user_access_map` need no changes for cascade.** They consume `_grants_map`'s output and the cascade rows flow through automatically.
- **Private toggle (`is_private`)** — a per-resource boolean that overrides the org floor downward. When `is_private=True`, the resource is invisible to role-floor-based access; only the owner (`created_by`) and users/groups with an explicit grant can see it. `accessible_filter` must account for this (see 1g below).

### `accessible_filter` update for Private toggle

```python
owned_or_granted = Q(created_by=orguser) | Q(id__in=allowed_ids)

if _org_floor(orguser) == AccessLevel.NO_ACCESS:
    return owned_or_granted
else:
    # Private resources bypass the floor — only accessible via owner or explicit grant
    private_ids = list(entry["model"].objects.filter(org=orguser.org, is_private=True).values_list("pk", flat=True))
    return owned_or_granted | ~Q(id__in=private_ids)
```

- Private resource + no grant + permissive floor → excluded (`id__in=private_ids`) ✓
- Private resource + explicit grant → included via `owned_or_granted` ✓
- Private resource + owner → included via `created_by` ✓
- Non-private resource + permissive floor → `~Q(id__in=private_ids)` includes it ✓
- Floor = NO_ACCESS (any resource) → only `owned_or_granted` ✓

### `_grants_map` fix in access_control.py

Currently user rows overwrite each other (last write wins). With cascade, a chart can appear in multiple dashboards shared to the same user at different levels — the last-fetched row wins, which is wrong. Fix: take max across all user rows.

```python
# Before (wrong with cascade):
user_levels[row.resource_id] = row.access_level

# After — take max:
current = user_levels.get(row.resource_id)
if current is None or LEVEL_RANK[row.access_level] > LEVEL_RANK[current]:
    user_levels[row.resource_id] = row.access_level
```

Example: Chart C1 in Dashboard D1 (User X → edit) and Dashboard D2 (User X → view).
`_grants_map("chart")` sees two rows for C1. Max = edit. ✓

The group branch already takes max — no change needed there.

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
- **`_grants_map` fix**: change user-level assignment from last-write-wins to max (handles a chart appearing in multiple shared dashboards); `accessible_filter` + `get_user_access_map` need no changes — they consume `_grants_map` output and cascade rows flow through automatically
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

**Pattern (already live on dashboards — replicate):**
- `dashboard_native_api.py` line ~78: `levels = access_control.get_user_access_map(orguser, ResourceType.DASHBOARD, dashboards)` then `access_level=levels[d.pk]` on each response object.
- Frontend: `dashboard.access_level === 'edit'` gates the edit button. List contains only items the user can see (backend filtered), so no frontend filtering is needed.

**Charts — backend:**
- `ddpui/core/charts/charts_service.py` — `list_charts`: add `orguser: OrgUser` param; apply `accessible_filter(orguser, ResourceType.CHART)` to the queryset
- Annotate `access_level` via `get_user_access_map(orguser, ResourceType.CHART, charts)` → pass to response
- `ddpui/api/charts_api.py` — pass `orguser` to `list_charts`; add `access_level: Optional[str]` to `ChartResponse`

**Reports — backend:**
- `ddpui/core/reports/report_service.py` — `list_snapshots`: same pattern — add `orguser`, apply `accessible_filter`, annotate via `get_user_access_map(orguser, ResourceType.REPORT, snapshots)`
- `ddpui/api/report_api.py` — pass `orguser`; add `access_level: Optional[str]` to `SnapshotResponse`

**Frontend (both):**
- `webapp_v2/types/charts.ts` — add `access_level?: 'view' | 'edit'`
- `webapp_v2/types/reports.ts` (or equivalent) — add `access_level?: 'view' | 'edit'`
- `app/charts/page.tsx` — change edit/share button gating from `PERMISSIONS.CAN_EDIT_CHARTS` → `chart.access_level === 'edit'`
- `app/reports/page.tsx` — same for the report edit/delete/share buttons

#### 1f. Update `list_grants` + ShareRowSchema
- Add `CascadeSourceSchema` and update `ShareRowSchema` with `cascade_sources`, `share_id: Optional[int]`
- Rewrite `list_grants` in `resource_share.py` to group by principal, compute effective max, populate `cascade_sources` (resolve parent row → Dashboard title)

#### 1g. Private toggle — backend
- Add `is_private = models.BooleanField(default=False)` to `Dashboard`, `Chart`, `Report`, `KPI` models + one migration covering all four
- Update `accessible_filter` in `access_control.py` with the Private toggle logic (see above)
- Add `PATCH /api/access/{rtype}/{resource_id}/private` endpoint in `access_api.py` — body `{ "is_private": bool }`; requires owner or Edit; updates the model field. When setting `is_private=True`, also clear the resource's public share token (`public_share_token=None, is_public=False`) so existing public links are immediately revoked.
- `get_user_access` also needs updating: when `is_private=True` and user is not owner/admin/grantee, skip the floor fallback and return `None` (invisible)
- `get_user_access_map` also needs updating: for each resource, if `resource.is_private=True` and the user has no grant and is not the creator, skip the floor fallback and return `None` instead of the floor level

#### 1h. Floor hierarchy enforcement — backend
- In `org_preferences_api.py` (the PUT handler for floor settings): validate that `default_member_level` rank ≤ `default_analyst_level` rank using `LEVEL_RANK`; return 400 if violated

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
3. Check recipient has effective Edit on the resource: `get_user_access(to_orguser, rtype, resource.pk) == AccessLevel.EDIT` — a Member with a direct Edit share qualifies; return 400 if not
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

**Private toggle in share modal (`components/ui/share-modal.tsx`):**
- Add Private toggle UI (needs M1g backend)
- On toggle: call `PATCH /api/access/{rtype}/{resource_id}/private`
- When on: show indicator that resource is private (floor bypassed)
- Requires owner or Edit to toggle

**Floor hierarchy enforcement (`components/settings/access/RolesTab.tsx`):**
- When Admin changes Member floor, disable options whose rank exceeds Analyst's current floor
- Mirror the backend validation (1h) in the UI so the constraint is obvious

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

**403 vs 404 on direct URL access:**
- Resource detail endpoints (dashboard, chart, report, KPI) currently return 404 when the resource is invisible to the caller. Change to return **403** when the resource exists but the caller lacks access — this allows the frontend to show the request-access screen instead of a dead-end not-found page.
- 404 is still correct when the resource genuinely doesn't exist (wrong ID, different org).

**Requests section in share modal** (`components/ui/share-modal.tsx`):
- Collapsible "Access Requests" section (owner/Edit-holders only)
- Pending requests: requester email, requested level, note, Approve / Decline
- API: `GET` + `POST /api/access/{rtype}/{resource_id}/request-access/{id}/respond`

---

### M9 — Access badges (frontend)

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
- Cascade — dashboard share propagates edit to inner chart; chart absent from other shares gets it via cascade
- Cascade max — chart in two dashboards (one edit, one view): effective = edit
- Cascade + floor: Member (floor=no_access) with dashboard share → sees inner charts; Member without any share → filtered out
- Admin → always "edit"
- `accessible_filter` with NO_ACCESS floor — only owned/directly-granted/cascade-granted resources visible

**Grants API integration tests:**
- POST adds; GET lists; PATCH changes level; DELETE removes
- Edit-holder (non-owner) can call POST/PATCH/DELETE; View-holder gets 403

**Cascade impact API tests:**
- Two inner charts; user has Edit via dashboard only → both in affected list
- User also has direct Edit on one chart → that chart excluded

**Ownership transfer tests:**
- Owner → Analyst (Edit floor on resource): succeeds
- Owner → Member with direct Edit share on resource: succeeds
- Owner → Member with no Edit share: 400 blocked
- Non-owner: 403

**Request access tests:**
- No access → 201; already has access → 409; duplicate pending → 409
- Owner approves → grant created; declines → status updated

---

## Verification checklist (end-to-end)

1. **Floor**: Analyst floor = No Access → can't see dashboards. Floor = Edit → sees all.
2. **Direct share**: Share dashboard with Member (floor = No Access). Member sees dashboard + inner charts (in /charts); unshared Member sees nothing.
3. **Cascade - view**: Share dashboard at View. Recipient sees inner charts in /charts as view-only (no edit button).
4. **Cascade - edit**: Share dashboard at Edit. Recipient sees inner charts in /charts with full edit access.
5. **Cascade removal warning**: Remove Edit from dashboard grant → dialog lists affected inner charts before applying.
6. **Private toggle**: Toggle a dashboard Private. Member with View floor can no longer see it. Direct-share Member still can.
7. **KPI sharing**: KPI share modal opens; grants work; KPI appears in recipient's KPI list.
8. **Ownership transfer to Member**: Give Member a direct Edit share on a dashboard → transfer ownership to them → succeeds.
9. **Request access**: No-access Member opens link → request form → submits → owner sees in share modal → approves → Member gains access.
10. **Floor hierarchy**: Try setting Member floor above Analyst → Roles tab blocks it; API returns 400.
11. **Public link toggle off**: Turning off org toggle makes all existing public links inaccessible immediately.
12. **Invitation promotion**: External email invited via share modal → accepts → ResourceShare row promoted to new OrgUser (no longer pending).

---

### M17 — View → Edit upgrade + share notifications

Two related additions (see spec §Request access / §Share notifications):

**Backend — request-access upgrade path** (`ddpui/api/access_api.py`):

- `POST /request-access` currently 409s when `existing_access` is anything other than `None`/`no_access` (see `create_access_request` at ~line 457). Change the guard to:
  ```python
  if existing_access is not None and _rank(existing_access) >= _rank(requested_level):
      raise HttpError(409, "you already have access at this level or higher")
  ```
  Reject same-level and downgrade requests; allow `view → edit`.
- `respond_to_access_request` on approve: if the requester already has a direct `ResourceShare` row on this resource, upgrade its `access_level` in place instead of creating a duplicate row. If they only had View via cascade/group/floor, create a new direct Edit share (existing behavior).

**Backend — share notifications** (`ddpui/api/access_api.py::add_resource_grants`):

- Snapshot existing `(principal_type, principal_id) → access_level` map from `ResourceShare` rows for this resource before calling `resource_share.add_grants`.
- After `add_grants` returns, diff to classify each row as:
  - **new**: no matching pre-snapshot row
  - **upgraded**: pre-snapshot level < post-snapshot level (per `AccessLevel` rank)
  - **unchanged / downgraded**: skip
- Expand recipients:
  - `principal_type == "user"` → `[principal_id]`
  - `principal_type == "group"` → `OrgUserGroupMember.objects.filter(group_id=principal_id, orguser__isnull=False).values_list("orguser_id", flat=True)`
  - `principal_type == "invitation"` → skip (invitation email handles it)
- De-dupe recipient orguser_ids across all classified rows; drop the sender's own id (don't notify yourself).
- Fire one `create_notification` per rtype+resource with the deduped recipient list. Message shape:
  - New: `"{sender_email} shared {rtype} '{title}' with you at {level} access.\n{resource_url}"`
  - Upgrade: `"{sender_email} upgraded your access on {rtype} '{title}' to {level}.\n{resource_url}"`
  - If both new and upgrade in the same call, send one notification per class (two `create_notification` calls) so email subjects can differ.
- Wrap in `try/except Exception as err: logger.error(...)` — notification failure never fails the API call (same pattern as `_notify_owner_of_new_request`).

**Frontend — one dialog, two entry points:**

Both the NoAccess screen and the new Request-Edit pill use the **same** `RequestAccessDialog` — same JSX, same POST `/request-access` call, same submitted state. The only per-entry-point variation is the pre-selected level radio.

- **Step 1 — extract dialog from NoAccess.** Move the modal body from `components/no-access.tsx` into `components/access/request-access-dialog.tsx`:
  ```tsx
  interface Props {
    rtype: string;
    resourceId: number;
    defaultLevel?: 'view' | 'edit';   // default 'view'
    isOpen: boolean;
    onClose: () => void;
    onSubmitted?: () => void;
  }
  ```
  Update `NoAccess` to render the extracted dialog with `defaultLevel='view'`. `no-access.test.tsx` must keep passing.

- **Step 2 — new `RequestEditPill`** (`components/access/request-edit-pill.tsx`):
  - Props: `rtype`, `resourceId`, `resourceAccessLevel: 'view' | 'edit'`
  - Renders a pill at the top of the resource: *"You have View access · Request Edit"*.
  - Hidden when `resourceAccessLevel !== 'view'`. No admin/owner check needed — the backend already computes `access_level = 'edit'` for Owners and Admins, so the level gate is sufficient.
  - Reuses `RequestAccessDialog` with `defaultLevel='edit'`.

- **Step 3 — mount the pill** in the four single-resource surfaces:
  - `components/dashboard/individual-dashboard-view.tsx`
  - `app/charts/[id]/ChartDetailClient.tsx`
  - `app/reports/[id]/page.tsx` (or the report detail component)
  - `components/kpis/kpi-detail-drawer.tsx`

**Tests — backend** (`ddpui/tests/api_tests/test_access_api.py`):

- L22 — view-holder can request edit → 201; `requested_level='edit'`
- L23 — edit-holder requesting edit → 409
- L24 — approve upgrade merges into existing `ResourceShare` row (no duplicate; `access_level` bumped from `view` → `edit`)
- L25 — approve upgrade when only cascade/floor gave View → new direct Edit row created
- L26 — direct user grant fires a share notification to the grantee
- L27 — group grant fires a share notification to every current group member
- L28 — level change from View → Edit on an existing row fires an upgrade notification
- L29 — no-op re-save (same level) does not fire a notification
- L30 — downgrade (edit → view) does not fire a notification
- L31 — invitation-typed rows do not fire share notifications (pending emails)
- L32 — user is both direct grantee and member of a granted group → single deduplicated notification
- L33 — sender is never their own share notification recipient

**Tests — frontend:**

- Pill visibility: renders for `access_level='view'`, hidden for `access_level='edit'`, hidden for Owner (backend returns `edit` for Owner).
- Clicking pill opens `RequestAccessDialog` with the level radio pre-selected to Edit.
- Existing `NoAccess.test.tsx` continues to pass after the modal refactor.

---

### M11 — Alert recipients: backend schema + validation

Adds `user_group` as a third recipient type. Existing `orguser` and `external` records are unaffected.

**`ddpui/schemas/alert_schema.py`:**
- Extend `RecipientIn.type` Literal: `"orguser" | "external" | "user_group"`
- Add `user_group_id: Optional[int] = None` to `RecipientIn`
- Add `user_group_id: Optional[int] = None` and `user_group_name: Optional[str] = None` to `RecipientOut`

No migration needed — `Alert.recipients` is a JSONField.

**`ddpui/core/alerts/alert_service.py`:**
```python
VALID_RECIPIENT_TYPES = {"orguser", "external", "user_group"}

# In _validate_recipients — add branch:
elif rtype == "user_group":
    group_id = r.get("user_group_id") if isinstance(r, dict) else r.user_group_id
    if not group_id:
        raise AlertValidationError(
            f"Recipient[{idx}]: user_group_id is required for type='user_group'"
        )
    if not OrgUserGroup.objects.filter(id=group_id, org=org).exists():
        raise AlertValidationError(
            f"Recipient[{idx}]: UserGroup {group_id} not in this org"
        )
```

`_serialize_recipients` needs no change — `r.model_dump()` with None-stripping handles the new field automatically.

**GET response** — wherever `RecipientOut` is built from stored `alert.recipients` JSON, add a bulk lookup for group names:
```python
group_ids = [r["user_group_id"] for r in recipients if r.get("type") == "user_group"]
group_name_by_id = {g.id: g.name for g in OrgUserGroup.objects.filter(id__in=group_ids)}
```

**Tests — new file `ddpui/tests/core/alerts/test_recipient_groups.py`:**

| Test | Checks |
|---|---|
| `test_validate_user_group_recipient_valid` | Valid group ID in same org passes |
| `test_validate_user_group_recipient_wrong_org` | Group from another org raises `AlertValidationError` |
| `test_validate_user_group_recipient_missing_id` | Missing `user_group_id` raises `AlertValidationError` |
| `test_existing_orguser_still_valid` | Backward compat — `orguser` type unchanged |
| `test_existing_external_still_valid` | Backward compat — `external` type unchanged |

---

### M12 — Alert recipients: backend delivery

When an alert fires, `user_group` recipients expand to all active group members' emails. Deduplication is applied across all recipient types.

**`ddpui/core/notifications/triggers/alert.py`:**

```python
from ddpui.models.org_user import OrgUser, OrgUserGroupMember

def notify_alert_recipients(alert, *, subject, body):
    deliveries = []
    recipients = alert.recipients or []

    # Resolve orguser recipients
    orguser_ids = [r["orguser_id"] for r in recipients if r.get("type") == "orguser"]
    orguser_email_by_id = {}
    if orguser_ids:
        for ou in OrgUser.objects.filter(id__in=orguser_ids, org_id=alert.org_id).select_related("user"):
            orguser_email_by_id[ou.id] = ou.user.email

    # Expand user_group recipients to active member emails
    group_ids = [r["user_group_id"] for r in recipients if r.get("type") == "user_group"]
    group_member_emails = set()
    if group_ids:
        memberships = (
            OrgUserGroupMember.objects
            .filter(group_id__in=group_ids, orguser__isnull=False)
            .select_related("orguser__user")
        )
        group_member_emails = {m.orguser.user.email for m in memberships}

    # Build deduplicated email list
    seen = set()
    resolved_emails = []
    for r in recipients:
        email = _resolve_recipient_email(r, orguser_email_by_id)
        if email and email not in seen:
            seen.add(email)
            resolved_emails.append(email)
    for email in group_member_emails:
        if email not in seen:
            seen.add(email)
            resolved_emails.append(email)

    for email in resolved_emails:
        deliveries.append(_deliver_email(to_email=email, subject=subject, ...))
    return deliveries
```

Update `_resolve_recipient_email` to return `None` for `user_group` entries (expanded in bulk above):
```python
def _resolve_recipient_email(recipient, orguser_email_by_id):
    if recipient.get("type") == "external":
        return recipient.get("email")
    if recipient.get("type") == "orguser":
        return orguser_email_by_id.get(recipient.get("orguser_id"))
    return None   # user_group: handled in bulk
```

Update `_describe_missing_recipient` to handle `user_group`:
```python
if r.get("type") == "user_group":
    return f"user_group:{r.get('user_group_id')}"
```

**Tests — update `ddpui/tests/core/alerts/test_delivery.py`:**

| Test | Checks |
|---|---|
| `test_group_recipient_expands_to_active_members` | 3 active members → 3 delivery dicts |
| `test_pending_members_skipped` | Members with `orguser=None` → 0 deliveries |
| `test_deduplication_across_types` | orguser who is also in a group → 1 delivery dict |
| `test_empty_group_no_deliveries` | Group with 0 members → 0 deliveries, no error |
| `test_orguser_and_external_unchanged` | Existing recipient types work alongside new type |

---

### M13 — Alert recipients: frontend picker

Replaces the existing `RecipientCombobox` with a unified `RecipientPicker` that supports org members, user groups, and external emails.

**`webapp_v2/types/alerts.ts`:**
```typescript
// Add to RecipientIn and RecipientOut:
user_group_id?: number | null;
user_group_name?: string | null;
// Extend type literal:
type: 'orguser' | 'external' | 'user_group';
```

**New component `webapp_v2/components/alerts/RecipientPicker.tsx`:**

Props: `value: RecipientIn[]`, `onChange: (v: RecipientIn[]) => void` — same interface as the old `RecipientCombobox`.

Data: `useActiveMembers()` for Members section; `useUserGroups()` for Groups section (both hooks already in `hooks/api/useAccess.ts`).

Dropdown layout:
```
┌──────────────────────────────────────────────────┐
│ [input: "fun"]                                    │
├──────────────────────────────────────────────────┤
│ Members                                           │
│  👤 funder@example.org          [Analyst]         │
├──────────────────────────────────────────────────┤
│ Groups                                            │
│  👥 Funders                     3 members         │
├──────────────────────────────────────────────────┤
│ External                                          │
│  ✉  Add "fun@external.com"  ← only for valid email│
└──────────────────────────────────────────────────┘
```

Chip color coding:

| Type | Icon | Colors |
|---|---|---|
| `orguser` | `UserIcon` | Emerald (`bg-emerald-50 text-emerald-800 border-emerald-200`) |
| `user_group` | `Users2Icon` | Violet (`bg-violet-50 text-violet-800 border-violet-200`) |
| `external` | `MailIcon` | Gray (`bg-gray-50 text-gray-700 border-gray-200`) |

Key behaviors:
- Members: substring-filtered, capped at 5; click → `{ type: 'orguser', orguser_id, orguser_name }`.
- Groups: substring-filtered, capped at 5; click → `{ type: 'user_group', user_group_id, user_group_name }`. Section hidden silently if hook returns no data (permission gap).
- External: shown only when input is a valid email; click or Enter → `{ type: 'external', email }`.
- Backspace on empty input removes last chip. Already-added recipients filtered from dropdown.

**`webapp_v2/components/alerts/AlertNotifyStep.tsx`:**
```typescript
// Replace:
import { RecipientCombobox } from './RecipientCombobox';
// With:
import { RecipientPicker } from './RecipientPicker';
```

Delete `RecipientCombobox.tsx` and its test file after swapping.

**Tests — new file `webapp_v2/components/alerts/__tests__/RecipientPicker.test.tsx`:**

| Test | Checks |
|---|---|
| `adds orguser chip from suggestion` | Member suggestion → emerald chip |
| `adds user_group chip from suggestion` | Group suggestion → violet chip |
| `adds external chip on valid email + Enter` | Valid email → gray external chip |
| `rejects duplicate across types` | Cannot add same orguser twice |
| `removes chip on X click` | All three types |
| `removes last chip on Backspace on empty input` | Backspace behavior |
| `already-added items filtered from suggestions` | Added orguser not in dropdown |
| `external section hidden for non-email input` | "Add" row only for valid email |
