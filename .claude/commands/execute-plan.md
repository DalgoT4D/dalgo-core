# Execute BASE PRP

Implement a feature using using the PRP file.

## Planning document: $ARGUMENTS

Make sure to always generate a {feature_name}_tasks.md first and mark the tasks that are finished as you execute them. 
This should be your checkpoint when you start. So you dont have to repeat stuff. 
If the file is not present, you can create a new one in root directory or else use an existing one to figure out where to start from 

## Execution Process

1. **Load the plannig document**
   - Read the specified planning document file
   - Understand all context and requirements
   - Follow all instructions in the planning document and extend the research if needed
   - Ensure you have all needed context to implement the planning document fully
   - Do more web searches and codebase exploration as needed

2. **ULTRATHINK**
   - Think hard before you execute the plan. Create a comprehensive plan addressing all requirements.
   - Break down complex tasks into smaller, manageable steps using your todos tools.
   - Use the TodoWrite tool to create and track your implementation plan.
   - Identify implementation patterns from existing code to follow.

3. **Execute the plan**
   - Execute the planning document
   - Implement all the code

4. **Validate**
   - Make sure all the service where the code was change are up & running
   - Run each validation command
   - Fix any failures
   - Re-run until all pass
   - Make sure all the test cases pass

5. **Complete**
   - Ensure all checklist items done
   - Run final validation suite
   - Report completion status
   - Read the PRD again to ensure you have implemented everything

6. **Pre-merge check**
   - Suggest running `/ship-checklist` before committing
   - Print: "Implementation complete. Run `/ship-checklist` to verify before merge."

7. **Reference the PRD**
   - You can always reference the PRD again if needed

Note: If validation fails, use error patterns in PRD to fix and retry.