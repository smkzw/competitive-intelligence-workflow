# Execution Context: ci-r2-terminal-recovery-review-boundary-20260905

Created: 2026-09-05 05:40:10 CST
Objective: 完成 R2 剩余科学控制：为 fresh B/C 实现两轮不同策略恢复后的类型化双重穷尽终态与审计/证据不足页；绑定可验的独立上下文复核回执；阻止 rendered_unreviewed 预览路径进入发布接受。不得触碰旧根，不得宣称 R2/RC 完成。
Task type: `long_horizon_code`
Risk: `high`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `off_peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `zcode/glm-5.3-flash:max -> openai-codex/gpt-5.6-luna:max -> codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `zcode` / `zcode` / `GLM-5.3-Flash`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md` §§5–6, 8–9, 13.
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md` R2.4, R3.4 and release gates.
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/checkpoint_20260905_r2_bc_science_wiring.md`.
- Current `fresh_research_ingestion.py`, `fresh_b_research_package.py`,
  `fresh_c_research_package.py`, `run_service.py`, blocker/snapshot/acceptance models and
  their directly related tests.
- The user-approved product contract: two distinct recovery strategies plus independent
  clean-context review before terminal insufficiency; one public Skill; HTML-only release;
  preview data must never become scientific or release acceptance.
- Existing Skill text and model reports are implementation evidence only, not authority.

## Risk Boundaries

- No production writes.
- The forbidden old workspace must not be read, resolved, inventoried, checked, written,
  chmodded or deleted.
- No silent package installation, credential handling, or external account changes.
- Each worker runs in its own runner-provided isolated repository copy. It may edit only
  `src/ci_workflow/`, `schemas/`, `policies/` and directly relevant `tests/` files needed
  for its assigned item. It must not edit governance docs, other workers' reports,
  generated portals, snapshots, manifests, credentials or package outputs.
- Use TDD: record a focused RED before implementation and focused GREEN after it. Do not
  weaken tests or accept caller-declared gate/review/release decisions.
- Preserve existing user changes; no reset, checkout, clean or `git add .`.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 设计并实现 fresh B/C 共用的类型化双重穷尽记录、终端 evidence_blocked 状态、blocker 审计 JSON/Markdown 与简洁证据不足页，先写负向测试且不允许单轮恢复伪装穷尽。
2. 设计并实现独立科学复核的不可变宿主回执合同：绑定生产上下文、复核上下文、内容摘要、review artifact digest 和时间顺序；无独立上下文能力时失败关闭，保持三宿主可适配。
3. 审计并修复发布接受边界：rendered_unreviewed/report-data/preview 路径可用于开发预览但不得生成可被科学/视觉/RC 接受的后继；补充 fail-closed 合同与回归测试。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
