# Report Scheduling v1 -- Implementation Plan

**Status:** Draft v1
**Date:** 2026-05-08
**Spec source:** User-provided spec (Report Scheduling feature)
**Domain map:** `/Users/siddhant/Documents/Dalgo/dalgo-core/docs/domain-map.md`

---

## 1. Overview

Build end-to-end scheduled report generation and delivery: **Schedule configuration per dashboard -> Automated snapshot creation on schedule -> PDF generation and email delivery to recipient list -> In-app notifications for mentions and failures -> Recipient management**.

This extends the existing manual report-sharing flow (snapshot creation -> one-time email send) with recurring automation.

**Services affected:**
- **DDP_backend** -- New `ReportSchedule` and `ScheduleRecipient` models, schedule CRUD API, Celery Beat hourly scheduler task, automated snapshot creation, PDF email delivery, retry logic with failure notifications
- **webapp_v2** -- Schedule configuration UI on dashboards, recipient management, schedule status display

**Not affected:** prefect-proxy (scheduling is Celery-based, not orchestrated through Prefect)

---

## 2. Blast Radius

Derived from `docs/domain-map.md` by traversing from Dashboard (the entity being scheduled).

| Surface | Hop | Why affected | Edge type | Status | Notes |
|---------|-----|-------------|-----------|--------|-------|
| **ReportSnapshot** | 1 from Dashboard | Scheduled runs create snapshots | `snapshot-of` | **In scope** | Core deliverable -- auto-create snapshot on schedule |
| **Live public share** | 1 from Dashboard | Schedule configuration appears on dashboard settings | `embed` | **Not affected** | Scheduling is a separate config surface, not rendered on the dashboard itself |
| **Notification** | 1 from ReportSnapshot (via email delivery) | Failure notifications and delivery confirmations | `trigger` | **In scope** | Failure notifications to schedule creator |
| **OrgUser** | 1 from Notification | Recipients of scheduled emails and failure alerts | terminal | **In scope** | Recipient management |
| **Organization** | boundary | Multi-tenant scoping | — | **In scope** | All schedules are org-scoped |
| **Chart** | 1 from Dashboard (via ReportSnapshot) | Chart configs frozen in snapshot | `snapshot-of` | **Auto-inherited** | Existing freeze logic handles this |
| **KPI** | 1 from Dashboard (via ReportSnapshot) | KPI data frozen in snapshot | `snapshot-of` | **Auto-inherited** | Existing freeze logic handles this (Milestone 4 of Metrics & KPIs is complete) |
| **Alert** | 2 from Dashboard (via KPI -> Alert) | Not affected -- alerts are triggered independently | — | **Not affected** | No interaction with scheduling |
| **Pipeline** | 0 | Schedule timing should ideally follow successful pipeline runs | — | **Needs confirmation** | Spec says "scheduler runs hourly." Open question: should a scheduled report wait for the most recent pipeline to succeed first? Or just run on the clock? |
| **Explore** | 0 | Not affected | — | **Not affected** | — |

**Surfaces NOT addressed by the spec that need user confirmation:**
1. **Pipeline dependency** -- Should a scheduled report defer if the most recent pipeline run has not yet completed? This avoids generating reports with stale data. The spec says "runs hourly, checks for reports due" but does not mention pipeline run gating.
2. **Public share of scheduled reports** -- Are automatically-created snapshots also auto-shared publicly, or are they private by default? Recommendation: private by default.
3. **Comment/mention notifications vs. Report delivery notifications** -- The spec mentions "in-app and email alerts for @mentions and comment replies" alongside report delivery. The @mention system already exists (built in Metrics/KPIs v1, Milestone 4). Confirm: is the spec asking for a NEW notification channel, or should scheduled report delivery use the existing `Notification` model?

---

## 3. High-Level Design (HLD)

### 3.1 Architecture

```
                        webapp_v2
  ┌───────────────────────────────────────────────────┐
  │                                                   │
  │  Dashboard Settings → Schedule Config UI          │
  │  ┌─────────────────────────────────────────────┐  │
  │  │ Frequency picker, recipients list,          │  │
  │  │ test email, enable/disable toggle           │  │
  │  └────────────────────┬────────────────────────┘  │
  └───────────────────────┼───────────────────────────┘
                          │ HTTP (apiPost/apiGet/apiPut/apiDelete)
  ┌───────────────────────┼───────────────────────────┐
  │                 DDP_backend                        │
  │                          │                         │
  │  ┌───────────────────────┴──────────────────────┐  │
  │  │  /api/dashboards/:id/schedule                │  │
  │  │  CRUD + toggle + test-email                  │  │
  │  └───────────────────────┬──────────────────────┘  │
  │                          │                         │
  │  ┌───────────────────────┴──────────────────────┐  │
  │  │  ReportScheduleService                       │  │
  │  │  - Schedule CRUD                             │  │
  │  │  - Recipient management                      │  │
  │  │  - Due check logic                           │  │
  │  │  - Trigger report creation                   │  │
  │  └───────────────────────┬──────────────────────┘  │
  │                          │                         │
  │  ┌───────────────────────┴──────────────────────┐  │
  │  │  Celery Beat: check_scheduled_reports        │  │
  │  │  (runs every hour)                           │  │
  │  │                                              │  │
  │  │  For each due schedule:                      │  │
  │  │  1. Create snapshot (ReportService)          │  │
  │  │  2. Generate PDF (PdfExportService)          │  │
  │  │  3. Email to recipients (AWS SES)            │  │
  │  │  4. On failure: retry up to 3x, then notify  │  │
  │  └──────────────────────────────────────────────┘  │
  │                                                    │
  │  Existing infrastructure reused:                   │
  │  - ReportService.create_snapshot()                 │
  │  - PdfExportService.generate_pdf()                 │
  │  - send_email_with_attachment()                    │
  │  - create_notification()                           │
  └────────────────────────────────────────────────────┘
```

