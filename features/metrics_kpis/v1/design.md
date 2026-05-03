# Metrics & KPIs v1 — UI Design

**Status:** Draft v2
**Date:** 2026-04-22
**Spec:** [v1 spec](./spec.md) | [Implementation plan](./plan.md)
**Reviewed through:** UX design standards + NGO user perspective (Priya)

---

## Design Assessment (UX Expert)

The feature introduces 8 interconnected screens. Key findings:

**Critical**
- Metric creation uses a single dialog (not wizard) — the entity is simple enough (data source + mode + expression + name)
- KPI cards must render RAG status as **text + color** (not color-only) for accessibility — "On Track" not just a green dot
- MetricsSelector gets a "Saved Metrics" tab — no rename, no terminology change

**Important**
- KPI page is the highest-value screen — optimize for scan speed (large values, visible RAG badges, readable trendlines)
- Dashboard KPI chart must adapt to different grid sizes (small/medium/large) without breaking layout
- Metric creation needs live preview and validation query on save to build user confidence

**Nice-to-Have**
- "Turn into KPI" shortcut on metric rows (one-click promotion)
- Usage count on metric rows ("Used in 3 charts, 1 KPI") for blast-radius awareness

## User Assessment (NGO Perspective)

**Blocks Adoption**
- Technical jargon throughout: "Schema", "Aggregation", "RAG thresholds", "Time grain" — must be replaced with plain language
- No preview/verification step before saving metrics — users won't trust numbers they can't verify
- Missing data freshness indicators — every value needs a "Last updated" timestamp

**Confuses Users**
- SQL mode needs guidance — syntax hint, example, test button, clear error messages
- Column expression free-text input needs column suggestions to avoid blank-field anxiety
- RAG threshold percentages are abstract without concrete value examples

**Could Be Simpler**
- Metric type tags on KPIs (Input/Output/Outcome/Impact) need descriptions — not all NGO staff know logframe terminology
- Default time grain should be "Monthly" (most common NGO reporting cycle)
- Metric creation as a single dialog (not wizard) reduces cognitive overhead

## Combined Recommendations (Prioritized)

1. **Replace jargon everywhere** — Single highest-impact change for adoption
2. **Add live preview to metric creation** — Builds trust, catches errors early
3. **Show data freshness on every value** — "Data as of April 20, 2026"
4. **Simple dialog for metric creation** — Single dialog, not wizard
5. **Make KPI page scan-optimized** — Large values, visible badges, readable trendlines
6. **Smart defaults on all forms** — Monthly time grain, 12 trend periods, 100%/80% thresholds
7. **Accessible RAG badges** — Text labels + color, not color-only
8. **Column expression combobox** — Suggestions from warehouse metadata + free-text for expressions

---

## Terminology Map

Every technical term gets a user-facing replacement. Engineers use the left column in code; the right column appears in the UI.

| Code/Internal | UI Label | Why |
|---|---|---|
| Metric | Metric (with subtitle: "A saved calculation you can reuse") | Keep consistent across code and UI |
| Dataset (schema.table) | Data Source | Users think "my beneficiary list", not "schema.table" |
| Column expression | Field or expression | Friendly for simple cases; "expression" clarifies power-user usage |
| Aggregation | Calculation type | Then use friendly sub-labels (see below) |
| `count` | Count (how many rows) |  |
| `sum` | Total (add up all values) |  |
| `avg` | Average (mean of all values) |  |
| `min` | Lowest value |  |
| `max` | Highest value |  |
| `count_distinct` | Count unique (how many different values) |  |
| MetricMode.SIMPLE | Simple | Column expression + calculation type |
| MetricMode.SQL | SQL | For power users writing custom queries |
| RAG status | Status: On Track / At Risk / Off Track |  |
| Time grain | Trend frequency (show trend by: monthly/quarterly/etc.) |  |
| Trend periods | Trend duration (show last X months) |  |
| KPI | KPI (keep — but subtitle explains: "Track progress toward your goals") |  |
| Direction | "Higher is better" / "Lower is better" |  |
| Threshold | Status threshold (with concrete value examples) |  |

---

## Screen Designs

### Screen 1: Metrics Library (`/metrics`)

**Purpose:** Browse and manage saved metrics. Table list view matching the Charts page pattern.

**Layout:** Fixed header + scrollable table + pagination footer. Follows `charts/page.tsx` pattern.

