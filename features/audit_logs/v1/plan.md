# Plan: Audit Logs — v1

## 1. Overview

A backend-only platform-wide audit logging system. Every significant user-initiated create/update/delete/lifecycle action across Dalgo writes one immutable record to a single `AuditLog` table.

- **Spec:** [../spec.md](../spec.md)
- **Services affected:** `DDP_backend` only. No `webapp_v2` UI changes in v1. No `prefect-proxy` changes.

## 2. Blast Radius

Audit Logging doesn't fit the usual "Entity A changed, who consumes A" shape. It's the inverse — it _observes_ write-actions across nearly every entity in the domain map, rather than consuming any one of them. So this table lists every entity from `docs/domain-map.md` and states whether its write-actions get an audit hook in this version.

| Surface | Hop distance | Why affected | Status | Notes |
|---|---|---|---|---|
| Source (Airbyte) | 0 (direct logging target) | CRUD + manual sync/reset are user-initiated actions | in scope | `api/airbyte_api.py` |
| Warehouse | 0 | Connect/update/remove are user-initiated | in scope | `api/user_org_api.py` |
| Transform (dbt) | 0 | ~20 distinct user actions across workspace, git, canvas, Elementary | in scope | `api/dbt_api.py`, `api/transform_api.py` — full list in spec.md Appendix A |
| Pipeline | 0 | CRUD, schedule toggle, manual trigger are user-initiated | in scope | `api/pipeline_api.py` |
| Data Quality check | 0 | Created/updated/deleted as pipeline steps | **deferred** | Confidence in domain map is `tribal-knowledge-needed` (blocking vs non-blocking unclear); this surface is still stabilizing. Add hooks once it's verified. |
| Chart | 0 | CRUD | in scope | `api/charts_api.py` |
| Metric | 0 | CRUD | in scope | `api/metric_api.py` |
| KPI | 0 | CRUD | in scope | `api/kpi_api.py` |
| Dashboard | 0 | CRUD, publish, share, lock, set-as-default | in scope | `api/dashboard_native_api.py` |
| ReportSnapshot | 0 | CRUD, share | in scope | `api/report_api.py` |
| Alert | 0 | Alert create/edit/delete are user-initiated | **deferred** | Alerts entity was still being scoped/shipped at the time of writing this plan. Add audit hooks as part of (or immediately after) the Alerts rollout, not retrofitted blind here. |
| Notification | 0 | System-generated, not user-initiated | **out of scope** | A Notification is itself a delivery mechanism, not a user action — nothing to audit. |
| Organization | 0 | Org created, logo/branding changed | in scope | `api/user_org_api.py` |
| OrgUser | 0 | Add/remove/role-change/invitations | in scope | `api/user_org_api.py` |
| Share link (Dashboard / ReportSnapshot mode) | 1 (mode of Dashboard/ReportSnapshot, not a standalone entity) | Already covered — share is a Dashboard or ReportSnapshot action, not a separate surface | in scope (via parent) | Same endpoints as Dashboard/ReportSnapshot |
| Explore | 0 | Ad-hoc, throwaway queries, no persisted artifact | **out of scope** | Nothing is created/updated/deleted to log |

All `in scope` rows are drawn from the events list in `spec.md` §5.1. The two `deferred` rows (Data Quality check, Alert) are explicitly flagged here rather than silently dropped — both surfaces are still evolving, per `docs/domain-map.md`'s own confidence tags.

## 3. High-Level Design (HLD)

Audit logging is implemented as a synchronous service-layer call, invoked from inside each existing API view function immediately after the underlying action succeeds. There is no new service, no message queue, and no async worker.

**The audit write can never break the main request.** It only runs after the real action has already succeeded, and `create_audit_log()` is designed to swallow its own failures internally (logged, never raised — see §4.3) rather than propagate them. So if the database write for the audit entry fails for any reason, the user's original action still returns success as normal; only the audit trail for that one action is missing, not the action itself.

**If the main action itself fails, no audit log entry is created.** The audit call sits after the real action succeeds in the code, so it never runs on a failure path. Every event is logged on success only — including login, with no exception.

```
User action --> Django Ninja API view --> existing service call (unchanged)
                                       --> create_audit_log() [NEW]
                                       --> response returned
```

Key design decisions:

