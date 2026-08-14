你在同一 `worker_03` session 中执行一次有边界的验收修复。主代理与独立 Luna 审查已否决当前 Task 5.1；不要辩解或只写建议，先补失败测试再修实现。

## 已确认的 P0 假绿

1. `EfficacyRecord` / `SafetySummaryRecord` 没有真实结果值，仅凭 `disclosure_state=REPORTED_VALUE` 就可通过。
2. `AProjectContract.result_bearing`、`result_bearing_basis_ids` 与 `ResultBearingTriggerEvidence.carries_attributable_numeric_result` 是自由布尔/字符串，可手工触发或降级；而 Phase 3 已有更强的 `GateEvidenceBinding`、`derive_product_maturity()`、`derive_result_bearing()`。
3. 核心试验、锚定试验、疗效、安全性记录没有产品—试验作用域闭合，可跨试验拼接。
4. 同一监管事件的地域与日期可由两条残缺事件拼接；重复项目、空宇宙、批准项目错误不适用、分母不适用仍可假绿。

## 强制实现方向

- 不再复制弱证据模型。Task 5.1 直接消费 Phase 3 的 `ApplicableUniverseSnapshot`、`GateEvidenceBinding`、`derive_product_maturity()`、`derive_result_bearing()`。
- 删除调用方可填写的 `AProjectContract.development_maturity`、`result_bearing`、`result_bearing_basis_ids`，删除自由布尔触发模型。`evaluate_maturity_gate()` 必须从当前不可变 snapshot + accepted bindings 确定成熟度/result-bearing。
- 对官方登记只有 Results posted 标志但值不完整的例外，新增强类型只读合同（例如 `RegistryResultsPostedEvidence`）：必须绑定 `project_id`、`trial_id`、`fact_version_id`、精确来源定位、`SourceRole.CLINICAL_TRIAL_REGISTRY`、`FactReviewState.ACCEPTED` 与 `official_results_posted: Literal[True]`；评估时校验产品—试验关系，不得用自由 bool/未知 trial。
- A 的核心疗效/TEAE-SAE 最低记录直接从 `GateEvidenceBinding` 判定：必须 accepted、observed、reported value/zero、真实 finite `numeric_value`、正分母、完整定义/单位/时间点或时间窗/分析人群/治疗组、精确来源定位，且 trial 属于该产品、属于 snapshot、与适格锚定试验一致。安全性必须 `FactDomain.SAFETY` 且 TEAE/SAE 的封闭 `unit_id`；疗效必须 `FactDomain.EFFICACY`。不允许任意片段 ID 冒充。
- `AnchorTrialRecord.trial_id` 必须存在于本产品 `core_trials`、snapshot trial_ids 和产品→试验边；其证据版本必须可在 accepted bindings 或 Results posted 证据中找到。
- 监管事件地域和日期必须由同一条事件同时满足；不得跨事件拼接。
- 开发者/原研方仅在确定性成熟度为暂停/终止/撤回时允许整组不适用。中国/境外整组不适用若与同地域监管事件矛盾则阻断。数值记录分母永远不可 `NOT_APPLICABLE`；只有 snapshot 的 `TrialDesignKind.SINGLE_ARM` 可允许对照组为空/不适用。
- `analyze_universe()` 必须接收 snapshot/bindings/flag evidence，要求项目 ID 与 snapshot.product_ids 精确一一对应、无重复、非空；空宇宙由 snapshot 合同本身拒绝。继续保留全部项目、无 Top-N、任一阻断则不生成。
- `BlockingExplanation` 的公共构造边界拒绝无中文字符的 `message_zh`，且解释身份与项目结果一一绑定。

## 必补 exact tests

- reported value 无 `numeric_value` 阻断；reported zero 必须真实 0；安全性同理。
- 手工 result-bearing / maturity 字段成为 extra 并被拒绝；Phase 3 accepted numeric binding 才触发；Results posted 强类型标志触发但缺结果仍阻断。
- anchor 与 core trial 不同、跨产品 trial、疗效与安全来自非 anchor trial均失败关闭。
- 两条残缺监管事件不能拼成一条完整事件。
- active/approved 项目 developer+originator 不适用阻断；中国批准与中国区域不适用冲突；分母不适用阻断；单臂与比较设计的对照组规则。
- 重复项目、项目集与 snapshot 不一致失败关闭；BlockingExplanation 拒绝纯英文。
- 原有无 Top-N、项目保留、递增字段、中文阻断测试继续通过，但必须改用强输入，不得为保旧 API 保留弱入口。

只修改已授权的 `src/ci_workflow/reports/a/*` 与 `tests/reports/a/*`。不要碰 Phase 3 实现。运行 `uv run pytest tests/reports/a -q`、ruff、strict mypy；返回完整 runner 报告并清楚列出尚未解决的边界。
