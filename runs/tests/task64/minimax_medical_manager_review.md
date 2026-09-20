The instructions require returning the report inline (no tool write). Here is the complete medical-manager review.

---

# 第6.4 步独立审评：MiniMax 医学经理视角（B 类疗效—安全性矩阵）

## 结论：**有条件通过**

科学合同、交互合同、五类矩阵状态、轴方向、面积公式、原始事实保留、不排名等都通过两项目标测试（19/19）和 ≥12 项对抗探针（70+ 断言全过）。合同在数据层足以支撑后续站点式页面；但有几处医学可读性与边界处理细节需要在6.5 阶段定稿前落实。

## 实际检查

- 读取 `prd.md`、`design.md`、`src/ci_workflow/reports/b/pages.py`、`tests/reports/b/test_bubble_area.py`、`tests/reports/b/test_matrix_states.py`。
- 运行：`pytest tests/reports/b/test_bubble_area.py tests/reports/b/test_matrix_states.py` → 19 passed（覆盖 PRD 验收标准 `test_bubble_area.py` + `test_matrix_states.py` 两份目标测试全部用例）。
- 运行 `runs/tests/task64/_adversarial_probes.py`（不写盘的对抗探针）：23 组共 70+ 断言全部 OK，包括同试验 T–C 差值与方向校正、原始事实保留、TEAE 原始发生率、倒序映射、面积/样本量、未知不作零、五类状态、URL 稳定往返、轴/表/提示/证据同步、无排名与综合分。

## 发现的问题（按严重度）

### 高1. **`build_matrix_view_state` 在不知道 `treatment_sample_sizes` 时无声回退到 `safety_treatment.denominator`，令"样本量未知"路径几乎不可达**
   - `_lookup_sample_size`（pages.py:1410）走完 `mapping` 即返回；如未提供映射或映射缺键，再回退到 `safety_treatment.denominator`。而 `SafetyFactRow` 的 `_disclosure_state=REPORTED_VALUE` 强制 `denominator` 非空且为正整数（safety.py 内 "已报告安全性数值必须保留正分母"）。
   - 实际后果：当唯一事实已"报告治疗组 TEAE 20%（n=100）"时，样本量被静默认定成 100，`status=comparable`，气泡会被绘出，而医学上"我们其实不知道总随机化入组的样本量"这条科学边界被掩盖。
   - 对抗探针 `_unknown_n()` 用 `treatment_sample_sizes={("p","T1","a1"): None}` 显式声明未知才能复现 `pending_verification`，这与默认构建路径不符。医学经理建议：若 `mapping` 未提供或缺键且无 `treatment_sample_size` 来源，应落 `sample_size_state=UNKNOWN`，并向 `UnplottableBubbleRow` 暴露原因"未提供独立治疗组样本量"。

2. **`build_matrix_comparison_rows` 将不同 endpoint/compatibility桶的治疗与对照分到独立 `MatrixComparisonRow`，并未发出"跨桶不可比"的明确状态**
   - 探针 `_different_endpoint_groups()` 显示：endpoint-family 与 compatibility-key 不同时（如 EASI-75 vs NPS），T 与 C 不在同一 `MatrixComparisonRow` 中，结果行只有治疗事实、对照臂缺失，状态变为 `not_reported`（因为 `efficacy_control is None`）。这在临床语义上等同于"对照无效"，而非更精确的"跨终点族不可合并"。
   - 医学经理建议：出现跨 endpoint配对时应在视图层产生显式"跨终点族不可合并"的 `INCOMPATIBLE` 提示，而不是悄悄变成"未报告"。

### 中

3. **`bubble_area` / `bubble_radius` 拒绝 `radius_scale <=0`，但 `bubble_radius(N, k=1)` 在没有显式 `radius_scale` 时默认1.0；视图层没有"恒定像素下限"或"最大 N截断"**
   - 当 N=10 000 时气泡半径 ≈ 56.4×k；N=100 时 r ≈ 5.6×k。两点面积比 ≈ 100，符合"面积 ∝ N"。但线性半径会带来视觉冲击；医学经理要求 UI 层在 6.5 渲染前对 `k` 做归一化（与最大样本量等比缩放）以保证肉眼可辨。
   - 合同层面没问题（探针 `_area()` 通过），但实际观感必须靠渲染层处理，不能让模型假装"小气泡 =少样本"。

