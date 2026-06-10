# Alerts — v1

**Scoped from**: ../spec.md
**Version**: v1
**Status**: Draft

## Scope for this iteration

A schedule-driven alerting system covering three alert shapes, with Email + Slack (webhook) delivery, a Test Alert preview, role-based gating, external email recipients, and a `/alerts` listing surface with two tabs (All alerts, Triggered) and a shared History modal. Notifications use Mustache-style templates with a live preview.

Alert conditions always resolve to a single numeric value (because every alert type runs an aggregation). Empty / no-rows query results are treated as "condition not satisfied" — the alert does not fire.

### What's included

- **Three alert types**, each with a distinct entry point:
  - **Metric-threshold alert** — created from the Metrics page (Metric pre-selected) with a numeric condition.
  - **KPI RAG alert** — created from a KPI card / KPI detail (KPI pre-selected) with an RAG-level trigger.
  - **Standalone alert** — created from the Alerts page; user picks a dataset, picks a column, defines an aggregation, optional filters, and a numeric condition. Same dataset / column picker as the Metrics page.
- **Schedule-driven evaluation.** Each alert runs on its own user-set schedule using frequency presets: hourly / daily / weekly / monthly. Default for all types is **daily**. Default time-of-day is **09:00 in the author's browser timezone**, with a toggle to set the time in UTC.
- **Delivery channels.** Email (always available) and Slack (via webhook URL). Multi-select per alert. **At least one channel is required**; Email is pre-checked by default at create time.
- **Recipients.** Any mix of Dalgo users (searched from the org user list) and free-form external email addresses.
- **Slack via per-alert webhook URL.** The alert author pastes a Slack incoming-webhook URL when picking Slack as a channel. A **"Send test message"** button next to the field POSTs a test payload to the webhook so the author can confirm it works before saving. No org-level Slack workspace setup, no OAuth, no channel picker.
- **Test Alert preview** from the authoring form — dry-run shows would-fire status (or "would not fire" when the result is empty), the numeric result, rendered email + Slack messages, and the generated SQL. Never sends a notification.
- **Message templates.** Mustache-style `{{ tokens }}`. All three alert types share **one default template** with the full token set; tokens that don't apply to a given type render blank. Authors customize per-alert. Live preview substitutes from the most recent test run.
- **`/alerts` listing with two tabs and a shared History modal.** Both tabs use the same table row format. Triggered/Fired surfaces what fired so Dalgo users can audit notifications that went to recipients outside Dalgo. The History modal (per-alert) is reachable from the 3-dot menu on every row in both tabs.
- **Role-based create / edit / delete gating** wired against the current Dalgo role structure.

### What's deferred to later versions