```
┌─────────────────────────────────────────────────────────────┐
│ Fixed Header (flex-shrink-0, border-b, bg-background)       │
│                                                             │
│  Metrics                              [+ CREATE METRIC]     │
│  Saved calculations you can reuse across charts and KPIs    │
│                                                             │
│  [Search by name...]  [Data Source ▼]                       │
├─────────────────────────────────────────────────────────────┤
│ Scrollable Content (flex-1, overflow-y-auto)                │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Name          │ Mode   │ Data Source        │ Definition│ │
│ │               │        │                    │           │ │
│ │ Current Value │ Used By│ Last Updated       │     [⋮]  │ │
│ ├───────────────┼────────┼────────────────────┼───────────┤ │
│ │ Total Active  │ Simple │ programs.          │ COUNT     │ │
│ │ Beneficiaries │        │ beneficiaries      │ DISTINCT  │ │
│ │               │        │                    │ (benefi.. │ │
│ │ 2,847         │ 3 chr  │ 2 hours ago        │     [⋮]  │ │
│ │               │ 1 kpi  │                    │           │ │
│ ├───────────────┼────────┼────────────────────┼───────────┤ │
│ │ Revenue Per   │ SQL    │ finance.           │ SUM(rev)  │ │
│ │ Beneficiary   │        │ transactions       │ / COUNT(  │ │
│ │               │        │                    │ DISTINCT..│ │
│ │ 2,340         │ 1 chr  │ 1 day ago          │     [⋮]  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Footer (flex-shrink-0, border-t)                            │
│  1–10 of 24                    [10 ▼]  [< 1 of 3 >]       │
└─────────────────────────────────────────────────────────────┘
```

**Table Columns:**

| Column | Width | Content |
|--------|-------|---------|
| Name | 25% | Metric name (font-semibold) + description truncated to 1 line (text-sm muted) |
| Mode | 10% | Badge: `Simple` or `SQL` (outline variant) |
| Data Source | 20% | `schema.table` (text-sm monospace) |
| Definition | 20% | Simple: `AGG(column_expression)` truncated. SQL: first line of sql_expression truncated |
| Current Value | 10% | Computed value (font-semibold). Skeleton while loading |
| Used By | 10% | "3 charts, 1 KPI" (text-xs muted). "—" if unused |
| Last Updated | — | `formatDistanceToNow` (text-xs muted) |
| Actions | 5% | `[⋮]` dropdown menu |

**Row actions dropdown:**
- Edit
- Create KPI from this (pre-fills KPI form with this metric)
- Delete (blocked if referenced — shows consumer list in AlertDialog)

**Key decisions:**
- **Table over cards** — Metrics are structured data (name, mode, source, definition). Tables are scannable and sortable. Cards are reserved for KPIs which have rich visual content (RAG, sparkline).
- **Current value column** — Immediate verification that the metric works. Loaded lazily per-row or on hover to avoid N queries on page load.
- **"Used By" column** — Blast-radius awareness at a glance. Sourced from `/consumers/` endpoint.
- **Mode badge** — Distinguishes Simple vs SQL at a glance.

**States:**
- **Empty:** Centered Calculator icon (w-12 h-12 muted) + "No metrics yet" + "Create your first metric to start building reusable calculations." + [CREATE METRIC] CTA
- **Loading:** Table skeleton rows (6 rows)
- **No results:** Search icon + "No metrics found for '{query}'" + suggestion to adjust filters
- **Delete blocked:** AlertDialog listing consumers: "This metric is used by: [list]. Remove references first."

**Responsive:** Table collapses to card-style rows on mobile (`< 768px`) showing Name + Mode + Value stacked.

---

### Screen 2: Create/Edit Metric (Dialog)

**Purpose:** Define a saved metric. Single dialog, not a wizard — the entity is simple enough.

**Layout:** Dialog (`sm:max-w-lg`). React Hook Form. Follows `create-snapshot-dialog.tsx` pattern.

```
┌──────────────────────────────────────────────┐
│ Create Metric                            [×] │
│ Define a calculation once and reuse it       │
│                                              │
│ Name *                                       │
│ [e.g., Active Beneficiaries              ]   │
│                                              │
│ Description                                  │
│ [What does this calculation represent?   ]   │
│                                              │
│ Data Source *                                 │
│ [Select a data source...                 ▼]  │
│   programs.beneficiaries                     │
│   programs.attendance                        │
│   finance.transactions                       │
│                                              │
│ ── Mode ──────────────────────────────────── │
│                                              │
│ ( Simple )  ( SQL )                          │
│                                              │
│ ┌─ Simple mode ────────────────────────────┐ │
│ │                                          │ │
│ │ Calculation type *                       │ │
│ │ [Count — How many rows              ▼]  │ │
│ │                                          │ │
│ │ Field or expression                      │ │
│ │ [beneficiary_id                      ]   │ │
│ │  ↳ programs.beneficiaries columns:       │ │
│ │    beneficiary_id · age · district       │ │
│ │  (or type an expression: col_a - col_b)  │ │
│ │                                          │ │
│ └──────────────────────────────────────────┘ │
│                                              │
│ ┌─ Preview ────────────────────────────────┐ │
│ │        2,847                             │ │
│ │ Calculating across all rows              │ │
│ │ ✓ Query validated                        │ │
│ └──────────────────────────────────────────┘ │
│                                              │
│               [Cancel]  [Save Metric]        │
└──────────────────────────────────────────────┘
```

