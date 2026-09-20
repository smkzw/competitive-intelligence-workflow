# Checkpoint — R2.3 P1 现场审计与迁移边界

## 已确认

- `publication_gate.py` 和 `manual_inbox.py` 目前只在孤立测试中形成能力，严格
  `research submit` 与 `run_project` 尚未消费，不能视为产品门完成。
- ResearchPackage 现有 `publication_classification` 只是来源标签，缺少规则/模型/
  独立 verdict、登记强绑定和逐篇自动获取尝试；必需论文不可访问仍可通过提交。
- PubMed/B 类、ResearchSource 和 PublicationRecord 存在三套相邻词汇；正式 verdict
  将成为唯一权威，连接器角色只作为信号。
- `ManualSupplyGate` 负责每快照一次用户中断；`ManualInboxService` 负责逐文件操作；
  `run_service` 负责受影响报告暂停、恢复和多报告聚合。

## 独立审阅

三个只读 worker 已完成分类权威、产品插入点和负向矩阵审计；报告由治理 runner
保存。其结论仅作为实现输入，R2.3 尚未验收，治理任务暂不归档。

## 下一安全动作

P2 先用 RED 测试建立 publication verdict、fetch attempt、生产者/复核者隔离和精确
摘要合同，再接入 ResearchPackage/schema；随后 P3/P4 接产品 gate 与收件恢复。