### 3.2 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Scheduling mechanism** | Celery Beat hourly task with custom check logic | Dalgo already uses Celery Beat for periodic tasks (`setup_periodic_tasks` in `ddpui/celeryworkers/tasks.py`). Adding one more hourly task is trivial. No need for Prefect or a custom scheduler. |
| **Schedule storage** | Django model (`ReportSchedule`) with `next_run_at` field | Simpler than Celery Beat dynamic schedules. The hourly check task queries for schedules where `next_run_at <= now()` and `is_active = True`. After execution, it computes and stores the next `next_run_at`. |
| **Report creation reuse** | Call `ReportService.create_snapshot()` directly | The existing manual snapshot creation logic is well-tested and handles KPI charts, filter injection, and chart freezing. No need to duplicate. |
| **PDF + email reuse** | Reuse `PdfExportService.generate_pdf()` and `send_email_with_attachment()` | The existing `send_report_email_task` in `report_tasks.py` already does PDF generation + email delivery. We can extract a shared helper or call the same primitives. |
| **Email sender address** | Use existing `SES_SENDER_EMAIL` (notifications@dalgo.org or similar) in v1 | Decision on separate `reports@dalgo.org` deferred. Spec says "Check unsubscribe rates first." v1 uses what exists. |
| **Notification on failure** | Reuse existing `create_notification()` | The existing pattern in `report_tasks.py` already creates urgent notifications on email failure. Extend for schedule failures. |
| **Recipient storage** | Separate `ScheduleRecipient` model (not just a JSON list) | Allows proper email validation, individual management, and future extensions (e.g., per-recipient delivery status). |
| **Date range for scheduled snapshots** | Rolling window based on frequency | Weekly: last 7 days ending on trigger day. Monthly: last month. Quarterly: last quarter. Configurable via `date_column` on the schedule. |
| **Schedule-per-dashboard** | One active schedule per dashboard | Simplifies UI and avoids confusion. The `unique_together` constraint on `(dashboard, org)` with `is_active=True` enforces this. |

### 3.3 Data Flow: Scheduled Report Execution

1. Celery Beat fires `check_scheduled_reports` every hour
2. Query: `ReportSchedule.objects.filter(is_active=True, next_run_at__lte=now())`
3. For each due schedule:
   a. Compute `period_start` and `period_end` from frequency + trigger time
   b. Call `ReportService.create_snapshot(title, dashboard_id, system_orguser, date_column, period_start, period_end)`
   c. Dispatch `send_scheduled_report_email_task.delay(snapshot_id, schedule_id)` (Celery async task)
   d. Update `schedule.last_run_at = now()`, compute and set `schedule.next_run_at`
   e. Create a `ScheduleRun` record for auditing
4. In `send_scheduled_report_email_task`:
   a. Generate PDF via `PdfExportService.generate_pdf()`
   b. For each recipient: `send_email_with_attachment()`
   c. On failure: retry up to 3 times (Celery `max_retries=3, retry_backoff=True`)
   d. After all retries exhausted: `create_notification()` to schedule creator with urgent=True

---

## 4. Low-Level Design (LLD)

### 4.1 Data Model

#### ReportSchedule model (`ddpui/models/report_schedule.py` -- new file)

