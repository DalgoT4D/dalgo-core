# Metrics & KPIs v1 — UI Design

**Status:** Draft
**Date:** 2026-04-21
**Spec:** [v1 spec](./spec.md) | [Implementation plan](./plan.md)
**Reviewed through:** UX design standards + NGO user perspective (Priya)

---

## Design Assessment (UX Expert)

The feature introduces 8 interconnected screens. Key findings:

**Critical**
- Metric creation form needs progressive disclosure (wizard) to avoid overwhelming users with dataset/column/aggregation/filter choices all at once
- KPI cards must render RAG status as **text + color** (not color-only) for accessibility — "On Track" not just a green dot
- MeasureSelector rename must not break existing chart builder UX — ad-hoc mode stays exactly as-is

**Important**
- KPI page is the highest-value screen — optimize for scan speed (large values, visible RAG badges, readable trendlines)
- Dashboard KPI widget must adapt to different grid sizes (small/medium/large) without breaking layout
- All new forms need live preview at every step to build user confidence

**Nice-to-Have**
- "Turn into KPI" shortcut on metric cards (one-click promotion)
- Usage footer on metric cards ("Used in 3 charts, 1 KPI") for blast-radius awareness

## User Assessment (NGO Perspective)

**Blocks Adoption**
- Technical jargon throughout: "Dataset", "Schema", "Aggregation", "RAG thresholds", "Time grain" — must be replaced with plain language
- No preview/verification step before saving metrics — users won't trust numbers they can't verify
- Missing data freshness indicators — every value needs a "Last updated" timestamp

**Confuses Users**
- "Metric" vs "Measure" vs "KPI" vocabulary collision — users call these "indicators" or "calculations"
- Filter builder must be visual (dropdowns), not text-based
- RAG threshold percentages are abstract without concrete value examples

**Could Be Simpler**
- Metric type tags (Input/Output/Outcome/Impact) need descriptions — not all NGO staff know logframe terminology
- Default time grain should be "Monthly" (most common NGO reporting cycle)
- Tag input pattern should show purpose ("helps you filter later")

## Combined Recommendations (Prioritized)

1. **Replace jargon everywhere** — Single highest-impact change for adoption
2. **Add live preview to all creation forms** — Builds trust, catches errors early
3. **Show data freshness on every value** — "Data as of April 20, 2026"
4. **Use wizard pattern for metric creation** — Progressive disclosure reduces cognitive load
5. **Make KPI page scan-optimized** — Large values, visible badges, readable trendlines
6. **Smart defaults on all forms** — Monthly time grain, 12 trend periods, 100%/80% thresholds
7. **Accessible RAG badges** — Text labels + color, not color-only

---

## Terminology Map

Every technical term gets a user-facing replacement. Engineers use the left column in code; the right column appears in the UI.

