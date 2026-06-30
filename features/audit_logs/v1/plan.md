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
| Dashboard | 0 | CRUD, publish, share, set-as-default | in scope | `api/dashboard_native_api.py` |
| ReportSnapshot | 0 | CRUD, share | in scope | `api/report_api.py` |
| Alert | 0 | Alert create/edit/delete are user-initiated | **deferred** | Alerts entity was still being scoped/shipped at the time of writing this plan. Add audit hooks as part of (or immediately after) the Alerts rollout, not retrofitted blind here. |
| Notification | 0 | System-generated, not user-initiated | **out of scope** | A Notification is itself a delivery mechanism, not a user action — nothing to audit. |
| Organization | 0 | Org created, logo/branding changed | in scope | `api/user_org_api.py` |
| OrgUser | 0 | Add/remove/role-change/invitations | in scope | `api/user_org_api.py` |
| Share link (Dashboard / ReportSnapshot mode) | 1 (mode of Dashboard/ReportSnapshot, not a standalone entity) | Already covered — share is a Dashboard or ReportSnapshot action, not a separate surface | in scope (via parent) | Same endpoints as Dashboard/ReportSnapshot |
| Explore | 0 | Ad-hoc, throwaway queries, no persisted artifact | **out of scope** | Nothing is created/updated/deleted to log |

All `in scope` rows are drawn from the events list in `spec.md` §5.1. The two `deferred` rows (Data Quality check, Alert) are explicitly flagged here rather than silently dropped — both surfaces are still evolving, per `docs/domain-map.md`'s own confidence tags.

## 3. High-Level Design (HLD)

Audit logging is implemented as an **asynchronous Celery task**, enqueued from inside each existing API view function immediately after the underlying action succeeds. Dalgo already runs Celery for other background work (e.g. dbt runs, notification delivery — `run_dbt_via_celery`), so this reuses existing infrastructure rather than introducing a new one.

**The audit write can never break or measurably slow the main request.** The call site only *enqueues* a task (`create_audit_log(...)`, a thin wrapper around `.delay()`) — it does not wait for the row to be written. Enqueueing is fast, and if it fails for any reason (e.g. the Celery broker is briefly unreachable), that failure is caught and logged via `CustomLogger`, never raised — see §4.2. So the user's original action always returns success as normal, with no added latency from the audit write itself.

**If the main action itself fails, no audit log entry is created.** The enqueue call sits after the real action succeeds in the code, so it never runs on a failure path. Every event is logged on success only — including login, with no exception.

**Accepted trade-off: eventual consistency, not strict consistency.** Moving the write off the request path means an audit entry may not be queryable the instant the action completes — there's a small window while the task sits in the queue and gets processed. It also means a (rare) audit entry can be lost if the broker drops the task or the worker crashes mid-task before it's durably written, with no automatic backfill. This was a deliberate call: the team decided the latency and decoupling benefit of async is worth a small amount of consistency risk, rather than guaranteeing zero gaps at the cost of adding latency to every audited request.

```
User action --> Django Ninja API view --> existing service call (unchanged)
                                       --> create_audit_log() [NEW] --> enqueues Celery task
                                       --> response returned                |
                                                                             v
                                                          Celery worker --> writes AuditLog row
```

Key design decisions:

- **Asynchronous, via Celery task.** Audit writes happen out-of-band from the request/response cycle. This keeps the audited action's response time unaffected by the audit write, at the cost of eventual (not immediate) consistency and a small, accepted risk of losing an entry if the broker/worker has an outage — see the trade-off note above.
- **Single table, discriminated by `resource_type`.** One `AuditLog` model rather than per-resource tables, avoiding join complexity across very different resource shapes (a dashboard, a git repo switch, a login attempt).
- **No new external service integrations.** Airbyte, Prefect, and the warehouse are unaffected — audit logging only observes Dalgo's own API layer, not these external systems directly.
- **No new API surface, write or read.** Audit entries are only ever created by `create_audit_log()` calls inside existing endpoints. No query endpoint either — deferred to v2 (spec.md §3).