```python
class ScheduleFrequency(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

class ReportSchedule(models.Model):
    id = models.BigAutoField(primary_key=True)
    
    # Which dashboard to snapshot
    dashboard = models.ForeignKey("Dashboard", on_delete=models.CASCADE, related_name="schedules")
    
    # Schedule configuration
    frequency = models.CharField(max_length=20, choices=ScheduleFrequency.choices())
    
    # Day-of-week (0=Monday, 6=Sunday) for weekly; day-of-month (1-31) for monthly
    # Ignored for quarterly (always 1st of Jan/Apr/Jul/Oct)
    trigger_day = models.IntegerField(default=0)
    
    # Hour of day (0-23) in org's timezone
    trigger_hour = models.IntegerField(default=9)
    
    # Timezone for scheduling (e.g., "Asia/Kolkata")
    timezone = models.CharField(max_length=50, default="Asia/Kolkata")
    
    # Date column configuration (same as snapshot creation)
    # {schema_name, table_name, column_name}
    date_column = models.JSONField(default=dict, blank=True)
    
    # State
    is_active = models.BooleanField(default=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    
    # Retry tracking
    consecutive_failures = models.IntegerField(default=0)
    
    # Org scoping + ownership
    org = models.ForeignKey("Org", on_delete=models.CASCADE)
    created_by = models.ForeignKey("OrgUser", on_delete=models.CASCADE, related_name="schedules_created")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "report_schedule"
        constraints = [
            models.UniqueConstraint(
                fields=["dashboard", "org"],
                name="unique_schedule_per_dashboard"
            )
        ]
```

#### ScheduleRecipient model (same file)

```python
class ScheduleRecipient(models.Model):
    id = models.BigAutoField(primary_key=True)
    schedule = models.ForeignKey(ReportSchedule, on_delete=models.CASCADE, related_name="recipients")
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True, default="")
    
    # Optional link to OrgUser (for internal recipients)
    orguser = models.ForeignKey("OrgUser", on_delete=models.SET_NULL, null=True, blank=True)
    
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey("OrgUser", on_delete=models.SET_NULL, null=True, related_name="recipients_added")
    
    class Meta:
        db_table = "schedule_recipient"
        constraints = [
            models.UniqueConstraint(
                fields=["schedule", "email"],
                name="unique_recipient_per_schedule"
            )
        ]
```

#### ScheduleRun model (same file -- audit trail)

```python
class ScheduleRunStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"  # Some emails failed
    FAILURE = "failure"

class ScheduleRun(models.Model):
    id = models.BigAutoField(primary_key=True)
    schedule = models.ForeignKey(ReportSchedule, on_delete=models.CASCADE, related_name="runs")
    snapshot = models.ForeignKey("ReportSnapshot", on_delete=models.SET_NULL, null=True)
    
    status = models.CharField(max_length=20, choices=ScheduleRunStatus.choices())
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery tracking
    recipients_total = models.IntegerField(default=0)
    recipients_sent = models.IntegerField(default=0)
    recipients_failed = models.IntegerField(default=0)
    
    # Error details (JSON list of {email, error})
    error_details = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "schedule_run"
        ordering = ["-started_at"]
```

#### Migration
- Single migration file creating all three tables + permission slugs: `can_manage_report_schedules`
- Next migration number follows the current latest in DDP_backend

### 4.2 API Design

All endpoints nested under `/api/dashboards/{dashboard_id}/schedule/` per the spec.

**Request/Response Schemas** (`ddpui/schemas/schedule_schema.py` -- new file):

```python
# --- Create ---
class ScheduleCreate(Schema):
    frequency: str  # weekly | monthly | quarterly
    trigger_day: int = 0  # day-of-week (0-6) or day-of-month (1-31)
    trigger_hour: int = 9  # 0-23
    timezone: str = "Asia/Kolkata"
    date_column: Optional[dict] = None  # {schema_name, table_name, column_name}
    recipients: List[RecipientInput]  # [{email, name?}]

class RecipientInput(Schema):
    email: str
    name: Optional[str] = None

# --- Response ---
class ScheduleResponse(Schema):
    id: int
    dashboard_id: int
    frequency: str
    trigger_day: int
    trigger_hour: int
    timezone: str
    date_column: Optional[dict]
    is_active: bool
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]
    consecutive_failures: int
    recipients: List[RecipientResponse]
    created_by_email: str
    created_at: datetime
    updated_at: datetime

class RecipientResponse(Schema):
    id: int
    email: str
    name: str
    is_org_user: bool
    added_at: datetime

# --- Update ---
class ScheduleUpdate(Schema):
    frequency: Optional[str] = None
    trigger_day: Optional[int] = None
    trigger_hour: Optional[int] = None
    timezone: Optional[str] = None
    date_column: Optional[dict] = None
    is_active: Optional[bool] = None

# --- Recipient management ---
class AddRecipientsRequest(Schema):
    recipients: List[RecipientInput]

class RemoveRecipientsRequest(Schema):
    recipient_ids: List[int]

class CsvImportResponse(Schema):
    added: int
    skipped: int  # duplicates
    invalid: int
    errors: List[str]

# --- Test email ---
class TestEmailRequest(Schema):
    recipient_email: str

# --- Run history ---
class ScheduleRunResponse(Schema):
    id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    snapshot_id: Optional[int]
    recipients_total: int
    recipients_sent: int
    recipients_failed: int
```

**API Endpoints** (`ddpui/api/schedule_api.py` -- new file):

