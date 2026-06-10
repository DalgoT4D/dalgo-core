---
name: documentation
description: Generate, update, or review Dalgo user-facing documentation. Use when the user asks to document a feature, write a docs page, update existing docs, or after a PR ships to refresh affected docs.
---

# Documentation Skill

Reference and workflow for generating Dalgo's user-facing Docusaurus documentation. Lives in the `dalgo_docs/` repo (symlinked into `dalgo-core/`).

## When to use

Trigger when the user asks to:
- Generate or update a doc page for a feature ("write docs for orchestrate")
- Refresh docs after a PR or commit range ("update docs for #142")
- Review existing docs for completeness or accuracy

Start by reading `workflow.md`.

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

## File index

| File | Purpose |
|------|---------|
| `workflow.md` | Step-by-step process from research to published markdown |
| `sidebar.md` | Sidebar structure + patterns for adding new entries |
| `repo-structure.md` | Doc repo layout + screenshot policy |
| `style-writing.md` | Audience + voice + instructions format + anti-patterns |
| `style-page.md` | Page structure + quickstart template |
| `style-admonitions.md` | Admonition rules + conditional features |
| `style-images.md` | Image naming + directory mapping + markdown syntax |
