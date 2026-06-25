# Alerts — v1

**Scoped from**: ../spec.md
**Version**: v1
**Status**: Draft
**Design**: see [design.md](./design.md) for Figma frame mappings and outstanding design feedback

## Scope for this iteration

A schedule-driven alerting system covering three alert shapes, with Email + Slack (webhook) delivery, a Test Alert preview, role-based gating, external email recipients, and a `/alerts` listing surface with two tabs (All alerts, Triggered) and a shared History modal. Notifications use Mustache-style templates with a live preview.

Alert conditions always resolve to a single numeric value (because every alert type runs an aggregation). Empty / no-rows query results are treated as "condition not satisfied" — the alert does not fire.

### What's included

- **Three alert types**, each with a distinct entry point:
  - **Metric-threshold alert** — created from the Metrics page (Metric pre-selected) with a numeric condition.
  - **KPI RAG alert** — created from a KPI card / KPI detail (KPI pre-selected) with an RAG-level trigger.
  - **Standalone alert** — created from the Alerts page; user picks a dataset, picks a column, defines an aggregation, optional filters, and a numeric condition. Same dataset / column picker as the Metrics page.
- **Schedule-driven evaluation.** Each alert runs on its own user-set schedule using frequency presets: daily / weekly / monthly. Default for all types is **daily**. Default time-of-day is **09:00 in the author's browser timezone**. All times are entered and displayed in the author's local timezone; the backend converts to UTC for storage and back to the viewer's local timezone for display.
- **Delivery channels.** Email (always available) and Slack (via webhook URL). Multi-select per alert. **At least one channel is required**; Email is pre-checked by default at create time.
- **Recipients.** Any mix of Dalgo users (searched from the org user list) and free-form external email addresses.
- **Slack via per-alert webhook URL.** The alert author pastes a Slack incoming-webhook URL when picking Slack as a channel. A **"Send test message"** button next to the field POSTs a test payload to the webhook so the author can confirm it works before saving. No org-level Slack workspace setup, no OAuth, no channel picker.
- **Test Alert preview** from the authoring form — dry-run shows would-fire status (or "would not fire" when the result is empty), the numeric result, rendered email + Slack messages, and the generated SQL. Never sends a notification.
- **Message templates.** Mustache-style `{{ tokens }}`. Each of the three alert types has its **own default template and its own token set** — tokens are scoped to the alert type so authors only see tokens that apply. Authors customize per-alert. Live preview substitutes from the most recent test run.
- **`/alerts` listing with two tabs and a shared Alert log modal.** Both tabs use the same table row format. The Firing tab surfaces what fired so Dalgo users can audit notifications that went to recipients outside Dalgo. The Alert log modal (per-alert) is reachable from the 3-dot menu on every row in both tabs.
- **Role-based create / edit / delete gating** wired against the current Dalgo role structure.

### What's deferred to later versions

