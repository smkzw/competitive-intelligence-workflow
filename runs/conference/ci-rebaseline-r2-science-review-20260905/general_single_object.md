# Conference Participant Output: ci-rebaseline-r2-science-review-20260905 - general_single_object

## Boundary Check

- 只在 runner 绑定的当前工作目录 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 内工作；只读审查 + 运行测试，未修改任何实现文件。
- 未读取 `runs/conference/ci-rebaseline-r2-science-review-20260905/general_single_object.md`（本报告以消息返回，由 runner 落盘）。
- 未访问禁区的旧中文工作流根目录，任何命令中未出现、未探测、未盘点该路径。
- 初始读集两文件已读；按授权补充读取了 v1.3 规范、roadmap、execution v3、G01-G20 差距矩阵（`reviews/codex_v13_implementation_gap_matrix_20260904.md`）、`src/ci_workflow/`、`policies/`、`tests/`、`runs/execution/ci-rebaseline-rebuild-20260904/worker_03.md`（仅作非权威证据）。
- 未查看其他与会者输出；未声称任何最终临床/监管/视觉/浏览器/发布验收权威——所有结论均为科学/状态机/合同层审查证据，最终接受权在 Codex。
- 测试运行使用 `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`，未产生仓库内新文件（pytest 临时目录在系统 /tmp）。

## Independent Work Product

审查方法：以 v1.3 §3/§5/§6/§8、roadmap R2、execution v3 §4（R2.1–R2.4）与 G01-G20 差距矩阵的 G01–G09 行为合同基准，逐条追踪当前字节中的类型化合同、状态机守卫与焦点测试，并实际运行焦点测试复现证据。

**逐项结论总览**

| 编号 | 审查领域 | 结论 |
|---|---|---|
| G01 | 入口消歧（一句话 + 原生 Ask + 可选 package） | **PASS** |
| G02 | Yaozh 一次性询问与凭据边界 | **PASS** |
| G03 | 独立上下文预检（主 Agent 不得自证） | **PASS**（附 1 项设计边界备注） |
| G04 | 竞品宇宙闭包 | **PASS**（附 1 项收敛证明合同缺口，非阻断） |
| G05 | 按条件触发的两轮恢复 + 细粒度路由失败 | **PASS**（附 2 项语义框架问题，见 Q1/Q4） |
| G06 | publication 分类 + manual-supply 单次中断 | **PASS** |
| G07 | 补件原地规范重命名（不复制/不移动/不改字节） | **PASS**（1 个陈旧测试待迁移） |
| G08 | B 类整体临床构念语义归并 + 确定性守卫 | **PASS**（附 1 项基线人群归并风险，见 Q3） |
| G09 | B 类三组气泡预设、中性不排名 | **PASS（限于 R2 合同层）**，预设 2/3 无运行时图表构建器（R3/R4 交付物） |
| 跨切 | 单报告分支直达科学 QC（成功标准 5） | **A：PASS；B/C：当前字节不可达 —— VETO 级阻断项 F-CROSS-1** |

---

**G01 入口消歧 — PASS**

证据：
- `src/ci_workflow/application/intake.py:119-125`：`PublicIntakeRequest._ask_matches_missing_types` —— 未指定报告类型时必须携带原生 Ask、已指定时禁止重复 Ask，双向失败关闭。
- `intake.py:56-89`：`REPORT_TYPE_OPTIONS` 按固定顺序 A/B/C 携带中文解释（与 v1.3 §1.2 的三句解释一致）；`ReportTypeAsk._options_are_fixed` 强制三选项按 A、B、C 顺序。
- `intake.py:141-143`：`reports=None` 是合法"待选择"状态并携带 Ask，用户不被要求先写 package。
- 复现：`uv run pytest tests/contract/test_v13_intake_package.py -q` → 5 passed（含缺省类型 Ask、一句话+历史截止日、Yaozh 一次、包严格校验、图合同）。
- `skills/competitive-intelligence-workflow/SKILL.md:2-3`：frontmatter `name: 竞品调研`，触发词、A/B/C 中文解释、可选历史截止日、可选高级输入均为原生中文；`gate/snapshot/receipt/research-package` 四个被禁内部词未出现在用户文案（用“结构化研究资料”替代）。

