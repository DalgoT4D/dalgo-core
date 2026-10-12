# Sidebar changes needed in dalgo_docs/sidebars.js

## New pages to add

### 1. Settings > Branding (new page)

In the `Settings` category, add `'settings/branding'`:

```javascript
{
  type: 'category',
  label: 'Settings',
  link: { type: 'doc', id: 'settings/index' },
  items: [
    'settings/user-management',
    'settings/branding',       // ← ADD THIS
    'settings/billing',
    'settings/about',
  ],
}
```

### 2. Charts > KPI Number Formatting (new page)

In the `Charts` category, add `'charts/kpi-number-formatting'`:

```javascript
{
  type: 'category',
  label: 'Charts',
  link: { type: 'doc', id: 'charts/index' },
  items: [
    'charts/creating-a-chart',
    'charts/chart-types',
    'charts/kpi-number-formatting',   // ← ADD THIS
    'charts/table-customization',     // ← ADD THIS
  ],
}
```

### 3. Charts > Table Customisation (new page)

See above — add `'charts/table-customization'` alongside `kpi-number-formatting`.

## Files to copy into dalgo_docs

| Draft file | Destination in dalgo_docs |
|---|---|
| `charts/kpi-number-formatting.md` | `docs/charts/kpi-number-formatting.md` |
| `charts/table-customization.md` | `docs/charts/table-customization.md` |
| `settings/branding.md` | `docs/settings/branding.md` |
