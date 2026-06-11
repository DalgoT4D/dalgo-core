# Alerts v1 — Implementation Plan

**Status:** Draft v1
**Date:** 2026-06-11
**Spec:** [Top-level](../spec.md) | [v1 scoped](./spec.md) | [design](./design.md)
**Research:** [research.md](./research.md)
**Domain map:** [docs/domain-map.md](../../../docs/domain-map.md)

---

## 1. Overview

A schedule-driven alerting system for Dalgo. Three alert types (Metric-threshold, KPI-RAG, Standalone) authored through a shared 3-step modal wizard. Each alert runs on its own cron schedule, evaluates a numeric condition against the org's warehouse, and on fire delivers a rendered message via Email (always) and/or Slack (per-alert webhook URL). The `/alerts` page lists every alert with All-alerts and Firing tabs and a per-alert fire-history modal. Role-gated CRUD.

**Services affected:**
- **DDP_backend** — New Alert/AlertRecipient/AlertFire/AlertDelivery models, Alert CRUD + dry-run + slack-test API, Celery dispatcher + evaluator tasks, Mustache rendering, SES + Slack-webhook delivery, permission slugs.
- **webapp_v2** — New `/alerts` page (listing + tabs), 3-step authoring wizard, Alert log modal, recipient picker, entry-point CTAs on Metrics page and KPI detail drawer.

**Not affected:** prefect-proxy (alerts do not orchestrate pipelines), prefect-airbyte, dalgo-ai-gen.

---

## 2. Blast Radius