非阻断备注（P3）：`intake.py:167-174` `_extract_indication` 对“请做 X 的竞品调研”会留下尾部“的”（标记表未含孤立“的”）；该字段是候选身份、由下游身份解析消歧，方向保守可接受，但建议补一条剥离规则或断言。`intake.py:144` `default_cutoff = date.today()` 用系统本地时区，而 v1.3 要求“合同建立日所在声明时区的自然日”——`declared_on` 参数已预留，需确认 CLI/宿主入口总是显式传入。

**G02 Yaozh 一次性询问与凭据边界 — PASS**

证据：
- `intake.py:180-207`：`YaozhAccessRecord.ask_count: Literal[1]`；`record_yaozh_answer`（`intake.py:222-243`）同答重放幂等、异答抛 `YaozhAskAlreadyAnswered`、跨项目身份不一致失败关闭；`route_enabled` 与答案一致性由模型校验器强制。
- `intake.py:210-257`：`YaozhRouteDecision.blocks_core_research: Literal[False]` —— 缺少 Yaozh 不阻断核心研究；中文说明明确“仅用于身份、别名、中国状态和线索交叉核验”。
- 凭据边界：`YaozhAccessRecord` 无任何凭据/Cookie/令牌字段；`domain/research_package.py` 的 `_assert_safe_value`（`research_package.py:446`）拒绝 secret 形态元数据；复现测试 `test_research_package_rejects_secret_like_metadata_and_accepts_strict_payload`（`tests/contract/test_v13_intake_package.py:164`）通过。

**G03 独立上下文预检 — PASS**

证据：
- `src/ci_workflow/application/capability_preflight.py:27-38`：`independent_context` 在 v1 冻结能力清单内；`:259-265` 未声明即 `available=False`（失败关闭）；`:61` 中文修复指引“请提供独立上下文审阅者；主 Agent 不能自证首份宇宙闭包”。
- `:394-406` `independent_context` 在 `_research_dependencies` 中，未就绪时逐报告 `research` 状态 blocked，并经 `:314-358` 矩阵一致性校验。
- 下游身份分离（防伪造同一上下文）：`capabilities/ontology_universe.py:286-287` `validate_universe_closure` 拒绝 `independent_context == producer_context`；`gates/exhaustion.py:464-465` 执行者/复核者角色标识必须不同；图合同 `graph/typed_skills.py:203-209` scientific-qc 绑定 `clean-context-scientific-review` 且 `independent=True`。
- 复现：`tests/integration/test_capability_preflight.py` 12/16 passed；4 个失败全部是选 `pdf/pptx/html_ppt` 输出的陈旧 v1.2 测试（见风险节 F-T-1），与 G03 能力逻辑无关。
- 备注（设计边界，接受）：宿主声明 `CI_WORKFLOW_INDEPENDENT_CONTEXT=1` 本质是声明式；预检无法技术性验证子 Agent 存在。伪造声明的实际防线是下游上下文分离摘要（closure/double-exhaustion/QC 全部绑定 context 并拒绝同上下文复用）。建议 R5 三宿主验收时把声明写入 host receipt 并与真实独立会话证据绑定。

**G04 竞品宇宙闭包 — PASS**

