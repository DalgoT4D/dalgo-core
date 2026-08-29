# Plan: Audit Logs — v1

## 1. Overview

A backend-only platform-wide audit logging system. Every significant user-initiated create/update/delete/lifecycle action across Dalgo writes one immutable record to a single `AuditLog` table.

- **Spec:** [../spec.md](../spec.md)
- **Services affected:** `DDP_backend` only. No `webapp_v2` UI changes in v1. No `prefect-proxy` changes.

## 2. Blast Radius

Audit Logging doesn't fit the usual "Entity A changed, who consumes A" shape. It's the inverse — it _observes_ write-actions across nearly every entity in the domain map, rather than consuming any one of them. So this table lists every entity from `docs/domain-map.md` and states whether its write-actions get an audit hook in this version.

| Surface | Hop distance | Why affected | Status | Notes |
|---|---|---|---|---|
| Source (Airbyte) | 0 (direct logging target) | CUD + manual sync/reset are user-initiated actions | in scope | `api/airbyte_api.py`. Source, Destination, and Connection CUD log `name`/`sourceDefId`/`destinationDefId` (or `name`/`streams`/`destinationSchema` for Connections) directly from the payload; `config` (Source/Destination credentials) is never logged. Connection `streams` is summarized to stream names via `_summarize_streams()` rather than logging the full `syncCatalog` (internal Airbyte field-type plumbing, not human-meaningful) — the payload's `streams` shape is untyped and callers have sent both plain strings and `{streamName, streamNamespace}` dicts, so the helper handles both. No external Airbyte call is made just to produce the audit log. |
| Warehouse | 0 | Connect/update/remove are user-initiated | in scope | `api/user_org_api.py`. `post_organization_warehouse` logs `wtype`/`name` only; `airbyteConfig` (raw warehouse credentials, e.g. BigQuery service-account JSON or Postgres password) is never logged. |
| Transform (dbt) | 0 | ~16 distinct user actions across workspace, git, canvas | in scope | `api/dbt_api.py`, `api/transform_api.py` — full list in spec.md Appendix A. `put_switch_git_repo` logs `gitrepo_url`/`is_repo_managed_by_system` read back from the DB after the git-repo switch completes (these are a side effect of the service call, not present in the payload) — `gitrepoAccessToken` (the PAT) is never logged. `put_dbt_schema_v1` logs `default_schema` straight from the payload. |
| Pipeline | 0 | CUD, schedule toggle, manual trigger are user-initiated | in scope | `api/pipeline_api.py` |
| Data Quality check | 0 | Created/updated/deleted as pipeline steps | **deferred** | Confidence in domain map is `tribal-knowledge-needed` (blocking vs non-blocking unclear); this surface is still stabilizing. Add hooks once it's verified. |
| Chart | 0 | CUD, CSV export | in scope | `api/charts_api.py`. CSV export logged in `download_chart_data_csv` (action=`export`, resource identified by `schema.table` — this endpoint has no `chart_id`, so exports aren't tied to a specific saved Chart record). PNG/PDF export is **out of scope**: both are generated entirely client-side (`lib/chart-export.ts`, canvas + jsPDF) and never reach the backend, so there's no request to hook an audit write into without adding a dedicated frontend-triggered logging call — not implemented yet. `ChartService.update_chart` is a genuine partial patch (`is not None` checks), so only touched fields are logged. |
| Metric | 0 | CUD | in scope | `api/metric_api.py`. No prior-state fetch — full definition (name, description, schema/table, aggregation or expression) is logged on both create and update; no resolver needed (no opaque foreign-key ids on this resource). |
| KPI | 0 | CUD | in scope | `api/kpi_api.py`. `KPIUpdate` is a genuine partial patch (`KPIService` uses `model_dump(exclude_unset=True)`), so only fields actually present in a request are logged, using that exact same criterion; `metric_id` is resolved to the metric's real name. |
| Dashboard | 0 | CUD, publish, share, set-as-default | in scope | `api/dashboard_native_api.py`. `DashboardService.update_dashboard` is a genuine partial patch (`is not None` checks; auto-save may send just one field), so only touched fields are logged. Writing a row is skipped when this specific request touched zero fields, or when none of the touched fields actually differ from what's already saved (checked against a pre-update fetch — see §4.1) — this avoids a noisy row on every tab switch-away, since the frontend's save-on-tab-away flow always sends a full payload even when nothing was edited. `tabs` (chart/KPI layout) is logged in full, straight from the payload — no summarizing, since the payload already carries the complete tab state on every save. |
| ReportSnapshot | 0 | CUD, share | in scope | `api/report_api.py`. `SnapshotUpdate` has only one editable field (`summary`). `create_snapshot` resolves `dashboard_id` to the frozen dashboard's title (`s.frozen_dashboard.get("title")`), not a raw id. **Gotcha:** `period_start`/`period_end` are Python `date` objects — the default `JSONField` encoder can't serialize those, and `create_audit_log()` never raises, so logging them raw would silently drop the audit row with no error anywhere. Fixed by converting to `.isoformat()` strings before logging; verified with a real (non-mocked) DB write, not just a mocked assertion. Update skips logging if nothing was actually sent. |
| Alert | 0 | Alert create/edit/delete/toggle are user-initiated | in scope | `api/alert_api.py`. Originally deferred here (Alerts was still being scoped/shipped at plan-writing time); added once the Alerts rollout stabilized. Source metric/KPI is resolved to its name, not id; `slack_webhook_url` is deliberately never logged. |
| Notification | 0 | System-generated, not user-initiated | **out of scope** | A Notification is itself a delivery mechanism, not a user action — nothing to audit. |
| Organization | 0 | Org created, logo/branding changed | in scope | `api/user_org_api.py` |
| OrgUser | 0 | Add/remove/role-change/invitations | in scope | `api/user_org_api.py`. `post_modify_orguser_role` logs `{"role": <new role slug>}`; invitation-accept logs `{"status": "accepted"}`; invitation-resend logs `{"action": "resent"}`. |
| Share link (Dashboard / ReportSnapshot mode) | 1 (mode of Dashboard/ReportSnapshot, not a standalone entity) | Already covered — share is a Dashboard or ReportSnapshot action, not a separate surface | in scope (via parent) | Same endpoints as Dashboard/ReportSnapshot |
| Explore | 0 | Ad-hoc, throwaway queries, no persisted artifact | **out of scope** | Nothing is created/updated/deleted to log |

All `in scope` rows are drawn from the events list in `spec.md` §5.1. The `deferred` row (Data Quality check) is explicitly flagged here rather than silently dropped — that surface is still evolving, per `docs/domain-map.md`'s own confidence tags. (Alert was deferred for the same reason at plan-writing time but has since been implemented — see row above.)

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
    ALERT = "alert", "Alert"


class AuditLogAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    EXECUTE = "execute", "Execute"
    SHARE = "share", "Share"
    EXPORT = "export", "Export"
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    # A dedicated action per AUTH event — the action alone says what
    # happened, with no need for any extra disambiguating text.
    PASSWORD_RESET_REQUESTED = "password_reset_requested", "Password Reset Requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed", "Password Reset Completed"
    PASSWORD_CHANGED = "password_changed", "Password Changed"
    EMAIL_VERIFIED = "email_verified", "Email Verified"


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

    action = models.CharField(max_length=50, choices=AuditLogAction.choices)

    # A flat snapshot of the resource's current identifying fields — see
    # §4.1 below. Never contains secrets; each call site curates this field
    # explicitly by hand.
    resource_fields = models.JSONField(default=dict, blank=True)

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

> **`resource_fields` holds a snapshot of the resource's current values** — `{"field": value, ...}`. History is reconstructed by querying all rows for a given `resource_id` in timestamp order and reading them as a sequence of snapshots; comparing two adjacent rows shows what changed between them.
>
> **Every successful create/update/delete writes exactly one row, straight from the request.** No prior-state fetch, no diffing.
>
> **Dashboard's `update_dashboard` is the one exception, by design.** Its frontend auto-saves on every tab-switch-away (part of the multi-user edit lock — see `rules/dashboards.md`), which would otherwise write a noisy row even when nothing was actually edited. So this one endpoint fetches the dashboard's current row first, and skips writing a row if none of the touched fields actually differ from what's already saved. (`description` needs a small normalization here: the DB stores an unset description as `None`, but the frontend always sends `""`, so `None` and `""` are treated as equal when deciding whether it changed — otherwise a dashboard's very first auto-save would look like a real edit.) No other resource does this — every other resource always writes a row on a successful action, with no comparison.
>
> **Every `resource_fields` is self-identifying** — it always includes the resource's own name/title (e.g. `{"title": "Sales Dashboard", ...}`), even on delete and even on a partial update that didn't touch that field, so a single row makes sense to a reader without needing to look anything else up. `resource_type` + `resource_id` + `resource_fields` is the complete identity of every logged row — there is no separate name field on the model.

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
    resource_fields: dict | None = None,
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
                "action": action,
                "resource_fields": resource_fields or {},
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
    action: str,
    resource_fields: dict,
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
            action=action,
            resource_fields=resource_fields,
        )
    except Exception as err:
        logger.error("audit_log_service: failed to write audit log", exc_info=err)
    finally:
        django.db.connection.close()
