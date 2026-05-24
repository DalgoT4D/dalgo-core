# Dalgo Documentation Style Guide

Writing conventions for Dalgo's user-facing documentation. Read at least two existing pages before writing a new one — match their tone and density, don't exceed them in length.

---

## Audience

Two personas, one voice:

- **Trained Dalgo user** — NGO program manager or M&E officer. Knows the platform, needs quick reference. Doesn't want theory.
- **First-time user** — same profile, but starting from scratch. Guided through the Quickstart. Needs plain language and reassurance.

**Plain language rules:**
- Write at a high-school reading level.
- Explain what things do, not how they work internally.
- If a technical term is unavoidable (e.g. "warehouse", "pipeline", "dbt"), explain it in context the first time. Or link to the glossary.
- Use "you" and "your". Address the reader directly.
- One idea per sentence. Short sentences.

---

## Page structure

Every page follows this structure:

```markdown
---
sidebar_position: {number}
---

# {Feature Name}

**{One-sentence summary of what this feature does or lets you do.}**

{1–2 paragraph introduction if needed. What is this? When would you use it?}

## {First Section}

{Step-by-step instructions or explanation.}

## {Second Section}

{Continue as needed.}

---

**Next:** [Adjacent page](../path/page.md) · [Related page](../path/page.md)
```

### H1 titles are bare nouns matching the product nav label

Use the product's label as the H1 — not a gerund, not a sentence.

| Product label | H1 | Not this |
|---|---|---|
| Charts | `# Charts` | `# Creating Charts` |
| Warehouse | `# Warehouse` | `# Setting up your Warehouse` |
| Orchestrate | `# Orchestrate` | `# Orchestrating your Pipeline` |

Task-focused headings (`## Creating a chart`, `## Editing a connection`) live at H2 level inside the page.

### Bold one-liner after H1

Every page's first line after the H1 is a **bold one-sentence promise**: what this page covers or what the feature does.

Good:
```markdown
# Orchestrate

**Orchestrate lets you schedule your data pipeline to run automatically — combining sync connections and transformation tasks into a single job.**
```

Bad:
```markdown
# Orchestrate

The orchestration module provides pipeline scheduling capabilities with cron-based execution.
```

### Every page ends with a "Next" line

Two or three cross-references to logically adjacent pages. This stitches pages into a system.

```markdown
---

**Next:** [Transform](../transform/index.md) · [Overview](../overview.md)
```

Or for category index pages:
```markdown
---

**Related:** [Dashboards](../dashboards/index.md) · [Reports](../reports/index.md)
```

---

## Instructions format

Use numbered steps for sequential actions. Each step = one action.

### Rules

1. **Bold every UI element** the user needs to interact with: button labels, tab names, field labels, menu items, icon names.
2. Place a screenshot after the step it illustrates, not before.
3. Keep steps atomic — one click or one fill per step.
4. Use "Select" not "Click" (works for touchscreens too).
5. Use quotes for exact text the user should type, bold for UI labels they click.
6. **Never break a numbered list with an admonition block.** Docusaurus resets the counter after any block-level element, so a step numbered "5." after a `:::info` block renders as "1.". Either place the admonition after the last step, or fold the note inline within the step text.

### Example

```markdown
1. Select **Data** in the left menu, then select **Ingest**.

![Connections list](/img/ingest/connections_list.png)

2. Select **+ Add Connection**.
3. Give your connection a name and select the source you want to sync.
4. Select **Connect** to save.
```

---

## Voice

| Don't | Do instead |
|---|---|
| "Click the button" | "Select **Create Pipeline**" |
| "The user should navigate to" | "Select **Reports** in the left menu" |
| "It is possible to" | "You can" |
| "In order to" | "To" |
| Passive voice | Active, second-person, present tense |

---

## Admonitions

Use sparingly. Only when the content genuinely needs to stand out.

### `:::info` — Automatic behaviour or "good to know"

Use when the system does something the user should know about but doesn't act on. Also use for "Screenshot coming soon" when a screenshot isn't available yet.

