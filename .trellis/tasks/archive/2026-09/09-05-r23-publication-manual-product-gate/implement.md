# 实施计划 — R2.3 Publication 与人工补件产品门

- [x] P1 审计 publication/manual/download-request/research-package/run-service 的真实消费链
  与重复状态，形成最小迁移边界和负向矩阵。
- [x] P2 完成 publication verdict、自动获取尝试、必需缺失与独立复核的类型合同和 schema。
- [x] P3 将唯一 manual gate 接入严格提交和产品运行，按受影响报告暂停并持久化恢复状态。
- [x] P4 接入 ManualInboxService 的核验、原地重命名、重抽取与单次不可得分流。
- [x] P5 覆盖综述/ad hoc 排除、边界分歧、自审、网络/解析/权限失败、错文件、扫描 PDF、
  重名碰撞、登记号不一致、重复询问、多报告局部阻断和篡改恢复。
- [x] P6 运行聚焦、integration、全仓 gate、bundle/fresh-install，完成独立执行审阅、
  checkpoint、精确清理和任务归档。

## 回滚与卫生

不 reset/checkout/clean；先保留现有文件状态机，接线测试通过后再删除重复状态。
临时下载样本与 bundle 只在摘要/哈希落档后精确清理；用户补件 fixture、规范回执和
当前/上一恢复点保留。
