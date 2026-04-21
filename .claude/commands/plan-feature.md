# Create a detailed feature implementation planning document

## Feature file: $ARGUMENTS

Generate a complete planning document for feature implementation with thorough research. This is a **Draft v1** — meant to be reviewed and refined by the engineering team through conversation.

## Pre-Check: Look for Existing Work

Before starting research:
1. If `$ARGUMENTS` points to a file (e.g. `workdocs/{feature-name}/v1/spec.md`), use it as the primary input.
2. Otherwise, extract the feature name and check `workdocs/{feature-name}/` for existing specs or plans.
3. If a top-level `spec.md` exists (PM's original spec), read it for full context.
4. If a versioned `v1/spec.md` exists, use it as the scoped input for this iteration.
5. If no spec exists, proceed with the standard research process below.

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

### 2. High-Level Design (HLD)
- System-level architecture: how services interact for this feature
- Data flow diagrams (describe in text or ASCII)
- New API endpoints or modified endpoints
- External service integrations (Airbyte, Prefect, dbt, warehouse)
- Key design decisions and trade-offs

### 3. Low-Level Design (LLD)
- **Data model**: New/modified Django models, migrations, schema changes
- **API design**: Request/response schemas, endpoint signatures, error codes
- **Backend logic**: Core layer functions, service interactions, Celery tasks if needed
- **Frontend components**: New/modified components, hooks, state changes
- **Integration points**: How frontend calls backend, how backend calls external services
- Reference real files and existing patterns for each

### 4. Security Review
- **Authentication & Authorization**: Are new endpoints protected with `@has_permission`? What roles can access this?
- **Input validation**: Where does user input enter the system? Is it validated at API boundaries (Pydantic schemas)?
- **Data access control**: Can users access only their own org's data? Are there multi-tenant leaks?
- **Sensitive data**: Does this feature handle PII, credentials, or tokens? How are they stored/transmitted?
- **Injection risks**: Any raw SQL, dynamic queries, or template rendering with user input?
- **External service calls**: Are secrets managed via env vars? Are responses validated before use?
- **Rate limiting / abuse**: Could this endpoint be abused? Does it need throttling?

### 5. Testing Strategy
- Unit tests: what to test, which modules
- Integration tests: cross-service validation
- Edge cases to cover
- Test data requirements

### 6. Milestones
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

### 7. Open Questions & Risks
- Unresolved design decisions
- Dependencies on other teams or features
- Performance concerns
- Migration risks

## Output
Save as: `workdocs/{feature-name}/{version}/plan.md`

Also save research to: `workdocs/{feature-name}/{version}/research.md`

## Quality Checklist
- [ ] HLD covers all affected services and their interactions
- [ ] LLD has concrete schema, API, and component details
- [ ] Security review covers auth, validation, and data access
- [ ] Milestones are independently shippable and ordered
- [ ] Testing strategy covers unit, integration, and edge cases
- [ ] References existing codebase patterns

## Next Step
After saving the plan, print:
"Draft v1 saved. Review the plan and tell me what to revise — architecture, scope, milestones, anything. When ready, run `/execute-plan workdocs/{feature-name}/{version}/plan.md` to implement."
