# W05A 混合测试批失败分诊

## 结论

- 本报告只分析已经运行的 `486 passed / 49 failed` 混合批；未重跑测试，也未用后续运行结果覆盖该批的原始结论。
- 该批不能被解释为 W05A 整体失败：49 项失败中，3 项属于冻结内容或资产摘要失配，5 项属于真实验收环境/当前运行绑定前置条件失败，18 项集中在共享 evidence drawer / chart-table-sync 基线，21 项属于 A 科学展示或旧验收契约与当前实现的差异，2 项与 W05A 本轮改动存在直接或高度可能的因果关系。
- 在该批本身能够支持的归因范围内：
  - **明确的 W05A 实际回归：1 项**——产品详情链接把返回状态直接写入 `href`，破坏了既有精确链接契约。
  - **高度可能的 W05A 实际回归：1 项**——1024 px 下安全性详情表新增折叠容器后的单元格宽度/行高不满足原验收阈值。
  - **可能受 W05A 共享样式改动影响但无法由本批证明：6 项**——图形点击、焦点返回与表格行高亮失败；同组同时存在大量与 W05A 无关的共享基线失败，因此不能据此直接归因。
  - 其余 A 图形/字段可达性失败是 W05A 验收相关风险，但从该批证据无法证明由 W05A 改动引入，不能标为“实际回归”。
- 请求的运行时身份为 `gpt-5.6-sol:medium`；本次没有可核验运行时身份回执，记为 **UNVERIFIED**。

