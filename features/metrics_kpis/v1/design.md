# Metrics & KPIs v1 — UI Design

**Status:** Draft v2
**Spec:** [spec.md](./spec.md) · **Implementation notes:** [plan.md](./plan.md)
**Figma:** See `~/Dalgo/FIGMA.md` (product-wide) + `~/Metrics & KPI/FIGMA.md` (canvas map, component specs)

---

## What belongs in this document

This file answers **how each screen looks and behaves**:
- Screen layouts and wireframes
- UX rationale — why each design decision was made
- Interaction patterns, states, validation rules
- Accessible language and terminology choices

It does **not** contain: Figma component keys, RGB values, CSS class names, canvas coordinates, or code file names. Those live in FIGMA.md and plan.md respectively.

---

## Design Principles for This Feature

These were reached after UX review + NGO user testing (Priya). They govern every screen.

**1. Trust before action**
Metrics are only useful if users trust the number. Every screen that shows a computed value must show when it was last calculated and let users verify it before saving.

**2. Plain language throughout**
Replace every technical term with the friendliest accurate alternative. See the Terminology Map below. "Calculation type" not "Aggregation". "Higher is better" not "Direction: ascending".

**3. Cards for KPIs, tables for Metrics**
Metrics are structured, comparable data — tables work best. KPIs have rich visual content (value, target, sparkline, RAG badge) — cards let each one breathe.

**4. Status is always text + colour**
RAG badges always show a word ("On Track", "At Risk", "Off Track"). Never rely on colour alone. This is an accessibility requirement and also makes sense in screenshots, print, and low-vision contexts.

**5. Data freshness everywhere**
Every value shown to a user must be accompanied by "Updated X ago" or "Data as of [date]". If data is older than 7 days, show an amber stale indicator.

---

## Terminology Map

Internal code terms → user-facing UI labels. Engineers use the left column in code; the right column appears on screen.

| Internal / Code | UI Label | Reason |
|-----------------|----------|--------|
| Metric | Metric *(subtitle: "A saved calculation you can reuse")* | Consistent with code |
| Dataset (schema.table) | Data Source | Users think "my beneficiary list", not "schema.table" |
| Column expression | Field or expression | Friendly for simple cases; "expression" signals power-user usage |
| Aggregation | Calculation type | Then use plain sub-labels (below) |
| `count` | Count — how many rows | — |
| `sum` | Total — add up all values | — |
| `avg` | Average — mean of all values | — |
| `min` | Lowest value | — |
| `max` | Highest value | — |
| `count_distinct` | Count unique — how many different values | — |
| MetricMode.SIMPLE | Simple | — |
| MetricMode.SQL | SQL | Keep — users understand this |
| RAG status | Status: On Track / At Risk / Off Track | — |
| Time grain | Trend frequency *(show trend by: monthly / quarterly)* | — |
| Trend periods | Trend duration *(show last X months)* | — |
| KPI | KPI *(subtitle: "Track progress toward your goals")* | Keep — users know this term |
| Direction | Higher is better / Lower is better | — |
| Threshold | Status threshold *(with concrete value examples)* | — |
| Input / Output / Outcome / Impact | Same — but always with a one-line description | Logframe terms need explaining |

---

## Screen 1 — Metrics Library (`/metrics`)

**Purpose:** Browse, search, and manage saved metrics. Matches the visual pattern of the existing Charts page.

**Layout:** Fixed header + scrollable table + pagination footer.

```
┌──────────────────────────────────────────────────────────────┐
│ Fixed Header                                                 │
│                                                              │
│  Metrics                              [+ CREATE METRIC]      │
│  Saved calculations you can reuse across charts and KPIs     │
│                                                              │
│  [Search by name...]  [Data Source ▼]                        │
├──────────────────────────────────────────────────────────────┤
│ Scrollable Table                                             │
│                                                              │
│  Name          │ Mode   │ Data Source   │ Definition │ Value │
│  ──────────────┼────────┼───────────────┼────────────┼────── │
│  Total Active  │ Simple │ programs.     │ COUNT      │ 2,847 │
│  Beneficiaries │        │ beneficiaries │ DISTINCT…  │       │
│                │        │               │            │ 3 chr │
│                │        │               │            │ 1 kpi │
│  ──────────────┼────────┼───────────────┼────────────┼────── │
│  Revenue Per   │  SQL   │ finance.      │ SUM(rev)/  │ 2,340 │
│  Beneficiary   │        │ transactions  │ COUNT(DIS… │       │
├──────────────────────────────────────────────────────────────┤
│ Footer                                                       │
│  1–10 of 24                    [Show: 10 ▼]  [< 1 of 3 >]  │
└──────────────────────────────────────────────────────────────┘
```

**Table columns:**

