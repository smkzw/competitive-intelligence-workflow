28 tests collected. Final review inline:

---

# Task 6.4 最终定向复核：MiniMax 医学经理视角

##结论：**PASS**

Codex 对上轮唯一 P1（`effect_measure` 跨桶时 `comparison_row_id` 冲突）与隐含的家族切换筛选残留风险做了修复：`row_material` 加入 `anchor.effect_measure or "not-specified"`（pages.py:1363），`_selection_for_build`（pages.py:3051-3068）在 `safety_family_changed=True` 时跳过对家族相关字段（term_id / event_definition_zh / time_window_zh / analysis_population_zh / denominator_semantics_zh）的自动回填，强制用户后续再次提供。两项目标测试 **28/28 全过**，两条反例全部通过。

## 实际检查- 只读 `pages.py`、`test_bubble_area.py`、`test_matrix_states.py`、`minimax_medical_manager_followup.md`。
- 运行 `pytest tests/reports/b/test_bubble_area.py tests/reports/b/test_matrix_states.py`：**28 passed**。
 - `test_bubble_area.py`：7 项。
  - `test_matrix_states.py`：21 项（含 `test_effect_measure_buckets_keep_unique_row_ids_and_never_subtract`、`test_switching_safety_family_drops_previous_family_dependent_filters` 等所有回归用例）。
- 运行 `runs/tests/task64/_final_probes.py`（不写盘）共 **16 个断言**：全部通过。

## 两条反例结果

### A. 不同 `effect_measure` 分桶后 `comparison_row_id` 唯一且不相减

- `RD vs OR` → 2 行，2 个不同 `comparison_row_id`（`matrix-comparison_3e2f…` 与 `matrix-comparison_a8c27…`），两行 `efficacy_signal`均为 `None`（跨桶不发生相减）。
- `RR vs HR` → 同上：2 行，2 个不同 ID。
- `RD vs RD`（同 effect_measure） → 1 行，`efficacy_signal = +30`（60−30），保留 `raw_treatment_efficacy_value=60`、`raw_control_efficacy_value=30`，原值未改写。
- 混合桶：T 用 RD + C 用 RD配对 + T 另带 OR 单臂 → 2 行不同 ID，RD配对行做60−30=+30 相减，OR 单臂行信号为 `None`；**没有任何一行跨 `effect_measure` 边界做减法**。
- `BubbleMatrixView` 在 RD/OR 拆行情况下不再抛"行标识不得重复"。

### B. 切换 `safety_family` 清空旧家族筛选并命中新家族唯一事实

-起点：SAE-anchored 选择（`safety_family=SAE`、`term_id=sae-any`、`event_definition_zh=研究期间出现的严重不良事件`、`time_window_zh=研究期间`、`analysis_population_zh=全因 SAE 集`、`denominator_semantics_zh=全部随机化受试者`），视图 COMPARABLE，y=3.0。
- 调用 `apply_matrix_selection(view, {"safety_family": SafetyFamily.TEAE})`：
  - `safety_family` 变为 `TEAE`。
  - 5 个家族相关筛选重置为 `from_facts` 默认锚（`term_id=teae-any`、`event_definition_zh=治疗期间不良事件`、`time_window_zh=治疗期间`、`analysis_population_zh=安全性分析集`、`denominator_semantics_zh=None`），旧 SAE 字段不再泄漏。
  - 视图 COMPARABLE，y=20.0，`safety_family=teae`。
  - `to_url()` 不再含 `event=sae-any`、`event_definition=研究期间…`、`window=研究期间`、`safety_population=全因 SAE 集`。
- 反向（TEAE→SAE）：
  - 默认 `from_facts` 锚在 TEAE；切换后5 字段全部为 None，视图 COMPARABLE，y=3.0，`safety_family=sae`。
- 不变性：`apply_matrix_selection(view, {})`（无 family变化）保持既有家族锚，证明变更检测是精确的，不是盲目清空。

## 仍未发生的视觉验收范围

按要求本次未运行 HTML/PDF/PPT 渲染与浏览器验收。下列项目须留到真实页面：

- 轴标签中文（"方向校正的试验内治疗—对照疗效信号"、"治疗组原始治疗期间不良事件发生率（倒序）"）的 OCR/换行/字号是否完整可读。
- 倒序纵轴 "向上 = 发生率更低 = 观察到的安全性位置更有利" 在 SVG 上的真实方向与刻度间距。
- `r = k·sqrt(N/π)` 面积随 N 缩放（100 vs400 真实4 倍可辨）；N极大（≥10000）时 UI 层 `k` 自适应是否必要。
- PENDING 单元格中文原因"存在多个安全性统计口径，请先选择…"、"已有该安全性维度数据，但…未匹配…" 在完整表与提示气泡中的字数截断、标点统一性。
- 多产品 × 多试验矩阵中"非默认 safety维度切换"的视觉辨识（默认仍 TEAE，但切换 SAE/AESI/治疗相关 TEAE 时视觉提示）。
- 切换 safety_family 后 URL状态栏可读性、浏览器地址栏对中文参数的兼容性（UTF-8 编码百分号后长度）。
- `comparison_row_id` 在 URL/state/evidence 三处引用是否在跨 effect_measure 拆行后保持1:1 映射（数据层28 项测试已验证唯一性，渲染层 ID复用还需视觉确认）。

## 备注

- 本步审评同时确认 `_selection_for_build` 在 `safety_family_changed=True` 时**不**继承 default 的家族字段——这是双刃：用户切换 family 时不会"暗带"旧家族的 term/window 等，但需要 UI 提示用户重新选择。这是合同要求的"切换必须重新选择"语义，符合 P1 残留 P0 阻断问题 #2/#3 的修复路径。
- `comparison_row_id` 现在含 `effect_measure` 后唯一性已满足，但若未来允许同一行含 T、C 不同 effect_measure 的"事后合并视图"，需要重新审视此字段的设计。
- 未覆盖：`safety_event_definition_zh`、`safety_analysis_population_zh`、`safety_denominator_semantics_zh` 三个二级筛选在多语境冲突下的反例（与 `safety_time_window_zh` 同源，逻辑应一致；本次未独立探针）。
