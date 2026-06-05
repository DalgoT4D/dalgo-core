# Doc Repo Structure

Layout of the `dalgo_docs/` repo (symlinked at `dalgo-core/dalgo_docs`).

```
dalgo_docs/
  docs/
    welcome.md
    quickstart/
      index.md
      account-setup.md
      impact.md
      first-dashboard.md
      first-report.md
      next-steps.md
    concepts/glossary.md
    impact/index.md
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
      ingest/{index,connections,sources,warehouse}.md
      transform/{index,ui-transform,dbt-transform,switching-repositories}.md
    settings/{index,user-management,billing,about}.md
    support/{index,getting-help,troubleshooting}.md
  static/img/{analysis,orchestrate,transform,managedata,reports,ingest,settings}/
  sidebars.js
  docusaurus.config.js
  src/{css/custom.css,pages/index.tsx}
```

## Images: placement & usage

- **Where they live:** `static/img/{feature}/` — one folder per feature area. See `style-images.md` for the full content-area → directory mapping.
- **How they're referenced in markdown:** standard markdown syntax with paths starting `/img/` (Docusaurus serves `static/` at the site root):
  ```markdown
  ![Sources list](/img/ingest/sources_list.png)
  ```
  Never use import + JSX.
- **Naming:** `{feature}_{description}.png`, lowercase, underscores.
- **Placement on a page:** screenshot goes *after* the step it illustrates, never before. One screenshot per major step.

For naming, dir mapping, and missing-screenshot handling, see `style-images.md`.

## Screenshot capture

- Capture with `scripts/screenshot.py` (recipe-driven). Bulk = no args; per-feature = pass the recipe name. See `workflow.md` step 5.
- **No `<!-- SCREENSHOT: ... -->` HTML comment placeholders** shipped to main. Use `:::info Screenshot coming soon` instead — it's honest and renders correctly.
