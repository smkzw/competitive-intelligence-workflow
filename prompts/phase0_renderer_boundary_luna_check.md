Active task: .trellis/tasks/08-10-phase-0-foundation

# 独立只读验收：Phase 0 结构化医学内容与确定性渲染边界

你是与编写者隔离的 Trellis 检查者。只读检查，不得修改、格式化、提交或删除任何文件。

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`，仅下列明确列出的上游文件为只读例外。
- 只读检查；不得修改、格式化、提交、移动或删除任何来源文件。
- 不访问网络，不运行生成器，不干预仍在运行的 S1 进程。
- Runner-managed report path: `runs/conference/ci_phase0_renderer_boundary_review_20260811/luna_check.md`. Never write that report path with tools; return the complete report and let the caller persist it.
- 上游相对路径从本工作区解析为 `../../康哲项目资料/模版/`。

Initial read set:

必须完整读取：

1. `AGENTS.md`
2. `.trellis/tasks/08-10-phase-0-foundation/prd.md`
3. `.trellis/tasks/08-10-phase-0-foundation/design.md`
4. `.trellis/tasks/08-10-phase-0-foundation/implement.md`
5. `docs/specs/competitive-intelligence-workflow-design-v1.2.md` 中架构、报告渲染、四格式和验收相关章节
6. `docs/decisions/0002-kangzhe-contract-reconciliation.md`
7. `docs/decisions/0003-offline-presentation-assets.md`
8. `docs/decisions/0004-structured-report-rendering-boundary.md`
9. 当前 `git status`、`git diff` 和未跟踪的新 ADR
10. `../../康哲项目资料/模版/design_v21_e2e/runs/S1_stream_hy3.log`
11. `../../康哲项目资料/模版/design_v21_e2e/runs/S1_htmlppt_m3.log`
12. `../../康哲项目资料/模版/design_v21_e2e/deliverables/S1_htmlppt_m3/index.html`
13. `../../康哲项目资料/模版/design_specs/local_map.md`
14. `../../康哲项目资料/模版/design_specs/ARCHITECTURE.md`

主 Agent 已运行的机械锚点：`pytest` 6 passed；Ruff passed；mypy passed；`LEGACY_REF_OK`；`uv lock --check` passed。你可以只读复跑必要检查，但不得把这些窄检查扩张为整体完成证明。

## 验收标准

- 决策是否是批准 v1.2 和实施计划的具体化，而非未经授权的新架构；
- 是否准确区分流式工具写入失败、HTML-PPT 功能合同失败和 design_specs 内部矛盾；
- 是否明确禁止仅凭退出码 0、文件存在、截图或生成者自述判定完成；
- 是否保持 HTML 门户、原生 PDF、HTML-PPT、PPT Master PPTX 四条原生输出轨；
- 是否保持 PPTX 必经 PPT Master，且没有暗示确定性渲染器直接制作 PPTX；
- 是否从中文资深临床试验医学用户视角约束可见文案与交互；
- 是否没有修改上游设计包、没有提前冻结候选、没有越过用户精确确认；
- 新 ADR 是否自洽、相对链接有效，Trellis 的 PRD/design/implement 状态是否与真实证据一致；
- 是否存在会允许 future false-green 的 P0/P1 缺陷。

## 输出格式

只输出以下之一：

- `PASS`，随后用不超过 8 条简短证据说明为什么可接受；或
- `FAIL`，随后按 P0/P1/P2 列出精确文件、行号、问题和最小修复。

不要重写文件，不要给泛化建议，不要声称整个 Phase 0 或系统已完成。
