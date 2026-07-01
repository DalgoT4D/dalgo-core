# Plan: Audit Logs — v1

## 1. Overview

A backend-only platform-wide audit logging system. Every significant user-initiated create/update/delete/lifecycle action across Dalgo writes one immutable record to a single `AuditLog` table.

- **Spec:** [../spec.md](../spec.md)
- **Services affected:** `DDP_backend` only. No `webapp_v2` UI changes in v1. No `prefect-proxy` changes.

## 2. Blast Radius

Audit Logging doesn't fit the usual "Entity A changed, who consumes A" shape. It's the inverse — it _observes_ write-actions across nearly every entity in the domain map, rather than consuming any one of them. So this table lists every entity from `docs/domain-map.md` and states whether its write-actions get an audit hook in this version.

| Surface | Hop distance | Why affected | Status | Notes |
|---|---|---|---|---|
| Source (Airbyte) | 0 (direct logging target) | CUD + manual sync/reset are user-initiated actions | in scope | `api/airbyte_api.py` |
| Warehouse | 0 | Connect/update/remove are user-initiated | in scope | `api/user_org_api.py` |
| Transform (dbt) | 0 | ~16 distinct user actions across workspace, git, canvas | in scope | `api/dbt_api.py`, `api/transform_api.py` — full list in spec.md Appendix A |
| Pipeline | 0 | CUD, schedule toggle, manual trigger are user-initiated | in scope | `api/pipeline_api.py` |
| Data Quality check | 0 | Created/updated/deleted as pipeline steps | **deferred** | Confidence in domain map is `tribal-knowledge-needed` (blocking vs non-blocking unclear); this surface is still stabilizing. Add hooks once it's verified. |
| Chart | 0 | CUD | in scope | `api/charts_api.py` |
| Metric | 0 | CUD | in scope | `api/metric_api.py` |
| KPI | 0 | CUD | in scope | `api/kpi_api.py` |
| Dashboard | 0 | CUD, publish, share, set-as-default | in scope | `api/dashboard_native_api.py` |
| ReportSnapshot | 0 | CUD, share | in scope | `api/report_api.py` |
| Alert | 0 | Alert create/edit/delete are user-initiated | **deferred** | Alerts entity was still being scoped/shipped at the time of writing this plan. Add audit hooks as part of (or immediately after) the Alerts rollout, not retrofitted blind here. |
| Notification | 0 | System-generated, not user-initiated | **out of scope** | A Notification is itself a delivery mechanism, not a user action — nothing to audit. |
| Organization | 0 | Org created, logo/branding changed | in scope | `api/user_org_api.py` |
| OrgUser | 0 | Add/remove/role-change/invitations | in scope | `api/user_org_api.py` |
| Share link (Dashboard / ReportSnapshot mode) | 1 (mode of Dashboard/ReportSnapshot, not a standalone entity) | Already covered — share is a Dashboard or ReportSnapshot action, not a separate surface | in scope (via parent) | Same endpoints as Dashboard/ReportSnapshot |
| Explore | 0 | Ad-hoc, throwaway queries, no persisted artifact | **out of scope** | Nothing is created/updated/deleted to log |

All `in scope` rows are drawn from the events list in `spec.md` §5.1. The two `deferred` rows (Data Quality check, Alert) are explicitly flagged here rather than silently dropped — both surfaces are still evolving, per `docs/domain-map.md`'s own confidence tags.

## 3. High-Level Design (HLD)

Audit logging is implemented as a **background Python thread**, started from inside each existing API view function immediately after the underlying action succeeds. Python's built-in threading module is the background task runner for writes — it decouples the audit write from the request/response cycle with no external queue or broker needed.

**The audit write can never break or measurably slow the main request.** `create_audit_log()` starts a daemon thread and returns immediately — it does not wait for the row to be written. If starting the thread fails for any reason, that failure is caught and logged via `CustomLogger`, never raised — see §4.2. The user's original action always returns success as normal.

**If the main action itself fails, no audit log entry is created.** The thread is only started after the real action succeeds in the code, so it never runs on a failure path. Every event is logged on success only — including login, with no exception.

**Accepted trade-off:** if the Django worker process is restarted (e.g. a deploy) while a thread is mid-write, that audit entry is lost. This is acceptable at Dalgo's scale — the team explicitly chose simplicity over strict consistency for this feature.

```
User action --> API view --> existing service call (unchanged)
                         --> create_audit_log() --> starts daemon thread --> writes AuditLog row
                         --> response returned
```

Key design decisions:

- **Asynchronous, via Python thread.** Audit writes happen in a background daemon thread — the request does not wait for the DB write. Simple, zero new infrastructure, appropriate for Dalgo's scale.
- **Single table, discriminated by `resource_type`.** One `AuditLog` model rather than per-resource tables, avoiding join complexity across very different resource shapes (a dashboard, a git repo switch, a login attempt).
- **No new external service integrations.** Airbyte, Prefect, and the warehouse are unaffected — audit logging only observes Dalgo's own API layer, not these external systems directly.
- **No new API surface, write or read.** Audit entries are only ever created by `create_audit_log()` calls inside existing endpoints. No query endpoint either — deferred to v2 (spec.md §3).

