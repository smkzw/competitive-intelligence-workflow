按 Codex 指示核验最后一项 P2 修复。重新读取当前 `MonitoringObservation`、反例测试、测试夹具与 Schema 语义说明。

验证 `ValidationInfo` 导入与反例测试存在性。

反例覆盖三场景确认。核验夹具与 Schema 语义说明。

夹具已改为内容版本（`NCT048-results-content-v1`）。核对根目录与包内 Schema 的语义说明。

全部核验完成。最后一项 P2 修复在代码、反例、夹具与双份 Schema 中均已落实。写入计划文件并返回最终报告。

# Conference Participant Output: ci-phase9-task93-optional-monitoring-review - general_single_object（最后一项 P2 修复核验）

## 核验方式

- 同一会话，重新读取当前工作树（不沿用旧行号）：`monitoring_service.py:167-265`、`tests/integration/test_monitoring_service.py:565-588`、夹具 :91/:271、`tests/graph/test_monitoring_nodes.py:227`、根目录与包内两份 Schema。
- `Bash` 被拒绝：未运行测试；Codex 提供的 66 聚焦 / 320 全量集成 / Ruff / mypy / 包完整性执行证据未由我复跑。

## 最后一项 P2 修复核验：已关闭

1. `MonitoringObservation`（monitoring_service.py:205-213）`_visible_prose_is_chinese` 直接校验 `discovery_note_zh` 与 `next_step_zh`：`_require_prose_zh` 要求含汉字；`ValidationInfo` 已导入（:45）。
2. `methods_tried_zh`（:215-223）逐项 `_require_prose_zh`（含空白规范化）且规范化后去重：重复抛"已尝试方法不得重复"。
3. 反例 `test_observation_rejects_ascii_or_duplicate_recovery_text`（integration:565-588）以三个参数化用例覆盖：英文方法 `("automatic retry",)`、英文下一步 `"please login"`、重复方法 `("直接抓取","直接抓取")`，均断言构造抛 `ValidationError`。
4. 测试夹具 `source_version_id` 已改为不可变内容版本 `"NCT048-results-content-v1"`（integration:91）与 `"NCT048-results-content-v2"`（:271），不再使用日期快照名；Skill 语义由 test_monitoring_nodes.py:227 断言。
5. 根目录与包内两份 Schema 均在 `SourceIdentity`/`source_version_id` 补充相同语义说明（"不可变的来源内容版本…不得使用抓取日期、运行编号或临时快照标签"，两文件同在第 73/76 行）；双份一致性由 `test_packaged_copy_matches_directory_contract` 字节级锁定。

**结论：无剩余 P0/P1/P2。**

## P3（非阻断建议，不升级）

- 归约处合同违法事件（discovered/rediscovered/diagnostic/disposition 分支，monitoring_service.py:966/977/988/1007）仍抛裸 `pydantic.ValidationError`。核验其影响：失败关闭、零写入、不产生非法状态，不构成用户可见功能错误或状态损坏，故按 Codex 规则维持非阻断建议（可选统一包装为 `MonitoringConflictError`）。
- 附带同类边缘：Python `_CJK_RANGES` 含扩展 A（0x3400-0x4DBF）而 Schema `ProseZh` 仅 `[\u4e00-\u9fff]`；仅含扩展 A 字符的罕见文本可通过 Python 但被 Schema 拒。医学经理场景概率极低，同样非阻断。

## 证据与假设

- 全部引用为当前工作树只读核验；无旧结论沿用。
- 假设：EventStore 追加权威模型不变；宿主（Task 9.4）为可信调用方。
- 未验证：测试执行证据（需 Codex/fallback 确认）。

## 建议下一步

- Task 9.3 审查轴全部关闭；可收口（可选做 P3 异常包装与扩展 A 口径对齐）。
- 咨询性质；不主张最终验收。
