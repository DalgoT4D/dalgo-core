# Create a detailed feature implementation planning document

## Feature file: $ARGUMENTS

Generate a complete planning document for general feature implementation with thorough research. Ensure context is passed to the AI agent to enable self-validation and iterative refinement. Read the feature file first to understand what needs to be created, how the examples provided help, and any other considerations.

The AI agent only gets the context you are appending to the PRP and training data. Assume the AI agent has access to the codebase and the same knowledge cutoff as you, so its important that your research findings are included or referenced in the PRP. The Agent has Websearch capabilities, so pass urls to documentation and examples.

## Pre-Check: Look for Existing Spec

Before starting research, check if a spec exists:
1. If `$ARGUMENTS` points to a file in `dalgo-ai-gen/dalgo_mds/specs/`, use it as the primary input.
2. Otherwise, extract the feature name and check `dalgo-ai-gen/dalgo_mds/specs/{feature-name}_spec.md`.
3. Also check `dalgo-ai-gen/dalgo_mds/claude/planning/` for existing plans on the same topic.
4. If a spec is found, use it as the primary input alongside the feature file. The spec provides problem statement, user stories, scope, and open questions that should inform the plan.
5. If no spec exists, proceed with the standard research process below.

## Research Process

1. **Codebase Analysis**
   - Search for similar features/patterns in the codebase
   - Identify files to reference in PRP
   - Note existing conventions to follow
   - Check test patterns for validation approach

2. **External Research**
   - Search for similar features/patterns online
   - Library documentation (include specific URLs)
   - Implementation examples (GitHub/StackOverflow/blogs)
   - Best practices and common pitfalls

3. **Clarification**
   - Ask questions if needed around the feature.

4. **Micro services**
   - Since Dalgo has multiple services. Analyze which services you would need to work in and what changes each service would have.
   - How would you go about validating that changes in each service work.
   - Think about integration testing too, functional testing and unit testing.  


## What to include in the planning document

### Critical Context to Include and pass to the AI agent as part of the PRP
- **Documentation**: URLs with specific sections
- **Code Examples**: Real snippets from codebase
- **Gotchas**: Library quirks, version issues
- **Patterns**: Existing approaches to follow

### Implementation Blueprint
- Use a top down approach. First figure out a high level flow/design of the feature
- Then get into low level quirks like schema design, data modelling, request-response flow, api design, modules, classes etc.
- Implement the models and migrations if needed. 
- Reference real files for patterns
- Write specific frontend logic and test it
- Include error handling strategy

### Testing & Validation
- The planning doc should also include testing steps and how to implement them. 
- The test cases should be meaningful and should cover edge cases. 
- The success criteria should have the test cases pass. 


*** ULTRATHINK ABOUT THE PLANNING DOCUMENT AND PLAN YOUR APPROACH THEN START WRITING THE PRD ***

## Output
Save as: `dalgo_mds/planning/{feature-name}_plan.md`


## Quality Checklist
- [ ] All necessary context included
- [ ] Validation gates are executable by AI
- [ ] References existing patterns
- [ ] Clear implementation path for all service(s)
- [ ] Error handling documented
- [ ] PRP confidence score (1-10): Rate how confident you are that an AI agent can implement this plan without additional context. A score below 7 means the plan needs more detail.

## Next Step
After saving the plan, print:
"Next: Run `/execute-plan <plan-path>` to implement"