Confirmed in scope-confirmation conversation 2026-06-11. Domain map traversal in [research.md § 5](./research.md#5-blast-radius--domain-map-traversal).

| Surface | Hop | Edge type | Why affected | Status | Notes |
|---|---|---|---|---|---|
| **Metric** | 1 (Alert→Metric) | `reference` | Metric-threshold alerts FK to `Metric`; deletion blocked while alert references it | **In scope (read-only)** | Reuses existing `MetricService` for value computation |
| **KPI** | 1 (Alert→KPI) | `reference` | KPI-RAG alerts FK to `KPI`; deletion blocked while alert references it | **In scope (read-only)** | Reuses existing `KPIService` for RAG resolution |
| **Warehouse** | 1 (Alert→Warehouse) | `query-from` | Evaluator runs SQL via `WarehouseFactory` for Standalone alerts | **In scope** | Same auth path as Metric/KPI |
| **Metrics page** | UI | entry point + consumer surface | (a) "Create Alert" CTA added per Metric row; (b) Alerts appear in the Metric's consumers list so users see which alerts depend on the Metric. (Deletion is NOT blocked — cascades — but the consumer list still warns the user before they delete.) | **In scope** | New row action + extension of existing `/api/metrics/{id}/consumers/` |
| **KPI detail drawer** | UI | entry point + consumer surface | (a) "Create Alert" CTA added; (b) Alerts appear in the KPI's consumers list (symmetric with Metric) | **In scope** | Drawer doesn't have a Create Alert CTA today (research §3); consumers list extends to alerts |
| **/alerts page** | UI (new) | new surface | All alerts + Firing tabs, Alert log modal | **In scope** | New route |
| **Pipeline** | 1 (Alert←Pipeline, per domain map) | `trigger` | Domain map lists Pipeline failure as an Alert trigger source | **Deferred** | v1 is schedule-driven only. Future spec |
| **Data Quality check** | 1 (Alert←DQ, per domain map) | `trigger` | Domain map lists DQ-check failure as Alert trigger | **Deferred** | Future spec |
| **Notification** | 1 (Notification←Alert) | `trigger` | Domain map: alert firing → Notification rows | **Out of scope** | User confirmed: Email + Slack only; no in-app rows |
| **OrgUser** | 1 (recipient) | `reference` | `AlertRecipient.orguser` for Dalgo-user recipients | **In scope** | External emails stored as strings (no OrgUser link) |
| **Dashboard / Report / Share link** | n/a | none | Alerts have no edge into composition surfaces | **Not affected** | Confirmed |

### v2 debt documented from this table

1. Pipeline-failure alerts (the original spec's design) — future iteration.
2. Data Quality check failure alerts — future iteration.
3. In-app Notification integration if cross-feature feed unification becomes a goal.

---

## 3. High-Level Design (HLD)

### 3.1 System architecture

```
┌──────────────────────────── webapp_v2 ───────────────────────────┐
│                                                                  │
│  /metrics page       KPI detail drawer       /alerts page        │
│      │                       │                       │           │
│      └────── "Create Alert" entry → AlertWizardModal ─┘          │
│                              │                                   │
│            Steps: 1. Define → 2. Notify → 3. Test                │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │  apiGet/apiPost/apiPut/apiDelete
┌──────────────────────────────┼───── DDP_backend ─────────────────┐
│                              │                                   │
│  Alert API                                                       │
│   • POST /api/alerts/        • POST /api/alerts/test/            │
│   • GET  /api/alerts/        • POST /api/alerts/test-slack-      │
│   • GET  /api/alerts/{id}/   ··    webhook/                      │
│   • PUT  /api/alerts/{id}/   • GET  /api/alerts/{id}/fires/      │
│   • DELETE /api/alerts/{id}/ • PATCH /api/alerts/{id}/toggle/    │
│   • GET  /api/alerts/firing/                                     │
│                              │                                   │
│                  AlertService (CRUD, validation, dry-run)        │
│                              │                                   │
│                       Postgres (4 tables)                        │
│                              ▲                                   │
│                              │ writes                            │
└──────────────────────────────┼───── Celery ─────────────────────┘
                               │
   beat (every 60s) ─► dispatch_due_alerts (worker)
                       └─► evaluate_alert.delay(alert.id) ×N
                               │
                       evaluate_alert (worker):
                          1. atomic claim via UPDATE
                          2. build SQL (reuse Metric/KPI/AggQB)
                          3. execute on org's warehouse
                          4. check_condition
                          5. if fired: render → SES + Slack POST
                          6. write AlertFire + AlertDelivery rows
                               │
                               ▼
                       SES email · Slack webhook
```

### 3.2 Data flow — schedule-driven evaluation

1. **Author creates Alert** in wizard. Frontend converts user's local-clock-time + frequency + day to a UTC cron expression. Backend persists `schedule_cron`.
2. **Celery Beat tick** (every 60s) enqueues `dispatch_due_alerts`.
3. **Dispatcher** iterates `Alert.objects.filter(is_active=True)`, calls `is_due(alert, now)` for each. If due, `evaluate_alert.delay(alert.id)`.
4. **Evaluator** runs per-alert:
   - **Phase 1 (atomic claim):** conditional UPDATE on `last_evaluated_at`. If `rows == 0`, another worker already claimed this scheduled tick — exit.
   - **Phase 2 (work):** build SQL based on `alert_type`, execute against org's warehouse, evaluate `condition`, render templates with tokens, deliver via SES + Slack POST, write `AlertFire` + `AlertDelivery` rows.

### 3.3 Data flow — Test Alert (Step 3 dry-run)

1. Frontend POSTs the current wizard form to `/api/alerts/test/`.
2. Backend validates, builds SQL, executes on warehouse, evaluates condition, renders templates with sample tokens — **but does not deliver or persist**.
3. Returns `{ would_fire, current_value, sql, rendered_email, rendered_slack }` for the wizard to render.

### 3.4 Data flow — Slack webhook test (Step 2 button)

1. Frontend POSTs the user-pasted `webhook_url` to `/api/alerts/test-slack-webhook/`.
2. Backend POSTs a static dummy payload (`"This is a test message from Dalgo platform"`) to the URL.
3. Returns HTTP status + response body. No alert state touched.

### 3.5 New API endpoints

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `POST` | `/api/alerts/` | `can_create_alerts` | Create alert |
| `GET` | `/api/alerts/` | `can_view_alerts` | List (paginated, filters: enabled, frequency, last_fire range; sort: any column) |
| `GET` | `/api/alerts/{id}/` | `can_view_alerts` | Single alert (full config) |
| `PUT` | `/api/alerts/{id}/` | `can_edit_alerts` | Update alert |
| `DELETE` | `/api/alerts/{id}/` | `can_delete_alerts` | Delete alert |
| `PATCH` | `/api/alerts/{id}/toggle/` | `can_edit_alerts` | Flip `is_active` |
| `GET` | `/api/alerts/firing/` | `can_view_alerts` | Alerts whose most-recent AlertFire fired (Firing tab) |
| `GET` | `/api/alerts/{id}/logs/` | `can_view_alerts` | Paginated evaluation log for Alert log modal (one entry per evaluation, with embedded deliveries) |
| `POST` | `/api/alerts/test/` | `can_create_alerts` | Dry-run (Step 3 of wizard) — no persistence, no delivery |
| `POST` | `/api/alerts/test-slack-webhook/` | `can_create_alerts` | Send static "test message" payload to a webhook URL |

**Modified endpoints (cross-feature):**

| Method | Path | Owning feature | Change in this plan |
|---|---|---|---|
| `GET` | `/api/metrics/{id}/consumers/` | metrics_kpis | Extend response to include alerts that reference this Metric (`alert_type=metric_threshold` or `standalone` that happens to use the metric — only the FK case counts) so the Metrics page can render them as dependencies |
| `GET` | `/api/kpis/{id}/consumers/` | metrics_kpis | Same: include alerts that reference this KPI (`alert_type=kpi_rag`) |

### 3.6 Key design decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Trigger model** | Schedule-only (cron), no pipeline/DQ triggers | Spec scope; user confirmed |
| **Cron storage** | `schedule_cron: TextField` in UTC; no TZ stored | User's call. Trade DST safety for simpler model. IST userbase doesn't observe DST |
| **Scheduler** | Single Celery Beat tick every 60s → dispatcher | Reuses existing `django-celery-beat` service; one source of periodic work; no PeriodicTask-per-alert overhead |
| **Dedup / at-most-once** | Conditional UPDATE on `last_evaluated_at` | Atomic via Postgres row-level locking; no explicit `select_for_update`; one SQL statement |
| **`last_evaluated_at` semantics** | Updated at the start of the evaluator (Phase 1 claim), not the end | Crash between claim and notification loses one fire; next cron tick runs normally. Accepted trade-off for `daily/weekly/monthly` cadences |
| **Three alert types in one table** | `Alert.alert_type` enum + nullable FK columns (`metric_id`, `kpi_id`) + nullable standalone columns | One model, one CRUD, one wizard. Validation enforces the right fields per type |
| **Recipients as JSON on `alert`** | `Alert.recipients` JSONField — list of `{type, orguser_id?, email?}` | Recipients are always loaded with the alert (for chips render, for delivery loop); never queried independently. No need for a normalized table |
| **Single `alert_log` table** | One row per evaluation (fired or not); deliveries embedded as JSON column on the row | Spec never queries deliveries independent of their fire. Alert log modal always shows them grouped under their fire row. One write per evaluation, one read for the modal |
| **No `summary_status`** (neither stored nor computed) | API returns `fired` + `deliveries` as-is; no roll-up surfaced anywhere in v1 | Defers the spec Story 6 "Delivery status column (green/amber/red)" badge. Frontend can derive locally from `deliveries` if/when we want it. Avoids carrying state we don't yet need |
| **Slack** | Per-alert `slack_webhook_url` (no OAuth, no org-level workspace) | Simpler than parent spec's OrgSlackConfig. Spec explicitly defers OAuth to a future spec |
| **No in-app Notification rows** | Email + Slack only on fire; Firing tab + Alert log are the in-app surface | User confirmed |
| **Delete cascades from Metric/KPI** | `on_delete=CASCADE` on Alert.metric and Alert.kpi — deleting a Metric/KPI silently deletes its alerts | User preference; overrides spec Story 5's "delete blocked" — flagged as Open Question §8 to update the spec |
| **Test endpoint (dry-run)** | Same SQL build + execute path as evaluator, but no persistence and no delivery | Reuses code; deterministic for wizard Step 3 |
| **Mustache rendering** | `pystache` library | Spec calls out Mustache; safe (no eval) |
| **Token sets** | Hardcoded per alert type in `alert_service.py`; frontend mirrors the list | Closed set, no user-defined tokens in v1 |
| **History retention** | Unlimited (paginated in UI) | Spec says unlimited; storage cost negligible at NGO scale |
| **Permissions** | Four new slugs: `can_view_alerts`, `can_create_alerts`, `can_edit_alerts`, `can_delete_alerts` | Mirrors metrics/KPIs/charts convention |

---

## 4. Low-Level Design (LLD)

### 4.1 Data Model

**Two new tables only.** Recipients live as JSON on the `alert` row; per-fire delivery records live as JSON on the `alert_log` row.

#### New file: `ddpui/models/alert.py`

```python
from django.db import models


class AlertType(models.TextChoices):
    METRIC_THRESHOLD = "metric_threshold", "Metric threshold"
    KPI_RAG = "kpi_rag", "KPI RAG"
    STANDALONE = "standalone", "Standalone"


# Note: condition operators (lt/gt/eq) and RAG states (red/amber/green) are
# enforced at the API boundary via the discriminated Pydantic Union below —
# not as Django field choices, because condition lives in a JSON column.


class Alert(models.Model):
    id = models.BigAutoField(primary_key=True)
    org = models.ForeignKey("Org", on_delete=models.CASCADE, related_name="alerts")

    # Identity
    name = models.CharField(max_length=255)
    alert_type = models.CharField(max_length=20, choices=AlertType.choices)

    # Source (exactly one populated based on alert_type).
    # on_delete=CASCADE — deleting the underlying Metric/KPI silently deletes its alerts
    # (and transitively their AlertLog rows). Spec Story 5 says delete should be blocked;
    # this plan overrides that — see Open Questions §8.
    metric = models.ForeignKey(
        "Metric", on_delete=models.CASCADE, null=True, blank=True, related_name="alerts"
    )
    kpi = models.ForeignKey(
        "KPI", on_delete=models.CASCADE, null=True, blank=True, related_name="alerts"
    )

    # Standalone source — populated only for STANDALONE alerts (null for metric/kpi types).
    # Shape (validated at API boundary by StandaloneConfig Pydantic model):
    #   {
    #     "schema_name": str,
    #     "table_name": str,
    #     "column": str | null,        # null for COUNT(*)
    #     "aggregation": str | null,   # sum/avg/count/min/max/count_distinct (Simple mode)
    #     "column_expression": str | null,   # Calculated mode (mutually exclusive with column+aggregation)
    #     "filters": [{"column": str, "operator": str, "value": Any}, ...]
    #   }
    standalone_config = models.JSONField(null=True, blank=True)

    # Condition — shape depends on alert_type.
    # Validated at API boundary by a discriminated Union of Pydantic models:
    #   For metric_threshold / standalone:
    #     {"operator": "lt" | "gt" | "eq", "value": float}
    #   For kpi_rag:
    #     {"rag_states": ["red" | "amber" | "green", ...]}  # 1–2 entries
    condition = models.JSONField()

    # Schedule (UTC cron; frontend converts user's local time -> UTC at save)
    schedule_cron = models.CharField(max_length=100)  # e.g. "30 3 * * *"

    # Delivery configuration
    delivery_channels = models.JSONField(default=list)  # ["email"] or ["email", "slack"]
    slack_webhook_url = models.TextField(null=True, blank=True)  # store plain, mask on GET
    # Single Mustache template — same body rendered for both email and Slack
    # (spec Story 8: "Slack rendering substitutes the same tokens as email")
    message_template = models.TextField()

    # Recipients — JSON list. Each entry:
    #   {"type": "orguser", "orguser_id": 42}
    #   {"type": "external", "email": "person@example.com"}
    # Validated at the API boundary; replaced wholesale on edit.
    recipients = models.JSONField(default=list)

    # State
    is_active = models.BooleanField(default=True)
    last_evaluated_at = models.DateTimeField(null=True, blank=True)  # UTC

    # Audit
    created_by = models.ForeignKey(
        "OrgUser", on_delete=models.CASCADE, related_name="alerts_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "alert"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["org", "name"], name="unique_alert_name_per_org"),
        ]
        indexes = [
            models.Index(fields=["org", "is_active"]),
            models.Index(fields=["is_active", "last_evaluated_at"]),  # dispatcher query
        ]


class AlertLog(models.Model):
    """One row per evaluation (whether or not it fired). Immutable history.

    Deliveries are stored as a JSON column on the row — there is no separate
    alert_delivery table. The Alert log modal always shows deliveries grouped
    under their evaluation, so we trade independent indexability for a simpler
    one-row-per-evaluation write/read.

    Summary delivery status (success / partial / failed / not_fired) is NOT
    stored — it is computed at serialization time from `fired` + `deliveries`.
    """
    id = models.BigAutoField(primary_key=True)
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name="logs")

    scheduled_for = models.DateTimeField()  # UTC; the cron tick this evaluation is for
    evaluated_at = models.DateTimeField()   # UTC; when we actually ran the query
    value = models.FloatField(null=True, blank=True)   # null if query returned no rows
    fired = models.BooleanField()

    # Snapshot — preserves the audit-relevant alert config as it was at evaluation time.
    # Shape:
    #   {
    #     "name": str,
    #     "alert_type": "metric_threshold" | "kpi_rag" | "standalone",
    #     "metric_id": int | null,       # populated for metric_threshold
    #     "kpi_id": int | null,          # populated for kpi_rag
    #     "condition": {"operator": "lt"|"gt"|"eq", "value": float}
    #                  | {"rag_states": ["red"|"amber"|"green", ...]},
    #     "recipients": [
    #       {"type": "orguser", "orguser_id": int},
    #       {"type": "external", "email": str}
    #     ],
    #     "message_template": str
    #   }
    # For standalone alerts: source (schema/table/column/aggregation/expression) is
    # NOT duplicated here — sql_executed already captures what was queried.
    # Slack webhook URL is intentionally excluded (sensitive; don't re-store).
    # delivery_channels is intentionally excluded (derivable from `deliveries` array).
    alert_snapshot = models.JSONField()
    sql_executed = models.TextField()
    # The rendered message body. Always populated — we render every evaluation so the log
    # shows "what would have been sent if this had fired," even on non-fires. Same body
    # for email + Slack since template is shared.
    message = models.TextField()

    # Deliveries as JSON. Each entry:
    #   {
    #     "channel": "email" | "slack",
    #     "target":  "recipient@example.com" | "slack:webhook",
    #     "status":  "sent" | "failed",
    #     "error_reason": "<smtp error or http body>" | null,
    #     "http_status": 200 | null,
    #     "sent_at": "2026-06-11T03:30:07Z"
    #   }
    # Empty list when fired=False.
    deliveries = models.JSONField(default=list)

    class Meta:
        db_table = "alert_log"
        ordering = ["-evaluated_at"]
        indexes = [
            models.Index(fields=["alert", "-evaluated_at"]),       # log modal pagination
            models.Index(fields=["alert", "-evaluated_at", "fired"]),  # Firing tab query
        ]
```

**Why two tables, not four:**
- `alert_recipient` collapsed into `Alert.recipients` JSON — recipients are always loaded with the alert (for chip render, for delivery loop) and never queried independently in v1. OrgUser deletions don't auto-cascade (the JSON ID may become stale), but the evaluator handles this gracefully (skip-if-not-found).
- `alert_fire` + `alert_delivery` collapsed into `AlertLog` with `deliveries` JSON column. The Alert log modal always reads them together, fully expanded. Trades cross-alert per-delivery analytics (not in spec) for a single-row write per evaluation and a single-table read for the modal.

#### Migration

`ddpui/migrations/0XXX_alert_models.py` (auto-generated `makemigrations`) plus a manual `RunPython` migration `0XXX_alert_permissions.py` to:
- Create permission slugs `can_view_alerts`, `can_create_alerts`, `can_edit_alerts`, `can_delete_alerts`.
- Assign them to roles. (Suggested mapping mirrors metrics/KPIs — confirm with Pratiksha during execution.)

### 4.2 API schemas

#### New file: `ddpui/schemas/alert_schema.py`

```python
from datetime import datetime
from typing import List, Optional, Literal
from ninja import Schema


# --- Recipient ---

class RecipientIn(Schema):
    type: Literal["orguser", "external"]
    orguser_id: Optional[int] = None
    email: Optional[str] = None

class RecipientOut(Schema):
    type: str
    orguser_id: Optional[int] = None
    orguser_name: Optional[str] = None
    email: Optional[str] = None


# --- Standalone source (one JSON column on Alert) ---

class FilterClause(Schema):
    column: str
    operator: str
    value: Any  # warehouse-typed; backend casts during query build

class StandaloneConfig(Schema):
    schema_name: str
    table_name: str
    column: Optional[str] = None       # null for COUNT(*)
    aggregation: Optional[str] = None  # sum/avg/count/min/max/count_distinct (Simple mode)
    column_expression: Optional[str] = None  # Calculated mode (mutually exclusive)
    filters: List[FilterClause] = []


# --- Condition (one JSON column on Alert, shape depends on alert_type) ---
# Pydantic discriminated Union — Ninja validates the correct branch based on what fields are present.

class ThresholdCondition(Schema):
    operator: Literal["lt", "gt", "eq"]
    value: float

class RagCondition(Schema):
    rag_states: List[Literal["red", "amber", "green"]]  # 1–2 entries; validated in service

Condition = Union[ThresholdCondition, RagCondition]


# --- Create / Update ---

class AlertCreate(Schema):
    name: str
    alert_type: Literal["metric_threshold", "kpi_rag", "standalone"]
    metric_id: Optional[int] = None
    kpi_id: Optional[int] = None
    standalone_config: Optional[StandaloneConfig] = None
    condition: Condition  # Union — Ninja picks the right shape

    schedule_cron: str  # validated by croniter

    delivery_channels: List[Literal["email", "slack"]]
    slack_webhook_url: Optional[str] = None
    message_template: str  # single template — same body for both email and Slack

    recipients: List[RecipientIn]


class AlertUpdate(Schema):
    name: Optional[str] = None
    standalone_config: Optional[StandaloneConfig] = None
    condition: Optional[Condition] = None
    schedule_cron: Optional[str] = None
    delivery_channels: Optional[List[str]] = None
    slack_webhook_url: Optional[str] = None
    message_template: Optional[str] = None
    recipients: Optional[List[RecipientIn]] = None
    is_active: Optional[bool] = None


# --- Responses ---

class AlertResponse(Schema):
    id: int
    name: str
    alert_type: str
    metric_id: Optional[int]
    metric_name: Optional[str]
    kpi_id: Optional[int]
    kpi_name: Optional[str]
    standalone_config: Optional[StandaloneConfig]
    condition: Condition  # Union — same shape as AlertCreate
    schedule_cron: str
    delivery_channels: List[str]
    slack_webhook_url_masked: Optional[str]  # e.g. "https://hooks.slack.com/services/****"
    message_template: str
    is_active: bool
    last_evaluated_at: Optional[datetime]
    recipients: List[RecipientOut]
    created_at: datetime
    updated_at: datetime


class AlertListItem(Schema):
    """Used for /api/alerts/ listing (lightweight)."""
    id: int
    name: str
    alert_type: str
    source_name: Optional[str]      # Metric/KPI name or dataset name
    source_kind: str                # "metric" | "kpi" | "dataset"
    source_id: Optional[int]        # nav target (Metric/KPI id; null for dataset)
    condition_pretty: str           # "value < 50" / "RAG = red" / etc.
    schedule_frequency: str         # derived: "daily" | "weekly" | "monthly"
    is_active: bool
    last_fire_at: Optional[datetime]
    fire_streak: int                # consecutive recent fires
    most_recent_fired: bool         # for Firing tab


class AlertListResponse(Schema):
    items: List[AlertListItem]
    total: int


# --- Test (dry-run) ---

class AlertTestRequest(Schema):
    """Same shape as AlertCreate, used for the wizard Step 3 dry-run."""
    alert_type: str
    metric_id: Optional[int] = None
    kpi_id: Optional[int] = None
    standalone_config: Optional[StandaloneConfig] = None
    condition: Condition
    delivery_channels: List[str]
    message_template: str


class AlertTestResponse(Schema):
    would_fire: bool
    current_value: Optional[float]
    sql_executed: str
    message: str  # single rendered body — wizard shows it under both "Email preview" and "Slack preview" headings
    error: Optional[str] = None


# --- Slack test message ---

class SlackTestRequest(Schema):
    webhook_url: str

class SlackTestResponse(Schema):
    success: bool
    http_status: int
    response_body: str


# --- Alert log (per-evaluation history) ---

class LogDeliveryOut(Schema):
    """One entry of the deliveries JSON column on AlertLog."""
    channel: str
    target: str                # email or "Slack webhook"
    status: str
    error_reason: Optional[str]
    http_status: Optional[int]
    sent_at: datetime

class AlertLogOut(Schema):
    id: int
    scheduled_for: datetime
    evaluated_at: datetime
    value: Optional[float]
    fired: bool
    condition_pretty: str        # human-readable, derived from alert_snapshot.condition
    sql_executed: str
    message: str  # always populated — rendered even on non-fires
    deliveries: List[LogDeliveryOut]

class LogListResponse(Schema):
    items: List[AlertLogOut]
    total: int
```

### 4.3 API layer — `ddpui/api/alert_api.py`

Thin Ninja `Router` instance, follows `metric_api.py` conventions. Each endpoint:
1. `@has_permission(["..."])`
2. Validates input via Ninja Schema.
3. Delegates to `AlertService` for business logic.
4. Returns typed response or raises `HttpError`.

```python
alert_router = Router()

@alert_router.post("/", response=AlertResponse)
@has_permission(["can_create_alerts"])
def create_alert(request, body: AlertCreate):
    orguser = request.orguser
    return AlertService.create_alert(orguser, body)

@alert_router.get("/", response=AlertListResponse)
@has_permission(["can_view_alerts"])
def list_alerts(request, page: int = 1, page_size: int = 50,
                enabled: Optional[bool] = None,
                frequency: Optional[str] = None,
                last_fire_within_hours: Optional[int] = None,
                sort_by: str = "last_fire_at", sort_order: str = "desc"):
    return AlertService.list_alerts(request.orguser.org, ...)

# ... similar for the rest
```

Registered in `ddpui/routes.py`: `api.add_router("/api/alerts/", alert_router)`.

### 4.4 Service layer — `ddpui/core/alerts/`

New package. Files:

- `alert_service.py` — CRUD, dry-run, slack-webhook test, listing/firing/fire-history queries.
- `alert_query.py` — Build SQL for the three alert types (delegates to `MetricService` and `KPIService` where possible, falls through to `AggQueryBuilder` for Standalone).
- `condition.py` — Pure functions: `evaluate_condition(alert_type, value, condition) -> bool`.
- `rendering.py` — Mustache rendering via `pystache`. Hardcoded token resolvers per alert type.
- `delivery.py` — Email (delegates to `awsses.py`) + Slack webhook POST. Returns per-recipient `AlertDelivery` records.
- `scheduling.py` — `is_due(alert, now)`, `derive_frequency_label(cron)` for display.

Key public methods on `AlertService`:

```python
@staticmethod
def create_alert(orguser, payload) -> Alert: ...

@staticmethod
def update_alert(alert_id, org, orguser, payload) -> Alert: ...

@staticmethod
def delete_alert(alert_id, org) -> None: ...

@staticmethod
def toggle_alert(alert_id, org, is_active: bool) -> Alert: ...

@staticmethod
def list_alerts(org, **filters) -> tuple[list[AlertListItem], int]: ...

@staticmethod
def list_firing(org, **filters) -> tuple[list[AlertListItem], int]: ...

@staticmethod
def get_log(alert_id, org, page, page_size) -> tuple[list[AlertLog], int]: ...

@staticmethod
def dry_run(orguser, payload) -> AlertTestResponse:
    """Build SQL, execute, evaluate, render — but do NOT persist or deliver."""

@staticmethod
def test_slack_webhook(webhook_url: str) -> SlackTestResponse:
    """POST a static test payload and return HTTP outcome."""
```

### 4.5 Celery tasks — `ddpui/celeryworkers/alert_tasks.py`

```python
from celery import shared_task
from django.db.models import Q
from django.utils import timezone
from croniter import croniter

from ddpui.models.alert import Alert
from ddpui.core.alerts import alert_service


@shared_task(name="alerts.dispatch_due_alerts")
def dispatch_due_alerts():
    """Run every 60s by Celery Beat. Enqueues evaluators for due alerts."""
    now = timezone.now()
    alerts = Alert.objects.filter(is_active=True).only(
        "id", "schedule_cron", "last_evaluated_at"
    )
    for alert in alerts:
        last_scheduled = croniter(alert.schedule_cron, now).get_prev(timezone.datetime)
        if alert.last_evaluated_at is None or alert.last_evaluated_at < last_scheduled:
            evaluate_alert.delay(alert.id)


@shared_task(name="alerts.evaluate_alert", bind=True, max_retries=0)
def evaluate_alert(self, alert_id: int):
    """Atomic claim → execute → deliver → record."""
    now = timezone.now()
    alert = Alert.objects.filter(id=alert_id, is_active=True).first()
    if not alert:
        return  # disabled or deleted between dispatch and execution

    scheduled_for = croniter(alert.schedule_cron, now).get_prev(timezone.datetime)

    # Atomic claim — Postgres serializes; only one worker matches the WHERE
    rows_updated = Alert.objects.filter(
        id=alert_id, is_active=True
    ).filter(
        Q(last_evaluated_at__isnull=True) | Q(last_evaluated_at__lt=scheduled_for)
    ).update(last_evaluated_at=now)
    if rows_updated == 0:
        return  # another worker already claimed this scheduled tick

    # Reload the alert with the rest of its fields
    alert = Alert.objects.select_related("metric", "kpi", "org").get(id=alert_id)
    alert_service.run_evaluation(alert, scheduled_for=scheduled_for, evaluated_at=now)
```

### 4.6 Celery Beat configuration

Append to Django settings (`ddpui/settings/`):

```python
CELERY_BEAT_SCHEDULE = {
    # ... existing entries ...
    "alerts-dispatcher": {
        "task": "alerts.dispatch_due_alerts",
        "schedule": 60.0,  # seconds
    },
}
```

### 4.7 Frontend — `webapp_v2`

#### New page

`app/alerts/page.tsx` — the `/alerts` listing. Composes `<AlertsTable />` with two `<TabsTrigger>` controls for All alerts / Firing.

#### New components

`components/alerts/`:

- `AlertsTable.tsx` — Shadcn `<Table>` with sortable column headers and per-column filter affordances. Rows include 3-dot menu (DropdownMenu) with Edit / Delete / Alert log items.
- `AlertWizardModal.tsx` — 3-step wizard. Holds form state in `react-hook-form`. Renders one of `AlertDefineStep`, `AlertNotifyStep`, `AlertTestStep` based on current step. Supports create + edit modes (edit prefills).
- `AlertDefineStep.tsx` — type-specific Step 1 body. Composes:
  - For Metric: read-only Metric chip + condition inputs + schedule.
  - For KPI: read-only KPI chip + read-only RAG bands + RAG-state multi-select + schedule.
  - For Standalone: `<DatasetSelector />` + `<MetricColumnAggregationFields />` (extracted from existing `metric-form-dialog`) + condition + schedule.
  - Shared `<ScheduleField />` subcomponent — frequency, day-of-week/month, time-of-day (browser tz). On submit converts to UTC cron.
- `AlertNotifyStep.tsx` — delivery channels checkboxes, `<RecipientCombobox />`, Slack webhook URL field + "Send test message" button, `<TemplateEditor />` (text area + live preview).
- `AlertTestStep.tsx` — would-fire banner, value, condition recap, rendered email + slack previews, collapsible SQL block.
- `RecipientCombobox.tsx` — single combobox that searches Dalgo users by name/email AND accepts free-form email input. Selected recipients render as chips with avatar (OrgUser) or envelope (external) icons.
- `TemplateEditor.tsx` — textarea + live-preview pane substituting tokens from the most recent test run (held in wizard state).
- `AlertLogModal.tsx` — modal showing per-fire rows. Each row expands to recipient list + per-recipient delivery status + collapsible SQL.
- `DeleteAlertDialog.tsx` — confirmation modal.
- `CreateAlertButton.tsx` — entry-point button used on /metrics, KPI drawer, /alerts page; pre-fills wizard with source if provided.

#### New hook

`hooks/api/useAlerts.ts` — SWR for list + firing + single + fires; standalone mutator functions for create/update/delete/toggle/test/test-slack-webhook.

#### New types

`types/alerts.ts` — TypeScript interfaces mirroring backend schemas. Cron utilities: `localScheduleToUtcCron(frequency, dayOfWeek?, dayOfMonth?, timeOfDay)` and the inverse for edit-mode prefill / display.

#### Modified components

- `app/metrics/page.tsx` (or wherever the metric row's action menu lives) — add "Create Alert" item.
- **Metric consumers list** (wherever it's currently rendered — likely a section of the Metric detail/edit view or a confirmation drawer when delete is attempted): add an "Alerts" group alongside the existing "Charts" and "KPIs" groups. Each row shows alert name + type + click-through into the alert wizard in edit mode. Source: extended `GET /api/metrics/{id}/consumers/` response. Same surface drives the "delete blocked" message.
- `components/kpis/kpi-detail-drawer.tsx` — (a) add "Create Alert" CTA; (b) extend the KPI consumers display (if present) or add one to mirror Metric. Source: extended `GET /api/kpis/{id}/consumers/`.
- `components/main-layout.tsx` — remove Alerts entry from `PRODUCTION_HIDDEN_ITEMS` once Milestone 4 ships.

### 4.8 Token sets per alert type

Hardcoded in `core/alerts/rendering.py`. Mirrored in frontend `types/alerts.ts` as a constant for the template editor's autocomplete and live preview substitution.

```python
TOKENS_BY_TYPE = {
    "metric_threshold": [
        "alert_name", "metric_name", "target_value", "current_value",
    ],
    "kpi_rag": [
        "alert_name", "kpi_name", "target_value", "current_value", "rag_status",
    ],
    "standalone": [
        "alert_name", "dataset_name", "target_value", "current_value",
    ],
}
```

`target_value` for `metric_threshold` / `standalone` = the user's `condition_value`. For `kpi_rag` = the KPI's `target_value` (read-only).

---

## 5. Security Review

### Authentication & Authorization
- All `/api/alerts/*` endpoints behind `@has_permission(["can_view_alerts" | ...])`.
- Migration adds the four permission slugs and assigns to roles consistent with metrics/KPIs (specific mapping confirmed during execution).

### Input validation
- Pydantic schemas at the API boundary reject malformed payloads.
- `schedule_cron` validated by attempting `croniter(cron, now)` in `AlertService.create_alert`. Invalid → 400 with field-level error.
- `aggregation` validated against the same allowed list as Metric: `[sum, avg, count, min, max, count_distinct]`.
- Standalone `column_expression` validated by a test query against the org's warehouse (mirrors Metric expression validation). Rejects DML/DDL via `sqlparse`.
- `rag_states` validated as subset of `{"red","amber","green"}` with 1 ≤ len ≤ 2.
- `recipients`: emails validated by Django's `EmailValidator`; orguser IDs validated against `OrgUser.objects.filter(org=org)`.
- Templates: passed through `pystache` which renders Mustache safely — no `eval`, no Python code execution from user input.

### Data access control
- Every query scoped to `request.orguser.org`. No cross-org access possible.
- Alert's warehouse SQL runs against the org's own `OrgWarehouse` — same isolation as Metric/KPI.
- External email recipients cannot be tied to OrgUsers; no privilege uplift via recipient list.

### Injection risks
- **Standalone alert SQL**: built via `AggQueryBuilder` (parameterized SQLAlchemy). Column names come from warehouse metadata (dropdown picks). Expression mode validated by sqlparse on save (same path as Metric).
- **Mustache rendering**: `pystache` does not evaluate code. Template text is rendered with token substitution only.
- **Slack webhook test**: We POST a fixed static body to the URL. We do not echo the URL into any user-facing HTML/JS.

### Sensitive data
- **Slack webhook URL** is a secret (anyone with it can post to the channel). Decisions:
  - Stored as `TextField` in plaintext (no at-rest encryption in v1).
  - **Masked on GET responses** (`slack_webhook_url_masked = "https://hooks.slack.com/services/****"`). Only the author who has the value already (or the wizard at submit) sees the full URL.
  - Edit modal does NOT fetch the full URL — if a user opens edit mode without re-pasting, the existing URL stays unchanged on PUT.
  - Documented as v2 candidate to encrypt with the same KMS pattern other secrets use.
- **External recipient emails** are PII. Stored unencrypted (consistent with `NotificationRecipient` pattern). Visible only inside Alert detail and Alert log.
- **AlertFire.sql_executed**: visible to every user with `can_view_alerts`. Confirmed acceptable per spec ("View SQL — visible to every user who can open the Alert log").

### External service calls
- SES: same configuration as existing email path (`SES_SENDER_EMAIL` env var).
- Slack: outbound POST via `requests` (already a transitive dep). Timeout = 10s. No secrets stored beyond the webhook URL itself.

### Rate limiting / abuse
- `POST /api/alerts/test/` and `POST /api/alerts/test-slack-webhook/` execute warehouse queries / external HTTP. Existing Django middleware rate-limit covers v1. If abuse appears, add per-orguser throttling later.

---

## 6. Testing Strategy

### Unit tests — DDP_backend

`tests/core/alerts/`:
- `test_scheduling.py`
  - `is_due` cases: NULL last_evaluated, past cron tick, future cron tick, exactly-at-tick.
  - `derive_frequency_label`: parses daily/weekly/monthly from cron; falls back to raw cron string.
- `test_condition.py`
  - `evaluate_condition`: each operator × value sign × edge case (None/empty result).
  - KPI-RAG state-membership check.
- `test_rendering.py`
  - Token substitution for all three alert types.
  - Missing token left as `{{token}}` (or empty — match prototype behavior).
- `test_delivery.py`
  - Email send: per-recipient SES call; per-recipient status capture.
  - Slack send: 2xx success, 4xx failure with HTTP status + body recorded.
  - Mixed success: AlertFire summary status = "partial".
- `test_alert_service.py`
  - Create: validation per alert_type (Metric requires metric_id, etc.).
  - Update: only the listed mutable fields change; the `recipients` JSON is replaced wholesale if `recipients` provided.
  - Toggle: `is_active` flips; `last_evaluated_at` preserved.
  - Delete: cascades to AlertLog (recipients and deliveries are inline JSON, deleted with their owner row).
  - Delete of underlying Metric/KPI cascades to the Alert (and transitively to AlertLog).
  - Deleting Metric/KPI cascades to alerts (and AlertLog rows); no error raised.
  - List + Firing filters and pagination.
  - Dry-run (`AlertService.dry_run`): no DB writes, no email sends, returns SQL + would_fire + rendered templates.
- `test_alert_tasks.py`
  - `dispatch_due_alerts` iterates and enqueues correctly (mock `evaluate_alert.delay`).
  - `evaluate_alert` claim succeeds on first call; subsequent identical call returns without doing work (atomic UPDATE returns 0).
  - `evaluate_alert` on a disabled alert exits cleanly.
- `tests/api_tests/test_alert_api.py`
  - CRUD with permissions (positive + 403 cases).
  - Schema validation rejections (missing required field per alert_type).
  - Dry-run endpoint: returns shape, no persistence.
  - Slack-webhook test endpoint: mocked HTTP success and failure.
  - Toggle endpoint flips state.
  - Firing tab filter (most recent fire is `fired=True`).
  - Fire history pagination.

### Integration / end-to-end

- **Schedule integration test** (Postgres + Celery eager mode):
  - Create an alert with `schedule_cron = "* * * * *"` (every minute) for the test.
  - Manually run `dispatch_due_alerts()` and assert `evaluate_alert` is enqueued.
  - Run the evaluator (eagerly) and assert: AlertLog row written with `deliveries` JSON populated and correct `summary_status`, `last_evaluated_at` updated.
  - Run `dispatch_due_alerts()` again immediately; assert no new enqueue (claim deduplication).
- **Mock SES + Slack** in integration tests to verify delivery records without external calls.

### Frontend tests

- `components/alerts/__tests__/`:
  - `AlertWizardModal` step navigation: Next is disabled until Step 1 valid; Test runs Step 3.
  - `RecipientCombobox`: typing a name surfaces matching OrgUsers; typing an email format with no match surfaces "Add as external recipient" option.
  - `ScheduleField` → cron conversion: round-trip a few sample times (IST 09:00 → `30 3 * * *`; weekly Mon 09:00 → `30 3 * * 1`).
  - `AlertsTable` sort/filter logic.
  - `AlertLogModal` row expansion + delivery list render.

### Edge cases
- Cron edited mid-day; `last_evaluated_at` preserved; next dispatcher tick uses new cron.
- All three RAG states selected on a KPI alert → blocked by schema validation (must be 1–2).
- Day-of-month = 31 → blocked by schema validation (1–28 allowed only).
- Standalone alert with `column_expression` returning non-numeric → validation rejects on save (same pathway as Metric).
- Empty query result (no rows): `current_value = None`, `fired = False`, AlertLog row still written (`deliveries = []`).
- Slack webhook returns 5xx: delivery JSON entry has `status="failed"` with HTTP code + body.
- All channels failed: every delivery JSON entry has `status="failed"`; `fired = True` still.
- User without `can_create_alerts` hits POST /api/alerts/ → 403.
- Two workers race the same scheduled tick → only one AlertLog row created.

---

## 7. Milestones

Each milestone is independently shippable: backend + frontend deliver a working slice the user can exercise.

### Milestone 1: Alert data model + CRUD API (backend-only)

**Deliverable:** Two new models (`Alert`, `AlertLog`) with migrations and permission slugs. Full CRUD via `/api/alerts/`. No evaluator yet — Alerts can be created but won't fire.

**Services:** DDP_backend

**Backend tasks:**
- [ ] Create `ddpui/models/alert.py` with `Alert` + `AlertLog` (two models, with `recipients` JSON on Alert and `deliveries` JSON on AlertLog)
- [ ] `makemigrations` → `0XXX_alert_models.py`
- [ ] Manual migration `0XXX_alert_permissions.py` adding slugs and role mappings
- [ ] Create `ddpui/schemas/alert_schema.py`
- [ ] Create `ddpui/core/alerts/alert_service.py` with create/update/delete/toggle/list/list_firing/get_log (dry-run + evaluator come in later milestones)
- [ ] Create `ddpui/core/alerts/scheduling.py` — `is_due`, `derive_frequency_label`
- [ ] Create `ddpui/core/alerts/condition.py` — pure functions (used by listing for `condition_pretty`)
- [ ] Create `ddpui/api/alert_api.py` with all endpoints stubbed; dry-run + slack-webhook test return 501 for now
- [ ] Register router at `/api/alerts/` in `ddpui/routes.py`
- [ ] Validation: `schedule_cron` via croniter; aggregation/operator/rag_states allowed lists
- [ ] **Extend `GET /api/metrics/{id}/consumers/`** (in `ddpui/core/metric/metric_service.py`) to include alerts via `Alert.objects.filter(org=org, metric_id=metric_id)` — return as a third group alongside Charts and KPIs
- [ ] **Extend `GET /api/kpis/{id}/consumers/`** (in `ddpui/core/metric/kpi_service.py`) to include alerts via `Alert.objects.filter(org=org, kpi_id=kpi_id)`
- [ ] Update `MetricConsumersResponse` and `KPIConsumersResponse` schemas to include an `alerts: List[{id, name, alert_type}]` field
- [ ] Update existing `tests/core/test_metric_service.py` / `test_kpi_service.py` consumer-list tests to assert alerts appear
- [ ] Write `tests/core/alerts/test_scheduling.py`, `test_condition.py`, `test_alert_service.py` (CRUD only)
- [ ] Write `tests/api_tests/test_alert_api.py` (CRUD only)

**Acceptance criteria:**
- All API tests pass.
- A developer can `curl POST /api/alerts/` with each alert type and have it persisted.
- Deleting a Metric/KPI cascades to its alerts (and AlertLog rows) — no error raised; alerts are silently removed.
- `GET /api/metrics/{id}/consumers/` returns alerts that reference the metric (alongside Charts and KPIs).
- `GET /api/kpis/{id}/consumers/` returns alerts that reference the KPI.
- `pylint`, `black`, and pre-commit pass.

---

### Milestone 2: Authoring wizard UI (Steps 1 + 2)

**Deliverable:** Authoring wizard works end-to-end for all three alert types except Step 3 (Test). Save creates an Alert in the DB. Edit re-opens the same wizard prefilled. Entry-point CTAs from Metrics page, KPI detail drawer, and /alerts page (placeholder listing). The "Send test message" Slack button works (via Milestone-3 endpoint, but we can stub-call the backend now and finish the impl in M3).

**Services:** DDP_backend (slack-webhook test endpoint only) + webapp_v2

**Backend tasks:**
- [ ] Implement `POST /api/alerts/test-slack-webhook/` (the only delivery code needed at this milestone)

**Frontend tasks:**
- [ ] Create `types/alerts.ts` mirroring backend schemas
- [ ] Create `hooks/api/useAlerts.ts` (CRUD + toggle; dry-run hook added in M3)
- [ ] Create `components/alerts/AlertWizardModal.tsx` with step state + form
- [ ] Create `components/alerts/AlertDefineStep.tsx` (3 type-specific layouts) + `ScheduleField`
- [ ] Create `components/alerts/AlertNotifyStep.tsx` + `RecipientCombobox` + `TemplateEditor`
- [ ] `MetricColumnAggregationFields` extracted from `metric-form-dialog.tsx` (or shared inline)
- [ ] Create `app/alerts/page.tsx` with a placeholder table (lists Alerts from `useAlerts`)
- [ ] Add "Create Alert" entry to Metrics page row action menu
- [ ] Add "Create Alert" CTA to KPI detail drawer
- [ ] Local-time → UTC cron utility + reverse for edit mode
- [ ] Toasts on success/failure for create/edit/delete/toggle
- [ ] Frontend tests for wizard navigation, RecipientCombobox, ScheduleField cron conversion

**Acceptance criteria:**
- Create flow from each of three entry points opens the wizard prefilled correctly.
- Save creates an Alert; placeholder listing shows it.
- Edit prefills wizard, save updates the Alert.
- Delete from row removes the Alert (with confirmation modal).
- Slack test message button hits backend; success/failure rendered inline.
- Enable/disable toggle works from the (placeholder) row.
- All client-side validation errors render inline.

---

### Milestone 3: Evaluation engine (dispatcher + evaluator + delivery + dry-run)

**Deliverable:** Saved alerts actually fire on schedule. SES emails arrive. Slack posts land. AlertFire + AlertDelivery rows written. Step 3 of the wizard (Test) shows real dry-run results.

**Services:** DDP_backend + webapp_v2 (Step 3 UI)

**Backend tasks:**
- [ ] Implement `ddpui/core/alerts/alert_query.py` — build SQL for the three types (delegate to MetricService/KPIService where possible)
- [ ] Implement `ddpui/core/alerts/condition.py` evaluator (extend M1 stub if needed)
- [ ] Implement `ddpui/core/alerts/rendering.py` with pystache + per-type token resolvers
- [ ] Implement `ddpui/core/alerts/delivery.py` — SES per recipient, Slack webhook POST, per-recipient status capture
- [ ] Implement `ddpui/celeryworkers/alert_tasks.py` — `dispatch_due_alerts` and `evaluate_alert`
- [ ] Configure `CELERY_BEAT_SCHEDULE["alerts-dispatcher"]` (60s)
- [ ] Implement `AlertService.dry_run` (reuses query builder + condition + rendering paths but no delivery, no persistence)
- [ ] Wire `POST /api/alerts/test/` to `AlertService.dry_run`
- [ ] Wire AlertLog writing inside `evaluate_alert` (one row per evaluation; deliveries collected into a list and written into the row's `deliveries` JSON). No summary roll-up stored or computed.
- [ ] Write `tests/core/alerts/test_alert_query.py`, `test_rendering.py`, `test_delivery.py`, `test_alert_tasks.py`
- [ ] Write integration test (eager celery) for full dispatch → evaluate → fire cycle with claim dedup

**Frontend tasks:**
- [ ] Implement `components/alerts/AlertTestStep.tsx` — calls `POST /api/alerts/test/` and renders banner, value, condition, rendered messages, collapsible SQL
- [ ] Update `AlertWizardModal` to wire Step 2 → Step 3 transition through the test endpoint
- [ ] Re-test allowed: going back to Step 1/2 and forward re-runs the dry-run
- [ ] Frontend tests for Step 3 UI states (would-fire, would-not-fire, empty-result, error)

**Acceptance criteria:**
- Create an alert with `schedule_cron = "* * * * *"` (test seed) → within 60s it fires (visible via SES log + Slack channel).
- AlertLog row exists with SQL, value, fired status, condition snapshot, and `deliveries` JSON populated with per-recipient + Slack entries.
- Dry-run from wizard Step 3 returns same SQL but no AlertLog row created.
- Re-running dispatcher within the same minute does not double-fire (claim dedup verified).
- Slack-webhook POST 5xx is captured inside the `deliveries` JSON entry with HTTP code + body; `summary_status` reflects the mix.

---

### Milestone 4: /alerts listing + Alert log modal + Firing tab

**Deliverable:** Real /alerts page with All alerts + Firing tabs, column filters/sorts, row 3-dot menu (Edit / Delete / Alert log), enable/disable toggle, empty states. Alert log modal opens from any row showing paginated fire history with per-fire expand → recipient list + per-recipient delivery status + collapsible SQL.

**Services:** webapp_v2 (frontend-heavy) + DDP_backend (firing list + fires list endpoint polish)

**Backend tasks:**
- [ ] Polish `GET /api/alerts/firing/` — efficient query: alerts whose most recent `AlertLog.fired = True`
- [ ] Polish `GET /api/alerts/{id}/logs/` — pagination over AlertLog rows (deliveries already embedded as JSON, no join needed)
- [ ] Fire-streak computation in `AlertListItem` (consecutive recent fires; cap at some N like 10) — uses `AlertLog.fired` over the last N rows
- [ ] Indexes: `(alert, -evaluated_at)` on AlertLog (added in M1) — verify query plan

**Frontend tasks:**
- [ ] Replace M2's placeholder table with full `AlertsTable` + Tabs (All alerts / Firing)
- [ ] Column-header sort + filter affordances per spec
- [ ] Subtitle in name cell with click navigation:
  - Metric alerts → metric edit page
  - KPI alerts → KPI annotation page
  - Standalone → dataset name plain text
- [ ] In-row enable/disable toggle (calls `PATCH /api/alerts/{id}/toggle/`)
- [ ] `AlertLogModal.tsx` with fire-row expand, recipient grouping, per-recipient status icons, collapsible SQL, paginated history
- [ ] Empty states: "No alerts yet" (with CTAs to Metrics / KPIs / Create Alert) and "No alerts firing"
- [ ] Disabled row treatment: muted text, off-state toggle, never on Firing tab
- [ ] **Metric consumers UI** — wherever the Metrics page renders the consumer list (the surface that says "this Metric is used by N Charts and M KPIs"), add an Alerts group. Source: extended `/api/metrics/{id}/consumers/`. Click an alert row → open the AlertWizardModal in edit mode for that alert.
- [ ] **KPI consumers UI** — same treatment for the KPI detail drawer's "Used by" / consumers section.
- [ ] **Delete confirmation message** — when delete is attempted on a Metric/KPI with alerts, the existing confirmation dialog must enumerate alerts alongside charts/KPIs so the user sees what will cascade.
- [ ] Frontend tests for listing tabs, row interactions, log modal expand/collapse
- [ ] Frontend test for Metric consumers list rendering alerts

**Acceptance criteria:**
- All spec scenarios in Story 5 and Story 6 visually verified end-to-end.
- Tab switching, sorting, filtering work without flicker.
- Default sort = Last fire descending.
- Alert log modal reaches consistent state from either tab.
- Disabled alerts are skipped by dispatcher (regression test M3 still passes).
- On the Metrics page, opening a Metric that has alerts shows those alerts in the consumers/dependencies area; same for KPIs in the KPI detail drawer.
- Attempting to delete a Metric/KPI with alerts shows the alerts in the confirmation dialog (so user knows what will be deleted alongside).

---

### Milestone 5: Polish — role gating, toasts coverage, validation copy, unhide nav

**Deliverable:** Spec validation passes (`/engineering/validate-spec`). All toasts and visual treatments per spec. Role-gated UI affordances per Story 9. Alerts nav item visible in production.

**Services:** webapp_v2 + DDP_backend (role mapping cleanup)

**Backend tasks:**
- [ ] Audit role → permission mapping; finalize assignments for `can_view_alerts`, `can_create_alerts`, `can_edit_alerts`, `can_delete_alerts`
- [ ] Migration adjustment if mapping changes

**Frontend tasks:**
- [ ] Wire `useUserPermissions().hasPermission(...)` into every entry-point CTA (hidden when missing create role)
- [ ] Wire into Edit/Delete/Toggle controls (disabled + tooltip when missing edit/delete role)
- [ ] Tooltip copy per spec
- [ ] All toast strings exactly per spec § "Toast notifications"
- [ ] Validation copy fix (`"Invalid email address."`), button casing (`Create alert`), sidebar `billing` typo, KPI menu typo per `design.md` feedback items 8–12
- [ ] Disabled row treatment per design.md item 14
- [ ] Empty states per design.md item 5
- [ ] Recipient chip visual differentiation per design.md item 7
- [ ] Remove `/alerts` from `PRODUCTION_HIDDEN_ITEMS` in `main-layout.tsx`
- [ ] Update screenshot recipe `scripts/recipes/alerts.yaml` (new) so docs can refresh

**Acceptance criteria:**
- `/engineering/validate-spec features/alerts/v1/spec.md` passes.
- All design.md feedback items 1–17 verified against the implementation (or filed as v2 if explicitly deferred).
- Permission matrix tested for all four slugs across two roles.

---

## 8. Open Questions & Risks

### Open questions

1. **Final role → permission mapping.** Mirroring metrics_kpis is the safe default; Pratiksha to confirm Org Admin / Analyst / Program Lead mappings before Milestone 5.
2. **Slack webhook URL — encrypt at rest in v1?** Recommend no (consistent with Discord webhook precedent). Mask on GET responses (decided). Encrypt + KMS in v2 if compliance requires.
3. **`AlertFire.sql_executed` visibility.** Spec explicitly makes this visible to every logged-in user with view access. Confirmed in research §4; flagging in case stakeholders revisit.
4. **External recipient PII retention.** Spec says history is unlimited. External email addresses in AlertFire snapshots accumulate forever. Acceptable for v1; flag for review if a data-deletion request lands.
5. **Cron drift on schedule edit.** When a user edits an alert's schedule mid-day, `last_evaluated_at` is preserved; the next tick uses the new cron. This is correct behavior but could surprise users ("I changed it to 5pm, why did it fire at 5pm if last was 9am?"). Spec doesn't ask for a reset — leave as-is, document in user docs.
6. **Schedule-frequency derivation from cron for display.** The listing UI shows "daily/weekly/monthly." We derive this from cron pattern shape. If the cron pattern doesn't match one of our wizard-produced shapes, fall back to displaying the raw cron string. Confirm this fallback acceptable.
7. **Spec Story 6 "Delivery status column" — deferred.** Spec asks for a Success/Partial/Failed badge on each collapsed Alert log row. We are NOT storing or computing a summary roll-up in v1 — the backend just returns `fired` + `deliveries`. Frontend can either: (a) ship the modal without the badge in v1, or (b) compute the badge client-side from `deliveries` if it's cheap enough. Decision deferred to UI implementation; flagged here so we don't claim full Story 6 compliance until decided.
8. **Spec deviation — Metric/KPI delete behavior.** Spec Story 5 says *"Deleting a Metric or KPI is blocked while any alert references it."* This plan uses `on_delete=CASCADE` instead: deleting a Metric/KPI silently deletes its alerts (and AlertLog rows). Per-user decision in scope-confirmation conversation. The spec text should be updated to match before merging; the Metric/KPI delete confirmation dialog should enumerate dependent alerts so the cascade is not surprising.

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **Beat tick coincidence drift over time** — if dispatcher runs at exactly the second the cron tick fires, edge case for `get_prev` returning the tick itself. | Off-by-1-second confusion in tests. | `croniter.get_prev(datetime, ret_type=datetime)` returns the most recent past or equal — verify in unit tests; treat "equal" as already-past. |
| **DST shift** in non-IST orgs — alerts silently shift by 1 hour twice a year. | User-perceived bug. | Documented limitation; v2 candidate (add `schedule_timezone` column). |
| **Worker swamp on coincident schedules** — many alerts on `0 9 * * *` all fire at once. | Spike in warehouse query load + SES rate-limit. | Acceptable at v1 scale. If it bites, jitter dispatch by alert.id hash within a small window, or dedicated alert queue with concurrency cap. |
| **Slack webhook URL leak via masked-but-not-redacted logs** | Secret exposure. | Audit logging; ensure webhook URL is never logged at INFO level; redact in error messages. |
| **External recipient delivery to non-Dalgo users** with no opt-out mechanism. | Compliance / spam complaints. | v1: acceptable per spec. v2: add unsubscribe link to external-recipient emails. |
| **`column_expression` validation rejects user intent** — overly strict sqlparse rule rejects valid expressions. | Author frustration. | Use same validator as Metric — known surface; team has experience tuning it. |
| **AlertLog history grows unbounded** — even at low alert counts, daily alerts × years = many rows per alert. | Storage growth (slow). | Acceptable through v1 (NGO scale). Add retention policy in v2 if needed. |

---

## Quality Checklist

- [x] `README.md` and `docs/domain-map.md` were read before research began
- [x] Blast Radius section lists every 1-hop and 2-hop consumer from the domain map
- [x] Every affected surface has a confirmed status (in-scope / deferred / out-of-scope) — none left as TBD
- [x] User was asked about surfaces the spec did not explicitly address (in-app Notification feed, Pipeline trigger, DQ-check trigger)
- [x] HLD covers all affected services and their interactions
- [x] LLD has concrete schema, API, and component details
- [x] Security review covers auth, validation, and data access
- [x] Milestones are independently shippable and ordered
- [x] Testing strategy covers unit, integration, and edge cases
- [x] References existing codebase patterns

---

*Draft v1 generated from [v1 spec](./spec.md), [research](./research.md), and [domain map](../../../docs/domain-map.md). Decisions captured in scope-confirmation conversation 2026-06-11.*
