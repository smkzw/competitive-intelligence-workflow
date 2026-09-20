所有验证工作已完成。现在我来编写最终报告。

# 会议参与者输出：ci-r24-gatespec-blocker-closure-review-20260906 - general_single_object

## 边界检查

- 角色：`general_single_object`（独立代码设计审阅），serial 模式，未查看其他参与者本次输出；三个执行期 worker 报告仅作为审计输入，逐项对照当前字节独立复核，未采信其结论。
- 工作目录为 runner 绑定的授权工作区；只读审阅 + 运行焦点测试（仅写 `.pytest_cache`/`__pycache__` 等可再生缓存）；未写 `runs/conference/ci-r24-gatespec-blocker-closure-review-20260906/general_single_object.md`（该路径现有 357 字节占位，本报告完整返回由 runner 持久化）。
- 未读取生产路径、旧中文工作区、凭据材料；未修改仓库；不宣称任何最终接受权。
- 初始读集之外补充的证据：v1.3 §5.4/5.5/6、执行计划 R2.4、三个 worker 报告、`src/ci_workflow/{gates,domain,application,capabilities,sources,renderers}` 相关字节、A/B/C YAML、两个 schema、相关集成/单元负向测试；全部在 Source Of Truth 清单内或其直接下游。

## 独立工作成果

结论先行：**在当前字节中，我没有找到新的、可达的 P0/P1 绕过**——即能够造成科学假绿、候选删减、终态无机器审计或阻断后下游残留的实现/测试缺陷。三个执行期 worker 指出的绕过项中，除新鲜度外，我逐项核对确认已在当前字节闭合（证据见下节）。执行 review 声称"除新鲜度外已修复"与字节实况相符。剩余问题集中在 7 项 P2 级残余/加固项与若干须由用户/Codex 裁决的合同问题。

### 一、逐项闭合核验（worker 历史发现 vs 当前字节）

**worker_01（GateSpec/evaluator）**

| 原发现 | 当前字节核验 | 状态 |
|---|---|---|
| 失败码/恢复路线缺失 | `GateUnitSpec` 现含 `failure_code` + `recovery_route_ids: tuple[GateRecoveryRoute,...] (min_length=1)`（`gates/models.py:341-342`）；关键单元失败码锁定 `missing_required_evidence`，扩展锁定 `missing_extension_evidence`（`models.py:384-389`）；override 单调性覆盖 `recovery_route_ids`（子集只能增不能删，`gates/coverage.py:106-107`） | 已闭合 |
| 候选删减绕过 | evaluator 层仍接受缩小宇宙——`tests/reports/test_report_specific_gates.py:770` 后半段明确注释"这是合法操作（新宇宙）"并断言单产品宇宙通过。**但产品层已闭合**：`ReportPayloadBinding.universe_product_ids` 参与 `reviewed_universe_sha256`（`domain/research_package.py:82-140, 899-914`）；submission 逐字节校验 `payload.universe_product_ids == binding.universe_product_ids`（`research_package_submission.py:125`）；`universe_product_ids == report_data.product_ids`（`source_research_service.py:1512`）；A/C 的 `product_ids` 是从实际 products 行派生的 computed property（`renderers/portal/report_a.py:270`、`report_c.py:205`），payload 另有 `content_sha256` 绑定。删除产品行 → 三处一致性与摘要同时破裂 | 已闭合（产品层）；evaluator 层为已文档化边界 |
| C 关键单元域过宽 | C 全部 8 个关键单元 `allowed_fact_domains: [trial_design]`（`policies/gates/C-v1.yaml:21-170`）。`allowed_observation_kinds` 全缺省（全集合），对设计类单元语义上正确（设计事实本多为 planned/target 值），不构成绕过 | 已闭合 |
| 关键冲突绕过 | `evaluate_unit_decision` 与 `_evaluate_endpoint_unit` 现检测作用域内任一 `CONFLICTING`/`OPEN_CONFLICT_PRESERVED` 绑定即整体阻断该单元（`models.py:1646-1663`、`evaluator.py:393-407`），另一个已解决绑定不能再掩护；负向测试 `test_unresolved_key_conflict_never_becomes_not_publicly_disclosed_or_zero` 覆盖 A/B/C | 已闭合（单元级合取） |
| （#6 成熟度启发式） | `derive_product_maturity`（`evaluator.py:126-164`）未变：任一已接受监管 NOT_APPLICABLE → PAUSED、监管 observed REPORTED_VALUE → APPROVED。属数据信任边界而非实现绕过，列为风险（见第五节） | 开放（风险级） |

