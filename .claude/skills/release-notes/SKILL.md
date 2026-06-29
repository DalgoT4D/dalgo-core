---
name: release-notes
description: Draft a new Dalgo release notes entry on dalgo_docs from the latest release tags of DDP_backend and webapp_v2. Use when the user asks to write, publish, or update release notes after a release ships.
---

# Release Notes Skill

Creates a new dated entry in `dalgo_docs/release-notes-docs/` from changes between the previous and latest release tags in `../DDP_backend` and `../webapp_v2`.

Audience: NGO clients reading https://docs.dalgo.org/release-notes. Tone is friendly and plain-spoken with a light touch of humour. No version numbers, no internal jargon.

## When to trigger

User says: "create release notes", "publish release notes", "update release notes from the latest tag", "draft release notes for the latest release".

## Canonical entry structure

Every entry must follow this exact shape. Consistency across entries matters more than any single entry being clever.

```markdown
---
title: <Month DD, YYYY>
sidebar_label: <Month DD, YYYY>
sidebar_position: <integer — see step 7>
---

# <Month DD, YYYY>

<One- or two-sentence one-liner.>

## <Headline feature title>

<Optional short intro sentence.>

- **<Noun>** — what changed for the user.
- ...

## <Secondary improvement title>

- ...

## Fixes

- **<Area>** — what was broken, now isn't.
- ...

---

*Release tags: <a href="https://github.com/DalgoT4D/DDP_backend/releases/tag/<tag>" target="_blank" rel="noopener noreferrer">DDP_backend &lt;tag&gt;</a> · <a href="https://github.com/DalgoT4D/webapp_v2/releases/tag/<tag>" target="_blank" rel="noopener noreferrer">webapp_v2 &lt;tag&gt;</a>*
```

Non-negotiable elements (present in every entry, in this order):

| Element | Rule |
|---|---|
| Frontmatter `title` / `sidebar_label` | Identical, US-format date: `Month DD, YYYY` (e.g. `June 29, 2026`). No version numbers, no ISO dates, no abbreviations like "Jun". |
| Frontmatter `sidebar_position` | Integer. Newest entry = `1`. Older entries bump to `2`, `3`, … when a new one is added. |
| H1 | Same date string as `title`. Exactly one H1 per entry. |
| One-liner | One or two sentences, plain prose, no bullets. Sits between H1 and first `##`. Never restates the date or version. |
| Section headings (`##`) | Title Case. Each section is a user-facing theme, not a repo or PR. Order: headline → secondary improvements → `## Fixes` last (if any). |
| Bullets | Start with **bold noun** + ` — ` (em dash + space) + plain-English clause. Second person (`you`, `your`). |
| Divider before footer | `---` on its own line, blank line above and below. |
| Footer | Exact line: italic `*Release tags: ...*` with the two `<a target="_blank" rel="noopener noreferrer">` links. Only the tag strings change between entries. |

The filename, sidebar position, dates, sections, and tags are the only things that vary. Nothing else in the shape changes between entries.

## Workflow

### 1. Fetch and identify the latest tags

Tags may be missing locally — always fetch first.

```bash
cd ../DDP_backend && git fetch --tags && git tag --sort=-creatordate | head -5
cd ../webapp_v2  && git fetch --tags && git tag --sort=-creatordate | head -5
```

Record for each repo: latest tag, previous tag, tag dates.

### 2. Pull commits in each tag range

```bash
git log --no-merges <prev>..<latest> --format="- %s"
git log <prev>..<latest> --format="%h %s" --grep="^Merge pull"
git diff --name-only <prev>..<latest>
```

Inspect file paths and PR titles to understand what shipped. For unclear PRs, `git show <sha>` the merge commit or read the diff.

### 3. Filter to user-facing changes

**Include**: new features, UI/UX improvements, behavior changes, notable fixes a user would observe.

