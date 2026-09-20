Trellis SessionStart ✓ — 已加载当前任务 6.4 上下文。

我先读取评审核对的文件，然后运行目标测试并执行只读对抗探针。

我已读完全部 5 个指定文件。注意到 `design.md` 与 `prd.md` 都没有提到 `MatrixSelectionState`、`apply_matrix_selection`、`build_matrix_view_state`、`reset_matrix_selection`、`MatrixViewState` 等"可配置选择状态与同源派生表面"类（在 `pages.py:1981+` 之后定义）。测试文件 `test_matrix_states.py` 大量依赖这些符号。我需要核实这些实现确实存在且未被改动。让我运行目标测试，并读取 `pages.py` 的剩余部分（2000 行之后的选择状态实现）。

Bash 权限被拒。我用 Read 直接读取 `pages.py` 剩余部分（2000 行之后）来核实选择状态实现，因为测试文件依赖这些符号，这是审评关键。同时用 Grep 确认测试引用的符号存在。

我已经完整读取了 `MatrixViewState` 之前的实现。现在读取剩余部分（3200 行之后），确认 `with_selection`、`build_matrix_view_state`、`apply_matrix_selection`、`reset_matrix_selection` 的语义，特别是它们如何保证"图/表/提示/证据/URL 同源同步"和"无排名"。

我已完成全部 5 个指定文件的完整阅读，并对 `pages.py`（共 3726 行）全量核对了气泡图与比较矩阵的实现。Bash 权限在非交互模式下被拒，无法实际运行 pytest；因此我改为**静态逐行核验测试覆盖的科学底线**，并执行了 ≥12 个只读对抗探针（下面列出），其中 probe 12 实际暴露了一个**语义缺陷**。

下面是完整报告正文（即需返回到 `runs/tests/task64/codebuddy_medical_manager_review.md` 的内容）。

---

# 第 6.4 步独立审评报告 — CodeBuddy 医学经理视角

**审评角色**：视觉敏感、希望一眼看懂但不熟悉程序操作的中国临床试验资深医学经理。
**审评性质**：只读、独立、反证式。未修改任何文件、未联网、未做安全测试。
**审评范围**：`.trellis/tasks/08-29-phase-6-task-64-efficacy-safety-matrix/{prd,design}.md`、`src/ci_workflow/reports/b/pages.py`、`tests/reports/b/{test_bubble_area,test_matrix_states}.py`（并对 `pages.py` 全量 3726 行做静态核验）。
**运行目标测试**：`pytest tests/reports/b/test_bubble_area.py tests/reports/b/test_matrix_states.py` —— 因当前非交互会话的 Bash 权限被拒，未能实际执行；改为对用例逐条比对实现代码，确认每条断言都能被实现满足（见"实测证据"）。这是本报告**未验证项**之一。

## 一、结论

从**类型与科学语义**层面，第 6.4 步的实现与 prd/design 的科学底线高度一致：没有跨试验池化、没有综合分数、没有排名、缺失不充零、倒序仅是视觉轴、气泡面积按治疗组样本量缩放。这些关键约束在 `MatrixViewState._state_integrity`、`BubbleMatrixView`、`BubblePoint` 的模型校验里被强制，而不是靠文案约定。

但作为**医学经理视角**的审评，我定位到 **1 个严重语义问题**和 **3 个一般问题**，全部集中在"测试绿，但真实医学经理会误读"的语义层；其中 **probe 12 证明倒序轴的纵轴语义存在可误读反转风险**。代码从未真正渲染过图表/HTML/PDF，因此所有视觉可用性（一眼看懂、气泡大小对比、轴标签位置）均**无法在本步验证**，必须留到真实浏览器/PDF/PPT 阶段。

**结论级别**：科学底线"通过静态核验"，但**存在 1 个必须在下一步修复的语义缺陷（轴反转风险）**，否则真实视觉输出会让医学经理误以为"向上=更安全=更好疗效"，越过二维观察工具的边界。

## 二、实测证据（逐条绑定科学底线）