| Column | Width | What it shows |
|--------|-------|---------------|
| Name | ~25% | Metric name (prominent) + description on second line (muted, truncated) |
| Mode | ~10% | Badge: Simple (green outline) or SQL (neutral/grey outline) |
| Data Source | ~20% | `schema.table` in monospace style |
| Definition | ~20% | Simple: `AGG(column)` truncated. SQL: first line truncated |
| Current Value | ~10% | Computed value, prominently weighted. Skeleton while loading |
| Used By | ~10% | "3 charts · 1 KPI" in muted style. "—" if unused |
| Last Updated | auto | Time since last calculation ("2 hours ago") |
| Actions | ~5% | ⋮ dropdown |

**Row action menu:**
- Edit
- Create KPI from this metric *(pre-fills KPI form)*
- Delete *(blocked if referenced — shows consumer list before allowing)*

**Why table, not cards:** Metrics are structured, comparable data. Tables are scannable and sortable. Cards are for KPIs which have richer visual content.

**Why "Used By" column:** Blast-radius awareness at a glance. Users understand the cost of editing before they click.

**Why "Current Value" column:** Immediate verification that the metric works. Builds trust in newly created metrics.

**States:**

- **Empty:** Illustration + "No metrics yet" + "Create your first metric to start building reusable calculations" + CREATE METRIC button
- **Loading:** Skeleton table rows (6 rows)
- **No search results:** "No metrics found for '[query]'" + suggestion to adjust filters
- **Delete blocked:** Dialog listing all consumers: "This metric is used by: [list]. Remove those references first."

---

## Screen 2 — Create / Edit Metric (Dialog)

**Purpose:** Define a saved metric. Simple enough for a single dialog — no wizard needed.

**Layout:** Modal dialog, medium width. Single scrollable form.

```
┌────────────────────────────────────────────┐
│ Create Metric                          [×] │
│ Define a calculation once and reuse it     │
│                                            │
│ Name *                                     │
│ [e.g., Active Beneficiaries            ]   │
│                                            │
│ Description                                │
│ [What does this calculation represent? ]   │
│                                            │
│ Data Source *                              │
│ [Select a data source...               ▼]  │
│                                            │
│ ── Mode ──────────────────────────────── │
│ ( Simple )  ( SQL )                        │
│                                            │
│ ┌─ Simple mode ──────────────────────────┐ │
│ │ Calculation type *                     │ │
│ │ [Count — how many rows            ▼]   │ │
│ │                                        │ │
│ │ Field or expression                    │ │
│ │ [beneficiary_id                    ]   │ │
│ │  Available columns: beneficiary_id     │ │
│ │  · age · district (or type freely)     │ │
│ └────────────────────────────────────────┘ │
│                                            │
│ ┌─ Preview ──────────────────────────────┐ │
│ │        2,847                           │ │
│ │ ✓ Query validated                      │ │
│ └────────────────────────────────────────┘ │
│                                            │
│              [Cancel]  [Save Metric]       │
└────────────────────────────────────────────┘
```

**SQL mode (when SQL selected):**

```
│ ┌─ SQL mode ─────────────────────────────┐ │
│ │ SQL Expression *                       │ │
│ │ ┌─────────────────────────────────────┐│ │
│ │ │ SUM(revenue) /                      ││ │
│ │ │ COUNT(DISTINCT beneficiary_id)      ││ │
│ │ └─────────────────────────────────────┘│ │
│ │ Must return a single numeric value.    │ │
│ │ Example: SUM(col), COUNT(*),           │ │
│ │ SUM(a) / NULLIF(SUM(b), 0)             │ │
│ │                     [Test Query]       │ │
│ └────────────────────────────────────────┘ │
```

**Field / expression input (Simple mode):**
- Combobox: type to search columns from warehouse metadata, but also accepts free-text expressions
- For COUNT: field is optional (empty = COUNT(*))
- For SUM / AVG / MIN / MAX: field is required
- Helper text: "Enter a column name or expression (e.g. `col_a - col_b`)"

**Preview panel:**
- Always visible, auto-runs on field changes (debounced)
- Shows the computed value or a validation error
- "✓ Query validated" when query runs successfully
- "✗ Error: column 'xyz' does not exist" on failure
- For SQL mode: only runs after "Test Query" is tapped

**Why single dialog, not wizard:** Metric has 4–5 fields depending on mode. A wizard adds navigation overhead without benefit. Everything stays visible.

**Why mode as radio buttons:** Simple and SQL are clearly distinct paths. Switching modes clears mode-specific fields — with a confirmation prompt if data was already entered.

**Why "Test Query" only in SQL mode:** Simple mode auto-validates on every change. SQL mode can be long — validate explicitly rather than on every keystroke.

**Validation:**
- Name: required, unique per org (inline error on blur)
- Data source: required
- Simple mode: calculation type required, field required for non-COUNT
- SQL mode: expression required, must return single numeric value
- On Save: runs a final validation query. If it fails, the error shows in the preview panel — dialog stays open for correction.

**States:**
- **Saving:** Button shows spinner + "Validating…", dialog not closeable. On success: toast "[Name] saved", dialog closes, list refreshes.
- **Validation error:** Preview panel shows error. Save button stays enabled for retry.
- **Edit mode:** Title reads "Edit Metric". If metric has consumers, show amber warning above Save: "Changes will affect 3 charts and 1 KPI."
- **Mode switch with data:** Confirmation: "Switching modes will clear your current definition. Continue?"