## 原始 pytest 命令与结果

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/reports/a tests/acceptance/test_report_a.py tests/acceptance/test_report_a_real.py tests/browser/test_a_w05a_product.py tests/browser/test_filter_state.py tests/browser/test_a_complete_observations.py tests/browser/test_a_portal.py tests/browser/test_evidence_drawer.py tests/browser/test_chart_table_sync.py tests/browser/test_a_public_source_drawer.py tests/unit/test_a_observation_numeric_contract.py tests/unit/test_report_a_safety_projection.py tests/contract/test_w03_production_consumer_closure.py tests/contract/test_page_catalogs.py tests/integration/reports/test_a_report_portal.py tests/integration/test_w04_user_fact_edit.py tests/integration/test_a_public_provenance.py tests/integration/test_report_a_render_transaction.py -q --tb=short
```

原始结果：

```text
49 failed, 486 passed in 956.36s (0:15:56)
```

## 49 个失败测试 nodeid 完整清单

1. `tests/acceptance/test_report_a.py::test_fresh_ad_content_is_frozen_complete_and_native_chinese`
2. `tests/acceptance/test_report_a.py::test_default_efficacy_view_is_truthful_compact_and_resettable`
3. `tests/acceptance/test_report_a.py::test_safety_heatmaps_transpose_products_to_rows_and_fit_at_1280`
4. `tests/acceptance/test_report_a.py::test_matrix_labels_bubbles_with_product_names_and_keeps_product_legend`
5. `tests/acceptance/test_report_a_real.py::test_real_a_acceptance_binds_current_run_snapshot_manifest_artifact_and_browser_verdicts`
6. `tests/acceptance/test_report_a_real.py::test_real_acceptance_fails_closed_on_stale_artifact_mtime`
7. `tests/acceptance/test_report_a_real.py::test_real_acceptance_fails_closed_on_cross_run_manifest`
8. `tests/acceptance/test_report_a_real.py::test_real_acceptance_fails_closed_on_broken_local_link`
9. `tests/acceptance/test_report_a_real.py::test_real_acceptance_fails_closed_on_incomplete_browser_verdict`
10. `tests/browser/test_a_complete_observations.py::test_matrix_bubbles_do_not_move_data_coordinates_to_avoid_collisions[1440-chromium]`
11. `tests/browser/test_a_complete_observations.py::test_matrix_bubbles_do_not_move_data_coordinates_to_avoid_collisions[1440-webkit]`
12. `tests/browser/test_a_complete_observations.py::test_matrix_bubbles_do_not_move_data_coordinates_to_avoid_collisions[768-chromium]`
13. `tests/browser/test_a_complete_observations.py::test_matrix_bubbles_do_not_move_data_coordinates_to_avoid_collisions[768-webkit]`
14. `tests/browser/test_a_complete_observations.py::test_matrix_bubbles_do_not_move_data_coordinates_to_avoid_collisions[390-chromium]`
15. `tests/browser/test_a_complete_observations.py::test_matrix_bubbles_do_not_move_data_coordinates_to_avoid_collisions[390-webkit]`
16. `tests/browser/test_a_complete_observations.py::test_matrix_bubbles_do_not_move_data_coordinates_to_avoid_collisions[320-chromium]`
17. `tests/browser/test_a_complete_observations.py::test_matrix_bubbles_do_not_move_data_coordinates_to_avoid_collisions[320-webkit]`
18. `tests/browser/test_a_complete_observations.py::test_all_efficacy_observations_survive_chart_and_table[1440-chromium]`
19. `tests/browser/test_a_complete_observations.py::test_all_efficacy_observations_survive_chart_and_table[1440-webkit]`
20. `tests/browser/test_a_complete_observations.py::test_all_efficacy_observations_survive_chart_and_table[768-chromium]`
21. `tests/browser/test_a_complete_observations.py::test_all_efficacy_observations_survive_chart_and_table[768-webkit]`
22. `tests/browser/test_a_complete_observations.py::test_all_efficacy_observations_survive_chart_and_table[390-chromium]`
23. `tests/browser/test_a_complete_observations.py::test_all_efficacy_observations_survive_chart_and_table[390-webkit]`
24. `tests/browser/test_a_complete_observations.py::test_all_efficacy_observations_survive_chart_and_table[320-chromium]`
25. `tests/browser/test_a_complete_observations.py::test_all_efficacy_observations_survive_chart_and_table[320-webkit]`
26. `tests/browser/test_a_portal.py::test_a_home_efficacy_preserves_all_endpoints_and_timepoints`
27. `tests/browser/test_a_portal.py::test_a_matrix_bubble_and_legend_open_accessible_product_insight_drawer`
28. `tests/browser/test_a_portal.py::test_a_safety_heatmap_uses_distinct_continuous_colors_within_each_event`
29. `tests/browser/test_a_portal.py::test_a_safety_details_are_paginated_and_fit_at_1024`
30. `tests/browser/test_evidence_drawer.py::test_packaged_drawer_assets_mirrored_and_manifested`
31. `tests/browser/test_evidence_drawer.py::test_general_view_renders_all_fields_no_blanks[chromium]`
32. `tests/browser/test_evidence_drawer.py::test_general_view_renders_all_fields_no_blanks[webkit]`
33. `tests/browser/test_evidence_drawer.py::test_field_states_semantic_chinese_and_zero_not_missing[chromium]`
34. `tests/browser/test_evidence_drawer.py::test_field_states_semantic_chinese_and_zero_not_missing[webkit]`
35. `tests/browser/test_evidence_drawer.py::test_baseline_extension_fields_complete[chromium]`
36. `tests/browser/test_evidence_drawer.py::test_baseline_extension_fields_complete[webkit]`
37. `tests/browser/test_evidence_drawer.py::test_baseline_severity_evidence_never_inherits_age_metadata[chromium]`
38. `tests/browser/test_evidence_drawer.py::test_baseline_severity_evidence_never_inherits_age_metadata[webkit]`
39. `tests/browser/test_evidence_drawer.py::test_pointer_bar_opens_same_row_evidence[chromium]`
40. `tests/browser/test_evidence_drawer.py::test_pointer_bar_opens_same_row_evidence[webkit]`
41. `tests/browser/test_evidence_drawer.py::test_pointer_bar_escape_returns_focus_to_exact_svg_mark[chromium]`
42. `tests/browser/test_evidence_drawer.py::test_pointer_bar_escape_returns_focus_to_exact_svg_mark[webkit]`
43. `tests/browser/test_evidence_drawer.py::test_matrix_tables_preserve_heatmap_values_and_status_semantics[chromium]`
44. `tests/browser/test_evidence_drawer.py::test_matrix_tables_preserve_heatmap_values_and_status_semantics[webkit]`
45. `tests/browser/test_evidence_drawer.py::test_product_filter_keeps_compatible_charts_for_selected_product[chromium]`
46. `tests/browser/test_evidence_drawer.py::test_product_filter_keeps_compatible_charts_for_selected_product[webkit]`
47. `tests/browser/test_chart_table_sync.py::test_pointer_click_highlights_table_row[chromium]`
48. `tests/browser/test_chart_table_sync.py::test_pointer_click_highlights_table_row[webkit]`
49. `tests/contract/test_w03_production_consumer_closure.py::test_w03_browser_freeze_rebinds_report_data_sources_and_screenshots`

## 根因分组

| 组别 | 数量 | nodeid 编号 | 混合批中的直接信号 | 对 W05A 的判断 |
|---|---:|---|---|---|
| A. 冻结内容/资产摘要失配 | 3 | 1、30、49 | 内容或静态资产实际摘要与冻结期望值不一致 | 不是功能回归的直接证据；49 是 W05A 修改共享资产后预期会触发的冻结证据失效，需后续正式重绑，但不能修改测试掩盖差异 |
| B. 真实验收环境与当前运行绑定前置条件失败 | 5 | 5–9 | 当前源码提交摘要未绑定；合成项目构建返回 `capability_blocked` 而非 `completed` | 环境/运行证据不可用，不是 W05A 产品回归；相关真实验收仍未完成 |
| C. A 科学展示/旧验收契约与当前实现差异 | 21 | 2–4、10–28（不含 27） | 默认筛选未按旧期望选中；安全性结构不再是旧 heatmap；矩阵坐标采用数据域；部分疗效观测未进入图；首页分页未把全部行同时置于 DOM；颜色或气泡数量不符 | 属于 W05A 验收相关风险，但本批无法证明由 W05A 改动引入；应区分“既有实现/测试契约漂移”和“合同仍未满足” |
| D. W05A 直接或高度可能回归 | 2 | 27、29 | 详情链接 `href` 被追加返回状态；1024 px 安全性详情表尺寸越过阈值 | 27 为明确回归；29 为高度可能回归 |
| E. 共享 evidence drawer / chart-table-sync 基线失配 | 18 | 31–48 | 缺少“量表”“兼容规则”等字段；原值文本变化；抽屉未打开；矩阵表值为空；筛选后行为空；点击未高亮 | 整组包含多类与 W05A 无关的语义/fixture/共享渲染失配；不能整体归因于 W05A。仅其中 39–42、47–48 存在受共享 CSS 影响的低置信可能性 |
| **合计** | **49** | 1–49 |  |  |

### A. 冻结内容/资产摘要失配（3）

- **#1**：冻结内容摘要期望 `3c4223…`，实际为 `42c996…`。这是内容冻结基线与当前输入不一致，不证明门户交互或响应式实现回归。
- **#30**：`evidence-drawer.js` 的清单摘要与实际打包资产不一致。失败发生在资产镜像/冻结契约层，不等同于浏览器功能失败。
- **#49**：W03 浏览器冻结绑定期望摘要 `b1c1…`，实际为 `369028…`。W05A 修改作者源共享资产后，冻结摘要失效是可预期结果；必须通过后续正式重绑和复核关闭，不能把它计作已通过，也不能据此断言产品功能回归。

### B. 真实验收环境与当前运行绑定前置条件失败（5）

- **#5**：真实 A 验收报告未绑定当前源码提交摘要。
- **#6–#9**：用于验证过期工件、跨运行清单、断链和浏览器 verdict 完整性的合成项目构建均返回 `capability_blocked`，测试预期为 `completed`。
- 这些失败说明真实验收链在该批中不可判定；它们没有进入对 W05A 页面行为的有效断言阶段。因此应记作 **UNVERIFIED / capability-blocked**，而不是产品回归。

### C. A 科学展示或验收契约差异（21）

- **#2**：旧测试要求默认选中 EASI-75 与第 16 周，实际无对应 pressed 状态。W05A 本轮重点不是改写默认筛选，混合批不足以证明这是新引入回归。
- **#3**：旧测试寻找 `.kz-a-heatmap`，实际数量为 0；当前安全性呈现已转为 observation/card 结构。属于结构契约差异，同时也提示旧测试与当前产品形态尚未统一。
- **#4**：SAE 矩阵只得到 1 个气泡，测试要求至少 2 个。它可能是数据覆盖、投影资格或筛选结果问题，但批内没有变更前对照，不能归因于 W05A。
- **#10–#17**：8 个浏览器/viewport 组合中，气泡横坐标约为 `78.427`，旧测试按固定 0–100 域期望约 `63.248`。当前实现使用数据驱动横轴域；这是图形契约差异，不是碰撞避让导致的数据坐标移动证据。
- **#18–#25**：8 个浏览器/viewport 组合中，合成的 `-4分` 疗效观测没有进入图，而图中保留了百分比终点。可能涉及 W03 typed numeric 投影资格、测试修改 fixture 后未同步投影，或当前图形对指标类型的选择；是“完整观测可达”验收风险，但不是由该批证明的 W05A 新回归。
- **#26**：首页疗效图 DOM 未同时包含测试要求的全部 endpoint/timepoint 行。当前分页/分段呈现可能使部分事实不在首屏 DOM；该问题与 W05A 完整宇宙及结果可达合同相关，但 W05A 没有在本轮引入该分页逻辑，故列为未关闭验收差距而非实际回归。
- **#28**：安全性观察单元没有返回测试要求的 4 个不同连续背景色。属于当前安全性视觉编码与旧 heatmap 契约差异，无法从本批归因给 W05A。

### D. W05A 直接或高度可能回归（2）

#### #27：明确的 W05A 实际回归

测试要求产品详情链接保留稳定的原始 `href`：

```text
products/fixture-product.html
```

该批实际得到：

```text
products/fixture-product.html?return=...focus...
```

W05A 为三层下钻/返回状态把返回参数直接追加到链接属性，改变了既有精确链接契约。失败与本轮改动具有直接因果链，因此在该混合批时点应标为 **实际回归**。本报告不引用后续修改或重跑来改写该批结论。

#### #29：高度可能的 W05A 实际回归

1024 px 下安全性详情表的关键尺寸至少有一项越界：单元格宽度约 `94.80 px`，低于测试阈值 `100 px`；同次观测中的行高约 `236.53 px`，也显示内容拥挤。W05A 对安全性详情增加了分页/折叠结构并调整响应式布局，失败断言直接落在改动区域，因此归为 **高度可能回归**。但单次混合批没有变更前浏览器几何基线，故不提升为确定因果。

### E. 共享 evidence drawer / chart-table-sync 基线失配（18）

- **#31–#36**：通用抽屉 fixture 缺少“量表”或“兼容规则”，其中一项 Chromium 路径还表现为抽屉未出现。
- **#37–#38**：测试期望来源原值 `EASI total score`，实际为 `EASI total score（登记原文，未译）`。这是 fixture/语义文本基线差异，不是 W05A 的“None 空值临床化表达”改动证据。
- **#39–#42**：柱图点击后抽屉未打开，Escape 也无法返回精确 SVG mark。
- **#43–#44**：矩阵折叠表没有返回预期的 `-12.1`、`-9.4` 值。
- **#45–#46**：产品筛选后兼容图形行为空。
- **#47–#48**：pointer 点击后没有选中预期表格行 `row-ctrl-endpoint-a`。

上述失败跨越语义字段、fixture 原值、抽屉可见性、矩阵值、筛选与指针同步，呈现为共享测试基线或共享渲染协议整体失配，而不是单一 W05A 页面缺陷。W05A 确实改动了共享 `portal.css`，因此 **#39–#42、#47–#48** 的命中区域可能受几何/点击样式影响；但同批没有显示 CSS 命中、事件目标或变更前对照，且同文件存在明显无关的字段基线失败，故只能标为 **低置信可能相关，未证明**。

## 哪些失败可能是 W05A 实际回归

| 级别 | nodeid | 判定依据 | 本批结论 |
|---|---|---|---|
| 明确 | `test_a_matrix_bubble_and_legend_open_accessible_product_insight_drawer` | W05A 直接改变链接 `href`，失败值正是新增返回参数 | 实际回归 |
| 高度可能 | `test_a_safety_details_are_paginated_and_fit_at_1024` | 失败断言位于 W05A 新增/调整的折叠与响应式详情表区域 | 高度可能回归，需后续独立浏览器复核 |
| 低置信可能 | `test_pointer_bar_opens_same_row_evidence` 两个浏览器参数、`test_pointer_bar_escape_returns_focus_to_exact_svg_mark` 两个浏览器参数、`test_pointer_click_highlights_table_row` 两个浏览器参数 | W05A 修改共享 CSS，理论上可能影响命中几何；但本批没有直接因果证据，且共享测试基线已广泛失配 | 不得记为已证实回归 |
| 验收相关但非已证实回归 | #2–#4、#10–#26、#28 | 涉及完整观测、图表/表格、矩阵、安全性编码和默认筛选；与 W05A 合同有关，但缺少变更前对照或明确改动链 | 保留为 W05A 验收风险，不作回归归因 |
| 非产品回归 | #1、#5–#9、#30、#49 | 摘要、当前运行绑定或 capability 前置条件失败 | 需要重绑/恢复验收能力，不代表页面功能退化 |

## 证据边界

- 本报告没有重跑任何测试，因此不声明上述失败在当前工作树仍然存在或已经消失。
- 本报告只依据该次混合批的原始命令、失败摘要、断言实得值及当时变更范围做归因；没有把后续测试、后续修复或人工浏览器观察倒灌进本批结论。
- `486 passed` 证明同批中的相应测试通过，但不能抵消 49 项失败，也不能替代 W05A 独立视觉/产品复审。
- 该批未覆盖或未关闭全 gate、24 门户、B/C、三宿主与 RC；不得据此宣布 W05A 最终 PASS。
- 运行时模型/effort 身份：**UNVERIFIED**（请求值 `gpt-5.6-sol:medium`，无可核验运行时身份回执）。