**Exclude**:
- Analytics / observability plumbing (PostHog field exposure, Sentry log-level changes)
- Internal refactors, test additions, type changes
- CI / pre-commit / lint / formatting
- Dev tooling, dependency bumps unless they change behavior
- Migrations without user-visible impact
- Backend-only permission/RBAC tightening unless the user is now blocked or unblocked from something

If the entire release is internal, tell the user — don't invent user-facing content. Offer to fold it into the next release entry.

### 4. Group by theme

Features often span both repos (one PR in DDP_backend + one in webapp_v2). Cluster them by user-facing capability, not by repo.

Section pattern:
- `## <Headline feature>` — the big new capability that anchors the release
- `## <Secondary improvement>` — meaningful enhancements
- `## Fixes` — notable fixes as a single bulleted list at the bottom

### 5. Write the one-liner

One or two sentences directly under the H1, before the first `##`. Tone matches Airbyte's release notes: friendly, slightly self-aware, points at the headline feature. Skip "we're excited to announce". Don't restate the date.

Examples that work:
- *"Your logo just moved into Dalgo. It now rides along on chart exports, PDFs, fullscreen views, and shared dashboards."*
- *"KPIs now count the same way wherever they show up. Big news for anyone with a calculator on their desk."*

Examples that don't:
- ~~"This release brings exciting new features."~~ — corporate-speak
- ~~"Released June 29, 2026."~~ — restates the title
- ~~"v4.3 of the webapp ships with…"~~ — version-led, not user-led

### 6. Write the entry file

File: `dalgo_docs/release-notes-docs/YYYY-MM-DD.md` — the filename uses ISO date for filesystem sortability. Use the **most recent** of the two tag dates so the filename matches the release event the user remembers.

Follow the **Canonical entry structure** at the top of this skill exactly. Do not improvise on shape — only the content inside sections varies between releases.

Specific reminders when writing the body:
- Skip technical detail unless it changes what the user does.
- Don't link to internal docs that don't exist yet — drop the link rather than break the build.
- If there are no real features (only fixes), open with the one-liner and go straight to `## Fixes`. Don't fabricate a headline section.
- The footer's only variable parts are the two tag strings (in the URL and the link text). Everything else in that line is fixed.

### 7. Put the new entry on top

Open `dalgo_docs/sidebarsReleaseNotes.js`. **Prepend** the new file id (filename without `.md`) so the navbar lands on the latest release:

```js
// before
releaseNotesSidebar: ['2026-06-29']

// after adding 2026-07-15
releaseNotesSidebar: ['2026-07-15', '2026-06-29']
```

Also bump `sidebar_position` of the previous top entry (2, 3, …) so the order is unambiguous if anyone reads frontmatter alone.

### 8. Verify build

```bash
cd dalgo_docs && yarn build
```

Must complete cleanly — no broken links, no warnings on the new page. If a link in the body points at a doc page that doesn't exist, drop the link rather than break the build.

### 9. Print next steps

```
Release notes drafted:
- Entry: dalgo_docs/release-notes-docs/<date>.md
- Sidebar: <date> placed at the top
- Build: clean

Preview locally:
  cd dalgo_docs && yarn start
  → http://localhost:3000/release-notes

Commit on a branch in dalgo_docs and open a PR when ready.
```

## Conventions

- **Title = date** (e.g. "June 29, 2026"). No version numbers anywhere.
- **Newest entry on top** — sidebar order is hand-managed in `sidebarsReleaseNotes.js`.
- **One file per release event**, not per tag. If backend tags Monday and frontend tags Friday, write one entry dated Friday.
- **Skip internal-only releases.** Tell the user; offer to combine with the next release.
- **Stand-alone entries.** Each one reads on its own — don't reference older entries.

## Anti-patterns

- Don't dump raw commit messages or PR titles into the body.
- Don't include PR numbers, branch names, file paths, or stack-trace fragments.
- Don't say "fixed bugs" — name what was broken from the user's perspective.
- Don't surface internal-only concepts (queue names, Celery tasks, S3 buckets, RBAC internals) unless the user sees something different now.
- Don't write a generic "About these notes" preamble. Each entry speaks for itself.