```

Call pattern (example — dashboard delete, `api/dashboard_native_api.py`):

```python
@dashboard_router.delete("/{dashboard_id}")
def delete_dashboard(request, dashboard_id: int):
    orguser = request.orguser
    org = orguser.org

    dashboard_name = DashboardService.delete_dashboard(dashboard_id, org, orguser)

    create_audit_log(
        org=org,
        orguser=orguser,
        resource_type=AuditLogResourceType.DASHBOARD,
        resource_id=str(dashboard_id),
        action=AuditLogAction.DELETE,
        resource_fields={"title": dashboard_name},
    )
    return {"success": True}
```

**On every delete endpoint, the service returns the resource's name/title — the API layer never fetches the resource itself.** Earlier, a common pattern was for the API view to fetch the resource first (e.g. `get_dashboard_or_404`) purely to grab its name for the audit log, then call the service separately to actually delete it — two reads of the same row for one request. Every `delete_*` service method (KPI, Metric, Chart, Dashboard, Alert, ReportSnapshot, Comment, Pipeline, Warehouse) now returns the deleted resource's identifying name/title (or, for bulk/pipeline operations, adds it to the dict the service already returns) instead of a bare `True`/`{"success": 1}`, so the one fetch the service already needs to do (for the delete itself) is the only fetch — the API layer just reads the return value.

This pattern is repeated at every in-scope endpoint listed in §2's Blast Radius table — roughly 60-70 call sites across `user_org_api.py`, `airbyte_api.py`, `pipeline_api.py`, `dbt_api.py`, `transform_api.py`, `dashboard_native_api.py`, `charts_api.py`, `metric_api.py`, `kpi_api.py`, `report_api.py`.

Call pattern for an update (example — pipeline update, `api/pipeline_api.py`):

```python
@pipeline_router.put("v1/flows/{deployment_id}")
def put_prefect_dataflow_v1(request, deployment_id, payload: PrefectDataFlowUpdateSchema3):
    orguser = request.orguser
    result = PipelineService.update_pipeline(orguser.org, deployment_id, payload)  # unchanged

    create_audit_log(
        org=orguser.org,
        orguser=orguser,
        resource_type=AuditLogResourceType.PIPELINE,
        resource_id=deployment_id,
        action=AuditLogAction.UPDATE,
        resource_fields={
            "name": payload.name or "",
            "cron": payload.cron,
            "connections": _resolve_connection_names([c.id for c in payload.connections]),
            "transform_tasks": _resolve_transform_task_labels(orguser.org, payload.transformTasks),
        },
    )
    return result