- **Notification cooldown / re-alert policy** — the schedule itself controls cadence in v1.
- **Pipeline-completion-triggered evaluation** and source-table lineage inference — original spec's evaluation model. Replaced in v1 by user-set schedules.
- **Provenance — "underlying data last refreshed X ago"** in the History modal and notifications (Goalkeep's ask). Deferred until source-table lineage is available.
- **KPI-card alert indicator** (§5.10 original) — visual marker on KPI cards showing alerts are linked. Deferred.
- **Lifting the `count_distinct` constraint** (§5.9 original) — v1 keeps the prototype's safety rail. Revisit once metric-composition semantics on COUNT DISTINCT are settled.
- **Org-level Slack workspace OAuth, channel picker, app-membership management** — v1 ships the simpler webhook path; richer Slack integration is a later version.
- WhatsApp delivery; generic webhook delivery to non-Slack endpoints.
- Acknowledge / mute / snooze controls.
- User-group-based recipient routing (covered by the Access Controls spec).
- AI-chat-over-alerts; anomaly / ML-based alerts; Elementary data-quality alerts; SLA / escalation chains.

## Authoring wizard structure

All three alert types (KPI, Metric, Standalone) use a shared **3-step modal wizard** for create and edit. The modal opens over whatever page the user clicked "Create Alert" from — KPI detail, Metrics page, or `/alerts` listing. Edit reuses the same modal, prefilled.

### Step 1 — Define
Type-specific fields:
- **Name** (all types)
- **KPI** locked to the source KPI (KPI alerts only)
- **Metric** locked to the source Metric (Metric alerts only)
- **Dataset / column / aggregation / filters** picker (Standalone only — reuses the Metric creation primitive, supports Simple + Calculated)
- **Alert condition**:
  - KPI: multi-select of {Red, Amber, Green} (1–2 states)
  - Metric / Standalone: comparison (less than / greater than / equal to) + numeric target value
- **Schedule** — fields depend on the frequency preset:
  - **Daily**: time-of-day only.
  - **Weekly**: day-of-week + time-of-day.
  - **Monthly**: day-of-month (1–28, to avoid month-end edge cases) + time-of-day.
  - **Time-of-day** defaults to `09:00`. All times are entered and shown in the **author's browser timezone**. The backend converts the scheduled time to UTC for storage and back to the viewer's local timezone when displayed elsewhere (history, listing, notifications).

Step 1 CTAs: `Cancel`, `Next` (advances to Step 2 only if all required fields are valid).

### Step 2 — Notify
- **Delivery channels** (multi-select, at least one required, Email pre-checked): Email, Slack
- **Email recipients** picker — a single combobox supporting both Dalgo users and external email addresses:
  - As the user types, **Dalgo users in the org appear first** in the suggestions (matched by name or email).
  - If the input is a valid email format and no Dalgo user matches, an inline option appears: *"Add `<typed address>` as an external recipient."*
  - Selected recipients are shown as chips, **visually distinguished** so authors can tell at a glance which are Dalgo users and which are external emails (e.g. Dalgo users get an avatar; external emails get an envelope icon).
  - Removing a chip removes the recipient.
- **Slack webhook URL** field (only when Slack is checked) + **"Send test message"** button next to it. The button POSTs a static dummy payload — *"This is a test message from Dalgo platform"* — to the URL and shows inline success/failure based on the HTTP response. No query is run, no tokens are substituted; the test purely validates that the webhook URL is reachable. This is distinct from the Step 2 → Step 3 `Test` action, which runs the full alert dry-run.
- **Message template** editor (Mustache `{{ tokens }}`, type-specific token set) with live preview

Step 2 CTAs: `Back`, `Test` (advances to Step 3 and runs the dry-run evaluation).

### Step 3 — Test
- **Would-fire banner** — "Alert will fire for current data" or "Alert will not fire for current data"
- **Current value** and the alert condition that was evaluated against it
- **Rendered message preview** (Email; Slack also if enabled)
- **View generated SQL** (collapsible)
- "Would not fire" is shown when the query returns no rows.

Step 3 CTAs: `Back`, `Create alert` (or `Save changes` in edit mode).

### Notes
- `Test` can be re-run from Step 3 by going back to Step 1 / Step 2, editing fields, then advancing again. Test never sends a real notification.
- Validation is per-step: invalid fields block `Next` / `Test` / `Create alert`. Errors are inline next to the field.
- Edit reuses the same modal, prefilled, with the final CTA labeled `Save changes` instead of `Create alert`.

## User stories / user flows

### Story 1 — Create a Metric-threshold alert from the Metrics page

**As a** data / analytics team member, **I want** to attach a threshold alert to a Metric I already use, **so that** I get notified when the Metric crosses a value I care about.

**Acceptance criteria:**
- [ ] From a Metric in the Metrics page, the user can click "Create Alert."
- [ ] The alert form opens with the Metric pre-selected and locked.
- [ ] The user defines a numeric condition: less than / greater than / equal to a value.
- [ ] The user sets a schedule from frequency presets: daily, weekly, monthly. Default: daily.
- [ ] A time-of-day field defaults to 09:00 in the author's browser timezone. Times are always entered and displayed in the viewer's local timezone — the backend stores UTC and translates on read.
- [ ] Frequency-specific field rules apply (no day-of-week on Daily, day-of-week on Weekly, day-of-month on Monthly) — see Authoring wizard structure → Step 1 — Define.
- [ ] The user picks recipients — any mix of Dalgo users (searched from the org user list) and free-form external email addresses.
- [ ] The user picks delivery channels: Email (pre-checked) and/or Slack. At least one channel must remain checked to save. For Slack, the user pastes a webhook URL.
- [ ] Next to the Slack URL field, a "Send test message" button POSTs a test payload to the webhook so the author can confirm it works before saving.
- [ ] The user can edit the shared default message template; the editor supports `{{ tokens }}` and a live preview.
- [ ] The user can click "Test Alert" to dry-run before saving (see Story 4).
- [ ] On save, the alert is active and runs on its schedule.

### Story 2 — Create a KPI RAG alert from a KPI

**As a** program lead, **I want** to be notified when one of my KPIs lands in a RAG state I care about, **so that** I can react without checking the dashboard.

**Acceptance criteria:**
- [ ] From a KPI card or KPI detail, the user can click "Create Alert."
- [ ] The alert form opens with the KPI pre-selected and locked.
- [ ] The KPI's existing RAG bands are shown read-only for context (e.g. "Red: current value exceeds X% of target. Amber: exceeds Y%. Green: at or below Z%."). The bands themselves are configured on the KPI and cannot be edited here.
- [ ] The user picks which RAG state(s) should fire the alert by multi-selecting from {Red, Amber, Green}.
- [ ] At least 1 state must be selected. At most 2 states may be selected (selecting all 3 would fire on every evaluation).
- [ ] On each scheduled evaluation, the alert fires if the KPI's current RAG state is in the selected set. v1 does not track state transitions — the alert only checks the current state at evaluation time.
- [ ] Schedule, time-of-day, recipients, channels (with the Slack "Send test message" button), template, and Test Alert behave the same as Story 1.
- [ ] On save, the alert is active and runs on its schedule.

### Story 3 — Create a Standalone alert from the Alerts page

**As a** data / analytics team member, **I want** to define an ad-hoc check that isn't tied to a Metric, **so that** I can monitor data quality, attendance gaps, missing rows, etc.

**Acceptance criteria:**
- [ ] From the Alerts page, the user can click "Create Alert."
- [ ] The dataset / column / aggregation picker is the **same primitive used by Metric creation** — Standalone alerts reuse the Metric creation form wholesale and layer alert-specific fields (condition, schedule, recipients, channels, template) on top.
- [ ] The picker supports both modes the Metric primitive supports:
  - **Simple** — pick a column + aggregation primitive + optional filters. **Simple is selected by default.**
  - **Calculated** — write a free-form expression that resolves to a single numeric value (e.g. `SUM(column_a) / NULLIF(SUM(column_b), 0)`).
- [ ] The user sets a numeric condition (less than / greater than / equal to a value) — same condition input as Metric-threshold.
- [ ] Schedule, time-of-day, recipients, channels (with the Slack "Send test message" button), template, and Test Alert behave the same as Story 1.
- [ ] On save, the alert is active and runs on its schedule.

### Story 4 — Test an alert before saving

**As an** alert author, **I want** to dry-run my alert before saving it, **so that** I know it does what I expect.

**Acceptance criteria:**
- [ ] Test is **Step 3** of the wizard, reached by clicking `Test` on Step 2 (Notify). Steps 1 and 2 must be valid before Test can run.
- [ ] Step 3 shows: would-fire status (banner reads *"Alert will fire for current data"* or *"Alert will not fire for current data"*), the numeric current value returned by the query, the alert condition that was evaluated against it, the rendered email message, the rendered Slack message (if Slack is enabled), and the generated SQL (collapsible).
- [ ] Test never sends a real notification.
- [ ] If the query returns no rows, the banner shows *"Alert will not fire for current data"* (no rows = condition not satisfied).
- [ ] The author can return to Step 1 or Step 2, change fields, and click `Test` again to re-run the dry-run with the new inputs.
- [ ] On Step 3, the final CTA is `Create alert` (or `Save changes` in edit mode); the author commits the alert from here.

### Story 5 — Browse alerts in `/alerts` (All alerts and Firing tabs)

**As an** alert owner or operator, **I want** a single place to see every alert and what's currently firing, **so that** I can audit configurations and recent activity in one view — including activity sent to recipients outside Dalgo.

**Acceptance criteria:**
- [ ] `/alerts` has two tabs: **All alerts** and **Firing**.
- [ ] Both tabs use the same table-row format. Each row shows:
  - [ ] **Alert name**, with the source entity name shown as a subtitle underneath:
    - KPI alerts: subtitle is the KPI name, clickable — opens the KPI's annotation page.
    - Metric alerts: subtitle is the Metric name, clickable — opens the Metric edit page.
    - Standalone alerts: subtitle is the dataset name, plain text (not clickable — datasets aren't a navigable entity in v1).
  - [ ] No separate **Source** column — the source-entity info lives entirely in the Alert name cell's subtitle (above).
  - [ ] **Alert condition** in plain language (e.g. `RAG = red`, `value < 50`, `count(*) > 100`).
  - [ ] **Enabled / disabled toggle** to deactivate or re-activate the alert in place.
  - [ ] **Schedule frequency** (daily / weekly / monthly).
  - [ ] **Fire streak** — consecutive recent evaluations that fired.
  - [ ] **Last fire timestamp**, shown relative (e.g. "2h ago").
  - [ ] **3-dot actions menu** with: Edit, Delete, Alert log (Story 6).
- [ ] **Filters and sorts are built into the table component's column headers**, not a separate filter bar. Each column header exposes a filter affordance and click-to-sort:
  - **Enabled** — filter by enabled / disabled.
  - **Frequency** — filter by daily / weekly / monthly.
  - **Last Fire** — sort by recency; filter by a relative time range (e.g. last 24h, last 7 days).
  - Other columns (Name, Alert condition, Fire streak) support sort but no filter in v1.
- [ ] Default sort is **Last Fire descending**.
- [ ] **All alerts tab** shows every alert in the org (active and inactive).
- [ ] **Firing tab** shows alerts whose most recent evaluation fired (i.e. those that would have sent a notification on their last scheduled run).
- [ ] Toggling enabled / disabled from the row updates immediately and does not delete the alert. The change persists across sessions.
- [ ] **Disabled alerts** are skipped on scheduled evaluations — they do not run their query, do not send notifications, and do not produce new history entries.
- [ ] **Disabled rows** remain visible on the **All alerts** tab (dimmed: row text uses a muted gray, toggle is in the off state) but **never appear on the Firing tab**, even if their last evaluation while enabled was a fire.
- [ ] When an alert is re-enabled, its next evaluation runs on its normal schedule (no immediate run on toggle).
- [ ] Clicking **Delete** in the 3-dot menu opens a confirmation modal:
  - Title: **Delete Alert**
  - Body: *"Are you sure you want to delete Alert "<alert name>"? This action cannot be undone."*
  - Buttons: `Cancel` (dismisses, no change), `Delete Alert` (executes the delete, closes the modal, removes the row from the table, and shows a success toast).
- [ ] Deleting a Metric or KPI is blocked while any alert references it (matches prototype behaviour).
- [ ] **Empty state — All alerts tab** (org has zero alerts):
  - Headline: *"No alerts yet"*
  - Subtext: *"Get notified when your Metrics, KPIs, or datasets cross a threshold you care about."*
  - Primary CTA: `Create Alert` (opens the create wizard for a Standalone alert).
  - Secondary buttons: `Go to Metrics` (navigates to `/metrics`) and `Go to KPIs` (navigates to `/kpis`), where the user can pick a Metric / KPI and click "Create Alert" from there.
- [ ] **Empty state — Firing tab** (org has alerts but none are currently firing): shows headline *"No alerts firing"* and subtext *"None of your alerts fired on their last scheduled run."*

### Story 6 — View an alert's fire history (Alert log modal)

**As an** alert owner, **I want** to inspect every past fire of one alert, **so that** I can audit what was sent, to whom, and when — including notifications to external recipients I can't see in any inbox.

**Acceptance criteria:**
- [ ] From the 3-dot menu on any row in either tab, the user can open the **Alert log** modal.
- [ ] The modal title is **Alert log**.
- [ ] The modal lists every past fire of the alert (modeled on the pipeline-history page).
- [ ] Each history entry row shows: time fired, current value at that time, the alert condition that was satisfied, delivery channel(s) used, recipient count summary, and a **Delivery status** column with the summary status for that fire: `Success` (green), `Partial` (amber), or `Failed` (red).
- [ ] **Summary delivery status semantics:**
  - `Success` — every email recipient and every Slack webhook delivery succeeded.
  - `Partial` — at least one delivery succeeded, at least one failed.
  - `Failed` — no delivery succeeded.
- [ ] Each history entry expands to reveal:
  - [ ] The full recipient list per channel — Email recipients (Dalgo users + external emails) grouped together; Slack delivery shown as the configured channel name from the webhook.
  - [ ] The rendered message that was sent per channel (email body, Slack post).
  - [ ] **Per-recipient delivery breakdown** — every email recipient and every Slack webhook is listed individually with a `Sent` / `Failed` status icon. For failed deliveries, the row shows the failure reason inline (email: bounce / SMTP error; Slack: HTTP status code + response body).
  - [ ] **View SQL** — a collapsible block showing the exact SQL that was executed for this evaluation (same SQL surface as Step 3 Test of the wizard). Visible to every user who can open the Alert log — it's a read-only audit affordance.
- [ ] The modal is reachable identically from the All alerts tab and the Firing tab.
- [ ] History is **unlimited** — every past fire is retained indefinitely. The modal paginates older entries.

### Story 7 — Receive a fired alert (Email)

**As a** recipient, **I want** the email notification to tell me what fired, what the current value is, and where to look, **so that** I can act without hunting for context.

**Acceptance criteria:**
- [ ] When an alert fires on its schedule, every recipient on the email list receives one email.
- [ ] External recipients (non-Dalgo users) receive the email but no portal login is required.
- [ ] The email renders the user's template with all tokens substituted.
- [ ] Available tokens are scoped to the alert type:
  - **KPI alert**: `{{ alert_name }}`, `{{ kpi_name }}`, `{{ target_value }}`, `{{ current_value }}`, `{{ rag_status }}`.
  - **Metric-threshold alert**: `{{ alert_name }}`, `{{ metric_name }}`, `{{ target_value }}`, `{{ current_value }}`.
  - **Standalone alert**: `{{ alert_name }}`, `{{ dataset_name }}`, `{{ target_value }}`, `{{ current_value }}`.
- [ ] Each email recipient's delivery is tracked individually. Bounces, invalid addresses, and SMTP errors are captured per recipient and surfaced in the Alert log's expanded history row.

### Story 8 — Receive a fired alert (Slack)

**As a** team that lives in a Slack channel, **I want** alerts to post into our channel via webhook, **so that** the team sees and triages them together without per-recipient DMs.

**Acceptance criteria:**
- [ ] When an alert with Slack delivery fires, the rendered message is POSTed to the alert's configured webhook URL.
- [ ] The channel the post lands in is whatever channel the webhook was created for in Slack (Dalgo does not pick the channel).
- [ ] All recipients on the alert see the same post in the shared channel (no per-user DMs in v1).
- [ ] Slack rendering substitutes the same tokens as email.
- [ ] If the webhook POST fails (non-2xx HTTP response or network error), the failure is recorded in the alert's history entry for that fire — Slack status = `Failed`, HTTP code + response body captured.
- [ ] **No automatic retry** in v1 — failed Slack deliveries are not re-attempted. The author is expected to check the Alert log and fix the webhook URL.
- [ ] Email and Slack delivery are independent — partial success across channels is possible and surfaces as `Partial` status on the fire.

### Story 9 — Role-gated alert management

**As an** org admin, **I want** create / edit / delete to be limited to roles that should have it, **so that** alerts aren't created or removed by people without the right responsibility.

**Acceptance criteria:**
- [ ] Create, edit, and delete actions are gated by role against the current Dalgo role structure.
- [ ] Users without the create role do not see "Create Alert" entry points.
- [ ] Users without the edit role see read-only alert detail and a disabled enabled-toggle.
- [ ] Users without the delete role do not see the delete action in the 3-dot menu.
- [ ] All users with login can view both tabs and open the Alert log modal (subject to org membership).
- [ ] **Visual treatment of gated controls:**
  - Entry-point CTAs (`Create Alert` buttons on Metrics / KPIs / Alerts page) are **hidden** for users without the create role — not visible at all, not greyed-out.
  - In-row controls users can see but not use (Edit / Delete in the 3-dot menu, the enabled toggle) are **disabled** (greyed, not clickable) with a tooltip on hover: *"You don't have permission to <edit / delete / enable> alerts. Contact your admin."*
  - The Alert log modal is fully visible to any logged-in user; no fields are gated within it.

## Toast notifications

User actions throughout the alerts surface produce short-lived toast notifications. All toasts dismiss automatically after ~4 seconds; the user can dismiss them earlier with an X.

### Success toasts (green)
- **Create alert** — *"Alert created. It will run on its next scheduled time."* (shown after clicking `Create alert` on Step 3.)
- **Edit alert** — *"Alert updated."* (shown after `Save changes` on Step 3 in edit mode.)
- **Delete alert** — *"Alert deleted."* (shown after confirming the Delete Alert modal.)
- **Enable alert** — *"Alert enabled."* (shown after the row toggle flips on.)
- **Disable alert** — *"Alert disabled."* (shown after the row toggle flips off.)
- **Slack test message succeeded** — *"Test message sent to Slack."* — shown **inline** next to the `Send test message` button (not a global toast), so it's adjacent to the action.

### Error toasts (red)
- **Create / Edit failed** — *"Couldn't save the alert. <reason>."* with the backend reason if available, generic fallback otherwise.
- **Delete failed** — *"Couldn't delete the alert. <reason>."*
- **Enable/Disable failed** — *"Couldn't update the alert. The row was reverted."*
- **Slack test message failed** — *"Test message failed: HTTP <code>."* — shown **inline** next to the `Send test message` button.

### No toast for
- Test Alert (Step 3 dry-run) — feedback is the Step 3 page content itself, not a toast.
- Tab switches, filter changes, sort clicks — non-destructive UI state changes.
- Scheduled alert fires — these go to the recipients, not back to the author. Authors see them via the Firing tab and Alert log.

## Dependencies

- **Requires:** the reusable Metric and KPI primitives from `features/metrics_kpis/v1/spec.md`. Metric and KPI alerts cannot exist without them. The Standalone alert's dataset / column / aggregation picker reuses the same primitive the Metrics page uses for Metric creation.
- **Requires:** the Access Controls roles already scaffolded in the prototype (for Story 9 gating). Group-based recipient routing is *not* required in v1.
- **Enables:** future versions can layer in pipeline-completion-triggered evaluation, cooldown / re-alert policy, provenance ("last refresh"), KPI-card alert indicators, lifting the `count_distinct` constraint, org-level Slack OAuth with a channel picker, per-type default templates, and additional delivery channels (WhatsApp, generic webhooks).