| 科学底线 | 实现位置 | 测试覆盖 | 核验 |
|---|---|---|---|
| 试验内治疗—对照疗效信号 | `_direction_corrected_signal` (pages.py:289) | test_bubble_area:158-176 | 方向校正后 x=30（治疗60−对照30，HIGHER_IS_BETTER），原始值 60/30 都保留 ✓ |
| 方向校正不覆盖原始方向/数值 | `raw_treatment_efficacy_value` / `raw_control_efficacy_value` 属性 (pages.py:689,693) | test_lower_is_better:178-196 | LOWER_IS_BETTER 时 x=10，原始值 20/30 保留 ✓ |
| TEAE 默认纵轴 | `SafetyFamily.TEAE` 默认 (pages.py:2077)；`_select_safety_context` 偏好 overall TEAE (pages.py:1499) | test_matrix_states:321-348 | 默认 safety_family=TEAE ✓ |
| 治疗组原始发生率 | `_safety_rate` 只用 `safety_treatment` (pages.py:268, 697) | 同坐标轴测试 | y_value=20 即治疗组 raw ✓ |
| 倒序轴中文说明 | `_BUBBLE_Y_AXIS_NOTE_ZH` (pages.py:45) = "向上 = 发生率更低 = 观察到的安全性位置更有利" | test_bubble_area:172 | 断言完全相等 ✓ |
| 气泡面积按样本量缩放、半径平方根 | `bubble_radius`/`bubble_area` (pages.py:346,364) | test_bubble_area:147-156 | `pi*r²/k²=N`、`area=4*100`(k=2) ✓ |
| 缺失不作零 | `_derive_row_status` 返回 PENDING/NOT_REPORTED 而非坐标0 (pages.py:1237) | test_unknown/未报告：253-286 | 未知样本量=待核实、无点 ✓ |
| 五类比较状态 | `MatrixComparisonStatus` + `_derive_row_status` (pages.py:72,1237) | test_all_five:248-262 | 可比/不兼容/未报告/不适用/待核实 五标签齐全 ✓ |
| 全部筛选与 URL 可复现 | `MatrixSelectionState.to_url/from_url` (pages.py:2416,2471) | test_matrix_states:321-348 | round-trip 稳定、参数排序、中文编码 ✓ |
| 图/明细/提示/证据身份同步 | `MatrixViewState._state_integrity` (pages.py:3163-3211) 强制 chart/table/prompt/evidence 同一 row 集合与 fact 集合 | test_surfaces:351-375 | 四表 row_id 集合相等断言 ✓ |
| 无排名/无综合分数/无跨试验池化 | `is_ranked=False` 多重保证；`_row_from_group` 不跨试验合并 (pages.py:1302) | test_comparison_rows:199-250 | 两试验各自成行、无 score/rank 字符串 ✓ |

## 三、严重问题

### S1（严重）— 倒序纵轴存在"医学经理反向误读"的语义风险
`BubblePoint.y_value` 保存的是**原始发生率**（20%），`safety_axis_reversed=True` 只是布尔标志（pages.py:882, 967）。这意味着：
- 实际渲染时，图形库会把 y=20 画在"向上=更低"的位置（倒序）。
- 但 `y_value=20`、`raw_safety_value=20` 这两个**数值字段**本身没有任何视觉方向信息。导出到 PDF/PPT 的明细表或悬浮提示若直接显示"y=20%"，医学经理可能把它当成"向上 20 分位"或"越高越差"，与"向上=更有利"的意图**相反**。

probe 12 实测：`BubblePoint(y_value=20)` 与 `BubblePoint(y_value=80)` 在模型层**只差数值、不差语义标识**——代码无法从数值本身区分"这是倒序后的低位"还是"原始低位"。测试 test_bubble_area:167-168 仅断言 `y_value==20` 与 `raw_safety_value==20` 相等，**没有断言任何"视觉高位=更安全"的派生说明随数值一起携带**。

**风险后果**：真实视觉输出里，如果轴标签/图例没把"倒序"明示在每一个气泡的上下文，医学经理会误以为右侧高y点=更安全=更好，越过二维观察边界，违背 prd "不得变成安全性得分" 与 "独立医学经理复核确认没有暗示综合优劣" 的验收。
**建议（供后续步骤）**：在 `BubblePoint` 增加 `safety_position_reversed_label_zh` 或在导出层强制每个气泡携带"原始发生率20%、图中位于更安全半区"的成对说明，而不能只靠全局轴注。

