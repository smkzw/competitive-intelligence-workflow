# 实施计划 — R2.2 竞品宇宙闭包运行态

- [x] U1 审计现有 ontology/closure/research-package/run-service 字节与 schema 漂移，先写
  负向测试和迁移决策。
- [x] U2 实现逐尝试与实体处置类型合同、JSON Schema 和确定性摘要。
- [x] U3 实现路线/维度完整性、失败恢复、连续零新增收敛和独立上下文边界。
- [x] U4 接入 research submit 与 run-service universe 节点，建立持久化/恢复/幂等门。
- [x] U5 覆盖拥挤适应症初搜少量、空宇宙、网络/解析失败、别名合并、边界本体、
  多报告共享宇宙和篡改/跨项目负向场景。
- [x] U6 运行聚焦、integration、全仓 gate、bundle/fresh-install；独立执行审阅和 Codex
  checkpoint 后归档任务。

## 回滚与卫生

不 reset/checkout/clean；新增合同先保持兼容读取，未通过迁移测试前不删除旧字段。
临时 bundle 和失败测试副本仅在摘要/哈希留档后精确清理；保留规范、fixture、回执、
当前与上一恢复点。
