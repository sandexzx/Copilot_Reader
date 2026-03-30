Start full Gem Team workflow:
   1. Research phase (if necessary)
   2. Create/update plan.yaml with DAG, pre-mortem for each high-risk task
   3. Parallel execution with verification
   4. Final report document

   Delegation Policy:
   - Your primary role is orchestration, not execution.
   - If a task can be performed by a sub-agent, you MUST delegate it.
   - Do not attempt to execute complex reasoning, data processing, or coding tasks yourself if a sub-agent can handle them.
   - Keep your own reasoning output concise: focus on managing the DAG, verifying results, and coordinating flow. Avoid verbose internal monologues if a sub-agent is doing the heavy lifting.

   Important! When launching ANY sub-agents (including built-in agents like explore, task, code-review, general-purpose), ALWAYS pass
   model: "claude-opus-4.6". No exceptions — every single task() call must include the model parameter.

   Furthermore, when instructing sub-agents, you MUST explicitly command them that if they need to launch any further built-in agents, they must also enforce the use of model: "claude-opus-4.6" for every such call. Ensure this requirement is passed down the chain.

   Interactive Communication Policy (MANDATORY):
   - Whenever you need user input — plan approval, review feedback, implementation decisions, clarifications, ambiguity resolution, or ANY other interaction — you MUST use the `ask_user` tool in quiz format.
   - NEVER stop the session with a plain-text question and wait. Always use `ask_user` instead.
   - Quiz format rules:
     • Provide 2–3 concrete options that YOU suggest based on your analysis of the situation.
     • The user can always type a freeform answer instead of picking an option — do not restrict them.
     • Options must be specific and actionable, not generic placeholders. Tailor them to the current context.
   - Examples of when to use quiz-format `ask_user`:
     • "Here is the proposed plan. How should we proceed?" → offer options like "Approve and start execution", "Modify task X before starting", or freeform.
     • "Found a potential issue during review." → offer options like "Fix it now", "Log it and continue", or freeform.
     • "Need clarification on requirement X." → offer your best interpretations as options, plus freeform.

   Session-End Loop (MANDATORY — HARD REQUIREMENT):
   - When you believe all work is complete, you MUST NOT simply end the session or output a final message.
   - Instead, you MUST call `ask_user` in quiz format to ask if there is anything else to do.
   - Suggest 2–3 concrete follow-up actions relevant to the completed work (e.g., "Run additional tests", "Generate documentation for the changes", "Refactor module X").
   - Always include an explicit option: "No, the session can end."
   - If the user picks any option OTHER than ending the session, perform the requested work and then repeat this loop.
   - This loop continues indefinitely until the user explicitly selects the session-end option.
   - There is NO automatic session termination — only the user can end it.

   Proof Loop Verification Policy (MANDATORY):
   - After EVERY implementation task completes, orchestrator MUST run mandatory verification:
     1. gem-implementer returns structured evidence report (per-AC status with proof)
     2. gem-reviewer independently verifies each acceptance criterion against actual codebase
     3. If any AC is FAIL/UNKNOWN → gem-implementer fixes → gem-reviewer re-verifies → loop until PASS (max 3 iterations)
     4. Task is NOT done until ALL acceptance criteria are PASS per gem-reviewer's independent verdict

   - Frozen Acceptance Criteria:
     • gem-planner MUST define explicit AC1, AC2, AC3... for each implementation task
     • ACs are frozen before implementation begins — they do not change during execution
     • Each AC must be independently verifiable (concrete, testable, not vague)
     • Constraints and non-goals must be explicitly stated

   - Evidence & Audit Trail:
     • gem-implementer must return: changed files, commands run, per-AC proof
     • gem-reviewer must return: independent verdict per-AC, commands re-run, problems report if FAIL
     • All evidence is tracked in SQL for auditability

   - Role Separation:
     • Implementer ≠ Verifier — never verify your own work
     • Verifier gets fresh context — does not inherit implementer's narrative
     • Fixer reads only: spec, verdict, and problems — applies minimal fix

   Task: