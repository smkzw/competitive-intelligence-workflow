# Phase 3 实施清单

## Task 3.1 版本化证据规则与覆盖评估

接受状态（2026-08-12）：已通过原 worker/Cursor/Luna 同会话复验；机械证据为 2 项最终攻击、143 项精确套件和 331 项全库回归。保留的上下文外成员关系 P2 延后到携带 GateSpec 的持久化加载服务，不阻断 Task 3.1 接受。

- [x] 创建 A/B/C YAML、三份 schema、模型、评估器和覆盖服务。
- [x] 首轮三个精确节点分别取得真实失败：`test_gate_evaluator_fails_closed_on_result_bearing_missing_safety_summary`、`test_report_specific_gates_reject_overall_value_for_group_scoped_evidence`、`test_gate_override_rejects_relaxation_and_preserves_parent_result`。
- [x] A 成熟度、B 疗效/安全/逐组基线、C 人群/分组/干预/终点/时间点/统计设计按批准范围编码。
- [x] B 处置字段和 C 统计细节分别验证为建模但非阻断。
- [x] 缺任一适用关键单元阻断；不能删除产品或试验换取通过。
- [x] 项目覆盖只能增加单元或提高阈值；新合同版本只重算受影响报告，旧结果不可变。
- [x] 完整对象集合摘要、作用域事实、披露状态与数值零分离、内部状态/中文用户说明分层均有参数化反例。
- [x] 精确套件、全库、Ruff、strict mypy、包校验、差异检查和独立验收通过后提交。

### Task 3.1 独立验收修复矩阵（2026-08-12）

首次独立对抗验收结论为 `FAIL; P0=6; P1=3`，Task 3.1 保持未接受。以下反例必须全部机械关闭后才能再次验收：

- [x] `test_b_core_efficacy_requires_distinct_treatment_and_control_numeric_values`：多臂/有对照终点必须按关系图覆盖治疗组与适用对照组的独立数值，单个数值加两个组名不能通过。
- [x] `test_a_always_applicable_critical_unit_rejects_unproven_not_applicable_binding`：固定必填字段不得被任意“不适用”文字绕过；不适用必须匹配受控谓词与版本化依据。
- [x] `test_gate_evaluator_rejects_unjustified_empty_endpoint_set_and_does_not_drop_b_core_efficacy`：关键对象集合为空时不得静默省略单元；空集合证明必须逐对象类型、结构化、绑定证据版本并进入集合摘要。
- [x] `test_gate_evaluator_rejects_cross_trial_group_endpoint_and_comparison_bindings`：宇宙保存产品→试验→比较/组/终点/时间点关系边；绑定必须通过整条父子路径，不能跨试验拼接。
- [x] `test_recompute_rejects_parent_spec_fingerprint_mismatch_and_preserves_blocked_parent`：规则结果绑定规范内容指纹；父规范内容不一致时不得生成子结果。
- [x] `test_aggregate_report_rejects_satisfied_unit_below_threshold`：单元结果必须机械约束 outcome/blocking/threshold/satisfied_count 一致性，聚合不得接受伪造满足结果。
- [x] `test_derive_result_bearing_requires_eligible_trial_scope`：所有公开推导入口统一要求适格试验作用域。
- [x] `test_b_single_arm_core_efficacy_accepts_unique_group_without_control`：单臂支持/特殊核心只要求唯一组数值，不虚构对照。
- [x] `test_c_region_visit_operational_requires_explicit_indication_rule`：地区/访视/操作特征仅在版本化适应症规则明确列为关键时适用，不能默认阻断。
- [x] 修复后重跑 Task 3.1 精确套件、全库、Ruff、strict mypy、包校验、差异检查，并由全新上下文独立复验至 P0/P1=0。

第二轮同会话独立复验仍为 `FAIL; P0=6; P1=3`，继续追加以下不可绕过条件：

- [x] `test_b_core_efficacy_with_comparator_requires_distinct_treatment_and_control_group_values`：存在比较对象时，每个比较至少关联两个组，关联终点必须覆盖治疗组与适用对照组；不能以“比较存在但只有一个组”通过。
- [x] `test_b_core_efficacy_rejects_wrong_domain_planned_or_nonfinite_numeric_evidence`：规则单元声明允许事实域与观察类型；B 核心疗效只接受有限的观察性疗效数值。
- [x] `test_gate_evaluator_rejects_cross_product_trial_evidence_stitching`：产品级绑定携带试验作用域时，试验必须属于该产品。
- [x] `test_b_multitrial_requires_per_trial_comparator_or_single_arm_proof`：每项试验单独保存比较/单臂设计证明；其他试验有比较不能替代本试验证明。
- [x] `test_evaluate_unit_decision_cannot_force_always_applicable_unit_to_not_applicable`：无条件适用单元不接受调用方传入 `applicable=false`。
- [x] `test_aggregate_rejects_malformed_or_cross_report_unit_results`：阈值≥1；聚合必须校验规格、报告类型、单元身份、关键性、适用性、结果/计数/决定/摘要一致；直接构造的矛盾报告结果失败关闭。
- [x] `test_b_effect_support_rejects_cross_endpoint_comparison_binding`：显式保存并校验比较↔终点关联。
- [x] `test_recompute_rejects_research_role_set_mismatch_and_binds_summary`：研究角色集合版本进入宇宙摘要与结果键。
- [x] `test_threshold_counts_distinct_fact_versions_not_duplicate_bindings`：同一事实版本重复绑定只计一次；终点逐组值还需组别与事实版本均独立。

第三轮同会话独立复验为 `FAIL; P0=5; P1=0; P2=1`，Task 3.1 继续保持未接受。新增以下机械停止条件：

- [x] `test_comparative_trial_rejects_comparison_with_zero_group_associations`：闭合校验必须遍历所有比较对象；比较存在但没有任何组边时也必须拒绝，不能只检查已有组边的比较。
- [x] `test_b_effect_support_requires_explicit_comparison_endpoint_association_when_endpoint_is_omitted`：比较效应关键证据必须携带具体终点并匹配显式比较→终点关系，省略终点不得满足。
- [x] `test_b_core_efficacy_respects_raised_unit_threshold_during_recompute`：终点逐组最低数量与项目提高后的单元阈值同时生效，实际阈值取二者较高值。
- [x] `test_aggregate_rejects_incomplete_spec_unit_result_set`：报告聚合必须使用由规范与闭合宇宙独立推导的完整 `(unit_id, object_id)` 结果矩阵；漏任一适用对象或关键/扩展单元均拒绝，不能由调用方只提交一条满足结果获得通过。
- [x] `test_aggregate_rejects_satisfied_result_without_distinct_fact_lineage`：满足结果的计数必须由足量且互异的不可变事实版本支撑；空事实链路、重复事实标识或计数不一致均拒绝。
- [ ] `test_report_gate_result_load_rejects_unknown_unit_id_with_canonical_spec` 作为 P2 加固项保留在后续持久化加载服务边界；当前上下文无规范的值对象不能单独判定成员关系，但正式加载路径必须携带规范校验。

第三轮构建后 Cursor 同会话整合复核关闭原五个 P0，但新增 `P1=1`；最终接受前还必须关闭：

- [x] `test_aggregate_rejects_unit_result_batch_from_different_snapshot_or_spec`：单元结果必须先形成不可变评估批次，批次键绑定报告类型、证据快照、宇宙摘要、规则指纹和单元结果摘要；聚合器拒绝把快照/规则 A 的批次重新贴到对象集合相同的快照/规则 B。正式评估与重算只通过该批次边界进入聚合。

最终暂停前 Luna 同会话复验为 `FAIL; P0=2; P1=0; P2=1`。以下两项未关闭，Task 3.1 不得接受、不得进入 Task 3.2：

