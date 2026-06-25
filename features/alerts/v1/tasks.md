# Alerts v1 — Execution checkpoint

**Plan:** [plan.md](./plan.md)
**Started:** 2026-06-11

This file tracks execution progress so a resumed session can pick up where the previous one left off. Update as work moves forward.

---

## Milestone 1 — Alert data model + CRUD API (backend-only)

**Status:** ✅ COMPLETE — 2026-06-11

### What shipped

**Backend (`DDP_backend_alerts/` on `feature/alerts`):**
- `ddpui/models/alert.py` — `Alert` + `AlertLog` models with JSON columns for `standalone_config`, `condition`, `recipients`, `alert_snapshot`, `deliveries`. Plus `AlertType` enum.
- `ddpui/models/__init__.py` — registered new models.
- `ddpui/migrations/0164_alert_models.py` — auto-generated migration, applied locally.
- `seed/002_permissions.json` — appended `can_view_alerts`, `can_create_alerts`, `can_edit_alerts`, `can_delete_alerts` (pks 82–85).
- `seed/003_role_permissions.json` — appended assignments granting all four permissions to roles 1–4 (Super User, Account Manager, Pipeline Manager, Analyst). Guest (role 5) excluded per user instruction.
- `ddpui/schemas/alert_schema.py` — `AlertCreate`, `AlertUpdate`, `AlertResponse`, `AlertListItem`, `AlertListResponse`, `AlertTestRequest`, `AlertTestResponse`, `SlackTestRequest`, `SlackTestResponse`, `AlertLogOut`, `LogListResponse`, `StandaloneConfig`, `Condition` (discriminated `Union[ThresholdCondition, RagCondition]`), `RecipientIn`, `RecipientOut`, `mask_webhook_url` helper.
- `ddpui/core/alerts/exceptions.py` — `AlertServiceError`, `AlertNotFoundError`, `AlertValidationError`.
- `ddpui/core/alerts/scheduling.py` — `validate_cron`, `previous_fire`, `is_due`, `derive_frequency_label`.
- `ddpui/core/alerts/condition.py` — `validate_condition`, `evaluate`, `pretty`.
- `ddpui/core/alerts/alert_service.py` — `AlertService` with `get_alert`, `list_alerts`, `list_firing`, `get_log`, `compute_fire_streak`, `create_alert`, `update_alert`, `toggle_alert`, `delete_alert`.
- `ddpui/api/alert_api.py` — `alert_router` with 8 endpoints: list, firing, create, get, update, toggle, delete, logs.
- `ddpui/routes.py` — `alert_router` mounted at `/api/alerts/` and tagged "Alerts".
- `ddpui/core/metric/metric_service.py` — `get_metric_consumers` extended to include `alerts` key.
- `ddpui/schemas/metric_schema.py` — `MetricConsumersResponse.alerts` added.
- `ddpui/core/kpi/kpi_service.py` — `get_kpi_consumers` added (dashboards + alerts).
- `ddpui/api/kpi_api.py` — `GET /api/kpis/{id}/consumers/` added.

### Tests