## 四、一般问题

### G1 — "可比"行的提示语把"不构成头对头结论"写死在代码，但倒序风险未同等级提示
`_prompt_for_row` (pages.py:2930) 对 COMPARABLE 行只说"不构成跨试验头对头结论"。但 S1 的倒序误读风险没有任何提示兜底。医学经理在表格里看到可比行时，缺少"纵轴为倒序，数值越低图位越靠上"的成对警告。

### G2 — 未知样本量时气泡"不绘制"，但医学经理可能以为"该产品无安全性问题"
`test_unknown_treatment_sample_size` 把未知样本量归为"待核实"且 `points==()`。视觉上该气泡消失，仅留在不可绘制列表。医学经理一眼扫图会**漏掉一个产品**，误读为"它没数据=没风险"，而不是"样本量未知待核实"。需要在图区显式保留一个"待核实"占位标记（非坐标点）而非完全消失。

### G3 — 多个兼容别名可能造成后续维护期语义漂移（非本步阻断）
`MatrixComparisonStatus` 用 `WAITING_VERIFICATION="pending_verification"`、`UNKNOWN="pending_verification"` 把两个名字映射到同一值 (pages.py:81-82)；`MatrixComparisonStatus`/`MatrixStatus`/`ComparisonStatus` 完全等同。这些是"兼容性名字"，但医学经理视角的报告字段若被某处误用 `UNKNOWN` 标签，会与"待核实"混同，丢失"未知 vs 待核实"的细微差别。建议后续收敛。

## 五、反证尝试（我怎样尝试推翻"通过"）

我以医学经理会误读为前提，构造了以下 **12 个只读对抗探针**（均通过静态代码路径推演，未写盘、未运行测试）：

1. **跨试验池化探针**：构造 product-a/NCT1 与 product-b/NCT2 两块事实，核验 `build_matrix_comparison_rows` 是否按 `_efficacy_group_key` 分桶成两行而非合并 → 分桶正确，未池化（test:199-250 印证）。
2. **倒序=得分探针**：搜全仓库 `score`/`rank`/`composite` 在 view dump 中的出现 → test_bubble_area:174-175 断言不存在，代码层 `_state_integrity` 也无相关字段 ✓。
3. **缺失充零探针**：令 treatment_sample_size=None → 期望非0坐标；`_derive_row_status` 返回 PENDING_VERIFICATION，`is_drawable=False` ✓（test:253）。
4. **方向翻转探针**：LOWER_IS_BETTER 治疗=20/对照=30 → x 应为 +10（校正后）；核验 `_direction_corrected_signal` 取 `-difference` → 10 ✓（test:178）。
5. **原始值篡改探针**：校正后 x=10，但 `raw_treatment_efficacy_value` 必须仍是20 → 属性独立存储 ✓。
6. **纵轴用对照组探针**：`y_value` 来源 `_safety_rate(safety_treatment)` 仅治疗组 → 未混入对照 ✓。
7. **气泡面积≠半径探针**：`bubble_area=pi*r²` 且 `r=k·sqrt(N/pi)`，面积∝N 而非半径∝N → 公式正确（test:147-156）。
8. **五状态互斥探针**：构造冲突状态别名（comparison_status 与 status 不一致）→ `_aliases` 抛"不得互相冲突"（test:265-272）✓。
9. **URL 复现探针**：所有维度 to_url→from_url 往返，含中文 `治疗期间` 编码 → 测试断言 `restored==normalized` ✓。
10. **同源同步探针**：chart/table/prompt/evidence 四集合 row_id 必须相等，否则 `_state_integrity` 抛错（pages.py:3169-3206）→ 测试 351-375 ✓。
11. **可重置探针**：`reset_matrix_selection` 恢复默认 selection 与 url → 测试 298-318 `reset==initial` ✓。
12. **倒序语义探针（推翻"通过"）**：`BubblePoint(y_value=20)` 与 `BubblePoint(y_value=80)` 在模型层**不携带任何"图位方向"信息**，仅 `safety_axis_reversed=True` 全局布尔；如果渲染层忘记应用倒序或明细表直接显示 y 值，医学经理会把 80% 误读为"更靠上=更安全"。**此探针成立 → 推翻"视觉层通过"**，暴露 S1。

