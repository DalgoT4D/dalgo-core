# Plan an enhancement to an existing feature

## Input: $ARGUMENTS

Generate a planning document for an **enhancement** to an existing feature. The enhancement is scoped as a minor version bump on top of the latest version of that feature (e.g. `v1` → `v1.1`, `v2.1` → `v2.2`).

`$ARGUMENTS` is one of:
- **A spec doc path** — e.g. `features/metrics_kpis/v1.1/spec.md` or any markdown file describing the enhancement.
- **A paragraph string** — an inline description of the enhancement (e.g. `"add number formatting options to KPI config — same as the number chart"`).

The output is a plan (`plan.md`) inside a newly created version folder. The rest of the planning logic — Blast Radius, HLD, LLD, Security, Testing, Milestones — is identical to `/engineering/plan-feature`. This command differs only in how it determines the target feature folder and the target version.

## Pre-Check: Establish context

Before research, in this order:

### 1. Read platform context (mandatory)
- `dalgo-core/README.md` — workflow and directory conventions.
- `dalgo-core/docs/domain-map.md` — product entities and their consumers. **Source of truth for impact analysis.**

Skipping these will produce an incomplete plan that misses downstream surfaces.

### 2. Resolve the target feature folder

1. **If `$ARGUMENTS` is a file path** under `features/`:
   - The feature folder is the nearest ancestor directly under `features/` (e.g. `features/metrics_kpis/v1.1/spec.md` → `features/metrics_kpis/`).
   - If the path is *outside* `features/` (e.g. a notes file), read it for the description and then continue to step 2.
2. **If `$ARGUMENTS` is a paragraph string**:
   - Scan `features/` and infer the most likely target by matching keywords in the paragraph against feature folder names and their top-level `spec.md` summaries.
   - If exactly one folder is a clear match, propose it and confirm with the user before proceeding.
   - If zero or multiple plausible matches, **stop and ask the user** which feature folder this enhancement belongs to. Show the list of available `features/` subdirectories.
3. **Never guess silently** — if there is any ambiguity about which feature this enhances, ask.

### 3. Resolve the target version

Inside the resolved feature folder, list existing version subdirectories matching `v{major}[.{minor}]` (e.g. `v1`, `v1.1`, `v2`, `v2.1`).

- **Latest version** = the version with the highest `(major, minor)` lexicographically (treat missing minor as `.0`). Example sets and their latest:
  - `{v1}` → latest `v1`
  - `{v1, v1.1}` → latest `v1.1`
  - `{v1, v2}` → latest `v2`
  - `{v1, v1.1, v2}` → latest `v2`
- **New version** = latest with `minor + 1`. Examples:
  - `v1` → `v1.1`
  - `v1.1` → `v1.2`
  - `v2` → `v2.1`
  - `v2.1` → `v2.2`
- **If no versioned folder exists** (only a top-level `spec.md`, or nothing): this is not an enhancement — stop and tell the user to run `/engineering/plan-feature` instead (or `/product/write-spec` if no spec exists yet).
- **If you are unsure** which major to bump from (e.g. multiple actively-developed majors), **ask the user** which version to enhance.

Create the new version directory: `features/{feature-name}/v{major}.{minor}/`.

### 4. Capture the enhancement description

- **If `$ARGUMENTS` was a spec doc inside the feature folder**: use it as the canonical spec for this enhancement. If it lives at the *new* version path (e.g. user pre-wrote `features/foo/v1.1/spec.md`), use it directly. If it lives elsewhere, copy/cite it from the plan's Overview.
- **If `$ARGUMENTS` was a paragraph string or a notes file outside `features/`**: embed the description verbatim in the plan's Overview section under a heading "Enhancement description". Do **not** auto-generate a `spec.md` — specs are PRDs and require proper grilling via `/product/write-spec`. The plan stands alone; the user can promote the description to a proper spec later if needed.

### 5. Load context from the parent version

Always read the parent version's `spec.md` and (if present) `plan.md` so the enhancement plan is grounded in what already shipped. Cite them in the Overview.

### 6. Blast Radius Analysis (mandatory)

Same as `/engineering/plan-feature`:
- Identify the primary entity(ies) the enhancement touches, using `docs/domain-map.md`.
- Traverse 1-hop, then 2-hop `Consumed by` edges. Build the impact set.
- For every surface in the impact set not explicitly addressed by the enhancement description, **stop and ask the user** whether it is in-scope, deferred, or intentionally out-of-scope.
- No silent inclusions or exclusions. No `TBD` entries.

