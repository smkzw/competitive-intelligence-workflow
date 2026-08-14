1. REVISE

2. 缺陷

P0-1：疗效/安全性记录没有真实结果值，却可放行。

- `contracts.py` 的 `EfficacyRecord`、`SafetySummaryRecord`（335–391）只有 `disclosure_state`、分母和任意 `evidence_fragment_ids`，没有 `numeric_value`、分子/发生率或可解析原始值。
- `analysis.py:_core_efficacy_outcome`（452–470）和 `_safety_summary_outcome`（474–495）仅凭 `REPORTED_VALUE`/`REPORTED_ZERO` 状态及槽位完整即满足。
- 只读反例：无疗效值、无 TEAE/SAE 值、仅填 `"REPORTED_VALUE"` 和任意片段 ID，`evaluate_maturity_gate()` 返回未阻断；输出为 `structural_reported_value_without_numeric_value: True`。
- 现有 71 项测试全部通过，但测试夹具本身也没有填入结果值（如 `test_result_bearing_gate.py:127–149`）。

P0-2：`result_bearing`、触发依据和成熟度仍可由调用方手工注入或降级。

- `AProjectContract.result_bearing` 与 `result_bearing_basis_ids`（`contracts.py:466–500`）只校验“布尔值与非空字符串是否一致”，不校验依据是否存在、是否已接受、是否含真实数值。
- `ResultBearingTriggerEvidence.carries_attributable_numeric_result`（`contracts.py:394–425`）本身也是自由布尔值；`derive_result_bearing_trigger()`（`analysis.py:259–285`）不接收真实数值或项目身份。
- `evaluate_maturity_gate()`（`analysis.py:548–557`）直接消费 `project.result_bearing`，没有调用确定性触发器。
- 只读反例：`carries_attributable_numeric_result=True`、无数值本体时返回 `trigger_free_boolean: True`；一个存在中国批准事件但手工标为 `CLINICAL` 的项目返回 `manual_clinical_maturity_with_approval_event: clinical False`，即成熟度为临床且未阻断。

P0-3：项目—试验—结果记录没有作用域绑定，可跨试验/跨项目拼接。

- `EfficacyRecord`、`SafetySummaryRecord` 没有 `project_id`/`trial_id`；`AnchorTrialRecord` 只检查非空试验号和非空片段 ID（`contracts.py:316–332`）。
- `_anchor_trial_outcome()`（`analysis.py:446–449`）只检查列表非空；`_core_trial_outcome()`（413–421）只检查存在任意核心试验；疗效和安全性分别从各自列表中取任意一条。
- 只读反例：核心试验为 `trial-a`、锚定试验为 `trial-b`，两条结构化但无真实数值的记录仍使门槛通过，输出 `anchor=trial-b, core=trial-a, gate.blocked=False`。
- 触发器只有 `eligible_trial_ids`，没有产品或适应症关系，无法拒绝其他项目的试验证据。

P1-1：`不适用`缺少适用性依据，且分母错误地允许不适用。

- `_developer_originator_outcome()`（`analysis.py:355–377`）对所有成熟度允许开发者或原研方声明不适用。
- `_region_outcome()`（380–410）对所有项目接受整组区域不适用，不验证是否存在该区域无开发证据或与监管事件矛盾。
- `_record_slots_complete()`（441–443）把分母 `NOT_APPLICABLE` 当作完整。
- 只读反例均通过：批准项目有中国批准事件但中国区域全为不适用；批准项目开发者/原研方全为不适用；疗效分母为不适用。输出均为 `True`。

P1-2：L1 身份和全宇宙边界不完整。

- `aliases` 默认空元组（`contracts.py:448–484`），分析层又把身份与创新资格“构造即满足”（`analysis.py:539–544`）；空别名项目可通过，输出 `empty_aliases_project_passes: True`。
- `analyze_universe()`（`analysis.py:578–610`）不检查重复 `project_id`、重复身份或闭合宇宙；同一项目 ID 可出现两次，输出 `['product-a', 'product-a']`。
- 空输入直接得到 `report_ready=True`；现有 `test_no_top_n.py:379–385` 将其定义为通过，但没有穷尽检索的空集证明。

P2：阻断说明模型本身不强制原生中文。

- `BlockingExplanation`（`analysis.py:163–179`）只检查非空，不检查中文；直接构造 `message_zh="missing evidence"` 可以成功。
- 内部 `_blocking_message_zh()` 生成路径目前是中文，但模型边界仍允许英文或工程状态文本。

3. 最小修复建议与应补 exact tests

- 用 Phase 3 已接受的事实/快照作为唯一输入；移除可写入的 `result_bearing` 和自由 `basis_ids`，由真实 `numeric_value`、披露状态、审核状态、来源定位及正式登记结果标志确定。
  - `test_reported_value_without_numeric_value_blocks`
  - `test_reported_zero_requires_actual_zero`
  - `test_safety_reported_value_without_numeric_value_blocks`
  - `test_result_trigger_requires_accepted_numeric_fact_not_boolean`
  - `test_result_bearing_cannot_be_manually_downgraded`

- 为每条疗效/安全记录绑定产品、适应症、试验、终点、时间点和证据版本；复用既有作用域校验，禁止跨产品/跨试验拼接。
  - `test_anchor_trial_must_match_project_trial_scope`
  - `test_efficacy_and_safety_records_require_trial_identity`
  - `test_cross_product_trial_result_fails_closed`
  - `test_cross_trial_records_do_not_satisfy_result_gate`

- `NOT_APPLICABLE` 必须带版本化适用性依据；分母必须为真实正数，只有单臂试验且有正式证明时对照组才可不适用。
  - `test_approved_project_originator_not_applicable_blocks`
  - `test_china_approval_cannot_coexist_with_china_not_applicable`
  - `test_denominator_not_applicable_blocks`
  - `test_control_not_applicable_requires_single_arm_proof`

- 要求至少一个别名或明确的别名“不存在”证据；输入宇宙拒绝重复 ID，并要求空集证明。
  - `test_empty_aliases_block_l1_identity`
  - `test_duplicate_project_ids_fail_closed`
  - `test_empty_universe_requires_exhaustive_empty_set_proof`

- 为 `BlockingExplanation.message_zh` 增加中文校验，并绑定项目名称。
  - `test_blocking_explanation_rejects_non_chinese_message`
  - `test_blocking_explanation_identity_matches_gate_project`

4. 已核查但未构成缺陷的边界

- `required_fields_for()` 与 `assert_ladder_monotonic()` 的成熟度字段确实逐层递增。
- 当前 `analyze_universe()` 没有 Top-N 或删除逻辑；40 个项目的现有测试通过且保持输入顺序。
- 已存在项目阻断时，整批 `report_ready=False`、项目保留、中文说明按项目对应。
- 计划值、目标值、方案假设、未知试验号和非允许来源的现有测试行为正确；问题在于输入布尔值和记录模型本身不携带可验证事实。
- 安全性 `BELOW_REPORTING_THRESHOLD` 状态在 §12.2 可作为准确阈值状态；缺陷是当前模型没有阈值证据或注册表绑定。
- 单臂试验的对照组“不适用”本身可以合法；当前缺的是试验设计和适用性证明。
- 本轮仅运行现有 A 测试和只读反例，未安装依赖、未做安全测试、未修改工作区。

