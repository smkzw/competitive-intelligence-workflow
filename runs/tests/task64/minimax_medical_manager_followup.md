Narrowing to "治疗16周" gives a drawable COMPARABLE point. All good.

I have all the evidence I need. Returning the focused follow-up report inline.

---

# Task 6.4 定向修订复核：MiniMax 医学经理视角

## 结论：**P0 已清零；P1 残留 1 项**

Codex 对照 Cursor/Grok 阻断问题（产品级样本量串号、"有数但未选语境"被错写为"未报告"）做了精准修订。`pages.py` 中 `_lookup_sample_size` 不再把 N 借给其它试验臂；`_select_safety_context` 显式分两类返回 `selection_required_reason_zh`（多语境 vs维度已存在但筛选不命中）；`from_facts` 默认 `safety_family=TEAE` 且只在唯一 overall-TEAE 时才锚定 term_id。两项目标测试 26/26 全过（19 旧 + 7 新），6 项定向反例 14 个断言全部通过。

仅剩 1 项 P1：`comparison_row_id` 行材质（pages.py:1354-1363）未包含 `effect_measure`，导致 RD vs OR 被分成两行后产生相同 `comparison_row_id`（`BubbleMatrixView` 拒绝），且凭同一 row_id 后续视图同步会出现混淆。

## 实际检查

- 只读范围：`pages.py`、`test_bubble_area.py`、`test_matrix_states.py`、两份已存审评文件。
- `pytest tests/reports/b/test_bubble_area.py tests/reports/b/test_matrix_states.py -v` → **26 passed**，含7 项新增：`test_broad_sample_size_keys_cannot_lend_n_to_a_trial_arm[product-a/NCT00000001/arm-treatment/(product-a, NCT00000001)]`、`test_scoped_nested_sample_size_must_name_the_treatment_arm`、`test_multiple_safety_contexts_require_selection_instead_of_claiming_unreported`、`test_existing_safety_dimension_with_unmatched_filter_is_not_called_unreported`。
- 运行 `runs/tests/task64/_followup_probes.py`（不写盘）6 组共 17 个断言，全部通过；唯一标记 `[GAP]`的是 effect_measure 桶行 ID 冲突。

## P0 阻断问题逐一清零状态

| P0 阻断问题 | 状态 | 证据 |
|---|---|---|
| #1 产品/试验/臂级样本量串号到具体试验臂 | ✅ 清零 | `_lookup_sample_size`（pages.py:1419-1468）显式只接受 `(product_id, trial_id, arm_id)` 三元键或 `fact_row_id`；扫到的 broad_key（product/trial/arm单独键与二元键）一律返回 None。新增4 项参数化测试 + 我的 `_broad_key_no_lend()` 探针全部通过 |
| #2 多个安全性时间窗被错写成"未报告" | ✅ 清零 | `_select_safety_context`（pages.py:1527-1542）多语境直接返回 `(None, None, "存在多个安全性统计口径，请先选择事件、时间窗、分析人群和分母口径")`；`_derive_row_status`（pages.py:1253）把它映射成 `PENDING_VERIFICATION`；`_status_reason`（pages.py:1290-1291）把这条 reason透传到 UI 而非 "未报告"。新增 `test_multiple_safety_contexts_require_selection_instead_of_claiming_unreported` + 我的 `_multi_safety_window()` 探针全部通过 |
| #3 已有安全性维度但筛选不命中被错写"未报告"且文案像 TEAE | ✅ 清零 | `_select_safety_context`（pages.py:1507-1513）区分 `base_candidates` 与 `candidates`；`base_candidates` 非空但 `candidates` 为空时返回 `(None, None, "已有该安全性维度数据，但当前事件、时间窗、分析人群或分母口径未匹配，请调整筛选条件")`。新增 `test_existing_safety_dimension_with_unmatched_filter_is_not_called_unreported` + 我的 `_existing_dim_unmatched_filter()` 探针全部通过 |

## 定向反例 6 组（共 17 断言）

