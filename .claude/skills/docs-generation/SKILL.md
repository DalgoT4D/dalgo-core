---
name: docs-generation
description: Generate and maintain Docusaurus documentation for Dalgo features. Use when creating new doc pages, updating existing docs, or reviewing documentation for completeness. Provides feature-to-route mapping, doc repo structure, sidebar conventions, and writing standards.
---

# Docs Generation Skill

Reference for generating Dalgo's user-facing documentation. Maps features to webapp routes and doc locations, defines the doc repo structure, sidebar conventions, and the IA principles that govern where content lives.

## PR Filtering Rules (for bi-weekly scan)

When scanning merged PRs for documentation needs, apply these rules:

**Always document:**
- New UI pages, flows, or settings the user interacts with
- New pipeline/dashboard/report behaviours or configuration options
- UX changes that alter how a user completes a task (e.g. a new "Load more" button changes how users read logs)

**Document briefly (one sentence update to the relevant section):**
- Bug fixes that restore previously broken behaviour for a specific named integration (e.g. "SharePoint source connector creation now works correctly")

**Skip:**
- Internal refactors, test-only changes, CI/CD, dependency bumps
- Monitoring/error-tracking changes (Sentry, Pendo, analytics) — these are invisible to users
- Infrastructure changes (worker pools, queues, EKS) — no user-visible effect
- Bug fixes that restore generic behaviour already described by existing docs (no mention needed)

**Paired PRs (backend + frontend for the same feature):**
When a backend repo and a frontend repo both have PRs for the same feature (e.g. "add multi-tab support to dashboards"), document the feature **once** from the user's perspective. Reference both PR numbers in the commit message but don't write separate docs for each. The user only cares what they can see and do — not which layer implemented it.

## IA Principles (read before writing anything)

The sidebar mirrors the product left-nav exactly. Sections 1–3 are docs-only orientation. Sections 4–9 match the product navigation order. Section 10 is support convention.

**Rule:** If a section exists in the product nav, it exists in the docs sidebar at the same level and with the same label. Don't invent groupings that don't exist in the product.

### Two entry points, one set of reference pages

- **Quickstart** (`quickstart/`) — short linear path for first-time users. Each page is one screen. Ends with "→ Next" links. Links *into* reference pages rather than duplicating them.
- **Reference** (all other sections) — feature docs. Trained users jump straight here. No assumed linear reading order.

### Three user personas

1. **Trained Dalgo user** (primary) — day-to-day user who wants reference docs they can jump into. Assumes pipelines are already set up.
2. **First-time independent user** (secondary) — needs the Quickstart linear path.
3. **Implementation partner** (tertiary) — uses the same producer-track reference but benefits from `:::note For implementation partners` callouts on pages like Warehouse setup, Transform repo switching, and User Management.

## Feature-to-Route Mapping

| Feature | Webapp Route(s) | Doc Location | Image Directory |
|---|---|---|---|
| Welcome / orientation | — | `docs/welcome.md` | `static/img/` |
| Quickstart | — | `docs/quickstart/` | `static/img/` |
| Glossary | — | `docs/concepts/glossary.md` | — |
| Impact / home screen | `/impact` | `docs/impact/index.md` | `static/img/impact/` |
| Charts (list) | `/charts` | `docs/charts/index.md` | `static/img/analysis/` |
| Charts (create/edit) | `/charts/new`, `/charts/[id]` | `docs/charts/creating-a-chart.md` | `static/img/analysis/` |
| Chart types | `/charts/new` (type selector) | `docs/charts/chart-types.md` | `static/img/analysis/` |
| Dashboards (list/create) | `/dashboards` | `docs/dashboards/index.md` | `static/img/analysis/` |
| Superset Usage | `/dashboards/usage` | `docs/dashboards/superset-usage.md` | `static/img/managedata/` |
| Superset | (external/embedded) | `docs/dashboards/superset.md` | `static/img/dashboards/` |
| Reports (overview/list) | `/reports` | `docs/reports/index.md` | `static/img/reports/` |
| Reports (create/view) | `/reports`, `/reports/[id]` | `docs/reports/creating.md` | `static/img/reports/` |
| Reports (comments/summary) | `/reports/[id]` | `docs/reports/comments.md` | `static/img/reports/` |
| Reports (sharing) | `/reports/[id]` | `docs/reports/sharing.md` | `static/img/reports/` |
| Reports (export/delete) | `/reports/[id]` | `docs/reports/exporting.md` | `static/img/reports/` |
| Data (section overview) | `/data` | `docs/data/index.md` | — |
| Pipeline Overview | `/data` (Overview tab) | `docs/data/overview.md` | `static/img/managedata/` |
| Ingest (overview) | `/ingest` | `docs/data/ingest/index.md` | `static/img/ingest/` |
| Connections | `/ingest` (connections tab) | `docs/data/ingest/connections.md` | `static/img/ingest/` |
| Sources | `/ingest` (sources tab) | `docs/data/ingest/sources.md` | `static/img/ingest/` |
| Warehouse | `/ingest` (warehouse tab) | `docs/data/ingest/warehouse.md` | `static/img/ingest/` |
| Transform (overview) | `/transform` | `docs/data/transform/index.md` | `static/img/transform/` |
| UI Transform | `/transform` (UI tab) | `docs/data/transform/ui-transform.md` | `static/img/transform/` |
| DBT Transform | `/transform` (DBT tab) | `docs/data/transform/dbt-transform.md` | `static/img/transform/` |
| Switching repositories | `/transform` (edit repo) | `docs/data/transform/switching-repositories.md` | `static/img/transform/` |
| Orchestrate | `/orchestrate` | `docs/data/orchestrate.md` | `static/img/orchestrate/` |
| Explore | `/explore` | `docs/data/explore.md` | `static/img/data/` |
| Data Quality | `/data-quality` | `docs/data/quality.md` | `static/img/managedata/` |
| Settings (overview) | `/settings` | `docs/settings/index.md` | — |
| User Management | `/settings/user-management` | `docs/settings/user-management.md` | `static/img/managedata/` |
| Billing | `/settings/billing` | `docs/settings/billing.md` | `static/img/settings/` |
| About | `/settings/about` | `docs/settings/about.md` | `static/img/settings/` |
| Support | — | `docs/support/index.md` | — |