**SQL mode variant (when SQL radio selected):**

```
│ ── Mode ──────────────────────────────────── │
│                                              │
│ ( Simple )  (•SQL )                          │
│                                              │
│ ┌─ SQL mode ──────────────────────────────┐  │
│ │                                         │  │
│ │ SQL Expression *                        │  │
│ │ ┌─────────────────────────────────────┐ │  │
│ │ │ SUM(revenue) /                      │ │  │
│ │ │ COUNT(DISTINCT beneficiary_id)      │ │  │
│ │ │                                     │ │  │
│ │ └─────────────────────────────────────┘ │  │
│ │ Must return a single numeric value.     │  │
│ │ e.g. SUM(col), COUNT(*),               │  │
│ │      SUM(a) / NULLIF(SUM(b), 0)        │  │
│ │                                         │  │
│ │           [Test Query]                  │  │
│ └─────────────────────────────────────────┘  │
│                                              │
│ ┌─ Preview ────────────────────────────────┐ │
│ │        2,340.00                          │ │
│ │ ✓ Query validated                        │ │
│ └──────────────────────────────────────────┘ │
```

**Field/expression input (Simple mode):**
- **Combobox pattern**: Type to search columns from warehouse metadata, but also accept free-text expressions
- Shows dropdown of available columns as user types (from existing warehouse column API)
- Helper text below: "Enter a column name or expression (e.g. `col_a - col_b`)"
- For COUNT aggregation, field is optional (null = COUNT(*))
- For SUM/AVG/MIN/MAX, field is required

**Key decisions:**
- **Single dialog, not wizard** — Metric has 4-5 fields depending on mode. A wizard adds navigation overhead for no benefit. Dialog keeps everything visible and reduces clicks.
- **Mode toggle with radio buttons** — Simple/SQL as two clearly distinct paths. Switching modes clears the mode-specific fields (with confirmation if data entered).
- **Preview panel always visible** — Shows computed value immediately. Auto-runs on field changes (debounced). Shows "✓ Query validated" or "✗ Error: [message]".
- **SQL textarea with monospace font** — Standard code-input affordance. Examples below the field teach by showing.
- **"Test Query" button for SQL mode** — Explicit action to validate before save. For Simple mode, preview auto-validates.
- **Aggregation dropdown uses friendly labels** — "Count — How many rows" not just "COUNT". Same pattern as existing chart builder.

**Validation:**
- Name: required, unique per org (inline error on blur)
- Data source: required
- Simple mode: aggregation required, column_expression required for non-COUNT
- SQL mode: sql_expression required
- On "Save": runs validation query against warehouse. If query fails, shows error in preview panel: "✗ Error: column 'xyz' does not exist". Save button stays enabled but dialog doesn't close until query passes.

**States:**
- **Saving:** Button shows `Loader2` spinner + "Validating...", dialog can't be closed. On success: toast `"Active Beneficiaries" saved`, dialog closes, list refreshes.
- **Validation error:** Preview panel shows red border + error message. Save button remains enabled for retry.
- **Edit mode:** Title says "Edit Metric". If metric has consumers, show amber warning above Save: "Changes will affect 3 charts and 1 KPI."
- **Mode switch with data:** Confirmation: "Switching modes will clear your current definition. Continue?"

**Responsive:** Dialog on desktop. Full-screen sheet (bottom-up) on mobile.

---

### Screen 3: KPI Page (`/kpis`)

**Purpose:** THE leadership view. Scannable at-a-glance status of all goals. **Highest-value screen in the feature.**

**Layout:** Fixed header + scrollable card grid.

