# Style: Page Structure

Every reference page follows this structure:

```markdown
---
sidebar_position: {number}
---

# {Feature Name}

**{One-sentence summary of what this feature does or lets you do.}**

{1–2 paragraph intro if needed. What is this? When would you use it?}

## {First Section}

{Step-by-step instructions or explanation.}

## {Second Section}

{Continue as needed.}

---

**Next:** [Adjacent page](../path/page.md) · [Related page](../path/page.md)
```

## H1 titles: bare nouns matching the product nav label

Not a gerund, not a sentence.

| Product label | H1 | Not this |
|---|---|---|
| Charts | `# Charts` | `# Creating Charts` |
| Warehouse | `# Warehouse` | `# Setting up your Warehouse` |
| Orchestrate | `# Orchestrate` | `# Orchestrating your Pipeline` |

Task-focused headings (`## Creating a chart`) live at H2 inside the page.

## Bold one-liner after H1

Every page's first line after H1 is a **bold one-sentence promise**.

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

## Every page ends with a "Next" line

Two or three cross-references to logically adjacent pages. Use `**Related:**` instead of `**Next:**` for category index pages.

```markdown
---

**Next:** [Transform](../transform/index.md) · [Overview](../overview.md)
```

## Quickstart pages (different from reference)

- Cover one screen each — readable in 60 seconds
- End with "→ Next" and "→ Reference" links
- Don't duplicate reference content — link to it
- Reassuring, forward-moving tone

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