- **Synchronous, in-request write.** Audit writes happen in the same request/response cycle as the action they record. This guarantees that if the write to `AuditLog` fails, it's surfaced immediately (logged, never raised) rather than silently lost in a background queue.
- **Single table, discriminated by `resource_type`.** One `AuditLog` model rather than per-resource tables, avoiding join complexity across very different resource shapes (a dashboard, a git repo switch, a login attempt).
- **No new external service integrations.** Airbyte, Prefect, and the warehouse are unaffected — audit logging only observes Dalgo's own API layer, not these external systems directly.
- **No new API surface for writing.** Audit entries are only ever created by `create_audit_log()` calls inside existing endpoints — there is no public "create an audit log" endpoint.
- **One new read endpoint.** `GET /api/audit-logs/` for querying, gated by a new permission (`can_view_audit_logs`) — see §4.2 and open question on role.

**Why not use an off-the-shelf audit library (e.g. `django-auditlog`, `django-simple-history`, `django-easy-audit`)?** These packages work by hooking into Django's `post_save` / `post_delete` model signals — they automatically log when a model instance changes. That fits a subset of our events well (Dashboard, Chart, Metric, KPI, Pipeline CRUD), but a large share of the events list in `spec.md` §5.1 aren't model saves at all: login (no row is saved at all on a login, success or attempted), dbt git pull, canvas lock/unlock, manual sync trigger, dashboard share. A signal-based library has no hook for any of these because nothing gets saved or deleted — they're just actions succeeding. Adopting one of these libraries would only cover roughly a third of our events, and we'd still need the custom `create_audit_log()` service layer for the rest — at that point we'd be maintaining two audit systems writing in two different shapes instead of one. The single custom service layer covers all ~70 events uniformly with one call pattern, which is simpler to maintain despite requiring more upfront wiring.

## 4. Low-Level Design (LLD)

### 4.1 Data model

New file: `DDP_backend/ddpui/models/audit_log.py`

```python
from django.db import models


class AuditLogResourceType(models.TextChoices):
    AUTH = "auth", "Auth"
    USER = "user", "User"
    ORG = "org", "Org"
    ORG_USER = "org_user", "Org User"
    INVITATION = "invitation", "Invitation"
    WAREHOUSE = "warehouse", "Warehouse"
    DATA_SOURCE = "data_source", "Data Source"
    CONNECTION = "connection", "Connection"
    PIPELINE = "pipeline", "Pipeline"
    DBT = "dbt", "dbt"
    DASHBOARD = "dashboard", "Dashboard"
    CHART = "chart", "Chart"
    METRIC = "metric", "Metric"
    KPI = "kpi", "KPI"
    REPORT = "report", "Report"
    COMMENT = "comment", "Comment"


class AuditLogAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    EXECUTE = "execute", "Execute"
    SHARE = "share", "Share"
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"


class AuditLogStatus(models.TextChoices):
    SUCCESS = "success", "Success"
    FAILURE = "failure", "Failure"


class AuditLog(models.Model):
    id = models.BigAutoField(primary_key=True)

    org = models.ForeignKey("ddpui.Org", on_delete=models.CASCADE, related_name="audit_logs")

    # orguser_email is denormalized so the log stays readable after the
    # OrgUser is deleted.
    orguser = models.ForeignKey(
        "ddpui.OrgUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    orguser_email = models.EmailField(max_length=255, blank=True)

    resource_type = models.CharField(max_length=50, choices=AuditLogResourceType.choices)
    resource_id = models.CharField(max_length=255, blank=True)
    resource_name = models.CharField(max_length=500, blank=True)

    action = models.CharField(max_length=50, choices=AuditLogAction.choices)

    # {"field_name": {"old": <value>, "new": <value>}, ...}
    # Never contains secrets — enforced by compute_changes()'s exclude list.
    changes = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20, choices=AuditLogStatus.choices, default=AuditLogStatus.SUCCESS
    )
    error_message = models.TextField(blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["org", "timestamp"], name="auditlog_org_ts_idx"),
            models.Index(fields=["org", "orguser", "timestamp"], name="auditlog_org_orguser_idx"),
            models.Index(
                fields=["org", "resource_type", "timestamp"], name="auditlog_org_restype_idx"
            ),
            models.Index(fields=["org", "action", "timestamp"], name="auditlog_org_action_idx"),
        ]
```

### 4.2 API design

New file: `DDP_backend/ddpui/api/audit_log_api.py`, registered on the existing Ninja router setup in `routes.py`.

**`GET /api/audit-logs/`** — list/query audit logs for the caller's org.

Query parameters:

| Param | Type | Notes |
|---|---|---|
| `orguser_email` | str, optional | partial match |
| `resource_type` | str, optional | exact match against `AuditLogResourceType` |
| `action` | str, optional | exact match against `AuditLogAction` |
| `resource_id` | str, optional | exact match |
| `start_date` | date, optional | inclusive |
| `end_date` | date, optional | inclusive |
| `status` | str, optional | `success` \| `failure` |
| `page` | int, default 1 | |
| `limit` | int, default 50, max 200 | |