```
┌─────────────────────────────────────────────────────────────┐
│ Fixed Header                                                │
│  KPIs                                     [+ CREATE KPI]    │
│  Track progress toward your goals                           │
│                                                             │
│  [Search KPIs...] [Program ▼] [Type ▼] [Status ▼]          │
├─────────────────────────────────────────────────────────────┤
│ Scrollable Content                                          │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ Girls Enrolled   On  │  │ Dropout Rate     At  │  ...   │
│  │                 Track│  │                 Risk │        │
│  │ [education] [output] │  │ [health] [outcome]   │        │
│  │                      │  │                      │        │
│  │      2,847           │  │      3.2%            │        │
│  │ Target: 3,000 · 95%  │  │ Target: 2.0% · 160%  │        │
│  │                      │  │                      │        │
│  │ Last 12 months    ↑8%│  │ Last 6 quarters  ↓2% │        │
│  │  ╱╲    ╱╲  ╱        │  │  ╱╲   ╱╲╱            │        │
│  │ ╱  ╲╱╱  ╲╱          │  │ ╱  ╲╱╱               │        │
│  │ Jan  Apr  Jul  Oct   │  │ Q1  Q2  Q3  Q4      │        │
│  │                      │  │                      │        │
│  │ Updated 2 hrs ago    │  │ Updated 1 day ago    │        │
│  └──────────────────────┘  └──────────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**KPI Card Component (most critical design in the feature):**

```
┌──────────────────────────────────────────┐
│ Girls Enrolled          [On Track] [⋮]   │  <- title + RAG badge + actions
│ [education] [output]                     │  <- program tags + metric type tag
│                                          │
│       2,847                              │  <- current value (text-4xl bold)
│ Target: 3,000 · 95% achieved            │  <- target + achievement (text-sm)
│                                          │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│ Last 12 months                ↑ +8.3%   │  <- trend label + change indicator
│                                          │
│  ╱╲    ╱╲  ╱                             │  <- ECharts sparkline (60px)
│ ╱  ╲╱╱  ╲╱                              │    with 3-4 X-axis labels
│ Jan    Apr    Jul    Oct                 │
│                                          │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│ Updated 2 hours ago                      │  <- data freshness (text-xs)
└──────────────────────────────────────────┘
```

**RAG Badge Variants:**

| Status | Badge | Classes |
|--------|-------|---------|
| On Track | `[On Track]` | `bg-green-50 text-green-700 border-green-200 border` |
| At Risk | `[At Risk]` | `bg-amber-50 text-amber-700 border-amber-200 border` |
| Off Track | `[Off Track]` | `bg-red-50 text-red-700 border-red-200 border` |
| No Target | `[No Target]` | `variant="outline" text-muted-foreground` |

**Key decisions:**
- **4xl current value** — The number is what leadership cares about. Make it unmissable.
- **RAG badge next to title** — Status is the second-most important signal. Text + color (not color-only) for accessibility.
- **Period-over-period with directional arrow** — `TrendingUp` icon in green or `TrendingDown` icon in red.
- **Readable trendline X-axis** — Show 3-4 labels (first, middle, last). Format by time grain: "Jan", "Q1", "Week 12", "2025".
- **"Updated X ago" in footer** — Data freshness. NGO users need to know the number is current.
- **No target handled gracefully** — KPIs without targets still show trend. Badge says "No Target" in muted gray.
- **Cards (not table) for KPIs** — KPIs have rich visual content (RAG badge, sparkline, target/achievement). Cards allow self-contained visual units that scan better than table rows for this data shape.

**Stale data indicator:** If last updated > 7 days, show amber `AlertCircle` dot in top-left corner of card.

**Change indicator component:**
```
↑ +8.3% vs last period    <- green text, TrendingUp icon
↓ -2.1% vs last period    <- red text, TrendingDown icon
  — vs last period         <- muted text, no change
```

**Trendline specification:**
- Uses ECharts sparkline
- `type: 'line'`, `smooth: true`, `showSymbol: false`
- Area fill: `rgba(0, 137, 123, 0.1)` (primary with 10% opacity)
- Line color: `var(--primary)`
- Target: dashed gray horizontal line (`markLine` in ECharts)
- X-axis: Show 3-4 evenly spaced labels, `text-xs`, gray color
- Height: 60px in card
- Grid: minimal margins (left: 15, right: 15, top: 5, bottom: 20)

**States:**
- **Empty:** Target icon (w-12) + "No KPIs yet. Create your first KPI to start tracking progress." + [CREATE KPI] CTA
- **Loading:** 6 skeleton cards. Each skeleton has: title placeholder, badge placeholder, value placeholder, sparkline rectangle.
- **No results:** Search icon + "No KPIs found" + adjust filters suggestion
- **Error loading value:** Card shows value area with `AlertCircle` + "Couldn't load value" + [Retry] link

**Responsive:** 3 cols (xl), 2 cols (md), 1 col (mobile). Cards stack on small screens.

**Card actions dropdown:**
- Edit KPI
- Delete KPI (confirmation dialog: "This will remove the KPI from this page and any dashboards. Continue?")

**Filter behavior:**
- All filters stack (AND logic)
- "Clear all" button appears when any filter is active
- Status filter: On Track / At Risk / Off Track / No Target

---

### Screen 4: Create/Edit KPI (Wizard Dialog)

**Purpose:** Configure a KPI on top of a saved metric. Set target, direction, thresholds.

**Layout:** Dialog (max-w-[600px]) with 4-step wizard. Wizard is justified here — KPIs have more fields with dependencies between steps.

**Step 1: Pick a Saved Metric**

```
Which metric do you want to track?