```

Every successful update writes a row straight from `payload` — no prior-state fetch, no diffing. `_resolve_connection_names` / `_resolve_transform_task_labels` translate opaque IDs into human-readable names/labels before they're logged — raw connection UUIDs or task UUIDs alone aren't useful to a human reading the log later.

**Not every resource's update payload is a full replace like Pipeline's, though — check the real frontend form before assuming.** `AlertUpdate` (`api/alert_api.py`) is a genuine partial patch: `AlertService` only touches a field when it's not `None`, so a request can legitimately update just one field and leave the rest untouched. Logging every declared field there (with `None` for the untouched ones) would misrepresent "not touched" as "cleared." The fix is a plain filter after building the candidate dict:

```python
raw_resource_fields = {
    "name": payload.name,
    "source": _resolve_alert_source_label(...),  # resolves to None if no source field was sent
    "condition": payload.condition.model_dump() if payload.condition is not None else None,
    ...
}
resource_fields = {k: v for k, v in raw_resource_fields.items() if v is not None}
```

This mirrors the exact same `is not None` check the service layer already uses to decide what to update — "what we log" and "what actually changed" are guaranteed to use the same signal. Before wiring a new resource's audit call, check whether its real frontend form sends a full payload (like Pipeline, Chart, and Dashboard do) or a genuine partial patch (like Alert) — the backend schema being `Optional` on every field does **not** tell you which; only reading the actual service logic and the frontend call site does.

**KPI (`api/kpi_api.py`) is a third variant, worth knowing about separately.** Its real frontend form (`kpi-form.tsx`) happens to send almost every field on every edit today — so, going only by observed behavior, it looks "full" like Pipeline. But `KPIService.update_kpi` is genuinely built as a partial-patch service (`payload.model_dump(exclude_unset=True)`, not an `is not None` check) — it just isn't exercised as partial by this one form *yet*. Rather than bake in an assumption that could silently break if the form (or another API consumer) changes later, the audit call uses the identical `exclude_unset=True` call the service itself uses:

```python
touched = payload.model_dump(exclude_unset=True)
resource_fields = {k: v for k, v in touched.items() if k != "metric_id"}
if "metric_id" in touched:
    resource_fields["metric"] = kpi.metric.name  # resolved name, not the raw id
