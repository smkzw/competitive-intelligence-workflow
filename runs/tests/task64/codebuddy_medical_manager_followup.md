I'll continue the review session. Let me read the files specified for this follow-up review.

Now let me read the current `pages.py` and the test files to check for the定向修订 (targeted revisions). I'll focus on the specific challenge areas: 样本量串借 (sample size cross-borrowing), 多安全性时间窗误报为未报告 (multiple safety time windows misreported as not reported), 总体 TEAE 静默回退 (overall TEAE silent fallback), 效应形式不一致仍相减 (inconsistent effect forms still subtracted).

Let me read the key sections of pages.py without full re-read — focusing on the relevant functions identified earlier.

Let me continue reading the `MatrixComparisonRow` and the key functions for the four challenge areas. I'll read from 420 to ~1350.

Let me read the remaining portion (1370–1500) covering `_row_from_group` finalization and `_select_safety_context` for the overall TEAE fallback and sample size handling.

I have enough detail now. Let me check the `build_bubble_matrix` and `build_matrix_comparison_rows` functions (the sample-size borrowing path) and the test files for the four targeted challenge areas. Let me read the relevant section 1560–1660 and then the test files.

Now let me read `build_bubble_matrix` (the actual bubble construction with sample size handling) around 1780–1980.

I now have full understanding of the four challenge areas. Let me check the test files for the four targeted challenges (样本量串借, 多时间窗误报, 总体TEAE回退, 效应形式不一致相减) to see what's covered. Let me grep the test files for relevant tests.

Now let me grep the matrix_states test for the four challenges and check whether there are new tests added for these specific challenges.

There's a test `test_multiple_safety_contexts_require_selection_instead_of_claiming_unreported` at line 281 — directly addressing the "多安全性时间窗误报为未报告" challenge. Let me read that test and surrounding tests (281–350) to confirm the coverage and exact semantics.

The four targeted challenges now have clear code + test coverage. Let me run the actual tests to verify they pass. I'll attempt via Bash; if denied, I'll annotate.

Let me try running the tests now.

Bash 权限仍被拒，无法实际运行 pytest。以下如实标注，并基于**逐行静态核验**完成定向审评。

---

# 第 6.4 步定向修订跟进审评 — CodeBuddy 医学经理视角

**审评性质**：只读、独立、反证式。未修改文件、未联网、未做安全测试。
**本轮范围**：`runs/tests/task64/codebuddy_medical_manager_review.md`（首轮报告）、`src/ci_workflow/reports/b/pages.py`（定向修订后的当前版本，已局部复核关键函数）、`tests/reports/b/{test_bubble_area,test_matrix_states}.py`。
**目标测试实际运行**：**未运行**。当前非交互会话的 Bash 权限被拒（`Permission to use Bash has been denied`）。本轮与首轮一致，改为对定向修订点逐行静态核验 + 反证推演。这是本轮**未验证项**："测试绿"未经执行确认，仅确认用例与实现逻辑自洽。

## 一、结论

针对首轮提出的 4 个定向挑战，本轮确认修订**已在数据合同层落到代码与测试**，且方向与医学经理安全阅读需求一致：

- **样本量串借** → 已被 `_lookup_sample_size` 显式拒绝（pages.py:1458-1465：显式 mapping 权威，宽泛 product/trial/arm 键不得外借）。
- **多安全性时间窗误报为未报告** → 已被 `_select_safety_context` + 新测试 `test_multiple_safety_contexts_require_selection…`(line 281) 与 `test_existing_safety_dimension_with_unmatched_filter…`(line 312) 覆盖：多口径→"待核实"而非"未报告"。
- **总体 TEAE 静默回退** → 已被 `_select_safety_context`(pages.py:1521-1526) 与"已有维度但口径未匹配→待核实"逻辑覆盖，不会静默落到某个非总体 TEAE。
- **效应形式不一致仍相减** → 已被 `_direction_corrected_signal`(pages.py:300-305) 与 `_row_integrity`(pages.py:582-590) double-guard：组键或方向不一致→`INCOMPATIBLE`，**不进入坐标、不相减**。

**首轮严重问题归类结论**：
- **S1（倒序轴误读）仍属"当前数据合同缺陷"** —— `BubblePoint` 数值字段仍不携带图位方向语义（pages.py:1022-1026 `safety_position` 仅返回原始 y，仅靠全局 `safety_axis_reversed=True` 布尔）。这是数据模型层缺陷，需在渲染前修复，非纯渲染问题。
- **G1（倒序警告兜底）、G2（待核实占位）属"后续渲染验收"** —— 数据层已正确产出 `PENDING_VERIFICATION` 状态与 `unplottable_rows` 原因（pages.py:1890-1898），但"是否以非坐标占位视觉呈现"取决于未实现的 HTML/PDF/PPT。
- **G3（状态别名混同）属"当前数据合同可收敛项"** —— 不影响正确性，仅维护期语义清晰风险。

