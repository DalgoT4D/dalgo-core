# Sidebar Structure & Patterns

Sidebar lives in `dalgo_docs/sidebars.js`. Mirrors the product left-nav exactly.

## Current Structure

```
tutorialSidebar:
  1. welcome                              ← docs/welcome.md
  2. Quickstart (category → quickstart/index)
       account-setup
       impact
       first-dashboard
       first-report
       next-steps
  3. Concepts (category)
       concepts/glossary
  4. Impact (category → impact/index)     ← no child items
  5. Charts (category → charts/index)
       charts/creating-a-chart
       charts/chart-types
  6. Dashboards (category → dashboards/index)
       dashboards/superset-usage
       dashboards/superset
  7. Reports (category → reports/index)
       reports/creating
       reports/comments
       reports/sharing
       reports/exporting
  8. Data (category → data/index)
       data/overview
       Ingest (nested category → data/ingest/index)
           data/ingest/connections
           data/ingest/sources
           data/ingest/warehouse
       Transform (nested category → data/transform/index)
           data/transform/ui-transform
           data/transform/dbt-transform
           data/transform/switching-repositories
       data/orchestrate
       data/explore
       data/quality
  9. Settings (category → settings/index)
       settings/user-management
       settings/billing
       settings/about
  10. Support (category → support/index)
       support/getting-help
       support/troubleshooting
```

## Adding to the Sidebar

**New page in existing category:**
```javascript
{
  type: 'category',
  label: 'Reports',
  link: { type: 'doc', id: 'reports/index' },
  items: [
    'reports/creating',
    'reports/new-page',   // add here
  ],
}
```

**New top-level page** (rarely needed):
```javascript
tutorialSidebar: [
  'welcome',
  // ...
  'new-top-level-page',
]
```

**New category:**
```javascript
{
  type: 'category',
  label: 'New Section',
  link: { type: 'doc', id: 'new-section/index' },
  items: [
    'new-section/page-one',
    'new-section/page-two',
  ],
}
```