```

The rule of thumb: don't just check what today's frontend sends — check what the *service* treats as "touched," and match that exact mechanism. A resource's backend can be genuinely partial-capable even when its only current caller happens to always send everything.

### 4.3 Frontend components

None in v1 — no `webapp_v2` changes. This is a backend-only implementation, per spec.md §1.

### 4.4 Integration points

- Audit calls are made directly from the Ninja view functions, after the existing service call succeeds — no new internal API contract between layers.
- **Audit log writes use Python's `threading` module as the background task runner** — the write happens in a daemon thread, decoupled from the request/response cycle.
- **Celery Beat is used only for the monthly purge** (`purge_old_audit_logs`) — same pre-existing Celery Beat infrastructure already used for alert scheduling.
- No outbound calls to Airbyte, Prefect, or the warehouse are added; this feature only touches Dalgo's own request/response cycle.

## 5. Security Review

- **Authentication & Authorization:** no read API in v1 (spec.md §3), so no `@has_permission` gate to review yet. Writes only happen from inside existing, already-authenticated endpoints.
- **Sensitive data:** this is the highest-risk part of the feature regardless of v1's scope. **There is no automatic exclusion mechanism** — each call site builds `resource_fields` by hand from named fields, so a secret only stays out if the developer simply never adds it to that dict. Confirmed live example: Alert's `slack_webhook_url` (a real, usable Slack webhook URL) is deliberately never included in `resource_fields` on either create or update — the frontend itself already treats it as sensitive (masked in the UI, only sent when the user actively retypes it). This must be enforced via code review on every call site, and covered by a unit test per sensitive resource type (see §6).
- **Injection risks:** no raw SQL or dynamic query construction on the write path — `_write_audit_log` writes through the Django ORM, using the indexed fields in §4.1.
- **External service calls:** none added by this feature.
- **Rate limiting / abuse:** the write path piggybacks on existing authenticated endpoints, so no new abuse surface. With no read endpoint in v1, there's no public/anonymous read surface to consider either.

## 6. Testing Strategy

- **Unit tests — service layer** (`core/audit_log_service.py`):
  - `create_audit_log()` starts a thread that calls `_write_audit_log` with the correct arguments for create/update/delete/login/logout actions.
  - `create_audit_log()` never raises, even when `threading.Thread.start()` fails (mock the exception, assert it's caught and logged, assert the primary action is unaffected).
  - `_write_audit_log()` writes the expected `AuditLog` row to the DB; if the DB write fails, error is logged and not re-raised.
- **Unit tests — secrets exclusion** (one per sensitive resource type): warehouse credentials, git access token, org logo upload, public share token, Alert's `slack_webhook_url` — assert none of these ever appear in a `resource_fields` JSON blob after going through the real call site.
- **Unit tests — `resource_fields` content**:
  - Every create/update call asserts the exact `resource_fields` content, not just that `create_audit_log()` was called.
  - Opaque IDs (connection UUIDs, task UUIDs, metric/kpi ids) resolve to human-readable names/labels in the logged output — never raw IDs. See `test_pipeline_api.py::test_post_prefect_dataflow_v1_audit_log_resolves_names` (Pipeline: connection/task names) and `test_alert_api.py::test_create_alert_creates_audit_log` (Alert: metric/kpi name resolved via `_resolve_alert_source_label`).
  - No prior-state DB fetch happens before the audit call, for any resource except Dashboard's `update_dashboard` (§4.1).
  - For resources with a genuinely partial update payload (e.g. Alert, KPI, Chart, Dashboard), a request touching only some fields logs only those fields — see `test_alert_api.py::test_update_alert_creates_audit_log_only_touched_fields`, `test_kpi_api.py::TestKPIAuditLogs::test_update_kpi_creates_audit_log` / `::test_update_kpi_change_metric_logs_resolved_name`, `test_charts_api.py::test_update_chart_creates_audit_log`, and `test_dashboard_native_api.py::test_update_dashboard_creates_audit_log` / `::test_update_dashboard_tabs_logs_full_tabs_json` (the latter also confirms large nested fields like `tabs` are logged in full, not summarized).
  - A request that touches zero fields writes no row at all — see `test_dashboard_native_api.py::test_update_dashboard_no_fields_touched_skips_audit_log`. Currently only implemented for Dashboard; consider applying the same guard to Alert/KPI/Chart once confirmed.
  - **Gotcha for any resource with date/datetime fields**: the default `JSONField` encoder used by `AuditLog.resource_fields` cannot serialize Python `date`/`datetime` objects, and `create_audit_log()` never raises — so logging one raw silently drops the entire audit row with no error anywhere. Always convert to `.isoformat()` strings before putting a date value into `resource_fields`, and verify with a real (non-mocked) `AuditLog.objects.create(...)` call, not just a mocked assertion — a mock never exercises Django's actual JSON serialization, so it would not have caught this.
- **Integration / spot-check tests** — for a representative sample across each in-scope area (one from auth, one from dashboards, one from dbt, one from pipelines), assert that calling the real action endpoint (e.g. `DELETE /api/dashboards/{id}`) produces exactly one new `AuditLog` row with the expected `resource_type`/`action`. Call `thread.join()` in the test to wait for the background write to complete before asserting.
- **Edge cases:** delete of an already-deleted resource (should not log twice), thread write failure (DB error — assert primary action still returns success, error is logged).

## 7. Milestones

#### Milestone 1: Core infrastructure

- **Deliverable:** `AuditLog` model + migration, `audit_log_service.py` (`create_audit_log`, `_write_audit_log`).
- **Services:** DDP_backend
- **Key tasks:**
  - [x] Create `models/audit_log.py` and migration
  - [x] Implement `core/audit_log_service.py` (thread-based write, never raises)
  - [x] Unit tests for service layer + secrets exclusion
- **Acceptance criteria:** `create_audit_log()` can be called standalone; the background thread writes a correct `AuditLog` row (use `thread.join()` in tests to wait for the write); no call site wired up yet.

#### Milestone 2: Auth & user management events

- **Deliverable:** All events in spec.md §5.1 "Login & Authentication" and "User & Organization Management" (including Settings & Branding) are logged.
- **Services:** DDP_backend
- **Key tasks:**
  - [x] Wire `user_org_api.py`: login, logout, password change/reset, email verify
  - [x] Wire user/org management: add/remove user, role change, invitations (sent/resent/accepted/deleted), org created
  - [x] Wire branding: logo upload/update/delete
- **Acceptance criteria:** each event in the requirements list produces exactly one `AuditLog` row with correct orguser/action/resource fields.

#### Milestone 3: Data infrastructure events

- **Deliverable:** Warehouse, Data Sources/Connections, Pipelines, and the full dbt event list (Appendix A) are logged.
- **Services:** DDP_backend
- **Key tasks:**
  - [x] Wire warehouse create/delete — **done** (`wtype`/`name` logged on create, `name` logged on delete; `airbyteConfig` credentials never logged). There is no dedicated warehouse-update endpoint in the product — only create and delete exist — so there's nothing to wire for "update."
  - [x] Wire `airbyte_api.py`: source/connection CUD, manual sync, reset, schema change — **done** (`config`/credentials never logged; Connection `streams` summarized to stream names via `_summarize_streams()`). See `test_airbyte_api.py` and `test_airbyte_api_v1.py` for audit-log-specific coverage.
  - [x] Wire `pipeline_api.py`: pipeline CUD, schedule toggle, manual trigger — **done** (connection IDs resolved via `ConnectionMeta` to real connection names, transform task UUIDs resolved to task labels). See `test_pipeline_api.py` for the audit-log-specific test coverage.
  - [x] Wire `dbt_api.py` + `transform_api.py`: all ~16 events from Appendix A — **done**. `put_switch_git_repo` logs `gitrepo_url`/`is_repo_managed_by_system` read back from the DB after the switch; `put_dbt_schema_v1` logs `default_schema` straight from the payload. See `test_dbt_api.py::test_put_switch_git_repo_creates_audit_log` / `::test_put_dbt_schema_v1_creates_audit_log` for the audit-log-specific coverage.
- **Acceptance criteria:** same as Milestone 2, applied to this set; dbt secrets (git tokens) verified excluded from `resource_fields`.

#### Milestone 4: Analytics & reporting events

- **Deliverable:** Dashboards, Charts, Metrics, KPIs, Reports & Comments are logged.
- **Services:** DDP_backend
- **Key tasks:**
  - [x] Wire `dashboard_native_api.py`: CUD, publish, share (unshare logs as a regular update), set-as-default, filters
  - [x] Wire `charts_api.py`: CUD
  - [x] Wire `metric_api.py` + `kpi_api.py`: CUD
  - [x] Wire `report_api.py`: CUD, share (unshare logs as a regular update), comments
- **Acceptance criteria:** same pattern as above; share-token values verified excluded from `resource_fields`.

#### Milestone 5: Retention

- **Deliverable:** `purge_old_audit_logs` management command + a Celery Beat periodic task that runs it automatically on a monthly schedule. Retention period is configurable via `AUDIT_LOG_RETENTION_DAYS` env variable so it can be changed without a code deployment.
- **Services:** DDP_backend
- **Key tasks:**
  - [x] Implement `purge_old_audit_logs` management command. Reads `AUDIT_LOG_RETENTION_DAYS` from the environment (default: 365) — so changing from 1 year to 6 months is a single env var update with no code change required.
  - [x] Register a Celery Beat periodic task (monthly cadence) to call this command automatically — following the same pattern used by `dispatch_due_alerts` in `ddpui/celeryworkers/alert_tasks.py`.
- **Acceptance criteria:** the periodic task runs automatically every month and removes all `AuditLog` rows older than `AUDIT_LOG_RETENTION_DAYS` days; engineers can also run the command manually on demand if needed.

## 8. Open Questions & Risks

- **Migration risk** — none. This is a net-new table; no existing data is migrated.
- **Thread write loss on restart (accepted)** — if a Django worker restarts while a background thread is mid-write, that audit entry is lost with no retry. This is a deliberate trade-off: audit log writes are eventually consistent, not guaranteed — see HLD §3.
- **Thread ordering risk (accepted)** — if two actions happen on the same resource moments apart, the two background threads are not guaranteed to write in the exact order they were started. In rare cases the `timestamp` on rows could be slightly out of step with the true order of events. Not expected to be load-bearing for v1's use cases.
- **Org deletion cascades the audit trail (accepted for now)** — `org` is `on_delete=models.CASCADE` (§4.1). If an org is deleted, every audit log row for that org is deleted too, including any entry that would have recorded the deletion itself — there's no way to later show "this org was deleted, by whom, and when." In practice this is low-risk today since org deletion is a manual, engineer-run process (`manage.py deleteorg`, with a dry-run option), not a customer-facing or automated action. Kept as `CASCADE` for v1; revisit (e.g. `SET_NULL` + a denormalized `org_name`, mirroring the `orguser`/`orguser_email` pattern) if a need to retain audit history past org deletion comes up later.
