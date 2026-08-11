Active task: .trellis/tasks/08-10-phase-0-foundation

# 独立只读检查：康哲 design_specs 修复与重新冻结合同

你是与提案编写者隔离的检查者。只读检查，不得修改、格式化、提交、移动或删除任何文件。

工作根：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`

## Hard boundaries

- 只读检查；不得修改、格式化、提交、移动或删除任何文件。
- 不访问网络，不运行生成器，不启动浏览器服务器，不干预其他任务。
- 只允许读取下列文件；相对路径均从工作根解析。
- Runner-managed report path: `runs/conference/ci_phase0_design_repair_contract_20260811/luna_check.md`. Never write that report path with tools; return the complete report and let the caller persist it.

## Initial read set

1. `AGENTS.md`
2. `.trellis/tasks/08-10-phase-0-foundation/prd.md`
3. `.trellis/tasks/08-10-phase-0-foundation/design.md`
4. `.trellis/tasks/08-10-phase-0-foundation/implement.md`
5. `docs/decisions/0002-kangzhe-contract-reconciliation.md`
6. `docs/decisions/0004-structured-report-rendering-boundary.md`
7. `docs/decisions/0005-kangzhe-design-spec-repair-contract.md`
8. `reviews/codex_ci_phase0_kangzhe_s1_candidate_20260811.md`
9. 已批准实施计划中 Task 0.3–0.5：`../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`
10. 上游只读文件：
   - `../../康哲项目资料/模版/design_specs/ROUTER.md`
   - `../../康哲项目资料/模版/design_specs/README.md`
   - `../../康哲项目资料/模版/design_specs/ARCHITECTURE.md`
   - `../../康哲项目资料/模版/design_specs/local_map.md`
   - `../../康哲项目资料/模版/design_specs/core.md`
   - `../../康哲项目资料/模版/design_specs/tests/test_package_load.py`
   - `../../康哲项目资料/模版/design_v21_e2e/sources/S1_pptx_ops_brief.md`
   - `../../康哲项目资料/模版/design_v21_e2e/deliverables/S1_pptx_hy3/FRICTION.md`
   - `../../康哲项目资料/模版/design_v21_e2e/deliverables/S1_pptx_hy3/DONE.md`
   - `../../康哲项目资料/模版/design_v21_e2e/reviews/CLEAR_MATRIX.md`

必要时只读检查 PPTX 生成脚本或已渲染 PNG，但不要运行生成器、不要访问网络、不要干预其他任务。

## 验收重点

- 提案是否准确匹配已批准 Task 0.3 停止条件，没有授权自己修改共享目录或提前进入 Task 0.4；
- 是否正确处理 `core.md` §0.7 的 12 pt 默认下限与 ultra 表体/轴标签 10.5 pt 例外；
- DS01–DS10 是否足以阻止：零文件 `EXIT:0`、生成者自签、兄弟 fixture 补数、HTML-PPT 讲者功能缺失/快捷键冲突/短讲稿/字号违规、PPTX KPI 重叠/字号例外滥用/来源外数字；
- source-pack 数字允许表是否会误伤页码/日期/章节号，或留下宽泛白名单绕过；
- PPTX/HTML 真实渲染、current-run 摘要和独立接受是否形成不可伪造的完成判定；
- S2 四轨矩阵和重新冻结条件是否机械、可执行、没有只写在 prose 的 P0/P1；
- 是否保持门户、原生 PDF、HTML-PPT、PPT Master PPTX 的后续边界，不让设计 S2 偷换成竞品报告实现；
- 用户可见内容仍为中文原生，不把内部回执、提示词、生成状态或日志放进受众页面；
- 不新增安全专项工作。

## 输出格式

只输出以下之一：

- `PASS`，随后不超过 10 条精确证据；或
- `FAIL`，按 P0/P1 列出文件、章节、问题、可复现原因和最小修复。

不要泛化重写提案，不要提出超出当前 Task 0.3 候选修复的功能，不要声称 Phase 0 或系统完成。
