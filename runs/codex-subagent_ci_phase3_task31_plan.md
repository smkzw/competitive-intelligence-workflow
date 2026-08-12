# Phase 3 Task 3.1 独立方案审查

## 结论

**FAIL，不建议激活 Task 3.1。**

当前计数：**P0=2，P1=7，P2=1**。P0/P1 尚未归零。

逐项结论：

1. **FAIL**：A/B/C 的科学意图已写明，但对象粒度、适用性表达式、完整枚举和字段级阻断条件不足以机械实现。
2. **FAIL**：B 的“不允许总体值冒充分组值、不能删除试验、缺失不得写零”只有文字约束，尚未形成可验证的数据类型和闭世界覆盖校验。
3. **FAIL**：C 的官方登记例外和统计细节非阻断边界方向正确，但最低临床设计字段及来源角色没有闭合。
4. **FAIL**：A 的成熟度和 `result_bearing` 没有封闭枚举、推导规则和优先级，既可能误阻断，也可能绕过结果摘要。
5. **FAIL**：项目覆盖必须进行适用性、来源角色、披露成熟度、缺失/冲突策略等逐字段偏序比较；当前计划不足以证明。
6. **FAIL**：三个测试文件没有定义 exact test node 和反例矩阵，存在仅测正例或空输入假通过。
7. **PASS（原则）/FAIL（可执行约束）**：中文用户界面边界已写明，但没有机器字段与用户文案的强制分层，后续可能泄露内部术语。

现有设计已明确 GateSpec、GateResult 和覆盖服务的职责分层（`design.md:5`），也明确了 A/B/C 的关键科学意图（`0011...md:7`）。问题是这些内容还不是可闭合的合同。

## 已覆盖边界

以下内容已经被批准计划覆盖，不应作为本轮否定理由：

- A 的项目基础信息及成熟度增加要求。
- B 的核心试验、可比较组基线、疗效、安全、处置字段。
- C 的人群、分组、干预、终点、时间点及统计细节非阻断原则。
- 缺关键单元不得生成通过结果，项目覆盖只能收紧并产生新版本。
- A/B/C 共享不可变证据但不共享规则结果。
- Phase 2 已接受范围不重新验收；Phase 3 后续无草稿、下载、控制图、视觉验收不属于 Task 3.1。

这些边界见 `docs/decisions/0011-phase-3-evidence-gates-and-recovery.md:7`、`.trellis/tasks/08-12-phase-3-evidence-gates-recovery/prd.md:9` 和 `implement.md:7`。

## P0/P1/P2 缺陷

### P0-01：没有闭世界的对象、适用性和完整枚举合同

**后果：** 评估器可能接收被过滤后的产品/试验列表，并把空集合或不完整集合当作“不适用”或通过，无法机械阻止删除产品/试验求通过。

**最小修补：**

在 GateSpec/GateResult 中固定：

- 稳定的 `project_id/product_id/trial_id/comparison_id/group_id/endpoint_id/timepoint_id`。
- 适用性表达式及其可证明的 `applicable_universe_fingerprint`。
- `enumeration_complete`、未知对象、重复对象、空适用集合的明确语义。
- 未证明“确实没有适用对象”时，空输入必须失败关闭。
- 报告结果必须满足“任一适用 GateResult 阻断，则报告阻断”。

**Exact test node：**

- `tests/unit/test_gate_evaluator.py::test_gate_evaluator_fails_closed_on_incomplete_applicable_universe`
- `tests/reports/test_report_specific_gates.py::test_report_specific_gates_reject_dropped_eligible_product_or_trial`
- `tests/reports/test_report_specific_gates.py::test_report_fails_when_any_applicable_gate_is_blocked`

### P0-02：B 的分组作用域和数值类型未闭合

**后果：** 虽然文字禁止总体值冒充分组值，但没有 `scope`、组别绑定、比较对和多臂处理规则。总体疗效、单组安全值或三臂试验的部分结果可能错误满足要求；缺失值也可能被转换为 `0`。

**最小修补：**

将证据值定义为带作用域的类型，至少包含：

- `trial_id/comparison_id/group_id/endpoint_id/timepoint_id`
- `scope = trial | comparison | group`
- 数值、单位、分母、来源定位和披露状态分离存储。
- 明确疗效和 TEAE/SAE 是“每组”“每比较对”还是“每试验”最低要求。
- 缺失、未公开、未找到、技术失败不能序列化成数值零。

**Exact test node：**

- `tests/reports/test_report_specific_gates.py::test_report_specific_gates_reject_overall_value_for_group_scoped_evidence`
- `tests/reports/test_report_specific_gates.py::test_b_missing_comparable_group_blocks_even_with_overall_value`
- `tests/unit/test_gate_evaluator.py::test_gate_evaluator_never_coerces_missing_numeric_value_to_zero`

### P1-01：A 的成熟度与 `result_bearing` 适用性不明确

**后果：** 临床前项目的体外/动物数值可能被误判为临床结果；早期临床无结果项目可能被要求不适用的疗效/安全摘要；已有临床结果项目也可能通过手工把 `result_bearing` 设为 false 绕过要求。

