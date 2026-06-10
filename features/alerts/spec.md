# Spec: Alerts

## 1\. Problem & opportunity

From the April sprint demos, alerts are a repeated, clear ask across orgs — but with varied shapes:

- **TAP:** dashboards have too much cognitive load for teachers and field staff. Adoption is low. Phone-based push notifications are a much better fit. WhatsApp delivery is the dream (future); they'd happily replace dashboards with alerts for most field use cases.  
- **Bhumi:** alerts are the \#2 priority after dashboards. **Slack integration is a requirement.** Wants alerts routed by team (M\&E vs implementation).  
- **Goalkeep:** wants **non-KPI-threshold alerts** in addition to metric ones — data-entry alerts, attendance-rate alerts, fellow-check-in alerts. Also wants cadence control: "keep telling me every 7 days if it's still failing." Wants alerts to surface last-pipeline-update provenance in the notification.  
- **Central teams (all orgs):** email is baseline; Slack is where real day-to-day ops happens.  
- **Leadership:** summary digest of RAG-state changes via email.

This spec covers an alerting system that serves all five audiences, with three alert types, a simple pipeline-triggered evaluation model, and email \+ Slack delivery at v1.

## 2\. Vocabulary & scope boundary

- **Alert** — a saved rule that evaluates a condition and notifies recipients when it fires  
- **Metric-threshold alert** — references a reusable [Metric](http://./metrics-and-kpis-spec.md) \+ a numeric condition (e.g. "fires when this Metric \< 50")  
- **KPI RAG alert** — references a [KPI](http://./metrics-and-kpis-spec.md) \+ an RAG level (e.g. "fires when RAG \= red")  
- **Standalone alert** — ad-hoc SQL aggregation \+ condition \+ filters, not tied to a Metric. For data-quality and operational checks.  
- **Evaluation** — one run of the alert rule (immutably logged with query, result, and rendered message). In v1, evaluations are triggered by pipeline completion.  
- **Schedule**— if an alert is still firing when the next evaluation runs, the cooldown prevents repeat notifications. Configured per alert; defaults to disabled (notify only on state change).

**Out-of-scope concepts called out here:**

- **Schedule-based / cron-triggered evaluation** — v1 evaluates on pipeline completion only. If pipeline cadence is daily and schedule is 7 days, recipients get weekly notifications — which covers the common case. Decoupled scheduling deferred to a future spec.  
- **Pipeline health alerts** ("notify if pipeline hasn't run in N hours") — pipeline monitoring is outside this spec. Alerts assume pipeline runs; if it doesn't, users notice through other means.  
- **Acknowledge / mute / snooze controls** — deferred to a future iteration. In v1, alert fatigue is managed via the per-alert notification cooldown.  
- **User-group-based recipient routing** (Bhumi's "M\&E team / implementation team") — covered by the **Access Controls spec**. In v1, recipients are picked individually from Dalgo's existing user list, plus free-form external emails.  
- **WhatsApp delivery, webhook delivery** — future. v1 is email \+ Slack.  
- **External-recipient portal login** — external stakeholders (funders, partners) receive emails only; no portal account needed.  
- **AI-chat-over-alerts** — TAP's future vision, separate spec.  
- **SLA / escalation chains** — e.g. "if not acknowledged in 1 hour, escalate to X." Not in v1.  
- **Anomaly-detection alerts** (statistical / ML-based) — not in v1.  
- **Elementary data-quality alerts** — not in v1.

## 3\. Users & primary use cases

- **Program lead / M\&E** — creates **KPI RAG alerts** tied to OKR states. Consumes notifications via email and/or Slack.  
- **Data / analytics team** — creates **Metric-threshold alerts** for operational checks (e.g. "notify when monthly enrolments drop below 500") and **standalone alerts** for data quality (missing rows, dropped pipeline partitions, attendance anomalies).  
- **Field team** — receives alerts on their phone. Does not create them. (WhatsApp delivery is aspirational, not specced here — email \+ Slack is what they get in v1.)  
- **Central team** — receives Slack alerts in shared channels for day-to-day operational coverage.  
- **Internal leadership** — receives summary digests via email.  
- **External stakeholders** (funders, partners) — receive specific alerts via email only when explicitly added to the recipient list.

## 4\. User flows

Text walk-throughs; no wireframes.

### 4.1 Create a KPI RAG alert

1. From a KPI card or the KPI detail drawer, the user clicks "Create Alert."  
2. Alert form opens, pre-filled with the KPI selected and locked.  
3. User picks the RAG level that should trigger (`fires when RAG = red`, or `= red or amber, or any state change`).  
4. **Pipeline(s) triggers evaluation** — default is "any pipeline that touches this KPI's data," which Dalgo infers from the underlying Metric's source tables. User can override with a specific pipeline selection.  
5. User sets **notification schedule** (default: off — "notify only on state change"; can set to re-notify every N days while still firing).  
6. User picks **recipients** — any mix of Dalgo users (searched from the existing user list) and free-form email addresses.  
7. User picks **delivery channels** (multi-select): email (always available), Slack (if org has configured Slack).  
8. For Slack, the user picks a **channel** from the org's Slack workspace (the one shared channel the alert will post to).  
9. The user writes or edits the **message template** — defaults to a sensible pre-filled message with `{{ tokens }}` for metric name, current value, target, RAG state, last-pipeline-update.  
10. User clicks **"Test Alert"** — runs a dry-run against the live warehouse, shows: would-fire status, result preview, rendered email/Slack message preview, generated SQL (for audit).  
11. User saves. Alert is now active — next pipeline run triggers the first evaluation.

### 4.2 Create a Metric-threshold alert

Same as 4.1 but starting from the Metric library (or via an inline Metric definition). Instead of picking an RAG level, user defines a numeric condition: "fires when \[Metric\] is less than / greater than / equal to \[value\]."

### 4.3 Create a standalone alert

Same as 4.1 but starting from scratch — user picks a dataset, aggregation, condition, optional filters. No Metric or KPI involved. Since there's no Metric to infer pipeline-triggers from, user picks the pipeline explicitly in step 4\. For data-entry and operational checks where no pre-defined Metric fits.

### 4.4 Test & Preview an alert before saving

Available from the alert authoring form at any time. Dry-run shows:

- Would-fire status (yes / no)  
- Result preview (rows or scalar value returned by the query)  
- Rendered email message (all tokens substituted with real values)  
- Rendered Slack message (if Slack is enabled)  
- Generated SQL (copy-pasteable, for debugging)

### 4.5 Browse the alerts list

`/alerts` page has two tabs:

- **Configured** — paginated list of every alert in the org. Each card shows: name, linked Metric / KPI (if any), triggering pipelines, last evaluated, last fired, fire streak, is-active toggle.  
- **Triggered** — paginated list of recent fired evaluations across the org. Accordion groups events by alert rule. Click an event to see full detail.

Filters: by linked Metric / KPI, by channel, by active state.

### 4.6 View a fired alert's detail

Opens from the Triggered tab or from a Slack/email link. Shows:

- Which pipeline run triggered the evaluation (`flow_run_id`)  
- What SQL ran (full query, copy-pasteable)  
- The result (rows or scalar that caused the fire)  
- The rendered message (email and/or Slack)  
- Which recipients received it, on which channels  
- **When was the underlying pipeline last updated** (provenance — Goalkeep's ask)  
- Timestamp of the evaluation

### 4.7 Edit / delete an alert

- Edit is the same form as create.  
- Delete is clean for the alert itself. Deleting the **linked Metric or KPI** is blocked while alerts reference it (existing prototype behaviour, keep).

### 4.8 Set up org-level Slack workspace auth

Admin flow, pre-requisite for Slack delivery:

1. Org admin goes to org settings → Integrations → Slack.  
2. Clicks "Connect Slack." Goes through OAuth.  
3. Dalgo receives Slack app tokens. Workspace is now connected.  
4. Alert creators can now pick Slack as a delivery channel and select any channel from that workspace.

Only one Slack workspace per Dalgo org in v1.

### 4.9 View the fired-alert feed across the org

Central-team monitoring view — Triggered tab of the alerts list. Useful for operators who watch everything that's firing, not just their own alerts.

## 5\. Functional requirements

### 5.1 Alert types

Three types, replacing today's single "metric-backed" shape:

- **Metric-threshold alert** — references a reusable Metric \+ a numeric condition  
- **KPI RAG alert** — references a KPI \+ a target RAG level  
- **Standalone alert** — ad-hoc SQL / aggregation \+ condition \+ filters, not tied to a Metric

All three share the same evaluation, recipient, delivery, and evaluation-history mechanics.

### 5.2 Evaluation trigger

Alerts evaluate every time a relevant pipeline completes.

- **For Metric-threshold and KPI RAG alerts**, the default is "any pipeline whose output feeds the Metric's source tables" — inferred automatically. User can override with explicit pipeline selection.  
- **For standalone alerts**, user picks the pipeline(s) explicitly (no Metric to infer from).  
- **Pipeline completion** \= a DBT / DBTCLOUD deployment finishes (existing prototype behaviour, keep).  
- **Evaluation is idempotent per `flow_run_id`** — the same pipeline run never re-evaluates an alert twice.  
- No schedule / cron-based evaluation in v1. If the pipeline doesn't run, alerts don't evaluate. This is an accepted trade-off for simplicity (see § 7).

### 5.3 Notification Schedule

When an alert fires and the condition is *still* met on the next evaluation, the cooldown prevents repeat notifications.

- **Configured per alert.** Alert owner sets a cooldown value in days, or disables it.  
- **Default: disabled** ("notify only on state change"). With default, recipients get one notification per firing event — when the state flips from not-firing to firing. No repeat notifications while the condition persists. If it clears and re-fires later, that's a fresh fire and a fresh notification.  
- **With cooldown \= N days:** while the condition remains firing, recipients get a notification every N days.  
- Cooldown does **not** affect evaluation frequency — evaluations still happen on every pipeline run. Cooldown only gates the outgoing notification.	

Example — cooldown \= 7 days, pipeline runs daily:

```
Mon: pipeline runs → evaluates → MET → NOTIFY (1st notification)
Tue: pipeline runs → evaluates → still MET → cooldown active, skip
Wed: pipeline runs → evaluates → still MET → cooldown active, skip
... (through Sunday) ...
Next Mon: pipeline runs → evaluates → still MET → 7 days passed → NOTIFY (2nd notification)
```

Example — cooldown \= disabled, pipeline runs daily:

```
Mon: pipeline runs → MET → NOTIFY
Tue-Sun: still MET → never re-notify
Wk3 Tue: condition clears → no notification
Wk4 Mon: MET again → fresh fire → NOTIFY
```

### 5.4 Delivery channels — alert-level, multi-select

- **Email** — always available. Recipients are any mix of Dalgo users (by ID) and free-form external email addresses.  
- **Slack** — available if the org has completed the one-time workspace auth. Alert creator picks **one channel** from the workspace. All recipients on the alert see the message in that shared channel (not DMed individually).  
- **WhatsApp** — future, out of scope for v1.  
- **Webhook / generic API delivery** — deferred, out of scope for v1.

### 5.5 Recipients

- **Internal:** pick from Dalgo's existing user list (search by name / email).  
- **External:** free-form email addresses (funders, partners, anyone without a Dalgo account).  
- **User-group-based routing** (M\&E team, implementation team, …) is **deferred to the Access Controls spec.** In v1, routing is via individual user selection.  
- No portal login for external recipients — they get emails only.

### 5.6 Provenance

Fired-alert detail shows **"last pipeline update was X ago"** for the data the alert evaluated against. Answers the "is this data stale?" question recipients will ask (Goalkeep).

### 5.7 Message templates

- Mustache-style `{{ token }}` system (existing prototype, keep).  
- Documented token list: `{{ alert_name }}`, `{{ metric_name }}`, `{{ kpi_name }}`, `{{ current_value }}`, `{{ target_value }}`, `{{ rag_state }}`, `{{ achievement_pct }}`, `{{ last_pipeline_update }}`, `{{ failing_rows_count }}`, `{{ dashboard_link }}`, \+ group-by tokens for grouped standalone alerts.  
- Template editor shows a live preview with tokens substituted from the last test run.

### 5.8 Evaluation history

Every evaluation run logged immutably with:

- Full config snapshot (trigger pipeline(s), recipients, message template at time of evaluation)  
- Query executed \+ raw result  
- Whether it fired  
- Whether a notification was sent (cooldown may have suppressed it)  
- Rendered message (for each channel, if sent)  
- Which recipients received it  
- Trigger source (`flow_run_id`)

Existing prototype behaviour, extended to record suppressed-by-cooldown outcomes.

### 5.9 Lift the `count_distinct` constraint

Current prototype blocks metric-backed alerts on COUNT DISTINCT Metrics as a safety rail. **Target for v1 is to lift this** so users can build alerts on any Metric regardless of aggregation. Contingent on engineering confirming they can compose alert filters and group-by on top of COUNT DISTINCT without semantic inconsistency. Fall back to keeping the constraint only if engineering flags a fundamental blocker.

### 5.10 Alert-to-Metric indicator

On a KPI card (on the KPIs page only), show a **simple correlation marker** — a dot or tag — when alerts are linked to that KPI. No counts. No firing-state indicator. Users who want detail click through to the alert list.

### 5.11 Role-based permissions

Match the current Dalgo role structure for view / create / edit / delete. Evolve alongside the broader Access Controls work as platform roles mature. Permission codes already scaffolded in the prototype; production build wires real gating.

## 6\. Data model — conceptual

- **`Alert`**  
    
  - `alert_type` (threshold / rag / standalone)  
  - Optional FK to Metric (for threshold alerts)  
  - Optional FK to KPI (for RAG alerts)  
  - `pipeline_triggers` — list of pipeline IDs that trigger evaluation. For Metric- or KPI-backed alerts, inferred by default from the Metric's source tables; overridable. For standalone alerts, explicitly picked.  
  - `notification_cooldown_days` — integer or null (null \= disabled, default)  
  - `condition` — numeric threshold details for threshold/standalone, RAG level for RAG alerts  
  - `recipients` — structured list of `{type: "user"|"email", ref: user_id | email_string}`  
  - `delivery_channels` — multi-select: email and/or Slack  
  - `slack_channel_id` — if Slack is enabled  
  - `message_template` — Mustache string  
  - `is_active` — on/off  
  - Standard metadata (created\_by, timestamps)


- **`AlertEvaluation`** — immutable history (exists today, keep, extended).  
    
  - FK to Alert  
  - Config snapshot  
  - Query executed  
  - Result  
  - Fired? (bool)  
  - Notification sent? (bool — false if cooldown suppressed it)  
  - Rendered messages (per channel, if sent)  
  - Recipients notified (if sent)  
  - `flow_run_id` (trigger source)  
  - Timestamp


- **`OrgSlackConfig`** — per-org Slack workspace auth.  
    
  - FK to Org  
  - OAuth tokens (encrypted)  
  - Workspace name / ID  
  - Connected channel list (cached; refreshed periodically)  
  - One config per org in v1.

## 7\. Out of scope (explicit)

- **Schedule-based / cron-triggered evaluation** — v1 evaluates on pipeline completion only. Deferred to a future spec.  
- **Pipeline health alerts** — "notify if pipeline hasn't run in N hours." Pipeline monitoring is a separate concern.  
- WhatsApp delivery (infrastructure dependency, flagged for a future spec)  
- Webhook / generic API delivery (v1 is email \+ Slack only)  
- **Acknowledge / mute / snooze controls** — deferred to a future iteration. v1 relies on a per-alert notification cooldown (including disabled) to manage fatigue.  
- AI-chat-over-alerts (TAP future vision — separate spec)  
- **User-group-based recipient routing** (M\&E / implementation) — covered by the Access Controls spec  
- External-recipient portal login — external stakeholders receive emails only  
- "Simple templates" layer for standalone alerts — current dataset/aggregation/filter UX ships as-is  
- Alert templates marketplace / pre-built packs  
- **Slack DMs to individual recipients** — v1 uses per-alert shared-channel delivery only  
- Elementary data-quality alerts  
- Cross-org alerts  
- SLA / escalation chains (e.g. "if unacknowledged in 1 hour, escalate to X")  
- Anomaly-detection alerts (statistical / ML-based)

## 8\. Open questions — for team / engineering review

- **Lifting `count_distinct`.** Engineering check: can alert filters / group-by compose cleanly on top of COUNT DISTINCT Metrics? If yes, v1 lifts the constraint. If no, keep as a safety rail and note the specific blocker in the spec.  
    
- **Slack app scopes.** What Slack OAuth scopes does the Dalgo app need?  
    
  - Channel posting only (simplest)?  
  - Or also user-read to map Dalgo users to Slack users (if we want to allow per-user Slack DMs in a later iteration)?  
  - Resolve during Slack-integration implementation.


- **Standalone alert — condition UX on aggregation result.** For `COUNT(*) > 100` standalone alerts, how is the condition surfaced in the UI? Unified with metric-threshold condition UX?  
    
- **Inferred pipeline-triggers — UX.** When creating a Metric- or KPI-backed alert, the default is "any pipeline touching the Metric's source tables." How do we surface this inference to the user — show them a preview of which pipelines will trigger, let them override?

## 9\. Success indicators

- **\# of alerts configured per org** — basic adoption  
- **\# of alerts delivered via Slack vs email** — channel adoption; tells us Bhumi's need landed  
- **\# of standalone alerts vs Metric- or KPI-backed** — tells us the non-metric use case is landing (Goalkeep)  
- **% of alerts with notification cooldown enabled** — signal; if most alerts have it enabled, users want repeat reminders; if most have it disabled, the state-change model is serving them well  
- **Field-team retention of phone notifications** — once WhatsApp lands, measures whether alerts-for-field is a real primary surface

---

## Dependencies

- **Slack integration infrastructure** — OAuth flow, app registration with Slack, encrypted token storage, channel posting library. Pre-requisite for any Slack delivery. Estimate with engineering.  
- **Reusable Metric object** — alerts reference Metrics. Blocks on the Metric primitive landing (see [`metrics-and-kpis-spec.md`](http://./metrics-and-kpis-spec.md)).  
- **Access controls** — parts of the alerts spec (recipient groups, permission-gated create/edit/delete) depend on the upcoming Access Controls spec. Flagged throughout.

**Infrastructure NOT needed:** unlike earlier drafts, no separate cron / scheduled worker is required — evaluation piggybacks on the existing pipeline-completion webhook from the prototype.

## Prototype → production migration

No user-visible data migration needed — the `pratiksha/alerts-metrics-changes` branch is not yet released to production.

Engineering-side changes:

- Add `OrgSlackConfig` model \+ OAuth flow  
- Extend `Alert` model: add `pipeline_triggers` (list), `notification_cooldown_days` (int|null), split recipients into `{user_id}` \+ `{email}` lists, add `slack_channel_id`  
- Update `AlertEvaluation` recording to include `notification_sent?` flag and per-channel rendered messages  
- Implement three alert types (today's is a single "metric-backed" shape) — split into threshold / RAG / standalone at the data-model level  
- Attempt to lift the `count_distinct` constraint; fall back to keeping it only if the filter/group-by composition is unsound

---

*Questions? Open a comment on this doc or ping the product team. Final sign-off from product \+ engineering before production build begins.*

# Discussion on snooze:

Makes sense — let me think it through with you before touching anything.

## The simplified model you're proposing

**One trigger mode:** alerts evaluate on pipeline completion (whatever transform / dbt job runs).  
**Re-alert cooldown:** if the condition is *still* crossed after the cooldown expires, re-notify.

That's it. Two things to configure. No separate "schedule" concept.

## Walking through whether it covers the use cases

### Bhumi — weekly fellow check-in alert

* Pipeline runs daily at midnight  
* Alert: "Fire if fewer than 20 check-ins this week"  
* Re-alert cooldown: 7 days

Timeline:

```

Mon midnight: pipeline runs → alert evaluates → <20 → NOTIFY
Tue midnight: pipeline runs → evaluates → still <20 → cooldown active, skip
Wed-Sun: same — still firing, still in cooldown
Next Mon: 7 days passed → still <20 → NOTIFY again
```

✅ Works — recipient gets notified weekly even though evaluation runs daily.

### Goalkeep — "tell me every 7 days if still failing"

Same pattern as above. ✅ Works.

### Success Metric RAG alert — goes red

* Pipeline runs daily  
* Alert: "Fire when RAG \= red"  
* Re-alert: 7 days (or disabled)

Day 1: pipeline runs → red → NOTIFY  
Day 2-7: still red → cooldown  
Day 8: still red → NOTIFY (if cooldown 7d) or silent (if disabled)  
Day 20: clears to green (no notification — we don't spam for recoveries unless user wants that)  
Day 30: goes red again → NEW fire → NOTIFY

✅ Works — state-change re-firing is still captured.

### Data quality / standalone alert

* Pipeline runs → check data shape → if broken, fire.

✅ Works — in fact this is the *native* use case for pipeline-triggered.

## The one gap I want to flag

**Pipeline didn't run at all** (broken, paused, or the Airbyte source is dead).

Under the simplified model, no pipeline run \= no evaluation \= no alert. You'd be silent about a scenario where something is genuinely wrong — the pipeline itself.

Two ways to handle this:

**(a) Accept the gap for v1.** Pipeline health is not in the alerts spec — it's a separate "monitoring" concern Dalgo either already has or handles elsewhere. Alerts assume pipeline runs; if pipeline doesn't run, the user has a bigger problem they'd notice through other means.

**(b) Add a "stale data" escape hatch.** One built-in alert type: "Notify if pipeline X hasn't completed in N hours." This one alert is the only thing that's time-triggered — everything else is pipeline-triggered.

My lean: **(a) for v1**. Keep the mental model simple. If pipeline monitoring matters later, spec it separately.

## What this does to the spec

If you land on this model, these changes follow:

1. **Collapse §5.2 "Trigger modes"** from the three-mode design (schedule / pipeline / both) to a single line: "alerts evaluate every time the underlying pipeline completes. User picks which pipeline(s) feed this alert."  
2. **Reframe §5.3 "Re-alert policy"** as **"Notification cooldown"** — if still firing when the next evaluation runs, notify again only if N days have passed since the last notification. Rename gets rid of the "re-alert" confusion entirely.  
3. **Simplify user flows §4.1–4.3** — no "set trigger schedule" step. Just "set re-notification cooldown."  
4. **Remove §4.8** entirely ("enable pipeline-completion as additional trigger" becomes moot — it's the default and only mode).  
5. **Drop the "Scheduled evaluation infrastructure" dependency** — huge engineering-complexity win. No net-new scheduled worker needed; reuse the existing pipeline-webhook evaluation hook from the prototype.  
6. **Data model** simplifies:  
   * trigger\_mode becomes pipeline\_ids: list (which pipelines trigger this alert)  
   * re\_alert\_policy becomes notification\_cooldown\_days: int | null

Net: the spec gets *meaningfully* shorter and simpler. Engineering doesn't have to build a cron-based alert evaluator. The mental model collapses into: "pipeline runs → if crossed → maybe notify, gated by cooldown."

## Is this what you want?

If yes, I'll:

1. Apply your three answers (KPI rename, §9 out-of-scope cleanup, trigger simplification) across README \+ both specs  
2. Also apply the team feedback from the metrics spec (drop page-level time filter in favour of per-metric)  
3. Come back with a clean sweep

If you want gap (b) — a built-in "stale pipeline" alert type — say so and I'll add it. Otherwise we ship (a) and leave pipeline monitoring to a separate spec.  
yes that's what I wan't lets go with (a)  
Executing the sweep. One additional call I'm making: since Derived Metrics was removed from §4.1's flow but still appears in §6 and §8, I'm removing it entirely (fold metric composition into Calculated SQL). Says so in my summary; revert if wrong.  
Updated todos  
Starting with the alerts spec — biggest structural simplification.  
Createdalerts-spec.md  
\+328-0  
Now the metrics-and-kpis spec:  
Createdmetrics-and-success-metrics-spec.md  
\+303-0  
Now the README:  
CreatedREADME.md  
\+116-0  
Now renaming the metrics spec file so the filename matches the KPI terminology:  
Ran a command, updated todos  
Sweep complete. Here's what changed.

## Rename propagated everywhere

* **"Success Metric" → "KPI"** across all three files — section headings, flow names, bullet copy, data model class name (SuccessMetric → KPI), success indicators, references between docs  
* Filename renamed: metrics-and-success-metrics-spec.md → metrics-and-kpis-spec.md. README link updated to match.  
* **KPIs page** (plural for the listing view), **KPI** (singular for the object and the dashboard chart type), **KPI RAG alert** (alert type)

## §9 cleanup — out-of-scope items now clean bullets

* Staggered targets per period → "every KPI has a single target in v1, period-specific overrides deferred"  
* Drill-down to a dimension → "every KPI is viewed at its configured grain in v1, runtime 'split by state' / 'filter to Karnataka' deferred"  
* Stripped the descriptive-paragraph content that was leaking from §5

## Trigger model simplified (alerts spec)

* **§5.2 Trigger modes** collapsed to a single evaluation rule: **"alerts evaluate every time a relevant pipeline completes."** No schedule, no cron, no "both" mode.  
* **§5.3 Re-alert policy** renamed to **"Notification cooldown"** with the clearer semantics: default \= disabled (notify on state change), user can set N-day cooldown for "keep telling me every 7 days" style behaviour. Includes two worked examples showing notification timing.  
* **§4.8 removed** (the "enable pipeline-completion as additional trigger" flow is no longer meaningful — it's the only trigger).  
* **Data model** simplified: trigger\_mode → pipeline\_triggers (list of pipeline IDs); re\_alert\_policy → notification\_cooldown\_days (int or null).  
* **Dependencies** updated — dropped "Scheduled evaluation infrastructure" (big engineering-complexity win). Explicit note added: "unlike earlier drafts, no separate cron / scheduled worker is required."  
* **Out of scope** now explicitly lists "Schedule-based / cron-triggered evaluation" \+ "Pipeline health alerts" with brief rationale.

## Per-metric time filter (team feedback applied)

* **Page-level time filter removed** from §5.2 (KPI browse) and §7 (KPI functional requirements)  
* Each KPI is scoped by its own trend config (grain \+ trailing periods), inherited from its Metric by default  
* README scope summary updated accordingly

## Derived Metrics folded into Calculated SQL

You'd removed "Derived" as a distinct mode from §4.1 but left references in §6 and §8. I fully collapsed the concept:

* **Creation modes are now Simple and SQL only**  
* Simple mode supports **column-level arithmetic in the column slot** (e.g. col\_a \- col\_b) — this is what "columns against other columns" meant  
* Metric-over-metric composition (Metric\_A / Metric\_B) is achievable via **Calculated SQL mode** — you write the SQL manually  
* Removed from open questions: "Derived Metrics — evaluation model" and "Derived Metrics — circular reference prevention" (not applicable without a derived builder)  
* Added a new open question: **"Simple-mode column expressions — how far?"** — arbitrary arithmetic vs constrained? Where's the line between Simple-with-expressions and SQL mode?

## Other small cleanups

* README scope summary refreshed (removed "derived Metrics (single-level)" reference)  
* Team-feedback section at bottom of metrics spec marked as **"(applied)"** with the two items ticked — kept as audit trail  
* Alerts spec §5.8 (evaluation history) extended to record notification\_sent? flag, since cooldown can now suppress notifications  
* All cross-references between specs updated to point to new filename

