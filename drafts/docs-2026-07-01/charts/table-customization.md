---
sidebar_position: 4
---

# Table Customisation

**Control how your table chart looks and behaves — reorder columns, freeze the first column, apply colour themes, highlight rows with conditional formatting, and search within the table.**

Table customisation options are available in the **Customise** tab of the chart editor for any table chart.

## Reordering columns

1. Open your table chart in the chart editor.
2. Select the **Customise** tab.
3. Under **Column Order**, drag and drop columns into the order you want.

[SCREENSHOT: Column order panel showing drag handles next to column names]

:::note
If you have conditional formatting rules set up for specific columns, reordering those columns will show a warning. Check your conditional formatting rules after reordering to make sure they still apply to the right columns.
:::

## Aligning columns

1. In the **Customise** tab, select a column name.
2. Under **Alignment**, choose **Left**, **Centre**, or **Right**.

You can set a different alignment for each column.

## Freezing the first column

Select **Freeze first column** in the **Customise** tab. When your table has many columns, the first column stays visible as you scroll horizontally.

[SCREENSHOT: Table with frozen first column and horizontal scroll]

## Zebra rows

Select **Zebra rows** to add alternating background shading to rows. This makes wide tables easier to read across a row.

## Colour themes

Under **Colour Theme**, choose from the available themes to change the header and row colours of your table.

[SCREENSHOT: Table colour theme options]

## Conditional formatting

Highlight cells automatically based on their values.

1. In the **Customise** tab, select **Add Rule** under **Conditional Formatting**.
2. Choose the **column** to apply the rule to.
3. Set the **condition** (e.g. greater than, equal to, contains).
4. Choose the **highlight colour** to apply when the condition is true.
5. Select **Save Rule**.

You can add multiple rules. Rules apply to each drill-down level separately, so you can set different highlighting for different levels of a drill-down table.

[SCREENSHOT: Conditional formatting rule editor]

## Searching within a table

Select the **Search** icon inside the table (visible in both view and edit mode) to search for text across all cells. Matching cells are highlighted and a count of matches appears.

[SCREENSHOT: In-table search with highlighted matches]

## Exports with drill-down filters

When you export a table that is in a drill-down state (for example, you have drilled into a region), the exported file name and title include the active filter — so it is clear which level of data the export represents.

---

**Related:** [Chart Types](./chart-types.md) · [Creating a Chart](./creating-a-chart.md)
