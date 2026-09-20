# Task Context: ci-r24-gatespec-blocker-closure-20260905

Created: 2026-09-05 18:50:11
Objective: 审计并闭合 R2.4 逐对象 GateSpec、两轮信息增益恢复、独立遗漏复核、完整 blocker audit 与 no-draft 产品门
Task type: `long_horizon_code`
Risk: `high`
Selected agent route: `cursor` / `default` / ``

## Trigger Reason

Codex selected a bounded execution or review unit under the applicable task contract. Record the concrete delegation benefit or independent-review requirement; step count and file format alone are not triggers.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md` 第 5.4、5.5、6 节。
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md` R2.4。
- `.trellis/tasks/09-05-r24-gatespec-blocker-closure/{prd,design,implement}.md`。
- `src/ci_workflow/gates/{models,evaluator,exhaustion,blocker_audit}.py`、
  `src/ci_workflow/sources/retries.py`、`src/ci_workflow/capabilities/scientific_qc.py`、
  `src/ci_workflow/application/{run_service,terminal_recovery,research_package_submission}.py`。
- `policies/gates/{A,B,C}-v1.yaml`、相关 schema、fixture 及分层测试。

## Scope

- In scope: R2.4 GateSpec、恢复信息增益、独立遗漏复核、统一 blocker、no-draft 与安装包合同。
- Out of scope: 新鲜度阈值的未裁决产品选择、门户视觉、真实药智、三宿主实机、24 份真实门户、RC。

## Success Criteria

- 除未裁决新鲜度策略外，P3–P5 的正向、负向、恢复、幂等与产品链测试全绿。
- 全仓开发门、integration/graph/application、bundle/fresh-install 均有准确范围的通过证据。
- 独立会商完成后，由 Codex 判断是否可在获得原生 Ask 裁决后关闭 P2/P6。

## Risk Boundaries

- Do not write to production paths until Codex review gate passes and writable paths are explicit.
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-09-05 18:50:11: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-09-06: 三个只读 worker 审计完成；Codex 对照实际字节逐项处置。
- 2026-09-06: P3–P5 实现完成；聚焦 124 项、产品链 577 项、开发门 944+20+7 项通过。
- 2026-09-06: 实包构建 328 文件并通过 `required-v12` 最终内容校验；临时包精准删除。
- Pending: P2 新鲜度策略必须使用原生 Ask 取得用户裁决，不以实现偏好代替产品决定。