## 二、证据（逐挑战绑定代码+测试）

### C1 样本量串借 — 已修复（数据合同层）
- 风险：A 试验/臂未知样本量被 B 试验/臂的宽泛键"借"成已知。
- 代码：`_lookup_sample_size`(pages.py:1419) 在显式 mapping 下只试精确键 `(product,trial,arm)` 与 `fact_row_id`，否则 `return None`(1465)；注释明确"宽泛 product/trial/arm 键不得外借"(1463-1464)。
- 测试：`test_unknown_treatment_sample_size_is_not_zero_and_does_not_create_a_point`(bubble_area:253) 与 `test_unknown_sample_size_is_pending_verification_not_zero`(matrix_states:235) 仍覆盖"None→待核实、无点"。
- 反证推演：构造 `{("product-a","NCT-X","arm-other"):150}` 给 `product-a/NCT1/arm-treatment`，因精确键不匹配且无嵌套匹配 → 返回 None → 该行 `PENDING_VERIFICATION`，**不串借**。成立，未推翻。

### C2 多安全性时间窗误报为未报告 — 已修复（数据合同层）
- 风险：同一产品两个时间窗（治疗期间 vs 整个研究期）存在时，被误报"未报告"而隐藏。
- 代码：`_select_safety_context`(pages.py:1507-1542)：`base_candidates` 非空但 `candidates` 为空→原因"已有该安全性维度数据，但当前…未匹配"(1508-1513)，**非 NOT_REPORTED**；多个 context 且无法唯一确定→返回 `None,None,"存在多个安全性统计口径…"`(1542)。`_derive_row_status` 因 `safety_treatment is None` → `NOT_REPORTED`？注意：此处需复核——`build_matrix_comparison_rows` 把 `selection_required_reason_zh` 传入 `_row_from_group`(pages.py:1709,1384)，`_row_integrity` 中 `selection_required_reason_zh is not None` → `_derive_row_status` 优先返回 `PENDING_VERIFICATION`(pages.py:1253-1254)。已正确转"待核实"。
- 测试：`test_multiple_safety_contexts_require_selection…`(matrix_states:281) 断言 `status is PENDING_VERIFICATION` 且 `"存在多个安全性统计口径" in reason_zh` 且 `points==()`；`test_existing_safety_dimension_with_unmatched_filter_is_not_called_unreported`(line 312) 断言 `"已有该安全性维度数据" in reason_zh`、`PENDING_VERIFICATION`。
- 反证推演：这是本轮**关键加固** —— 此前若多窗口被静默选错一个，医学经理会误以为"该药只有一个安全性读数"。现在强制"待核实 + 提示选口径"，符合 fail-closed。成立，未推翻。

### C3 总体 TEAE 静默回退 — 已修复（数据合同层）
- 风险：用户未选具体事件时，系统静默回退到某个非总体 TEAE 行。
- 代码：`_select_safety_context`(pages.py:1521-1526) 仅在 `safety_term_id is None and safety_family is TEAE` 且 `overall` 唯一时锁定总体；否则保留 `ordered_contexts` 原序，交由"多口径"逻辑(1542)或精确匹配(1539)处理，不会静默落点。同时 C2 的"口径未匹配→待核实"也阻止了静默回退。
- 测试：默认 `_facts()` 用 `teae-any`/`any_treatment_emergent_adverse_events`(test 文件 `_safety` 默认 term_id="teae-any")，被 `_is_overall_teae`(pages.py:246) 识别为总体；无专门"禁止回退"测试，但 C2 两条测试已覆盖"非默认/多口径不静默选"。
- 反证推演：构造两条 TEAE——`teae-any`(治疗期间) 与 `teae-skin`(治疗期间)，未选 term_id。因 `overall` 仅含 `teae-any` 一条 → 锁定总体，未回退到 skin。**未静默回退**。成立。