**Why not use an off-the-shelf audit library (e.g. `django-auditlog`, `django-simple-history`, `django-easy-audit`)?** These packages work by hooking into Django's `post_save` / `post_delete` model signals — they automatically log when a model instance changes. That fits a subset of our events well (Dashboard, Chart, Metric, KPI, Pipeline CUD), but a large share of the events list in `spec.md` §5.1 aren't model saves at all: login (no row is saved at all on a login, success or attempted), dbt git pull, manual sync trigger, dashboard share. A signal-based library has no hook for any of these because nothing gets saved or deleted — they're just actions succeeding. Adopting one of these libraries would only cover roughly a third of our events, and we'd still need the custom `create_audit_log()` service layer for the rest — at that point we'd be maintaining two audit systems writing in two different shapes instead of one. The single custom service layer covers all ~70 events uniformly with one call pattern, which is simpler to maintain despite requiring more upfront wiring.

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
    field_changes = models.JSONField(default=dict, blank=True)

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

### 4.2 Backend logic — service layer

New file: `DDP_backend/ddpui/core/audit_log_service.py`

```python
# core/audit_log_service.py
import threading

import django.db

from ddpui.models.audit_log import AuditLog
from ddpui.utils.custom_logger import CustomLogger

logger = CustomLogger("ddpui.audit_log_service")


def create_audit_log(
    *,
    org,
    orguser,
    resource_type: str,
    resource_id: str,
    action: str,
    resource_name: str = "",
    field_changes: dict | None = None,
) -> None:
    """
    Writes an audit log entry in a background daemon thread. Never raises —
    if the thread fails to start or the DB write fails, the error is caught
    and logged so it never breaks the primary request.
    """
    try:
        t = threading.Thread(
            target=_write_audit_log,
            kwargs={
                "org_id": org.id,
                "orguser_id": orguser.id if orguser else None,
                "orguser_email": orguser.user.email if orguser else "",
                "resource_type": resource_type,
                "resource_id": resource_id,
                "resource_name": resource_name,
                "action": action,
                "field_changes": field_changes or {},
            },
            daemon=True,
        )
        t.start()
    except Exception as err:
        logger.error("audit_log_service: failed to start write thread", exc_info=err)


def _write_audit_log(
    *,
    org_id: int,
    orguser_id: int | None,
    orguser_email: str,
    resource_type: str,
    resource_id: str,
    resource_name: str,
    action: str,
    field_changes: dict,
) -> None:
    """
    Actual DB write — runs in a background daemon thread.

    Django database connections are thread-local: each thread gets its own
    connection from the pool, completely isolated from every other thread.
    Daemon threads do not go through Django's normal request teardown,
    which means the connection this thread opens would otherwise stay open
    indefinitely. The `finally` block closes it explicitly so it is returned
    to the pool after each write, preventing connection exhaustion.
    """
    try:
        AuditLog.objects.create(
            org_id=org_id,
            orguser_id=orguser_id,
            orguser_email=orguser_email,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            action=action,
            field_changes=field_changes,
        )
    except Exception as err:
        logger.error("audit_log_service: failed to write audit log", exc_info=err)
    finally:
        django.db.connection.close()


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

### 4.3 Frontend components

None in v1 — no `webapp_v2` changes. This is a backend-only implementation, per spec.md §1.

### 4.4 Integration points

- Audit calls are made directly from the Ninja view functions, after the existing service call succeeds — no new internal API contract between layers.
- **Audit log writes use Python's `threading` module as the background task runner** — the write happens in a daemon thread, decoupled from the request/response cycle.
- **Celery Beat is used only for the monthly purge** (`purge_old_audit_logs`) — same pre-existing Celery Beat infrastructure already used for alert scheduling.
- No outbound calls to Airbyte, Prefect, or the warehouse are added; this feature only touches Dalgo's own request/response cycle.

## 5. Security Review

- **Authentication & Authorization:** no read API in v1 (spec.md §3), so no `@has_permission` gate to review yet. Writes only happen from inside existing, already-authenticated endpoints.
- **Sensitive data:** this is the highest-risk part of the feature regardless of v1's scope. `compute_changes()` requires an explicit `exclude_fields` list for any resource that can carry secrets — passwords, API keys, git access tokens, warehouse credentials, public share tokens, JWTs. This must be enforced via code review on every call site, and covered by a unit test per sensitive resource type (see §6).
- **Injection risks:** no raw SQL or dynamic query construction on the write path — `_write_audit_log` writes through the Django ORM, using the indexed fields in §4.1.
- **External service calls:** none added by this feature.
- **Rate limiting / abuse:** the write path piggybacks on existing authenticated endpoints, so no new abuse surface. With no read endpoint in v1, there's no public/anonymous read surface to consider either.

## 6. Testing Strategy

- **Unit tests — service layer** (`core/audit_log_service.py`):
  - `create_audit_log()` starts a thread that calls `_write_audit_log` with the correct arguments for create/update/delete/login/logout actions.
  - `create_audit_log()` never raises, even when `threading.Thread.start()` fails (mock the exception, assert it's caught and logged, assert the primary action is unaffected).
  - `_write_audit_log()` writes the expected `AuditLog` row to the DB; if the DB write fails, error is logged and not re-raised.
  - `compute_changes()` correctly diffs two dicts and excludes fields in the exclude list.
- **Unit tests — secrets exclusion** (one per sensitive resource type): warehouse credentials, git access token, org logo upload, public share token — assert none of these ever appear in a `field_changes` JSON blob after going through the real call site.
- **Integration / spot-check tests** — for a representative sample across each in-scope area (one from auth, one from dashboards, one from dbt, one from pipelines), assert that calling the real action endpoint (e.g. `DELETE /api/dashboards/{id}`) produces exactly one new `AuditLog` row with the expected `resource_type`/`action`. Call `thread.join()` in the test to wait for the background write to complete before asserting.
- **Edge cases:** delete of an already-deleted resource (should not log twice), thread write failure (DB error — assert primary action still returns success, error is logged).

## 7. Milestones

#### Milestone 1: Core infrastructure

- **Deliverable:** `AuditLog` model + migration, `audit_log_service.py` (`create_audit_log`, `_write_audit_log`, `compute_changes`).
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Create `models/audit_log.py` and migration
  - [ ] Implement `core/audit_log_service.py` (thread-based write, never raises)
  - [ ] Unit tests for service layer + secrets exclusion
- **Acceptance criteria:** `create_audit_log()` can be called standalone; the background thread writes a correct `AuditLog` row (use `thread.join()` in tests to wait for the write); no call site wired up yet.

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
  - [ ] Wire warehouse CUD
  - [ ] Wire `airbyte_api.py`: source/connection CUD, manual sync, reset, schema change
  - [ ] Wire `pipeline_api.py`: pipeline CUD, schedule toggle, manual trigger
  - [ ] Wire `dbt_api.py` + `transform_api.py`: all ~16 events from Appendix A
- **Acceptance criteria:** same as Milestone 2, applied to this set; dbt secrets (git tokens) verified excluded from `field_changes`.

#### Milestone 4: Analytics & reporting events

- **Deliverable:** Dashboards, Charts, Metrics, KPIs, Reports & Comments are logged.
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Wire `dashboard_native_api.py`: CUD, publish, share (unshare logs as a regular update), set-as-default, filters
  - [ ] Wire `charts_api.py`: CUD
  - [ ] Wire `metric_api.py` + `kpi_api.py`: CUD
  - [ ] Wire `report_api.py`: CUD, share (unshare logs as a regular update), comments
- **Acceptance criteria:** same pattern as above; share-token values verified excluded from `field_changes`.

#### Milestone 5: Retention

- **Deliverable:** `purge_old_audit_logs` management command + a Celery Beat periodic task that runs it automatically on a monthly schedule. Entries older than 1 year are deleted with no manual intervention needed.
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Implement `purge_old_audit_logs` management command with `--days` parameter defaulting to 365.
  - [ ] Register a Celery Beat periodic task (monthly cadence) to call this command automatically — following the same pattern used by `dispatch_due_alerts` in `ddpui/celeryworkers/alert_tasks.py`.
- **Acceptance criteria:** the periodic task runs automatically every month and removes all `AuditLog` rows older than 365 days; engineers can also run the command manually on demand if needed.

## 8. Open Questions & Risks

- **Migration risk** — none. This is a net-new table; no existing data is migrated.
- **Thread write loss on restart (accepted)** — if a Django worker restarts while a background thread is mid-write, that audit entry is lost with no retry. This is a deliberate trade-off: audit log writes are eventually consistent, not guaranteed — see HLD §3.
- **Thread ordering risk (accepted)** — if two actions happen on the same resource moments apart, the two background threads are not guaranteed to write in the exact order they were started. In rare cases the `timestamp` on rows could be slightly out of step with the true order of events. Not expected to be load-bearing for v1's use cases.
- **Org deletion cascades the audit trail (accepted for now)** — `org` is `on_delete=models.CASCADE` (§4.1). If an org is deleted, every audit log row for that org is deleted too, including any entry that would have recorded the deletion itself — there's no way to later show "this org was deleted, by whom, and when." In practice this is low-risk today since org deletion is a manual, engineer-run process (`manage.py deleteorg`, with a dry-run option), not a customer-facing or automated action. Kept as `CASCADE` for v1; revisit (e.g. `SET_NULL` + a denormalized `org_name`, mirroring the `orguser`/`orguser_email` pattern) if a need to retain audit history past org deletion comes up later.
