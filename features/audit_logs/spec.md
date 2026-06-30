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

- **Org Admin (Account Manager role)** — needs to answer "who changed this" when investigating an incident or unexpected change within their org.
- **Dalgo platform/support team** — needs to investigate cross-org issues and answer customer questions about activity history.
- **NGO program leads** — indirect beneficiaries: trust that the platform is accountable, useful when reporting to donors about data governance.

Who exactly is _permitted_ to view logs is an open product question — see §7. This spec assumes some authorized role can query the data; it does not assume "everyone."

## 4. User flows

This is backend-only — there's no UI to walk through yet. The flows below describe how an audit entry comes into existence and how it gets queried.

### 4.1 A user performs any tracked action

1. A user performs an action via the Dalgo UI (e.g. deletes a dashboard).
2. The corresponding API request succeeds.
3. An audit log entry is created automatically, capturing the actor, the resource, what changed, and the timestamp.
4. The user sees no difference in the product — logging is invisible in v1.

### 4.2 An authorized person queries audit history

1. An authorized user calls the internal audit query capability.
2. They filter by organization, actor, resource type, action, or date range.
3. They get back a list of matching audit entries to investigate an incident or answer a "who did X" question.

## 5. Functional requirements

### 5.1 Events captured

Every significant create / update / delete / lifecycle action across these areas is logged:

- **Login & Authentication** — login, logout, password change, password reset request, email verification
- **User & Organization Management** — user added to org, user removed from org, user role changed, invitation sent / resent / accepted / deleted, organization created
- **Settings & Branding** — org logo uploaded, updated, deleted
- **Warehouse** — connected, updated, removed
- **Data Sources & Connections** — source created / updated / deleted, connection created / updated / deleted, manual sync triggered, connection reset, schema change detected and applied
- **Pipelines** — created / updated / deleted, schedule turned on or off, manually triggered
- **Transformations (dbt)** — dbt workspace setup (project created/deleted, workspace deleted); git repo operations (repo switched, changes published, changes pulled); visual model builder/canvas operations (lock/unlock/refresh, node created/updated/deleted, chain finalized into a model, remote project synced); sources & schema (sources synced, target schema updated); running dbt (run triggered, docs generated); data quality (Elementary report fetched/refreshed, tracking tables created, profile created, report deployment created) — full enumerated list in Appendix A
- **Dashboards** — created / updated / deleted, published / unpublished, shared publicly (share revoked is logged as a regular update), locked / unlocked for editing, set as org default, filter created / updated / deleted
- **Charts** — created / updated / deleted
- **Metrics & KPIs** — created / updated / deleted
- **Reports & Comments** — report created / updated / deleted, shared publicly (share revoked is logged as a regular update), comment added / deleted

### 5.2 What's captured per event

Each audit entry records: who performed it (actor email), which organization, what kind of resource and which specific one, what action was taken, what changed (old value → new value, where applicable), whether it succeeded or failed, and when it happened.

### 5.3 Data isolation

Every audit entry belongs to exactly one organization. Whether Dalgo's own platform team can see across organizations is a permissions question (§7), not a data-isolation question — the data itself is always org-scoped.

### 5.4 Immutability

Audit log entries are never edited or deleted through normal use — there is no edit or delete API for them. Whether and how old entries are eventually removed is covered by the retention policy open question in §7.

### 5.5 Secrets are never logged

Passwords, API keys, git access tokens, warehouse credentials, and public share tokens are never captured in the "what changed" diff, even when they're part of the resource being modified.

## 6. Dependencies

- **None blocking.** This is foundational infrastructure rather than a feature that depends on another. It does, however, touch nearly every existing API endpoint to add a logging call — see `v1/plan.md`'s Blast Radius analysis for the full list.
- **Enables:** future versions can layer in a browsing UI, retention configuration per org, and export to external tools.

## 7. Open questions — for team / engineering review

- **Who should be able to view audit logs?** Only Account Managers and above, or all org users, or also Dalgo's platform team across organizations? This determines the permission gating on the query capability.
- **What should the retention policy be?** Whether removal should be automatic (a scheduled purge) or manual, and if automatic, what period — options discussed: 6 months, 1 year, indefinitely. Longer retention helps long-term investigations but increases storage cost.

## 8. Success indicators

- **Coverage** — percentage of the events listed in §5.1 that have a working audit log call wired in.
- **Time-to-answer** — support and org admins can answer "who did X" questions directly from the log, without escalating to engineering for a database query.
- **Zero secret leakage** — no password, token, or credential ever appears in an audit log's `changes` field, verified through code review and tests.

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

- Canvas is locked for editing
- Canvas lock is refreshed
- Canvas is unlocked
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

**Data Quality (Elementary)**

- An Elementary report is fetched or refreshed
- Elementary tracking tables are created
- An Elementary profile is created
- An Elementary report deployment is created
