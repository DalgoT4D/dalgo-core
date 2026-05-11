# Report Scheduling v1 — Research Notes

**Date:** 2026-05-08
**Purpose:** Codebase analysis and architecture research to inform the implementation plan.

---

## 1. Backend Architecture (DDP_backend)

### Framework & Patterns
- **Django + Django Ninja** for REST APIs with automatic Pydantic schema validation
- **Layer architecture**: API (`api/`) -> Core/Service (`core/`, `services/`) -> Models (`models/`)
- **Auth**: JWT via `rest_framework_simplejwt` + `@has_permission(["can_verb_module"])` decorator
- **Response format**: Typed `response=` on endpoints with schema validation
- **Celery Beat**: Used for periodic tasks, registered in `setup_periodic_tasks()` in `ddpui/celeryworkers/tasks.py`

### Key Models (relevant to scheduling)

| Model | File | Purpose |
|-------|------|---------|
| `Dashboard` | `models/dashboard.py` | Dashboard entity; scheduled reports are per-dashboard |
| `ReportSnapshot` | `models/report.py` | Frozen dashboard state with data queries; the core deliverable of a scheduled run |
| `Org` | `models/org.py` | Organization entity; all schedules are org-scoped |
| `OrgUser` | `models/org_user.py` | User-org link; schedule creator and notification recipient |
| `Notification` | (notification model) | In-app notification for failures and alerts |

### Existing Report Infrastructure

**ReportService** (`ddpui/core/reports/report_service.py`):
- `ReportService.create_snapshot()` -- Creates a frozen snapshot of a dashboard with date range filtering
- Handles KPI charts, filter injection, chart freezing
- Already well-tested and reusable for automated snapshot creation
- Takes: `title`, `dashboard_id`, `orguser`, `date_column`, `period_start`, `period_end`

**PdfExportService** (`ddpui/core/reports/pdf_export_service.py`):
- `PdfExportService.generate_pdf()` -- Generates PDF from a snapshot
- Used by the existing manual share-via-email flow

**Email Infrastructure** (`ddpui/celeryworkers/report_tasks.py`):
- `send_report_email_task` -- Existing Celery task for sending report emails
- `send_email_with_attachment()` -- Utility for sending emails with PDF attachments via AWS SES
- Pattern to follow: dispatches as async Celery task with retry logic

**Notification Infrastructure**:
- `create_notification()` -- Creates in-app notification with optional email delivery
- Supports `urgent=True` flag for critical notifications
- Already used for email delivery failures in existing report_tasks.py

### Celery Beat Setup
- Periodic tasks registered via `setup_periodic_tasks()` in `ddpui/celeryworkers/tasks.py`
- Uses `crontab()` scheduling (e.g., `crontab(minute=0)` for hourly)
- Adding a new hourly task (`check_scheduled_reports`) follows existing patterns

### API Routing
- Routers registered in `routes.py`: `src_api.add_router("/api/{module}/", {module}_router)`
- Dashboards at `/api/dashboards/`
- New schedule endpoints will nest under `/api/dashboards/{id}/schedule/`

### Permission Slugs Convention
- Existing: `can_view_dashboards`, `can_create_dashboards`, `can_edit_dashboards`, `can_delete_dashboards`
- New: `can_manage_report_schedules` (single permission for schedule CRUD)
- Read access: reuses `can_view_dashboards`

---

## 2. Frontend Architecture (webapp_v2)

### Framework & Patterns
- **Next.js 15 + React 19** with App Router
- **Shadcn UI** component library with teal brand theme
- **SWR** for data fetching and caching
- **API layer**: `apiPost()`, `apiGet()`, `apiPut()`, `apiDelete()` utilities

### Key UI Patterns (relevant to scheduling)

**Share-via-email dialog** (`components/reports/share-via-email-dialog.tsx`):
- Email input with comma separation
- Email validation (regex + backend validation)
- `MAX_RECIPIENTS` constant for limit enforcement
- Pattern to follow for recipient management UI

**Create-snapshot dialog** (`components/reports/create-snapshot-dialog.tsx`):
- Date column discovery (lists datetime columns from warehouse tables)
- Date range picker
- Pattern to follow for date column configuration in schedule setup

