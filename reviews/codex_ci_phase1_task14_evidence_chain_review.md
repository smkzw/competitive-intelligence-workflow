# Codex Review: ci_phase1_task14_evidence_chain

Date: 2026-08-11
Delegated-agent output: `runs/pi_ci_phase1_task14_evidence_chain.md`

## Verdict

PASS。Task 1.4 可以接受；事件、检查点、快照、检索连接器与报告渲染仍未接受。

## Boundary Check

- 原独立审查会话只读，退出码 0，未发生 fallback；runner 只生成声明的最终报告与原始运行记录。
- 会话使用当前有限代码首选路由 `Pi/cms-smk/deepseek-v4-flash:max`，没有因等待时间或日夜间策略重派。
- 产品变更仅覆盖内容寻址原文、来源版本、证据片段、审计合同、追加式 0007 迁移与相应测试；旧工程保持只读。
- 未新增安全测试，也未实现 Task 1.5+。

## Codex Verification

- 精确测试：`10 passed in 0.15s`。
- 全库回归：`118 passed in 5.38s`。
- Ruff：通过。
- strict mypy：15 个源文件无问题。
- 包校验：`PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4`。
- 直接调用系统 Python 会因缺少项目包与依赖产生 3 个 collection errors；改用仓库固定 `.venv/bin/*` 后全部通过。该偏差是执行环境选择错误，不是产品回归，也未通过全局安装掩盖。
- 独立审查指出 `error_class` 与 `parent_attempt_id` 虽为双合同必填，但原测试没有逐字段删除验证；Codex 已取消跳过并重跑全库，确认两个字段缺失时 JSON Schema 与 Pydantic 均失败关闭。

## Delegated-Agent Output Review

Hermes 独立审查覆盖了内容摘要去重与移动读回、四类来源日期分离、未公开状态、片段定位、空原文双层拒绝、0007 追加式迁移、不可变保护及来源回执/证据缺口双合同。结论与 Codex 复验一致：无 P0/P1，且未越权接受后续能力。

## Residual Risk

- 0002 `source_versions` 的旧日期文本列没有格式级 CHECK；当前权威类型化日期存于 0007 `source_date_assertions`，应用写入经过带时区的领域模型。Phase 1 退出时继续验证所有生产写入只走该服务，不把旧列当作独立真源。
- Task 1.5 必须把当前来源/证据身份绑定到事件、检查点、快照与产物清单，并补上 Task 1.3 遗留的孤儿项目记录探针。
