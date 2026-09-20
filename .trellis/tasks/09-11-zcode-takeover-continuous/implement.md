# 实施记录

## 2026-09-11 会商与恢复（已完成）
- 重锚：HEAD bb27ec9 + 八哈希一致。
- 恢复被中断验证：B 领域+浏览器 278 绿；gate 6/6（修交接文档 historical 标记后）；integration+B 门户 818 绿（修 three-report-complete 夹具 matrix row_id 唯一化 + catalog/binding/digest 级联）。
- 会商（packets/2026-09-11-takeover-review/）：Reviewer-A gpt-5.6-luna P3 终审（第二轮修复成立 + 4×P2 护栏）；Reviewer-B deepseek-v4-flash 架构评审（F1 科学视图层死代码 P0 等 10 项），主线程逐项核验。

## 2026-09-11 P3.0 护栏（RED→GREEN）
新增 tests/reports/b/test_full_pool_adjudication_guards.py（7 项：子集拒绝/孤立提案拒绝/未知域拒绝/全池裁决合并/域不改写/uncovered 隔离/行为钉住）。
report_b.py：
- 新 `_POOL_ADJUDICATION_DOMAINS` + `_adjudicate_full_pool()`（全池唯一裁决入口：域白名单、孤立提案拒绝、跨域提案拒绝、分域递归）+ `_assert_page_fallback_only_uncovered()`。
- 主装配 3690 行改走 `_adjudicate_full_pool`。
- `_groups_for_page` 的 product-trial-profiles 分支删除域拆分重裁决：真实域子集直接 raise；profile-only 保持状态矩阵；generic-only 保持返回空。
- `_records_with_semantics` 拒绝静默改写已有域标签。
- `_render_page_context` 对 uncovered 记录执行 `_assert_page_fallback_only_uncovered`（真实域且无 _synthetic/_empty_state 标记 → raise）。
- `_synthetic_status_records` 两分支行加 `_synthetic=True`（digest 不受影响， "_" 前缀不入摘要）。
- 旧测试 test_descriptive_domains_honor_veto... 原把 baseline 行喂 disposition/matrix 页依赖静默改域——违反新合同，改为去域标签后传入（真实数据流同构）。
- 超越说明：tmp/semantic-independent-w1RHFS/test_independent.py::test_product_page_is_projection_of_global_groups（第一轮反例）被正式超越：不变量由 tests/browser/test_b_semantic_proposals.py::test_dossier_uses_global_scientific_partition（真实渲染路径）+ 新护栏测试承担；tmp/ 原文件保留为审阅证据不改。
- 定向结果：护栏 7/7；B 领域+语义浏览器 285 绿；两改动源码 Ruff/strict-mypy 绿。完整 integration/gate 回归进行中。

## 2026-09-11 P3.0 补充：护栏捕获真实档案完整性缺陷（重要）
uncovered 隔离护栏在真实 PNH 夹具上触发，暴露 Reviewer-A 与主线程初判均未发现的缺陷：
- detail_pool 的处置记录来自 `_page_records('disposition-overview')`（带元素过滤），adherence/participant-flow/loss-exit/screen-failure/rescue-treatment/prohibited-medication/plan-deviation 七个处置子页的记录（依从性等）从未进入全池裁决，一直走每页静默重分组；
- 更严重：**产品/试验档案页从 detail_pool 筛选，因此完全缺失这些处置观察**——档案完整性缺口，不是纯分组问题。
修复（report_b.py）：
- 新增 `_disposition_pool_records()`：池消费未过滤的全量处置记录，处置子页成为真正的元素级投影；
- `subgroups-supporting-evidence` 页的 supporting 域入池（`_POOL_ADJUDICATION_DOMAINS` += supporting；`_semantic_domain_for_page` 该页返回 "supporting"，消除 efficacy 静默改写）。
- 验证：PNH 23 页完整渲染（adherence 页有分组）；档案页现含依从性观察。B 领域+语义浏览器 285 绿；Ruff/strict-mypy 绿。完整 integration+browser 回归重跑中。

## 2026-09-11 下午批次：P3.5-1 接线 + P2 PubMed 路线 + F4/F8/F6

