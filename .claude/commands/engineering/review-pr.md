# Review a Pull Request

## Input: $ARGUMENTS

Perform a structured code review of a GitHub pull request.

## Process

### Step 1: Fetch PR Details
- If `$ARGUMENTS` is a full GitHub URL, extract the repo and PR number.
- If `$ARGUMENTS` is just a number, assume it's a PR in the current repo.
- Run `gh pr view $PR_NUMBER --json title,body,baseRefName,headRefName,files,additions,deletions` to get PR metadata.
- Run `gh pr diff $PR_NUMBER` to get the full diff.

### Step 2: Identify Affected Services
From the changed files, determine which services are affected:
- `DDP_backend/` → Backend (Django)
- `webapp_v2/` → Frontend (Next.js)
- `prefect-proxy/` → Orchestration proxy
- `dalgo-ai-gen/` → AI/ML services
- Other files → Note for review

### Step 3: Review by Service

#### For Backend Changes (DDP_backend)
Check compliance with `DDP_backend/.claude/CLAUDE.md`:
- **Layer architecture**: Are API, Core, Schema, Model responsibilities respected?
- **No local imports**: All imports at file top?
- **Router naming**: Uses `{module}_router` pattern?
- **Permission decorators**: `@has_permission` on all endpoints?
- **Response wrapping**: All responses use `api_response()`?
- **Schema validation**: Pydantic schemas for request validation?
- **Exception handling**: Feature-specific exceptions, not bare `except:`?
- **No barrel exports**: `__init__.py` files kept empty?

#### For Frontend Changes (webapp_v2)
Check compliance with `webapp_v2/CLAUDE.md`:
- **Component structure**: Thin pages, logic in components?
- **SWR hooks**: Proper hook patterns (`useFeatures`, `useFeature`, `useCreateFeature`)?
- **data-testid**: Present on all new interactive elements?
- **TypeScript**: No `any` types, proper interfaces defined?
- **No magic numbers**: Named constants with explanations?
- **Toast usage**: Uses `toastSuccess`/`toastError` from `lib/toast.ts`, not raw `toast()`?
- **Color conventions**: CSS variables, not hardcoded hex?
- **Page layout**: Follows fixed header + scrollable content pattern?
- **No barrel exports**: No `index.ts` re-exports?

### Step 4: Cross-Cutting Checks
Regardless of which service:

**Security:**
- No hardcoded secrets, API keys, or tokens in code
- No SQL injection vulnerabilities (raw SQL without parameterization)
- No XSS vulnerabilities (unescaped user input in templates/JSX)
- Proper authentication/authorization on new endpoints
- Sensitive data not exposed in logs or error messages

**Testing:**
- Are there tests for new functionality?
- Do existing tests still pass with these changes?
- Are edge cases covered?
- Is test data realistic and meaningful?

**Breaking Changes:**
- Do API changes maintain backward compatibility?
- Are database migrations reversible?
- Do frontend changes handle both old and new API response formats during transition?

**Code Quality:**
- No dead code introduced
- No unnecessary complexity
- Consistent naming with existing codebase
- Appropriate error handling

### Step 5: Output Review

Structure the review with severity levels:

```
## PR Review: {PR Title}

**PR**: #{number} ({head} → {base})
**Files Changed**: {count} ({additions}+ / {deletions}-)
**Services Affected**: [list]

### Blocking Issues
Items that should be fixed before merge.
- [{severity}] {file}:{line} — {description}

### Suggestions
Improvements that would make the code better but aren't blockers.
- [{file}:{line}] — {suggestion}

### Nitpicks
Minor style or convention preferences.
- [{file}:{line}] — {nitpick}

### What's Done Well
Positive aspects of the PR worth noting.
- {observation}

### Summary
[1-2 sentence overall assessment]
```

**Tip:** For frontend UI changes, also consider applying the `design-review` skill for a combined UX + NGO user evaluation.

**Important:** This command outputs the review for the developer to use. It does NOT auto-post comments to GitHub.
