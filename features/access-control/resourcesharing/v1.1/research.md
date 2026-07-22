# Research: making charts independently shareable

Read-only research on the `feature/resource-sharing` branch, in these worktrees:

- Backend: `.dalgo-worktrees/resource-sharing/DDP_backend`
- Webapp: `.dalgo-worktrees/resource-sharing/webapp_v2`

Jargon used below, defined once: **general access** is an org-wide default level
("none"/"view"/"edit") a resource grants to everyone with the Analyst role and,
separately, everyone with the Member role. A **grant** is a per-user or
per-group override layered on top of general access. A **public link** lets
anyone with the URL view a resource with no login. **rtype** ("resource type")
is the string key ("dashboard", "report", ...) the sharing system uses to look
up which model and which rules apply.

---

## 1. Chart model

File: `ddpui/models/visualization.py:36-78`

Fields on `Chart`:

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `title` | CharField(255) | |
| `description` | TextField, null | |
| `chart_type` | CharField, choices `bar/pie/line/number/map` | |
| `computation_type` | CharField, default `aggregated` | deprecated, kept for old rows |
| `schema_name` / `table_name` | CharField(255) each | which warehouse table the chart reads |
| `extra_config` | JSONField | the chart's full config (axes, metrics, filters, etc.) |
| `created_by` | FK → OrgUser, null, `SET_NULL` | |
| `owner` | FK → OrgUser, null, `SET_NULL`, `related_name="owned_%(class)ss"` | |
| `org` | FK → Org, `CASCADE` | |
| `last_modified_by` | FK → OrgUser, null, `CASCADE` | |
| `created_at` / `updated_at` | auto timestamps | |

