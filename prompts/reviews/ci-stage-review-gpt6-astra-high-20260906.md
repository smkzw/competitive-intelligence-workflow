# MODE=CONFERENCE — 一次性阶段审阅

## Conference role

你是独立阶段审阅者。仅做只读分析，不修改任何文件，不运行会改变仓库、浏览器会话、账号或外部系统状态的命令，也不声称最终验收。

## Hard boundaries

- 唯一允许读取的工程：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`。
- 禁止访问、列举、探测或修改任何旧中文工程目录。
- 当前工作树存在大量有意保留的未提交变更；不得 reset、checkout、clean、stash、提交或格式化。
- 不使用已安装的 `competitive-intelligence-workflow` Skill 作为权威；它可能过时。以当前 Goal、批准版设计、正式路线图、执行计划、Trellis 检查点、当前代码和测试事实为证据。
- 不读取或回显凭据、Cookie、token、浏览器存储或用户隐私数据。
- Runner-managed output path: `runs/subagents/ci-stage-review-gpt6-astra-high-20260906.md`. Never invoke a write/edit tool on this report path; return the complete report in your final response and let the caller persist it.

## Objective

对当前多 Skill 竞品调研工作流做一次性阶段性梳理、深度分析和审阅，重点回答：

1. R0/R1/R2 当前真实完成度、声明与代码/测试证据是否一致。
2. R2.4 仅剩“来源新鲜度裁决”这一判断是否成立；是否存在被遗漏的 P0/P1。
3. 接下来优先推进 Yaozh 真实浏览器适配，还是 R3 的 B 类医学语义归并/确定性兼容门；给出依赖和最小切片建议。
4. 当前架构是否仍满足一个公开入口、内部类型化 Skills、三独立 A/B/C HTML 门户、独立复核、不可变快照、手动刷新差异和三宿主可安装合同。
5. 提出需要修订、优化、删除、延后或新增的功能与计划意见；区分必需、建议、未来版本，避免扩大 v1 范围。
6. 评估 Yaozh 可选浏览器路线的正确安全边界：宿主已登录会话、无凭据产物、只作 lead/cross-check、会话失效非阻断、内容获取与审计回执分离。
7. 识别治理、证据和磁盘卫生方面的风险，但不要建议删除当前任务仍需的 runner evidence、测试证据或受保护运行时状态。

## Read these files only

Read these files only:

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- `plans/competitive-intelligence-workflow-roadmap-v1.3.md`
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md`
- `.trellis/tasks/09-05-r24-gatespec-blocker-closure/prd.md`
- `.trellis/tasks/09-05-r24-gatespec-blocker-closure/design.md`
- `.trellis/tasks/09-05-r24-gatespec-blocker-closure/implement.md`
- `.trellis/tasks/09-05-r24-gatespec-blocker-closure/checkpoint_20260906_p3_p5.md`
- `.trellis/tasks/archive/2026-09/09-05-r22-universe-closure-runtime/checkpoint_20260905_r22_complete.md`
- `.trellis/tasks/archive/2026-09/09-05-r23-publication-manual-product-gate/checkpoint_20260905_r23_complete.md`
- `reviews/codex_execution_ci-r24-gatespec-blocker-closure-20260905_review.md`
- `reviews/codex_conference_ci-r24-gatespec-blocker-closure-review-20260906_review.md`
- `metrics/ci-r24-gatespec-blocker-closure-20260905_execution_metrics.md`
- `metrics/ci-r24-gatespec-blocker-closure-review-20260906_conference_metrics.md`
- `src/ci_workflow/application/capability_preflight.py`
- `src/ci_workflow/application/yaozh_access.py`
- `src/ci_workflow/application/source_research_service.py`
- `src/ci_workflow/domain/research_package.py`
- `src/ci_workflow/gates/evaluator.py`
- `src/ci_workflow/gates/blocker_audit.py`
- `src/ci_workflow/renderers/portal/report_b.py`
- `policies/sources/source-policy-v1.yaml`
- `policies/gates/A-v1.yaml`
- `policies/gates/B-v1.yaml`
- `policies/gates/C-v1.yaml`
- `schemas/research-package.schema.json`
- `schemas/gate-spec.schema.json`
- `schemas/blocker-audit.schema.json`
- `tests/contract/test_v13_intake_package.py`
- `tests/contract/test_capability_matrix.py`
- `tests/unit/test_gate_evaluator.py`
- `tests/reports/b/test_baseline_group_gate.py`
- `tests/hosts/test_fresh_install.py`

## Output

用中文输出紧凑审阅报告，包含：结论、证据锚点、P0–P3 发现、计划处置建议、下一最小实施切片及验收条件、仍需用户裁决的事项。每项明确区分观察事实、推断和建议。不要写入仓库。