---

## Screen 3 — KPI Page (`/kpis`)

**Purpose:** The leadership view. Scannable at-a-glance status of all goals. The highest-value screen in this feature.

**Layout:** Fixed header + scrollable card grid.

```
┌──────────────────────────────────────────────────────────────┐
│ Fixed Header                                                 │
│  KPIs                                      [+ CREATE KPI]    │
│  Track progress toward your goals                            │
│                                                              │
│  [Search KPIs...]  [Program ▼]  [Type ▼]  [Status ▼]        │
├──────────────────────────────────────────────────────────────┤
│ Scrollable Card Grid (3 columns at full width)               │
│                                                              │
│  ┌──────────────────────┐  ┌──────────────────────┐         │
│  │ Girls Enrolled  On   │  │ Dropout Rate     At  │  ...    │
│  │                 Track│  │                 Risk │         │
│  │ [education][output]  │  │ [health][outcome]    │         │
│  │                      │  │                      │         │
│  │      2,847           │  │      3.2%            │         │
│  │ Target: 3,000 · 95%  │  │ Target: 2.0% · 160%  │         │
│  │                      │  │                      │         │
│  │  ╱╲  ╱╲  ╱           │  │  ╱╲  ╱╲╱             │         │
│  │ ╱  ╲╱  ╲╱            │  │ ╱  ╲╱                │         │
│  │ Jan  Apr  Jul  Oct   │  │ Q1  Q2  Q3  Q4       │         │
│  │                      │  │                      │         │
│  │ ↑ +8.3%  2 hrs ago   │  │ ↓ +60%  1 day ago   │         │
│  └──────────────────────┘  └──────────────────────┘         │
└──────────────────────────────────────────────────────────────┘
```

**KPI card anatomy:**

```
┌────────────────────────────────────────────┐
│ Girls Enrolled    [On Track]  🔔  [⋮]      │ ← name + RAG badge + alerts dot + actions
│ [education]  [output]                      │ ← program tags + type tag
│                                            │
│         2,847                              │ ← current value (very large)
│ Target: 3,000 · 95% achieved               │ ← target + % to goal
│                                            │
│ ─────────────────────────────────────────  │
│ Last 12 months                  ↑ +8.3%   │ ← trend label + change
│                                            │
│  ╱╲    ╱╲  ╱                               │ ← sparkline (60px tall)
│ ╱  ╲╱╱  ╲╱                                │   with X-axis labels
│ Jan    Apr    Jul    Oct                   │
│                                            │
│ ─────────────────────────────────────────  │
│ Updated 2 hours ago                        │ ← data freshness
└────────────────────────────────────────────┘
```

**Linked-alerts indicator (🔔):** A small teal dot appears between the RAG badge and the ⋮ menu when one or more alerts are linked to this KPI. It shows only that alerts exist — not their count or firing state. Clicking it does nothing on the card; full alert detail is inside the drawer. Cards with no alerts show no dot.

**RAG badge states:**

| Status | Label | Visual treatment |
|--------|-------|-----------------|
| On Track | "On Track" | Green badge (text + light green background) |
| At Risk | "At Risk" | Amber badge |
| Off Track | "Off Track" | Red badge |
| No Target | "No Target" | Neutral/muted badge |

**Change indicator:**
```
↑ +8.3% vs last period   ← positive: green + up arrow
↓ −2.1% vs last period   ← negative: red + down arrow
  — vs last period        ← no change: muted, no arrow
```
Note: for "lower is better" KPIs (e.g. Dropout Rate), a decrease is positive — the arrow and colour should reflect whether the change is *good*, not just whether the number went up or down.

**Sparkline spec:**
- Smooth line chart with area fill
- Target shown as dashed horizontal line
- X-axis: 3–4 labels spaced evenly (first, middle-ish, last)
- Labels formatted by time grain: "Jan", "Q1", "Week 12", "2025"
- Height: 60px in card

**Stale data:** If data is older than 7 days, show a small amber dot in the top-right corner of the card.

**Why cards, not table:** KPIs have rich visual content — sparkline, RAG badge, target %, change indicator. A table can't fit this without becoming unreadable. Cards let each KPI stand alone.

**Why the current value is very large text:** Leadership users glance at this page. The number should be readable from across the room without zooming in.

**Card actions (⋮ menu):**
- Edit KPI
- Delete KPI *(blocked if any alert is linked — user sees: "This KPI has linked alerts: [list]. Remove those alerts first." If no alerts are linked: confirmation dialog "This will remove the KPI from all dashboards. Continue?")*

**Filter behaviour:** All filters stack with AND logic. "Clear all" appears when any filter is active.

**States:**
- **Empty:** Icon + "No KPIs yet. Create your first KPI to start tracking progress." + CREATE KPI button
- **Loading:** 6 skeleton cards, each with a value placeholder + sparkline rectangle
- **No search results:** "No KPIs found" + suggestion to adjust filters
- **Value load error:** Card shows "Couldn't load value" + Retry link in place of the value

