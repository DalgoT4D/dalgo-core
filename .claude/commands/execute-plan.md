# Execute a Feature Plan

Implement a feature using the planning document.

## Planning document: $ARGUMENTS

Make sure to always generate a `{feature_name}_tasks.md` first and mark the tasks that are finished as you execute them.
This should be your checkpoint when you start. So you don't have to repeat stuff.
If the file is not present, you can create a new one in root directory or else use an existing one to figure out where to start from.

## Execution Process

1. **Load the planning document**
   - Read the specified planning document file from `plans/`
   - Understand all context and requirements
   - Follow all instructions in the planning document and extend the research if needed
   - Ensure you have all needed context to implement the planning document fully
   - Do more web searches and codebase exploration as needed

2. **Plan your approach**
   - Think carefully before you execute. Create a comprehensive plan addressing all requirements.
   - Break down complex tasks into smaller, manageable steps.
   - Identify implementation patterns from existing code to follow.

3. **Execute the plan**
   - Implement all the code
   - Follow existing codebase patterns and conventions

4. **Validate**
   - Make sure all services where code was changed are up & running
   - Run each validation command
   - Fix any failures
   - Re-run until all pass
   - Make sure all test cases pass

5. **Complete**
   - Ensure all checklist items done
   - Run final validation suite
   - Report completion status
   - Read the plan again to ensure you have implemented everything

6. **Pre-merge check**
   - Suggest running `/ship-checklist` before committing
   - Print: "Implementation complete. Run `/ship-checklist` to verify before merge."

7. **Reference the plan**
   - You can always reference the planning document again if needed

Note: If validation fails, use error patterns in the plan to fix and retry.