**Dashboard page** (`app/dashboards/[id]/page.tsx`):
- Dashboard settings and actions area
- Where schedule status card and config entry point will live

### Hooks Convention
- SWR-based hooks for GET requests: `useSWR(url, fetcher)`
- Async functions for mutations: `apiPost()`, `apiPut()`, `apiDelete()`
- Pattern: `hooks/api/use{Resource}.ts`

---

## 3. Domain Map Analysis

From `docs/domain-map.md`, traversing from Dashboard (the entity being scheduled):

### Direct Dependencies (1 hop)
- **ReportSnapshot** (snapshot-of): Scheduled runs create snapshots -- **in scope**
- **Live public share** (embed): Not affected by scheduling
- **Chart** (via snapshot): Chart configs frozen in snapshot -- auto-inherited from existing freeze logic
- **KPI** (via snapshot): KPI data frozen in snapshot -- auto-inherited (Metrics & KPIs v1 Milestone 4 complete)

### Indirect Dependencies (2 hops)
- **Notification** (trigger from snapshot): Failure notifications -- **in scope**
- **OrgUser** (terminal from notification): Recipients -- **in scope**
- **Alert** (via KPI): Not affected by scheduling
- **Pipeline** (0 hops): Open question -- should reports wait for pipeline completion?

### Surfaces Needing Confirmation
1. **Pipeline dependency**: Should scheduled reports defer if latest pipeline run hasn't completed?
2. **Public share**: Are auto-created snapshots also auto-shared publicly? (Recommendation: private by default)
3. **Notification channel**: Use existing `Notification` model or create new channel?

---

## 4. Existing Patterns (from Metrics & KPIs v1)

Reference: `features/metrics_kpis/v1/plan.md` and `features/metrics_kpis/v1/tasks.md`

### Migration Pattern
- Migrations numbered sequentially (e.g., `0158`, `0159`...)
- Include permission slug creation in migration
- Include seed data for new permission assignments to existing roles

### Service Layer Pattern
- `@dataclass` for input/output data structures
- Service classes with static methods or module-level functions
- Error handling: raise Django Ninja `HttpError` with appropriate status codes
- Validation: at service layer, not in API layer

### Testing Pattern
- Test files mirror source structure: `tests/services/test_{service_name}.py`
- Factory Boy for model fixtures
- Mock external services (email, PDF generation) in unit tests

---

## 5. Email Infrastructure

### AWS SES
- Already configured for the platform (`SES_SENDER_EMAIL`)
- Sending limits: typical SES sandbox ~200/day, production ~50K/day
- Estimated load: ~20 orgs x ~20 recipients = ~400 emails per hourly batch (well within limits)

### Email Templates
- Existing report email templates in `report_tasks.py`
- Pattern: `render_report_email()` returns `(plain_text, html_body)`
- Scheduled reports need a new template distinguishing them from one-off shares

### Unsubscribe Handling
- Spec says: "Check unsubscribe rates first" before considering separate sender address
- v1 uses existing `SES_SENDER_EMAIL` (e.g., notifications@dalgo.org)
- Decision on separate `reports@dalgo.org` deferred to v2

---

## 6. Key Files for Implementation

| File | Purpose |
|------|---------|
| `DDP_backend/ddpui/celeryworkers/tasks.py` | Register hourly `check_scheduled_reports` task |
| `DDP_backend/ddpui/core/reports/report_service.py` | Reuse `ReportService.create_snapshot()` |
| `DDP_backend/ddpui/celeryworkers/report_tasks.py` | Pattern for `send_report_email_task` |
| `DDP_backend/ddpui/routes.py` | Register new schedule API router |
| `webapp_v2/components/reports/share-via-email-dialog.tsx` | UI pattern for recipient management |
| `webapp_v2/components/reports/create-snapshot-dialog.tsx` | Pattern for date column picker |

---

*Research compiled from codebase exploration via DDP_backend GitHub repo, domain-map.md, existing features/metrics_kpis/v1 artifacts, and existing report infrastructure analysis.*
