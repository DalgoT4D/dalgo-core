# Ship a Feature — Full Pipeline

## Input: $ARGUMENTS

Pipeline: **spec → design → plan → implement → validate → design review → docs → PR**

This command is a **thin orchestrator**. It reads only `pipeline.md` between stages and spawns isolated sub-agents for each stage. It never accumulates work product in its own context — results live in files.

Supports resume: re-run the same command after an interruption and completed stages are skipped.

---

## Orchestrator Rules

These apply throughout. Do not break them:

- Between stages, read **only** `pipeline.md`. Do not re-read spec, plan, research, or code.
- Each stage that does real work **must be spawned as a sub-agent**, not run inline. Sub-agents start with a fresh context and receive only what they need.
- Write stage outcomes (pass/fail/blocker) to `pipeline.md` immediately. This is the only persistent state.
- If a sub-agent returns a blocker, stop and surface it to the user. Do not guess around blockers.

---

## Step 0: Resolve Input

1. If `$ARGUMENTS` ends in `spec.md`, use it directly.
2. If `$ARGUMENTS` is a feature name, look for `features/{name}/v1/spec.md`.
3. If no spec found:
   ```
   No spec found. Run /product/write-spec "{name}" first.
   ```
   Stop.
4. Extract `{feature-name}` and `{version}` (default: `v1`).
5. Read the spec **once** to determine feature type (UI or backend-only). Then do not read it again — the planner agent will read it in its own context.

---

## Step 1: Pipeline State

Check `features/{feature-name}/{version}/pipeline.md`:

**If it doesn't exist**, create it:

```markdown
# Pipeline: {feature-name} v{version}

Started: {timestamp}
Branch: (none yet)
PR: (none yet)
Feature type: (unknown)

| Stage         | Status  | Notes |
|---------------|---------|-------|
| design        | pending |       |
| plan          | pending |       |
| implement     | pending |       |
| validate      | pending |       |
| design-review | pending |       |
| docs          | pending |       |
| pr            | pending |       |

Validate attempts: 0
Design review attempts: 0
```

**If it exists**, read it. Skip any stage already `complete` or `skipped`. Print the stage statuses.

---

## Step 2: Branch

If `Branch` is `(none yet)`:

```bash
git branch --list feature/{feature-name}
# if exists:  git checkout feature/{feature-name}
# if not:     git checkout -b feature/{feature-name}
```

Update `Branch` in pipeline.md.

---

## Step 3: Design Gate

If `design` is not `complete` or `skipped`:

**Does the spec mention UI surfaces?** (screens, pages, modals, components, user interactions)

- **No UI** → mark `design` and `design-review` both as `skipped`. Set `Feature type: backend-only`.
- **Has UI, design artifacts exist** (`design.md` or `FIGMA.md` in the feature folder, or `## Design` section in spec) → mark `design` as `complete`. Set `Feature type: UI feature`.
- **Has UI, no design artifacts** → stop:

  ```
  This feature has UI but no design yet.

  Run:  /design/design-handoff features/{feature-name}/{version}/spec.md

  Then re-run:  /engineering/ship-feature features/{feature-name}/{version}/spec.md
  The pipeline will resume from the plan stage.

  To skip design (prototypes or backend-heavy features only):
    /engineering/ship-feature features/{feature-name}/{version}/spec.md --skip-design
  ```

  If `--skip-design` was passed: mark `design` as `skipped`.

---

## Step 4: Plan

If `plan` is not `complete`:

Mark `plan` as `in-progress`. Spawn the **`planner` sub-agent**:

```
Agent input: features/{feature-name}/{version}/spec.md
Task: Produce plan.md and research.md. Confirm blast radius with user before finishing.
```

When the planner reports completion:
- Verify `plan.md` exists at `features/{feature-name}/{version}/plan.md`.
- Mark `plan` as `complete`.

If the planner reports a blocker: write it to pipeline.md notes and stop.

---

## Step 5: Implement

If `implement` is not `complete`:

Mark `implement` as `in-progress`. Spawn the **`engineer` sub-agent**:

