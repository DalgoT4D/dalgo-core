# Ship a Feature — Synchronous Pipeline (Command Mode)

## Input: $ARGUMENTS

Pipeline: **spec → plan → implement → validate → docs → PR**

Runs in the **current session** — you see every step as it happens. Pauses for human
confirmation at blast-radius and any genuine blockers. Supports resume.

**Tracking:** records `mode: command` in pipeline.md for comparison with agent mode.

---

## Orchestrator Rules

- Between stages, read **only** `pipeline.md`. Do not re-read spec, plan, or code.
- Spawn sub-agents for every stage that does real work — never inline.
- Write outcomes to `pipeline.md` immediately after each stage.
- Stop at genuine blockers; do not guess through them.

---

## Step 0: Resolve Input

1. If `$ARGUMENTS` ends in `spec.md`, use it directly.
2. If `$ARGUMENTS` is a feature name, look for `features/{name}/v1/spec.md`.
3. If no spec found: `No spec found. Run /product/write-spec "{name}" first.` Stop.
4. Extract `{feature-name}` and `{version}` (default: `v1`).
5. Read the spec **once** to understand scope. Then do not re-read it.

---

## Step 1: Pipeline State

Check `features/{feature-name}/{version}/pipeline.md`:

**If it doesn't exist**, create it:

```markdown
# Pipeline: {feature-name} v{version}

Mode: command
Started: {timestamp}
Branch: (none yet)
PR: (none yet)

| Stage      | Status  | Notes |
|------------|---------|-------|
| plan       | pending |       |
| implement  | pending |       |
| validate   | pending |       |
| docs       | pending |       |
| pr         | pending |       |

Validate attempts: 0
Human interventions: 0
```

**If it exists**, read it. Skip stages already `complete` or `skipped`. Print stage statuses.

---

## Step 2: Branch

If `Branch` is `(none yet)`:
```bash
git branch --list feature/{feature-name}
# exists:   git checkout feature/{feature-name}
# missing:  git checkout -b feature/{feature-name}
```
Update `Branch` in pipeline.md.

---

## Step 3: Plan

If `plan` not `complete`:

Mark `plan` as `in-progress`. Spawn **`planner` sub-agent**:
```
Input: features/{feature-name}/{version}/spec.md
Task:  Produce plan.md and research.md. Confirm blast radius with user before finishing.
```

On completion → verify `plan.md` exists → mark `plan` as `complete`.
On blocker → write to pipeline.md, increment `Human interventions`, stop.

---

## Step 4: Implement

If `implement` not `complete`:

Mark `implement` as `in-progress`. Spawn **`engineer` sub-agent**:
```
Input: features/{feature-name}/{version}/plan.md
Task:  Implement all milestones. Track in tasks.md.
```

On completion → mark `implement` as `complete`.
On blocker → write to pipeline.md, increment `Human interventions`, stop.

---

## Step 5: Validate (Loop)

If `validate` not `complete`:

Mark `validate` as `in-progress`. Spawn **fresh validator sub-agent**:
```
Context: spec path + git diff (git diff main...HEAD) + prior failures from pipeline.md
Task:    Run all checks from /engineering/validate-spec. Fix failures. Report pass or failures.
```

- Pass → mark `validate` as `complete`.
- Fail, attempts < 3 → increment `Validate attempts`, spawn fresh validator. Repeat.
- Fail, attempts = 3 → mark `validate` as `blocked`, stop.

---

## Step 6: Docs

If `docs` not `complete`:

Spawn **docs sub-agent**:
```
Context: spec path + plan path
Task:    Run docs-generation skill. Cover feature usage, API changes, configuration.
```

Mark `docs` as `complete`.

---

## Step 7: Open PR

Mark `pr` as `in-progress`.

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat({feature-name}): {short description from spec}

Implements features/{feature-name}/{version}/spec.md

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
git push -u origin feature/{feature-name}
```

```bash
gh pr create \
  --title "{feature title — under 70 chars}" \
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
- [x] Docs generated

🤖 Shipped by /engineering/ship-feature (command mode)
EOF
)"
```

Record PR URL in pipeline.md. Mark `pr` as `complete`.

---

## Final Output

```
Feature shipped! (command mode)

Feature:  {feature-name} {version}
Branch:   feature/{feature-name}
PR:       {PR URL}
Human interventions: {count from pipeline.md}

Pipeline: features/{feature-name}/{version}/pipeline.md
```