---

## Screen 4 — Create / Edit KPI (Wizard Dialog)

**Purpose:** Configure a KPI on top of a saved metric. Wizard is justified here — KPI has more fields than a Metric, with dependencies between steps.

**Layout:** Modal dialog, wider than Create Metric. 4 steps with step indicator.

---

**Step 1 — Pick a metric**

```
Which metric do you want to track?

[Search your metrics...                        ]

┌───────────────────────────────────────────────┐
│ | Girls Enrolled - Secondary - Rajasthan      │ ← selected (left border highlight)
│   Count unique beneficiary IDs                │
│   [programs.beneficiaries] · Value: 1,247     │
├───────────────────────────────────────────────┤
│   Total Training Hours                        │
│   Sum of training_hours                       │
│   [programs.training] · Value: 8,420          │
├───────────────────────────────────────────────┤
│   Revenue Per Beneficiary    [SQL]            │
│   finance.transactions · Value: 2,340         │
└───────────────────────────────────────────────┘

[+ Create a new metric instead]
```

Why a searchable list, not a dropdown: organisations will have 20+ metrics. Dropdowns become unusable at that scale. Each row also shows the current value so users pick the right one confidently.

---

**Step 2 — Set target and status thresholds**

```
KPI display name
[Girls Enrolled in Secondary Ed              ]
(Leave blank to use the metric name)

Target value              Direction
[1500              ]      [Higher is better ▼]

┌─ Status Thresholds ──────────────────────────┐
│ When is this KPI on track?                   │
│                                              │
│ On Track    [100]% or better                 │
│ At Risk     [80 ]% to 99%                    │
│ Off Track   below 80%                        │
│                                              │
│ With target 1,500:                           │
│ [≥1,500 On Track] [1,200–1,499 At Risk]      │
│ [<1,200 Off Track]                           │
└──────────────────────────────────────────────┘
(No target? Leave blank to track trend only.)
```

Smart defaults: On Track = 100%, At Risk = 80% (for "higher is better"). When direction switches to "lower is better", amber threshold auto-adjusts to 120%.

The concrete value examples ("≥1,500 = On Track") update in real time as the user types the target — this makes abstract percentages immediately understandable.

---

**Step 3 — Trend configuration**

```
Show trend by: *
[Monthly                              ▼]

How many periods to show?
[12         ]
(Show last 12 months in the trend chart)

Date field for trend *
[enrollment_date                      ▼]
(Which date field should be used to group by time?)

┌─ Preview ──────────────────────────────────┐
│ This KPI will show 12 monthly values       │
│ Example range: May 2025 → April 2026       │
└────────────────────────────────────────────┘
```

Default: Monthly, 12 periods — the most common NGO reporting cycle.

---

**Step 4 — Tags and summary**

```
Indicator type (optional)
[Output                               ▼]
  Input   — Resources invested (budget, staff, time)
  Output  — Activities completed (trainings, distributions)
  Outcome — Short-term changes (knowledge, behaviour)
  Impact  — Long-term effects (lives improved)

Program tags (optional)
[Type a tag and press Enter            ]
  [Education ×]  [Rajasthan ×]

┌─ Summary ──────────────────────────────────┐
│ Metric:    Girls Enrolled - Secondary      │
│ Target:    1,500 (higher is better)        │
│ On Track:  ≥1,500                          │
│ At Risk:   1,200–1,499                     │
│ Off Track: <1,200                          │
│ Trend:     12 monthly periods              │
│ Type:      Output                          │
│ Tags:      Education, Rajasthan            │
└────────────────────────────────────────────┘

                           [Back]  [Save KPI]
```

Indicator type descriptions are shown in the dropdown — logframe vocabulary is not universally understood and the descriptions teach while the user works.

**Validation:**
- Step 1: metric selection required to proceed
- Step 3: date field required (no trend without a time dimension)
- Step 2 thresholds: On Track % must be greater than At Risk %

---

**Edit KPI mode**

When editing an existing KPI the wizard opens at Step 2, not Step 1. The metric is locked and shown as a read-only summary above the form:

```
┌─ Metric (locked) ──────────────────────────┐
│ Girls Enrolled - Secondary - Rajasthan      │
│ Count unique · programs.beneficiaries       │
│ Current value: 2,847          [Change ▸]   │
└─────────────────────────────────────────────┘
```

- Steps 2, 3, and 4 are fully editable.
- "Change metric" link on the locked summary reopens Step 1 — user must confirm: *"Changing the metric will reset your target and thresholds. Continue?"*
- Title bar reads "Edit KPI" instead of "Create KPI".
- Save button reads "Save changes".
- Blast-radius warning: if the underlying metric has other consumers (charts, alerts), an amber banner appears at the top of the wizard: *"Editing the metric will also affect [N] charts and [N] alerts."* This is informational only and does not block saving.

---

## Screen 5 — KPI Detail Drawer

**Purpose:** Full detail for a single KPI. Trend chart, configuration summary, annotations timeline.