| Method | Endpoint | Permission | Description |
|--------|----------|-----------|-------------|
| `POST` | `/api/dashboards/{id}/schedule/` | `can_manage_report_schedules` | Create schedule + initial recipients |
| `GET` | `/api/dashboards/{id}/schedule/` | `can_view_dashboards` | Get current schedule with recipients |
| `PATCH` | `/api/dashboards/{id}/schedule/` | `can_manage_report_schedules` | Update schedule config or toggle active |
| `DELETE` | `/api/dashboards/{id}/schedule/` | `can_manage_report_schedules` | Delete schedule |
| `POST` | `/api/dashboards/{id}/schedule/recipients/` | `can_manage_report_schedules` | Add recipients |
| `DELETE` | `/api/dashboards/{id}/schedule/recipients/` | `can_manage_report_schedules` | Remove recipients |
| `POST` | `/api/dashboards/{id}/schedule/recipients/import-csv/` | `can_manage_report_schedules` | CSV import |
| `POST` | `/api/dashboards/{id}/schedule/test-email/` | `can_manage_report_schedules` | Send test email |
| `GET` | `/api/dashboards/{id}/schedule/runs/` | `can_view_dashboards` | List run history |

### 4.3 Backend Logic

#### ReportScheduleService (`ddpui/services/report_schedule_service.py` -- new file)

Key methods:

- `create_schedule(dashboard_id, data, orguser)` -- Validates dashboard exists and belongs to org, validates frequency + trigger_day range, computes initial `next_run_at`, creates schedule + recipients
- `get_schedule(dashboard_id, org)` -- Returns schedule with recipients or 404
- `update_schedule(dashboard_id, org, data)` -- Updates fields, recomputes `next_run_at` if frequency/trigger changed
- `delete_schedule(dashboard_id, org)` -- Deletes schedule and all recipients
- `add_recipients(schedule, recipients)` -- Validates emails, de-duplicates, links to OrgUser if email matches
- `remove_recipients(schedule, recipient_ids)` -- Removes by ID
- `import_csv_recipients(schedule, csv_content)` -- Parses CSV (columns: email, name), validates, adds
- `send_test_email(schedule, recipient_email, orguser)` -- Generates current snapshot, sends one-off email
- `compute_next_run_at(schedule)` -- Based on frequency, trigger_day, trigger_hour, timezone

**Next run computation logic:**

```python
def compute_next_run_at(schedule: ReportSchedule) -> datetime:
    tz = pytz.timezone(schedule.timezone)
    now = datetime.now(tz)
    
    if schedule.frequency == "weekly":
        # Find next occurrence of trigger_day (0=Mon) at trigger_hour
        days_ahead = (schedule.trigger_day - now.weekday()) % 7
        if days_ahead == 0 and now.hour >= schedule.trigger_hour:
            days_ahead = 7
        next_run = now.replace(hour=schedule.trigger_hour, minute=0, second=0, microsecond=0)
        next_run += timedelta(days=days_ahead)
        
    elif schedule.frequency == "monthly":
        # trigger_day = 1-31 (clamped to month length)
        day = min(schedule.trigger_day, calendar.monthrange(now.year, now.month)[1])
        next_run = now.replace(day=day, hour=schedule.trigger_hour, minute=0, second=0, microsecond=0)
        if next_run <= now:
            # Move to next month
            if now.month == 12:
                next_run = next_run.replace(year=now.year + 1, month=1)
            else:
                next_run = next_run.replace(month=now.month + 1)
            day = min(schedule.trigger_day, calendar.monthrange(next_run.year, next_run.month)[1])
            next_run = next_run.replace(day=day)
            
    elif schedule.frequency == "quarterly":
        # 1st of Jan/Apr/Jul/Oct at trigger_hour
        quarter_months = [1, 4, 7, 10]
        for month in quarter_months:
            candidate = now.replace(month=month, day=1, hour=schedule.trigger_hour, minute=0, second=0, microsecond=0)
            if candidate.month < now.month:
                candidate = candidate.replace(year=now.year + 1)
            if candidate > now:
                next_run = candidate
                break
        else:
            next_run = now.replace(year=now.year + 1, month=1, day=1, hour=schedule.trigger_hour, minute=0, second=0, microsecond=0)
    
    return next_run.astimezone(pytz.UTC)
```

**Period computation for snapshot date range:**

```python
def compute_period_range(schedule: ReportSchedule, run_time: datetime) -> tuple[date, date]:
    """Compute the reporting period for the snapshot."""
    if schedule.frequency == "weekly":
        period_end = run_time.date()
        period_start = period_end - timedelta(days=7)
    elif schedule.frequency == "monthly":
        period_end = run_time.date().replace(day=1) - timedelta(days=1)  # last day of prev month
        period_start = period_end.replace(day=1)  # first day of prev month
    elif schedule.frequency == "quarterly":
        # Prev quarter
        current_quarter_start_month = ((run_time.month - 1) // 3) * 3 + 1
        period_end = run_time.date().replace(month=current_quarter_start_month, day=1) - timedelta(days=1)
        period_start = (period_end.replace(day=1) - timedelta(days=60)).replace(day=1)  # simplified; proper quarter start
    return period_start, period_end
```

