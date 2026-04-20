# Create a detailed feature implementation planning document

## Feature file: $ARGUMENTS

Generate a complete planning document for feature implementation with thorough research.

## Pre-Check: Look for Existing Spec

Before starting research, check if a spec exists:
1. If `$ARGUMENTS` points to a file in `specs/`, use it as the primary input.
2. Otherwise, extract the feature name and check `specs/{feature-name}_spec.md`.
3. Also check `plans/` for existing plans on the same topic.
4. If a spec is found, use it as the primary input alongside the feature file. The spec provides problem statement, user stories, scope, and open questions that should inform the plan.
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

## What to include in the planning document

### Critical Context
- **Documentation**: URLs with specific sections
- **Code Examples**: Real snippets from codebase
- **Gotchas**: Library quirks, version issues
- **Patterns**: Existing approaches to follow

### Implementation Blueprint
- Use a top-down approach. First figure out a high-level flow/design of the feature.
- Then get into low-level details: schema design, data modelling, request-response flow, API design, modules, classes.
- Implement the models and migrations if needed.
- Reference real files for patterns.
- Write specific frontend logic and test it.
- Include error handling strategy.

### Testing & Validation
- Include testing steps and how to implement them.
- Test cases should be meaningful and cover edge cases.
- Success criteria should have the test cases pass.

## Output
Save as: `plans/{feature-name}_plan.md`

## Quality Checklist
- [ ] All necessary context included
- [ ] References existing patterns
- [ ] Clear implementation path for all affected service(s)
- [ ] Error handling documented
- [ ] Testing strategy defined

## Next Step
After saving the plan, print:
"Next: Run `/execute-plan plans/{feature-name}_plan.md` to implement"
