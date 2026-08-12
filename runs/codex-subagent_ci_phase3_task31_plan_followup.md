# Phase 3 Task 3.1 独立方案复核

## 结论

**FAIL。**

本轮只读复核了上轮报告及更新后的合同/任务文件，未读取或执行实际 YAML、Schema、Python 和测试实现。

当前剩余：

- **P0=0**：上轮两个 P0 已写入合同层。
- **P1=5**：仍有适用性闭合、来源/披露枚举、覆盖比较、版本重算和测试矩阵缺口。
- **P2=0**：用户说明与内部状态分层已写入合同。

因此尚不能建议激活 Task 3.1。

## 逐项结果

### 1. 完整对象集合与失败关闭

**PASS：上轮 P0-01 已解决。**

合同已明确：

- 产品、试验、比较、组别集合；
- 输入快照摘要和集合摘要；
- `enumeration_complete=true`；
- 未知、重复、漏评、未证明为空均失败关闭；
- 不得接收调用方过滤后的裸列表。

依据：`0011...md:15`、`design.md:15`、`prd.md:10`。

实际实现仍需证明摘要与 Phase 2 闭合宇宙绑定，但合同层已覆盖。

### 2. B 的作用域、总体值、单臂/多臂和零值

**PASS：上轮 P0-02 已解决。**

合同已明确：

- 试验、比较、组别作用域；
- 治疗组与适用对照组；
- 单臂不虚构对照；
- 多臂总体值或部分组值不能覆盖其余组；
- 安全最低记录按适用组保存；
- `reported_zero` 必须有原文，其他披露状态不得转成零。

依据：`0011...md:16`、`0011...md:17`。

### 3. A 的成熟度与 `result_bearing`

**FAIL：上轮 P1-01 仍部分未闭合。**

已补充的内容包括：

- 成熟度和结果状态由事实推导；
- 临床前数值不触发临床 `result_bearing`；
- 早期无结果项目不得误触发；
- 临床数值结果需要同时具备疗效和 TEAE/SAE 摘要。

但仍缺：

- `result_bearing` 的封闭事实谓词；
- 计划数值与实际观察结果的区分；
- “指定来源”的完整枚举；
- 成熟度枚举及优先级；
- 不能仅凭来源存在或调用方字段触发/降级的明确校验式。

**最小修补：**

固定 `result_domain`、`observed_vs_planned`、成熟度枚举和触发谓词；明确只有临床观察结果触发 A 的结果摘要。

建议 exact nodes：

- `test_a_result_bearing_uses_observed_clinical_numeric_result_not_planned_registry_values`
- `test_a_maturity_trigger_matrix`
- `test_a_result_bearing_missing_efficacy_blocks`
- `test_a_result_bearing_missing_safety_blocks`

### 4. C 的完整设计字段与登记例外

**PASS：上轮 P1-03 已解决。**

合同已补充：

- 试验身份、阶段、开发角色；
- 目标人群、关键入排；
- 分组、随机性、盲法；
- 干预、对照、背景/救援治疗；
- 剂量、给药、疗程、随访、延伸；
- 主要/重要次要终点及时间点；
- 计划/实际样本量；
- 适应症要求的地区、访视、操作特征；
- 官方登记覆盖全部适用核心字段即可通过；
- Protocol/SAP 缺失本身不阻断；
- 分析人群、模型、估计目标、多重性、缺失数据等统计扩展字段非阻断。

依据：`0011...md:9`、`0011...md:19`。

### 5. 来源角色、披露成熟度、缺失/冲突和只收紧偏序

**FAIL：上轮 P1-04、P1-06 仍未完全变成可执行比较器。**

合同已写明原则：

- 来源角色集合只能收窄；
- 最低披露成熟度只能提高；
- 非阻断缺失可改为阻断；
- 阻断不得放松；
- 可接受冲突处置只能收窄；
- 适用对象集合不能缩小。

依据：`0011...md:24` 至 `0011...md:26`、`design.md:28`。

但仍缺：