证据：
- `capabilities/ontology_universe.py:175-265` `UniverseClosureReceipt`：`closed=True` 要求全球+中国路线非空、互不重叠、状态均为 `completed/not_applicable`（`access_blocked`/`network_error` 一律不得闭合，`:249-264`）；alias/target/company/trial 四个反向扩展维度 receipt 非空且唯一；必须绑定 `independent_review_id` + `independent_context`；每轮新增实体集合 `new_entity_ids_by_round` 必填。
- `domain/research_package.py:488-499,515-540`：包级闭包绑定——闭包路线必须存在于路线集合、候选/排除实体 ⊆ 实体集；`assert_gate_ready` 要求闭包路线 result_class ∈ {completed, success_with_evidence, not_applicable} 且独立干净上下文复核已记录，否则不得进门槛。
- 复现：`uv run pytest tests/integration/test_v13_closure_recovery.py -q` → passed，含三个负向断言：`china_route_status="network_error"` 拒绝闭合、`trial_expansion_receipts=[]` 拒绝、生产上下文复用拒绝。

非阻断缺口（建议 R3 前修复，最小修正 + 负向测试）：
- **收敛证明不可表达**：`ontology_universe.py:233-247` 要求每一轮 `new_entity_ids_by_round` 非空，因此"最后一轮零新增”的收敛轮无法记录；`closed` 只是断言布尔，没有任何“已收敛”谓词。这与 G04 修复要求“每轮新增集合与收敛证明”中的收敛证明半缺。最小修正：允许显式空轮（或新增 `convergence_round_id` 字段绑定最后一轮），负向测试 = 未记录收敛轮/收敛轮引用未知实体即拒绝闭合。

**G05 两轮恢复 + 细粒度路由失败 — PASS**

证据：
- 细粒度分类完整：`domain/enums.py:16-45` `RouteAttemptResult` 12 类与 v1.3 §5.5 逐一对应；`RouteCompletion` = completed/not_applicable/access_blocked；`FactDisclosureState` 8 类逐一对应。
- 技术失败≠无证据：`sources/receipts.py:129-157` `assert_supports` —— `route_completed` 终态回执只允许 `content_acquired/not_found`（“技术失败不能标记为路线已完成”）；`route_access_blocked` 必须 ACCESS_BLOCKED 适用性 + 实际尝试回执 + 终态属技术类（`:164-181`）。
- 条件触发两轮：科学缺口（`not_reported/not_publicly_disclosed/conflicting`）才要求恢复证明；`gates/exhaustion.py:422` `information_gain_rounds ≥ 2` 且连续递增（`:733-738`）；`sources/retries.py:191-200` 饱和 = 最近两轮均无门槛相关增益且 `strategy_signature` 不同；`retries.py:202-214` `add_round` 拒绝重复策略签名（“重复相同查询、标识符和访问方式不算新策略”的直接实现）。
- 网络错误≠真实无数据：`retries.py:155-182` 轮次饱和要求全部终态回执为 content_acquired/not_found；`:385-407` 可重试技术故障必须先完成 ≥3 次带真实退避的同路径重试（`SamePathRetryAudit` 校验实际间隔 ≥ 计划退避、首试不得伪造退避）；技术缺口必须绑定独立技术诊断且不得复用科学 not_found 证明（`exhaustion.py:582-592`）。
- 逐缺口绑定与反篡改：复核输入摘要由缺口内容确定性派生、结论必须精确绑定（`exhaustion.py:477-482`）；路线回执/尝试数/访问方式/终态全部由实际回执派生，调用方不得自报（`:651-687`）。
- 复现：`uv run pytest tests/integration/test_double_exhaustion.py tests/integration/test_route_recovery.py tests/integration/test_v13_closure_recovery.py -q` → 24 passed，含 `test_two_saturated_recovery_rounds_are_required`、`test_technical_failure_cannot_become_scientific_absence`、`test_access_blocked_conclusion_requires_technical_diagnosis`、`test_research_package_gate_readiness_rejects_same_strategy_or_network_failure`。

需 Codex 裁决的语义框架（见问题节 Q1、Q4）：`reported_zero` 未纳入恢复触发集；包级 `assert_gate_ready` 硬编码恰好第 1、2 轮。

**G06 publication 分类 + manual-supply 单次中断 — PASS**

