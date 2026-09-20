# Task 6.6 验收结论

## 结论

通过。独立复核发现的正式测试阻断、跨概念差异标签污染、状态重校验、浅层可变索引和内部英文标签泄漏均已由 Codex 修复并加入回归测试。明确来源分箱维持兼容键拆分，不做重分箱；正式网址状态使用重复查询参数。

## 已验证

- BaselineObservation 合同与 Gate 回归：19 passed。
- Task 6.1–6.5 选定 B 回归：97 passed；A 报告：144 passed；单位报告/Gate：438 passed；合同与来源/报告集成：202 passed。
- `ruff check src tests`：通过。
- `mypy --strict src/ci_workflow`：100 个源文件无问题。
- 目标视图除阻断夹具外：16 passed；内存中使用合并 override 的修正版等价夹具执行严重程度拆分和默认顺序：两项通过。
- 本任务没有物理 HTML/PDF/PPT，未作视觉验收声明。

## 已关闭的对抗性发现

以下为 worker_03 首轮发现，均已按本文件结论所述关闭：

1. `tests/reports/b/test_baseline_views.py:210-228` 的 `_severity()` 通过显式关键字和 `**overrides` 重复传入 `theoretical_range`（同时潜在重复 `source_name`、`source_definition`），导致正式目标 1 failed、16 passed。应先合并默认 payload 与 override 再调用 `_observation()`。
2. 同两份目标测试在 strict mypy 下有 18 项夹具错误：`dict[str, object]` 的 `**overrides` 展开、`None` 传入 `_proportion` 的 `int` 参数、对可空 `reason_zh` 做成员测试。需在目标测试正式重跑前收紧夹具类型。
3. `_auto_difference_labels()` 接收完整事实集，未限制同一 `standardized_concept`；不同严重程度概念会产生错误的量表/理论范围差异标签。
4. `BaselineViewState.assert_synchronized()` 是无操作返回；视图状态通过 `model_copy(update=...)` 注入变更后的事实后，公开重建路径未重新校验当前 facts，存在绕过已验收 `BaselineObservation` 单一事实源的风险。普通 dict 字段还可被原地修改而不触发冻结或断言。
5. 未知规范概念可将 `pending_status` 等内部/工程化词原样暴露为变量标题和筛选标签，不符合中文临床试验用户文案约束。
6. 显式来源年龄分箱当前按完整兼容键逐箱生成独立比例柱状面板；是否符合分类变量分组柱状图需 Codex/设计确认，不能在视图层自动重分箱。
7. 标准 URL 重复参数可往返；`to_url_params()` 的逗号兼容表示经 `selection_from_url()` 不会拆分，需明确兼容边界或补充解析规则。

请修正目标夹具/类型问题后重跑完整目标；并在最终验收前处理或明确接受上述 3–7 项语义/边界问题。