## Research Process

Identical to `/engineering/plan-feature`:

1. **Codebase Analysis** — search for similar patterns, identify files to reference, note conventions, check test patterns.
2. **External Research** — library docs (with URLs), implementation examples, common pitfalls.
3. **Clarification** — ask whatever is needed to resolve ambiguity in the enhancement.
4. **Multi-service Impact** — DDP_backend, webapp_v2, prefect-proxy — which services change, how to validate each.
5. **Save Research** — write findings to `features/{feature-name}/v{major}.{minor}/research.md`.

## Plan Document Structure

The output plan should have these sections (identical to `/engineering/plan-feature`):

### 1. Overview
- Enhancement summary (1-2 sentences).
- **Parent version**: link to `features/{feature-name}/v{N}/spec.md` and `plan.md`.
- **Enhancement description**: if `$ARGUMENTS` was a paragraph or external notes file, paste it here verbatim. If it was a spec doc, link to it.
- Services affected.

### 2. Blast Radius
| Surface | Hop distance | Why affected | Status | Notes |
|---------|--------------|--------------|--------|-------|

Every entry confirmed with the user. No `TBD`. If a domain-map surface is not affected, state why explicitly.

### 3. High-Level Design (HLD)
- System-level interaction changes.
- Data flow (text or ASCII).
- New / modified endpoints.
- External service integrations.
- Key design decisions and trade-offs — especially anything that diverges from the parent version's choices.

### 4. Low-Level Design (LLD)
- **Data model** — new / modified Django models, migrations, schema changes. Call out what existing fields are reused vs. extended.
- **API design** — request/response schemas, endpoint signatures, error codes.
- **Backend logic** — core layer functions, service interactions, Celery tasks.
- **Frontend components** — new / modified components, hooks, state.
- **Integration points** — frontend ↔ backend ↔ external services.
- Reference real files and existing patterns for each.

### 5. Security Review
- Authentication & Authorization (`@has_permission`, roles).
- Input validation at API boundaries.
- Multi-tenant data access — can users only access their own org's data?
- Sensitive data handling.
- Injection risks.
- External service secrets.
- Rate limiting / abuse vectors.

### 6. Testing Strategy
- Unit tests — what, where.
- Integration tests — cross-service validation.
- Edge cases.
- Test data requirements.
- **Regression coverage** — what existing v{N} behavior must remain unchanged. Call out the parent-version tests to keep green.

### 7. Milestones
Each milestone: independently shippable, reviewable (single PR), testable (clear acceptance criteria).

```
#### Milestone 1: {title}
- **Deliverable**: ...
- **Services**: ...
- **Key tasks**:
  - [ ] Task 1
- **Acceptance criteria**: ...
```

### 8. Open Questions & Risks
- Unresolved design decisions.
- Dependencies on other teams or features.
- Performance concerns.
- Migration risks — especially backward-compat with the parent version's data (e.g. default values for new fields on existing rows).

## Output

- Plan: `features/{feature-name}/v{major}.{minor}/plan.md`
- Research: `features/{feature-name}/v{major}.{minor}/research.md`

## Quality Checklist

- [ ] `README.md` and `docs/domain-map.md` were read before research began
- [ ] Target feature folder was confirmed (not silently guessed)
- [ ] New version follows `v{major}.{minor+1}` from the latest existing version
- [ ] Parent version's spec and plan were read and cited
- [ ] Blast Radius lists every 1-hop and 2-hop consumer from the domain map
- [ ] Every affected surface has a confirmed status — none left as `TBD`
- [ ] User was asked about any surface the enhancement description did not explicitly address
- [ ] HLD covers all affected services
- [ ] LLD has concrete schema, API, and component details
- [ ] Security review covers auth, validation, data access
- [ ] Testing strategy includes regression coverage for parent-version behavior
- [ ] Milestones are independently shippable and ordered
- [ ] Backward-compat / migration risk against the parent version is addressed

## Next Step

After saving the plan, print:
"Draft v1 of the enhancement plan saved at `features/{feature-name}/v{major}.{minor}/plan.md`. Review and tell me what to revise — architecture, scope, milestones, anything. When ready, run `/engineering/execute-plan features/{feature-name}/v{major}.{minor}/plan.md` to implement."