证据：
- 版本化分类：`ingestion/publication_gate.py:17-39` 必需类 = primary_result / extension_primary_result / key_safety_or_long_term；排除类 = review / ad_hoc / irrelevant_exploratory，与 v1.3 §5.2 一致。`:135-160`：模型建议与规则不一致或 boundary 状态必须携带独立复核 + 干净上下文；`rejected` 不得通过必需分类。
- 单次中断：`:254-303` `ManualSupplyGate.user_response_count: Literal[0,1]`；`record_user_response`（`:305-346`）重放/二次追问抛“同一快照的 manual gate 不能重复询问用户”；三分支精确对应 v1.3 §5.2 —— file_received→accepted；不可得+官方证据足够→unavailable+强制中文限制说明；不可得+核心不可答→unavailable+`evidence_insufficiency_page`；且“用户响应前不能发布限制或证据不足页”。
- 一快照一 gate：`:380-395` `ManualSupplyLedger` 拒绝同快照第二个 gate；请求对象（`:181-196`）完整携带产品/试验、登记号、DOI/PMID、精确标题、阻断字段、已尝试路径、原文链接、唯一投递目录、最小用户动作、受影响报告清单；`to_markdown`（`:348-377`）按合同渲染用户可见 Markdown。
- 受影响报告粒度：gate 与 request 均带 `affected_reports`，不是全局暂停。
- 复现：`uv run pytest tests/integration/test_v13_publication_gate.py tests/integration/test_double_exhaustion.py -q` → passed（含分类分歧必须独立复核、单次响应、二次 gate 拒绝三个负向用例）。

**G07 原地重命名 — PASS**

证据（`ingestion/manual_inbox.py`）：
- 前置映射回执：`accept()` 先 `_append_manual_mapping`（`:1451-1488`，写原名、SHA-256、DOI/PMID/登记号、目标文件名、目标相对路径、碰撞检查结果），成功后才 `os.replace`（`:1623-1627`）——同目录原子改名，无复制、无移动、无字节改写。
- 碰撞失败关闭：`:1565-1582` 目标规范名已存在时写入 conflict 映射（含现有文件摘要）后抛错拒绝覆盖；历史归档漂移守卫 `:1586-1606`。
- 身份绑定：`_match_guard`（`:1249-1274`）要求请求标识符与文件内容标识符有交集，且 DOI 命中或标题核对通过；与其他活跃请求自动比对防一文件双收；登录/错误页、不可读、错附件按摘要隔离（`scan_and_process_inbox` + `_quarantine_file`）。
- 幂等重放：ACCEPTED + 同摘要 → no-op，不重新改名、不删除用户文件（`:1505-1509`）。
- 唯一投递目录：`DownloadRequest._inbox_directory_is_project_relative`（`:232-239`）强制 `evidence/manual-inbox/{request_id}` 一一对应。
- 复现：`uv run pytest tests/integration/test_manual_inbox_in_place.py tests/integration/test_manual_inbox_recovery.py tests/integration/test_user_filename_auto_rename.py -q` → passed。决定性测试 `test_accept_renames_the_existing_inbox_file_without_copying_or_changing_bytes` 前后对比 `st_ino` 与字节 SHA-256，证明同一 inode 原地改名。
- 边界澄清（建议写入验收说明）：`accept()` 同时调用 `add_source_version`（`:1532-1552`）把内容登记进项目内容寻址证据库——这是 §4.3 `evidence/raw/<sha256>/` 架构的必然动作；“不复制、不归档”约束的是用户投递目录中的用户文件处理（G07 缺陷旧行为正是“复制进证据库后删除原文件”，现原文件保留且原地改名），二者不矛盾，但应在 G07 验收记录中显式写明以免后续误改。

**G08 B 类语义归并 + 确定性守卫 — PASS**

