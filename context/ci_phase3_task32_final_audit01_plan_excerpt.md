# Task 3.2 批准计划验收摘录

来源：`/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`，只读摘录；原文优先。

## 文件范围

- `src/ci_workflow/gates/exhaustion.py`
- `src/ci_workflow/gates/blocker_audit.py`
- `schemas/blocker-audit.schema.json`
- `tests/integration/test_double_exhaustion.py`
- `tests/integration/test_no_draft_when_blocked.py`
- `tests/integration/test_no_draft_on_unresolved_key_conflict.py`
- `tests/integration/test_no_draft_after_scientific_qc_rejection.py`

## 验收要求

1. 检索执行者完成多路径恢复，独立遗漏检查者再审；两者职责分离。
2. 阻断包同时生成 `audit.json` 和简洁中文 `audit.md`，列出阻断对象、原因、已尝试路径和下一步。
3. 两层参数化测试：A 空宇宙、B 无达到最低结果门槛的适格试验、C 无达到设计核心门槛的适格试验；并从 A/B/C GateSpec 枚举每个适用阻断单元，用非空产品/试验候选构造只缺该单元的场景。不得只测空输入。
4. 每个场景均不得进入锁定快照；数据库不得出现报告快照、coverage/projection、格式作业/渲染队列、产物记录；正式、draft 或占位报告目录均不得存在。只允许 `blockers/<report>/<version>/{audit.json,audit.md}` 以及内部回执/日志。
5. A/B/C 各一例非空关键冲突，复用全部零数据库、零队列、零产物、零报告目录负断言。
6. GateSpec 已通过但独立科学质控否决的 A/B/C 三例：可修复回 `recovering`，已穷尽进 `evidence_blocked`，两者均无锁定快照、coverage、渲染作业和产物。
7. 精确测试为上述四个文件；通过集合应覆盖三个空场景、三份 GateSpec 的全部适用阻断单元、三个关键冲突及三个科学质控否决场景。

Phase 3 退出合同还要求 Task 3.1—3.7 的完整阶段命令全部通过；本次验收只裁定 Task 3.2，不提前声称 Phase 3 完成。