**最小修补：**

固定成熟度枚举、结果领域和触发优先级。`result_bearing` 应由不可变证据推导，不能由调用方自由降级；临床结果摘要必须明确为 all-of：核心疗效 + TEAE 或 SAE 数值摘要。

**Exact test node：**

- `tests/reports/test_report_specific_gates.py::test_a_preclinical_numeric_result_does_not_trigger_clinical_result_summary`
- `tests/reports/test_report_specific_gates.py::test_a_early_clinical_without_results_is_not_blocked_by_result_summary`
- `tests/reports/test_report_specific_gates.py::test_a_result_bearing_missing_efficacy_blocks`
- `tests/reports/test_report_specific_gates.py::test_a_result_bearing_missing_teae_or_sae_blocks`
- `tests/reports/test_report_specific_gates.py::test_a_result_bearing_cannot_be_manually_downgraded`

### P1-02：A 的基础单元和成熟度增加单元未原子化

A 需要身份、创新纳排、靶点/机制、模态、开发者/原研方、适应症关系、中国/境外阶段状态及日期，但实施清单只概括为“A 成熟度”。

**最小修补：**

将上述字段逐一建为 GateSpec unit，并规定无中国或境外开发时必须是有证据的 `not_applicable`，不能是空白。

**Exact test node：**

`tests/reports/test_report_specific_gates.py::test_a_each_base_unit_is_independently_required`

使用参数矩阵逐项删除每个基础字段，分别断言阻断。

### P1-03：C 的“官方登记足够”和“最低统计设计”边界不够精确

**后果：** 可能错误要求 Protocol/SAP，也可能把缺少人群、分组、干预、主要终点、关键时间点或最低设计的信息错误放行。`统计细节非阻断` 与 `最低统计设计` 尚未字段级区分。

**最小修补：**

固定：

- 官方登记作为允许来源角色时，必须覆盖全部 C 阻断字段。
- Protocol/SAP 缺失本身不阻断、不触发补件。
- 人群、分组、干预、主要终点、关键时间点、最低统计设计逐项阻断。
- 分析集、模型、多重性、估计目标、缺失数据、样本量假设逐项建模但非阻断，并保留披露状态。

**Exact test node：**

- `tests/reports/test_report_specific_gates.py::test_c_official_registry_passes_without_protocol_or_sap`
- `tests/reports/test_report_specific_gates.py::test_c_each_core_design_unit_blocks_when_missing`
- `tests/reports/test_report_specific_gates.py::test_c_optional_statistical_details_are_nonblocking_and_state_preserved`

### P1-04：来源角色、披露成熟度、缺失和冲突策略未形成字段合同

**后果：** 来源定位存在，但无法判断某字段是否达到最低来源角色；技术失败、未公开、未找到和冲突可能被压成同一种状态。

**最小修补：**

每个 unit 增加来源角色下限、披露成熟度、缺失策略和冲突策略。关键字段的未解决冲突必须阻断；非阻断字段仍保留真实状态。

**Exact test node：**

- `tests/unit/test_gate_evaluator.py::test_gate_evaluator_enforces_field_source_role_floor`
- `tests/unit/test_gate_evaluator.py::test_required_unresolved_conflict_blocks`
- `tests/unit/test_gate_evaluator.py::test_nonblocking_missing_preserves_disclosure_state`

### P1-05：B 的完成/处置字段只被叙述为非阻断，未定义模型

**后果：** 实现可能把完成/处置字段误当作必填，也可能干脆丢弃，导致无法区分“未报告”和“未完成”。

**最小修补：**

将完成状态和处置字段显式建模为 `blocking=false` 的字段，缺失时保留状态，不得影响其他关键单元的阻断判断。

**Exact test node：**

`tests/reports/test_report_specific_gates.py::test_b_completion_and_disposition_are_modeled_nonblocking_and_state_preserved`

### P1-06：只收紧覆盖缺少逐字段偏序

必须比较的不只是“单元数量”和“阈值”：

- 单元集合：只能增加，不能删除。
- 阈值：只能提高。
- 适用性：不能缩小适用对象集合。
- 来源角色：可接受角色集合只能收窄，最低权威级别只能提高。
- 披露成熟度：只能提高。
- 缺失策略：非阻断改阻断可以，阻断改非阻断不可以。
- 冲突策略：可接受的解决方式只能收窄，未解决冲突不能改为通过。

**Exact test node：**

- `tests/reports/test_gate_override_strictness.py::test_override_accepts_added_unit`
- `tests/reports/test_gate_override_strictness.py::test_override_accepts_raised_threshold`
- `tests/reports/test_gate_override_strictness.py::test_override_rejects_deleted_unit`
- `tests/reports/test_gate_override_strictness.py::test_override_rejects_lowered_threshold`
- `tests/reports/test_gate_override_strictness.py::test_override_rejects_applicability_scope_shrink`
- `tests/reports/test_gate_override_strictness.py::test_override_rejects_source_role_relaxation`
- `tests/reports/test_gate_override_strictness.py::test_override_rejects_disclosure_maturity_relaxation`
- `tests/reports/test_gate_override_strictness.py::test_override_rejects_missing_or_conflict_policy_relaxation`