### P3.5-1 科学视图层接线（F1 第一步，主线程）
- 新增 `src/ci_workflow/reports/b/__init__.py`（F3：包入口，a/c/common 均有而 b 缺失）。
- 新增 `src/ci_workflow/reports/b/portal_science.py`：`efficacy_science_partition(records)` —— 门户行→EndpointObservation→`match_endpoint_compatibility`（版本化 policies/endpoints+timepoints YAML）→`EfficacyFactRow`→`build_efficacy_views`，按 single_timepoint 视图产出科学初始分桶；未命中政策/缺语义/组别角色不支持的观察保留 unmatched 描述性路径并带差异标签，不丢弃。
- report_b.py `_cross_trial_groups` 增加 `science_partition` 参数：efficacy 页初始分桶来自科学层，unmatched 才走文本键；longitudinal 页保持同试验系列语义（描述性、P3.0 护栏已隔离）；safety/subgroups 暂保持文本键（Phase B）。
- F2 类型化：ReportBPortalData 八个视图字段 `Any|None`→`Mapping[str,Any]|None`，schema 漂移在边界暴露。
- RED→GREEN：tests/reports/b/test_science_partition_consumption.py 4 项（政策近窗裁决 48/50→week-52-v1、unmatched 守恒、渲染器服从科学分区 mock 正反、真实渲染消费科学层 spy）。
- 验证：B 领域+语义浏览器 289 绿（285+4，零行为波及）；两文件 Ruff/strict-mypy 绿。

### P2 PubMed 真实路线（Worker-C：deepseek-v4-flash，受控写集）
- 派发/验收记录：packets/2026-09-11-p2-routes/（prompt、events、report、acceptance）。
- 交付：sources/connectors/pubmed_fetch.py（424 行，stdlib、禁重定向、超时/限流/坏 XML 分类、CAS、游标/预算、total 一致性、诚实 incomplete）+ `research fetch-pubmed` CLI + 45 项合成 transport 测试（主线程亲跑通过）。
- 真实网络全链 smoke（主线程）：nemolizumab AND prurigo nodularis → search 1 页 + efetch 1 页 + 99 条真实记录（PMID 42696343 等）；101 vs 99 不一致诚实置 incomplete；no_records/incomplete 语义正确。
- 写集核验澄清：git status 中其他 cli 测试文件为暂停前既有 WIP（mtime 9月4-6日 + 暂停索引佐证），非越界。
- 相邻合同更新：CLI 表面计数 15→16（test_cli_surface_stays_sixteen，注明新增命令与验收）。
- Worker 测试文件 1 处 ruff UP012 由主线程 --fix（45 项仍绿）。

### F4 闭包门收紧（主线程）
- domain/research_package.py RouteReceipt：`not_applicable` 必须携带适用性依据（diagnostic 非空），否则拒绝——裸字符串不再让必查路线闭包门变绿。
- RED→GREEN：tests/contract/test_route_applicability_contract.py 3 项；相邻 submission/source-binding 78 绿。

### F8 资产护栏（主线程）
- tests/browser/test_portal_shell.py 新增 `test_all_shared_portal_assets_match_repo_and_manifest`：5 个共享资产双副本字节相等 + manifest sha 按模块内发货副本校验。

### F6 README/权威一致（主线程）
- README.md 重写为当前合同（HTML-only、开发候选、无排除格式宣传、无 Phase 0 状态）。
- tests/contract/test_readme_scope_contract.py：README formats 声明 == package-manifest.package.formats；无过时阶段标记。

### 本批次回归终态
- integration+B 门户浏览器：862 通过/1 失败（CLI 计数合同）→ 计数更新后该文件 20 绿。
- 完整 gate：ruff（修 UP012 后全绿）→ 最终 gate 重跑进行中（结果记入检查点）。

## 2026-09-11 晚间批次：P3.7-core 已批准归并合同（构建-测试-优化 LOOP 第二轮）

### 变更（先 RED 后 GREEN）
- `reports/b/semantic_grouping.py`：新增 `ApprovedSemanticMerge`（merge_id + 候选提案 + `SemanticAdjudicationReceipt` 绑定；构造期整体再校验防 model_copy；提案必须 compatible、回执 decision 必须 compatible、观察对一致）。`proposed_semantic_buckets` 新参数 `approved_merges`：**候选正向提案不再授权合并**（降级为确定性路径）；否决照旧；描述性域拒绝；重复/摘要漂移拒绝。
- `report_b.py`：`ReportBPortalData.semantic_adjudications` 字段 + `_groups_for_page`/`_cross_trial_groups`/`_adjudicate_full_pool`/`_render_page_context`/渲染循环全链穿透；池级孤儿/跨域/摘要校验。
- 测试：`test_approved_merge_contract.py` 9 项（候选不合并/批准合并/否决免批/陈旧摘要拒绝/模型绑定/receipt model_copy 伪造拒绝/页面消费/描述性拒绝/安全性可达 + 外层伪造池级拒绝）；既有正向用例升级为已批准形式；`proposal_data()` 净化为纯候选助手（合并套件在专用 fixture 显式加批准并整体重校验），消除两处陈旧裁决陷阱。

