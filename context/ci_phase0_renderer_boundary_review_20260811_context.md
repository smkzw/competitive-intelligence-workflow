# Task Context: ci_phase0_renderer_boundary_review_20260811

Created: 2026-08-11 08:39
Objective: 独立验收 Phase 0 的“结构化医学内容—确定性渲染—真实产物验收”边界，修复会导致后续报告假完成的 P0/P1 缺口。
Task type: `high_risk_contradiction_review`
Risk: `high`
Effective route: `codex` / `gpt-5.6-luna` / `max`

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `.trellis/tasks/08-10-phase-0-foundation/{prd.md,design.md,implement.md}`
- `docs/decisions/0002-kangzhe-contract-reconciliation.md`
- `docs/decisions/0003-offline-presentation-assets.md`
- `docs/decisions/0004-structured-report-rendering-boundary.md`
- 上游只读 S1 日志、HTML-PPT 实产物源码和 `design_specs/{local_map.md,ARCHITECTURE.md}`

## Scope And Boundaries

- 只修改新仓 ADR 与 Trellis Phase 0 检查点；不修改上游康哲设计包、旧工程或活动报告产物。
- 不复制或冻结 design_specs，不进入 Task 0.4，不请求用户确认不稳定候选。
- 不扩展安全专项测试；只检查架构、功能、语义一致性、中文用户体验和真实验收边界。
- 检查者只读，拥有接受/否决权；Codex 主会话负责最小修复和最终提交。

## Route And Recovery Record

1. 原生 Codex 子任务能力探测请求 `gpt-5.6-luna:max`，接口明确返回 `Unknown model gpt-5.6-luna`；这是能力拒绝，不是延迟或健康检查超时。
2. `hermes_workflow_guard.py route --task-type high_risk_contradiction_review --risk high` 确认首选路由仍为 `codex/gpt-5.6-luna:max`。
3. 按全局合同使用 ChatGPT 内置 Codex CLI 兼容路由，未替换成 Sol/Terra、Hermes 或其他模型：
   - model：`gpt-5.6-luna`
   - effort：`max`
   - session：`019fee44-1f71-7820-b0da-b075c930af27`
   - fallback reason：`native_spawn_rejected_unknown_model`
4. 首轮只读验收为 FAIL，发现两个 P1；主会话最小修复后复用同一 session 复核，最终 PASS。

## Decisive Findings

- S1 流式路线写入工具连续四次参数序列化失败，零文件却 `EXIT:0`。
- S1 HTML-PPT 缺讲者运行时、快捷键冲突、逐字稿不足、存在过小文字。
- S1 HTML-PPT 可见摘要声称运营主责 5/9，但 RACI 九行和另一处列表可重算为 6/9；视觉或运行成功不能替代跨页语义一致性。
- ADR 0002 顶部一度错误指向已经失效的历史章节；已修为 §§1–9 历史、§§10–14 当前。
- ADR 0004 已要求每个可见数字、比例、计数、列表长度、排序标签和定量结论绑定稳定 claim/fact/row ID，并在首页、详情、图、表、逐字稿和四格式间可重算一致。

## Result

本次边界复核最终 PASS；只证明 ADR/Trellis 边界已闭合，不证明 Task 0.3、Phase 0 或系统完成。