| Code/Internal | UI Label | Why |
|---|---|---|
| Metric | Saved Calculation (or just the metric's name) | "Metric" is overloaded; users think "indicator" |
| Dataset (schema.table) | Data Source | Users think "my beneficiary list", not "schema.table" |
| Column | Field | Slightly friendlier; "column" is OK if showing spreadsheet-like context |
| Aggregation | Calculation type | Then use friendly sub-labels (see below) |
| `count` | Count (how many rows) |  |
| `sum` | Total (add up all values) |  |
| `avg` | Average (mean of all values) |  |
| `min` | Lowest value |  |
| `max` | Highest value |  |
| `count_distinct` | Count unique (how many different values) |  |
| Filter | Narrow down (only include rows where...) |  |
| RAG status | Status: On Track / At Risk / Off Track |  |
| Time grain | Trend frequency (show trend by: monthly/quarterly/etc.) |  |
| Trend periods | Trend duration (show last X months) |  |
| KPI | KPI (keep — but subtitle explains: "Track progress toward your goals") |  |
| Direction | "Higher is better" / "Lower is better" |  |
| Threshold | Status threshold (with concrete value examples) |  |

---

## Screen Designs

### Screen 1: Metrics Library (`/metrics`)

**Purpose:** Browse and manage saved calculations. Analyst's toolkit.

**Layout:** Fixed header + scrollable card grid (matches Dalgo page pattern).

```
┌─────────────────────────────────────────────────────────────┐
│ Fixed Header                                                │
│  Metrics                              [+ Create Metric]     │
│  Saved calculations you can reuse across charts and KPIs    │
│                                                             │
│  [🔍 Search by name or tag...] [Data Source ▼] [Tags ▼]    │
├─────────────────────────────────────────────────────────────┤
│ Scrollable Content                                          │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐  │
│  │ Total Active     │  │ Avg Training    │  │ Dropout    │  │
│  │ Beneficiaries    │  │ Hours           │  │ Rate       │  │
│  │                  │  │                 │  │            │  │
│  │ Count unique     │  │ Average of      │  │ ...        │  │
│  │ beneficiary_ids  │  │ training_hours  │  │            │  │
│  │ from programs.   │  │ from ...        │  │            │  │
│  │ beneficiaries    │  │                 │  │            │  │
│  │                  │  │                 │  │            │  │
│  │ [education] [Q1] │  │ [training]      │  │ [health]   │  │
│  │                  │  │                 │  │            │  │
│  │ ── ── ── ── ──   │  │ ── ── ── ── ── │  │ ── ── ──   │  │
│  │ 2,847            │  │ 24.5            │  │ 3.2%       │  │
│  │ Current value    │  │ Current value   │  │ Current    │  │
│  │                  │  │                 │  │            │  │
│  │ 📊 3 charts,    │  │ 📊 1 chart     │  │ 📊 2 KPIs │  │
│  │    1 KPI         │  │                 │  │            │  │
│  └─────────────────┘  └─────────────────┘  └────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Metric Card Component:**

```
┌──────────────────────────────────────┐
│ Total Active Beneficiaries      [⋮]  │  ← title + actions dropdown
│ Count unique beneficiary IDs from    │  ← description (2 lines max)
│ the Girls Literacy Program sheet     │
│                                      │
│ [education] [quarterly]              │  ← tag badges (outline variant)
│                                      │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │  ← divider
│ 2,847                                │  ← current value (text-2xl bold)
│ Current value · Updated 2 hrs ago    │  ← meta (text-xs muted)
│                                      │
│ 📊 Used in 3 charts, 1 KPI          │  ← usage footer (text-xs muted)
└──────────────────────────────────────┘
```

**Key decisions:**
- **Card grid over table** — Metrics have rich metadata (description, tags, value) that doesn't fit table rows. Cards allow scannable, self-contained units.
- **Current value prominently displayed** — Immediate feedback that the metric works. Users verify correctness at a glance.
- **"Updated X ago" timestamp** — Data freshness is critical for NGO trust.
- **Usage footer** — Blast-radius awareness. Shows which metrics are trusted/popular.
- **3-column grid** — `md:grid-cols-2 lg:grid-cols-3`. Prevents cards from becoming too wide.

**Card actions dropdown:**
- Edit
- Create KPI from this (one-click promotion, pre-fills KPI form)
- Delete (blocked if referenced — shows consumer list)

**States:**
- **Empty:** Centered Calculator icon (w-12 h-12 muted) + "No saved calculations yet" + [Create Metric] CTA
- **Loading:** 6 skeleton cards in grid
- **No results:** Search icon + "No metrics found for {query}" + suggestion to adjust filters
- **Delete blocked:** AlertDialog listing consumers: "This metric is used by: [list]. Remove references first."

**Responsive:** 3 cols desktop, 2 cols tablet, 1 col mobile.

---

### Screen 2: Create/Edit Metric (Wizard Dialog)

**Purpose:** Define a saved calculation. Must feel like Google Forms, not a SQL IDE.

**Layout:** Dialog (max-w-[600px]) with 4-step wizard.

```
┌─────────────────────────────────────────────┐
│ Create Metric                           [×] │
│ Define a calculation once and reuse it      │
│                                             │
│  (1)───(2)───(3)───(4)                      │  ← step indicator
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │                                         │ │
│ │  [Step content — see below]             │ │
│ │                                         │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│                      [Back]  [Next / Save]  │
└─────────────────────────────────────────────┘
```

**Step 1: Pick Data Source**

```
Which data source contains the values you need?

[Select a data source...                    ▼]
  📁 programs.beneficiaries
  📁 programs.attendance
  📁 programs.training_sessions

(hint: This determines which fields are available)
```

**Step 2: Define Calculation**

```
What do you want to calculate?

Calculation type *
[Select...                                  ▼]
  Count        — How many rows
  Total        — Add up all values
  Average      — Mean of all values
  Count Unique — How many different values
  Lowest       — Smallest value
  Highest      — Largest value

Field *
[Select a field...                          ▼]
  📊 beneficiary_id  (text)
  📊 age             (number)
  📊 enrollment_date (date)

┌─ Preview ─────────────────────────────────┐
│ 2,847                                     │
│ (calculating across all rows)             │
└───────────────────────────────────────────┘
```

**Key decisions for Step 2:**
- Aggregation dropdown uses **friendly labels with descriptions** — "Count — How many rows" not just "COUNT"
- Column dropdown shows **data type icons** (reuse existing `ColumnTypeIcon`)
- **Live preview** updates on every change. Debounced API call. Shows skeleton while loading.
- For COUNT, column auto-selects `*`. For SUM/AVG, non-numeric columns are disabled (with visual explanation).

**Step 3: Narrow Down (Optional Filters)**

```
Only include specific rows? (optional)

┌─ No filters added ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐
│                                           │
│  This will calculate across all rows.     │
│          [+ Add Filter]                   │
│                                           │
└─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘

── OR with filters added: ──

┌──────────────────────────────────────────┐
│ [status ▼]  [is equal to ▼]  [Active  ] │  [🗑]
└──────────────────────────────────────────┘
┌──────────────────────────────────────────┐
│ [district ▼]  [is equal to ▼] [Jaipur ] │  [🗑]
└──────────────────────────────────────────┘
[+ Add Another Filter]

┌─ Preview with filters ────────────────────┐
│ 1,247                                     │
│ (1,247 of 2,847 rows match your filters)  │
└───────────────────────────────────────────┘
```

**Key decisions for Step 3:**
- **Dashed border empty state** signals "optional — you can add something here but don't have to"
- **Visual filter builder** — dropdowns only, no typing SQL. Operator dropdown uses plain language: "is equal to", "is not equal to", "is greater than", "contains"
- **Preview shows row context** — "1,247 of 2,847 rows match" helps users verify the filter is working correctly
- If filter returns 0 rows, show amber warning: "No rows match these filters. Check your conditions."

**Step 4: Name & Save**

```
Name your calculation *
[e.g., Active Beneficiaries - Jaipur       ]

Description
[What does this calculation represent?      ]
[When should someone use it?                ]
(hint: Help others understand this metric)

Tags (optional)
[Type a tag and press Enter                 ]
  [education ×] [quarterly ×]

┌─ Summary ─────────────────────────────────┐
│                          2,847            │
│ Data source: programs.beneficiaries       │
│ Calculation: Count unique beneficiary_id  │
│ Filters: status = Active, district = ...  │
└───────────────────────────────────────────┘

                        [Back]  [Save Metric]
```

**States:**
- **Validation:** Name required (inline error on blur). Column + aggregation required. Inline errors — not just on submit.
- **Incompatible selection:** If user picks Average on a text column, show amber alert: "Average only works with number fields. Try Count instead."
- **Saving:** Button shows spinner + "Saving...", dialog can't be closed. Toast on success: `"Active Beneficiaries" saved`
- **Edit mode:** Title says "Edit Metric". Shows blast-radius warning before save if metric has consumers: "This will affect 3 charts and 1 KPI. Continue?"

**Responsive:** Dialog on desktop. Full-screen sheet (bottom-up) on mobile.

---

### Screen 3: KPI Page (`/kpis`)

**Purpose:** THE leadership view. Scannable at-a-glance status of all goals. This is what executives check every morning. **Highest-value screen in the feature.**

**Layout:** Fixed header + scrollable card grid.

```
┌─────────────────────────────────────────────────────────────┐
│ Fixed Header                                                │
│  KPIs                                     [+ Create KPI]    │
│  Track progress toward your goals                           │
│                                                             │
│  [🔍 Search KPIs...] [Program ▼] [Type ▼] [Status ▼]      │
├─────────────────────────────────────────────────────────────┤
│ Scrollable Content                                          │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ Girls Enrolled   🟢  │  │ Dropout Rate     🟡  │  ...   │
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
│ Girls Enrolled          [On Track] [⋮]   │  ← title + RAG badge + actions
│ [education] [output]                     │  ← tag badges
│                                          │
│       2,847                              │  ← current value (text-4xl bold)
│ Target: 3,000 · 95% achieved            │  ← target + achievement (text-sm)
│                                          │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│ Last 12 months                ↑ +8.3%   │  ← trend label + change indicator
│                                          │
│  ╱╲    ╱╲  ╱                             │  ← ECharts sparkline (60px)
│ ╱  ╲╱╱  ╲╱                              │    with 3-4 X-axis labels
│ Jan    Apr    Jul    Oct                 │
│                                          │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│ Updated 2 hours ago                      │  ← data freshness (text-xs)
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
- **Period-over-period with directional arrow** — `TrendingUp` icon in green or `TrendingDown` icon in red. Humans process direction faster than reading percentages.
- **Readable trendline X-axis** — Show 3-4 labels (first, middle, last). Format by time grain: "Jan", "Q1", "Week 12", "2025". Sparklines without labels are decorative; labeled trends enable conversation.
- **"Updated X ago" in footer** — Data freshness. NGO users need to know the number is current. Stale data = loss of confidence = back to Excel.
- **No target handled gracefully** — KPIs without targets still show trend. Badge says "No Target" in muted gray.

**Stale data indicator:** If last updated > 7 days, show amber `AlertCircle` dot in top-left corner of card.

**Change indicator component:**
```
↑ +8.3% vs last period    ← green text, TrendingUp icon
↓ -2.1% vs last period    ← red text, TrendingDown icon
  — vs last period         ← muted text, no change
```

**Trendline specification:**
- Uses ECharts via existing MiniChart pattern
- `type: 'line'`, `smooth: true`, `showSymbol: false`
- Area fill: `rgba(0, 137, 123, 0.1)` (primary with 10% opacity)
- Line color: `var(--primary)`
- X-axis: Show 3-4 evenly spaced labels, `text-xs`, gray color
- Height: 60px in card
- Grid: minimal margins (left: 15, right: 15, top: 5, bottom: 20)

**States:**
- **Empty:** Target icon (w-12) + "No KPIs yet. Create your first KPI to start tracking progress." + [Create KPI] CTA
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

**Layout:** Dialog (max-w-[600px]) with 4-step wizard. Same shell as metric creation.

**Step 1: Pick a Saved Calculation**

```
Which saved calculation do you want to track?

[🔍 Search your calculations...            ]

┌──────────────────────────────────────────┐
│ ▌ Girls Enrolled - Secondary - Rajasthan │  ← selected (primary border-left)
│   Count unique beneficiary IDs from...   │
│   [programs.beneficiaries] · Value: 1,247│
├──────────────────────────────────────────┤
│   Total Training Hours                   │
│   Sum of training_hours from...          │
│   [programs.training] · Value: 8,420     │
├──────────────────────────────────────────┤
│   Average Cost Per Beneficiary           │
│   Average of cost from...                │
│   [finance.expenses] · Value: 2,340      │
└──────────────────────────────────────────┘

─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
[+ Create a new calculation instead]
```

**Key decisions:**
- **Searchable list, not dropdown** — Orgs will have 20+ metrics. Dropdown becomes unusable.
- **Each row shows description + current value** — Helps identify the right metric.
- **"Create new" link at bottom** — Inline creation flow so user doesn't lose context.
- **Selected state:** Primary color left border + subtle primary background.

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
│  │ 🟢 On Track     [100]% or better   │  │
│  │ 🟡 At Risk      [80 ]% to 99%      │  │
│  │ 🔴 Off Track    Below 80%          │  │
│  │                                     │  │
│  │ Example with target of 1,500:       │  │
│  │ [≥1,500 🟢]  [1,200-1,499 🟡]     │  │
│  │ [<1,200 🔴]                         │  │
│  └─────────────────────────────────────┘  │
│                                           │
│  ┌ No target? ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  │
│  │ Leave blank to track trend only,   │  │
│  │ without status colors.             │  │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  │
└───────────────────────────────────────────┘
```

**Key decisions:**
- **Direction as "Higher is better" / "Lower is better"** — Plain language. Icons reinforce (TrendingUp / TrendingDown).
- **RAG thresholds shown as concrete values** — Abstract percentages are hard. "≥1,500 = On Track" is immediately understandable.
- **Threshold section only appears if target is set** — Progressive disclosure.
- **Smart defaults:** Green = 100%, Amber = 80% (for increase). When direction switches to "decrease", amber auto-adjusts to 120%.
- **No target is OK** — Clear explanation of what happens (trend only, no status colors).

**Step 3: Trend Configuration**

```
Show trend by: *
[Monthly                                   ▼]
  Daily
  Weekly
  Monthly    ← default
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
│ Example: May 2025 → April 2026            │
└───────────────────────────────────────────┘
```

**Key decisions:**
- **"Show trend by" not "Time grain"** — Plain language.
- **Period count with context** — "Show last 12 months" not just "12".
- **Date field picker** — Required for trend. Only date/datetime columns shown. This resolves Open Question #1 from the plan.
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
  [Education ×] [Rajasthan ×]
(Helps you filter KPIs on the main page)

┌─ Summary ─────────────────────────────────┐
│ Metric:   Girls Enrolled - Secondary      │
│ Target:   1,500 (higher is better)        │
│ Status:   🟢 ≥1,500  🟡 1,200-1,499     │
│           🔴 <1,200                       │
│ Trend:    12 monthly periods              │
│ Type:     Output                          │
│ Tags:     Education, Rajasthan            │
└───────────────────────────────────────────┘

                         [Back]  [Save KPI]
```

**Key decisions:**
- **Input/Output/Outcome/Impact with descriptions** — NGO logframe vocabulary. Descriptions teach the framework for users unfamiliar with M&E terminology.
- **Summary preview before save** — Final checkpoint. Reduces errors, builds confidence.
- **Tag purpose explained** — "Helps you filter KPIs on the main page" — users understand WHY to add tags.

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
│ Girls Enrolled         [On Track]   [⋮]  │  ← sticky header
│ [education] [output]                     │
├──────────────────────────────────────────┤
│                                          │  ← scrollable
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
│  Thresholds:  🟢 ≥100%  🟡 80-99%      │
│               🔴 <80%                    │
│                                          │
└──────────────────────────────────────────┘
```

**Key decisions:**
- **Value + Target side by side** — Direct comparison. The two numbers users care about most.
- **Achievement + period-over-period in 2x2 grid** — Summary stats with equal visual weight.
- **Full-height trend chart (250px)** with target as dashed horizontal line — Classic KPI visualization.
- **Period selector** on trend section — "Last 12 periods" / "Last 6" / "All time" dropdown.
- **"How this KPI works"** section title — Plain language for configuration details.
- **Drawer actions:** Edit KPI, Edit Underlying Metric (with blast-radius warning), Delete.

**Trend chart specification:**
- ECharts line chart, 250px height
- Actual value: solid primary-colored line
- Target: dashed gray horizontal line
- Hover tooltip: period name + exact value + RAG status at that point
- X-axis: All period labels visible (rotate if needed)
- Y-axis: Auto-scaled with target value visible
- Legend: Below chart — "── Actual" and "- - Target"

**States:**
- **Loading:** Skeletons for values, chart rectangle, config list
- **Error:** AlertCircle + "Couldn't load KPI data" + [Retry]
- **No trend data yet:** Chart area shows message "Not enough data for a trend yet. Values will appear as data accumulates."

---

### Screen 6: MeasureSelector (Chart Builder Refactor)

**Purpose:** Replace `MetricsSelector.tsx` with `MeasureSelector.tsx`. Two tabs: saved metrics and ad-hoc.

**Layout:** Embedded in chart builder sidebar. Two-tab interface.

```
Measure
Choose what value to display in this chart

┌──────────────────────────────────────────┐
│  [Saved Metrics]  [Custom (Ad-hoc)]      │  ← Tabs
├──────────────────────────────────────────┤
│                                          │
│  [🔍 Search saved metrics...          ]  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ ▌ Girls Enrolled                   │  │  ← selected
│  │   Count · beneficiary_id           │  │
│  ├────────────────────────────────────┤  │
│  │   Total Training Hours             │  │
│  │   Sum · training_hours             │  │
│  ├────────────────────────────────────┤  │
│  │   Average Cost                     │  │
│  │   Average · cost                   │  │
│  └────────────────────────────────────┘  │
│                                          │
│  [+ Create and save a new metric]        │
│                                          │
└──────────────────────────────────────────┘
```

**Custom tab** preserves the existing MetricsSelector UI exactly as-is (bordered container per measure, 2-col grid for function + column, remove button, "Add Measure" button).

**Key decisions:**
- **"Saved Metrics" tab first** — Encourages reuse (primary goal). Ad-hoc always available.
- **Filtered to current dataset** — Only show metrics whose data source matches the chart's selected dataset. Prevents incompatible selections.
- **Search within saved tab** — As libraries grow (10-20 metrics), dropdown becomes unusable.
- **"Custom (Ad-hoc)" label** — Clarifies these are one-off, not saved.
- **"Create and save" link** — Opens metric creation dialog. On save, new metric auto-selected.
- **Existing ad-hoc UI unchanged** — No regression. Users familiar with current flow are unaffected.

**Rename scope:**
- `MetricsSelector.tsx` → `MeasureSelector.tsx`
- Update imports in: `ChartDataConfigurationV3.tsx`, `MapDataConfigurationV3.tsx`, tests
- Update label from "Metrics" to "Measure" in the component and all chart type configs

---

### Screen 7: KPI Dashboard Widget

**Purpose:** Compact KPI card rendered inside dashboard grid (react-grid-layout).

**Layout:** Card component that adapts to container size.

**Default size (3x2 grid units, ~300x200px):**

```
┌──────────────────────────────┐
│ Girls Enrolled    [On Track] │
│                              │
│       2,847                  │
│ Target: 3,000 (95%)         │
│                              │
│  ╱╲    ╱╲  ╱                │  ← sparkline (40px)
│ ╱  ╲╱╱  ╲╱                  │
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
- **Sparkline fills remaining vertical space** — `flex-1` with min-height 30px.
- **Click opens detail drawer** — Widgets are entry points, not destinations.
- **Footer: change indicator + timestamp** — Side by side at all sizes.

**States:**
- **Loading:** Skeleton matching widget layout
- **Error:** Centered AlertCircle + "Couldn't load" (text-sm)
- **Stale (>7 days):** Amber dot in top-right corner

---

### Screen 8: Component Selector Modal (Updated)

**Purpose:** Add "KPI" tab to the existing chart-selector-modal in dashboard builder.

**Layout:** Existing Dialog gains a TabsList with "Charts" and "KPIs" tabs.

```
┌──────────────────────────────────────────────────┐
│ Add Component                                [×] │
│ Choose a chart or KPI to add to your dashboard   │
│                                                  │
│  [Charts]  [KPIs]                                │  ← tabs
├──────────────────────────────────────────────────┤
│                                                  │
│  [🔍 Search KPIs...                          ]   │
│                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │ Girls      │  │ Dropout    │  │ Training   │ │
│  │ Enrolled   │  │ Rate       │  │ Hours      │ │
│  │        🟢  │  │        🟡  │  │        🟢  │ │
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
- **KPI preview cards** match the dashboard widget layout — Users see what they're about to add.
- **Mini sparkline in preview** — Helps distinguish KPIs. More scannable than just names.
- **RAG badge visible** — Critical selection context.
- **3-column grid** — Same as existing chart preview grid (from `chart-selector-modal.tsx`).
- **Click to add** — Closes modal, adds KPI widget to dashboard at next available grid position.

**Empty state:** Target icon + "No KPIs created yet" + link to KPI page.

---

## Cross-Cutting Specifications

### Typography Scale (for this feature)

| Element | Class | Used In |
|---------|-------|---------|
| Page title | `text-3xl font-bold` | All page headers |
| Section heading | `text-xl font-semibold` | Drawer sections |
| Card title | `text-base font-semibold` | Metric cards, KPI cards |
| KPI current value (card) | `text-4xl font-bold` | KPI page cards |
| KPI current value (drawer) | `text-5xl font-bold` | Detail drawer |
| KPI widget value | `text-3xl font-bold` | Dashboard widget (medium size) |
| Body text | `text-sm` | Descriptions, config details |
| Helper text | `text-xs text-muted-foreground` | Form hints, timestamps |
| Badge text | `text-xs` | Tags, RAG badges |

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

### Loading Patterns

| Context | Pattern |
|---------|---------|
| Card grids | 6 skeleton cards visible |
| Value computation | Skeleton rectangle matching text size |
| Trend chart | Skeleton rectangle at chart height |
| Form submission | Loader2 spinner in button, text changes to "-ing" form |
| Page-level | Centered Loader2 with specific message |

### Error Patterns

| Context | Pattern |
|---------|---------|
| Field validation | Red text below field on blur: "Metric name is required" |
| Incompatible selection | Amber alert below field: "Average only works with numbers. Try Count." |
| API error | Toast: `toastError("Couldn't save metric. Try again.")` |
| Load failure | Centered AlertCircle + message + [Retry] button |
| Delete blocked | AlertDialog listing consumers |
| Zero filter results | Amber warning: "No rows match these filters" |

### Accessibility Requirements

- **RAG badges:** Always text + color, never color-only ("On Track" not just green)
- **Focus states:** 2px ring in primary color on all interactive elements
- **Touch targets:** 44x44px minimum on mobile
- **Icon-only buttons:** Always have `aria-label`
- **Form inputs:** Visible `<Label>` elements, required indicator (`*`)
- **Trend charts:** `aria-label` describing the trend ("Girls Enrolled trend: increasing from 2,100 to 2,847 over 12 months")
- **Tab order:** Logical reading order in wizards (step indicator → content → navigation)

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
| `types/metrics.ts` | Type definitions for Metric, MetricCreate, etc. |
| `types/kpis.ts` | Type definitions for KPI, KPISummary, RAGStatus, etc. |
| `hooks/api/useMetrics.ts` | SWR hook for metrics CRUD |
| `hooks/api/useKPIs.ts` | SWR hook for KPIs CRUD + summary + trend |
| `app/metrics/page.tsx` | Screen 1: Metrics Library page |
| `app/kpis/page.tsx` | Screen 3: KPI Page |
| `components/metrics/metrics-library.tsx` | Metrics grid with search/filter |
| `components/metrics/metric-card.tsx` | Individual metric card |
| `components/metrics/metric-form.tsx` | Screen 2: Create/edit metric wizard |
| `components/metrics/metric-preview.tsx` | Value preview during creation |
| `components/kpis/kpi-page.tsx` | KPI grid with search/filter |
| `components/kpis/kpi-card.tsx` | Screen 3: Individual KPI card |
| `components/kpis/kpi-form.tsx` | Screen 4: Create/edit KPI wizard |
| `components/kpis/kpi-detail-drawer.tsx` | Screen 5: KPI detail sheet |
| `components/kpis/kpi-widget.tsx` | Screen 7: Dashboard KPI widget |
| `components/dashboard/kpi-widget-element.tsx` | Widget wrapper for dashboard grid |

### Modified Frontend Files
| File | Change |
|------|--------|
| `components/charts/MetricsSelector.tsx` → `MeasureSelector.tsx` | Rename + add tabs |
| `components/charts/ChartDataConfigurationV3.tsx` | Update import |
| `components/charts/MapDataConfigurationV3.tsx` | Update import |
| `components/dashboard/chart-selector-modal.tsx` | Add KPI tab |
| `components/dashboard/dashboard-builder-v2.tsx` | Handle `kpi` component type |
| `components/main-layout.tsx` | Add KPIs nav item, update Metrics visibility |

---

*Design document generated from [v1 spec](./spec.md), [implementation plan](./plan.md), Dalgo design system patterns, and NGO user perspective evaluation.*