```
Agent input: features/{feature-name}/{version}/plan.md
Task: Implement all milestones. Track progress in tasks.md. Treat design.md and FIGMA.md
      as source of truth for all UI labels, states, and components.
```

When the engineer reports completion:
- Mark `implement` as `complete`.

If the engineer reports a blocker: write it to pipeline.md and stop:
```
Implementation blocked — see tasks.md → Blockers.
Fix the blocker and re-run /engineering/ship-feature {spec-path} to continue.
```

---

## Step 6: Validate

If `validate` is not `complete`:

Mark `validate` as `in-progress`. Spawn a **fresh validator sub-agent** with:

```
Context: spec path, current git diff (git diff main...HEAD), any prior failures from pipeline.md
Task: Run all checks from /engineering/validate-spec. Fix failures found. Report pass or remaining failures.
```

- **Pass** → mark `validate` as `complete`.
- **Fail, attempts < 3** → increment `Validate attempts`, spawn a fresh validator with the failure list. Repeat.
- **Fail, attempts = 3** → mark `validate` as `blocked`, write failures to pipeline.md, stop:
  ```
  Validation blocked after 3 attempts. See pipeline.md for failures.
  Fix manually and re-run to continue from validate.
  ```

---

## Step 7: Design Review

If `design-review` is not `complete` or `skipped`:

Check: `git diff main...HEAD --name-only | grep "^webapp_v2/"`

**No frontend files changed** → mark `design-review` as `skipped`.

**Frontend files changed** → mark `design-review` as `in-progress`. Spawn a **fresh design-review sub-agent** with:

```
Context: changed webapp_v2 files (diff), design.md and FIGMA.md if they exist
Task: Apply the design-review skill. Check implementation against design decisions and the NGO user
      lens (would a non-technical program manager understand this screen?). Classify findings as
      blocking or suggestion. Fix blocking findings. Report outcome.
```

- **No blocking findings** → mark `design-review` as `complete`. Write suggestions to pipeline.md for PR description.
- **Blocking findings, attempts < 3** → increment `Design review attempts`, spawn fresh reviewer. Repeat.
- **Blocking findings, attempts = 3** → mark as `blocked`, stop.

---

## Step 8: Docs

If `docs` is not `complete`:

Mark `docs` as `in-progress`. Spawn a **docs sub-agent** with:

```
Context: spec path, plan path
Task: Run the docs-generation skill. Cover what the feature does, how to use it, API changes,
      and configuration. Place docs per docs-generation skill conventions.
```

Mark `docs` as `complete` when done.

---

## Step 9: Open PR

If `pr` is not `complete`:

Mark `pr` as `in-progress`.

1. Commit:
   ```bash
   git add -A
   git commit -m "$(cat <<'EOF'
   feat({feature-name}): {short description from spec}

   Implements features/{feature-name}/{version}/spec.md

   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
   EOF
   )"
   ```

2. Push: `git push -u origin feature/{feature-name}`

3. Read `pipeline.md` for: services affected (from plan stage notes), design suggestions (from design-review notes). Read the spec summary section only.

4. Create PR:
   ```bash
   gh pr create \
     --title "{feature title from spec — under 70 chars}" \
     --base main \
     --body "$(cat <<'EOF'
   ## Summary
   {3-5 bullets from spec}

   ## Spec
   `features/{feature-name}/{version}/spec.md`

   ## Services Affected
   {from pipeline.md}

   ## Test Plan
   {acceptance criteria from plan milestones, as checkboxes}

   ## Validation
   - [x] validate-spec passed
   - [x] Backend tests pass
   - [x] Frontend lint + format pass
   - [x] Design review passed (or N/A — backend-only)
   - [x] Docs generated

   {if design suggestions recorded in pipeline.md}
   ## Design Suggestions (non-blocking)
   {list from pipeline.md}

   🤖 Shipped by /engineering/ship-feature
   EOF
   )"
   ```

5. Record PR URL in pipeline.md. Mark `pr` as `complete`.

---

## Final Output

```
Feature shipped!

Feature:  {feature-name} {version}
Branch:   feature/{feature-name}
PR:       {PR URL}

Pipeline: features/{feature-name}/{version}/pipeline.md
```