**worker_02（恢复/信息增益）**

| 原发现 | 当前字节核验 | 状态 |
|---|---|---|
| C1 MATERIAL_OMISSION 可坐缺口模型/QC | `GapDoubleExhaustion._gap_type_binds_compatible_evidence`：科学缺口只接受 `NO_MATERIAL_OMISSION`、技术缺口只接受 `TECHNICAL_ACCESS_UNRESOLVED`（`gates/exhaustion.py:592-611`），`MATERIAL_OMISSION_FOUND` 在两分支均被拒；blocker builder 独立复检同一约束（`blocker_audit.py:1577-1590`）；负向测试 `test_terminal_exhaustion_rejects_material_omission_conclusion` | 已闭合 |
| C2 技术伪造信息增益 | 技术缺口任何非空增益字段（含 new_fields/new_source_versions）即拒绝（`exhaustion.py:612-620`）；负向测试（`gap-technical-fake-gain`，"伪造字段"/"fake-v1"） | 已闭合 |
| C3 增益只比布尔值 | 现逐轮精确对齐 `new_evidence_fragment_ids`/`changed_gate_unit_ids`/`reduced_conflict_set_ids` 三个身份元组（`exhaustion.py:742-765`），且 `evidence_gap.information_gain_diff == information_gain_rounds` 全等（`exhaustion.py:538-539`）。**残余**：`new_fields`/`new_source_versions` 仍是自由字符串（见第二节 P2-a） | 大部分闭合 |
| C4 同查询/访问换标签 | `RecoveryRound.retrieval_signature` 由回执 `(query_or_identifier, access_method)` 派生，`RecoveryHistory` 构造与 `add_round` 双处拒绝重复检索签名，饱和判定同时要求策略签名与检索签名不同（`sources/retries.py:155-167, 206-255, 227-237`）；负向测试 `test_strategy_labels_cannot_hide_repeated_query_and_access_path` | 已闭合 |
| C5 遗漏复核无干净上下文 | `GapOmissionReview` 新增 `producer_context_digest`/`reviewer_context_digest`（64-hex），相等即拒绝（`exhaustion.py:244-269`）。**残余**：两摘要为调用方自报，不锚定真实上下文内容（见 P2-b） | 模型级闭合，锚定声明性 |

**worker_03（blocker/no-draft 产品链）**

| 原发现 | 当前字节核验 | 状态 |
|---|---|---|
| publication/B-baseline 平行写包器 | `write_report_b_blocker` 已从 `src/` 全量消失（rg 零命中）；publication 路径改走类型化 `build_and_write_publication_blocker_package`（`blocker_audit.py:1874`），绑定 ManualSupplyGate 字节 SHA、单次响应、`file_unavailable` 终态，失败关闭（`run_service.py:3403-3434`）；B 基线不全现返回 `recovery_required`（`run_service.py:2905-2925`）且拒绝出 HTML，与 checkpoint"不能发布终态 lite blocker"一致；产品运行级测试验证 `blocker_kind == "publication_unavailable"`（`test_multi_report_product_run.py:840`） | 已闭合 |
| QC 穷尽无机器包 | `apply_scientific_qc_verdict` 已穷尽否决在迁移前强制 `build_and_write_scientific_qc_blocker_package`（`capabilities/scientific_qc.py:463-484`），全量重验证 12 组身份一致性 + 嵌入完整穷尽记录 | 已闭合 |
| resume 只看存在性 | resume 现走 `validate_existing_blocker_package`（模型重验证 + audit_digest + 身份 + publication 门字节绑定 + audit.md 再生成比对）+ 无下游断言（`run_service.py:3157-3192`、`blocker_audit.py:2166-2279`）；负向测试 `test_cli_project_run_resume_rejects_pre_drifted_blocker_package` | 已闭合 |
| symlink/多余文件 | 目录与文件均拒 symlink、恰好两文件、字节精确漂移检测（`_write_blocker_package`/`_verify_existing_package`，`blocker_audit.py:2106-2193`）；负向测试 `test_blocker_directory_and_files_reject_symlinks` | 已闭合 |
| no-draft/resume_node 机器字段 | 三个审计变体均含 `no_draft: Literal[True]` + `resume_node: Literal["recovery"]`（`blocker_audit.py:601-602, 800-801, 906-907`），schema 根 required 含两字段 | 已闭合 |
| 撞库/抢先伪造包 | 既有目录内容不精确匹配即 `BlockerAuditDriftError`/`BlockerPackageIntegrityError`，canonical 写入永不覆盖异字节 | 已闭合 |

