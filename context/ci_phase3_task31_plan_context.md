# Task Context: ci_phase3_task31_plan

Created: 2026-08-12 02:45:05
Objective: 独立审查 Phase 3 Task 3.1 A/B/C 版本化证据规则与覆盖评估实施边界，发现科学规则遗漏、误阻断或可绕过路径
Task type: `high_risk_contradiction_review`
Risk: `high`
Selected agent route: `codex` / `gpt-5.6-luna` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/decisions/0011-phase-3-evidence-gates-and-recovery.md`：批准设计 v1.2 与实施计划 Phase 3 的项目内精简合同。
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/{prd,design,implement}.md`：当前 Phase 3 任务边界与 Task 3.1 清单。
- `docs/acceptance/runs/phase-2-exit/verdict.md` 与 `reviews/codex_ci_phase2_exit_review.md`：Phase 2 accepted 输入和未接受边界。
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` 仅在精简合同出现歧义时按指定章节核对，不全量加载。

## Scope

- In scope: 只读审查 Task 3.1 的 A/B/C GateSpec 内容、适用性、阻断/非阻断边界、覆盖结果、项目覆盖只收紧与新合同版本/受影响报告重算设计；发现遗漏、误阻断、可删除产品/试验绕过或无法机械测试之处。
- Out of scope: 不修改文件，不实现 Task 3.1，不扩展到 Task 3.2 之后的阻断包/下载/控制图，不验收 Phase 3，不进行安全测试。

## Success Criteria

- A 的成熟度与已有数值结果项目最低疗效/安全摘要；B 的每核心试验、每可比较组基线与最低疗效/安全，同时处置字段非阻断；C 的临床设计核心与统计细节非阻断均无缺口。
- 任一适用关键单元失败都阻断对应报告，不能通过删除产品/试验、总体值冒充分组值或缺失写零绕过。
- 项目覆盖删除/放松基础规则均失败，只允许增加单元或提高阈值；产生新项目合同版本、保留旧结果并只重算受影响报告。
- 三个指定测试文件能以确定性、参数化反例证明上述边界；P0/P1=0 才建议激活实现。

## Risk Boundaries

- 全程只读；不得修改工程文件或 runner 管理的报告路径。
- 用户可见中文不是本轮报告模板，但审查者应指出任何会迫使后续界面暴露程序状态或“xx门/信号”等非用户语言的合同设计。
- 不做安全测试；只审科学功能、数据完整性和用户恢复边界。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-12 02:45:05: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- Phase 2 已以 61 项阶段测试、188 项全库测试和 Luna/max P0/P1/P2=0 独立验收接受；本轮不得重新打开其科学真源结论。
- 原生 Luna 在当前 Codex App 会话已被实际能力探测明确拒绝，按全局规则使用 CLI 兼容路线；新只读会话 `019ff225-134d-7321-9d40-919702c3d90d`，未切换模型或另行重派。
- 首轮方案否证为 FAIL（P0=2、P1=7、P2=1）；补充闭世界对象集合、B 作用域、A 观察性结果触发、只收紧偏序、结果版本和 exact tests 后，同会话第二轮为 P0=0、P1=5、P2=0。
- 再补封闭枚举、计划/观察结果区分、偏序公式、不可变结果键、反向依赖和 B 逐组反例后，同会话最终复核 PASS，P0=0、P1=0、P2=0；最终报告摘要 `42eb575c8c8be3d36d325980c8f5775ba58bd3b339622033c2aeaeed1a54a03c`。
