# DDP_backend Landmarks

> **What this file is:** a lookup table of file paths + line ranges + conventions, so planners and implementers don't have to re-explore the codebase to find where things live. Load this **before** spawning Explore agents.

> **What this file is NOT:** documentation of how the code works, templates, or architectural overviews — see `templates.md` (code templates) and `examples.md` (walkthroughs) for those.

> **Confidence:** each section ends with a `Verified` date. If a path doesn't resolve, the codebase moved — update this file rather than blindly re-exploring.

---

## Auth, roles, permissions

| Concern | Location |
|---|---|
| `Role` model | `ddpui/models/role_based_access.py:5-14` (uuid, slug, name, level) |
| `Permission` model | `ddpui/models/role_based_access.py:17-25` (uuid, slug, name) |
| `RolePermission` model (join) | `ddpui/models/role_based_access.py:28-38` |
| `OrgUser.new_role` FK | `ddpui/models/org_user.py:74` (FK Role, `on_delete=SET_NULL`) |
| Role seed JSON | `seed/001_roles.json` (5 roles incl. `super-admin`) |
| Permission seed JSON | `seed/002_permissions.json` (85 slugs as of 2026-06-17) |
| RolePermission seed JSON | `seed/003_role_permissions.json` |
| `@has_permission([...])` decorator | `ddpui/auth.py:30-51` — raises `HttpError(403, "not allowed")` |
| JWT auth middleware | `ddpui/auth.py:176-188` (`CustomJwtAuthMiddleware.authenticate`) — populates `request.permissions` (set) and `request.orguser` |
| Redis role→permissions cache | `ddpui/auth.py:81-91` (`set_roles_and_permissions_in_redis`) — env key `ROLE_PERMISSIONS_REDIS_KEY` (default `dalgo_permissions_key`); cleared on deploy at lines 213-215 |
| Per-user `orguser_role:{user.id}` cache | `ddpui/auth.py:219-232` — populated on login + token refresh |

*Verified: 2026-06-05.*

---

## Content models (org-scoped; all have `created_by` + `last_modified_by` FK to OrgUser)

| Resource | Model file | created_by | last_modified_by |
|---|---|---|---|
| Dashboard | `ddpui/models/dashboard.py:49-156` | line 111 | lines 113-119 |
| Chart | `ddpui/models/visualization.py:36-67` | line 60 | lines 62-67 |
| ReportSnapshot | `ddpui/models/report.py:8-92` | lines 65-70 (`SET_NULL`) | lines 71-78 (`SET_NULL`) |
| Metric | `ddpui/models/metric.py:38-82` | lines 62-63 | lines 65-67 (nullable) |
| KPI | `ddpui/models/metric.py:84-129` | line 117 | lines 118-120 (nullable) |

Notes:
- `is_org_default` Boolean on Dashboard at lines 105-108; unique-per-org constraint at lines 150-156.
- Dashboard has `is_public` + `public_share_token`; ReportSnapshot has its own `public_share_token`. Two independent share tokens — never collapse them.
- Chart `extra_config` is a JSON blob (loose schema). `computation_type` is deprecated.
- **No `owner` field exists** — only `created_by` / `last_modified_by`. (Access-control v2 adds `owner`.)

### Delete handlers + current ownership check

| Resource | DELETE route (api) | Service fn | Ownership check today |
|---|---|---|---|
| Dashboard | `api/dashboard_native_api.py:142-157` (`can_delete_dashboards`) | `services/dashboard_service.py:396` | `created_by != orguser` → blocked (line 422); **no Admin override** |
| Chart | `api/charts_api.py:1190-1203` (`can_delete_charts`) | `services/chart_service.py:225` | `created_by != orguser` → blocked (line 243) |
| ReportSnapshot | `api/report_api.py:193-207` (`can_delete_dashboards`) | `core/reports/report_service.py:735` | `created_by != orguser` → blocked (line 753) |
| Metric | `api/metric_api.py:204-217` (`can_delete_metrics`) | `core/metric/metric_service.py:279` | **none** (only ref-count check) |
| KPI | `api/kpi_api.py:135-148` (`can_delete_kpis`) | `core/kpi/kpi_service.py:310` | **none** (only usage check) |

Role slug inside an endpoint: `request.orguser.new_role.slug` (e.g. `api/user_org_api.py:119`).

*Verified: 2026-06-17.*

---

## Data-infrastructure API modules

| Section | API module | Permission slugs (examples) |
|---|---|---|
| Ingest / Airbyte / Sources | `ddpui/api/airbyte_api.py` | `can_view_sources`, `can_create_source`, `can_edit_source` |
| Transform (dbt) | `ddpui/api/transform_api.py` | `can_view_dbtworkspace`, `can_create_dbtworkspace`, … |
| Warehouse | `ddpui/api/warehouse_api.py` | `can_view_warehouse_data`, … |
| Pipeline | `ddpui/api/pipeline_api.py` | `can_create_pipeline`, `can_edit_pipeline` |
| Orchestration / Org tasks | `ddpui/api/orgtask_api.py` | `can_view_orgtask`, `can_create_orgtask` |
| Data Quality | `ddpui/api/data_quality_api.py` *(confirm filename if unsure)* | `can_view_dataquality`, … |