#### Celery task: Hourly check (`ddpui/celeryworkers/schedule_tasks.py` -- new file)

```python
@app.task(bind=True)
def check_scheduled_reports(self):
    """Hourly task: find due schedules and trigger report generation."""
    now = timezone.now()
    due_schedules = ReportSchedule.objects.filter(
        is_active=True,
        next_run_at__lte=now,
    ).select_related('dashboard', 'org', 'created_by')
    
    for schedule in due_schedules:
        try:
            execute_scheduled_report.delay(schedule.id)
        except Exception as e:
            logger.error(f"Failed to dispatch schedule {schedule.id}: {e}")

@app.task(bind=True, max_retries=3, retry_backoff=True)
def execute_scheduled_report(self, schedule_id):
    """Execute a single scheduled report: create snapshot + send emails."""
    schedule = ReportSchedule.objects.select_related(
        'dashboard', 'org', 'created_by'
    ).get(id=schedule_id)
    
    # Create run record
    run = ScheduleRun.objects.create(
        schedule=schedule,
        status="running",
        recipients_total=schedule.recipients.count(),
    )
    
    try:
        # Compute period
        period_start, period_end = compute_period_range(schedule, timezone.now())
        
        # Create snapshot using existing ReportService
        system_orguser = schedule.created_by  # or a system user
        title = f"{schedule.dashboard.title} - {schedule.get_frequency_display()} Report ({period_end})"
        
        snapshot = ReportService.create_snapshot(
            title=title,
            dashboard_id=schedule.dashboard.id,
            orguser=system_orguser,
            date_column=schedule.date_column,
            period_start=period_start,
            period_end=period_end,
        )
        
        run.snapshot = snapshot
        run.save()
        
        # Generate PDF and send emails
        share_token = ReportService.ensure_share_token(snapshot)
        pdf_bytes = PdfExportService.generate_pdf(snapshot.id, share_token)
        
        recipients = list(schedule.recipients.values_list('email', flat=True))
        failed = []
        
        for email in recipients:
            try:
                plain, html_body = render_scheduled_report_email(...)
                send_email_with_attachment(email, subject, plain, html_body, pdf_bytes, filename)
            except Exception as e:
                failed.append({"email": email, "error": str(e)})
        
        # Update run record
        run.recipients_sent = len(recipients) - len(failed)
        run.recipients_failed = len(failed)
        run.error_details = failed
        run.status = "success" if not failed else "partial_failure"
        run.completed_at = timezone.now()
        run.save()
        
        # Update schedule
        schedule.last_run_at = timezone.now()
        schedule.next_run_at = compute_next_run_at(schedule)
        schedule.consecutive_failures = 0
        schedule.save()
        
    except Exception as e:
        run.status = "failure"
        run.error_details = [{"error": str(e)}]
        run.completed_at = timezone.now()
        run.save()
        
        schedule.consecutive_failures += 1
        schedule.next_run_at = compute_next_run_at(schedule)
        schedule.save()
        
        # Notify schedule creator
        if self.request.retries >= self.max_retries:
            create_notification(NotificationDataSchema(
                author="System",
                message=f'Scheduled report for "{schedule.dashboard.title}" failed after 3 retries: {str(e)}',
                email_subject=f"Scheduled report failed: {schedule.dashboard.title}",
                urgent=True,
                recipients=[schedule.created_by.id],
            ))
        else:
            raise self.retry(exc=e)
```

Register in `setup_periodic_tasks`:
```python
# In ddpui/celeryworkers/tasks.py, inside setup_periodic_tasks():
sender.add_periodic_task(
    crontab(minute=0),  # every hour at :00
    check_scheduled_reports.s(),
    name="check scheduled reports",
)
```

### 4.4 Frontend Components

#### New Components

**`components/reports/schedule-config-dialog.tsx`** -- Dialog for creating/editing a schedule:
- Frequency picker (Weekly/Monthly/Quarterly radio buttons)
- Day-of-week selector (Weekly mode) or day-of-month picker (Monthly mode)
- Time picker (hour selector)
- Timezone selector (default: org timezone or Asia/Kolkata)
- Date column picker (reuse existing datetime column discovery from `create-snapshot-dialog.tsx`)
- Recipients section with inline management

**`components/reports/schedule-recipients.tsx`** -- Recipient list management:
- Email input with comma separation (same pattern as `share-via-email-dialog.tsx`)
- CSV import button (file input, parse client-side, show preview, submit)
- List of current recipients with remove buttons
- "Test Email" button per recipient or for current user

**`components/reports/schedule-status-card.tsx`** -- Status display on dashboard page:
- Shows: frequency, next run, last run status, recipient count
- Toggle active/inactive
- Link to run history
- Edit/delete buttons