[Search your metrics...                   ]

┌──────────────────────────────────────────┐
│ | Girls Enrolled - Secondary - Rajasthan │  <- selected (primary border-left)
│   Count unique beneficiary IDs from...   │
│   [programs.beneficiaries] · Value: 1,247│
├──────────────────────────────────────────┤
│   Total Training Hours                   │
│   Sum of training_hours from...          │
│   [programs.training] · Value: 8,420     │
├──────────────────────────────────────────┤
│   Average Cost Per Beneficiary           │
│   SQL · finance.transactions             │
│   Value: 2,340                           │
└──────────────────────────────────────────┘

─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
[+ Create a new metric instead]
```

**Key decisions:**
- **Searchable list, not dropdown** — Orgs will have 20+ metrics. Dropdown becomes unusable.
- **Each row shows description + current value** — Helps identify the right metric.
- **Mode badge** — Shows "SQL" badge for SQL metrics, nothing for Simple (default).
- **"Create new" link at bottom** — Opens metric creation dialog. On save, new metric auto-selected.

**Step 2: Target & Status**

```
KPI Display Name
[Girls Enrolled in Secondary Ed            ]
(Leave blank to use the metric name)

┌─ Target ──────────────────────────────────┐
│                                           │
│  Target value         Direction           │
│  [1500          ]     [Higher is better ▼]│
│                                           │
│  ┌─ Status Thresholds ─────────────────┐  │
│  │ (When is this KPI on track?)        │  │
│  │                                     │  │
│  │ On Track     [100]% or better       │  │
│  │ At Risk      [80 ]% to 99%         │  │
│  │ Off Track    Below 80%             │  │
│  │                                     │  │
│  │ Example with target of 1,500:       │  │
│  │ [>=1,500 On Track] [1,200-1,499     │  │
│  │  At Risk] [<1,200 Off Track]        │  │
│  └─────────────────────────────────────┘  │
│                                           │
│  ┌ No target? ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  │
│  │ Leave blank to track trend only,   │  │
│  │ without status colors.             │  │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  │
└───────────────────────────────────────────┘
```

**Key decisions:**
- **Direction as "Higher is better" / "Lower is better"** — Plain language.
- **RAG thresholds shown as concrete values** — ">=1,500 = On Track" is immediately understandable.
- **Threshold section only appears if target is set** — Progressive disclosure.
- **Smart defaults:** Green = 100%, Amber = 80% (for increase). When direction switches to "decrease", amber auto-adjusts to 120%.

**Step 3: Trend Configuration**

```
Show trend by: *
[Monthly                                   ▼]
  Daily
  Weekly
  Monthly    <- default
  Quarterly
  Yearly

How many periods to show?
[12         ]
(Show last 12 months in the trend chart)

Date field for trend *
[enrollment_date                           ▼]
(Which date field should we use to group by time?)

┌─ Preview ─────────────────────────────────┐
│ This KPI will show 12 monthly values      │
│ Example: May 2025 -> April 2026           │
└───────────────────────────────────────────┘
```

**Key decisions:**
- **"Show trend by" not "Time grain"** — Plain language.
- **Period count with context** — "Show last 12 months" not just "12".
- **Date field picker** — Required for trend. Only date/datetime columns shown.
- **Default: Monthly, 12 periods** — Most common NGO reporting cycle.

**Step 4: Tags & Summary**

```
Indicator type (optional)
[Output                                    ▼]
  Input    — Resources invested (budget, staff)
  Output   — Activities completed (trainings, distributions)
  Outcome  — Short-term changes (knowledge, behavior)
  Impact   — Long-term effects (lives improved)

Program tags (optional)
[Type a tag and press Enter                ]
  [Education x] [Rajasthan x]
(Helps you filter KPIs on the main page)

┌─ Summary ─────────────────────────────────┐
│ Metric:   Girls Enrolled - Secondary      │
│ Target:   1,500 (higher is better)        │
│ Status:   On Track >=1,500                │
│           At Risk 1,200-1,499             │
│           Off Track <1,200                │
│ Trend:    12 monthly periods              │
│ Type:     Output                          │
│ Tags:     Education, Rajasthan            │
└───────────────────────────────────────────┘

                         [Back]  [Save KPI]
