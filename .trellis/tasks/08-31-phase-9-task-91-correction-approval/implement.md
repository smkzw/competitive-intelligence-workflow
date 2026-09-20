# Task 9.1 实施步骤

- [x] RED：新增 `tests/integration/test_correction_flow.py`，覆盖所有合法迁移、验证不能批准、发布前置条件、追加历史和幂等重放。
- [x] 定义 `schemas/correction-proposal.schema.json` 及 `src/ci_workflow/schemas/` 同步副本，并加入包清单。
- [x] 实现 `src/ci_workflow/application/correction_service.py`，复用现有项目库、事件、摘要与幂等约定。
- [x] 实现 `src/ci_workflow/graph/definitions/correction.py`，复用既有迁移与守卫，不复制状态规则。
- [x] GREEN：运行 `uv run pytest tests/integration/test_correction_flow.py -q`。
- [x] 回归：运行修订状态、事件重放、SQLite 迁移、包清单相关测试。
- [x] 运行 mypy 与 Ruff 的目标范围检查。
- [x] 独立检查者审阅状态、真源与幂等边界；治理审计通过后更新检查点。

## 验收记录

- Task 9.1 合同、图、服务测试：31 passed。
- 共享图、检查点、迁移、追加式记录、包清单回归：16 passed。
- 目标 Ruff、mypy：通过；两份 Schema：逐字一致。
- 独立会商：同一 CodeBuddy session 两轮，修订后结论“可接受，无阻断问题”。
- Phase 9.4 边界：站点/宿主修订包生产者与报告负责人身份绑定；如扩 Schema，需显式升版。
- Phase 9.2 边界：扩展非 claim 目标枚举与重建回执持久化。

## 回滚点

任何发布前置条件或幂等测试失败时，停在本任务，不接入 CLI 或站点按钮；已保存建议和历史记录保留，不删除。