Response: paginated list of `AuditLogSchema` (id, timestamp, orguser_email, resource_type, resource_id, resource_name, action, changes, status).

Permission: gated by `@has_permission(["can_view_audit_logs"])` — new permission slug to be seeded in `seed/permissions.json`. Which roles get this permission is decided as seed data (see spec.md §7), not hardcoded in the endpoint — a one-line change either way.

Always scoped to `request.orguser.org` — no cross-org query path in v1. If Dalgo's platform team needs cross-org visibility, that's a distinct superuser code path to design later, not a parameter on this endpoint.

### 4.3 Backend logic — service layer

New file: `DDP_backend/ddpui/core/audit_log_service.py`

```python
def create_audit_log(
    *,
    org,
    orguser,
    resource_type: str,
    resource_id: str,
    action: str,
    resource_name: str = "",
    changes: dict | None = None,
    status: str = AuditLogStatus.SUCCESS,
    error_message: str = "",
) -> AuditLog | None:
    """
    Creates one immutable audit log entry. Never raises — a failure to write
    an audit log must never break the primary request. Failures are logged
    via CustomLogger instead.
    """


def compute_changes(before: dict, after: dict, exclude_fields: list[str] | None = None) -> dict:
    """
    Diffs two flat dicts, returning only changed keys as
    {"field": {"old": x, "new": y}}. exclude_fields is mandatory for any
    resource that might carry secrets (passwords, tokens, credentials,
    share tokens) — callers must pass it explicitly for those resources.
    """
```

Call pattern (example — dashboard delete, `api/dashboard_native_api.py`):

```python
@dashboard_router.delete("/{dashboard_id}")
def delete_dashboard(request, dashboard_id: int):
    orguser = request.orguser
    dashboard = get_dashboard_or_404(dashboard_id)
    snapshot_name = dashboard.title

    dashboard_service.delete_dashboard(orguser, dashboard_id)  # unchanged

    create_audit_log(
        org=orguser.org,
        orguser=orguser,
        resource_type=AuditLogResourceType.DASHBOARD,
        resource_id=str(dashboard_id),
        resource_name=snapshot_name,
        action=AuditLogAction.DELETE,
    )
    return {"success": True}
```

This pattern is repeated at every in-scope endpoint listed in §2's Blast Radius table — roughly 60-70 call sites across `user_org_api.py`, `airbyte_api.py`, `pipeline_api.py`, `dbt_api.py`, `transform_api.py`, `dashboard_native_api.py`, `charts_api.py`, `metric_api.py`, `kpi_api.py`, `report_api.py`.

### 4.4 Frontend components

None in v1 — no `webapp_v2` changes. This is a backend-only implementation, per spec.md §1.

### 4.5 Integration points

- Audit calls are made directly from the Ninja view functions, after the existing service call succeeds — no new internal API contract between layers.
- No outbound calls to Airbyte, Prefect, or the warehouse are added; this feature only touches Dalgo's own request/response cycle.

## 5. Security Review

- **Authentication & Authorization:** the new `GET /api/audit-logs/` endpoint is protected by `@has_permission(["can_view_audit_logs"])`, consistent with every other endpoint in the codebase. Role-to-permission mapping is seed data — see spec.md §7 for which roles get this permission.
- **Input validation:** query parameters on the list endpoint are validated via a Pydantic/Ninja schema (enum-constrained `resource_type`, `action`, `status`; `limit` capped at 200) before hitting the ORM.
- **Data access control:** every query is scoped to `request.orguser.org` server-side — never trusts a client-supplied org filter. No multi-tenant leak path exists because there is no client-controllable "which org" parameter.
- **Sensitive data:** this is the highest-risk part of the feature. `compute_changes()` requires an explicit `exclude_fields` list for any resource that can carry secrets — passwords, API keys, git access tokens, warehouse credentials, public share tokens, JWTs. This must be enforced via code review on every call site, and covered by a unit test per sensitive resource type (see §6).
- **Injection risks:** no raw SQL or dynamic query construction — all reads go through the Django ORM with the indexed fields in §4.1.
- **External service calls:** none added by this feature.
- **Rate limiting / abuse:** the write path piggybacks on existing authenticated endpoints, so no new abuse surface. The read endpoint is permission-gated; no public/anonymous access.

## 6. Testing Strategy

