# Execution Context: ci-r25-yaozh-browser-adapter-20260906

Created: 2026-09-05 21:00:54 CST
Objective: Close the optional Yaozh authenticated-browser adapter contract without credentials, false session readiness, or scientific authority escalation.
Task type: `competitive_intelligence`
Risk: `high`
Execution module trigger: Codex assigned 3 bounded work item(s). Each item must identify its inputs, allowed paths, deliverable and acceptance check.
Route schedule: `off_peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `zcode/glm-5.3-flash:max -> cursor/default -> openai-codex/gpt-6-astra:low`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `evidence_research_executor` -> `zcode` / `zcode` / `GLM-5.3-Flash`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- User-approved product contract: `docs/specs/competitive-intelligence-workflow-design-v1.3.md`, especially the public-entry, source-policy, capability and Yaozh sections.
- Canonical phase/dependency truth: `plans/competitive-intelligence-workflow-roadmap-v1.3.md` and `plans/codex_execution_ci-rebaseline-rebuild-v3.md`.
- Current R2 evidence: `.trellis/tasks/09-05-r24-gatespec-blocker-closure/` and the archived R2.2/R2.3 task checkpoints.
- Current implementation truth: `src/ci_workflow/application/capability_preflight.py`, `src/ci_workflow/application/yaozh_access.py`, `src/ci_workflow/application/autonomous_research.py`, `src/ci_workflow/domain/research_package.py`, `policies/sources/source-policy-v1.yaml`, the matching schemas and tests.
- The installed `competitive-intelligence-workflow` Skill is explicitly non-authoritative and may be stale. Do not use it to decide the contract.
- This execution pass is read-only analysis. Workers may read relevant files inside this workspace but may not edit source, tests, plans, prompts, context, reviews, metrics, runs or any external path. Runner-managed reports are persisted by the runner only.

## Risk Boundaries

- No production writes.
- Never access, list, probe or modify the old Chinese-named workspace.
- Never inspect or emit usernames, passwords, cookies, tokens, authorization headers, browser storage, profile data, screenshots or session traces.
- Do not open a real Yaozh or browser session in this pass; analyze the portable host-adapter contract only.
- Preserve the dirty tree; no reset, checkout, clean, stash, commit, format or dependency installation.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Completion Evidence

- Every finding cites a current workspace file and symbol/section.
- Recommendations distinguish contract, application/session probe, research-package/source-policy integration and later real-host smoke.
- Proposed tests include false browser-readiness, expired/captcha/permission/tool states, secret/path rejection, idempotency and no authority escalation.
- No worker file changes; Codex independently verifies and implements any accepted change with TDD.

## Work Items

1. Audit the current Yaozh project answer, capability probe, source policy, research-package and package boundaries; identify exact fail-closed contract gaps with file evidence.
2. Design the smallest typed session-observation and credential-free access-receipt contract, including expired/captcha/permission/tool states, idempotency and secret/path rejection.
3. Design research-package and source-policy integration plus negative tests proving Yaozh remains optional lead/cross-check and cannot become sole evidence for critical claims.

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