## Sidebar Structure

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

## Doc Repo Structure

```
dalgo_docs/
  docs/
    welcome.md                 # Orientation + platform overview
    quickstart/
      index.md
      account-setup.md
      impact.md
      first-dashboard.md
      first-report.md
      next-steps.md
    concepts/
      glossary.md
    impact/
      index.md
    charts/
      index.md
      creating-a-chart.md
      chart-types.md
    dashboards/
      index.md
      superset-usage.md
      superset.md
    reports/
      index.md
      creating.md
      comments.md
      sharing.md
      exporting.md
    data/
      index.md
      overview.md
      explore.md
      orchestrate.md
      quality.md
      ingest/
        index.md
        connections.md
        sources.md
        warehouse.md
      transform/
        index.md
        ui-transform.md
        dbt-transform.md
        switching-repositories.md
    settings/
      index.md
      user-management.md
      billing.md
      about.md
    support/
      index.md
      getting-help.md
      troubleshooting.md
  static/
    img/
      analysis/        # Charts and dashboards screenshots
      orchestrate/
      transform/
      managedata/      # data-quality, pipeline-overview, user-management screenshots
      reports/
      ingest/
      settings/
      welcome-email.png
  sidebars.js
  docusaurus.config.js
  src/
    css/custom.css
    pages/index.tsx
```

## Image Reference Pattern

Use standard markdown image syntax only. Do **not** use import+JSX.

```markdown
![Pipeline list](/img/orchestrate/pipeline_list.png)
```

Image paths start with `/img/` (Docusaurus serves `static/` at the site root).

## Adding to the Sidebar

See `dalgo_docs/sidebars.js`. Three patterns:

**New top-level page** (rarely needed — most content lives in a section):
```javascript
tutorialSidebar: [
  'welcome',
  // ...
  'new-top-level-page',
]
```

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

## Screenshot Policy

- **No `<!-- SCREENSHOT: ... -->` HTML comment placeholders** shipped to main. If a real screenshot is not available, use a `:::info Screenshot coming soon` admonition instead. It's honest and renders correctly.
- Screenshots live in `static/img/{feature}/`. File naming: `{feature}_{description}.png`, lowercase, underscores.
- Capture with the Playwright script at `scripts/screenshot_docs_all.py` using the staging environment.

## Self-improvement workflow

When improving this skill after a bi-weekly run, **never commit to `main`**. Always use a branch:

```bash
git checkout -b improve/docs-generation-skill
git add .claude/skills/docs-generation/SKILL.md
git commit -m "improve(skills): ..."
git push -u origin improve/docs-generation-skill
# open a PR — do not merge automatically
```

If `git push` returns 403 (the session's git credentials may not have write access), use `mcp__github__push_files` targeting the branch name instead of `main`:

```
mcp__github__push_files  owner=dalgot4d  repo=dalgo-core  branch=improve/docs-generation-skill
```

## Related Files

- `style-guide.md` in this directory — writing conventions, page structure, voice, admonition rules
- `scripts/screenshot_docs_all.py` — Playwright screenshot capture for all doc pages
