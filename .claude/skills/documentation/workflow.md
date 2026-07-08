# Documentation Workflow

Process to generate or update a doc page, from research to published markdown.

## 0. Check repo access

Before starting, confirm `dalgo_docs` is cloneable:

```bash
git ls-remote https://github.com/DalgoT4D/dalgo_docs HEAD
```

If the clone fails (403/network blocked), write draft files to `dalgo-core/drafts/docs-{date}/` instead and open a PR in `dalgo-core` with `SIDEBAR-CHANGES.md` explaining what to apply. Skip steps 5 (screenshots) and 7 (sidebar). Note the constraint clearly in the PR body.

## 1. Parse Input & Determine Mode

**Mode A — Feature Name** (default): input is a feature description (e.g. "orchestrate", "data quality").

**Mode B — PR / Commits**: input matches `#\d+`, a GitHub PR URL, or `\w+\.\.\w+`.

## 2. Load Reference Files

Read what's needed for the task:
- `sidebar.md`, `repo-structure.md` for placement
- `style-writing.md`, `style-page.md`, `style-admonitions.md`, `style-images.md` for conventions

## 3. Research the Feature

**Mode A:**
1. Find the webapp route by exploring `webapp_v2/app/` — the directory tree mirrors the product nav.
2. Read frontend page components in `webapp_v2/app/{route}/` to understand the UI.
3. Read related `DDP_backend/` endpoints if the feature has API interactions.
4. Check existing docs in `dalgo_docs/docs/` and screenshots in `dalgo_docs/static/img/`.

**Mode B:**
1. `gh pr diff $PR_NUMBER` or `git diff $COMMIT_RANGE` to see changes.
2. Identify the affected feature area from changed file paths.
3. Read the changed files in full to understand new behavior.
4. Check existing docs for that area.

## 4. Derive Doc Placement

No static mapping — derive from filesystem:
- **Webapp route** → product-nav section
- **`dalgo_docs/sidebars.js`** → canonical doc folder for that section
- **Existing files under that folder** → new page vs extend existing

**Check the domain map** at `docs/domain-map.md`. If the feature introduces a new entity or changes an existing entity's `Consumes` / `Consumed by` / `Platform-specific behaviors` / `Change impact`, the map MUST be updated. Pure UI/copy changes = no-op.

Print the placement plan:

```
Placement plan:
- Doc: dalgo_docs/docs/{path}/{filename}.md
- Images: dalgo_docs/static/img/{feature}/
- Sidebar: {category or top-level position}
- Action: {new page | update existing}
- Domain map: {no entity impact | add entity {name} | update entity {name}}
```

**Ask the user to confirm** before proceeding.

## 5. Capture Screenshots

Recipe-driven. For feature `X`, look at `scripts/recipes/X.yaml`. **Missing** → create it. **Present** → review against your current understanding (from step 3); add/update flows for any user path the docs reference but the recipe doesn't cover, and refresh selectors / waits / nuances if the UI has drifted.

Creating or editing the recipe:
1. **Identify selectors** — read the route's `page.tsx` + imported components (and `DDP_backend` endpoints if a flow depends on server state). Prefer `data-testid` → ARIA role+name → visible text. Avoid raw CSS classes (style-fragile).
2. **Write/update the YAML** — flows × steps (navigate, click, wait, snap, press). See `kpis.yaml` / `ingest.yaml` for patterns. Required flows abort the recipe on failure; optional flows skip with a warning. Put quirks in the `nuances` field.

Then run: `cd dalgo-core && uv run python scripts/screenshot.py X`. Verify expected files land in `dalgo_docs/static/img/{output_dir}/`. Iterate on any selector that misses — don't ship guesses.

Use `:::info Screenshot coming soon` when a real screenshot is not available — for unbuilt features or when running in an environment without browser access. Bulk refresh (`screenshot.py` with no args) picks up every recipe automatically.

## 6. Write Documentation

Follow `style-writing.md` + `style-page.md`. Save to `dalgo_docs/docs/{path}/{filename}.md`.

## 7. Update Sidebar

New page: read `dalgo_docs/sidebars.js`, add the doc ID per `sidebar.md` patterns. Updates to existing pages need no sidebar changes.

## 8. Update Domain Map

If step 4 flagged it, edit `docs/domain-map.md`. Read its "Entity shape" section first; new entries must include all fields and use correct edge labels (`snapshot-of`, `compose`, `embed`, `reference`, `trigger`, `query-from`).

**Promote to `verified` whenever possible — this is not optional.** If the feature has shipped (UI routes exist), READ the relevant Django models under `DDP_backend/ddpui/models/` plus any recent migration, cross-check against your entry, then set `Confidence: verified`. Also remove the entity from the "promote draft entries" roadmap at the bottom of the map. Use `draft` only if (a) the feature is spec-only with no shipped code, or (b) you genuinely can't locate the models — in case (b), add a note saying which paths you searched. The domain map drives `/product/write-spec` and `/engineering/plan-feature` blast-radius analysis; `draft` is contagious.

## 9. Validate

- [ ] Image paths exist (or are placeholders); standard markdown syntax; no GitHub URLs
- [ ] `sidebar_position` doesn't conflict; doc ID matches `sidebars.js`
- [ ] `docs/domain-map.md` updated if entity impact; Confidence = `verified` if shipped + models read

## 10. Print Next Steps

```
Documentation generated:
- Doc: dalgo_docs/docs/{path}/{filename}.md
- Images: dalgo_docs/static/img/{feature}/ ({N} screenshots)
- Sidebar: updated dalgo_docs/sidebars.js

Next:
1. Preview: cd dalgo_docs && npm start
2. Review at http://localhost:3000/docs/{slug}
3. Commit when satisfied
```
