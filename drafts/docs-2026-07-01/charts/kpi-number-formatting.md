---
sidebar_position: 3
---

# KPI Number Formatting

**Format the numbers on your KPI cards — add units, percentage symbols, or compact notation — and the same formatting carries through to alerts and reports automatically.**

KPI cards now support the same number formatting options available on number charts. Once you set a format, it applies everywhere that KPI value appears: the dashboard widget, alert emails, frozen reports, and the annotation view.

## Setting a number format on a KPI

1. Open the **Charts** section and select your KPI chart, or create a new one by selecting **+ New Chart** and choosing **KPI**.
2. In the chart editor, select the **Customise** tab.
3. Under **Number Format**, choose the format that fits your data:

| Format | What it does | Example |
|---|---|---|
| **Default** | Shows the raw number | 85000 |
| **Locale** | Adds comma separators | 85,000 |
| **Compact** | Shortens large numbers | 85K |
| **Percentage** | Multiplies by 100 and adds % | 85% (from 0.85) |

4. Optionally add a **Prefix** (e.g. `₹`) or **Suffix** (e.g. `beneficiaries`) to appear before or after the number.
5. Select **Save**.

[SCREENSHOT: KPI chart editor showing Number Format options with prefix/suffix fields]

:::note
The **percentage format** treats your raw value as a decimal and multiplies by 100. For example, if your data contains `0.85`, it displays as `85%`. If your data already contains `85`, use a suffix of `%` instead.

The **Currency** format option has been removed from all chart types — it only added a prefix, which the **Prefix** field now handles more flexibly.
:::

## How formatting flows through alerts

If you have an alert set up on a KPI, the alert email and notification now show the same formatted value as the KPI card — not the raw number. No extra setup is needed.

For example, if your KPI shows **42K beneficiaries reached** and an alert is triggered, the alert message will say **42K**, not **42000**.

## How formatting appears in reports and dashboards

- **Dashboard KPI widgets** — show the formatted value once you save.
- **Frozen report snapshots** — capture the formatting that was active when the snapshot was created. Later changes to the format do not update old snapshots.
- **KPI annotation view** — shows the formatted value alongside the annotation.

---

**Related:** [Creating a Chart](./creating-a-chart.md) · [Chart Types](./chart-types.md) · [Alerts](../reports/creating.md)
