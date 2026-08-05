# Tasks: Audit Logs v1

## Milestone 1: Core infrastructure

- [x] Create `models/audit_log.py` with AuditLog model
- [x] Create migration for AuditLog table
- [x] Implement `core/audit_log_service.py` (the code that writes logs)
- [x] Unit tests for service layer

## Milestone 2: Auth & user management events

- [x] Wire login event
- [x] Wire logout event
- [x] Wire password change event
- [x] Wire password reset request event
- [x] Wire email verification event
- [x] Wire user added to org event (via invitation accepted)
- [x] Wire user removed from org event
- [x] Wire user role change event
- [x] Wire invitation sent event
- [x] Wire invitation resent event
- [x] Wire invitation accepted event
- [x] Wire invitation deleted event
- [x] Wire organization created event
- [x] Wire org logo upload/update/delete events

## Milestone 3: Data infrastructure events

### Warehouse
- [x] Wire warehouse connect
- [x] Wire warehouse update
- [x] Wire warehouse delete

### Data Sources & Connections (airbyte_api.py)
- [x] Wire source create/update/delete
- [x] Wire connection create/update/delete
- [x] Wire manual sync triggered (via pipeline manual trigger)
- [x] Wire connection reset (covered by schema change - no standalone endpoint)
- [x] Wire schema change

### Pipelines (pipeline_api.py)
- [x] Wire pipeline create/update/delete
- [x] Wire schedule toggle (on/off)
- [x] Wire manual trigger

### Transformations - dbt (dbt_api.py, transform_api.py)
- [x] Wire dbt project create/delete
- [x] Wire dbt workspace delete
- [x] Wire git repo switch
- [x] Wire changes publish (commit/push)
- [x] Wire changes pull
- [x] Wire canvas node create/update/delete
- [x] Wire model finalize
- [x] Wire remote project sync
- [x] Wire sources sync
- [x] Wire target schema update
- [x] Wire dbt run triggered
- [x] Wire dbt docs generated

## Milestone 4: Analytics & reporting events

### Dashboards (dashboard_native_api.py)
- [x] Wire dashboard create
- [x] Wire dashboard update
- [x] Wire dashboard delete
- [x] Wire dashboard duplicate
- [x] Wire dashboard share (public/private toggle)
- [x] Wire set as landing page

### Charts (charts_api.py)
- [x] Wire chart create
- [x] Wire chart update
- [x] Wire chart delete (single and bulk)

### Metrics & KPIs (metric_api.py, kpi_api.py)
- [x] Wire metric create/update/delete
- [x] Wire KPI create/update/delete

### Reports & Comments (report_api.py)
- [x] Wire report/snapshot create
- [x] Wire report update
- [x] Wire report delete
- [x] Wire report share
- [x] Wire comment create

## Milestone 5: Retention

- [x] Create `purge_old_audit_logs` management command
- [x] Add `AUDIT_LOG_RETENTION_DAYS` env config (default: 365)
- [x] Support `--days` flag for custom retention period
- [x] Support `--dry-run` flag for preview mode
- [x] Add Celery periodic task (monthly on 1st at 2:00 AM)
- [x] Unit tests for retention logic

## Post-implementation fixes

- [x] Skip audit log creation when `resource_fields` is empty (avoid noisy logs from auto-save)
  - Fixed in: `dashboard_native_api.py`, `charts_api.py`, `metric_api.py`, `kpi_api.py`, `report_api.py`, `pipeline_api.py`, `airbyte_api.py`
- [x] Show proper component IDs in dashboard resource_fields (e.g., "Chart ID 123 added to tab 'Tab 1'" instead of just "Chart")
- [x] Ensure every resource's `resource_fields` is self-identifying (includes its own name/title) on every action, including delete and untouched fields on partial updates, across all resources — AUTH, Chart, Pipeline, KPI, Metric, Alert, ReportSnapshot/Comment, Warehouse/Airbyte, OrgUser/Org, dbt/Transformations, Dashboard
- [x] Verify: full backend test suite (2167 passed, 0 regressions), `black --check .`, `manage.py check`