```

**Key decisions:**
- **Input/Output/Outcome/Impact with descriptions** — Teaches logframe vocabulary.
- **Summary preview before save** — Final checkpoint.
- **Tags are on KPIs, not Metrics** — Metrics have no tags per plan.

**States:**
- **Metric required** to proceed from step 1
- **Date field required** in step 3 (no trend without a time dimension)
- **Threshold validation:** Green > Amber, Amber > 0
- **Saving:** Spinner in button, toast on success

---

### Screen 5: KPI Detail Drawer

**Purpose:** Deep dive into a single KPI. Full trend chart, configuration, edit access.

**Layout:** Sheet from right, 600px wide. Sticky header, scrollable body.

```
┌──────────────────────────────────────────┐
│ Girls Enrolled         [On Track]   [⋮]  │  <- sticky header
│ [education] [output]                     │
├──────────────────────────────────────────┤
│                                          │  <- scrollable
│  ┌──────────┐  ┌──────────┐             │
│  │  2,847   │  │  3,000   │             │
│  │ Current  │  │ Target   │             │
│  └──────────┘  └──────────┘             │
│                                          │
│  ┌──────────┐  ┌──────────┐             │
│  │   95%    │  │  ↑ +8.3% │             │
│  │ Achieved │  │ vs last  │             │
│  └──────────┘  └──────────┘             │
│                                          │
│  Updated 2 hours ago                     │
│                                          │
│ ─ Trend ──────────── [12 periods ▼] ─── │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │                                  │    │
│  │    Full ECharts line chart       │    │
│  │    with target dashed line       │    │
│  │    Height: 250px                 │    │
│  │                                  │    │
│  └──────────────────────────────────┘    │
│  ── Actual   - - Target                  │
│                                          │
│ ─ How this KPI works ────────────────── │
│                                          │
│  Based on:    Girls Enrolled - Secondary │
│  Direction:   Higher is better           │
│  Frequency:   Monthly                    │
│  Thresholds:  On Track >=100%            │
│               At Risk 80-99%             │
│               Off Track <80%             │
│                                          │
└──────────────────────────────────────────┘
```

**Key decisions:**
- **Value + Target side by side** — Direct comparison.
- **Full-height trend chart (250px)** with target as dashed horizontal line — ECharts sparkline.
- **Period selector** on trend section — "Last 12 periods" / "Last 6" / "All time" dropdown.
- **"How this KPI works"** section title — Plain language for configuration details.
- **Drawer actions:** Edit KPI, Edit Underlying Metric (with blast-radius warning), Delete.

**Trend chart specification:**
- ECharts line chart, 250px height
- Actual value: solid primary-colored line
- Target: dashed gray horizontal line (`markLine`)
- Hover tooltip: period name + exact value + RAG status at that point
- X-axis: All period labels visible (rotate if needed)
- Y-axis: Auto-scaled with target value visible
- Legend: Below chart — "── Actual" and "- - Target"

**States:**
- **Loading:** Skeletons for values, chart rectangle, config list
- **Error:** AlertCircle + "Couldn't load KPI data" + [Retry]
- **No trend data yet:** Chart area shows message "Not enough data for a trend yet. Values will appear as data accumulates."

---

### Screen 6: MetricsSelector (Saved Metrics Tab)

**Purpose:** Add a "Saved Metrics" tab to the existing `MetricsSelector.tsx` in the chart builder. No rename. No terminology change.

**Layout:** Embedded in chart builder sidebar. Two-tab interface added to existing component.

```
Metrics
Choose what value to display in this chart