**Layout:** Sheet sliding in from the right, 600px wide. Sticky header, scrollable body.

```
┌──────────────────────────────────────────┐
│ Girls Enrolled       [On Track]     [⋮]  │ ← sticky header
│ [education]  [output]                    │
├──────────────────────────────────────────┤
│                                          │
│  ┌──────────┐  ┌──────────┐             │
│  │  2,847   │  │  3,000   │             │
│  │ Current  │  │  Target  │             │
│  └──────────┘  └──────────┘             │
│                                          │
│  ┌──────────┐  ┌──────────┐             │
│  │   95%    │  │  ↑ +8.3% │             │
│  │ Achieved │  │ vs last  │             │
│  └──────────┘  └──────────┘             │
│                                          │
│  Updated 2 hours ago                     │
│                                          │
│ ─ Trend ─────────── [Last 12 periods ▼] │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  Full line chart · 250px tall      │  │
│  │  Target as dashed horizontal line  │  │
│  │  Hover tooltip: period + value     │  │
│  └────────────────────────────────────┘  │
│  ── Actual   - - Target                  │
│                                          │
│ ─ How this KPI works ─────────────────── │
│  Based on:   Girls Enrolled - Secondary  │
│  Direction:  Higher is better            │
│  Frequency:  Monthly                     │
│  On Track:   ≥100%                       │
│  At Risk:    80–99%                      │
│  Off Track:  <80%                        │
│                                          │
│ ─ Annotations ────────────── [+ Add] ── │
│                                          │
│  Apr 2026  2,847                         │
│  ┌──────────────────────────────────┐    │
│  │ "Enrollment peaked after the     │    │
│  │ awareness campaign in March."    │    │
│  │                      — Priya     │    │
│  │                  Apr 15, 2026    │    │
│  └──────────────────────────────────┘    │
│                                          │
│  Jan 2026  2,510                         │
│  ┌──────────────────────────────────┐    │
│  │ Post-holiday dip, expected.      │    │
│  │                      — Noopur    │    │
│  └──────────────────────────────────┘    │
└──────────────────────────────────────────┘
```

**Trend chart spec:**
- Full line chart, 250px tall
- Actual values: solid line in brand teal
- Target: dashed grey horizontal line
- Hover tooltip: period name + exact value + RAG status at that point
- X-axis: all period labels, rotate if needed
- Y-axis: auto-scaled with target value always in view
- Legend below chart: "── Actual  - - Target"

**Period selector:** "Last 12 periods" / "Last 6" / "All time" dropdown on the trend section heading. This is session-only — it does not persist to the KPI's saved config. The card on the KPI page and the dashboard widget always render using the KPI's configured default, regardless of what the viewer selects in the drawer.

**"How this KPI works" section:** Plain-language config summary. Named to be non-technical. No jargon.

**Annotations timeline:**

Entries are in reverse chronological order (newest at top). Each entry shows: period label, value snapshot at that period, the note or quote, author name, and date added.

Two annotation types:

**Comment** — an internal note from a team member.
```
┌──────────────────────────────────────────┐
│  Apr 2026  ·  2,847  ·  +337 vs Mar      │ ← period + value + delta
│                                          │
│  Enrollment peaked after the awareness   │
│  campaign in March. School outreach +    │
│  community events drove the spike.       │
│                                          │
│  — Noopur  ·  Apr 15, 2026          ✎ 🗑 │ ← author + date + hover actions
└──────────────────────────────────────────┘
```

**Beneficiary Quote** — a direct quote from a beneficiary, with attribution.
```
┌──────────────────────────────────────────┐
│  Jan 2026  ·  2,510  ·  −110 vs Dec      │
│                                          │
│  " My daughter enrolled because she      │
│    finally had a school near our area." │
│                                          │
│  — Beneficiary, Rajasthan                │ ← attribution field (not author)
│    Added by Priya  ·  Jan 8, 2026   ✎ 🗑 │
└──────────────────────────────────────────┘
```

The period dropdown shows only the KPI's trailing periods (e.g. last 12 months for a monthly KPI). The value snapshot is auto-populated when the user selects a period and cannot be edited — it captures the actual KPI value at save time.

**Add annotation form** (inline at top of timeline when + Add is clicked):

```
┌─ Add annotation ─────────────────────────┐
│  Type   ( Comment )  ( Beneficiary Quote )│
│                                          │
│  Period *                                │
│  [Select a period...            ▼]       │
│                                          │
│  Value snapshot  (auto)                  │
│  [2,847 — Apr 2026]                      │
│                                          │
│  Note *                                  │
│  [                                    ]  │
│  [                                    ]  │
│                                          │
│  ← shown only for Beneficiary Quote:     │
│  Attribution                             │
│  [e.g. Beneficiary, Rajasthan         ]  │
│                                          │
│                   [Cancel]  [Save]       │
└──────────────────────────────────────────┘
```

The Attribution field appears only when "Beneficiary Quote" type is selected. It is free text — not linked to any beneficiary record.

**Annotation edit and delete:**