- 来源角色的封闭枚举及比较顺序；
- 披露成熟度的封闭枚举及序关系；
- 冲突处置的允许集合和子集比较规则；
- `GateOverride` 的操作类型及逐字段比较公式；
- 适用性集合、来源集合、成熟度值发生变化时的确定性比较算法。

**最小修补：**

将每类偏序写成 schema 可验证的关系：

- `new_applicable_set ⊇ old_applicable_set`
- `new_source_roles ⊆ old_source_roles`
- `new_maturity_floor ≥ old_maturity_floor`
- `new_conflict_acceptance ⊆ old_conflict_acceptance`
- `blocking=false → true` 允许，反向拒绝。

建议 exact nodes：

- `test_gate_spec_uses_closed_source_role_and_maturity_enums`
- `test_override_compares_each_monotonic_field`
- `test_override_rejects_conflict_policy_relaxation`

### 6. 合同版本、旧结果与受影响报告重算

**FAIL：上轮 P1-07 仍部分未闭合。**

合同已写明：

- 保存父/子合同版本；
- 保存变更摘要、依赖单元和受影响报告；
- 旧结果不可变；
- 只重算依赖变更单元的报告。

依据：`0011...md:27`、`design.md:28`、`implement.md:10`。

仍缺：

- 结果对象的不可变唯一键；
- 证据快照摘要与合同版本的绑定方式；
- 受影响报告集合是否由依赖关系计算，而不是由调用方直接提供；
- 父版本被覆盖时的明确拒绝条件；
- 变更单元与报告依赖不一致时的失败行为。

**最小修补：**

固定结果键，例如报告、证据快照、基础 GateSpec 版本和项目合同版本的组合；增加依赖指纹，并验证声明的受影响报告集合与计算集合一致。

建议 exact nodes：

- `test_override_binds_result_to_parent_version_and_evidence_snapshot`
- `test_override_rejects_incorrect_affected_report_set`
- `test_override_creates_child_version_without_mutating_parent`
- `test_override_recomputes_only_dependency_affected_reports`

### 7. Exact nodes 与用户说明分层

**FAIL：用户分层已解决，测试矩阵仍不足。**

用户说明分层已明确：

- `GateUnitResult`/`ReportGateResult` 包含中文用户说明；
- 内部 ID、枚举、状态不得直接输出。

依据：`0011...md:20`、`design.md:20`、`design.md:27`。

三个测试文件也已列出首轮节点和矩阵，但仍缺少 B 的关键反例节点：

- 每个比较组的样本量、年龄、性别、严重程度锚点逐字段缺失；
- 治疗/对照作用域；
- 单臂不生成虚拟对照；
- 多臂每组覆盖；
- 组级安全值不能由 trial-level overall 值替代。

此外，`missing_efficacy_or_safety`、`accepts_added_unit_or_raised_threshold` 等合并命名，必须明确为参数化多用例，否则仍可能只覆盖其中一支。

**最小修补：**

在 `implement.md` 的精确矩阵中增加：

- `test_b_each_comparable_group_requires_baseline_fields`
- `test_b_treatment_control_scope_is_explicit`
- `test_b_single_arm_does_not_fabricate_control`
- `test_b_multiarms_require_all_applicable_group_values`
- `test_b_group_scoped_safety_cannot_use_trial_overall_value`
- 将疗效缺失、安全缺失、增加单元、提高阈值拆为独立参数化案例。

## 仍需最小修补

1. 固定 A 的 `result_bearing` 事实谓词、计划/实际结果区分和成熟度枚举。
2. 固定来源角色、披露成熟度、事实状态和冲突处置的封闭枚举及偏序。
3. 将 `GateOverride` 的逐字段比较写成可验证的集合/序关系和操作类型。
4. 固定结果不可变键、证据快照绑定、依赖指纹及受影响报告集合校验。
5. 补齐 B 的组级基线、治疗/对照、单臂、多臂和组级安全 exact nodes。
6. 完成后重新进行独立只读复核；只有 **P0=0 且 P1=0** 才可建议激活 Task 3.1。