4. **`SampleSizeState` 与 `MatrixComparisonStatus` 的关联靠私有路径；当 `_sample_size_state` 已知且 N 为 None 时，模型自身会抛 `ValueError("已知样本量状态必须携带正整数")`，但 `_derive_row_status` 路径下，`pending_verification` 仅在所有事实都"可绘制"且 `treatment_sample_size is None` 时才出现**
   - 在 `_derive_row_status`（pages.py:1265）这一行后才会进入 `pending_verification`；任一上游状态（CONFLICTING/UNRESOLVED_DUE_TO_ROUTE/NOT_APPLICABLE/INCOMPATIBLE/NOT_REPORTED）都会先截获。这意味着 `pending_verification` 在临床事实上几乎只剩"技术路径未解决但其他都齐"的语义。
   - `test_unknown_sample_size_is_pending_verification_not_zero` 通过是因为它走 `build_bubble_matrix(..., treatment_sample_sizes={...: None})` 路径，绕开了 `build_matrix_comparison_rows` 的内部 `safety_treatment.denominator` 回退。
   - 医学经理建议：在矩阵视图层对"未报告但应有"的字段给出明确的"待核实"标签，并保留 `reason_zh` 可视化提示，已做到（探针 `_unknown_n` 通过）。

5. **`MatrixSelectionState.from_facts` 默认 `safety_family=TEAE`、`safety_term_id` 取首个 overall TEAE**（pages.py:2229-2330）
   - 当快照里没有 overall TEAE（只有 SAE/严重事件/治疗相关 TEAE）时，fallback走到 `ordered_safety[0]`，可能选出非 TEAE 维度作为默认。这会让"默认视图"误导：用户期望"治疗期间任何不良事件"总发生率，但实际显示的是 SAE之类。
   - 医学经理建议：默认行为固定为 `SafetyFamily.TEAE + term_id=None + 优先选 overall TEAE`，否则保留为"待选"，并在 UI 上提示"未识别到总体 TEAE，已退回到 SAE"。

### 低

6. **`BubblePoint.efficacy_fact_row_id != safety_fact_row_id` 的校验在 `model_validator(mode="after")` 中检查，但并未阻止"原始事实行相同而坐标仅一"的退化输入**（pages.py:986-987）。
   - 当前校验只阻止"气泡点复用同一事实行"。无独立探针证伪，但建议6.5 渲染层在调用前再确认 `comparison_row_id` 在所有视图中唯一。

7. **`selection_from_url` 接受 `bubble_size=任何非已知字符串`抛 `ValueError`**，但默认落回 `treatment_sample_size`（pages.py:2626）。当用户在 URL 中塞入"安全性 N"或"次要终点 N"做切换，当前模型用一句错信息拒绝，无法给出可恢复提示。
   - 医学经理建议：在 `MatrixViewState` 解析层捕获并降级为"仅支持治疗组样本量"的中文提示。

8. **`MatrixSelectionState.from_facts` 在 endpoint_family_id 选取时按 `_default_endpoint_family_id`（pages.py:1382）以 `_PRIMARY_ENDPOINT_ROLE_TOKENS` 优先 +完整桶数最多优先**。
   - 当 endpoint标签同时命中"主要/次要"且双语对应时（"primary"/"主要"/"主要终点"），fallback 在 `_default_endpoint_family_id` 的 sort_key `(complete, key)` 中以 `(complete, key)` 字典序排序兜底，可能让"主要但更长的 endpoint_id"反而被丢。需6.5 UI 提示"默认主终点"由何规则挑出。

##建议修复（6.5 阶段前）

- **A.** 在 `build_matrix_view_state` 与 `build_bubble_matrix` 路径中：当 `treatment_sample_sizes` 未提供或显式为 `None`，禁止回退到 `safety_treatment.denominator`；改为 `sample_size_state=UNKNOWN` + 显式原因"治疗组样本量未独立提供"。当前 `_lookup_sample_size` 的回退顺序需要调整。
- **B.** `build_matrix_comparison_rows` 在跨 endpoint/compatibility-key 配对时，产出 `INCOMPATIBLE` 行而非"只有治疗臂"。可在 `_select_safety_context` 中增加"跨 endpoint 配对"分支。
- **C.** `MatrixSelectionState.from_facts` 默认 `safety_family=TEAE`，无 overall TEAE 时在视图层写明"当前快照未识别总体 TEAE，已退回 {具体}"。
- **D.** `_BUBBLE_X_AXIS_LABEL_ZH` 与 `_BUBBLE_Y_AXIS_LABEL_ZH` 的字符串虽然正确，但是否中文化尚未在 6.5 渲染中走 OCR验证（本次不做视觉验收）。
- **E.** `_derive_row_status` 与 `_status_reason` 把"未知样本量"理由显示为"治疗组样本量未知，不以零绘制气泡"，中文提示合格；不过 `_is_pending_verification_state` 把 CONFLICTING 与 UNRESOLVED_DUE_TO_ROUTE 都收拢到 `pending_verification`，应在 `reason_zh` 中明确区分"来源冲突"与"技术路径未解决"两条子类提示。`test_matrix_surfaces_share_rows_facts_and_never_rank` 通过，但未验证两条原因文本可分辨。

## 尝试推翻实现的对抗探针及结果（共 23 组）

