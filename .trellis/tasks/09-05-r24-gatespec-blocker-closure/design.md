# 设计 — R2.4 逐对象 GateSpec 与 blocker 闭包

## 真源与边界

- 规范真源：`docs/specs/competitive-intelligence-workflow-design-v1.3.md` 第 5.4、5.5、6 节。
- 执行计划：`plans/codex_execution_ci-rebaseline-rebuild-v3.md` R2.4。
- 现有 `ci_workflow.gates`、A/B/C GateSpec YAML、科学 QC 和 blocker 代码均为待核验实现，
  不是自动正确的权威。
- R2.2 宇宙闭包和 R2.3 Publication/manual gate 只通过稳定合同接入，不重复建设。

## 控制链

1. 读取已锁定的项目/报告候选宇宙与版本化 GateSpec。
2. 由 GateSpec 的适用性谓词展开 `(report, object, unit)` 矩阵。
3. 对每个单元校验事实值状态、来源角色、披露成熟度、新鲜度、完整上下文和冲突状态。
4. 缺失、异常零值、未决冲突或技术路线问题进入两条不同策略的恢复；回执证明实际执行
   与信息增益，而非仅改变字符串。
5. 干净上下文 reviewer 按完整矩阵检查遗漏；producer/reviewer、上下文与摘要均不同且绑定。
6. 只有全部适用关键单元通过、无关键冲突且独立科学 QC accepted 才可进入渲染。
7. 否则原子发布机器 blocker audit 与简洁用户 Markdown，并断言零下游门户/草稿。

## 最小审计对象

blocker audit 至少绑定合同/报告/GateSpec 版本与摘要、候选宇宙、失败对象和单元、事实及
缺失状态、来源与定位、全部路线回执、两轮信息增益差异、独立遗漏结论、诊断、不确定性、
是否需要用户、最小动作、附件/外链、唯一投递目录、恢复节点和 no-draft 断言。

上述 GateSpec/双重穷尽字段适用于 GateSpec 或科学质控失败。必需论文经自动获取和一次
人工补件仍不可得时，使用独立 `publication_unavailable` 审计合同，绑定补件门原始字节、
请求、阻断字段、真实尝试路径、用户唯一响应与原文链接；不得伪造未发生的 GateSpec 失败
或科学恢复轮次。三类审计均共享项目/报告身份、原子双文件发布、no-draft、恢复节点、
同版本幂等、漂移拒绝和恢复时全量重验证基线，并分别由安装包登记的 JSON Schema 约束。

## 负向重点

- 适用对象被删、总覆盖率掩盖关键失败、跨对象事实借用、来源角色/成熟度/新鲜度不足。
- `reported_zero` 无原文、`not_applicable` 无版本化谓词、技术错误伪装无证据。
- 两轮使用同一路线家族、虚构执行回执、信息增益历史错位或独立 reviewer 自审。
- blocker 缺字段、额外文件、漂移覆盖、软链接/路径跳转、用户 Markdown 泄漏内部语言。
- 任何阻断后仍出现 reports、render staging、artifact manifest 或锁定候选草稿。

## 验收策略

先由三个只读执行 worker 分别审计 GateSpec/逐对象矩阵、恢复与信息增益、blocker/no-draft
产品接线；Codex 建立真实 RED、实施最小修复并运行分层门。之后使用不同模型的独立会商
挑战遗漏和产品诚实性，Codex 最终裁决。
