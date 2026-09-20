# Checkpoint — R2.4 P1 全链审计完成

## 已确认基础

- A/B/C GateSpec 已按对象矩阵求值，关键单元拒绝缺失/未决冲突；`reported_zero`、
  `not_applicable`、来源角色、披露成熟度、上下文和覆盖 override 已有较强失败关闭。
- 双重穷尽已绑定路线、回执、实体、终端结果与 producer/reviewer 分离；canonical
  blocker publisher 具备模型重验证、原子写入、幂等、漂移拒绝、用户 Markdown 清洁和
  数据库/报告目录 no-draft 断言。

## 需修复问题

1. 恢复轮次只比较策略标签；相同 query/identifier 与 access method 可伪装新策略。
2. 科学信息增益只比较有/无布尔值，技术缺口可携带未绑定的自由增益摘要。
3. `MATERIAL_OMISSION_FOUND` 可进入 gap/exhausted 模型；遗漏复核未绑定独立上下文。
4. GateSpec 尚无规范要求的新鲜度、失败代码与恢复路线字段；C 类关键单元默认事实域过宽；
   对一个关键单元存在未决冲突时，另一条已解决事实仍可能使报告通过。
5. 产品存在两个轻量阻断旁路：Publication 不足与旧 B baseline gate 写入同名
   `blockers/*/audit.json`，但不符合 canonical BlockerAudit schema；科学 QC exhausted
   路径也可能只进入状态而不发布完整阻断包。
6. no-draft 仅检查报告版本目录和数据库表，尚未覆盖已知 staging/derived 残留与阻断目录
   软链接；终态 resume 仅看两个文件存在，不重验证审计内容。

## 实施顺序

先以 RED 固化不需要新科学裁决的失败关闭：同查询/访问伪新策略、遗漏结论、技术伪增益、
阻断目录/文件篡改与旁路 schema。随后收束唯一 blocker 发布和产品 no-draft。新鲜度算法
涉及科学规则，待其他确定性修复完成后再以原生 Ask 提供有界选项，不擅自选择。

三名 worker 均在 `cursor/default` 一轮完成，无 fallback；其输出是审计输入，Codex 负责
当前字节复核、修订和最终验收。