On hover, each annotation card shows a pencil (✎) and trash (🗑) icon in the top-right corner. These are visible to the author and to any user with edit permission on the KPI.

*Edit:* Clicking ✎ expands the annotation card into a pre-filled edit form inline. The period and value snapshot are locked (shown in a disabled/grey state) — only the note text (and attribution for quotes) can be changed. A teal "Editing annotation" label appears at the top of the form to distinguish it from the add form. Buttons: Cancel and Save changes.

```
┌─ Editing annotation ─────────────────────┐  ← teal label
│  Period (locked)     Value (locked)       │
│  [Apr 2026      🔒]  [2,847 (auto)     ]  │
│                                          │
│  Note *                                  │
│  [Enrollment peaked after the awareness ┐│
│   campaign in March...                  ]│
│                                          │
│                 [Cancel]  [Save changes] │
└──────────────────────────────────────────┘
```

*Delete:* Clicking 🗑 turns the annotation card red with an inline confirmation — no modal. The card shows: *"Delete this annotation? This cannot be undone."* with Cancel and Delete buttons. If the user cancels, the card returns to its normal state.

```
┌──────────────────────────────────────────┐  ← card turns red bg
│  Delete this annotation?                 │
│  This cannot be undone.                  │
│                                          │
│                    [Cancel]  [Delete]    │
└──────────────────────────────────────────┘
```

**Drawer actions (⋮ menu):**
- Edit KPI *(opens wizard in edit mode at Step 2)*
- Edit underlying metric *(shows blast-radius warning if metric has other consumers)*
- Delete KPI *(blocked if any alert is linked — same rule as card ⋮ menu)*

**States:**
- **Loading:** Skeletons for values grid, chart rectangle, config list
- **No trend data yet:** Message in chart area: "Not enough data for a trend yet. Values will appear as data accumulates."
- **Error:** AlertCircle + "Couldn't load KPI data" + Retry

---

## Screen 6 — MetricsSelector: Saved Metrics Tab

**Purpose:** Add a "Saved Metrics" tab to the existing MetricsSelector in the chart builder. The existing Ad-hoc tab is unchanged.

**Layout:** Embedded in chart builder sidebar. Two tabs replace the current single view.

```
Metrics
Choose what value to display in this chart

┌──────────────────────────────────────────┐
│ [Saved Metrics]  [Ad-hoc]                │
├──────────────────────────────────────────┤
│ [Search saved metrics...             ]   │
│                                          │
│  | Girls Enrolled                        │ ← selected
│    Count · beneficiary_id                │
│  ─────────────────────────────────────── │
│    Total Training Hours                  │
│    Sum · training_hours                  │
│  ─────────────────────────────────────── │
│    Revenue Per Beneficiary  [SQL]        │
│                                          │
│ [+ Create and save a new metric]         │
└──────────────────────────────────────────┘
```

**Saved Metrics tab behaviour:**
- Filtered to the current chart's selected dataset — only compatible metrics shown
- Search within the list (for orgs with 10–20+ metrics)
- "Create and save a new metric" link opens the metric creation dialog; on save, new metric is auto-selected
- SQL metrics show a "SQL" badge to distinguish them

**Ad-hoc tab:** Preserves the existing MetricsSelector UI exactly as-is.

**Why "Saved Metrics" tab first:** Encourages reuse. Ad-hoc is always available but not the default path.

**No renaming:** The component stays "MetricsSelector", the label stays "Metrics". No "Measure" or other terminology change.

---

## Screen 7 — KPI Dashboard Chart

**Purpose:** Compact KPI widget rendered inside a dashboard grid.

**Layout:** Card that adapts to its container size (3 sizes).

```
┌──────────────────────────────┐
│ Girls Enrolled   [On Track]  │
│                              │
│       2,847                  │
│  Target: 3,000 (95%)         │
│                              │
│  ╱╲  ╱╲  ╱                  │ ← sparkline (adapts to container size)
│ ╱  ╲╱  ╲╱                   │   target shown as dashed line
│ Jan   Apr   Jul   Oct        │
│                              │
│ ↑ +8.3%     Updated 2h ago   │
└──────────────────────────────┘
```

**Size-responsive rendering:**

| Container width | Value size | Show target % | Sparkline height | X-axis labels |
|----------------|-----------|---------------|-----------------|---------------|
| < 250px | Large | Yes (no %) | 30px | Hidden |
| 250–350px | Larger | Yes (with %) | 40px | 3 labels |
| > 350px | Very large | Yes (with %) | 60px | 4+ labels |

The RAG badge is always visible regardless of size — it's the most critical signal.

Clicking the chart opens the KPI Detail Drawer.

**States:** Loading skeleton; error: "Couldn't load" + Retry; stale (>7 days): amber dot top-right.

---

## Screen 8 — Component Selector Modal (Updated)

**Purpose:** Add a "KPIs" tab to the existing chart-selector-modal so users can add KPI charts to dashboards.

**Layout:** Existing dialog gains a two-tab structure: "Charts" and "KPIs".

