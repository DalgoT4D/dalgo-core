# Dalgo Documentation Style Guide

Writing conventions for Dalgo's user-facing documentation. This guide codifies the patterns observed across existing doc pages and establishes standards for new content.

## Audience

Dalgo users are **non-technical NGO staff**: program managers, data coordinators, M&E officers, and field staff. Many are using a data platform for the first time.

**Plain language principles:**
- Write at a high-school reading level
- Explain what things do, not how they work internally
- If a technical term is unavoidable (e.g. "warehouse", "pipeline"), explain it in context the first time
- Use "you" and "your" — address the reader directly
- Prefer short sentences. One idea per sentence.

## Document Structure

Every doc page follows this structure:

```markdown
---
sidebar_position: {number}
---

# {Feature Name}

**{One-sentence summary of what this feature lets you do.}**

{1-2 paragraph introduction if needed. What is this? When would you use it?}

## {First Section}

{Step-by-step instructions or explanation.}

## {Second Section}

{Continue as needed.}
```

### Frontmatter

Required fields:
- `sidebar_position` — determines ordering within a sidebar category

Optional fields:
- `slug` — custom URL path (only use for special pages like `intro`)

Do not add other frontmatter fields unless Docusaurus requires them.

### H1 + Bold One-Liner

Every page starts with an H1 heading matching the feature name, immediately followed by a **bold one-liner** that summarizes what the feature does. This is the first thing a user reads.

Good:
```markdown
# Orchestrate

**Through this step Dalgo enables you to automate your data pipeline by setting up scheduled ingestion and transformation.**
```

Bad:
```markdown
# Orchestrate

The orchestration module provides pipeline scheduling capabilities with cron-based execution.
```

## Instructions Format

Use numbered steps for sequential actions. Each step should describe exactly one action the user takes.

### Rules

1. **Bold every UI element** the user needs to interact with: button labels, tab names, field labels, menu items.
2. Place a screenshot after the step it illustrates, not before.
3. Keep steps atomic — one click or one fill per step.
4. Use quotes for exact text the user should type, bold for UI labels they should click.

### Example

```markdown
1. Select **Orchestrate** on the left menu panel. You will see a list of your existing pipelines.

![Pipeline list](/img/orchestrate/pipeline_list.png)

2. Select **"+ Create Pipeline"** — this will take you to the "Create Pipeline" screen.

![Create pipeline](/img/orchestrate/pipeline_create.png)

3. Give your pipeline a name.
4. Select one or more of the connections you have set up.
```

## Admonitions

Use Docusaurus admonitions sparingly. Only when the information is genuinely important and should stand out from the surrounding text.

### `:::info` — Automatic or background behavior

Use when the system does something automatically that the user should know about but doesn't need to act on.

```markdown
:::info
The following tasks are automatically added before your transformation tasks and do not need to be configured manually:
1. **Git pull/clone** — pulls the latest code from the default branch.
2. **dbt clean** — removes compiled dbt artifacts.
3. **dbt deps** — installs dbt package dependencies.
:::
```

### `:::note` — Helpful context

Use for supplementary information that adds useful context but isn't critical to completing the task.

```markdown
:::note
Superset is only available if you have subscribed to Dalgo with Superset.
:::
```

### `:::warning` — Destructive or irreversible actions

Use when an action could cause data loss or is difficult to undo.

```markdown
:::warning
Deleting a connection will remove all sync history. This cannot be undone.
:::
```

**Do not** use `:::tip`, `:::danger`, or `:::caution` — keep to the three types above for consistency.

## Images

### Naming Convention

```
{feature}_{description}.png
```

Examples:
- `pipeline_list.png`
- `pipeline_create.png`
- `pipeline_edit.png`
- `pipeline_history.png`
- `elementary.png`

Use lowercase, underscores between words. Keep names short and descriptive.

### Directory Mapping

| Feature Area | Image Directory |
|-------------|-----------------|
| Orchestrate | `static/img/orchestrate/` |
| Transform | `static/img/transform/` |
| Managing Data | `static/img/managedata/` |
| Reports | `static/img/reports/` |
| Ingest | `static/img/ingest/` |
| Dashboards | `static/img/dashboards/` |

Create a new directory for a new feature area. Use the shortest reasonable name.

### Markdown Reference Syntax

Always use standard markdown:

```markdown
![Pipeline list](/img/orchestrate/pipeline_list.png)
```

The path starts with `/img/` because Docusaurus serves the `static/` directory at the site root.

### Screenshot Placeholders

When screenshots aren't available yet, use an HTML comment:

```markdown
<!-- SCREENSHOT: Description of what this screenshot should show -->
```

This makes it easy to find and replace later. Existing docs use this pattern (see `reports.md`).

## Sidebar Updates

When adding a new doc page, update `dalgo_docs/sidebars.js`.

### Adding to an existing category

Add the doc ID string to the category's `items` array:

```javascript
{
  type: 'category',
  label: 'Managing Data',
  items: [
    'managing-data/data-quality',
    'managing-data/pipeline-overview',
    'managing-data/usage-dashboard',
    'managing-data/user-management',
    'managing-data/new-page',        // new entry
  ],
}
```

### Adding a new top-level page

Add the doc ID string to the `tutorialSidebar` array at the appropriate position:

```javascript
const sidebars = {
  tutorialSidebar: [
    'intro',
    // ... existing items
    'new-top-level-page',
    'reports',
  ],
};
```

### Adding a new category

```javascript
{
  type: 'category',
  label: 'New Category Name',
  link: {type: 'doc', id: 'new-category/index'},
  items: [
    'new-category/first-page',
    'new-category/second-page',
  ],
}
```

The `link` property is optional — include it if the category should have its own landing page (an `index.md` file).

## Anti-Patterns

Things to avoid in Dalgo documentation:

| Don't | Do Instead |
|-------|------------|
| `import Image from '/static/img/...'` + JSX `<img src={Image} />` | `![Alt text](/img/path.png)` |
| External GitHub URLs for images (`https://github.com/...assets/...`) | Local images in `static/img/` |
| Code-structured docs (API references, config examples as primary content) | Task-oriented docs ("how to do X") |
| Passive voice ("The pipeline can be created by...") | Active voice ("Select **Create Pipeline** to...") |
| Jargon without explanation ("Configure the DAG schedule") | Plain language ("Set when your pipeline runs") |
| Long paragraphs of explanation before the first action | H1 + bold one-liner, then straight to steps |
| Multiple features on one page | One page per feature, split into sub-pages if needed |
| `:::tip` or `:::danger` admonitions | Stick to `:::info`, `:::note`, `:::warning` |