证据（三层职责已厘清）：
- 运行时守卫（真正执法点）：`renderers/portal/report_b.py:2771-2832` `_semantic_group_key` —— efficacy/safety 行的分组键覆盖：临床构念、统计形式、单位、人群语境、时间带，外加 semantic_definition、semantic_direction、semantic_estimand（估计目标）、semantic_denominator（分母口径）、semantic_analysis_set（分析集）、semantic_analysis_form、semantic_instrument_or_scale（量表/仪器）——即 v1.3 §8.2 拆分轴全集；任一轴不同即拆成独立小组（小多图），未知轴以 `*-not-reported` 哨兵参与比较（已报告 vs 未报告不相等 → 拆分，方向失败关闭）。
- 近窗共框：时间带函数 `:840-844` 48–56 周归入 `around_year_1`（约1年），48 与 50 周同带共框；版本化时间窗策略 `policies/timepoints/compatibility-v1.yaml`（week-52 窗 [48,56]，规范值 52）命中非规范值时输出中文差异标签（`reports/b/contracts.py:951-959`“实际时间点为第 48 周，归入第 52 周附近”）——共框且标注，不是无差别合并。行级 `actual_timepoint` 原值保留并在行标识/折叠表中可见。
- 类型化合同（模型辅助裁断的确定性面）：`reports/b/semantic_contract.py:126-171` `compare_clinical_constructs` 九轴（构念/定义/方向/单位/估计目标/分母/分析集/分析形式/量表）逐对比较 + 近窗 ±2.0 周：超窗必拆、窗内有差异必附中文说明；`assert_clinical_construct_compatible` 任一对不兼容即抛错（模型只能提议分组，守卫一票否决）。
- 复现：`uv run pytest tests/reports/b/test_v13_semantic_contract.py tests/reports/b/test_r13_semantic_grouping.py tests/reports/b/test_endpoint_compatibility.py -q` → 29 passed。关键断言：48/50 周兼容共框且带注记；量表版本不同（EASI v1.0 vs v2.0）抛 `ClinicalSemanticError`；方向/估计目标/分母/分析集/分析形式逐轴拒绝合并；估计目标不同 → portal 分成 2 组。

两项非阻断发现：
- **双实现漂移风险（P2）**：`semantic_contract.py` 的九轴比较器目前只被自身测试引用；portal 实际执法靠 `_semantic_group_key` 的字段等值（`BUBBLE_PRESETS` 是唯一被 portal 引入的符号）。两套守卫语义一致但机制不同，未来任一侧加轴即漂移。建议 portal 分组键改为调用类型化比较器（或在合同测试中增加“两实现对全部九轴给出相同判定”的等价性测试）。另：portal 层对分母口径、量表两轴的拆分行为尚无直接单测（只有估计目标拆分有）。
- **基线人群归并（见 Q3）**：`test_r13_semantic_grouping.py:292-317` 断言“全分析集”与“来源报告基线/相应分析人群”合并为一组且组标题“基线 · 年龄 · 均值”不含人群限定——未知人群被归一化为 full_analysis_set，原始文本保留在行级但组标题不可见差异。这属于模型辅助映射越权风险。

**G09 B 类气泡预设 — PASS（R2 合同层）**

证据：
- `reports/b/semantic_contract.py:196-266`：恰好三个 preset（疗效×总体安全性/大小=治疗组样本量；疗效×严重风险/大小=有效分析集规模；获益持续性×停药风险/大小=长期暴露量），与 roadmap R3.2 三预设逐字对应；`neutral=True, ranking=False, composite_score=False, recommendation=False` 为 Literal 锁定；横/纵/大小轴互异校验。
- `build_bubble_point`（`:276-309`）：任一轴披露状态非 reported_value/reported_zero → 返回 None（不可绘制，不沉零）；负值抛错；输出强制 `rank=None, composite_score=None`。
- 预设 1 已有完整运行时构建器与测试：`reports/b/pages.py:1821-1856` `build_bubble_points`（疗效信号×安全率、大小=治疗组样本量，不完整行留在矩阵视图不入图）。
- 复现：`tests/reports/b/test_v13_semantic_contract.py::test_b_has_exactly_three_neutral_non_ranked_presets`、`tests/reports/b/test_bubble_area.py` 均 passed；portal 数据载荷含 `bubble_presets`（`renderers/portal/report_b.py:3515`）。