```
┌──────────────────────────────────────────────┐
│ Add Component                            [×] │
│ Choose a chart or KPI to add                 │
│  [Charts]  [KPIs]                            │
├──────────────────────────────────────────────┤
│ [Search KPIs...                          ]   │
│                                              │
│ ┌───────────┐ ┌───────────┐ ┌───────────┐   │
│ │ Girls     │ │ Dropout   │ │ Training  │   │
│ │ Enrolled  │ │ Rate      │ │ Hours     │   │
│ │ [On Track]│ │ [At Risk] │ │ [On Track]│   │
│ │ 2,847     │ │ 3.2%      │ │ 8,420     │   │
│ │ ╱╲  ╱╲   │ │ ╲╱  ╲╱   │ │ ╱╱╱╱     │   │
│ └───────────┘ └───────────┘ └───────────┘   │
└──────────────────────────────────────────────┘
```

Preview cards match the dashboard chart layout so users see exactly what they're adding.

Clicking a card adds the KPI chart to the dashboard and closes the modal.

**Empty state:** "No KPIs created yet" + link to create one on the KPI page.

---

## User Flows

Step-by-step sequences showing how users move through the feature. Each step describes what the user does and what the UI does in response.

---

### Flow 1 — Browse and search metrics

1. User navigates to `/metrics` → page loads with 6 skeleton rows
2. Rows fill in with Name, Mode badge, Data Source, Definition, Value, Used By, Last Updated
3. User types in the search field → table filters live (debounced)
4. User selects a Data Source from the filter dropdown → table narrows further (AND logic with search)
5. No results match → "No metrics found for '[query]'" message + suggestion to adjust filters
6. User clicks ⋮ on any row → dropdown shows: Edit / Create KPI from this metric / Delete

---

### Flow 2 — Create a metric

1. User clicks + Create Metric → modal opens, title "Create Metric"
2. User types a name → validated on blur (required, must be unique per org)
3. User selects a Data Source from the dropdown
4. User picks mode: Simple or SQL
   - **Simple:** selects Calculation type → types or picks a field → preview panel auto-runs and shows the computed value
   - **SQL:** types a SQL expression → clicks Test Query → preview runs and shows the result or an error
5. User clicks Save Metric → button shows spinner + "Validating…", dialog locks (cannot be closed)
6. On success → toast "[Name] saved", dialog closes, metric appears at top of list
7. On failure → error shown in preview panel, dialog stays open for correction

---

### Flow 3 — Edit a metric

1. User clicks ⋮ on a metric row → Edit → dialog opens, title "Edit Metric", fields pre-filled
2. If the metric has consumers → amber warning: "Changes will affect [N] charts and [N] KPIs"
3. User edits fields → preview updates in real time
4. If user switches mode (Simple ↔ SQL) while fields are filled → confirmation: "Switching modes will clear your current definition. Continue?"
5. Save flow is the same as Create

---

### Flow 4 — Delete a metric

1. User clicks ⋮ → Delete
2. If the metric has no consumers → confirmation dialog → metric deleted, row removed
3. If the metric has consumers → blocked: "This metric is used by: [list]. Remove those references first." — no delete option

---

### Flow 5 — Browse KPIs

1. User navigates to `/kpis` → 6 skeleton cards appear
2. Cards load with name, RAG badge, value, target, % achieved, sparkline, updated time
3. If any single card's value fails → "Couldn't load value" + Retry shown inside that card only (other cards unaffected)
4. If any card's data is older than 7 days → amber stale dot appears top-right of that card
5. User types in search or picks a Program / Type / Status filter → grid narrows, filters stack with AND logic
6. Any filter is active → "Clear all" link appears next to the filters
7. No results match → "No KPIs found" + suggestion to adjust filters
8. No KPIs exist at all → empty state: illustration + "No KPIs yet. Create your first KPI to start tracking progress." + Create KPI button

---

### Flow 6 — Create a KPI (4-step wizard)

**Step 1 — Pick a metric**
1. User clicks + Create KPI → wizard dialog opens at Step 1
2. User sees a searchable list of metrics, each showing name, definition, and current value
3. User searches if needed, clicks a row → row highlights with a teal left border
4. Next button is enabled only after a metric is selected
5. If no metrics exist → "Create a new metric instead" link opens the Create Metric dialog; on save, the new metric is auto-selected and the wizard resumes

**Step 2 — Target and thresholds**
1. User optionally types a KPI display name (defaults to the metric name if left blank)
2. User enters a target value and picks Direction (Higher is better / Lower is better)
3. On Track and At Risk % thresholds are shown — defaults: 100% and 80% for "higher is better"
4. If Direction switches to "lower is better" → At Risk threshold auto-adjusts to 120%
5. Concrete value examples update in real time as user types the target: "≥1,500 = On Track"
6. If On Track % ≤ At Risk % → inline error, Next blocked until resolved

**Step 3 — Trend configuration**
1. User picks time grain (Monthly / Quarterly / Weekly)
2. User sets number of periods (default 12)
3. User selects the date field from a dropdown (required — blocks Next if empty)
4. Preview text updates in real time: "This KPI will show 12 monthly values. Example range: May 2025 → Apr 2026"

