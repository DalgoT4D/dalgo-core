# Validate Spec

## Input: $ARGUMENTS

Validate that the implementation matches the spec. Input is the path to the spec file (e.g. `workdocs/{feature-name}/v1/spec.md`). If no argument is provided, look for the most recent spec in `workdocs/`.

## Process

### Step 1: Load the Spec

- Read the spec file provided as input
- Extract all requirements, acceptance criteria, and expected behaviors
- Read the plan.md in the same folder if it exists

### Step 2: Identify Changes

```bash
git diff main...HEAD --stat
```

Identify which files changed and which services are affected.

### Step 3: Validate Requirements Against Implementation

For each requirement in the spec:
- [ ] Find the corresponding implementation in the diff
- [ ] Verify the implementation matches the spec's intent
- [ ] Check that edge cases mentioned in the spec are handled
- [ ] Verify any API contracts (endpoints, request/response shapes) match the spec

### Step 4: Run Service-Specific Checks

#### For DDP_backend Changes
If any files under `DDP_backend/` changed:
- Run lint check on changed files
- Run `uv run pytest` for any changed test files or test files related to changed modules
- Check for missing Django migrations if models changed (`python manage.py makemigrations --check --dry-run`)

#### For webapp_v2 Changes
If any files under `webapp_v2/` changed:
- Run `npm run lint` in webapp_v2
- Run `npm run format:check` in webapp_v2
- Run `npm test` for changed components (if test files exist)

### Step 5: Scan Diff for Common Issues

Scan the `git diff main...HEAD` output for these patterns:

**TypeScript Issues:**
- [ ] No `any` type usage in new/modified TypeScript code
- [ ] No `// @ts-ignore` or `// @ts-nocheck` added

**Testing:**
- [ ] No `data-testid` missing on new interactive elements (buttons, inputs, links)
- [ ] No `.only` or `.skip` left on test cases

**Security:**
- [ ] No hardcoded secrets, API keys, or passwords
- [ ] No `console.log` statements left in production code
- [ ] No commented-out code blocks added

**Django:**
- [ ] No missing migrations for model changes
- [ ] No bare `except:` blocks added
- [ ] No local imports inside functions

**General:**
- [ ] No TODO comments without issue references
- [ ] No large files (>500 lines) added without justification
- [ ] No debug/development configuration left in code

### Step 6: Output Report

```
## Spec Validation: {spec-path}

**Branch**: {branch} → main
**Files Changed**: {count}
**Services Affected**: [list]

### Spec Coverage
- [COVERED/MISSING] Requirement 1: {description}
- [COVERED/MISSING] Requirement 2: {description}
...

### Automated Checks
- [PASS/FAIL] Backend lint
- [PASS/FAIL] Backend tests
- [PASS/FAIL] Frontend lint
- [PASS/FAIL] Frontend format
- [PASS/FAIL] Frontend tests
- [PASS/FAIL] Migration check

### Diff Scan
- [PASS/FAIL] No `any` types
- [PASS/FAIL] No missing data-testid
- [PASS/FAIL] No hardcoded secrets
- [PASS/FAIL] No console.log
- [PASS/FAIL] No bare except
- [PASS/FAIL] No local imports
- [PASS/FAIL] No .only/.skip in tests

### Result
[ALL CLEAR — Spec fully implemented / {N} issue(s) found — see details above]
```

**Important:** All checks are read-only. This command does NOT modify code, auto-fix issues, or create commits. It only reports findings.
