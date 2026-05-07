# Generate Documentation

## Input: $ARGUMENTS

Generate or update Docusaurus documentation for a feature, from research through screenshots to published markdown.

## What the PM runs

```
/product/generate-docs "orchestrate"
/product/generate-docs "#142"
/product/generate-docs "abc123..def456"
```

## What it produces

- A new or updated markdown page in `dalgo_docs/docs/`
- Screenshots in `dalgo_docs/static/img/{feature}/`
- Updated `dalgo_docs/sidebars.js` (if new page)

---

## Process

### 1. Parse Input & Determine Mode

**Mode A — Feature Name** (default):
- `$ARGUMENTS` is a feature description (e.g. `"orchestrate"`, `"data quality"`, `"user management"`)
- Used to look up the feature in the docs-generation skill's feature-to-route table

**Mode B — PR / Commits**:
- `$ARGUMENTS` contains a PR number (`#142`), a GitHub URL (`https://github.com/.../pull/142`), or a commit range (`abc123..def456`)
- Used to identify what changed and which feature area is affected

To determine mode: if `$ARGUMENTS` matches `#\d+`, a GitHub PR URL, or a `\w+\.\.\w+` commit range pattern, use Mode B. Otherwise, Mode A.

### 2. Load the Docs-Generation Skill

Read the following files for conventions and reference:
- `.claude/skills/docs-generation/SKILL.md` — feature-to-route mapping, doc repo structure, sidebar categories
- `.claude/skills/docs-generation/style-guide.md` — writing conventions, formatting rules, anti-patterns

### 3. Research the Feature

**Mode A (Feature Name):**
1. Map the feature to its webapp route using SKILL.md's feature-to-route table.
2. Read the frontend page components in `webapp_v2/app/{route}/` to understand the UI.
3. Read related backend endpoints in `DDP_backend/` if the feature has API interactions.
4. Check existing docs in `dalgo_docs/docs/` — is there already a page for this feature?
5. Check existing images in `dalgo_docs/static/img/` — what screenshots already exist?

**Mode B (PR / Commits):**
1. Run `gh pr diff $PR_NUMBER` or `git diff $COMMIT_RANGE` to see changes.
2. Identify which feature area the changes affect by looking at changed file paths.
3. Read the changed files in full context to understand the new behavior.
4. Check existing docs — does the affected feature already have documentation?
5. Determine whether this requires a new doc page or an update to existing docs.

### 4. Determine Doc Placement

Based on research, decide:
- **Directory**: which folder under `dalgo_docs/docs/` (e.g. `docs/`, `docs/ingest/`, `docs/managing-data/`)
- **File**: new page or update to existing page
- **Sidebar position**: where it fits in the current sidebar structure
- **Image directory**: corresponding folder under `dalgo_docs/static/img/`

Print the placement plan:

```
Placement plan:
- Doc: dalgo_docs/docs/{path}/{filename}.md
- Images: dalgo_docs/static/img/{feature}/
- Sidebar: {category or top-level position}
- Action: {new page | update existing}
```

**Ask the user to confirm** before proceeding.

### 5. Capture Screenshots

Ask the user to choose one of these options:

1. **Capture with Playwright** — the app must be running on `localhost:3001`. Claude determines which URLs and filenames are needed from the research step, then runs:
   ```bash
   cd dalgo-core && python3 scripts/screenshot.py \
     --urls "/route1" "/route2" \
     --output dalgo_docs/static/img/{feature}/ \
     --names "feature_description1" "feature_description2"
   ```
2. **Insert placeholders** — add `<!-- SCREENSHOT: description -->` comments where images should go. The user captures them manually later.
3. **Skip screenshots** — write text-only documentation.

### 6. Write Documentation

Generate the markdown page following the style guide conventions:

- YAML frontmatter with `sidebar_position`
- H1 title + bold one-liner summary
- Step-by-step instructions with numbered lists
- Bold UI element names (buttons, tabs, labels)
- Screenshots between steps using markdown syntax: `![Alt text](/img/{feature}/{name}.png)`
- Admonitions where appropriate (`:::info`, `:::note`, `:::warning`)
- No import+JSX for images, no external GitHub URLs for images, no jargon

Save to: `dalgo_docs/docs/{path}/{filename}.md`

### 7. Update Sidebar

If this is a new page:
1. Read `dalgo_docs/sidebars.js`
2. Add the new doc ID in the correct position within the existing sidebar structure
3. Follow the patterns in SKILL.md for adding to existing categories, new top-level pages, or new categories

If this is an update to an existing page, no sidebar changes are needed.

### 8. Validate

Check that:
- [ ] All image paths referenced in the markdown exist on disk (or are placeholders)
- [ ] The frontmatter `sidebar_position` doesn't conflict with existing pages
- [ ] The doc ID matches what's in `sidebars.js`
- [ ] No import+JSX image patterns were used
- [ ] No external GitHub URLs were used for images

### 9. Print Next Steps

```
Documentation generated:
- Doc: dalgo_docs/docs/{path}/{filename}.md
- Images: dalgo_docs/static/img/{feature}/ ({N} screenshots)
- Sidebar: updated dalgo_docs/sidebars.js

Next steps:
1. Preview: cd dalgo_docs && npm start
2. Review the generated page in browser at http://localhost:3000/docs/{slug}
{3. Replace screenshot placeholders (if any):}
{   <!-- SCREENSHOT: {description} -->}
4. Commit when satisfied
```

---

## Guidelines

- **Write for NGO staff.** Plain language, no jargon. If a technical term is unavoidable, explain it inline.
- **Show, don't tell.** Screenshots between every major step. The user should be able to follow along visually.
- **Match existing docs.** Read 2-3 existing doc pages before writing to match the established tone and depth.
- **One feature per page.** Don't combine unrelated features. Each page should answer "how do I do X?"
- **Bold UI elements.** Every button, tab, field name, and menu item the user needs to click should be **bold**.
- **Keep it short.** If a doc page is longer than ~50 lines of content, consider splitting into sub-pages with a category index.
- **Use admonitions sparingly.** Only for genuinely important callouts — prerequisite info, automatic behaviors, or warnings about destructive actions.