**独立抽测**：当前 dirty tree 上运行 `test_double_exhaustion + test_route_recovery + test_no_draft_on_unresolved_key_conflict + test_report_specific_gates`（85 passed）与 `test_no_draft_when_blocked + test_no_draft_after_scientific_qc_rejection + test_gate_evaluator`（140 passed），与 checkpoint 声称的绿灯一致。

### 二、仍开放的发现（按严重度排列；无 P0，P1 级仅新鲜度一项且属已声明待裁决）

**P1（合同缺口，已声明待用户裁决——按任务要求只列风险不裁决）**
- **新鲜度缺失**：`GateUnitSpec`、A/B/C YAML、`gate-spec.schema.json`、gates 全目录对新鲜度零字段零校验（rg 零命中）。v1.3 §6 把"新鲜度"列为规则必备内容，当前陈旧事实可无限期满足关键单元，是唯一能通向"科学假绿"的合同级开口。checkpoint 已声明须用户原生 Ask 裁决模型/窗口/截止日语义后方可 RED→修复。

**P2（残余/加固，均给出锚点）**
- **(a) 增益摘要自由字段**：`InformationGainDiff.new_fields/new_source_versions`（`domain/evidence.py:310-323`）未与 `RecoveryRound.source_versions` 或任何历史内容绑定；`exhaustion.py:750-761` 只对齐三个身份元组。机器 blocker JSON 可携带历史中不存在的字段/版本标签（不影响饱和判定，影响审计保真）。补救：从回执/版本记录派生或删除字段。
- **(b) 遗漏复核上下文摘要自报**：`exhaustion.py:244-245` 两摘要为调用方 64-hex 自报，仅约束不等；对比 `ScientificQcCurrentContext` 的摘要是由内容计算的。独立性证明强度依赖恢复阶段纪律。补救：在 host 边界由规范化上下文包派生。
- **(c) 未知 unit_id 绑定被静默忽略**：`assert_bindings_in_universe`（`models.py:1402-1543`）校验对象作用域但不校验 `binding.unit_id ∈ spec.units`；evaluator 按 `(object_id, unit_id)` 过滤后未匹配绑定被丢弃。当前绑定 unit_id 由我方摄取代码硬编码（`fresh_b_research_package.py:1079-1239`），不可达；但一旦映射代码出错，冲突事实会被无声丢弃而非失败关闭。补救：`evaluate_report` 加闭世界 unit_id 断言（一处检查，成本极低）。
- **(d) 空宇宙阻断页硬编码假链接**：`_drive_blocker_write` 仍写死 `source_links=("https://clinicaltrials.gov/study/NCT01234567",)`（`run_service.py:3474` 附近），出现在用户面前——恰是 worker_03 指出、未见修复的一条。
- **(e) fail-open 形状**：`_drive_blocker_write` 在 `ctx.universe_evidence is None` 时静默 return（`run_service.py:3453-3455`）。当前不可达（`_hydrate_universe_evidence` 缺文件即 raise；resume 走终态重验分支），但正确形状是显式 `ContractConfigError`。
- **(f) 两个新审计变体不受 JSON schema 约束且 publication 变体 §6 字面缺口**：`schemas/blocker-audit.schema.json` 根 required/defs 仅覆盖 canonical `BlockerAudit`（无 publication/scientific_qc 变体 defs）。`PublicationUnavailableBlockerAudit` 无 rule_spec_id/指纹、无路线回执清单（仅 `attempted_paths`）、无两轮信息增益、无独立遗漏结论、无 residual_uncertainty 字段（`blocker_audit.py:772-810`）。机器审计存在（类型化、摘要绑定、可恢复），但是否满足 §6 最低字段集属合同解释，交 Codex 裁决（见问题 1）。
- **(g) 成熟度启发式的对抗性误标**（worker_01 #6 沿革）：现有测试覆盖矩阵正例，不含 source_role/披露状态误标的对抗用例；误标可移动 `maturity_ge_clinical/submission` 适用性边界。属数据信任边界，建议补对抗性负向测试锁定当前行为或引入 claim 级监管事实二次核验。