**`components/reports/schedule-run-history.tsx`** -- Run history drawer:
- List of past runs with status (success/partial/failure), timestamp, recipient stats
- Click to expand details (error list, snapshot link)

#### Modified Components

**`components/dashboard/dashboard-builder-v2.tsx`** or dashboard settings:
- Add "Schedule" tab or button in dashboard actions
- Opens `schedule-config-dialog.tsx`

**`app/dashboards/[id]/page.tsx`** or relevant dashboard page:
- Show `schedule-status-card.tsx` when a schedule exists

#### New Hooks

**`hooks/api/useSchedule.ts`**:
```typescript
export function useSchedule(dashboardId: number) { ... }  // SWR GET
export async function createSchedule(dashboardId: number, data: ScheduleCreate) { ... }
export async function updateSchedule(dashboardId: number, data: ScheduleUpdate) { ... }
export async function deleteSchedule(dashboardId: number) { ... }
export async function addRecipients(dashboardId: number, recipients: RecipientInput[]) { ... }
export async function removeRecipients(dashboardId: number, recipientIds: number[]) { ... }
export async function importCsvRecipients(dashboardId: number, csvContent: string) { ... }
export async function sendTestEmail(dashboardId: number, email: string) { ... }
export function useScheduleRuns(dashboardId: number) { ... }  // SWR GET
```

#### New Types

**`types/schedule.ts`**:
```typescript
export interface ReportSchedule {
  id: number;
  dashboard_id: number;
  frequency: 'weekly' | 'monthly' | 'quarterly';
  trigger_day: number;
  trigger_hour: number;
  timezone: string;
  date_column: DateColumn | null;
  is_active: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  consecutive_failures: number;
  recipients: ScheduleRecipient[];
  created_by_email: string;
  created_at: string;
  updated_at: string;
}

export interface ScheduleRecipient {
  id: number;
  email: string;
  name: string;
  is_org_user: boolean;
  added_at: string;
}

export interface ScheduleRun {
  id: number;
  status: 'success' | 'partial_failure' | 'failure';
  started_at: string;
  completed_at: string | null;
  snapshot_id: number | null;
  recipients_total: number;
  recipients_sent: number;
  recipients_failed: number;
}
```

---

## 5. Security Review

### Authentication & Authorization
- All schedule endpoints protected with `@has_permission(["can_manage_report_schedules"])` for writes
- Read-only endpoints (GET schedule, GET runs) use `@has_permission(["can_view_dashboards"])`
- New permission slug `can_manage_report_schedules` added via migration, assigned to appropriate roles
- Schedule creation validates that the dashboard belongs to `orguser.org`

### Multi-Tenant Isolation
- `ReportSchedule.org` FK ensures org scoping
- All queries filter by `org`: `ReportSchedule.objects.filter(dashboard__org=org)`
- The hourly check task processes schedules across orgs but creates snapshots via `ReportService.create_snapshot()` which enforces org scoping
- Recipients are per-schedule (not shared across orgs)

### Email Validation
- `ScheduleRecipient.email` uses Django's `EmailField` with built-in validation
- CSV import validates each email before insert
- No cross-org email sending (recipients are managed per schedule, but emails can be external)

### Rate Limiting
- Test email endpoint: rate-limit to 5 test emails per hour per org (prevent abuse)
- Scheduled runs: inherently limited by frequency (max 1 per hour per schedule)
- SES sending limits: AWS SES has per-account sending quotas. The system should not exceed ~20 orgs x ~20 recipients = ~400 emails per hourly batch. Well within typical SES limits.

### Data Privacy
- Report PDFs contain org data -- email recipients are chosen by the org user, not by the system
- Scheduled report snapshots are private by default (no `is_public` auto-setting)
- Share tokens are generated for PDF rendering but the snapshot itself remains private

---

## 6. Testing Strategy

### Unit Tests

**Backend:**
- `tests/services/test_report_schedule_service.py`:
  - Create schedule with valid/invalid frequencies
  - `compute_next_run_at()` for all frequency types + edge cases (month boundaries, DST transitions)
  - `compute_period_range()` for all frequencies
  - Add/remove recipients, duplicate handling
  - CSV import parsing with valid/invalid/mixed data
  - Schedule toggle (active/inactive) recomputes `next_run_at`
  - Delete cascade (schedule -> recipients, schedule -> runs)
- `tests/celeryworkers/test_schedule_tasks.py`:
  - `check_scheduled_reports` finds due schedules
  - `execute_scheduled_report` creates snapshot + sends emails
  - Retry logic on failure (mock email service to fail)
  - Notification on final failure
  - `ScheduleRun` audit records created correctly
- `tests/api_tests/test_schedule_api.py`:
  - CRUD endpoints with permission checks
  - Recipient management endpoints
  - Test email endpoint
  - Run history endpoint

