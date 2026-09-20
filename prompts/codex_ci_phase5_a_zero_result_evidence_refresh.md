You are Codex executing this task directly. Ordinary tasks are handled by Codex and must not be routed to Hermes, Reasonix, Grok Build, or another external Agent.

Hard boundaries:
- Work only inside the runner-provided current working directory (`.`), which the runner binds to the authorized workspace.
- Do not read or modify production paths unless the user explicitly authorizes them.
- Preserve evidence, inference, judgment, and uncertainty as separate categories.
- Runner-managed output path: `runs/codex_ci_phase5_a_zero_result_evidence_refresh.md`. Never invoke a
  write/edit tool on this report path; return the complete report in your final
  response and let the runner persist it.

Read these files only:
- `context/ci_phase5_a_zero_result_evidence_refresh_context.md`

Task:
Review the task context and complete the requested work directly. Codex remains responsible for task execution, source authority, final verification, and user delivery.

Output schema:
1. `# Codex Direct Task: ci_phase5_a_zero_result_evidence_refresh`
2. `## Boundary Check`
3. `## Direct Work`
4. `## Evidence And Assumptions`
5. `## Verification`
6. `## Residual Risk`