**Why not use an off-the-shelf audit library (e.g. `django-auditlog`, `django-simple-history`, `django-easy-audit`)?** These packages work by hooking into Django's `post_save` / `post_delete` model signals — they automatically log when a model instance changes. That fits a subset of our events well (Dashboard, Chart, Metric, KPI, Pipeline CRUD), but a large share of the events list in `spec.md` §5.1 aren't model saves at all: login (no row is saved at all on a login, success or attempted), dbt git pull, manual sync trigger, dashboard share. A signal-based library has no hook for any of these because nothing gets saved or deleted — they're just actions succeeding. Adopting one of these libraries would only cover roughly a third of our events, and we'd still need the custom `create_audit_log()` service layer for the rest — at that point we'd be maintaining two audit systems writing in two different shapes instead of one. The single custom service layer covers all ~70 events uniformly with one call pattern, which is simpler to maintain despite requiring more upfront wiring.

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
    changes = models.JSONField(default=dict, blank=True)

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

New file: `DDP_backend/ddpui/core/audit_log_service.py` (thin, synchronous-looking wrapper called from API views)
New file: `DDP_backend/ddpui/celery_tasks/audit_log_tasks.py` (the actual Celery task that writes the row)

```python
# core/audit_log_service.py

def create_audit_log(
    *,
    org,
    orguser,
    resource_type: str,
    resource_id: str,
    action: str,
    resource_name: str = "",
    changes: dict | None = None,
) -> None:
    """
    Enqueues an audit log write as a Celery task. Never raises — if
    enqueueing itself fails (e.g. broker unreachable), that failure is
    caught and logged via CustomLogger instead of propagating, so a
    broker outage can never break the primary request.

    Only JSON-serializable primitives are passed through to the task
    (org.id / orguser.id, not the model instances themselves) since
    Celery task arguments must be serializable.
    """


def compute_changes(before: dict, after: dict, exclude_fields: list[str] | None = None) -> dict:
    """
    Diffs two flat dicts, returning only changed keys as
    {"field": {"old": x, "new": y}}. exclude_fields is mandatory for any
    resource that might carry secrets (passwords, tokens, credentials,
    share tokens) — callers must pass it explicitly for those resources.
    """
```