**Step 4 — Tags and summary**
1. User picks an Indicator Type (Input / Output / Outcome / Impact) — each shown with a one-line description
2. User types program tags and presses Enter to add each as a removable pill
3. Full summary panel shows all configuration in plain language
4. User clicks Save KPI → wizard closes, new KPI card appears in the grid

---

### Flow 7 — Open KPI detail

1. User clicks anywhere on a KPI card → drawer slides in from the right (600px)
2. Drawer loads → skeletons for values grid, trend chart, config section
3. Data arrives → 4 stat tiles (Current, Target, % Achieved, vs Last), full trend chart, "How this KPI works" config summary, annotations timeline
4. User changes the period selector (Last 6 / Last 12 / All time) → trend chart updates; the KPI card and dashboard widget are unaffected
5. Not enough historical data → message in chart area: "Not enough data for a trend yet. Values will appear as data accumulates."

---

### Flow 8 — Add an annotation

1. User clicks + Add in the Annotations section → inline form appears at top of the timeline
2. User picks type: Comment or Beneficiary Quote
3. User selects a period from the dropdown → value snapshot auto-populates (read-only)
4. User types the note (and attribution text for Beneficiary Quote type)
5. User clicks Save → annotation appears at top of the timeline, form closes
6. Multiple annotations for the same period are allowed

---

### Flow 9 — Edit an annotation

1. User hovers over an annotation card → pencil (✎) and trash (🗑) icons appear top-right
2. User clicks ✎ → card expands into a pre-filled edit form; period and value snapshot are locked
3. User edits the note text (and attribution if applicable)
4. User clicks Save changes → card collapses back to display view with updated content
5. User clicks Cancel → card returns to its previous state with no changes

---

### Flow 10 — Delete an annotation

1. User hovers over an annotation card → trash (🗑) icon appears
2. User clicks 🗑 → card turns red inline with: "Delete this annotation? This cannot be undone." + Cancel / Delete
3. User clicks Delete → annotation is removed, adjacent cards close the gap
4. User clicks Cancel → card returns to normal state

---

### Flow 11 — Edit a KPI

1. User opens ⋮ on a card or in the drawer → Edit KPI
2. Wizard opens at Step 2; metric shown as a locked read-only summary at top
3. User edits name, target, thresholds, trend config, or tags across Steps 2–4
4. To change the metric: user clicks "Change metric" link → confirmation prompt → Step 1 reopens
5. Save changes → wizard closes, card and drawer update with new values

---

### Flow 12 — Delete a KPI

1. User opens ⋮ on a card or in the drawer → Delete KPI
2. If alerts are linked → blocked: "This KPI has linked alerts: [list]. Remove those alerts first."
3. If no alerts linked → confirmation: "This will remove the KPI from all dashboards. Continue?"
4. User confirms → KPI removed, card disappears from grid, drawer closes if open

---

### Flow 13 — Add a KPI to a dashboard

1. In the dashboard builder, user opens Add Component → clicks KPIs tab
2. User sees preview cards of all KPIs (name, RAG badge, current value, sparkline)
3. User clicks a card → KPI widget added to the dashboard at a default size, modal closes
4. User resizes or repositions the widget on the canvas like any other component
5. Widget renders at the appropriate responsive size (3 breakpoints by container width)
6. User clicks the widget on the dashboard → KPI Detail Drawer opens

---

## Cross-Cutting Patterns

### Data freshness
Every computed value on screen must show when it was last calculated:
- Standard: "Updated [time] ago"
- If older than 7 days: amber stale indicator alongside the timestamp
- Never show a value without its freshness indicator

### Loading
| Context | Pattern |
|---------|---------|
| Full table | 6 skeleton rows |
| Card grid | 6 skeleton cards |
| Single value | Skeleton rectangle matching text size |
| Chart | Skeleton rectangle at chart height |
| Form submission | Spinner in button, button text changes to past-progressive ("Saving…") |

### Errors
| Context | Pattern |
|---------|---------|
| Required field | Inline red text below field on blur |
| Expression / SQL error | Error shown in preview panel (red border + message) |
| Save failure | Toast notification: "Couldn't save. Try again." |
| Load failure | Centred AlertCircle + short message + Retry button |
| Delete blocked | Dialog listing all consumers by name |

### Accessibility
- RAG badges: always text + colour, never colour alone
- Icon-only buttons: always have an accessible label
- Form inputs: always have visible label elements, required fields marked with *
- Trend charts: descriptive accessible label ("Girls Enrolled trend: increasing from 2,100 to 2,847 over 12 months")
- Mode toggle: radio button group with proper roles
- Minimum touch target: 44×44px on all interactive elements

---

*Paired with: [spec.md](./spec.md) · [plan.md](./plan.md) · [~/Dalgo/FIGMA.md](../../Dalgo/FIGMA.md) · [~/Metrics & KPI/FIGMA.md](./FIGMA.md)*
