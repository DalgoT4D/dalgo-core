# Debug an Issue

## Input: $ARGUMENTS

Diagnose a bug from a Sentry issue URL, error message, or behavior description.

## Process

### Step 1: Parse Input
Determine the type of input:
- **Sentry URL** (contains `sentry.io`): Fetch issue details using `mcp__plugin_sentry_sentry__get_sentry_resource` with the URL.
- **Error message or stack trace**: Parse directly.
- **Behavior description**: Use as context for codebase search.

### Step 2: Classify as Backend or Frontend
Determine which debugger to use based on:

**Backend indicators:**
- Python stack trace (`.py` files, Django/Ninja references)
- API endpoint URLs (`/api/` paths)
- Server error codes (500, 502, 503)
- Database errors (Django ORM, PostgreSQL)
- External service errors (DBT, Airbyte, Prefect)

**Frontend indicators:**
- JavaScript/TypeScript stack trace (`.tsx`/`.ts` files)
- React component errors (hooks, rendering, hydration)
- Browser console errors
- Page route references (not `/api/` paths)
- SWR/Zustand/Next.js specific errors

**If unclear:** Check both. Start with the stack trace language. If no stack trace, check the affected URL pattern.

### Step 3: Diagnose

Apply the 4-phase debugging methodology:

1. **Gather** — Collect all available information about the error.
   - For Sentry issues: fetch full details, check related issues, review breadcrumbs.
   - For descriptions: search codebase for the affected area.

2. **Hypothesize** — Form 2-3 ranked hypotheses about the root cause.
   - Trace the code path through the relevant architecture.
   - Check known pitfalls (see debugger agent for lists).

3. **Isolate** — Narrow to the specific function, component, or query.
   - Read the actual source code.
   - Verify each hypothesis against the code.

4. **Fix** — Propose a minimal fix.
   - Show the affected file(s) and line(s).
   - Provide a concrete code change.
   - Assess regression risk.
   - Suggest a test case.

### Step 4: Output Diagnosis Report

Structure the output as:

```
## Diagnosis Report

### Issue Summary
[What's happening, who's affected]

### Classification
[Backend / Frontend / Both]

### Root Cause
[Specific code path and condition]

### Affected Files
- [file:line] — [what's wrong]

### Fix Proposal
[Code diff with explanation]

### Regression Risk
[What could break]

### Suggested Test
[Test case that catches this bug]
```

### Step 5: Suggest Next Steps
- If the fix is small and self-contained: "This is a straightforward fix. You can implement it directly."
- If the fix is complex or crosses multiple services: "This fix is non-trivial. Consider running `/engineering/plan-feature` to create a proper implementation plan."
- If more investigation is needed: Suggest specific things to check or monitor.
