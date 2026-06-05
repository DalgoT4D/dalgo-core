# Style: Writing

Read at least two existing pages before writing a new one — match their tone and density.

## Audience

Two personas, one voice:
- **Trained Dalgo user** — NGO program manager or M&E officer. Knows the platform, needs quick reference.
- **First-time user** — same profile, starting from scratch. Guided through Quickstart. Needs plain language and reassurance.

**Plain language rules:**
- High-school reading level.
- Explain what things do, not how they work internally.
- If a technical term is unavoidable ("warehouse", "pipeline", "dbt"), explain it in context the first time or link to the glossary.
- Use "you" and "your". One idea per sentence.

## Voice

| Don't | Do instead |
|---|---|
| "Click the button" | "Select **Create Pipeline**" |
| "The user should navigate to" | "Select **Reports** in the left menu" |
| "It is possible to" | "You can" |
| "In order to" | "To" |
| Passive voice | Active, second-person, present tense |

## Instructions format

Numbered steps for sequential actions. Each step = one action.

**Rules:**
1. **Bold every UI element** the user interacts with: button labels, tab names, field labels, menu items, icon names.
2. Place a screenshot after the step it illustrates, not before.
3. Keep steps atomic — one click or one fill per step.
4. Use "Select" not "Click" (works for touchscreens too).
5. Quotes for exact text the user types; bold for UI labels they click.
6. **Never break a numbered list with an admonition block.** Docusaurus resets the counter after any block-level element — a step numbered "5." after `:::info` renders as "1.". Place admonitions after the last step, or fold the note inline.

**Example:**
```markdown
1. Select **Data** in the left menu, then select **Ingest**.

![Connections list](/img/ingest/connections_list.png)

2. Select **+ Add Connection**.
3. Give your connection a name and select the source.
4. Select **Connect** to save.
```

## Anti-patterns

| Don't | Why |
|---|---|
| `import Image from '/static/img/...'` + JSX | Docusaurus markdown renderer doesn't need it — breaks consistency |
| `<!-- SCREENSHOT: ... -->` HTML comments on main | Invisible in rendered docs — dishonest gap; use `:::info` instead |
| External GitHub URLs for images | Images move; use local `static/img/` |
| H1 titles with gerunds ("Creating your Dashboard") | Product labels are the H1 — gerunds live at H2 |
| Blockquotes for important notes (`> Note:`) | Use admonitions (`:::note`) |
| Multiple unrelated features on one page | One page per feature — split if needed |
| `:::tip`, `:::danger`, `:::caution` | Not used in Dalgo docs |
| Duplicating dbt/Superset upstream docs | Link to docs.getdbt.com or superset.apache.org |
| Long intro paragraphs before the first action | H1 + bold one-liner → straight into steps |