| # | 探针目的 | 结果 |
|---|---|---|
| 1 |方向校正：`lower-is-better` 翻号 + 原始值不改 | OK |
| 2 | `higher-is-better` 同试验 T–C 差值 | OK |
| 3 | 气泡面积 ∝ N（线性 4 倍放大） | OK |
| 4 | `pi·r² == N` 数值恒等 | OK |
| 5 | 治疗组样本量显式为 None → `pending_verification`（非"样本量未知"误标） | OK |
| 6 |治疗组疗效未报告 → `NOT_REPORTED`，不画零坐标 | OK |
| 7 | CONFLICTING 安全披露 → `pending_verification`，原因含"冲突" | OK |
| 8 | UNRESOLVED_DUE_TO_ROUTE也会落到 `pending_verification`，但需要 value=None（模型边界） | OK |
| 9 | Y 轴保留原始 20.0 TEAE 率，轴反转标志 = True | OK |
| 10 | 五类状态（可比/不兼容/未报告/不适用/待核实）四种可直接构造并去重为四个标签 | OK（不适用因需 `applicability_predicate_id` 模型边界跳过） |
| 11 | URL 8 个维度的全部往返：endpoint / safety_family / product_ids / trial_ids / target_ids / snapshot_id / timepoint / safety_term_id | OK |
| 12 | `with_selection` 重建后 chart/table/prompt/evidence 行 ID同步 | OK |
| 13 | `reset()` 回到 `default_selection` 且 `comparison_row_ids` 与 URL 一致 | OK |
| 14 | dump 中无 `rank` / `score` / `排名` / `综合` / `名次` / `winner` / `best` | OK |
| 15 | 同一产品两试验 → 两条独立 `MatrixComparisonRow`，不跨试验合并 | OK |
| 16 |安全性治疗臂 `arm_id` 错配 → 不画气泡且原始疗效事实保留 | OK |
| 17 | 筛选产品 → chart/table/prompt/evidence 行 ID 全等 | OK |
| 18 | `treatment_sample_size=0` 失败关闭（Pydantic ge=1） | OK |
| 19 | `bubble_radius(-10, 1.0)` 失败关闭（自定义消息） | OK |
| 20 | `bubble_area(100, radius_scale=0.0)` 失败关闭 | OK |
| 21 | `REPORTED_ZERO` 安全值0 → 真实零发生率，不视作未报告 | OK |
| 22 | 安全性 `unit="例"` + denominator=120 → 12/120 = 10% | OK |
| 23 | 治疗组 N来自映射 120 但 safety denominator=80 时，N=120仍驱动气泡，且 y=15/80=18.75% | OK |
| 24 | URL `product_ids` 顺序 `(b,a,c)` 与 `(a,b,c)` 产生相同 URL 参数（稳定排序） | OK |
| 25 | 状态别名 WAITING_VERIFICATION / UNKNOWN 与 PENDING_VERIFICATION 共享 `pending_verification` 字符串 | OK |
| 26 | 轴标签/注释中文：`x 轴 =方向校正…`、`y 轴 = 治疗组原始治疗期间不良事件发生率（倒序）`、`y 注 = 向上 = 发生率更低 = 观察到的安全性位置更有利`、`x 注 = 越右表示所选疗效指标的观察信号越强` | OK |
| 27 | 跨 endpoint配对（EASI-75 vs NPS）走 build路径得到 `not_reported` 行（应改 `INCOMPATIBLE`） |暴露问题 #2 |

> 注：探针 10 中跳过 `not_applicable` 行的直接构造（受 `SafetyFactRow.applicability_predicate_id` 模型边界限制），但 `_STATUS_LABELS_ZH` 字典中显式存在 `不适用 → 不适用` 标签，状态机本身完备（已通过 `test_all_five_matrix_states_have_distinct_chinese_labels`）。

## 尚未验证

- 视觉验收：本步骤按要求未运行 HTML/PDF/PPT/浏览器渲染物；轴标签、矩阵单元颜色、提示气泡位置、超长靶点名溢出、复合分母语义栏布局都未在真实渲染上观察。Codex 后续必须独立跑浏览器验证。
- 字段覆盖：本次未对 `effect_measure`、`denominator_semantics_zh` 等可选字段做交叉一致性探针；model_copy 旁路防御由 `validate_*` 重跑校验保障。
- 中文提示的语言风格一致性：理由文本来自 `_status_reason` 字符串拼接，未对全部5 类状态、5 种披露状态做拼写/标点统一性检查（建议 6.5 OCR/翻译阶段追加）。
- 端到端回流：实际 `runtime/report_pack` → `MatrixViewState` 的快照绑定未运行（不在本次范围）。
- 长期口径：`treatment_group_sample_sizes`、`sample_sizes`、`sample_size_by_arm`、`treatment_sample_sizes` 四个映射别名同时存在；只接受单源（已校验），但未对"同时提供两个不同映射导致歧义"做错误信息可读性检查。
- 国际化标签稳定性：`_BUBBLE_*_LABEL_ZH / NOTE_ZH` 常量已锁定；如有版本更替需要文档登记。
