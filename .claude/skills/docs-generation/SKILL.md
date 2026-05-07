---
name: docs-generation
description: Generate and maintain Docusaurus documentation for Dalgo features. Use when creating new doc pages, updating existing docs, or reviewing documentation for completeness. Provides feature-to-route mapping, doc repo structure, and sidebar conventions.
---

# Docs Generation Skill

Reference for generating Dalgo's user-facing documentation. Maps features to webapp routes and doc locations, defines the doc repo structure, and provides sidebar conventions.

## How to Use

This skill is loaded by the `/product/generate-docs` command. It can also be used standalone when:
- Reviewing whether documentation is up to date after a feature change
- Checking where a new doc page should live
- Understanding the current sidebar structure

## Feature-to-Route Mapping

| Feature | Webapp Route(s) | Doc Location | Image Directory |
|---------|-----------------|--------------|-----------------|
| Ingest (overview) | `/ingest` | `docs/ingest/index.md` | `static/img/ingest/` |
| Warehouse setup | `/ingest` (warehouse tab) | `docs/ingest/warehouse.md` | `static/img/ingest/` |
| Sources | `/ingest` (sources tab) | `docs/ingest/sources.md` | `static/img/ingest/` |
| Connections | `/ingest` (connections tab) | `docs/ingest/connections.md` | `static/img/ingest/` |
| Transform | `/transform` | `docs/transform.md` | `static/img/transform/` |
| Transform canvas | `/transform/canvas` | `docs/transform.md` | `static/img/transform/` |
| Orchestrate | `/orchestrate`, `/orchestrate/create` | `docs/orchestrate.md` | `static/img/orchestrate/` |
| Dashboards (overview) | `/dashboards` | `docs/analysis/index.md` | `static/img/dashboards/` |
| Dalgo dashboards | `/dashboards`, `/dashboards/create`, `/dashboards/[id]` | `docs/analysis/dalgo-dashboards.md` | `static/img/dashboards/` |
| Superset | (external) | `docs/analysis/superset.md` | `static/img/dashboards/` |
| Charts | `/charts`, `/charts/new` | `docs/analysis/dalgo-dashboards.md` | `static/img/dashboards/` |
| Reports | `/reports`, `/reports/[id]` | `docs/reports.md` | `static/img/reports/` |
| Data quality | `/data-quality` | `docs/managing-data/data-quality.md` | `static/img/managedata/` |
| Pipeline overview | `/pipeline` | `docs/managing-data/pipeline-overview.md` | `static/img/managedata/` |
| Usage dashboard | `/dashboards/usage` | `docs/managing-data/usage-dashboard.md` | `static/img/managedata/` |
| User management | `/settings/user-management` | `docs/managing-data/user-management.md` | `static/img/managedata/` |
| Impact / Home | `/impact` | `docs/intro.md` | `static/img/` |

## Current Sidebar Structure

```
tutorialSidebar:
  - intro
  - Ingest (category, links to ingest/index)
      - ingest/warehouse
      - ingest/sources
      - ingest/connections
  - transform
  - orchestrate
  - Dashboards (category, links to analysis/index)
      - analysis/dalgo-dashboards
      - analysis/superset
  - Managing Data (category, no index link)
      - managing-data/data-quality
      - managing-data/pipeline-overview
      - managing-data/usage-dashboard
      - managing-data/user-management
  - reports
```

## Doc Repo Structure

```
dalgo_docs/
  docs/                        # Markdown source files
    intro.md                   # Landing page (sidebar_position: 1)
    transform.md               # Top-level pages
    orchestrate.md
    reports.md
    ingest/                    # Category with index
      index.md
      warehouse.md
      sources.md
      connections.md
    analysis/                  # Category with index
      index.md
      dalgo-dashboards.md
      superset.md
    managing-data/             # Category without linked index
      index.md
      data-quality.md
      pipeline-overview.md
      usage-dashboard.md
      user-management.md
  static/
    img/                       # Screenshots and images
      orchestrate/             # One directory per feature area
      transform/
      managedata/
      reports/
      welcome-email.png        # Standalone images at root
  sidebars.js                  # Sidebar configuration
  docusaurus.config.js         # Site configuration
```

## Image Reference Pattern

Use standard markdown image syntax. Do **not** use import+JSX.

```markdown
![Pipeline list](/img/orchestrate/pipeline_list.png)
```

Not this:
```markdown
import PipelineList from '/static/img/orchestrate/pipeline_list.png';
<img src={PipelineList} />
```

Image paths in markdown start with `/img/` (Docusaurus serves `static/` at the root).

## Adding to the Sidebar

See `dalgo_docs/sidebars.js`. Three patterns:

**Top-level page** (like `transform`, `orchestrate`):
```javascript
const sidebars = {
  tutorialSidebar: [
    'intro',
    // ... existing items
    'new-page-id',   // doc ID = filename without .md
  ],
};
```

**New page in existing category** (like adding to "Managing Data"):
```javascript
{
  type: 'category',
  label: 'Managing Data',
  items: [
    'managing-data/data-quality',
    // ... existing items
    'managing-data/new-page',   // add here
  ],
}
```

**New category**:
```javascript
{
  type: 'category',
  label: 'New Category',
  link: {type: 'doc', id: 'new-category/index'},
  items: [
    'new-category/page-one',
    'new-category/page-two',
  ],
}
```

## Related Files

- `style-guide.md` in this directory — writing conventions, formatting rules, anti-patterns
- `scripts/screenshot.py` — Playwright screenshot utility for capturing app screenshots