┌──────────────────────────────────────────┐
│  [Saved Metrics]  [Ad-hoc]               │  <- Tabs
├──────────────────────────────────────────┤
│                                          │
│  [Search saved metrics...            ]   │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ | Girls Enrolled                   │  │  <- selected
│  │   Count · beneficiary_id           │  │
│  ├────────────────────────────────────┤  │
│  │   Total Training Hours             │  │
│  │   Sum · training_hours             │  │
│  ├────────────────────────────────────┤  │
│  │   Revenue Per Beneficiary          │  │
│  │   SQL · finance.transactions       │  │
│  └────────────────────────────────────┘  │
│                                          │
│  [+ Create and save a new metric]        │
│                                          │
└──────────────────────────────────────────┘
```

**Ad-hoc tab** preserves the existing MetricsSelector UI exactly as-is (bordered container per metric, 2-col grid for function + column, remove button, "Add Metric" button).

**Key decisions:**
- **"Saved Metrics" tab first** — Encourages reuse. Ad-hoc always available.
- **Filtered to current dataset** — Only show metrics whose data source matches the chart's selected dataset. Prevents incompatible selections.
- **Search within saved tab** — As libraries grow (10-20 metrics), list becomes long.
- **SQL metrics show "SQL" badge** — Distinguishes mode at a glance.
- **"Create and save" link** — Opens metric creation dialog. On save, new metric auto-selected.
- **No rename** — `MetricsSelector.tsx` stays. Label stays "Metrics". No "Measure" terminology.
- **Existing ad-hoc UI unchanged** — No regression. Users familiar with current flow are unaffected.

**Modified files:**
- `components/charts/MetricsSelector.tsx` — Add tabs, saved metrics list
- `components/charts/ChartDataConfigurationV3.tsx` — No import change needed
- `components/charts/MapDataConfigurationV3.tsx` — No import change needed

---

### Screen 7: KPI Dashboard Chart

**Purpose:** Compact KPI chart rendered inside dashboard grid (react-grid-layout).

**Layout:** Card component that adapts to container size.

**Default size (3x2 grid units, ~300x200px):**

```
┌──────────────────────────────┐
│ Girls Enrolled    [On Track] │
│                              │
│       2,847                  │
│ Target: 3,000 (95%)         │
│                              │
│  ╱╲    ╱╲  ╱                │  <- ECharts sparkline (40px)
│ ╱  ╲╱╱  ╲╱                  │    with target threshold line
│ Jan    Apr    Jul    Oct     │
│                              │
│ ↑ +8.3%    Updated 2h ago   │
└──────────────────────────────┘
```

**Size-responsive rendering:**

| Size | Value font | Show target | Show sparkline | Show X-axis |
|------|-----------|-------------|----------------|-------------|
| Small (< 250px wide) | text-2xl | Yes (no %) | Yes (30px) | No |
| Medium (250-350px) | text-3xl | Yes (with %) | Yes (40px) | Yes (3 labels) |
| Large (> 350px) | text-4xl | Yes (with %) | Yes (60px) | Yes (4+ labels) |

**Key decisions:**
- **Adapts via `useResizeObserver`** — Detects container width and adjusts rendering.
- **RAG badge always visible** — Even at smallest size. It's the most critical signal.
- **Sparkline with target threshold line** — ECharts sparkline with `markLine` for target.
- **Click opens detail drawer** — Charts are entry points, not destinations.
- **Footer: change indicator + timestamp** — Side by side at all sizes.

**States:**
- **Loading:** Skeleton matching chart layout
- **Error:** Centered AlertCircle + "Couldn't load" (text-sm)
- **Stale (>7 days):** Amber dot in top-right corner

---

### Screen 8: Component Selector Modal (Updated)

**Purpose:** Add "KPI" tab to the existing chart-selector-modal in dashboard builder.

**Layout:** Existing Dialog gains a TabsList with "Charts" and "KPIs" tabs.

```
┌──────────────────────────────────────────────────┐
│ Add Component                                [x] │
│ Choose a chart or KPI to add to your dashboard   │
│                                                  │
│  [Charts]  [KPIs]                                │  <- tabs
├──────────────────────────────────────────────────┤
│                                                  │
│  [Search KPIs...                             ]   │
│                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │ Girls      │  │ Dropout    │  │ Training   │ │
│  │ Enrolled   │  │ Rate       │  │ Hours      │ │
│  │    On Track│  │    At Risk │  │    On Track│ │
│  │            │  │            │  │            │ │
│  │  2,847     │  │  3.2%      │  │  8,420     │ │
│  │  ╱╲  ╱╲   │  │  ╲╱  ╲╱   │  │  ╱╱╱╱     │ │
│  │            │  │            │  │            │ │
│  │ [educ]     │  │ [health]   │  │ [training] │ │
│  └────────────┘  └────────────┘  └────────────┘ │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Key decisions:**
- **Tabs, not a new modal** — Maintains consistency with existing component selector.
- **KPI preview cards** match the dashboard chart layout — Users see what they're about to add.
- **Mini sparkline in preview** — Helps distinguish KPIs.
- **RAG badge visible** — Critical selection context.
- **3-column grid** — Same as existing chart preview grid.
- **Click to add** — Closes modal, adds KPI chart to dashboard at next available grid position.

**Empty state:** Target icon + "No KPIs created yet" + link to KPI page.

---

## Cross-Cutting Specifications

### Typography Scale (for this feature)

| Element | Class | Used In |
|---------|-------|---------|
| Page title | `text-3xl font-bold` | All page headers |
| Section heading | `text-xl font-semibold` | Drawer sections |
| Card title | `text-base font-semibold` | KPI cards |
| Table row name | `text-sm font-semibold` | Metric table rows |
| KPI current value (card) | `text-4xl font-bold` | KPI page cards |
| KPI current value (drawer) | `text-5xl font-bold` | Detail drawer |
| KPI chart value | `text-3xl font-bold` | Dashboard chart (medium size) |
| Body text | `text-sm` | Descriptions, config details |
| Helper text | `text-xs text-muted-foreground` | Form hints, timestamps |
| Badge text | `text-xs` | Mode badges, RAG badges |

