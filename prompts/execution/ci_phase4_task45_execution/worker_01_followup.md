继续同一 Task 4.5 / worker_01 会话，只做一个已由 Codex 复核发现的合同补丁，不重做既有实现。

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read these files only initially: `context/ci_phase4_task45_execution_execution_context.md`, `src/ci_workflow/reports/common/evidence_view.py`, `tests/unit/reports/test_evidence_view.py`.
- 只修改下文明确列出的两个项目内文件；不读写生产路径，不安装依赖，不切换模型，不另开会话。
- Runner-managed output path: `runs/execution/ci_phase4_task45_execution/worker_01_followup.md`. Never write this report path through tools; return the report in the final response for the runner to persist.

Codex 已在本地主会场确认：当前 163 项 reports 测试、scoped Ruff、strict mypy 均通过。但 design §15.5 明确要求 baseline/disposition 同时展示“来源原名与定义”。当前 `EvidenceView` 只有 `source_field_definition`，把两个科学语义合并后会使跨试验核对无法区分“原始字段名称”与“来源给出的定义”。

请在原工作树中：

1. 先补一个精确失败测试，要求扩展观察必须分别携带 `source_field_name` 与 `source_field_definition`，通用观察仍不得携带扩展字段；两个字段均使用 `EvidenceField`，可用四种语义状态，但不得空白。
2. 将 `source_field_name` 加入 `EvidenceView` 与 `_EXTENSION_FIELDS`，保持既有 frozen/extra-forbid/页面 profile/披露合同不变。
3. 更新基线/完成情况 fixture helper 和断言，确保来源原名可与定义不同，且都被逐字段保留。
4. 运行 `tests/unit/reports/test_evidence_view.py`、`tests/unit/reports`、scoped Ruff 和 strict mypy。
5. 只修改 `evidence_view.py`、`test_evidence_view.py`；若无需导出新类型，不修改其他文件。返回简短补充报告，包含 RED/GREEN 和改动路径。

不要改 JS/CSS/浏览器测试，不切换模型，不另开会话。