## 风险、缺口与验证需求

**风险清单（只列不裁决）**
1. 新鲜度模型三选一（as-of 下限 / 按来源角色 max-age / 来源版本时效）未定 → P1 开口（上文）。
2. 阈值语义：终点级 `threshold = max(unit.threshold, len(required))`（`evaluator.py:432`）已防稀释；但 YAML 内其他 threshold>1 单元在"多个独立事实版本"语义下是否有临床上限，未见用户裁决记录。
3. 历史截止日：产品路径仅单向拒绝 `data_cutoff > contract.data_cutoff`（`run_service.py:2820-2822, 1670-1671`），无最低新鲜度或截止日重算语义。
4. `_evaluate_endpoint_unit` 中 `covered` 在单事实版本跨组复用时不计入 contributing（`evaluator.py:409-433`）——语义正确但依赖 `threshold≥组数` 保持；若未来某单元显式 threshold 覆盖语义变化，需回归锁定。
5. render 先行、`rendered_unreviewed` 预览态字节在复核前已落盘（`run_service.py:2113-2133`）：这是 R2 既定合同（晋级复用字节），与 no-draft 合同（阻断报告无产物）并行不悖，但两者边界值得一条显式回归测试锁住"未晋级预览不得被当作可交付门户"。

**验证需求（尚未验证的部分）**
- 我未重跑全量 gate（944 unit/contract、bundle/fresh-install）；以 Codex review 记录 + 我方 225 项抽测为据。
- 我未实机跑 `no-draft-a-empty`/publication/B-baseline 三条产品链到磁盘验证 audit.json 落盘字节（worker_03 曾请求的实盘验证仍未做）；静态审阅 + 测试证据为主。
- `test_v13_closure_recovery.py`（10 测试）未逐条审阅；B/C `recovery_required → evidence_blocked` 接线的测试覆盖面未穷尽确认。

## 给 Codex 的 bounded 问题

1. **publication 变体的 §6 合规口径**：`PublicationUnavailableBlockerAudit` 缺 rule_spec_id/路线回执/两轮增益/遗漏结论等 §6 最低字段。是否裁定"ManualSupplyGate 字节绑定 + attempted_paths + 请求级 blocking_fields 视为满足 §6"，还是要求该变体补齐（或嵌入等价 evidence）？这决定 P2-f 是关闭还是转为修复任务。
2. **evaluator 层缩小宇宙**：接受 `test_report_specific_gates.py:770` 现状（产品层闭合 + 注释文档化），还是给 `evaluate_report` 增加可选 locked-universe digest 参数以在库层也失败关闭？
3. **P2-a/b** 是否授权一次最小修复（派生/删除自由字段；上下文摘要由内容派生）+ 各一条 RED。
4. **P2-d** NCT 硬编码链接：改为回执派生真实链接、或空集合场景显式无外链？

## 建议的后续步骤

1. Codex 裁决上述 4 个 bounded 问题（同会话答复即可，均不影响本轮"无新 P0/P1"结论）。
2. 若采纳 P2 修复：先 RED（自由字段伪造、未知 unit_id 绑定、硬编码链接可见性）后最小实现，全部落在 `gates/exhaustion.py`、`gates/models.py`（evaluate_report 一处断言）、`run_service.py` 两处，不触碰已闭合面。
3. 新鲜度三项（模型/阈值/历史截止日）按 checkpoint 既定路线走用户原生 Ask；裁决前不得以任何默认语义关闭 P2。
4. 裁决后按任务计划推进 P2 收口与 P6 治理门（独立会商、分层 gate、bundle/fresh-install、checkpoint、归档），Codex 保留最终接受权。

**恢复点**：若需续跑本会话，从"P2 修复授权 + 4 问题答复"继续；我方证据链（文件锚点 + 225 项抽测结果）均在上文，无需重探。
