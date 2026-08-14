# Task 5.2 批准合同摘录

来源：`docs/specs/competitive-intelligence-workflow-design-v1.2.md` §12.1–12.3；实施计划 Task 5.2。该文件只为受限上下文注入节省 Token，不替代原文。

## 产品目标与证据边界

A 是目标适应症下全部创新治疗项目的完整开发档案，不是明星产品卡片、销售预测或市场模型。临床前项目不因没有试验失败，未合作项目不因没有交易失败；非阻断扩展字段缺失必须保留真实状态，任何正面陈述仍须有自身证据。

## 页面责任

- 竞争格局：全部项目的靶点、模态、阶段、地域、生命周期和开发状态；支持管线、时间线、矩阵和完整表。
- 产品总览：所有项目的可筛选事实表与比较视图，不以 Top-N 截断。
- 产品档案：每个产品独立详情，覆盖别名、机制、模态、分子/给药、组织关系、开发时间线、试验组合、关键结果与风险、监管、交易及专利。
- 临床开发组合：产品—试验—地区—阶段—状态及核心试验下钻。
- 中国与全球监管：申报、批准、审评、撤回、暂停/终止及差异化状态时间线。
- 企业与交易：原研、开发者、许可方/被许可方、合作、并购、地域权益和公开交易条款。
- 专利与保护：可核验专利族、范围、到期或独占；专利和监管独占分开。
- 历史与边缘观察：暂停、终止、撤回、放弃项目及邻近机制观察层。

## 精确验收节点

1. `test_landscape_contains_every_in_scope_product_and_grouping_dimension`
2. `test_product_overview_is_complete_filterable_and_not_top_n`
3. `test_every_product_has_complete_dossier_and_stable_route`
4. `test_clinical_portfolio_preserves_product_trial_region_phase_and_status`
5. `test_china_and_global_regulatory_events_are_separate_and_versioned`
6. `test_company_relationships_rights_and_transactions_are_not_conflated`
7. `test_patent_family_jurisdiction_expiry_and_exclusivity_are_separate`
8. `test_suspended_terminated_withdrawn_and_abandoned_programs_remain_visible`

所有视图只消费锁定快照，不创建模板或产物。整套验收命令：`uv run pytest tests/unit/reports/a -q`。