Pattern in every module: Django Ninja router, `@router.get/post/...` + `@has_permission([...])`. Error responses are `raise HttpError(status, "human-readable message")`.

*Verified: 2026-06-05.*

---

## Org config + preferences

| Concern | Location |
|---|---|
| `OrgPreferences` model | `ddpui/models/org_preferences.py:7-39` (OneToOne with Org) |
| OrgPreferences API | `ddpui/api/org_preferences_api.py:28-80` |
| Existing fields | `llm_optin`, `llm_optin_approved_by`, `enable_discord_notifications`, `discord_webhook` |
| Permission for edits | `can_edit_llm_settings`, `can_edit_org_notification_settings` |

When adding new org-level toggles (e.g. `default_visibility_floor`, `allow_public_sharing`), this is the canonical place — don't introduce a parallel `org_settings` table.

*Verified: 2026-06-05.*

---

## Invitation flow

| Step | Location |
|---|---|
| `Invitation` model | `ddpui/models/org_user.py:142-151` (`invited_email`, `invited_by`, `invited_on`, `invite_code` UUID string, `invited_new_role` FK Role) |
| `NewInvitationSchema` | `ddpui/models/org_user.py:154-158` (`invited_email`, `invited_role_uuid`) |
| `AcceptInvitationSchema` | `ddpui/models/org_user.py:171-178` (`invite_code`, `password?`, `work_domain?`) |
| POST invite endpoint | `ddpui/api/user_org_api.py:470-477` |
| `invite_user_v1` function | `ddpui/core/orguserfunctions.py:205-267` |
| **Role-level cap (inviter ≥ invitee)** | `ddpui/core/orguserfunctions.py:217-218` |
| Email send (AWS SES) | `awsses.send_invite_user_email` at line 245 |
| POST accept endpoint | `ddpui/api/user_org_api.py:483-487` |
| `accept_invitation_v1` function | `ddpui/core/orguserfunctions.py` (search for it) |

Re-use this flow. Don't build a new invite path.

*Verified: 2026-06-05.*

---

## Migration conventions

| Pattern | Reference migration |
|---|---|
| Schema migration (`CreateModel`) | `ddpui/migrations/0063_permission_role_rolepermission.py` |
| Data migration (`RunPython` with forward + reverse) | `ddpui/migrations/0137_update_landing_page_permissions.py` (lines 1-82) — manipulates RolePermission rows; both forward and reverse implemented |
| Pattern for "get the model" inside RunPython | `apps.get_model("ddpui", "ModelName")` (don't import the model directly) |
| Redis cache clear at end of role/permission migrations | call `set_roles_and_permissions_in_redis()` at the end of the RunPython forward function |

**Always implement reverse** — Dalgo migrations are rolled back occasionally. Migrations without reverse functions block staging rollback.

*Verified: 2026-06-05.*

---

## Test conventions

| Concern | Reference |
|---|---|
| Framework | pytest + pytest-django |
| Module marker | `pytestmark = pytest.mark.django_db` |
| Template test file | `ddpui/tests/api_tests/test_dashboard_native_api.py` |
| `authuser` + `orguser` fixtures | top of `test_dashboard_native_api.py` |
| `seed_db` fixture (loads role/permission JSON) | `ddpui/tests/api_tests/test_user_org_api.py` (calls `call_command("loaddata", "001_roles.json")` etc.) |
| `mock_request` helper (builds `request.permissions` from `RolePermission`) | `ddpui/tests/api_tests/test_user_org_api.py:~1100-1115` |
| Assertion style | `assert response.status_code == 200`; `assert Model.objects.count() == N`; `assert "expected text" in str(exc.value)` |

Don't re-derive the mock-request pattern — import or copy it.

*Verified: 2026-06-05.*

---

## API conventions

| Concern | Convention |
|---|---|
| Web framework | Django Ninja (`from ninja import Router, Schema`) |
| Schemas | Pydantic via Ninja's `Schema`; lives in `ddpui/schemas/` |
| Error responses | `raise HttpError(status_code, "message")` |
| Route prefix | `/api/v1/...` under `ddpui/urls.py` |
| Org scoping | Every endpoint pulls `orguser = request.orguser` and filters all queries by `orguser.org`. No exceptions. |
| Multi-tenant safety | When fetching a resource by id, **always** include `org=request.orguser.org` in the filter — never just `pk=id` |

*Verified: 2026-06-05.*

---

## When this file gets stale

If a `Verified:` date is more than ~6 months old, or if a path no longer resolves, the easy fix is to spawn one targeted Explore agent (not a broad re-explore) and update the affected row in this file. The file's value is that it's small and current — keep it that way.