### Reviewer-D 终审（gpt-5.6-luna，read-only；packets/2026-09-11-p37-approvals/）
无 P0/P1。Q1 无批准旁路；Q3 "看似无批准也合并"的确定性反例属合同允许路径（完整语义+同桶+守卫，与既有测试一致）；Q4 否决优先于批准=保守欠合并，符合当前政策。三项 P2 已全部修复：
1. 池级入口对外层 merge 整体重验（防 model_copy 伪造）；
2. safety 页分支漏传 adjudications（已传 + 回归测试）；
3. matrix/baseline/disposition 描述性域现在显式收到并拒绝批准归并（不再静默忽略）。
P3（外层伪造攻击测试）已补。

### 回归终态
B 领域+语义浏览器 298 绿（289+9）；integration+浏览器+gate 最终字节重跑进行中（结果记入检查点）。tmp 反例：re-review 8/8 恢复通过；第一轮文件 2 处失败均为结构性超越（product_page 投影测试、cross_page_negative 的档案页入口——P3.0 护栏即其意图的强制形式），tmp 原文件保留为证据不改。

### 诚实边界
已批准归并的**生产者**（capabilities/semantic_review.py 工作项发射 + 图节点接线 + 真实独立上下文签发）尚未实现——当前批准数据由测试/上游构造，渲染端合同已就位。这是 P3.7 下一步。

## 2026-09-11 深夜批次（LOOP 第三轮）
- kangzhe v5.1 视觉差距评估入册（仓库 v4.4 合同、缺 html_charts/html_interact；五步同步工作流写入 v6 计划 P4）。
- P3.7 生产者：application/semantic_review_task.py（对选择与消费端分桶语义一致 + 提交验证四重绑定）；tests/application/test_semantic_review_task.py 11 项。
- Reviewer-E 终审（packets/2026-09-11-p37-approvals/reviewer-e-last-message.md）"暂不通过"→ 修复 7/8；±2 周硬编码记为 P3.3 首项（与 timepoints YAML 的 48–56 窗存在两套机制不一致）。
- 回归：314 绿 + gate 6/6 + Ruff/mypy 绿。

## 2026-09-11 夜间批次（LOOP 第四轮）：P3.7 流程接线
- cli.py：`research semantic-review`（--emit/--submit 互斥动作组；发射幂等原子；提交经 validate_semantic_review_submission 后 store_semantic_adjudications 三重绑定落 state）。CLI 计数 16→17。
- report_b.py：导出 `semantic_review_domain_inputs`（efficacy/safety 观察池）与 `semantic_review_buckets_for`（efficacy=科学分区+孤立桶、safety=渲染端同款文本键）；`build_report_b_artifact(extra_adjudications)` 注入（双源拒绝，注入后摘要含裁决）。
- semantic_review_task.py：`store/load_semantic_adjudications_for_render`（项目/报告/载荷 sha256 绑定，漂移失败关闭）。
- run_service.py：`_render_html_b` 渲染前加载注入。
- 测试：tests/integration/test_semantic_review_flow.py 2 项（CLI 往返含伪造拒绝与幂等；loader 绑定漂移拒绝）。
- 回归：B+application 314 绿；integration+浏览器 865 绿；gate 6/6（ruff import 顺序修复后）。

## 2026-09-11 末班（LOOP 第五轮）：P3.3 时间政策统一
- contracts.py：TimepointCompatibilityRule.comparison_tolerance_weeks（默认 2.0 + 校验）。
- policies/timepoints/compatibility-v1.yaml v1.1：5 规则显式容差。
- semantic_contract.py：compare_clinical_constructs 时间段重写（双侧规则命中+同规则+容差内；未命中/异规则拒；理由带政策/规则/容差身份）；time_policy_identity() 公开审计身份；唯一命中冲突保守不可比；lru_cache 默认政策。
- semantic_grouping.py：semantic_row_digest 政策前缀纳入时间政策身份（升级即失效重裁）。
- semantic_review_task.py/cli.py：任务 policy_version 用真实组合身份（去除摘要前缀伪造）。
- RED→GREEN：tests/reports/b/test_versioned_time_policy.py 7 项（窗外拒/同窗容差内可比/超容差拒/政策容差可调/异规则拒/政策文件版本断言）。
- Reviewer-F 终审 3 P2 当日修复、1 P3（_time_band 展示带）记档 P3.5-4。
- 回归：323 + 865 + gate 6/6。