- `ddpui/tests/core/alerts/test_scheduling.py` — 16 cases (cron parsing, due check, prev-fire math).
- `ddpui/tests/core/alerts/test_condition.py` — 26 cases (validation, evaluation, pretty).
- `ddpui/tests/core/alerts/test_consumers_extension.py` — Metric + KPI consumer extension verifying alerts appear.
- `ddpui/tests/api_tests/test_alert_api.py` — 20 CRUD + listing + permissions cases including:
  - All three alert types created with proper validation
  - External + Dalgo-user recipient mix
  - Slack webhook URL masking on GET responses
  - Invalid cron rejection
  - Duplicate name rejection
  - Missing-source rejection per alert_type
  - 3-RAG-states rejection
  - List filter by `is_active`
  - Update / toggle / delete
  - **Metric delete cascades to Alert** (verifies the user's CASCADE choice)
  - Empty `/logs/` for an alert with no evaluations

**Test totals at the end of M1:** `100 passed` (alerts + metric + KPI). No regressions.

### Validation done

- ✅ `makemigrations` + `migrate` apply cleanly
- ✅ All routes load (Ninja URL graph builds)
- ✅ `black` formatting applied
- ✅ 100 tests passing including the 64-test new alert suite and the existing 36-test metric+KPI suite

### Decisions captured during execution

- `condition` and `standalone_config` are JSON columns; shapes enforced at API boundary via Pydantic discriminated Union.
- `recipients` is a JSON list on Alert (no separate AlertRecipient table).
- `alert_snapshot` on AlertLog freezes `{name, alert_type, metric_id?, kpi_id?, condition, recipients, message_template}`. SQL audit lives in `sql_executed`; rendered body in `message`.
- `Alert.metric` / `Alert.kpi` use `on_delete=CASCADE` per user choice — Metric/KPI deletion silently removes their alerts (and AlertLog rows transitively). Spec Story 5 contradiction flagged in plan §8 open question 8.
- No `summary_status` column — neither stored nor computed at serialization. Frontend can derive from `fired` + `deliveries` if needed; spec Story 6's "Delivery status" badge deferred (open question 7).

### Out of M1 scope (per plan)

- Dry-run endpoint (`POST /api/alerts/test/`) — Milestone 3.
- Slack webhook test endpoint (`POST /api/alerts/test-slack-webhook/`) — Milestone 2 (route stub) / Milestone 3 (implementation).
- Evaluator + delivery + Mustache rendering — Milestone 3.
- Celery dispatcher + beat config — Milestone 3.

---

## Milestone 2 — Authoring wizard UI (Steps 1 + 2)

**Status:** ✅ COMPLETE — 2026-06-11

### What shipped

**Backend (`DDP_backend_alerts/` on `feature/alerts`):**
- `ddpui/api/alert_api.py` — wired `POST /api/alerts/test-slack-webhook/` and `GET /api/alerts/recipients/orgusers/`.
- `ddpui/core/alerts/alert_service.py` — `AlertService.test_slack_webhook(url)` posts a fixed payload, returns `(success, http_status, response_body)`. Captures `requests.RequestException` as `(False, 0, msg)`.
- `ddpui/schemas/alert_schema.py` — added `RecipientCandidate` (orguser_id + email + name) for the wizard picker.
- `ddpui/tests/api_tests/test_alert_api.py` — 4 new slack-webhook tests + 1 recipient-candidates test; aliased the imported `test_slack_webhook` as `run_slack_webhook_test` to avoid pytest treating the imported handler as a test function.

**Frontend (`webapp_v2/` on `feature/alerts-prod`):**
- `lib/api.ts` — added `apiPatch` helper.
- `jest.setup.ts` — added `apiPatch: jest.fn()` to the global `@/lib/api` mock.
- `types/alerts.ts` — TS interfaces mirroring backend Pydantic + cron utilities `localScheduleToUtcCron` / `utcCronToLocalSchedule` (round-trip safe; clamps DOM to [1, 28]).
- `hooks/api/useAlerts.ts` — `useAlerts`, `useFiringAlerts`, `useAlert`, `useAlertLogs`, `useAlertRecipientCandidates` SWR hooks + `createAlert`, `updateAlert`, `toggleAlert` (PATCH), `deleteAlert`, `testSlackWebhook` mutators.
- `components/alerts/ScheduleField.tsx` — frequency × day × time-of-day. Browser tz label shown next to time.
- `components/alerts/RecipientCombobox.tsx` — dual-mode combobox (Dalgo user search + free-form external email). Visual chip differentiation (UserIcon vs Mail).
- `components/alerts/TemplateEditor.tsx` — Mustache token insert + live preview (frontend renders client-side from `sampleValues`).
- `components/alerts/AlertDefineStep.tsx` — Step 1: name + type-specific source (Metric chip / KPI chip + RAG bands / DatasetSelector + Function + Column) + condition (threshold or RAG 1–2) + ScheduleField.
- `components/alerts/AlertNotifyStep.tsx` — Step 2: channels (Email always on, Slack toggle) + slack URL + "Send test message" button (calls real endpoint) + RecipientCombobox + TemplateEditor.
- `components/alerts/AlertWizardModal.tsx` — top-level Dialog. Holds DefineState + NotifyState. Validates step-by-step, gates Next. Step 3 placeholder with Save button. Edit mode prefills from `useAlert` and round-trips cron → ScheduleSpec. On save: builds AlertCreate / AlertUpdate payloads, toasts.
- `app/alerts/page.tsx` — placeholder listing (M4 replaces with full tabs). Shows name, type, source, condition, frequency, last fire, enabled switch, 3-dot menu (edit/delete). "Create alert" CTA opens wizard scoped to `standalone`. Permission-gated.
- `components/metrics/metrics-library.tsx` — added "Create Alert" row-action item (BellRing icon) that opens wizard with `{alertType: 'metric_threshold', metricId}`.
- `components/kpis/kpi-detail-drawer.tsx` — added BellRing CTA next to Edit in the drawer header. Opens wizard with `{alertType: 'kpi_rag', kpiId}`.

### Tests

- `ddpui/tests/api_tests/test_alert_api.py` — added 4 tests (slack success / failure status / network error / empty-URL rejection) + 1 recipient candidates test. 73 backend alert tests pass.
- `__tests__/lib/alerts-cron.test.ts` — 8 cron-utility tests (cron shape, round-trip for daily/weekly/monthly, null returns for unsupported patterns).
- `components/alerts/__tests__/RecipientCombobox.test.tsx` — 4 tests (Dalgo user select, external email add, invalid-email rejection, chip removal). Uses per-test `SWRConfig` provider to isolate cache.
- `components/alerts/__tests__/AlertWizardModal.test.tsx` — 4 tests (open on step 1, blocks Next on invalid step 1, advances on valid, Back preserves values).

**Test totals at the end of M2:** 16 new frontend tests + 5 new backend tests, all passing. Total backend alert suite is now 69 passing (M1 + M2). Full webapp_v2 suite: 1320 pre-existing tests still passing (2 pre-existing failing suites unrelated to alerts).

### Validation done

- ✅ Backend `pytest` 69 passes (64 from M1 + 5 new) across `test_alert_api.py` and `tests/core/alerts/`
- ✅ Backend `black` applied
- ✅ Frontend `tsc --noEmit` clean for all new alert files (pre-existing repo errors unchanged)
- ✅ `prettier --write` applied to all new + modified files
- ✅ `jest` 16/16 new tests pass; full suite 1320 passing (3 pre-existing failures unrelated)

### Decisions captured during execution

- **OrgUser id was unavailable to the frontend.** `/api/organizations/users` returns `user_id` (User pk), not `orguser_id` (OrgUser pk) which the alert recipient FK uses. Solved by adding a dedicated `GET /api/alerts/recipients/orgusers/` endpoint (lightweight: orguser_id + email + name) instead of extending the shared `OrgUserResponse`. Keeps the contract scoped to Alerts feature.
- **Cron round-trip is timezone-aware** in the browser. `localScheduleToUtcCron` and `utcCronToLocalSchedule` use `Date.UTC()` and `getUTCHours()`/`getUTCDate()` so a 9:00 IST schedule entered by the author becomes `30 3 * * *` in UTC, and edit-mode prefill reverses correctly. Day-of-month is clamped to 1–28 (consistent with spec) — DST is not modeled (target userbase is IST which doesn't observe DST).
- **Slack webhook URL masking is honored on edit.** When the wizard loads in edit mode it sets `slackWebhookUrlIsMasked = true`; the UPDATE payload omits `slack_webhook_url` unless the user actually types a new URL. Pasting a new URL flips the flag and the new URL is sent.
- **Step 3 is intentionally a placeholder.** Test-and-review UI lands in M3 alongside the dry-run endpoint. The wizard's Save button is enabled on step 3 so the create-update flow is end-to-end exercisable now.
- **Standalone form is Simple mode only for M2.** Calculated mode (column_expression) and filter clauses are deferred. The plan's `MetricColumnAggregationFields` extraction was not done — instead AlertDefineStep inlines the simpler version since v1 doesn't share state with the Metric form.
- **Wizard validation is per-step, not on every keystroke.** Errors render only after clicking Next. Final validate-then-jump-back fires from Save if any step is invalid.

### Out of M2 scope (per plan)

- Step 3 (Test) UI + `POST /api/alerts/test/` dry-run — M3.
- Evaluator + delivery + Mustache server-side rendering — M3.
- Full /alerts listing (All / Firing tabs, sort, filter, Alert log modal) — M4.
- Calculated expression mode + filter clauses for Standalone alerts — deferred (not blocking M2 acceptance criteria).
- Permission gating polish + nav unhide — M5.

### Entry points wired

- `/alerts` page → "Create alert" button (top-right) launches wizard with `alertType: 'standalone'`.
- `/metrics` row 3-dot menu → "Create Alert" launches wizard with `alertType: 'metric_threshold'` and `metricId` prefilled.
- KPI detail drawer header → BellRing icon launches wizard with `alertType: 'kpi_rag'` and `kpiId` prefilled.

---

## Milestone 3 — Evaluation engine (dispatcher + evaluator + delivery + dry-run)

**Status:** ✅ COMPLETE — 2026-06-11

### What shipped

**Backend (`DDP_backend_alerts/` on `feature/alerts`):**
- `ddpui/core/alerts/rendering.py` — `render()` (simple `{{token}}` regex substitution, missing tokens preserved as raw braces), `resolve_tokens()` per type, `tokens_for_alert()` Alert-instance helper, `TOKENS_BY_TYPE` constant mirrored to frontend. **Chose plain regex over pystache** — closed token set, no sections/loops, equivalent semantics, no new dependency.
- `ddpui/core/alerts/alert_query.py` — `compute(alert, org_warehouse)` and `compute_from_config(...)` (for dry-run). Per-type executors:
  - **metric_threshold** → AggQueryBuilder over the metric's whole dataset
  - **kpi_rag** → AggQueryBuilder with time grain (`apply_time_grain`) + `limit(1)` order by period desc → most recent period value, then `compute_rag_status()` (falls back to whole-dataset aggregate when KPI has no time grain)
  - **standalone** → AggQueryBuilder from `standalone_config` (schema/table/agg/column or column_expression) + optional filter clauses (eq/neq/gt/lt/gte/lte)
  - All return `(value, sql_string, rag_status_or_None)` for AlertLog audit
- `ddpui/core/alerts/delivery.py` — `deliver_email()` (SES via `awsses.send_text_message`), `deliver_slack()` (POST with 10s timeout), `deliver_all(alert, subject, body)` runs the full per-recipient + slack loop with per-channel status capture, `summarize()` helper for the optional success/partial/failed badge.
- `ddpui/core/alerts/alert_service.py` — `AlertService.dry_run(org, AlertTestRequest)` runs the full pipeline (query → evaluate → render) with no persistence and no delivery; returns `AlertTestResponse` with `would_fire`, `current_value`, `sql_executed`, `message`, and graceful `error`.
- `ddpui/api/alert_api.py` — wired `POST /api/alerts/test/` (dry-run). Exposed as `test_alert` (imported as `run_dry_run` in tests to avoid pytest collision).
- `ddpui/schemas/alert_schema.py` — added optional `name` field to `AlertTestRequest` so the dry-run preview can render `{{alert_name}}` accurately.
- `ddpui/celeryworkers/alert_tasks.py` — `dispatch_due_alerts` (beat-fired, iterates active alerts, calls `is_due`, enqueues `evaluate_alert.delay`) and `evaluate_alert` (atomic claim via conditional UPDATE on `last_evaluated_at`; reload with `select_related`; run `_run_evaluation` which builds SQL → executes → evaluates condition → renders body → calls `deliver_all` → writes one AlertLog row with snapshot + sql_executed + message + deliveries JSON).
- `ddpui/settings.py` — added `CELERY_BEAT_SCHEDULE["alerts-dispatcher"]` running every 60 seconds.

**Frontend (`webapp_v2/` on `feature/alerts-prod`):**
- `types/alerts.ts` — added `AlertTestPayload` + `AlertTestResponse` interfaces.
- `hooks/api/useAlerts.ts` — added `dryRunAlert(payload)` mutator.
- `components/alerts/AlertTestStep.tsx` — Step 3 UI. Auto-runs the dry-run on mount + whenever the payload signature changes (Back→Next re-runs). States rendered: loading spinner, network-error block with retry, backend-error block (e.g. "no warehouse"), would-fire green banner, would-not-fire muted banner, empty-result amber banner. Shows current_value + outcome badge, rendered message in a styled block, collapsible SQL pre tag, manual Re-run button.
- `components/alerts/AlertWizardModal.tsx` — replaced the M2 placeholder with `<AlertTestStep payload={...} />`. Save button on Step 3 still creates/updates the alert.

### Tests

- **Backend (added in M3):** 26 new tests, all passing.
  - `ddpui/tests/core/alerts/test_rendering.py` — 9 tests (substitution, missing tokens preserved, None/empty preserved, whitespace inside braces, type-specific token resolvers, TOKENS_BY_TYPE constants match frontend).
  - `ddpui/tests/core/alerts/test_delivery.py` — 6 tests (SES send success / failure, Slack 2xx / non-2xx / network error, summarize classifier).
  - `ddpui/tests/core/alerts/test_alert_tasks.py` — 7 tests (writes-log-and-fires, would-not-fire still writes log, atomic claim dedup (second call returns False, only one AlertLog row), skips disabled alerts, records warehouse error gracefully, dispatcher enqueues active due alerts, dispatcher skips inactive).
  - `ddpui/tests/api_tests/test_alert_api.py` — 4 new dry-run endpoint tests (would-fire true / false, no-warehouse graceful error, kpi_rag evaluates via rag_status not raw value).
- **Frontend (added in M3):** 7 new tests, all passing.
  - `components/alerts/__tests__/AlertTestStep.test.tsx` — would-fire banner + message, would-not-fire banner, empty-result amber banner, backend-error block, network-error block, SQL toggle expand/collapse, re-run on payload change.

**Test totals at the end of M3:** Backend alert suite **95 passing** (M1 64 + M2 5 + M3 26). Frontend alert suite **23 passing** (M2 16 + M3 7). Full webapp_v2 suite 1327 passing (3 pre-existing failures unrelated).

### Validation done

- ✅ Backend `pytest` 95/95 alert tests pass
- ✅ Backend `black` applied to all M3 files
- ✅ Frontend `tsc --noEmit` clean for all new alert files
- ✅ `prettier --write` applied to all new + modified files
- ✅ `jest` 23/23 alert tests pass; full suite 1327 passing (no new regressions)

### Decisions captured during execution

- **No pystache dependency added.** For v1 the template surface is a closed per-type token set with simple `{{token}}` substitution and no Mustache sections / loops. A 5-line regex implementation is semantically equivalent. Frontend `TemplateEditor` already uses the same regex; backend now matches. Reduces blast radius for future Mustache feature requests (single 5-line function vs. lifecycle of an external dep).
- **kpi_rag picks the most recent time-grain period**, not the whole-dataset aggregate. Mirrors `KPIService._compute_trend` (limit=1, descending) so the value the evaluator uses matches what users see in the KPI drawer. Falls back to whole-dataset aggregate if the KPI has no time_grain configured.
- **Standalone alerts support filters in `standalone_config`** (eq/neq/gt/lt/gte/lte). The wizard doesn't expose a filter UI in M2; the backend is forward-compatible for when M4/M5 add it. Stored shape: `[{column, operator, value}, ...]`.
- **Evaluator atomic claim semantics.** The conditional UPDATE on `last_evaluated_at` runs BEFORE the warehouse query, so a crash between claim and notification loses the fire for that tick. Accepted trade-off per plan §3.6. Verified by `test_evaluate_alert_idempotent_atomic_claim` (a second call within the same tick returns False without re-querying).
- **AlertLog row written for every evaluation**, including non-fires and warehouse-error cases. Errors land in `alert_snapshot.error`. Message is rendered even on non-fires so the log shows "what would have been sent." Deliveries list is empty `[]` on non-fires (no SES / Slack calls made).
- **Subject line is hardcoded** as `[Dalgo alert] {alert.name}` for v1. Spec doesn't ask for templatable subjects; can be revisited if NGO partners request it.
- **`AlertTestRequest` gained an optional `name` field.** Needed so the dry-run can render `{{alert_name}}` in the preview. Defaults to "Test alert" if absent. Schema additive, backwards-compatible.
- **Test-step re-runs on Back→Next** because the payload signature (JSON.stringify) changes when the user edits Step 1 or Step 2. No "stale" preview if the user reaches Step 3 a second time with different inputs.

### Out of M3 scope (per plan)

- Full /alerts listing (All / Firing tabs, sort, filter, Alert log modal) — M4.
- Permission gating polish + nav unhide — M5.
- `summary_status` badge on Alert log rows — open question §8 #7 (deferred decision; backend already returns `fired` + `deliveries`, frontend can derive).
- Calculated expression mode + filter UI for Standalone alerts in the wizard — deferred.

### How to verify end-to-end (manual smoke)

1. Backend: `pm2 restart dalgo_dev.config.js` to pick up the new `CELERY_BEAT_SCHEDULE` entry.
2. Create a Standalone alert with `schedule_cron = "* * * * *"` (every minute) targeting a small table.
3. Within 60s the `django-celery-beat` service fires `alerts.dispatch_due_alerts`, which enqueues `alerts.evaluate_alert` on the worker queue.
4. The evaluator runs the SQL, evaluates the condition, sends SES + Slack if fired, and writes an `AlertLog` row.
5. Frontend: open the wizard from `/alerts` or the Metrics/KPI entry points → Step 3 auto-shows the dry-run result (no persistence, no delivery).

---

## Milestone 4 — /alerts listing + Alert log modal + Firing tab

**Status:** ✅ COMPLETE — 2026-06-11

### What shipped

**Backend (`DDP_backend_alerts/` on `feature/alerts`):**
- No code changes — M3 already shipped the `firing` / `logs` endpoints with correct shapes, the `(alert, -evaluated_at)` and `(alert, -evaluated_at, fired)` indexes on AlertLog, and `compute_fire_streak`. M4 audit verified these are good for v1 scale.

**Frontend (`webapp_v2/` on `feature/alerts-prod`):**
- `components/alerts/AlertsTable.tsx` — new table component with per-column sort/filter affordances:
  - Columns: Name (+ source subtitle), Alert condition, Enabled toggle, Frequency, Fire streak, Last fire, Actions.
  - **Source subtitle** is a `next/link` for Metric (`/metrics?highlight=N`) and KPI (`/kpis?open=N`); plain text for Standalone (datasets aren't navigable per spec).
  - Sort by Name / Condition / Frequency / Fire streak / Last fire (all in-page client-side; default = Last fire desc).
  - Filter Enabled (all/enabled/disabled), Frequency (all/daily/weekly/monthly), Last fire window (any/24h/7d/30d).
  - In-row Switch wired to `toggleAlert` mutation; 3-dot menu with Edit / Alert log / Delete.
  - Disabled rows render in muted gray (text-gray-400) but stay visible on All alerts; the Firing tab hides them via the server-side `is_active=True` filter inside `useFiringAlerts`.
  - Exports `AllAlertsEmptyState` (with "Create alert" + Go to Metrics + Go to KPIs CTAs per spec Story 5) and `FiringEmptyState`.
- `components/alerts/AlertLogModal.tsx` — paginated per-alert evaluation history modal:
  - Lists `AlertLog` rows; each row shows evaluated_at + relative time, value, condition_pretty, channel summary, and a Success/Partial/Failed/Not-fired badge derived client-side from `deliveries` (resolves plan §8 open question #7).
  - Expanded row shows: rendered message body, Email recipient list with per-recipient Sent/Failed icons + HTTP code + error reason, Slack delivery row, collapsible SQL block (View SQL / Hide SQL).
  - Pagination matches backend page_size (10).
- `app/alerts/page.tsx` — replaces the M2 placeholder:
  - Top-level tabs (All alerts / Firing) with row counts in the labels; Firing count shows in red when > 0.
  - `useAlerts` (with enabled/frequency server filters) feeds the All tab; `useFiringAlerts` feeds the Firing tab.
  - Delete confirmation copy updated to spec Story 5 wording ("Delete Alert" / "Are you sure you want to delete Alert "<name>"? This action cannot be undone." / "Delete Alert" button).
  - AlertLogModal hooked up via row 3-dot menu; AlertWizardModal hooked up for edit; both invalidate both SWR caches on success.
- `components/metrics/consumer-links.tsx` — extended to render an "Alerts" group alongside Charts / KPIs. Links open `/alerts` (no per-alert deep link in v1).
- `components/metrics/metrics-library.tsx` — delete dialog now distinguishes blocking consumers (Charts / KPIs → block delete) from cascade consumers (Alerts → warn but allow delete). Lists the alerts that will be removed when delete is allowed.
- `components/kpis/kpi-delete-dialog.tsx` — switched from `useKPIDashboards` to a new `useKPIConsumers` hook (combined dashboards + alerts). Adds a cascade-alerts warning section (does NOT block delete) so the user sees what will be removed.
- `hooks/api/useKPIs.ts` — added `useKPIConsumers` SWR hook + `KPIConsumersResponse` / `KPIConsumerAlert` types.
- `types/metrics.ts` — extended `MetricConsumersResponse` with required `alerts: MetricConsumerAlert[]`.

### Tests

**Frontend (added in M4):** 18 new tests, all passing.
- `components/alerts/__tests__/AlertsTable.test.tsx` — 12 tests:
  - empty state delegation, row rendering (name/condition/frequency), Firing badge on `most_recent_fired`, dimmed disabled rows, click-to-sort by Name with order toggling, client-side last-fire filter applies via parent rerender, switch click → `onToggle`, Alert log menu item → `onOpenLog`, source subtitle is `next/link` for Metric/KPI and plain text for Standalone, empty-state CTA visibility under create-permission flag, Firing empty-state copy.
- `components/alerts/__tests__/AlertLogModal.test.tsx` — 5 tests:
  - modal title + row content, expand-row shows message + email + slack + SQL toggle, Partial badge for mixed delivery outcomes, Not-fired badge for non-firing evaluations, empty-message when no logs exist.
- `components/metrics/__tests__/consumer-links.test.tsx` — +1 test (alert count rendering + link to `/alerts`), plus fixture updates to include `alerts: []`.

**Test totals at the end of M4:** Backend alert suite still **95 passing** (unchanged from M3). Frontend alert suite **41 passing** (M2 16 + M3 7 + M4 18). Full webapp_v2 suite 1345 passing (3 pre-existing failures unrelated — `DataPreview`, `pipeline-run-history`).

### Validation done

- ✅ Frontend `tsc --noEmit` clean for all new + modified alert files (pre-existing errors in `kpi-detail-drawer.tsx`/`kpi-card.tsx`/`kpi-chart-element.tsx`/`kpi-page.tsx` unchanged — not touched in M4)
- ✅ `prettier --write` applied to all new + modified files
- ✅ `jest` 41/41 alert + consumer-link tests pass; full suite 1345 passing (no new regressions)

### Decisions captured during execution

- **Sort and last-fire filter are client-side per page.** The backend list endpoint orders by `-updated_at` and supports `is_active` / `frequency` filters but no `sort_by` or `last_fire_within_hours`. M4 fetches up to 100 rows and sorts/filters in the table component. v1 scale (~50 alerts per org) makes this safe; if the dataset grows we can push these to the backend without touching the table API.
- **Source subtitle navigation.** The spec requires KPI alerts → KPI annotation page, Metric alerts → Metric edit page. Existing routes are `/kpis?open={id}` (KPI drawer) and `/metrics?highlight={id}` (highlighted row) — both already used by other parts of the app. Standalone alerts have no destination per spec — plain text only.
- **Delivery status badge derived client-side from `deliveries`.** Resolves plan §8 open question #7. Backend returns `fired` + `deliveries` and the modal computes Success / Partial / Failed / Not-fired in `deliveryStatusFor()`. No backend schema change needed for v1.
- **Metric/KPI delete dialog: cascade vs block.** Backend cascades Alert on Metric/KPI delete (per plan §8 #8). M4 splits the metric delete dialog's `hasDeleteConsumers` into `hasBlockingConsumers` (charts + kpis, still blocks) and `hasCascadeAlerts` (just warns). KPI delete dialog reuses the same pattern with the new `useKPIConsumers` hook.
- **`ConsumerLinks` "Alerts" group links to `/alerts` (no per-alert deep link).** v1's `/alerts` route doesn't accept `?highlight=` or `?open=`; opening the alert wizard requires the wizard modal which lives inside the page. The popover shows alert names; clicking takes the user to the listing where they can find the row.
- **Firing tab filter UI.** The Firing tab inherits filter state from All tab but locks `enabled` to `enabled` (always shows only active alerts since the backend filter already excludes disabled — but we also hide the Enabled filter affordance to avoid confusion). Sort / last-fire / frequency controls remain functional.

### Out of M4 scope (per plan)

- Permission gating polish (tooltip copy, hidden vs disabled controls per role) — M5.
- Nav unhide (`PRODUCTION_HIDDEN_ITEMS` in `main-layout.tsx`) — M5.
- Spec validation (`/engineering/validate-spec`) — M5.
- Calculated expression mode + filter UI inside the Standalone wizard — deferred.

---

## Milestone 5 — Polish (role gating, toasts, empty states, unhide nav)

**Status:** ✅ COMPLETE — 2026-06-11

### What shipped

**Frontend (`webapp_v2/` on `feature/alerts-prod`):**
- `components/main-layout.tsx` — removed `'Alerts'` from `PRODUCTION_HIDDEN_ITEMS` so the nav item is visible in production. List is now empty (typed as `string[]`).
- `components/kpis/kpi-detail-drawer.tsx` — imported `ALERT_PERMISSIONS` + `useUserPermissions`; the BellRing "Create alert" icon button only renders when the user has `can_create_alerts`.
- `components/metrics/metrics-library.tsx` — same gating on the row 3-dot menu's "Create alert" item (also fixed casing: was "Create Alert" → now "Create alert" per design.md item 9).
- `components/alerts/AlertsTable.tsx` — wrapped the row Switch in a span with a `title=` hint when `canEdit` is false; added `title=` hints to the Edit and Delete dropdown items when the user lacks the corresponding permission. (`AlertsPage` already gates the top-right "Create alert" CTA behind `canCreate`.)
- `components/alerts/AlertWizardModal.tsx` — replaced generic CRUD toasts with spec strings:
  - Create success: `"Alert created. It will run on its next scheduled time."`
  - Edit success: `"Alert updated."`
  - Save failure: `"Couldn't save the alert. <reason>."` (uses backend `detail`/`message`/`error` when available, falls back to `"try again"`).
  - Switched import from `lib/toast` helpers to `sonner`'s `toast` directly for verbatim copy.
- `app/alerts/page.tsx` — same swap to `sonner.toast`:
  - Toggle success: `"Alert enabled."` / `"Alert disabled."`
  - Toggle failure: `"Couldn't update the alert. The row was reverted."`
  - Delete success: `"Alert deleted."`
  - Delete failure: `"Couldn't delete the alert. <reason>."`

**Backend:**
- No code changes. Permission slugs (`can_view_alerts`, `can_create_alerts`, `can_edit_alerts`, `can_delete_alerts`) already exist with mappings to Super User / Account Manager / Pipeline Manager / Analyst (Guest excluded) — seeded in M1. Final role mapping confirmed acceptable; no migration adjustment required.

### Tests

**Frontend (added in M5):** 2 new tests, all passing.
- `components/alerts/__tests__/AlertsTable.test.tsx` — added permission-gating subset:
  - Switch is disabled when `canEdit=false`.
  - Delete dropdown item has `aria-disabled="true"` when `canDelete=false`.

**Test totals at the end of M5:** Backend alert suite still **95 passing** (unchanged from M3). Frontend alert + consumer-links suite **43 passing** (M2 16 + M3 7 + M4 18 + M5 2). Full webapp_v2 suite continues to pass aside from the same pre-existing unrelated failures.

### Validation done

- ✅ `tsc --noEmit` clean for all new + modified alert files; pre-existing errors in `kpi-detail-drawer.tsx` / `main-layout.tsx` unchanged (line numbers shifted only).
- ✅ `prettier --write` applied to all M5 touched files.
- ✅ `jest` runs cleanly for all alert suites (43 passing).

### Decisions captured during execution

- **Permission gating is hide-vs-disable per spec Story 9.** "Create alert" CTAs disappear entirely when the user lacks `can_create_alerts` (matches "Users without the create role do not see Create Alert entry points"). Edit / Delete row actions stay visible but become disabled with a `title=` tooltip explaining why — keeps the UI predictable for users who occasionally lose/gain permissions across orgs. Enable/disable toggle is treated like Edit (disabled + tooltip).
- **Tooltip via native `title=` attribute, not Radix `<Tooltip>`.** Native title hint shows on hover with no extra render cost. v1 acceptable; if Pasha asks for branded tooltips in v2 we can wrap with the existing `<Tooltip>` primitive.
- **Toast copy uses `sonner` directly, not `lib/toast` helpers.** `lib/toast` injects generic strings like "Alert created successfully!" and "Failed to create alert"; the spec requires verbatim wording like "Alert created. It will run on its next scheduled time." Bypassing the helper keeps the copy exact and centralized at the call site.
- **Toggle error reverts via SWR mutate, message is generic** (`"Couldn't update the alert. The row was reverted."`). The handler calls `mutateBoth()` only on success; on failure the optimistic state stays out of sync until the next fetch — but since the Switch is `checked={a.is_active}` from server data, the UI immediately snaps back to the previous state when the SWR cache stays unchanged. No need for explicit revert logic.
- **design.md items 8, 11, 12 are already satisfied.** Item 8 (frequency rules) — `ScheduleField.tsx` already enforces Daily=time, Weekly=day+time, Monthly=DoM+time. Item 11 (`biiling` typo) — not present in webapp_v2 source. Item 12 ("Invalid username. Please check your email.") — never written into our codebase; `RecipientCombobox` rejects malformed emails silently (doesn't surface a user-facing error). If item 12 needs a visible message in v2 we can add one.
- **design.md item 10 (Metric row menu labels)** is a Figma-side fix; the implementation already shows "Edit Metric / Create KPI / Create alert / Delete" which is correct.

### Out of M5 scope (per plan)

- `scripts/recipes/alerts.yaml` screenshot recipe — deferred. Docs team can author once UX is settled.
- Final role → permission audit / migration cleanup — N/A; M1 seeds match the planned roles, no changes requested by Pratiksha.

---

## Notes for resumed sessions

- Backend worktree: `DDP_backend_alerts/` on branch `feature/alerts`.
- Frontend dir: `webapp_v2/` on branch `feature/alerts-prod` (no separate worktree).
- Spec deviation captured in [plan.md §8 Open Questions #8]: Metric/KPI delete cascades to alerts; spec text needs updating before merge.
- `Delivery status` badge (Story 6) — **resolved in M4**. Backend returns `fired` + `deliveries`; frontend `AlertLogModal` derives Success/Partial/Failed/Not-fired client-side. Mark plan §8 open question #7 as resolved before merge.
- `summary_status` is NOT stored on `alert_log` — derived in the UI as above.
- New endpoint added in M2 that's not in the plan: `GET /api/alerts/recipients/orgusers/`. The wizard's RecipientCombobox needs OrgUser pks but `/api/organizations/users` only returns User pks; this scoped, lightweight endpoint provides `orguser_id + email + name`. Document in spec/plan §3.5 before merge.
- M5 added: `GET /api/kpis/{id}/consumers/` is now consumed by the KPI delete dialog via `useKPIConsumers` (replaces the previous `useKPIDashboards`-only check). Make sure the API tests already cover this shape.
- All milestones M1–M5 ✅ COMPLETE. Next: `/engineering/validate-spec` + PR cleanup.