### C4 效应形式不一致仍相减 — 已修复（数据合同层，double-guard）
- 风险：治疗组 `response_rate`、对照组 `change_from_baseline` 或方向不同，仍被 `value_t - value_c` 相减出虚假信号。
- 代码：`_direction_corrected_signal`(pages.py:300-305) 组键不一致或 `direction` 不一致→返回 `None`；`_row_integrity`(pages.py:582-590) 同样条件→`INCOMPATIBLE`，且注释"Never reject the row or subtract values from incompatible contexts"(588-589)。`BubblePoint` 仅在 `COMPARABLE` 且三值齐备时生成(pages.py:715-724)。
- 测试：`test_incompatible_efficacy_context_is_retained_without_a_zero_coordinate`(matrix_states:166) 用 LOWER_IS_BETTER 对照 → `INCOMPATIBLE`、`x_value is None`、无点。
- 反证推演：构造治疗 `response_rate`/对照 `change_from_baseline`（组键 `analysis_form` 不同）→ `_efficacy_group_key` 不同 → 信号 None、状态 INCOMPATIBLE、无坐标、无相减。成立，未推翻。

## 三、剩余阻断

1. **[当前合同缺陷 · 必修] S1 倒序轴语义**：`BubblePoint` 仍不携带"图位方向"成对说明（pages.py:884 `safety_axis_reversed` 仅全局布尔；1022-1026 `safety_position` 返回原始 y）。建议在 `BubblePoint` 增加 `safety_position_label_zh`（如"原始发生率20%，图中位于更安全半区"），使脱离图轴的导出（PDF/PPT 明细）不误读。这是首轮 S1 的延续，未在本轮修订中修复。
2. **[未验证] 测试未实际执行**：Bash 被拒，无法确认 pytest 绿灯。仅静态确认用例与实现自洽。
3. **[合同可收敛 · 非阻断] G3 别名**：`UNKNOWN="pending_verification"`(pages.py:82) 与 `WAITING_VERIFICATION` 同值，存在"未知/待核实"标签混同风险，建议收敛。
4. **[渲染验收 · 非阻断] G1/G2**：倒序警告兜底、待核实非坐标占位，数据层已就绪（`unplottable_rows` 带 `reason_zh`，pages.py:1890-1898），但视觉呈现待真实阶段验收。

## 四、真实视觉验收清单（本步仍无法验证，单列）

沿用并精简首轮清单，标注与本轮修订的关联：

1. **[关联 C2/C3] 多口径提示可见性**：当出现"存在多个安全性统计口径，请先选择…"或"已有该安全性维度数据，但…未匹配"时，图区与提示区是否同时、显式呈现，且该产品气泡不出现（待核实），而非静默消失或误报"未报告"。
2. **[S1] 倒序轴成对说明**：每个可比气泡的悬浮/明细除"y=20%"外，是否同时显示"原始发生率 + 图中更安全/更不利半区"，不依赖仅全局轴注。
3. **[G2] 待核实占位**：未知样本量/未报告产品是否在图区以非坐标占位（虚框/灰标）保留并标注"待核实"，而非完全不出现在图里被误读为"无风险"。
4. **[C1] 样本量不串借的视觉证据**：当某试验样本量未知时，其气泡确为待核实，未被其他试验样本量"借"成已知大小。
5. **[C4] 不兼容不相减**：方向/效应形式不一致的竞品在图上明确标"不兼容"且**无任何坐标点**，医学经理不会误以为它有一个疗效信号。
6. **气泡大小直觉**：面积∝样本量在视觉可感知，差 10 倍样本量面积差 10 倍。
7. **无排名暗示**：图/表/提示无任何"最优/第一/综合"字样或排序箭头。
8. **筛选同步与 URL 复现**：切换维度后图、表、提示、证据、URL 同源更新且可分享复现。
9. **中文原生**：面向医学经理文案全中文，无暴露英文后端状态名/字段名。

---
*定向修订审评完成：4 个挑战（样本量串借、多时间窗误报、总体TEAE回退、效应形式不一致相减）已在数据合同层确认修复并有测试覆盖；S1 倒序轴仍为当前合同缺陷需渲染前修；G1/G2 属后续渲染验收；测试因权限未实际运行，仅静态核验。*

---

**核心判断**：定向修订针对 4 个医学误读风险都已落到**数据合同 + 测试**，fail-closed 取向正确，医学经理不会因这些路径产生"假读数"。但 **S1（倒序轴语义）仍未被本轮修订触及**，属于必须在真实视觉阶段前修复的数据合同缺陷。所有视觉可用性项仍无法在本步验证。

需要我把这份跟进报告实际写入 `runs/tests/task64/codebuddy_medical_manager_followup.md` 吗？那需要你授予写文件权限（当前 plan mode 下我被禁止写盘）。