## 2026-09-11 深夜二班（LOOP 第六轮）：P3.5-3 成员裁决真源入科学层
- portal_science.py：adjudicate_comparable_membership（桶键注入；efficacy 科学分区+unmatched 文本聚合、safety 文本聚合；complete-link 成员输出）+ validate_full_pool_inputs（池级五重校验搬移）。
- report_b.py：_cross_trial_groups 可比域只消费科学成员；_dress_membership_groups 展示组装提取（描述域路径共用）；_adjudicate_full_pool 校验委托；science_partition 死参数移除。
- 测试：test_pool_membership_science.py 7 项；P3.5-1 spy 迁移至成员接缝。
- 记档：safety 视图集消费/物理拆文件/_time_band 观察期政策化（P3.5-4 剩余）。
- 回归：7/7 + 330 + 865 + gate 6/6。

## 2026-09-11 终班（LOOP 第七轮）：PNH 竖向首验启动
- 真实入口链验证：project create（PNH A/B/C）→ yaozh skipped → capability preflight（需 CI_WORKFLOW_INDEPENDENT_CONTEXT=1 + --host local）→ project run --resume 发射 9 路线研究工作项。
- 缺口：G7-1 独立上下文声明无 CLI/SKILL 指引；G7-2 中国路线执行器缺失 vs 闭包门；G7-3 submit 严格校验工程量。
- 产物：packets/2026-09-11-pnh-vertical/{runbook.md, emitted-work-item.json}。

## ⏸ 2026-09-11 23:18 无损暂停（LOOP 第十一轮中点）
- 位置：审计包过严格校验（57,908B，sha256 55561f26…）；submit 碰"报告集合与项目合同不一致"（A,B,C 项目 vs A 切片），未解决。
- 已修合同细节：双层来源形状（ResearchSource vs SourceCapture）、扩展回执轮次键集全等、维度回执全绑定、A 载荷规范路径+universe_product_ids。
- 恢复：按检查点顶部"下一安全步骤"（A-only 新项目 → 入口链 → /tmp/pnh-proj-path.txt 重定向 → build_pnh_audit.py → submit → run）。全部身份哈希与现场路径已录检查点。无后台进程；未提交未清理。

## 2026-09-11 深夜续：恢复执行至科学复核红线
- A-only 重建+submit 推进（日期精度合同修正）；scientific_review 必填触发真实独立复核。
- Reviewer-G 判 rejected（非产品实体/资产拆分/状态覆盖/区域错误/联合治疗丢失/样本量排除）；不伪造 accepted，六项修复清单入 runbook，第十二轮执行。
- G11-1：TrialRow 单 product_id 无多对多。

## 2026-09-12 凌晨：R12-R14 两轮修复+三次复核循环
- G/H/I 三会话独立复核均 rejected（每次发现真实且收敛）；R12 六项+R13 归一/复合名+R14 预处理药/复数/BIOLOGICAL/默认区域修复后 52 产品/141 试验/260 疗效/86 安全零残留。
- 第四轮四待办入 runbook（lfg316、hrs-5965×2、G11-1 模型演进独立切片、复核数字自文件）。

## 2026-09-12 破晓：R15（过矫）→ J rejected → R16 修复
- R15 全干预注册被 J 判违反创新竞品边界+排序首项错归属；R16：来源顺序主药（NCT02534909→lfg316 ✓）、背景药 11 类黑名单、变体词/双品牌复合归并、result_status 精确化 → 54/135/237/81 零残留。
- G12-1：干预角色结构化分类器（黑名单为过渡）。Reviewer-K 第五会话待终审。

## 2026-09-12 清晨：K 第五判 + R17
- K 确立裁决框架（可披露限制 vs 可修复错误）；R17 五修（同义词/SB12/剂量/斜杠/冒号）→ 46/134/234/80 零残留。Reviewer-L 待终审。

## 2026-09-12 上午：L 第六判 + R18
- R18 四修（ATG 变体/alias v2/borderline 豁免）→ 44/135/239/81；sirolimus/levamisole 恢复+待审标记。Reviewer-M 第七会话待终审。

## 🏁 2026-09-12 正午：PNH A 门户真实生成
- M accepted → scientific_review 真实签发 → RESEARCH_PACKAGE_ACCEPTED（三关：日期/事实绑定/v1 版本）→ run 完成 → 55 页 A 门户（44 产品档案，真实产品名验证）。项目首个真实门户。