- **Unit tests — service layer** (`core/audit_log_service.py`):
  - `create_audit_log()` writes the expected row for create/update/delete/login/logout actions.
  - `create_audit_log()` never raises, even when the DB write fails (mock a DB error, assert no exception propagates, assert it's logged).
  - `compute_changes()` correctly diffs two dicts and excludes fields in the exclude list.
- **Unit tests — secrets exclusion** (one per sensitive resource type): warehouse credentials, git access token, org logo upload, public share token — assert none of these ever appear in a `changes` JSON blob after going through the real call site.
- **API tests** (`tests/api_tests/test_audit_log_api.py`):
  - `GET /api/audit-logs/` returns only the caller's org's entries.
  - Filtering by `orguser_email`, `resource_type`, `action`, `status`, date range each work in isolation and combined.
  - Permission denial for a role without `can_view_audit_logs`.
  - Pagination behaves correctly at the `limit` boundary (200).
- **Integration / spot-check tests** — for a representative sample across each in-scope area (one from auth, one from dashboards, one from dbt, one from pipelines), assert that calling the real endpoint produces exactly one new `AuditLog` row with the expected `resource_type`/`action`.
- **Edge cases:** delete of an already-deleted resource (should not log twice), partial failures (action succeeds but audit write fails — assert primary action still returns success to the caller).

## 7. Milestones

#### Milestone 1: Core infrastructure

- **Deliverable:** `AuditLog` model + migration, `audit_log_service.py` (`create_audit_log`, `compute_changes`), `can_view_audit_logs` permission seeded.
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Create `models/audit_log.py` and migration
  - [ ] Implement `core/audit_log_service.py`
  - [ ] Seed `can_view_audit_logs` permission
  - [ ] Unit tests for service layer + secrets exclusion
- **Acceptance criteria:** `create_audit_log()` can be called standalone and produces a correct row; no call site wired up yet.

#### Milestone 2: Auth & user management events

- **Deliverable:** All events in spec.md §5.1 "Login & Authentication" and "User & Organization Management" (including Settings & Branding) are logged.
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Wire `user_org_api.py`: login, logout, password change/reset, email verify
  - [ ] Wire user/org management: add/remove user, role change, invitations (sent/resent/accepted/deleted), org created
  - [ ] Wire branding: logo upload/update/delete
- **Acceptance criteria:** each event in the requirements list produces exactly one `AuditLog` row with correct orguser/action/resource fields.

#### Milestone 3: Data infrastructure events

- **Deliverable:** Warehouse, Data Sources/Connections, Pipelines, and the full dbt event list (Appendix A) are logged.
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Wire warehouse CRUD
  - [ ] Wire `airbyte_api.py`: source/connection CRUD, manual sync, reset, schema change
  - [ ] Wire `pipeline_api.py`: pipeline CRUD, schedule toggle, manual trigger
  - [ ] Wire `dbt_api.py` + `transform_api.py`: all ~20 events from Appendix A
- **Acceptance criteria:** same as Milestone 2, applied to this set; dbt secrets (git tokens) verified excluded from `changes`.

#### Milestone 4: Analytics & reporting events

- **Deliverable:** Dashboards, Charts, Metrics, KPIs, Reports & Comments are logged.
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Wire `dashboard_native_api.py`: CRUD, publish, share (unshare logs as a regular update), lock/unlock, set-as-default, filters
  - [ ] Wire `charts_api.py`: CRUD
  - [ ] Wire `metric_api.py` + `kpi_api.py`: CRUD
  - [ ] Wire `report_api.py`: CRUD, share (unshare logs as a regular update), comments
- **Acceptance criteria:** same pattern as above; share-token values verified excluded from `changes`.

#### Milestone 5: Query API & retention

- **Deliverable:** `GET /api/audit-logs/` ships; retention cleanup ships once the team confirms the retention policy (§8).
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Implement and test the list/filter/paginate endpoint
  - [ ] Implement `purge_old_audit_logs` management command (retention period as a parameter, default TBD per open question). Building it as a manually-invoked command keeps both options open — it can be left as a manual tool or wired to a scheduled job once the team decides whether removal should be automatic.
  - [ ] Full API test suite for the endpoint
- **Acceptance criteria:** an org admin (or whichever role is confirmed) can query and filter their org's audit history; old logs are purged per whatever retention policy the team confirms.

## 8. Open Questions & Risks

- **Role gating for the query endpoint** — blocks finalizing the permission seed data for Milestone 5. Carried over from spec.md §7.
- **Retention policy** — whether removal should be automatic or manual, and if automatic, what period. Blocks finalizing whether `purge_old_audit_logs` stays a manual tool or gets wired to a scheduled job, and its default period. Carried over from spec.md §7.
- **Migration risk** — none. This is a net-new table; no existing data is migrated.