### P1-07：新版本、旧结果和受影响报告重算无法机械证明

**最小修补：**

`gate-override` 必须包含父合同版本、子合同版本、变更指纹、证据版本和受影响 unit 依赖。新版本追加写入；旧 GateResult 不可变；仅依赖受影响 unit 的报告重算。

**Exact test node：**

- `tests/reports/test_gate_override_strictness.py::test_override_creates_new_contract_version_and_keeps_parent_result_immutable`
- `tests/reports/test_gate_override_strictness.py::test_override_recomputes_only_dependency_affected_reports`
- `tests/reports/test_gate_override_strictness.py::test_unaffected_report_result_remains_unchanged`

### P2-01：内部状态可能泄露到后续用户界面

原则上 PRD 已禁止代码状态、日志术语和“门/信号”（`prd.md:16`），但若后续直接展示 GateResult，以下词汇容易泄露：

`A-v1`、`GateSpec`、`GateResult`、`result_bearing`、`not_applicable`、`partial_delivery_blocked`、`manual-inbox`、`blocker`、`source_locator`。

**最小修补：**

在合同层区分机器字段和用户说明字段；内部 ID/状态不得直接作为用户文本。为阻断 unit 固定中文医学对象、缺失内容、已尝试范围和下一步字段。页面设计留给后续任务。

**Exact test node：**

`tests/reports/test_report_specific_gates.py::test_user_reason_contract_is_chinese_and_excludes_internal_status_names`

## 建议精确测试矩阵

### 首轮三个最小合同测试

每个测试必须使用非空、结构完整但有明确缺陷的 fixture，并断言具体 unit-level 结果，不能只断言“不抛异常”。

- `tests/unit/test_gate_evaluator.py::test_gate_evaluator_fails_closed_on_result_bearing_missing_safety_summary`
  - A：已有临床数值疗效，缺 TEAE/SAE。
  - 预期：阻断，缺失状态保留，不写零。

- `tests/reports/test_report_specific_gates.py::test_report_specific_gates_reject_overall_value_for_group_scoped_evidence`
  - B：治疗组/对照组基线齐全，但疗效只有 trial-level overall 值。
  - 预期：阻断，不得覆盖任一 group-level unit。

- `tests/reports/test_gate_override_strictness.py::test_gate_override_rejects_relaxation_and_preserves_parent_result`
  - 覆盖尝试删除 unit、降低阈值或放宽缺失策略。
  - 预期：覆盖拒绝，旧合同和旧结果不变。

### 后续参数化矩阵

`test_gate_evaluator.py`：

- A/B/C YAML 均通过 schema，unit ID 唯一。
- 空适用集合、未知 unit、重复对象、未完成枚举均失败关闭。
- `missing`、`not_disclosed`、`not_found_after_exhaustive`、`technical_failure` 与数值 `0` 分离。
- 必填冲突阻断，非阻断字段保留状态。
- 来源角色下限逐字段生效。

`test_report_specific_gates.py`：

- A：逐项删除所有基础字段。
- A：临床前、早期无结果、临床已有结果、申报/上市/终止项目适用性矩阵。
- A：疗效缺失、安全缺失、两者齐全。
- B：删除一个核心试验、删除一个产品、删除一个可比较组。
- B：单组值、总体值、多臂值、缺失写零。
- B：完成/处置字段缺失但非阻断。
- C：官方登记完整核心设计且无 Protocol/SAP，允许通过。
- C：逐项删除人群、分组、干预、主要终点、关键时间点、最低统计设计，均阻断。
- C：逐项删除分析集、模型、多重性、估计目标、缺失数据、样本量假设，均非阻断但保留状态。
- 任一适用 A/B/C 阻断时，报告总体结果必须阻断。

`test_gate_override_strictness.py`：

- 接受增加 unit、提高阈值。
- 拒绝删除 unit、降低阈值、缩小适用性、放宽来源角色、降低成熟度要求。
- 拒绝把阻断缺失/冲突改为非阻断。
- 新版本追加生成，父版本和旧结果不可变。
- 仅重算依赖变更 unit 的报告，未受影响报告结果指纹不变。

## 激活 Task 3.1 前的最小动作

1. 先补齐 A/B/C 的规范字段、对象层级、适用性表达式、来源角色、披露状态、缺失/冲突策略和闭世界枚举。
2. 明确 B 的安全值作用域、三臂试验比较规则，以及 A 的 `result_bearing` 推导和成熟度优先级。
3. 为 `gate-override` 固定逐字段只收紧偏序、父子版本、变更指纹和受影响报告依赖。
4. 按上述 exact test node 先写出三项真实红测，再扩展参数化反例矩阵。
5. 只有在 P0/P1 全部归零、精确套件和独立只读复核通过后，才建议激活 Task 3.1。

本轮未修改文件，未重新验收 Phase 2，也未进行安全审查。