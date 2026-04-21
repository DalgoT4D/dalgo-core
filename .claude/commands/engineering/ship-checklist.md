# Pre-Merge Ship Checklist

## Input: $ARGUMENTS

Run automated quality checks before merging. Input is an optional branch name (defaults to current branch).

## Process

### Step 1: Identify Changes
```bash
# If branch specified, use it; otherwise use current branch
git diff main...HEAD --stat
```

Identify which files changed and which services are affected.

### Step 2: Run Service-Specific Checks

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

### Step 3: Scan Diff for Common Issues

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

### Step 4: Output Checklist

```
## Ship Checklist: {branch-name}

**Branch**: {branch} → main
**Files Changed**: {count}
**Services Affected**: [list]

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
[ALL CLEAR — Ready to merge / {N} issue(s) found — see details above]
```

**Important:** All checks are read-only. This command does NOT modify code, auto-fix issues, or create commits. It only reports findings.
