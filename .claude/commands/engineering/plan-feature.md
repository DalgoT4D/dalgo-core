# Create a detailed feature implementation planning document

## Feature file: $ARGUMENTS

Generate a complete planning document for feature implementation with thorough research. This is a **Draft v1** — meant to be reviewed and refined by the engineering team through conversation.

## Pre-Check: Establish Context

Before starting research, in this order:

### 1. Read platform context (mandatory)
Read these two files first — they are the canonical references for how Dalgo works:
- `dalgo-core/README.md` — the AI-assisted workflow and directory conventions.
- `dalgo-core/docs/domain-map.md` — the product entities, what they consume, and what consumes them. **This is the source of truth for impact analysis.**

Do not skip these. Without them, you will miss downstream surfaces and plan an incomplete feature. The reason this step exists: historically, specs have silently dropped downstream surfaces (e.g. a Metrics spec that forgot Reports) because the planner had no map of product-level relationships.

### 2. Load the spec
1. If `$ARGUMENTS` points to a file (e.g. `workdocs/{feature-name}/v1/spec.md`), use it as the primary input.
2. Otherwise, extract the feature name and check `workdocs/{feature-name}/` for existing specs or plans.
3. If a top-level `spec.md` exists (PM's original spec), read it for full context.
4. If a versioned `v1/spec.md` exists, use it as the scoped input for this iteration.
5. If no spec exists, proceed with the standard research process below.

### 3. Blast Radius Analysis (mandatory before any codebase research)
- Identify the primary entity(ies) the spec is changing, using the vocabulary from `docs/domain-map.md`.
- Traverse the map: follow `Consumed by` edges 1-hop, then 2-hop minimum. Build the full impact set of product surfaces.
- Cross-check against the spec. For every surface in the impact set that the spec does **not** explicitly address, **stop and ask the user** whether it is:
  - **in scope** for this version
  - **deferred** to a later version
  - **intentionally out of scope**
- Do not silently include or exclude any surface. Do not guess the user's intent.
- Capture the confirmed decisions — they become section 2 of the plan (see below).

## Research Process

1. **Codebase Analysis**
   - Search for similar features/patterns in the codebase
   - Identify files to reference in the plan
   - Note existing conventions to follow
   - Check test patterns for validation approach

2. **External Research**
   - Search for similar features/patterns online
   - Library documentation (include specific URLs)
   - Implementation examples (GitHub/StackOverflow/blogs)
   - Best practices and common pitfalls

3. **Clarification**
   - Ask questions if needed around the feature.

4. **Multi-service Impact**
   - Since Dalgo has multiple services (DDP_backend, webapp_v2, prefect-proxy), analyze which services need changes.
   - How would you validate that changes in each service work.
   - Think about integration testing, functional testing, and unit testing.

5. **Save Research**
   - Save research findings to `workdocs/{feature-name}/{version}/research.md`
   - This preserves context for future reference and plan iterations.

## Plan Document Structure

The output plan should have these sections:

### 1. Overview
- Feature summary (1-2 sentences)
- Link back to spec (top-level and versioned)
- Services affected

### 2. Blast Radius
Every product surface the Pre-Check identified as affected, with its confirmed scope status. This is the section that prevents downstream surfaces from being silently dropped.

| Surface | Hop distance | Why affected | Status | Notes |
|---------|--------------|--------------|--------|-------|
| (example) Report | 1 and 2 | Direct Metric value render + via Dashboard | deferred | Pradeep confirmed v2 in conversation on {date} |

- Every entry must be confirmed with the user during Pre-Check — no entries marked `TBD` or `unclear`.
- If a surface from the domain map is not listed here, state explicitly why it is not affected (e.g. "Alerts: unaffected because this change does not modify Metric thresholds").
- If the spec's own scope is narrower than the map suggests, the rationale belongs in this section's notes.

### 3. High-Level Design (HLD)
- System-level architecture: how services interact for this feature
- Data flow diagrams (describe in text or ASCII)
- New API endpoints or modified endpoints
- External service integrations (Airbyte, Prefect, dbt, warehouse)
- Key design decisions and trade-offs

### 4. Low-Level Design (LLD)
- **Data model**: New/modified Django models, migrations, schema changes
- **API design**: Request/response schemas, endpoint signatures, error codes
- **Backend logic**: Core layer functions, service interactions, Celery tasks if needed
- **Frontend components**: New/modified components, hooks, state changes
- **Integration points**: How frontend calls backend, how backend calls external services
- Reference real files and existing patterns for each

### 5. Security Review
- **Authentication & Authorization**: Are new endpoints protected with `@has_permission`? What roles can access this?
- **Input validation**: Where does user input enter the system? Is it validated at API boundaries (Pydantic schemas)?
- **Data access control**: Can users access only their own org's data? Are there multi-tenant leaks?
- **Sensitive data**: Does this feature handle PII, credentials, or tokens? How are they stored/transmitted?
- **Injection risks**: Any raw SQL, dynamic queries, or template rendering with user input?
- **External service calls**: Are secrets managed via env vars? Are responses validated before use?
- **Rate limiting / abuse**: Could this endpoint be abused? Does it need throttling?

### 6. Testing Strategy
- Unit tests: what to test, which modules
- Integration tests: cross-service validation
- Edge cases to cover
- Test data requirements

### 7. Milestones
Break the implementation into ordered milestones. Each milestone should be:
- **Independently shippable** — produces a working state, even if incomplete
- **Reviewable** — small enough for a single PR
- **Testable** — has clear acceptance criteria

Format:
```
#### Milestone 1: {title}
- **Deliverable**: What's done at the end of this milestone
- **Services**: Which repos are touched
- **Key tasks**:
  - [ ] Task 1
  - [ ] Task 2
- **Acceptance criteria**: How to verify this milestone works
```

### 8. Open Questions & Risks
- Unresolved design decisions
- Dependencies on other teams or features
- Performance concerns
- Migration risks

## Output
Save as: `workdocs/{feature-name}/{version}/plan.md`

Also save research to: `workdocs/{feature-name}/{version}/research.md`

## Quality Checklist
- [ ] `README.md` and `docs/domain-map.md` were read before research began
- [ ] Blast Radius section lists every 1-hop and 2-hop consumer from the domain map
- [ ] Every affected surface has a confirmed status (in-scope / deferred / out-of-scope) — none left as `TBD`
- [ ] User was asked about any surface the spec did not explicitly address
- [ ] HLD covers all affected services and their interactions
- [ ] LLD has concrete schema, API, and component details
- [ ] Security review covers auth, validation, and data access
- [ ] Milestones are independently shippable and ordered
- [ ] Testing strategy covers unit, integration, and edge cases
- [ ] References existing codebase patterns

## Next Step
After saving the plan, print:
"Draft v1 saved. Review the plan and tell me what to revise — architecture, scope, milestones, anything. When ready, run `/engineering/execute-plan workdocs/{feature-name}/{version}/plan.md` to implement."