**Yes**, it already has `created_by`, `owner`, and `org` — the same shape
Dashboard and ReportSnapshot use for ownership. **No** per-chart access field
exists today (no `analyst_level`, `member_level`, `is_public`,
`public_share_token`, etc. — see §3 for what's missing).

Latest migration in the repo: **`0178_org_preferences_view_view_defaults.py`**
(194 migration files total, most recent by number).

---

## 2. Chart APIs

File: `ddpui/api/charts_api.py` (1403 lines). Every endpoint is gated by
`@has_permission([...])` (a role-level RBAC slug check, not a per-resource
check) plus, for the chart-content endpoints, calls into
`ddpui/core/sharing/chart_access.py`.

| Endpoint | Line | Permission slug | Extra gate |
|---|---|---|---|
| `GET /` (list) | `charts_api.py:276-278` | `can_view_charts` | **none** — see finding below |
| `GET /available-layers/` | `:325-327` | `can_view_charts` | — |
| `POST /map-data-overlay/` | `:390-392` | `can_view_charts` | `require_chart_view_access` (if `chart_id`) or `require_analyst_plus` (config-only), then `require_payload_within_chart_config` (`:417-426`) |
| `POST /chart-data/` | `:549-551` | `can_view_charts` | — |
| `POST /chart-data-preview/` | `:594-596` | `can_view_charts` | same pattern as map-data-overlay (`:634-641`) |
| `POST /chart-data-preview/total-rows/` | `:749-751` | `can_view_charts` | same pattern (`:777-784`) |
| `GET /regions/`, `/regions/{id}/children/` | `:857-869` | `can_view_charts` | — |
| `POST /geojsons/upload/` | `:877-879` | `can_create_charts` | — |
| `GET /geojsons/{id}/` | `:936-938` | `can_view_charts` | — |
| `POST /map-data/` | `:959-961` | `can_view_charts` | — |
| `POST /download-csv/` | `:1092-1094` | `can_view_charts` | — |
| `GET /{chart_id}/` (detail) | `:1145-1147` | `can_view_charts` | `require_chart_view_access` (`:1158`) |
| `GET /{chart_id}/data/` | `:1174-1176` | `can_view_charts` | `require_chart_view_access` (`:1194`) |
| `POST /` (create) | `:1257-1259` | `can_create_charts` | — |
| `PUT /{chart_id}/` (update) | `:1312-1314` | `can_edit_charts` | — (no ownership/view gate beyond role) |
| `DELETE /{chart_id}/` | `:1356-1358` | `can_delete_charts` | — |
| `POST /bulk-delete/` | `:1372-1374` | `can_delete_charts` | — |
| `GET /{chart_id}/dashboards/` | `:1392-1394` | `can_view_charts` | — |

**`list_charts` scoping (finding):** `list_charts` (`charts_api.py:276-319`)
calls `ChartService.list_charts` (`ddpui/services/chart_service.py:88-129`),
which filters only `Q(org=org)` (plus optional `search`/`chart_type` text
filters) — **no** `accessible_filter`, no role check beyond the
`can_view_charts` slug. Since Members hold `can_view_charts`
(`ddpui/management/commands/migrate_rbac_v2_roles.py:53`, the `MEMBER_SLUGS`
list), **any Member can list every chart in the org** — title, description,
schema/table name, full `extra_config` — through this one endpoint, even
though the detail/data endpoints below block them. This is a real
metadata-leak gap the enhancement should either close (scope the list by
Chart-level access, once it exists) or explicitly decide to leave, because
today the plan's premise ("charts are not independently visible outside a
dashboard") is already false for the list endpoint.

**The container-context gate — `require_chart_view_access`**
(`ddpui/core/sharing/chart_access.py:110-138`), used by the detail and data
endpoints above:

- With a `dashboard_id` query param (dashboard-tile context): 404 if that
  dashboard doesn't exist in the viewer's org; 403 if the chart is not
  actually a tile on that dashboard (`_dashboard_chart_ids`,
  `chart_access.py:80-91`, which walks `dashboard.tabs[*].components[*].config.chartId`);
  403 if `effective_permission(orguser, "dashboard", dashboard)` is `None`.
  In short: Member access to a chart rides entirely on the framing
  dashboard's Resource Sharing decision.
- Without `dashboard_id` (standalone — Charts page / builder): passes for
  Analyst+ (`_is_analyst_plus`, `chart_access.py:104-107`) or the chart's
  owner (`_is_chart_owner`, `:94-101`, owner_id wins, `created_by_id`
  fallback); everyone else (plain Members) gets 403.

Two sibling gates in the same file:
- `require_analyst_plus` (`:141-154`) — for the two table/map POST endpoints'
  config-only path (unsaved chart-builder preview, no `chart_id` yet).
- `require_payload_within_chart_config` (`:270-383`) — pins every column a
  dashboard-context POST payload references to the saved chart's own config
  (plus the framing dashboard's filter columns), so a dashboard-admitted
  Member can't smuggle in other warehouse columns via the request body.

The module's own docstring (`chart_access.py:1-42`) states the current
design intent plainly: *"A chart is visible wherever its dashboards are
visible"* — i.e., charts today are deliberately NOT independently shareable;
this whole file is the seam the v1.1 enhancement needs to widen.

---

## 3. The shareable contract

File: `ddpui/core/sharing/shareable_types.py` (98 lines).

The registry's own docstring (`:1-10`) states the contract precisely: a
model must have `analyst_level`, `member_level`, `owner`, `created_by`,
`org`, and a string-able primary key. It also says outright: *"`chart` is
deliberately NOT registered — charts ride along with their dashboard and are
not independently shareable."*

`ShareableType` (`:23-33`) is a frozen dataclass with:

- `rtype: str`
- `model: Type[Model]`
- `general: bool` — supports Layer 1 general access
- `grants: bool` — supports Layer 2 per-principal `ResourceShare` grants
- `public_link: bool` — supports a public share link
- `requests: bool` — supports "request access"
- `share_permission_slug: str` — the RBAC slug gating that rtype's sharing
  mutations (e.g. `can_share_dashboards`)

Currently registered (`:36-82`): `dashboard` (all four capabilities),
`report` (all four), `alert` (general + grants + requests, no public link),
`metric` and `kpi` (general + requests only, no grants, no public link).

**How Dashboard/Report satisfy the contract:** there is **no shared mixin** —
each model declares the fields directly, verbatim, field-for-field
identical:
- Dashboard: `analyst_level`/`member_level` at `ddpui/models/dashboard.py:115-120`
  (both `CharField(max_length=5, choices=AccessLevel.choices, default=AccessLevel.NONE)`),
  `created_by`/`owner`/`org` at `:123-129`.
- ReportSnapshot: same two fields at `ddpui/models/report.py:69-` (confirmed
  present; grep shows identical declaration pattern), `created_by`/`owner`
  at `:77-88`.

`AccessLevel` (`ddpui/models/general_access.py:21-27`) is the shared
`TextChoices` enum (`none`/`view`/`edit`) both models' fields use, plus
`ACCESS_LEVEL_RANK` (`:34-38`) for narrowing/widening comparisons.

**What Chart would need added** (schema-wise, to register):
1. `analyst_level` and `member_level` fields (copy Dashboard's declaration
   verbatim — `CharField(max_length=5, choices=AccessLevel.choices,
   default=AccessLevel.NONE)`) — a new migration after `0178`.
2. If public-link support is wanted for standalone charts: `is_public`,
   `public_share_token`, `public_shared_at`, `public_disabled_at`,
   `public_access_count`, `last_public_accessed` (Dashboard's public-sharing
   block, `dashboard.py:87-103`) — `set_public`
   (`ddpui/core/sharing/sharing_actions.py:600-638`) is written generically
   against exactly these field names, so Chart would slot in with zero
   changes to that function if these fields are added with the same names.
3. A new `ShareableType` entry in `RESOURCE_TYPES` (`shareable_types.py:36`)
   with a new `share_permission_slug` (e.g. `can_share_charts`) that would
   need seeding in `seed/002_permissions.json` and role-permission fixtures,
   mirroring the existing `can_share_dashboards` pattern.
4. `access_resolver.py` needs **no changes** — it is already fully generic
   (reads `analyst_level`/`member_level`/`owner`/`created_by`/`org` off
   whatever `resource` is passed; no `if rtype == ...` branching anywhere in
   that file, confirmed by inspection of `access_resolver.py:1-247`).

---

## 4. Dashboard→chart embed flow

There is **no dedicated "attach chart" backend endpoint**. The whole
tabs/components layout — including which chart tiles are on the dashboard —
is edited client-side and saved as one blind JSON blob via the existing
dashboard update endpoint:

- `PUT /{dashboard_id}/` → `update_dashboard`
  (`ddpui/api/dashboard_native_api.py:132-156`), gated by
  `@has_permission(["can_edit_dashboards"])` and `require_edit_access` (`:142`).
- It calls `DashboardService.update_dashboard`
  (`ddpui/services/dashboard_service.py:366-424`), which — when `data.tabs`
  is present — does `dashboard.tabs = [tab.model_dump() for tab in
  data.tabs]` (`:403-405`) and saves. **No validation** that any `chartId`
  named inside `tabs[*].components[*].config.chartId` exists, belongs to
  the org, or is otherwise legitimate — it's a straight overwrite.

**Consequence for planning:** the backend has no natural "a chart was just
added to a dashboard" event to hook a warning on — it would have to diff
old vs. new `tabs` server-side to detect newly-introduced `chartId`s, or
(more likely) the warning has to live entirely in the frontend picker UI,
since that's the only place the "add this chart" action is a distinct user
gesture rather than an opaque JSON diff.

**Webapp add-chart picker:** `components/dashboard/chart-selector-modal.tsx`
(`ChartSelectorModal`), opened from the dashboard editor at
`components/dashboard/dashboard-builder-v2.tsx:2430-2435`. It fetches
candidates via `useCharts({ search: chartSearch })`
(`chart-selector-modal.tsx:29`; hook at `hooks/api/useCharts.ts:30-63`),
which calls `GET /api/charts/?search=...` — i.e., it lists through the
same ungated `list_charts` endpoint from §2, with only a free-text search
box wired (no `chart_type` filter, despite the hook supporting one). Already
-embedded charts are greyed out client-side via `excludedChartIds`
(`chart-selector-modal.tsx:80-88`), not excluded from the fetched list. This
modal — specifically the moment a user clicks a chart card to add it — is
the natural hook point for an embed warning ("this chart isn't
independently shareable yet — adding it here exposes it to everyone who can
see this dashboard").

---

## 5. Dashboard-widening surfaces (hook points for a broadening warning)

All in `ddpui/core/sharing/sharing_actions.py` (868 lines).

- **General access change** — `set_general_access`
  (`sharing_actions.py:544-597`). It already has a **narrowing**
  warn-and-offer protocol (`_narrowed_roles`, `:495-507`, comparing
  `ACCESS_LEVEL_RANK` before/after per role; `_persisting_grants_for_narrowed_roles`,
  `:510-541`, listing grants that would still admit someone even after the
  narrowing commits). There is **no equivalent widening check today** — a
  request that raises `analyst_level`/`member_level` commits immediately at
  `:589-591` with no warning of any kind. A "dashboard-broadening" warning
  that enumerates contained charts would need new logic symmetric to
  `_narrowed_roles`, hooked in right before that commit.
- **Grant add** — `upsert_grant` (`:321-423`). New/changed grants commit at
  `ResourceShare.objects.update_or_create(...)` for groups (`:362-374`) and
  for users (`:403-415`). No widening warning exists here either.
- **Public link enable** — `set_public` (`:600-638`). The `if is_public:`
  branch (`:622-631`) mints a token (if missing) and flips the flag — no
  warning. (Disabling, `:632-633`, always succeeds, also no warning needed
  there.)
- **Bulk equivalents**, same absence of widening warnings: `_bulk_set_general`
  (`:760-809`, calls `set_general_access` per resource, only surfaces the
  existing narrowing confirmations via `confirmations.append`, `:800-807`),
  `_bulk_toggle_public` (`:812-835`, calls `set_public` per resource),
  `_bulk_add_grant` (referenced at `:854`, not read in depth here).

**Querying "which charts are on dashboard X":** two independent
implementations of the same tabs-walk exist today (both would need to
converge or one would need to become the shared helper):
- `ChartService.get_chart_dashboards` (`ddpui/services/chart_service.py:303-`,
  the reverse direction — chart → dashboards containing it) walks
  `dashboard.tabs[*].components[*]` checking
  `component.get("type") == DashboardComponentType.CHART.value` and
  `component["config"]["chartId"] == chart_id` (`:322-327`).
- `DashboardService.get_dashboard_charts` (`ddpui/services/dashboard_service.py:968-993`)
  does the forward direction — dashboard → its charts — with the identical
  walk (`:986-991`).
- `chart_access._dashboard_chart_ids` (`ddpui/core/sharing/chart_access.py:80-91`)
  is a third, access-gate-local copy of the same walk (returns a `Set[int]`
  of chart ids for membership checks). Its own docstring says it "mirrors"
  the other two — so this walk is already duplicated three times; a
  broadening-warning feature enumerating a dashboard's charts should almost
  certainly reuse (or extract) one shared helper rather than adding a fourth
  copy.

---

## 6. Reports as containers

`ReportSnapshot` (`ddpui/models/report.py:9-`) is explicitly documented as
**immutable and self-contained**: *"No FK to Dashboard or Chart. Once
frozen, the snapshot is fully self-contained. Deleting dashboards or charts
does NOT affect snapshots."* (`:10-16`). It stores:
- `frozen_dashboard` (JSONField, `:39-42`) — the frozen dashboard config +
  filters at snapshot time.
- `frozen_chart_configs` (JSONField, `:44-47`) — frozen chart configs
  **keyed by chart_id**, i.e., a point-in-time copy of each embedded
  chart's config, not a live FK/reference to the `Chart` row.

**Consequence:** report rendering does not go through `Chart` rows or
`require_chart_view_access` at all — it renders from its own frozen JSON.
Adding per-chart access rows to the live `Chart` model would have **no
effect on report rendering**, because reports never look the live chart up
by access-gated id; they already snapshotted everything they need at
creation time. (Whether report *creation* — the moment a dashboard's charts
get frozen into a snapshot — should itself check chart-level access is a
separate design question this research didn't need to resolve, since it's
about a write-time gate, not the render path asked about here.)

---

## 7. Public dashboard rendering

`ddpui/api/public_api.py`. Two endpoints matter:

- `get_public_chart_metadata` (`:164-215`) — looks up the dashboard by
  token (`:184`), then does `chart = Chart.objects.filter(id=chart_id,
  org=dashboard.org).first()` (`:191`). **It only checks that the chart
  belongs to the same org as the public dashboard — it never checks that
  `chart_id` is actually a tile on that dashboard.**
- `get_public_chart_data` (`:218-`, same pattern at `:256`) — identical gap.

**Finding (asymmetry / gap):** the authenticated path's
`require_chart_view_access` (§2) explicitly checks dashboard-tile
membership via `_dashboard_chart_ids` before admitting a Member. The public
path does **not** — today, anyone holding a public dashboard link can
already fetch metadata/data for **any chart in that org** by guessing/
iterating `chart_id`, not just the charts actually placed on that public
dashboard. This is a pre-existing gap, independent of whether Chart gets
per-chart access rows. If Chart-level access rows are added, this endpoint
is the most natural place to also add the missing membership check — doing
one without the other would be an odd half-fix, since the two problems
(no membership check; no per-chart access) compound in the public,
unauthenticated context most.

---

## 8. Webapp chart surfaces

Full detail from the frontend investigation, condensed:

- **`/charts` list** (`app/charts/page.tsx`): columns are Name (with a
  client-side-only favorite star), Data Source, Type, Created by, Last
  Modified, Actions (`:1179-1304`). Row actions: Edit link (gated
  `CAN_EDIT_CHARTS`, `:881-887`), a "⋮" menu with Select / Duplicate
  (`CAN_CREATE_CHARTS`) / Export / Delete (`CAN_DELETE_CHARTS`)
  (`:895-941`). A bulk toolbar exists for multi-delete
  (`:1017-1073`, `handleBulkDelete` `:452-507`) but — unlike the dashboard
  list's per-row checkboxes (`components/dashboard/dashboard-list-v2.tsx:882`)
  — there is no per-row select checkbox wired in `renderChartTableRow`
  (`page.tsx:794-948`); "Select All" operates over the whole filtered set.
  **No share badge, no access-level column, no Share button** exist for
  charts (contrast: dashboards render a general-access badge via
  `deriveGeneralAccessBadge`, `dashboard-list-v2.tsx:929-976`, and a
  per-row Share button, `:1044-1046`/`:1576-1578`).
- **Chart detail** (`app/charts/[id]/page.tsx` → `ChartDetailClient.tsx`)
  and **editor** (`app/charts/[id]/edit/page.tsx`, plus
  `/charts/new`, `/charts/new/configure`): the detail header
  (`ChartDetailClient.tsx:758-823`) shows title, "Created by {email}", an
  Edit button, and an export dropdown — **no Share button, no
  general-access UI at all**. Sharing is entirely absent from the chart UI
  today.
- **Existing sharing components available to extend**: `ShareModal`
  (`components/ui/share-modal.tsx:95-113` for its props), generic over
  `entityType`, already used for dashboards/reports/alerts; `BulkShareDialog`
  (`components/sharing/bulk-share-dialog.tsx:80-93`), used for bulk
  dashboard sharing. Both are blocked from targeting charts today purely by
  a frontend type union: `ShareableResourceType` in
  `hooks/api/useResourceAccess.ts:12` is
  `'dashboard' | 'report' | 'alert' | 'metric' | 'kpi'` — `'chart'` is
  simply not a member yet. Once the backend registers `chart` in
  `RESOURCE_TYPES` (§3), adding `'chart'` to this union plus a `CHART` row
  in the charts list/detail pages is largely wiring, since the modal
  components are already generic.
- **No standalone chart rendering exists outside Charts pages and the
  dashboard tile renderer** (`components/dashboard/chart-element-v2.tsx`).
  KPIs are a separate model/API (`useKPIs`/`useKPIData`), unrelated to
  Chart. Reports contain no chart-picker or chart references in the
  frontend at all (they render from the frozen snapshot, matching §6).

---

## 9. `accessible_filter`

`ddpui/core/sharing/access_resolver.py:210-246`.

Signature:
```python
def accessible_filter(
    viewer,
    rtype: str,
    get_group_ids: Optional[GetGroupIds] = None,
) -> Q
```

Returns one ORM `Q` combining: rows visible via general access (`~Q(**{field_name:
AccessLevel.NONE})` for the viewer's role, `:230-231`), rows granted via an
active `ResourceShare` (`:233-242`), and rows the viewer owns (`owner_id` or
`created_by_id` match, `:244`), all AND-ed with `Q(org_id=viewer_org_id)`
(`:246`). It does **not** special-case Admins — callers are expected to skip
calling it entirely for admin viewers (docstring, `:218-222`).

**Nothing here is rtype-specific** — it works purely off the
`analyst_level`/`member_level`/`owner`/`created_by`/`org` field names, so
once Chart has those fields and is registered in `RESOURCE_TYPES` (§3),
`accessible_filter(viewer, "chart", chart_qs)`-style scoping would work with
**zero changes to this function** — Chart just needs the fields to exist.
The only real work is wiring `list_charts` (§2) to actually call it (it
currently doesn't call anything like it — that's the metadata-leak gap
already flagged in §2).

---

## Summary of what this means for plan shape

See the 10-line summary returned to the caller for the highest-priority
items; the details behind each point are in the numbered sections above.
