# Spec: Audit Logs

## 1. Problem & opportunity

Dalgo is a multi-tenant platform where several people within an org — and Dalgo's own platform team — create, modify, and delete data sources, pipelines, transformations, dashboards, charts, metrics, KPIs, reports, and user/org settings. Today none of these actions are recorded anywhere. When something breaks or changes unexpectedly — a dashboard disappears, a pipeline's schedule changes, a user's role gets escalated — there is no way to answer "who did this, what changed, and when."

This spec covers a backend-only, org-scoped audit logging system that records every significant user-initiated action across the platform.

## 2. Vocabulary & scope boundary

- **Audit Log entry** — one immutable record of a single action: who, what, when, what changed.
- **Actor** — the user (OrgUser) who performed the action.
- **Resource** — the entity the action was performed on (e.g. a Dashboard, a Pipeline, a User).
- **Action** — the type of operation (create, update, delete, login, logout, share, execute).

## 3. Users & primary use cases

- **Org Admin (Account Manager role)** — needs to answer "who changed this" when investigating an incident or unexpected change within their org. This is the long-term target user; v1 builds no way for them to access this data yet.
- **Dalgo platform/support team** — needs to investigate cross-org issues and answer customer questions about activity history. In v1, this happens via direct SQL queries against the database, not a product feature.
- **NGO program leads** — indirect beneficiaries: trust that the platform is accountable, useful when reporting to donors about data governance.

**v1 builds the capture infrastructure only — no query API, for anyone, including Dalgo's own team.** Reading the data means a direct database query. A query API, and eventually a UI for org-level access, is deferred to a later version (v2).

## 4. User flows

This is backend-only — there's no UI or query API yet (§3). The flow below describes how an audit entry comes into existence.

### 4.1 A user performs any tracked action

1. A user performs an action via the Dalgo UI (e.g. deletes a dashboard).
2. The corresponding API request succeeds.
3. An audit log entry is created automatically, capturing the actor, the resource, what changed, and the timestamp.
4. The user sees no difference in the product — logging is invisible in v1.

## 5. Functional requirements

### 5.1 Events captured

Every significant create / update / delete / lifecycle action across these areas is logged:

- **Login & Authentication** — login, logout, password change, password reset request, email verification
- **User & Organization Management** — user added to org, user removed from org, user role changed, invitation sent / resent / accepted / deleted, organization created
- **Settings & Branding** — org logo uploaded, updated, deleted; Discord notification toggle enabled or disabled
- **Warehouse** — connected, updated, removed
- **Data Sources & Connections** — source created / updated / deleted, connection created / updated / deleted, manual sync triggered, connection reset, schema change detected and applied
- **Pipelines** — created / updated / deleted, schedule turned on or off, manually triggered
- **Transformations (dbt)** — dbt workspace setup (project created/deleted, workspace deleted); git repo operations (repo switched, changes published, changes pulled); visual model builder/canvas operations (node created/updated/deleted, chain finalized into a model, remote project synced); sources & schema (sources synced, target schema updated); running dbt (run triggered, docs generated) — full enumerated list in Appendix A
- **Dashboards** — created / updated / deleted, published / unpublished, shared publicly (share revoked is logged as a regular update), set as org default, filter created / updated / deleted
- **Charts** — created / updated / deleted
- **Metrics & KPIs** — created / updated / deleted
- **Reports & Comments** — report created / updated / deleted, shared publicly (share revoked is logged as a regular update), comment added / deleted

### 5.2 What's captured per event

Each audit entry records: who performed it (actor email), which organization, what kind of resource and which specific one, what action was taken, what changed (old value → new value, where applicable), and when it happened. Only successful actions are logged, so there is no separate success/failure status on the entry itself. Only write actions are captured (create, update, delete, execute, share, login, logout) — read/view operations such as viewing a dashboard or listing resources are never logged.

### 5.3 Data isolation

Every audit entry belongs to exactly one organization. No query API exists yet (§3), but the data is still org-scoped at the model level for when one is built.

### 5.4 Immutability

Audit log entries are never edited or deleted through normal use — there is no edit or delete API for them. Entries older than 1 year are purged automatically via the `purge_old_audit_logs` management command.

### 5.5 Secrets are never logged

Passwords, API keys, git access tokens, warehouse credentials, and public share tokens are never captured in the "what changed" diff, even when they're part of the resource being modified.

## 6. Dependencies

- **None blocking.** This is foundational infrastructure rather than a feature that depends on another. It does, however, touch nearly every existing API endpoint to add a logging call — see `v1/plan.md`'s Blast Radius analysis for the full list.
- **Enables:** future versions can layer in a query API, a browsing UI on top of it, retention configuration per org, and export to external tools.

## 7. Success indicators

- **Coverage** — percentage of the events listed in §5.1 that have a working audit log call wired in.
- **Time-to-answer** — Dalgo's team can answer "who did X" questions via a direct database query, without needing to add new logging or reconstruct events from other sources.
- **Zero secret leakage** — no password, token, or credential ever appears in an audit log's `field_changes` field, verified through code review and tests.

---

## Appendix A — Full dbt / Transformations event list

**dbt Workspace Setup**

- A dbt project is created
- A dbt project is deleted
- The dbt workspace is deleted

**Git Repository**

- The git repo is switched (from Dalgo-managed to the user's own repo)
- Changes are published (committed and pushed to git)
- Latest changes are pulled from git

**Visual Model Builder (Canvas)**

- A source/model node is created
- An operation node is created (e.g. a filter or join step)
- An operation node is updated
- An operation node is finalized into a model
- A model/node is deleted
- A remote dbt project is synced into the canvas

**Sources & Schema**

- Sources are synced from the warehouse
- The target schema is updated

**Running dbt**

- A dbt run is triggered
- dbt docs are generated