边界声明：预设 2/3 目前只有类型化 schema + 载荷元数据，`src/` 中未发现严重风险图/持续性图的专用点位构建器。G09 差距矩阵的“最小修复”（preset schema/计算/展示）中“展示”未闭合——属 R3/R4 页面交付物；**R3 B 类验收时若仍缺预设 2/3 的图表构建与展示，应按差距矩阵判不通过**。

---

**跨切成功标准 5：单报告分支直达科学 QC — A：PASS；B/C：VETO（F-CROSS-1）**

已验证（A）：
- `application/run_service.py:1213-1216` 新鲜研究包路径强制 `contract.reports == ("A",)`，随后 gate→snapshot→scientific_qc→analyze→format 全部以 `report_kind="A"` 逐报告驱动（`:1345-1382`），不要求 B/C 视图；QC 结论绑定独立复核者身份与候选快照摘要（`:1355-1370`）。测试链（`tests/integration/test_no_draft_when_blocked.py`、`test_no_draft_after_scientific_qc_rejection.py`、`test_scientific_qc_gate.py` 等）通过。

未达成（B/C，阻断）：
- 默认运行路径 `run_service.py:1796-1898`：gate/recovery 仅对 `kind_value == "A"` 执行，B/C 直接标 "skipped" 并 `continue`——B/C 报告在当前确定性执行器中没有通往 scientific QC 的证据链。
- 多报告数据包路径 `run_service.py:1500-1520`：仅运行 format 节点，然后直接写 `"report_states": {kind: "snapshot_locked"}` 运行时元数据——绕过 gate/快照/独立 QC 直接宣称快照锁定。若该路径的产物被用作验收证据，即构成“生产者自行宣布接受”的合同违例（v1.3 §4.1）。当前它作为 fixture 预览/开发工装存在，负向矩阵也禁止以 fixture 替代真实验收，但它与状态机的字面冲突必须在 R3 接线时清除（B/C 接入证据链后此路径必须停止伪造状态标签）。
- 图合同歧义：`graph/typed_skills.py:203-209` scientific-qc 节点声明输入 `("ReportAView","ReportBView","ReportCView")`，而 §3.3 禁止 A/B/C 分析互相依赖；宿主适配器读此图会推出“QC 需要全部三个视图”。最小修正：把输入改为逐报告元组 `("ReportKind","ReportView")`（或拆为 qc-a/qc-b/qc-c），并加负向测试“图合同不得要求未选报告的视图作为所选报告 QC 的输入”。

按成功标准的字面（“单个请求的报告分支可达科学 QC”），当前只有 A 分支成立 → 本项判 **VETO**；它不是 G01-G09 某一行的合同缺陷，而是 R2→R3 接线进度缺陷 + 一处图合同文字缺陷（F-CROSS-2）。worker_03 与提交历史（`bb27ec9 test: accept complete report A vertical slice`）表明这是已知的 A 类垂直切片阶段，故修复路径是接线而非返工。

## Evidence And Assumptions

**确定性门（当次复现，2026-09-05）**
- `uv run pytest tests/unit tests/contract -q -p no:cacheprovider` → **860 passed**（声明快门的 unit/contract 范围）。
- `uv run ruff check src tools tests` → All checks passed。
- `uv run mypy --strict src/ci_workflow` → no issues in 175 files。
- 焦点集成集：double_exhaustion + route_recovery + v13_closure_recovery + v13_publication_gate（24 passed）；manual_inbox 三套 + B 语义三套（29 passed）；competitor_universe + scientific_qc_isolated_veto + partial_delivery + no_draft 三套（84 passed 中 1 失败，见 F-T-1）。