```python
# celery_tasks/audit_log_tasks.py

@app.task(bind=True, max_retries=3, default_retry_delay=10)
def write_audit_log_task(
    self, *, org_id, orguser_id, resource_type, resource_id, action, resource_name, changes
):
    """
    Writes the actual AuditLog row. Retries a small, bounded number of
    times on transient DB errors (e.g. connection blip). If retries are
    exhausted, the failure is logged and the task is dropped — per the
    accepted eventual-consistency trade-off (HLD §3), this is not backed
    by a dead-letter queue or manual replay in v1.
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
- **New dependency: Celery.** Audit log writes go through Dalgo's existing Celery worker pool (`write_audit_log_task`), the same infrastructure already used for dbt runs and notification delivery. No new broker or worker fleet is introduced — this reuses what's there.
- No outbound calls to Airbyte, Prefect, or the warehouse are added; this feature only touches Dalgo's own request/response cycle plus the existing Celery layer.

## 5. Security Review

- **Authentication & Authorization:** no read API in v1 (spec.md §3), so no `@has_permission` gate to review yet. Writes only happen from inside existing, already-authenticated endpoints.
- **Sensitive data:** this is the highest-risk part of the feature regardless of v1's scope. `compute_changes()` requires an explicit `exclude_fields` list for any resource that can carry secrets — passwords, API keys, git access tokens, warehouse credentials, public share tokens, JWTs. This must be enforced via code review on every call site, and covered by a unit test per sensitive resource type (see §6).
- **Injection risks:** no raw SQL or dynamic query construction on the write path — `write_audit_log_task` writes through the Django ORM, using the indexed fields in §4.1.
- **External service calls:** none added by this feature.
- **Rate limiting / abuse:** the write path piggybacks on existing authenticated endpoints, so no new abuse surface. With no read endpoint in v1, there's no public/anonymous read surface to consider either.

## 6. Testing Strategy

- **Unit tests — service layer** (`core/audit_log_service.py`):
  - `create_audit_log()` enqueues `write_audit_log_task` with the expected arguments for create/update/delete/login/logout actions.
  - `create_audit_log()` never raises, even when enqueueing itself fails (mock a broker/connection error on `.delay()`, assert no exception propagates, assert it's logged).
  - `compute_changes()` correctly diffs two dicts and excludes fields in the exclude list.
- **Unit tests — Celery task** (`celery_tasks/audit_log_tasks.py`):
  - `write_audit_log_task` writes the expected `AuditLog` row given valid arguments.
  - Retries the expected number of times on a transient DB error, then gives up and logs the failure (does not raise out of the task).
- **Unit tests — secrets exclusion** (one per sensitive resource type): warehouse credentials, git access token, org logo upload, public share token — assert none of these ever appear in a `changes` JSON blob after going through the real call site.
- **Integration / spot-check tests** — for a representative sample across each in-scope area (one from auth, one from dashboards, one from dbt, one from pipelines), assert that calling the real action endpoint (e.g. `DELETE /api/dashboards/{id}`) produces exactly one new `AuditLog` row with the expected `resource_type`/`action`. Run with `CELERY_TASK_ALWAYS_EAGER=True` so the task executes synchronously and deterministically within the test, rather than asserting against a real queue.
- **Edge cases:** delete of an already-deleted resource (should not log twice), enqueue failure (broker unreachable — assert primary action still returns success to the caller, per the accepted trade-off in HLD §3), retry exhaustion on the task (assert it's logged and dropped, not retried forever).

## 7. Milestones

#### Milestone 1: Core infrastructure

- **Deliverable:** `AuditLog` model + migration, `audit_log_service.py` (`create_audit_log`, `compute_changes`), `audit_log_tasks.py` (`write_audit_log_task`).
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Create `models/audit_log.py` and migration
  - [ ] Implement `core/audit_log_service.py` (enqueues) and `celery_tasks/audit_log_tasks.py` (writes, with bounded retries)
  - [ ] Unit tests for service layer + Celery task + secrets exclusion
- **Acceptance criteria:** `create_audit_log()` can be called standalone and enqueues a task that produces a correct row (with `CELERY_TASK_ALWAYS_EAGER=True` in tests); no call site wired up yet.

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
  - [ ] Wire `dashboard_native_api.py`: CRUD, publish, share (unshare logs as a regular update), set-as-default, filters
  - [ ] Wire `charts_api.py`: CRUD
  - [ ] Wire `metric_api.py` + `kpi_api.py`: CRUD
  - [ ] Wire `report_api.py`: CRUD, share (unshare logs as a regular update), comments
- **Acceptance criteria:** same pattern as above; share-token values verified excluded from `changes`.

#### Milestone 5: Retention

- **Deliverable:** retention cleanup ships once the team confirms the retention policy (§8).
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Implement `purge_old_audit_logs` management command (retention period as a parameter, default TBD per open question). Building it as a manually-invoked command keeps both options open — it can be left as a manual tool or wired to a scheduled job once the team decides whether removal should be automatic.
- **Acceptance criteria:** old logs are purged per whatever retention policy the team confirms; data in the meantime is readable via direct database query by Dalgo's team.

## 8. Open Questions & Risks

- **Retention policy** — whether removal should be automatic or manual, and if automatic, what period. Blocks finalizing whether `purge_old_audit_logs` stays a manual tool or gets wired to a scheduled job, and its default period. Carried over from spec.md §7.
- **Migration risk** — none. This is a net-new table; no existing data is migrated.
- **Async consistency risk (accepted)** — audit writes go through Celery (HLD §3), so entries are eventually consistent, not immediately queryable, and a small number can be lost if the broker/worker has an outage during retry exhaustion. The team explicitly chose this trade-off over the latency cost of a synchronous write. No dead-letter queue or manual replay path exists in v1 — worth revisiting if lost entries turn out to matter more in practice than expected.
- **Async ordering risk (accepted)** — if two actions happen on the same resource moments apart (e.g. create then immediately delete), the two resulting audit tasks are enqueued in the correct order, but Celery does not strictly guarantee they're *processed* in that same order — especially if one hits a retry. In rare cases, the `timestamp` on written rows could be slightly out of step with the true order of events. Not expected to be common or load-bearing for v1's use cases (incident investigation, "who did X"), but worth knowing if exact ordering ever becomes a hard requirement.
- **Org deletion cascades the audit trail (accepted for now)** — `org` is `on_delete=models.CASCADE` (§4.1). If an org is deleted, every audit log row for that org is deleted too, including any entry that would have recorded the deletion itself — there's no way to later show "this org was deleted, by whom, and when." In practice this is low-risk today since org deletion is a manual, engineer-run process (`manage.py deleteorg`, with a dry-run option), not a customer-facing or automated action. Kept as `CASCADE` for v1; revisit (e.g. `SET_NULL` + a denormalized `org_name`, mirroring the `orguser`/`orguser_email` pattern) if a need to retain audit history past org deletion comes up later.