### Color System

| Purpose | Classes | Notes |
|---------|---------|-------|
| On Track | `bg-green-50 text-green-700 border-green-200` | Badge, trend arrow |
| At Risk | `bg-amber-50 text-amber-700 border-amber-200` | Badge, trend arrow |
| Off Track | `bg-red-50 text-red-700 border-red-200` | Badge, trend arrow |
| No Target | `variant="outline" text-muted-foreground` | Neutral badge |
| Positive change | `text-green-600` | +% arrows |
| Negative change | `text-red-600` | -% arrows |
| Primary action | `var(--primary)` (#00897B teal) | CTA buttons, selected states |
| Sparkline | `var(--primary)` line, `rgba(0,137,123,0.1)` fill | All trendlines |
| Target line | Dashed gray | `markLine` in ECharts |

### Loading Patterns

| Context | Pattern |
|---------|---------|
| Metric table | 6 skeleton rows |
| KPI card grids | 6 skeleton cards |
| Value computation | Skeleton rectangle matching text size |
| Trend chart | Skeleton rectangle at chart height |
| Form submission | Loader2 spinner in button, text changes to "-ing" form |
| Page-level | Centered Loader2 with specific message |

### Error Patterns

| Context | Pattern |
|---------|---------|
| Field validation | Red text below field on blur: "Metric name is required" |
| Expression validation | Red border on preview: "Error: column 'xyz' does not exist" |
| SQL validation | Red border on preview: "Error: query must return a single numeric value" |
| API error | Toast: `toastError("Couldn't save metric. Try again.")` |
| Load failure | Centered AlertCircle + message + [Retry] button |
| Delete blocked | AlertDialog listing consumers |

### Accessibility Requirements

- **RAG badges:** Always text + color, never color-only ("On Track" not just green)
- **Focus states:** 2px ring in primary color on all interactive elements
- **Touch targets:** 44x44px minimum on mobile
- **Icon-only buttons:** Always have `aria-label`
- **Form inputs:** Visible `<Label>` elements, required indicator (`*`)
- **Trend charts:** `aria-label` describing the trend ("Girls Enrolled trend: increasing from 2,100 to 2,847 over 12 months")
- **Tab order:** Logical reading order in dialogs and wizards
- **Mode toggle:** Radio buttons with proper `role="radiogroup"`

### Data Freshness (Cross-Cutting)

Every screen that shows a computed value must display:
- **"Updated X ago"** or **"Data as of [date]"** — using `formatDistanceToNow` from date-fns
- **Stale indicator** — Amber dot if > 7 days since last warehouse data refresh
- Values are computed at query-time (not cached in v1)

---

## Files Changed/Created Summary

### New Frontend Files
| File | Screen |
|------|--------|
| `types/metrics.ts` | Metric, MetricCreate, MetricUpdate, MetricMode interfaces |
| `types/kpis.ts` | KPI, KPISummary, KPICreate, RAGStatus, RAG_COLORS |
| `hooks/api/useMetrics.ts` | SWR hook for metrics CRUD |
| `hooks/api/useKPIs.ts` | SWR hook for KPIs CRUD + summary + trend |
| `app/metrics/page.tsx` | Screen 1: Metrics Library page |
| `app/kpis/page.tsx` | Screen 3: KPI Page |
| `components/metrics/metrics-library.tsx` | Metrics table with search/filter |
| `components/metrics/metric-form-dialog.tsx` | Screen 2: Create/edit metric dialog |
| `components/metrics/metric-preview.tsx` | Value preview during creation |
| `components/kpis/kpi-page.tsx` | KPI grid with search/filter |
| `components/kpis/kpi-card.tsx` | Screen 3: Individual KPI card |
| `components/kpis/kpi-form.tsx` | Screen 4: Create/edit KPI wizard |
| `components/kpis/kpi-detail-drawer.tsx` | Screen 5: KPI detail sheet |
| `components/kpis/kpi-chart.tsx` | Screen 7: Dashboard KPI chart |
| `components/dashboard/kpi-chart-element.tsx` | Chart wrapper for dashboard grid |

### Modified Frontend Files
| File | Change |
|------|--------|
| `components/charts/MetricsSelector.tsx` | Add "Saved Metrics" + "Ad-hoc" tabs |
| `components/dashboard/chart-selector-modal.tsx` | Add KPI tab |
| `components/dashboard/dashboard-builder-v2.tsx` | Handle `kpi` component type |
| `components/main-layout.tsx` | Add KPIs nav item, add Metrics nav item |

---

*Design document generated from [v1 spec](./spec.md), [implementation plan](./plan.md), Dalgo design system patterns (`patterns.md`), and NGO user perspective evaluation.*
