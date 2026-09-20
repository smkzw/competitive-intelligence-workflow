# Task 9.3 独立复审补充证据

请在同一会话中重新读取当前工作树，不沿用上一轮行号或结论。重点核验：

1. `application/monitoring_service.py::apply_disposition` 已在交接单存在时只允许精确重放，其他新处置先于事件追加失败；反例为 `test_disposition_cannot_change_after_refresh_handoff`。
2. `domain/monitoring.py::verify_candidate_dedupe_identity` 先重算摘要和 ID，再从当前序列化内容重新构造完整候选合同；`_reduce_candidate` 将失败转为 `MonitoringConflictError`。跨候选交接反例为 `test_reducer_rejects_handoff_bound_to_another_candidate`。
3. 领域模型的用户可见说明已直接要求中文；恢复方法禁止重复。反例在 `test_domain_contract_rejects_ascii_user_visible_prose`。
4. `_suggested_review_scope_zh` 不再拼接页面机器标识；集成测试断言 `a-efficacy-matrix` 不出现在交接说明。
5. `MonitoringSourceIdentity`、Task 9.3 设计和内部 Skill 已明确 `source_version_id` 是不可变来源内容版本，相同内容跨次获取复用，禁止抓取日期/运行编号/临时快照名。
6. `submit_observation` 在任何事件或投影写入前核对当前项目身份；反例 `test_submission_rejects_foreign_project_without_writing` 验证事件流和收件箱字节/目录均不变。
7. 已有交接单重放会恢复丢失的 handoff 文件并重建候选投影。

## 最后一项 P2 修复

你上一轮指出的观察输入中文与去重缺口已修复：

- `MonitoringObservation` 现在直接校验 `discovery_note_zh`、`next_step_zh` 必须包含中文；
- `methods_tried_zh` 的每一项必须包含中文，且规范化后不得重复；
- 反例 `test_observation_rejects_ascii_or_duplicate_recovery_text` 覆盖英文方法、英文下一步和重复方法；
- 测试中的来源版本示例已改为不可变内容版本，不再使用日期快照名；根目录与包内 Schema 均补充相同语义说明。

当前验证：Task 9.3 聚焦 66 项通过；全量集成 320 项通过；目标 Ruff、三个实现模块 mypy、包完整性均通过。请只报告当前工作树仍可复现的 P0/P1/P2 功能缺陷；若最后一项 P2 已关闭，请明确给出“无剩余 P0/P1/P2”的结论。P3 异常类型一致性仅在能证明会造成用户可见功能错误或状态损坏时升级，否则作为非阻断建议保留。

当前验证：Task 9.3 聚焦 63 项通过，目标 Ruff 通过，三个实现模块 mypy 通过。请只报告当前工作树仍可复现的 P0/P1/P2 功能缺陷；若上述旧问题已关闭，请明确写“已关闭”，不要复述旧版代码。
