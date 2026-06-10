# Style: Images

## Naming convention

```
{feature}_{description}.png
```

Examples: `pipeline_list.png`, `reports_create.png`, `sources_add.png`. Lowercase, underscores, short and descriptive.

## Directory mapping

| Content area | Image directory |
|---|---|
| Charts / Dashboards | `static/img/analysis/` |
| Orchestrate | `static/img/orchestrate/` |
| Transform | `static/img/transform/` |
| Pipeline overview, Data Quality, User Management | `static/img/managedata/` |
| Reports | `static/img/reports/` |
| Ingest (warehouse, sources, connections) | `static/img/ingest/` |
| Settings | `static/img/settings/` |

## Markdown reference syntax

Always standard markdown. Never import+JSX. Paths start with `/img/` (Docusaurus serves `static/` at site root).

```markdown
![Sources list](/img/ingest/sources_list.png)
```

## Missing screenshots

If a real screenshot isn't available, use `:::info Screenshot coming soon` — not an HTML comment.

```markdown
:::info Screenshot coming soon
A screenshot of the warehouse connection test will be added here.
:::
```