## 2026-09-12 深夜（LOOP 第二十轮）
- B 包构建脚本+政策 7 个 PNH 终点族；458 错修至结构碰撞 G20-2（终点分类 177/239、时间窗数值 27/239）+G20-1（schema Literal）。两条处置路径入 runbook 待裁决。

## 2026-09-13 凌晨：AB 双包 ACCEPTED + B gate 两轮恢复合同首触
- 重建脚本组修复（URL 同源/作用域唯一/分类器兼容结果/真实分母/零值原文/投影镜像）→ AB 双包 ACCEPTED（持久化 runs/pnh-vertical/ab-v2）。
- A 门户 55 页重生成；B gate 卡 6 unit→G22-1 两轮恢复路径查明（RecoveryRound schema + CAS baseline 数据源）。

## 2026-09-13 凌晨二：AB v2 ACCEPTED + G22-2 精确化
- ab-v4 干净项目全链：B 包 v2（235 基线行+recovery_rounds+anchor concepts）→ AB ACCEPTED → A 门户 55 页重生成。
- G22-2：gate 6 unit 满足判定语义需 gates/evaluator.py 专项分析（下轮首项）。
- 经验：替换已接受包需补件门；迭代用新项目目录；hash 后缀不可跨进程比对。

## 2026-09-13 持续：ab-v6 AB ACCEPTED + A 55 页
- B 包 v3 (ldh/hemoglobin → demographics 域推迟) → AB 双包 ACCEPTED → A 门户 55 页。
- B 门户仍因 severity anchor gate 阻塞（已知 G22-2 推迟项）。

## 2026-09-13 最终状态：B gate 正确阻塞，恢复合同等待宿主执行
- B gate 返回 blocked——6 unit 因登记数据不满足完整证据门槛被正确阻塞
- 恢复工作项 b-evidence-recovery.json 已创建，等待宿主差异化恢复
- A 门户 55 页正常生成；B/C 需恢复数据补全后生成
- 这不是代码 bug——是证据门槛与登记数据现实之间的真实鸿沟

## 2026-09-13: B gate 深度诊断——GateSpec critical unit 需 comparison 绑定
- severity anchor 修复生效(9条) → 但 GateSpec 的 b_treatment_control_identity/b_effect_difference_support 等 critical unit 要求 comparison 类绑定，登记数据(single_arm)无法满足 → 这是 GateSpec 定义与登记数据现实的结构性鸿沟
- 需要下一步: GateSpec 定义调整(将 comparison unit 改为 extension) 或补充 comparison 绑定数据

## B gate 最终诊断
GateSpec B-v1 的 comparison critical unit 阻塞 B 门户。需 GateSpec 定义调整（demote comparison units to extension）或补充 comparison 绑定。所有其他修复已完成。

## B gate 最终诊断（2026-09-13）
- GateSpec B-v1 comparison critical unit 阻塞 B 门户。PNH 登记试验全为 single_arm，无法产生 comparison 绑定。
- 需 GateSpec B-v1 定义调整（demote comparison units）+ FreshBResearchContent 校验链同步。
- A 门户 55 页正常。全部材料和脚本持久化。

## 2026-09-13: G22-2 深度分析完成——GateEvidenceBinding context fields 映射缺口
- build_b_gate_bindings 创建的 GateEvidenceBinding 需要所有 required_context_fields 非 None
- 当前 sample_size 行的 denominator 已修复，但 age/severity 行的 definition/timepoint 等 context fields 可能仍为 None
- 下轮：检查 _baseline_evidence_binding 或创建 baseline binding 的代码，确认 context fields 映射完整性

## 2026-09-13 最终诊断：B gate 正确阻塞——需要额外恢复来源
GateSpec B-v1 要求每个 trial×group 都有基线/疗效/安全绑定。CT.gov 登记数据天然覆盖不完全（部分试验无 enrollment/LDH/Hgb/sex 数据），导致 gate 正确阻塞。这不是 bug 而是证据门槛合同与数据现实的正确交互。需要补充来源（PubMed/公司公告/监管文件）提供更多基线和结果数据才能满足全覆盖。

## B gate 阻塞精确诊断：safety facts 与 dedup 后 safety_rows 不同步
- facts 循环遍历原始 safety 列表但 safety_rows 只含 dedup 后的行
- 修复：在 safety_rows.append 后同步创建 fact
- 全部其他修复已完成，此为 B 门户生成最后一步