```markdown
:::info
Dalgo creates a draft dashboard the moment you select **+ Create Dashboard**. If you leave without saving, the draft is kept.
:::

:::info Screenshot coming soon
A screenshot of the warehouse connection test will be added here.
:::
```

### `:::note` — Helpful context or prerequisites

Use for supplementary information that adds useful context but isn't critical to completing the task. Also use for conditional feature availability.

```markdown
:::note
Superset is only available to organisations on the **Dalgo + Superset** plan.
:::

:::note
You may need to whitelist these IP addresses in your firewall: `13.202.128.47`, `65.2.173.97`
:::
```

### `:::warning` — Destructive or irreversible actions

Use when an action could cause data loss or is difficult to undo *once confirmed*. Dalgo often shows a confirmation dialog before a destructive action — the `:::warning` belongs near the action, not on the confirmation step itself. Do not write "This cannot be undone without canceling" — that is confusing. Write what happens after the user confirms.

```markdown
:::warning
Deleting a connection is permanent and removes all its sync history. This cannot be undone.
:::
```

**Do not use** `:::tip`, `:::danger`, or `:::caution`. Stick to these three.

### Declaring conditional features

When a feature requires a specific subscription or setup, declare it at the top of the page with `:::note`:

```markdown
:::note
The Superset Usage dashboard requires a **Dalgo + Superset** subscription. Contact support@dalgo.org to add it to your subscription.
:::
```

---

## Quickstart pages

Quickstart pages are different from reference pages. They:
- Cover one screen each — short enough to read in 60 seconds
- End with "→ Next: [next step]" and "→ Reference: [reference page]" links
- Don't duplicate reference page content — they link to it
- Use a reassuring, forward-moving tone

Template:
```markdown
---
sidebar_position: {N}
---

# {Step name}

**{What this step achieves in one sentence.}**

## Steps

1. ...
2. ...

:::note
{Optional prerequisite or "if this doesn't work" note}
:::

---

→ Next: [{next step}]({next-step}.md)
→ Reference: [{reference page}]({../section/page}.md)
```

---

## Images

### Naming convention

```
{feature}_{description}.png
```

Examples: `pipeline_list.png`, `reports_create.png`, `sources_add.png`

Lowercase, underscores, short and descriptive.

### Directory mapping

| Content area | Image directory |
|---|---|
| Charts / Dashboards | `static/img/analysis/` |
| Orchestrate | `static/img/orchestrate/` |
| Transform | `static/img/transform/` |
| Pipeline overview, Data Quality, User Management | `static/img/managedata/` |
| Reports | `static/img/reports/` |
| Ingest (warehouse, sources, connections) | `static/img/ingest/` |
| Settings | `static/img/settings/` |

### Markdown reference syntax

Always use standard markdown. Never import+JSX.

```markdown
![Sources list](/img/ingest/sources_list.png)
```

### Missing screenshots

If a real screenshot isn't available, use `:::info Screenshot coming soon` — not an HTML comment.

```markdown
:::info Screenshot coming soon
A screenshot of the warehouse connection test will be added here.
:::
```

---

## What not to do

| Don't | Why |
|---|---|
| `import Image from '/static/img/...'` + JSX | Docusaurus markdown renderer doesn't need it — breaks consistency |
| `<!-- SCREENSHOT: ... -->` HTML comments shipped to main | Invisible in rendered docs — dishonest gap; use `:::info` instead |
| External GitHub URLs for images | Images move; use local `static/img/` |
| H1 titles with gerunds ("Creating your Dashboard") | Product labels are the H1 — gerunds live at H2 |
| Blockquotes for important notes (`> Note:`) | Use admonitions (`:::note`) — they render properly |
| Multiple unrelated features on one page | One page per feature — split if needed |
| `:::tip`, `:::danger`, `:::caution` | Not used in Dalgo docs — inconsistent rendering |
| Duplicating dbt or Superset upstream docs | Link to docs.getdbt.com or superset.apache.org instead |
| Long intro paragraphs before the first action | H1 + bold one-liner → straight into steps |
