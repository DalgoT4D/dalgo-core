# Alerts — v1 Design

**Companion to**: spec.md
**Figma file**: [Dalgo 2.0 — Alerts](https://www.figma.com/design/grz6hMemfrBGfHfJuhBCTu/Dalgo-2.0?node-id=846-5045)
**Last updated**: 2026-06-10

## Frames

| Surface | Story | Figma node IDs |
|---|---|---|
| KPI alert — Step 1 Define | Story 2 | 846:5836, 846:5910 (lower is better), 846:5984 (higher is better) |
| KPI alert — Step 2 Notify | Story 2 | 846:6097 |
| KPI alert — Step 3 Test | Story 2, 4 | 846:6173 (won't fire, SQL closed), 846:6219 (won't fire, SQL open), 846:6269 (will fire) |
| KPI source-page row menu | Story 2 | 846:6058 |
| Metric alert — Step 1 Define | Story 1 | 846:6319 |
| Metric alert — Step 2 Notify | Story 1 | 846:6383 |
| Metric alert — Step 3 Test | Story 1, 4 | 846:6458, 846:6505, 846:6555 |
| Metric source-page row menu | Story 1 | 846:6605 |
| Standalone alert — Step 1 Define (Simple) | Story 3 | 846:6935 |
| Standalone alert — Step 1 Define (Calculated) | Story 3 | 846:7787 |
| Standalone alert — Step 2 Notify | Story 3 | 846:7189 |
| Standalone alert — Step 3 Test | Story 3, 4 | 846:7409, 846:7596 |
| /alerts listing — default | Story 5 | 846:6781, 846:8034 |
| /alerts listing — Firing tab active | Story 5 | 846:8895 |
| /alerts listing — row tooltip | Story 5 | 846:6632 |
| /alerts listing — row action menu open | Story 5 | 846:8177, 846:9212 |
| /alerts listing — never-fired rows | Story 5 | 846:9107 |
| Edit alert (modal over listing) | Story 5, wizard | 846:8495 |
| Delete confirmation modal | Story 5 | 846:8726 |
| Alert log — Metric variant | Story 6 | 846:9334, 846:9517 (expanded) |
| Alert log — KPI variant | Story 6 | 846:9860 |
| Alert log — empty state | Story 6 | 846:9722 |
| Step 2 Notify — email validation error | Story 1, 2, 3 | 846:10042 |

## Design feedback / pushbacks

Items decided in spec review (2026-06-10) that the current Figma needs to be updated to match. Pasha to revise:

1. **KPI Step 1 Define — RAG bands are read-only, not editable.** The current frames look like the author defines the X/Y/Z percentage thresholds per alert. Spec model: bands come from the KPI itself; the alert author only multi-selects which RAG state(s) to fire on (1–2 of {Red, Amber, Green}). Update the Step 1 layout to show the bands as **read-only descriptive context** with a multi-select control underneath.
2. **Alert log is a modal, not a full page.** Frames 846:9334, 846:9517, 846:9860, 846:9722 are designed as full pages with the `/alerts` chrome behind them. Redesign as a modal opened over the listing.
3. **Tab labels.** Final: `All alerts` + `Firing` (sentence case on "alerts"). The `All Alerts | Firing | KPI Alerts | Metric Alerts | Custom Alerts` 5-tab variant and the `Configured | Firing` variant are dropped.
4. **No `Source` column.** The source entity name moves into the Alert name cell as a subtitle (KPI link, Metric link, or dataset name as plain text). Update the listing tables.
5. **Empty state for `/alerts` listing.** Currently undesigned. Add: headline *"No alerts yet"*, subtext *"Get notified when your Metrics, KPIs, or datasets cross a threshold you care about."*, primary `Create Alert` CTA, secondary `Go to Metrics` and `Go to KPIs` buttons.
6. **"Send test message" Slack button** is missing from every Step 2 Notify frame. Add the button next to the Slack webhook URL field with inline success/failure feedback ("Test message sent to Slack" on success; "Test message failed: HTTP <code>" on failure).
7. **Recipient picker distinction.** Current chips don't visually distinguish Dalgo users from external emails. Add visual differentiation (e.g. avatar for Dalgo users, envelope icon for external emails).
8. **Schedule field rules per frequency.** Current Step 1 shows `Daily + Monday 3:30pm` (daily shouldn't take a day). Field set: Daily = time only; Weekly = day-of-week + time; Monthly = day-of-month (1–28) + time. Hourly is dropped. UTC toggle is dropped (everything in browser local timezone).
9. **`cREATE aLERT` button typo** — render as `Create alert` (sentence case).
10. **Metric source-page row menu** (846:6605) shows `Edit KPI / Create KPI / Create Alert` — should be `Edit Metric / Create Metric / Create Alert`.
11. **Sidebar typo** `biiling` → `billing` across all frames.
12. **Validation copy** *"Invalid username. Please check your email."* (846:10042) → *"Invalid email address."*
13. **Tab/button label casing** — Dalgo uses sentence case: `All alerts` (not `All Alerts`), `Firing`, etc.
14. **Disabled alert row treatment** — Currently undesigned. Show as a dimmed row (muted gray text, off-state toggle).
15. **Role-gated states** — Currently undesigned. Hidden CTAs for users without create; disabled-with-tooltip controls for users without edit/delete.
16. **Delivery status & per-recipient breakdown in Alert log** — Currently the expanded row only shows the message and recipient chips. Add: summary `Delivery status` column on each fire row (Success/Partial/Failed); per-recipient status icons; failure reason inline.
17. **Toast notifications** — None currently designed. See spec.md § "Toast notifications" for the full list.