- **Notification cooldown / re-alert policy** — the schedule itself controls cadence in v1.
- **Pipeline-completion-triggered evaluation** and source-table lineage inference — original spec's evaluation model. Replaced in v1 by user-set schedules.
- **Provenance — "underlying data last refreshed X ago"** in the History modal and notifications (Goalkeep's ask). Deferred until source-table lineage is available.
- **KPI-card alert indicator** (§5.10 original) — visual marker on KPI cards showing alerts are linked. Deferred.
- **Lifting the `count_distinct` constraint** (§5.9 original) — v1 keeps the prototype's safety rail. Revisit once metric-composition semantics on COUNT DISTINCT are settled.
- **Org-level Slack workspace OAuth, channel picker, app-membership management** — v1 ships the simpler webhook path; richer Slack integration is a later version.
- **Per-type default templates** — v1 ships a single shared template. If authors consistently customize the same way per type, revisit.
- WhatsApp delivery; generic webhook delivery to non-Slack endpoints.
- Acknowledge / mute / snooze controls.
- User-group-based recipient routing (covered by the Access Controls spec).
- AI-chat-over-alerts; anomaly / ML-based alerts; Elementary data-quality alerts; SLA / escalation chains.

## User stories / user flows

### Story 1 — Create a Metric-threshold alert from the Metrics page

**As a** data / analytics team member, **I want** to attach a threshold alert to a Metric I already use, **so that** I get notified when the Metric crosses a value I care about.

**Acceptance criteria:**
- [ ] From a Metric in the Metrics page, the user can click "Create Alert."
- [ ] The alert form opens with the Metric pre-selected and locked.
- [ ] The user defines a numeric condition: less than / greater than / equal to a value.
- [ ] The user sets a schedule from frequency presets: hourly, daily, weekly, monthly. Default: daily.
- [ ] A time-of-day field defaults to 09:00 in the author's browser timezone, with a toggle to set the time in UTC instead.
- [ ] The user picks recipients — any mix of Dalgo users (searched from the org user list) and free-form external email addresses.
- [ ] The user picks delivery channels: Email (pre-checked) and/or Slack. At least one channel must remain checked to save. For Slack, the user pastes a webhook URL.
- [ ] Next to the Slack URL field, a "Send test message" button POSTs a test payload to the webhook so the author can confirm it works before saving.
- [ ] The user can edit the shared default message template; the editor supports `{{ tokens }}` and a live preview.
- [ ] The user can click "Test Alert" to dry-run before saving (see Story 4).
- [ ] On save, the alert is active and runs on its schedule.

### Story 2 — Create a KPI RAG alert from a KPI

**As a** program lead, **I want** to be notified when one of my KPIs goes into a specific RAG state, **so that** I can react to drift without checking the dashboard.

**Acceptance criteria:**
- [ ] From a KPI card or KPI detail, the user can click "Create Alert."
- [ ] The alert form opens with the KPI pre-selected and locked.
- [ ] The user picks the RAG trigger: fires when RAG = red; or = red or amber; or on any state change.
- [ ] Schedule, time-of-day, recipients, channels (with the Slack "Send test message" button), template, and Test Alert behave the same as Story 1.
- [ ] On save, the alert is active and runs on its schedule.

### Story 3 — Create a Standalone alert from the Alerts page

**As a** data / analytics team member, **I want** to define an ad-hoc check that isn't tied to a Metric, **so that** I can monitor data quality, attendance gaps, missing rows, etc.

**Acceptance criteria:**
- [ ] From the Alerts page, the user can click "Create Standalone Alert."
- [ ] The user picks a dataset using the same dataset picker the Metrics page uses.
- [ ] The user picks a column to evaluate the condition against.
- [ ] The user defines an aggregation over the column (the same aggregation primitives available in Metric creation).
- [ ] The user optionally adds filters that scope which rows are aggregated.
- [ ] The user sets a numeric condition (less than / greater than / equal to a value) — same condition input as Metric-threshold.
- [ ] Schedule, time-of-day, recipients, channels (with the Slack "Send test message" button), template, and Test Alert behave the same as Story 1.
- [ ] On save, the alert is active and runs on its schedule.

### Story 4 — Test an alert before saving

**As an** alert author, **I want** to dry-run my alert before saving it, **so that** I know it does what I expect.

**Acceptance criteria:**
- [ ] From the authoring form (any of the three types), the user can click "Test Alert" at any time.
- [ ] The dry-run shows would-fire status (yes / no), the numeric result returned by the query, the rendered email message, the rendered Slack message (if Slack is enabled), and the generated SQL.
- [ ] Test Alert never sends a notification.
- [ ] If the query returns no rows, the preview shows "Would not fire" (no rows = condition not satisfied).
- [ ] The live preview of the message template updates from the most recent test run.

### Story 5 — Browse alerts in `/alerts` (All alerts and Triggered tabs)

**As an** alert owner or operator, **I want** a single place to see every alert and what's currently firing, **so that** I can audit configurations and recent activity in one view — including activity sent to recipients outside Dalgo.

**Acceptance criteria:**
- [ ] `/alerts` has two tabs: **All alerts** and **Triggered** (also called Fired).
- [ ] Both tabs use the same table-row format. Each row shows:
  - [ ] **Alert name**, with linked Metric or KPI name underneath (for Metric / KPI alerts) or the dataset name (for Standalone alerts).
  - [ ] **Source** — link out to the source entity: KPI annotation for KPI alerts, Metric edit for Metric-threshold alerts, dataset name (no link) for Standalone alerts.
  - [ ] **Alert condition** in plain language (e.g. `RAG = red`, `value < 50`, `count(*) > 100`).
  - [ ] **Enabled / disabled toggle** to deactivate or re-activate the alert in place.
  - [ ] **Schedule frequency** (hourly / daily / weekly / monthly).
  - [ ] **Fire streak** — consecutive recent evaluations that fired.
  - [ ] **Last fire timestamp**, shown relative (e.g. "2h ago").
  - [ ] **3-dot actions menu** with: Edit, Delete, View History (Story 6).
- [ ] Filters and sorts on the table: alert type (Metric / KPI / Standalone), delivery channel, enabled state, schedule frequency, last fire time.
- [ ] **All alerts tab** shows every alert in the org (active and inactive).
- [ ] **Triggered tab** shows alerts whose most recent evaluation fired.
- [ ] Toggling enabled / disabled from the row updates immediately and does not delete the alert.
- [ ] Deleting a Metric or KPI is blocked while any alert references it (matches prototype behaviour).

### Story 6 — View an alert's fire history (History modal)

**As an** alert owner, **I want** to inspect every past fire of one alert, **so that** I can audit what was sent, to whom, and when — including notifications to external recipients I can't see in any inbox.

**Acceptance criteria:**
- [ ] From the 3-dot menu on any row in either tab, the user can open **View History**.
- [ ] The History modal lists every past fire of the alert (modeled on the pipeline-history page).
- [ ] Each history entry row shows: time fired, current value at that time, the alert condition that was satisfied, delivery channel(s) used, recipient count summary.
- [ ] Each history entry expands to reveal:
  - [ ] The full recipient list (Dalgo users + external emails) per channel.
  - [ ] The rendered message that was sent per channel (email body, Slack post).
- [ ] The modal is reachable identically from the All alerts tab and the Triggered tab.
- [ ] History is **unlimited** — every past fire is retained indefinitely. The modal paginates older entries.

### Story 7 — Receive a fired alert (Email)

**As a** recipient, **I want** the email notification to tell me what fired, what the current value is, and where to look, **so that** I can act without hunting for context.

**Acceptance criteria:**
- [ ] When an alert fires on its schedule, every recipient on the email list receives one email.
- [ ] External recipients (non-Dalgo users) receive the email but no portal login is required.
- [ ] The email renders the user's template with all tokens substituted.
- [ ] Available tokens cover at minimum: `{{ alert_name }}`, `{{ metric_name }}`, `{{ kpi_name }}`, `{{ current_value }}`, `{{ target_value }}`, `{{ rag_state }}`, `{{ achievement_pct }}`, `{{ failing_rows_count }}`, `{{ dashboard_link }}`. Tokens that don't apply to the alert's type render blank.

### Story 8 — Receive a fired alert (Slack)

**As a** team that lives in a Slack channel, **I want** alerts to post into our channel via webhook, **so that** the team sees and triages them together without per-recipient DMs.

**Acceptance criteria:**
- [ ] When an alert with Slack delivery fires, the rendered message is POSTed to the alert's configured webhook URL.
- [ ] The channel the post lands in is whatever channel the webhook was created for in Slack (Dalgo does not pick the channel).
- [ ] All recipients on the alert see the same post in the shared channel (no per-user DMs in v1).
- [ ] Slack rendering substitutes the same tokens as email.
- [ ] If the webhook POST fails, the failure is recorded in the alert's history entry for that fire.

### Story 9 — Role-gated alert management

**As an** org admin, **I want** create / edit / delete to be limited to roles that should have it, **so that** alerts aren't created or removed by people without the right responsibility.

**Acceptance criteria:**
- [ ] Create, edit, and delete actions are gated by role against the current Dalgo role structure.
- [ ] Users without the create role do not see "Create Alert" entry points.
- [ ] Users without the edit role see read-only alert detail and a disabled enabled-toggle.
- [ ] Users without the delete role do not see the delete action in the 3-dot menu.
- [ ] All users with login can view both tabs and open the History modal (subject to org membership).

## Dependencies

- **Requires:** the reusable Metric and KPI primitives from `features/metrics_kpis/v1/spec.md`. Metric and KPI alerts cannot exist without them. The Standalone alert's dataset / column / aggregation picker reuses the same primitive the Metrics page uses for Metric creation.
- **Requires:** the Access Controls roles already scaffolded in the prototype (for Story 9 gating). Group-based recipient routing is *not* required in v1.
- **Enables:** future versions can layer in pipeline-completion-triggered evaluation, cooldown / re-alert policy, provenance ("last refresh"), KPI-card alert indicators, lifting the `count_distinct` constraint, org-level Slack OAuth with a channel picker, per-type default templates, and additional delivery channels (WhatsApp, generic webhooks).