- [x] `test_aggregate_rejects_model_copy_tampered_batch_key_or_unit_results`：聚合器入口必须重新验证传入批次实例；Pydantic `model_copy(update=...)` 跳过模型校验后，伪造批次键或嵌套单元事实链路仍必须拒绝。
- [x] `test_public_batch_constructor_rejects_detached_unit_results_from_changed_snapshot_or_spec`：导出的批次构造器不得把旧快照/旧规则的脱离结果重新盖章为新身份。修复应让批次构造与聚合成为评估器所有的不可分原子路径，或给单元结果加入不可重盖章的规范/快照来源证明；仅重新计算批次键不足以关闭。

### Task 3.1 精确反例矩阵

- `test_gate_evaluator.py` exact nodes：`test_gate_evaluator_fails_closed_on_incomplete_applicable_universe`、`test_gate_evaluator_never_coerces_missing_numeric_value_to_zero`、`test_gate_evaluator_enforces_field_source_role_floor`、`test_gate_spec_uses_closed_source_role_maturity_fact_state_and_conflict_enums`、`test_required_unresolved_conflict_blocks`、`test_nonblocking_missing_preserves_disclosure_state`、`test_report_fails_when_any_applicable_gate_is_blocked`。
- `test_report_specific_gates.py` exact nodes：`test_a_each_base_unit_is_independently_required`、`test_a_preclinical_numeric_result_does_not_trigger_clinical_result_summary`、`test_a_early_clinical_without_results_is_not_blocked_by_result_summary`、`test_a_result_bearing_uses_observed_clinical_numeric_result_not_planned_registry_values`、`test_a_maturity_trigger_matrix`、`test_a_result_bearing_cannot_be_manually_downgraded`、`test_a_result_bearing_missing_efficacy_blocks`、`test_a_result_bearing_missing_safety_blocks`、`test_report_specific_gates_reject_dropped_eligible_product_or_trial`、`test_b_each_comparable_group_requires_baseline_fields`、`test_b_treatment_control_scope_is_explicit`、`test_b_single_arm_does_not_fabricate_control`、`test_b_multiarms_require_all_applicable_group_values`、`test_b_group_scoped_safety_cannot_use_trial_overall_value`、`test_b_completion_and_disposition_are_modeled_nonblocking_and_state_preserved`、`test_c_official_registry_passes_without_protocol_or_sap`、`test_c_each_core_design_unit_blocks_when_missing`、`test_c_optional_statistical_details_are_nonblocking_and_state_preserved`、`test_user_reason_contract_is_chinese_and_excludes_internal_status_names`。
- `test_gate_override_strictness.py` exact nodes：`test_override_accepts_added_unit`、`test_override_accepts_raised_threshold`、`test_override_rejects_deleted_unit`、`test_override_rejects_lowered_threshold`、`test_override_rejects_applicability_scope_shrink`、`test_override_rejects_source_role_or_disclosure_maturity_relaxation`、`test_override_rejects_missing_or_conflict_policy_relaxation`、`test_override_compares_each_monotonic_field`、`test_override_binds_result_to_parent_version_and_evidence_snapshot`、`test_override_rejects_incorrect_affected_report_set`、`test_override_creates_child_version_without_mutating_parent`、`test_override_recomputes_only_dependency_affected_reports`、`test_unaffected_report_result_remains_unchanged`。

## Task 3.2–3.7

- [ ] 双重穷尽、证据不足说明和所有无草稿负断言。
- [ ] 下载请求、manual-inbox 自动识别、规范命名、归档与恢复。
- [ ] GT01–GT11 类型化控制图、非法迁移拒绝、节点合同与重放幂等。
- [ ] 报告/格式独立的部分交付与阻断。
- [ ] EX01–EX02、FX01–FX06 真实项目/fixture 执行器、唯一 catalog 和规范产物路径。
- [ ] SQ01–SQ04 独立科学质控接受/否决。

## Phase 3 退出

- [ ] 正式阶段命令通过；真实 `no-draft-a-empty` 项目只生成中文证据不足说明，不生成假 HTML。
- [ ] 独立科学数据与控制图验收 P0/P1=0；项目缓存和被取代过程材料完成可恢复清理。