**Frontend:**
- `components/reports/__tests__/schedule-config-dialog.test.tsx`:
  - Frequency picker changes show/hide appropriate day pickers
  - Validation: trigger_day range by frequency
  - Recipient input parsing (comma-separated)
- `components/reports/__tests__/schedule-recipients.test.tsx`:
  - Add/remove recipients
  - Invalid email rejection
  - CSV import preview

### Edge Cases
- Monthly schedule with trigger_day=31 on February (should clamp to 28/29)
- Quarterly schedule crossing year boundary (Oct -> Jan)
- Timezone handling: DST transitions (trigger_hour stays consistent in local time)
- Dashboard deleted while schedule exists (cascade delete via FK)
- All recipients fail (full failure notification)
- Schedule with 0 recipients (should skip email, create snapshot only? Or refuse to activate?)
- Concurrent hourly checks (use `select_for_update()` or a lock to prevent double execution)
- Very large org with many charts (PDF generation timeout)

---

## 7. Milestones

Each milestone delivers independently testable functionality.

### Milestone 1: Schedule Data Model + CRUD API

**Deliverable:** Backend models, migrations, and CRUD API for creating, reading, updating, and deleting report schedules with recipients. No actual scheduling logic yet.

**Services:** DDP_backend

**Backend tasks:**
- [ ] Create `ddpui/models/report_schedule.py` with `ReportSchedule`, `ScheduleRecipient`, `ScheduleRun`
- [ ] Create migration (tables + `can_manage_report_schedules` permission)
- [ ] Create `ddpui/schemas/schedule_schema.py`
- [ ] Create `ddpui/services/report_schedule_service.py` (CRUD + recipient management + `compute_next_run_at`)
- [ ] Create `ddpui/api/schedule_api.py` (schedule_router nested under dashboards)
- [ ] Register routes in `ddpui/routes.py` (mount under dashboard_native_router or as separate router)
- [ ] Write unit tests for service layer
- [ ] Write API tests

**Verification:**
- [ ] Can create a schedule for a dashboard via API
- [ ] Can add/remove recipients
- [ ] Can update frequency/trigger settings (next_run_at recomputes)
- [ ] Can delete a schedule
- [ ] Uniqueness enforced (one schedule per dashboard)
- [ ] Permission checks pass

---

### Milestone 2: Scheduler Task + Automated Report Creation

**Deliverable:** Celery Beat hourly task that finds due schedules, creates snapshots, generates PDFs, and sends emails. Failure notifications and retry logic.

**Services:** DDP_backend

**Backend tasks:**
- [ ] Create `ddpui/celeryworkers/schedule_tasks.py` with `check_scheduled_reports` and `execute_scheduled_report`
- [ ] Implement `compute_period_range()` for all frequencies
- [ ] Register hourly task in `setup_periodic_tasks()` in `tasks.py`
- [ ] Create email template for scheduled reports (`render_scheduled_report_email` in `email_templates.py`)
- [ ] Implement retry logic (Celery `max_retries=3, retry_backoff=True`)
- [ ] Implement failure notification via `create_notification()`
- [ ] Create `ScheduleRun` audit records on each execution
- [ ] Add `select_for_update()` or similar locking to prevent double execution on the same schedule
- [ ] Write tests for scheduler task (mock ReportService, PdfExportService, email)
- [ ] Add CSV recipient import endpoint

**Verification:**
- [ ] Create schedule, wait for hourly check -> snapshot created automatically
- [ ] Recipients receive email with PDF attachment
- [ ] Run history shows success record
- [ ] Simulate email failure -> retry up to 3 times -> failure notification to creator
- [ ] `next_run_at` advances correctly after each run

---

### Milestone 3: Schedule Configuration UI

**Deliverable:** Frontend UI for creating, viewing, editing, and deleting schedules from the dashboard page. Recipient management with CSV import. Test email button.

**Services:** webapp_v2

**Frontend tasks:**
- [ ] Create `types/schedule.ts`
- [ ] Create `hooks/api/useSchedule.ts`
- [ ] Create `components/reports/schedule-config-dialog.tsx` (frequency, day, hour, timezone, date column, recipients)
- [ ] Create `components/reports/schedule-recipients.tsx` (add/remove/CSV import)
- [ ] Create `components/reports/schedule-status-card.tsx` (status display + toggle)
- [ ] Create `components/reports/schedule-run-history.tsx` (history drawer)
- [ ] Add "Schedule" action button on dashboard page (in dashboard header actions or settings)
- [ ] Handle schedule create/edit/delete flows
- [ ] Implement test email button
- [ ] Write frontend tests

**Verification:**
- [ ] Navigate to dashboard -> click "Schedule Reports"
- [ ] Create schedule: pick frequency, day, time -> recipients -> save
- [ ] Schedule status card shows on dashboard page: "Weekly on Mondays at 9:00 AM"
- [ ] Add recipients manually and via CSV import
- [ ] Send test email -> recipient receives PDF
- [ ] Toggle schedule active/inactive
- [ ] View run history -> see past runs with status
- [ ] Delete schedule -> confirmation dialog -> removed