| # | 反例目的 | 结果 |
|---|---|---|
| 1 | 4 种 broad_key（`"p"`、`"T1"`、`"arm-treatment"`、`("p","T1")`）均不得借 N 给具体试验臂 | 4/4 OK |
| 2 | 三元键 `("p","T1","arm-treatment")` 仍可正常驱动气泡（COMPARABLE，N=120） | OK |
| 3 | 试验内嵌组别键 `{("p","T1"): {"arm-treatment": 123}}` 仍生效 | OK |
| 4 | 试验内嵌错误臂名 `{("p","T1"): {"arm-treatmentXXX": 999}}`拒绝借 N | OK |
| 5 | 多安全性时间窗未选 → `PENDING_VERIFICATION` + 中文"存在多个安全性统计口径，请先选择事件、时间窗、分析人群和分母口径"，不出现"未报告" | OK |
| 6 | 显式 `safety_time_window_zh="治疗16周"` 命中其中一组 → `COMPARABLE` 且 `points=1` | OK |
| 7 | 数据仅含"整个研究期"但筛选"治疗16周" → `PENDING_VERIFICATION`，reason="已有该安全性维度数据…未匹配…" | OK |
| 8 | 同上，文案绝不出现"未报告" | OK |
| 9 | 数据仅含 SAE 时，默认 `safety_family=TEAE`（不悄悄退到 SAE） | OK |
| 10 | 同上，默认 `safety_term_id=None`（不暗中锚到 SAE） | OK |
| 11 | 同上，默认 `safety_time_window_zh=None`（不按文本排序落到"整个研究期"） | OK |
| 12 | T 用 RD、C 用 OR → 拆为2 行，每行只有一臂，`efficacy_signal=None`，原值保留 | OK |
| 13 | 跨 effect_measure 的 efficacy_signal 永远 None | OK |
| 14 | 原始 T/C 数值在拆分后仍分别在各自行 | OK |
| 15 | 拆出的两行 `comparison_row_id` 实际为相同字符串（冲突 GAP） | 见 P1 |
| 16 | 目标测试 19 项旧 + 7 项新 = 26 全过 | OK |
| 17 | `test_bubble_area.py` + `test_matrix_states.py` 整体运行0.28s 内通过 | OK |

##残留 P1（须6.5 前修复）

**`comparison_row_id` 行材质未含 `effect_measure`，跨 effect_measure 拆行时产生重复 row_id。**

`pages.py:1354-1363` 的 `row_material` 当前为 `[product, trial, endpoint, compat, timepoint, time_unit, population, analysis_form]`。但 `_efficacy_group_key`（pages.py:205-217）含 `effect_measure`。两个事实 `risk_difference`（T）和 `odds_ratio`（C）在 build 路径里被分成2 行，2行的 `stable_id("matrix-comparison", ...)` 哈希输入相同，因此 `comparison_row_id` 相同。

后果：
- `_assemble_matrix_view_state` 与 `BubbleMatrixView.model_validator(mode="after")` 都会因"行标识不得重复"而拒绝；`build_bubble_matrix` 抛 ValidationError。
- 即便后续放宽 row_id 唯一性校验，证据链接、提示、表单元都与单一 `comparison_row_id` 关联，跨 effect_measure 的两行若共享 row_id 会让6.5 渲染层无法区分。

修复方式（最小改动）— 把 `effect_measure` 加入 `row_material`：

```python
row_material = [
    anchor.product_id, anchor.trial_id,
    anchor.endpoint_family_id, "::".join(anchor.compatibility_key),
    _scalar_key(anchor.actual_timepoint), anchor.actual_timepoint_unit,
    anchor.analysis_population or "",
    anchor.analysis_form,
    anchor.effect_measure or "",
]
```

或在 `_row_from_group` 取 T、C `effect_measure` 的有序 tuple 作为附加锚。

## 视觉验收清单（须留到真实页面）

本步仍未做 HTML/PDF/PPT渲染与浏览器验收。下列视觉项合同已具备语义数据，但须在 6.5 渲染闭环内独立确认：

- 轴标签中文渲染（"方向校正的试验内治疗—对照疗效信号" / "治疗组原始治疗期间不良事件发生率（倒序）"），OCR 是否完整可读。
- 倒序纵轴"向上 = 发生率更低 = 观察到的安全性位置更有利"在真实 SVG 上的方向与视觉间距。
- `r = k·sqrt(N/π)` 的圆面积随 N 真实缩放；N=100 vs N=400 在视觉上是否4 倍可辨；N极大（如 ≥10000）时是否需要 UI 层 `k` 自适应。
- PENDING 单元格中文原因"存在多个安全性统计口径，请先选择…"与"已有该安全性维度数据，但…未匹配…"在完整表/提示气泡中的字数截断、标点统一。
- 多产品跨多个试验的彩色矩阵单元中"非默认 safety维度"的视觉辨识（默认仍 `TEAE`，但 UX 是否能立刻看出切换）。
- `selection` 默认锚（仅当唯一 overall-TEAE 时锚 term_id）时，URL `event=teae-any` 是否回填且与中文标签"任何治疗期间不良事件"一致。

## 尚未验证

- 试验内嵌 `{("p","T1"): {...}}` 当 `safety_treatment.denominator` 显式存在时，是否会被 `_lookup_sample_size` 错误覆盖（当前 lookup 优先走 mapping，与 denominator 回退互斥；具体未独立探针覆盖）。
- 同一矩阵多产品 × 多试验 × 多 endpoint × 多 effect_measure 的组合爆炸下，矩阵视图的 `comparison_row_ids` 与 `url_state` 一致性在大规模下的性能与稳定性（仅在1–2 产品单试验层面通过）。
- `safety_event_definition_zh`、`safety_analysis_population_zh`、`safety_denominator_semantics_zh` 三个二级筛选维度的多语境冲突尚未单独跑探针（与 `safety_time_window_zh` 同源，预计逻辑一致）。
- 6.5 真实页面布局：横轴/纵轴字号、提示气泡遮挡、表头折叠、`target_id_by_product` 在多产品矩阵上的排序。
