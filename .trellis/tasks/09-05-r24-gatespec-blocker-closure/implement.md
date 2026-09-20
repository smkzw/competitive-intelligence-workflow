# 实施计划 — R2.4 逐对象 GateSpec 与 blocker 闭包

- [x] P1 全量审计 GateSpec、evaluator、exhaustion、blocker audit、科学 QC 与 run-service
  真实消费链，形成重复真源和可绕过矩阵。
- [ ] P2 建立逐对象逐适用单元的稳定评估/摘要合同，补齐来源角色、成熟度、新鲜度、
  缺失、零值、冲突、适用性和候选宇宙不可删减边界。
- [x] P3 收束两轮恢复与信息增益饱和：真实执行回执、不同策略家族、历史差异及独立遗漏
  终审相互绑定。
- [x] P4 完整化机器 blocker audit 与简洁用户页，接入唯一原子发布、幂等恢复和历史快照。
- [x] P5 在产品运行证明核心可答带限制、核心不可答 no-draft；覆盖篡改、跨报告/对象借用、
  技术失败误分类、零值/不适用伪造和下游残留。
- [ ] P6 完成受控执行、独立会商、聚焦/integration/全仓 gate、bundle/fresh-install、
  checkpoint、精确清理和任务归档。

## 回滚与卫生

不 reset/checkout/clean，不复制旧状态机。只删除本任务可再生的临时目录、测试下载和
runner 原始日志；先保留摘要、哈希、review、metrics 与当前/上一恢复点。