---

### Milestone 4: @Mention and Comment Notification Enhancements

**Deliverable:** In-app notifications for @mentions and comment replies in reports (if not already fully covered by existing implementation from Metrics/KPIs Milestone 4). This milestone is potentially minimal if the existing mention system already works end-to-end.

**Services:** DDP_backend + webapp_v2

**Backend tasks:**
- [ ] Verify existing mention notification flow works for report comments
- [ ] If needed: add comment-reply notification (notify previous commenters when a new comment is added to a thread)
- [ ] Confirm email delivery for mention notifications uses appropriate sender address

**Frontend tasks:**
- [ ] Verify notification bell shows mention notifications with deep links to report comments
- [ ] If needed: add unsubscribe preference for report notifications

**Verification:**
- [ ] @mention a user in a report comment -> they get in-app notification
- [ ] @mention a user in a report comment -> they get email notification (if email notifications enabled)
- [ ] Click notification -> navigates to report with comment thread open

---

## 8. Open Questions & Risks

### Open Questions

1. **Pipeline dependency gating**: Should scheduled reports wait for the latest pipeline run to complete successfully before generating? This avoids sending reports with stale data. **Recommendation**: v1 runs on the clock without gating. Add optional "wait for pipeline" flag in v2.

2. **Email sender address**: The spec mentions checking unsubscribe rates from `notifications@dalgo.org` and potentially using `reports@dalgo.org`. **Recommendation**: v1 uses whatever `SES_SENDER_EMAIL` is configured. Decision on separate sender address deferred until unsubscribe rate data is collected.

3. **Notification channel for report delivery**: The spec mentions "in-app only, new address (reports@dalgo.org), or hybrid" for delivery notifications. **Recommendation**: Report emails go directly via SES (as today). In-app notifications only for failures. No in-app notification for successful delivery (avoids notification spam).

4. **Quarterly schedule configurability**: Spec says "Not configurable in V1." Confirm: are quarters always Jan/Apr/Jul/Oct, or should they align to the org's fiscal year?

5. **Schedule with 0 recipients**: Should a schedule with no recipients still create a snapshot (for archival), or should activation require at least 1 recipient?

6. **Max recipients per schedule**: Current email sharing has `MAX_RECIPIENTS` (found in `utils.ts`). What's the limit for scheduled reports? **Recommendation**: 50 recipients per schedule in v1.

7. **System user for snapshot creation**: Scheduled snapshots are created programmatically. Should they be attributed to the schedule creator or a system user? **Recommendation**: schedule creator (so they can manage/delete the snapshots).

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| PDF generation timeout for large dashboards | Scheduled report fails, no email sent | Set generous timeout (60s), retry logic. Monitor average PDF generation time. |
| SES rate limiting under high load | Some emails not delivered | Batch emails within a schedule run, add delay between emails. SES limit is typically 14 emails/second. |
| Timezone edge cases (DST, non-standard offsets) | Reports trigger at wrong time | Use `pytz` for all timezone conversions. Store `next_run_at` in UTC. Test with common NGO timezones (IST, EAT, WAT). |
| Double execution of same schedule | Duplicate snapshots + emails | Use `select_for_update()` in the hourly check or a Redis lock per schedule ID. |
| Dashboard deleted while schedule exists | FK cascade deletes schedule -- clean | Django `on_delete=CASCADE` handles this. No orphaned schedules. |
| Recipient email bounces | SES reputation degradation | v2: track bounce notifications from SES. v1: rely on SES's built-in bounce handling. |
| Scheduled report volume growth | DB and storage growth from auto-generated snapshots | Consider snapshot retention policy (auto-delete snapshots older than N months) in v2. |

---

### Quality Checklist
- [x] `README.md` and `docs/domain-map.md` were read before research began
- [x] Blast Radius section lists every 1-hop and 2-hop consumer from the domain map
- [x] Every affected surface has a confirmed status (in-scope / deferred / needs-confirmation)
- [x] Surfaces not explicitly addressed by the spec are called out (Pipeline gating, public share of scheduled reports, notification channel)
- [x] HLD covers all affected services and their interactions
- [x] LLD has concrete schema, API, and component details
- [x] Security review covers auth, validation, multi-tenant isolation, and rate limiting
- [x] Milestones are independently shippable and ordered
- [x] Testing strategy covers unit, integration, and edge cases
- [x] References existing codebase patterns (ReportService, PdfExportService, send_email_with_attachment, create_notification, Celery Beat setup_periodic_tasks)

---

*Plan generated from user-provided spec, [domain map](/Users/siddhant/Documents/Dalgo/dalgo-core/docs/domain-map.md), codebase research via DDP_backend GitHub repo, and reference plan from [Metrics & KPIs v1](/Users/siddhant/Documents/Dalgo/dalgo-core/features/metrics_kpis/v1/plan.md).*

---