**观察到的失败（全部为陈旧测试，非生产缺陷）F-T-1**
- `tests/integration/test_capability_preflight.py` 4 failed：测试选 `("html","pdf","pptx")` 等输出，被 v1.3 的 `OutputName=Literal["html"]` 正确拒绝——生产代码行为正确（HTML-only），测试是 v1.2 时代遗留。
- `tests/graph/test_partial_delivery.py` 1 failed：`optional_formats=("pptx",)` 被 `DeliveryContract` 正确拒绝。
- `tests/graph/test_pptx_confirmation_interrupt.py` 2 failed、`tests/integration/test_selective_capability_blocking.py` 2 failed：同类 pptx 遗留。
- `tests/integration/test_download_request_transitions.py` 1 failed：测试在收件目录无实际文件的情况下调用 `accept()`，被 G07 新守卫“接受必须引用收件目录中实际存在的原文件”（`manual_inbox.py:1526-1527`）正确拒绝——守卫正确，测试需迁移到原地语义。
- 与 worker_03 报告一致："Existing broad tests still contain pre-v1.3 expectations… not evidence that the current HTML-only contract is incorrect"。这些测试都在声明快门（unit/contract）之外，但 R5/R6 的 Phase 0–10 全量回归前必须迁移或显式排除，否则全量套件永远不可绿。

**关键假设**
1. G01-G09 的验收意图以 `reviews/codex_v13_implementation_gap_matrix_20260904.md` 行文本 + v1.3 对应条款为准（执行上下文声明其为“已验证的 R2-R4 RED→GREEN 路由清单”）。
2. R2 范围 = 研究/证据合同层；B/C 证据链接线、门户视觉、三宿主属 R3-R5（A 类垂直切片是当前批准的中间态）。
3. 运行测试产生的系统临时目录写入与既存 `__pycache__` 不构成“修改文件”。

**不确定性标注**：G03 的声明式独立上下文在恶意宿主下的强度未验证（依赖下游摘要分离，见备注）；预设 2/3 是否已有我未检索到的 R3 分支实现（当前树内未见）；`BubblePoint` 在 A 类报告（`reports/a`）中另有历史气泡逻辑，我未审计 A 类气泡是否已与 B 三预设隔离（G09 差距矩阵提及“历史 A 气泡逻辑不能替代 B 合同”，B 侧已隔离，A 侧建议 Codex 复核）。

## Risks, Gaps, And Verification Needs

**F-CROSS-1（VETO 级，需修复后才能过 M3 出口）**：B/C 报告在确定性执行器中不可达科学 QC；数据包路径直接标注 `snapshot_locked`。最小修正：在 `run_service` 默认路径为 B/C 接入 gate/recovery/snapshot/scientific_qc 逐报告节点（复用现有 `_run_node(node_id, kind, ...)` 机制与 A 同构），移除数据包路径的状态伪造标签（改为 `queued` 或删除标签）。决定性负向测试：构造 reports=("B",) 的项目 + 无 B 研究输入 → 不得出现 `snapshot_locked`/`delivery_ready` 任何标签或 HTML 产物；B 研究包齐备 + QC veto → 无 draft、状态为 evidence 决议态。

**F-CROSS-2（合同文字缺陷，小修）**：`typed_skills.py` scientific-qc 输入三元组。最小修正见上；负向测试 = 图合同断言任一 (kind, view) 子集即可满足 scientific-qc 输入。

**F-G04-1（P2）**：闭包收敛证明不可表达（详见 G04 节）。

**F-T-1（P2，测试债）**：10 个陈旧 pre-v1.3 集成/图测试失败（清单见证据节）。它们在快门外，不构成假绿，但阻塞 R6 Phase 0–10 全量回归；需按 HTML-only 合同迁移或显式归档排除，且不得以“跳过”冒充修复。