除 probe 12 外，其余 11 个反证均被实现或测试挡回，未推翻科学底线。

## 六、后续真实视觉验收清单（本步无法验证，单列）

因本步"尚无页面或导出物"，以下必须留到真实浏览器/HTML/PDF/PPT 阶段，由医学经理亲自验收：

1. **轴注可见性**：倒序轴的中文说明"向上 = 发生率更低 = 观察到的安全性位置更有利"是否固定在纵轴旁、不随筛选消失。
2. **气泡数值配对**：每个可比气泡的悬浮/明细是否同时显示"原始发生率 X%（图中位置：更安全/更不利半区）"，而非孤立的 y 数值（对应 S1）。
3. **待核实占位**：未知样本量/未报告的产品是否在图区以非坐标的"待核实"标记保留，而非完全消失（对应 G2）。
4. **气泡大小直觉**：面积∝样本量是否在视觉上可感知，两个样本量差 10 倍的气泡面积是否差 10 倍（避免半径错觉）。
5. **无排名暗示**：图表/表格/提示中无任何"最优/第一/综合"字样或排序箭头。
6. **筛选同步**：切换终点/安全性维度时，图、表、提示、证据、URL 是否瞬时同源更新且可分享 URL 复现。
7. **跨试验不混**：不同试验的气泡在视觉上可区分语境（如试验标签），避免被误读为头对头。
8. **中文原生**：所有面向医学经理的文案为中文，无暴露的英文后端状态名/字段名。

## 七、给实施方的修复建议（供下一步，非本步动作）

- **S1（必修）**：在 `BubblePoint` 或其导出序列化中携带成对语义（如 `safety_position_label_zh`），使任何脱离图轴的展示都能声明"原始发生率 + 图位方向"，不能只依赖全局 `safety_axis_reversed` 布尔。
- **G2（建议）**：`UnplottableBubbleRow` 应能在图区渲染为非坐标占位（如虚线框/灰色标记），并标注"待核实"，而非仅落入不可绘制列表。
- **G3（建议）**：收敛 `UNKNOWN`/`WAITING_VERIFICATION` 别名，避免"未知"被误标为"待核实"。

---
*审评完成：科学底线在类型/语义层通过静态核验；1 个严重语义缺陷（倒序轴误读）需在真实视觉阶段前修复；12 个反证探针中 11 个被挡回，probe 12 推翻"视觉层通过"。*

---

我已完成审评并把完整报告正文写在上方（即应写入 `runs/tests/task64/codebuddy_medical_manager_review.md` 的内容，按你的要求未用工具写入该路径）。

**核心发现概括**：
- 测试"绿"在类型与科学语义层可靠——跨试验池化、综合分数、排名、缺失充零、倒序变得分等底线都被模型校验强制。
- **1 个严重语义缺陷**：倒序纵轴只靠全局布尔 `safety_axis_reversed`，`BubblePoint` 的数值字段本身不携带"图位方向"信息（probe 12 成立）。真实渲染时若轴注或明细未成对显示，医学经理会把高 y 误读为"更安全=更好"，越过二维观察边界。
- **3 个一般问题**：可比行缺少倒序警告兜底、未知样本量产品在图上"消失"易被误读为无风险、状态别名 `UNKNOWN`/`WAITING_VERIFICATION` 可能混同。
- 因 Bash 权限被拒，目标测试未实际运行，改为逐条静态核验；**所有视觉可用性（轴注可见性、气泡大小直觉、待核实占位等）无法在本步验证**，已单列 8 项后续真实视觉验收清单。

需要我把这份报告实际写入 runner 指定路径吗？那需要你授予 Bash/写文件权限（当前 plan mode 下我被禁止写盘）。
