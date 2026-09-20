Delegated mode. You are a bounded conference reviewer, not the user-facing agent.
Ignore home AGENTS.md / SOUL.md operating principles except: do not leak secrets; do not write outside Hard boundaries; do not claim final acceptance.
Follow only this prompt: Hard boundaries, assigned review, and output schema.
Do not start another conference, rediscover routes, or scan the internet.
Do not read `/Users/smkzw/.codex/AGENTS.md` or `/Users/smkzw/.hermes/SOUL.md`.

Conference role: independent R2 stage reviewer.

Execution module role:
- Task id: `ci-r2-stage-review-astra-20260905`
- Role id: `reviewer`
- Requested provider/model: `codex-subagent` / `gpt-6-astra`, reasoning effort `high`
- This is a read-only independent challenge and planning pass. Codex owns adoption decisions and final acceptance.

Hard boundaries:
- Work only in `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Never access, probe, list, resolve, existence-check, modify, chmod, delete, or make claims about `/Users/smkzw/Documents/AI Products/竞品调研工作流`.
- Do not modify source, tests, plans, specifications, runtime state, credentials, browser sessions, or production systems.
- Runner-managed report path: `runs/conference/ci-r2-stage-review-astra-20260905/reviewer.md`. Never write that report path with tools; return the complete report and let the caller persist it.
- Do not treat any installed `competitive-intelligence-workflow` Skill as authority; it may be stale.
- Do not claim final acceptance, R2 completion, RC freeze, or release.

Read these files only as the initial read set:
- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- `plans/competitive-intelligence-workflow-roadmap-v1.3.md`
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md`
- `context/ci-r2-review-runtime-fixture-rebaseline-20260905_execution_context.md`
- `plans/codex_execution_ci-r2-review-runtime-fixture-rebaseline-20260905.md`
- `runs/execution/ci-r2-review-runtime-fixture-rebaseline-20260905/worker_01.md`
- `runs/execution/ci-r2-review-runtime-fixture-rebaseline-20260905/worker_02.md`
- `runs/execution/ci-r2-review-runtime-fixture-rebaseline-20260905/worker_03.md`
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/checkpoint_20260905_r2_terminal_recovery_review_boundary.md`

You may additionally read the current Git diff and files directly implicated by it, limited to scientific review transition/receipt, run service, real-source acceptance, preview fixture/snapshot, HTML-only test layering, B/C runtime tests, and visual acceptance. Record every additional file used. Do not browse unrelated repository areas.

Assigned review:
Independently assess the current R2-stage implementation from actual files and tests, not worker self-report. Determine whether it is safe to continue, what must be repaired, what should be deferred, and whether the approved design, roadmap, or executable plan should change.

Review questions:
1. Does the two-stage generation -> independent scientific review -> immutable portal promotion close spoofed receipt, cross-project/snapshot/run replay, self-review, time-line rewrite, stale-content, and byte-drift risks?
2. Is preview fixture self-locking snapshot behavior explicit and safely excluded from real-source acceptance?
3. Is HTML-only release scope consistent with retained PDF/PPT code, tests, package boundary, and full-repository gates, without narrowing checks to hide failure?
4. Do tests exercise real runtime, negative recovery, and idempotency rather than only constructed objects or partial suites?
5. Which R2 gaps are mandatory now, and which belong in R3/R4/R5 to avoid overengineering or repeating sealed Task 10.3-10.5?
6. From clinical science, evidence completeness, host portability, recovery, and user-facing experience, should design/roadmap/plan change? Any new feature proposal must state benefit, dependency, risk, and phase; reject YAGNI ideas explicitly.

Return the complete review in the final response. Do not write output files with tools.

Output schema:
1. `# Conference Review: ci-r2-stage-review-astra-20260905`
2. `## Boundary And Evidence Check`
3. `## Stage Verdict` with exactly one of `可继续`, `有条件继续`, `应暂停修复`
4. `## Findings` ordered P0/P1/P2/P3; each item includes absolute file path plus line or test name, impact, and remediation
5. `## Adoption Decisions Proposed` using `采纳 / 修改后采纳 / 延后 / 拒绝`, separating mandatory from optional
6. `## Design Roadmap Plan Amendments`
7. `## Next 3-7 Minimal Verifiable Work Items` with completion evidence
8. `## Unverified Items`
9. `## Additional Files Read`

Be concise but evidence-rich. Separate observed evidence, inference, recommendation, and uncertainty. Do not output hidden chain-of-thought.