**F-G08-1（P2，医学语义风险）**：基线未知人群归一化为 full_analysis_set 且组标题不显示人群（详见 Q3）。若 Codex 判定必须拆分/显未知态，最小修正 = 未知人群映射为独立 `population_as_reported` 语境（不与 FAS 共框），并在基线组标题追加人群限定。

**F-G08-2（P2，漂移风险）**：类型化九轴比较器与 portal 分组键双实现（详见 G08 节）。

**F-G09-1（P3→R3 阻断）**：气泡预设 2/3 无运行时构建器（详见 G09 边界声明）。

**F-G06-1（P3 文案）**：`ManualSupplyGate.to_markdown` 首行向用户暴露内部 `snapshot_id`（`publication_gate.py:354`）。manual gate 属项目内中文补件说明而非报告页面，暂不违其合同，但建议改用中文序号+日期等用户可读标识。

**验证需求（Codex 侧）**：1) 复现 F-CROSS-1：`grep -n "skipped" src/ci_workflow/application/run_service.py`（1830/1866 行附近）与 `:1514` 的 `snapshot_locked` 标注；2) 复现 F-T-1：跑上文失败测试清单；3) 对 B/C 语义轴拆分补 portal 层直接单测（分母/量表两轴）。

## Recommended Next Step

**给 Codex 的四个有界问题（各附安全临时路径）：**

- **Q1（G05 语义裁决）**：`reported_zero`（有明确零值原文+定位）当前满足门槛且不进两轮恢复机制（`gates/exhaustion.py:66-68` GAP_STATES 不含它；`gates/models.py:690-696` 仅强制零值原文）。v1.3 §5.4“关键缺失或异常零值必须两条不同替代恢复检索”中的“异常零值”是否要求：**(a)** 维持现状（零值原文+干净上下文科学 QC 即可），或 **(b)** 为关键单元的 reported_zero 增加类型化异常零恢复触发（进入 GAP_STATES 或新增谓词）？这决定 G05 的“按条件触发”边界。安全临时路径：先按 (a) 接受 R2，把 (b) 记为 R3 前的 RED 项。
- **Q2（F-CROSS-1 时点）**：确认“B/C 单分支直达科学 QC”是 R3 出口条件而非 R2 出口条件（当前 A 垂直切片 + G01-G09 合同层即可收 R2），还是要求本轮即修？若后者，F-CROSS-1/2 的最小接线契约我已给出，可转执行包。
- **Q3（G08 基线人群）**：`来源报告基线/相应分析人群 → full_analysis_set` 的归一化是否可接受为受控词表默认值（原始文本保留在行级/折叠表），还是必须按 v1.3“分析集不兼容必须拆分”改为独立未知语境并在基线组标题显示人群？（医学语义裁决，建议医学经理复核一例。）
- **Q4（G05 合同对称性）**：包级 `assert_gate_ready` 硬编码恢复轮恰为 {1,2}（`research_package.py:528-530`），而引擎 `RecoveryHistory` 支持 N 轮、以最近两轮饱和判收敛。若某缺口第 1/2 轮有增益、第 3 轮才饱和，包按现状会被拒绝（失败关闭）。是否有意为之（两轮即证据终点）？若非，最小修正 = 校验改为 `set(rounds) ⊆ {1..N} 且包含饱和证明`。

**建议的下一步顺序**：Codex 先裁决 Q1–Q4 → 以 RED 测试固化 F-CROSS-2（图合同修正）与 F-G04-1（收敛证明）→ R3 开工首项即 F-CROSS-1 的 B/C 证据链接线（复用 A 同构节点）→ 同批迁移 F-T-1 陈旧测试 → B/C 门禁接线完成前，不推进任何真实 B/C 门户验收，更不出 M3 之后的信号。

本报告未修改任何文件；全部结论绑定当前字节与可复现命令，最终接受权归 Codex。
