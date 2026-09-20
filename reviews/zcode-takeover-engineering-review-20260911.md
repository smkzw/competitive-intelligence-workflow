# ZCode 接管工程 Review（2026-09-11）

执行者：ZCode 主线程（GLM-5.3）。方法：现场重锚 → 恢复被中断验证 → 主线程代码审查 → 两个非 GLM 独立审阅节点（gpt-5.6-luna 只读 P3 语义复验；deepseek-v4-flash plan 模式整体架构评审）→ 主线程核验采纳。派发记录：`packets/2026-09-11-takeover-review/`。

## 1. 现场核验（全部通过）

- HEAD `bb27ec9d750cf02fb64da5dfe665b2f4b262922d` 与交接记录一致；八关键文件 SHA-256 全部一致。
- 脏树 1219 条（交接时 1218 + 交接文档），符合交接描述。
- 权威链已读：v1.4 设计、v5 计划、Goal 快照、两次暂停交接、累计检查点。

## 2. 被中断验证的完整重跑结果

| 被中断项 | 暂停时状态 | 本次结果 |
|---|---|---|
| tests/reports/b + browser 语义 | 计数止于修复前 | **278 passed**（9.87s）完整通过 |
| 第二轮反例 tmp/semantic-rereview-a4bUhi | 未完成 | **全部通过** |
| 第一轮反例 tmp/semantic-independent-w1RHFS | 从未在第二轮修复后重跑 | **29 passed / 1 FAILED**（见 §3.1） |
| bash tools/gate.sh 六步 | Ruff/mypy 后 58% 中断 | **5 绿 1 失败**：legacy-references 指向交接文档自身 718 行缺 historical: 标记（文档问题，非代码）；Ruff、strict-mypy 217 源、986 活跃单元/合同、兼容 20、分层 7 全绿 |
| tests/integration + B 门户浏览器 | 164 passed 后中断 | 初跑 **817 passed / 1 failed**；失败根因为夹具身份违约（§3.2），修复后 §4.2 重跑 |

结论：第二轮语义修复本身在有界范围内成立；两个失败都不是科学源码缺陷，分别是遗留文档标记缺失与旧夹具数据违反新身份合同。

## 3. 发现清单

### 3.1 第一轮反例失败：产品页投影不变量（待 Reviewer-A 终审）

`test_product_page_is_projection_of_global_groups` 失败：全局分组 `{third}`/`{first,second}`，但把 product-b 子集直接喂 `_groups_for_page('product-trial-profiles', …)` 得到 `{second,third}`（重分组）。

主线程初判：真实渲染路径已符合合同——主装配 3690 行全池一次裁决，档案页（3770-3797）从 detail_pool 筛选后经 `_project_scientific_groups` 投影；失败反例直接调用底层函数绕过了投影机制。不变量本身有效，验证机制过时，且底层函数仍是"允许子集重分组"的活隐患。Reviewer-A 终审结论见 §5。

### 3.2 夹具身份违约（已定案，已修复）

`three-report-complete` 的 `matrix_view.comparison_rows` 4 行仅 2 个 row_id：`matrix-apply-teae` 同时代表 fixture-product 与 competitor-biologic 两条不同观察。第二轮护栏 `_dedupe_records`（report_b.py:2048）正确拒绝。暂停前最后一次完整 integration 早于第二轮修复，故从未暴露。处置：夹具行 ID 唯一化（`matrix-{fixture|competitor}-{apply|appoint}-teae`），不改任何临床数值，级联更新 catalog/binding-contract/case_digest。护栏不放松。

### 3.3 Reviewer-B 架构发现（主线程已逐项核验）

| # | 发现 | 主线程核验 |
|---|---|---|
| F1 (P0) | **权威科学视图层在生产路径是死代码**：`reports/b` 的 `build_efficacy_views`/`build_safety_views`/`build_matrix_view_state`/`build_endpoint_basis_set` 在 src/ 内零生产调用者（仅测试调用）；出 HTML 唯一路径 `run_service.py:732 → build_report_b_artifact` 不触碰它们；渲染器自带 `_CLINICAL_CONCEPT_GROUPS`、`_semantic_group_key`、`_time_band` 等全套裁决副本。`_project_scientific_groups` 校验的"完整科学视图"来自渲染器自身 3690 行——循环校验，非跨层校验 | ✅ grep 确认零生产调用者 |
| F2 (P1) | `ReportBPortalData.efficacy_views/safety_views` 等五个 `Any` 字段是科学层接入缝上的类型逃生口 | ✅（待改类型化时复核行号） |
| F3 (P1) | `src/ci_workflow/reports/b/__init__.py` 缺失（a/c/common 都有），科学内核是隐式命名空间包 | ✅ ls 确认 |
| F4 (P1) | 闭包门允许 `not_applicable` 路线结果却不要求适用性依据（research_package.py:1019-1031），与"明确不适用必须有适用性依据"冲突 | ✅ 源码确认 |
| F5 (P2) | 缺"渲染器不得裁决"负向合同（缺 efficacy_views 时应失败关闭，当前静默容忍） | 采信（与 F1 同根） |
| F6 (P2) | README.md 进发货包却宣传 PDF/HTML-PPT/PPTX 四格式与 Phase 0 状态，与 package-manifest formats=["html"] 冲突 | ✅ |
| F7 (P2) | 单条件 CT.gov 查询回执有路径满足闭包门（验收完整性风险） | ✅ 与 F4 叠加 |
| F8 (P3) | charts.js 双副本无字节相等测试；manifest sha 校验的是 repo 根副本而运行期消费模块内副本；report-{a,b,c}.* 六资产无 manifest 覆盖 | ✅ |
| F9 (P3) | latest_delivery 失败关闭实现是范式保留（正向） | 采信 |
| F10 (P3) | bundle 延后路径排除正确但按前缀人工维护（正向+维护点） | 采信 |

Reviewer-B 对我初判的三处修正，均采纳：
1. 资产收敛方向反了：模块内副本才是发货副本；应把字节相等测试扩到全部 5 文件（或降级根副本为被校验镜像），**不要**加构建期复制。
2. **不做中间里程碑提交**：当前科学链未接线、真实取数未成，提交会把未验证身份固化为 provenance 锚点。恢复成本改用不落 git 的内容寻址脏树清单（路径+sha256+字节数）。
3. "竖向样例 vs 横向铺开"是伪二选一：正确顺序 = 先补一条真实可执行路线（PubMed 最便宜，URL 构造与 XML 解析已存在）→ 闭合语义提案链 → PNH 竖向首验 → 8×3 铺开。

### 3.4 P3.2 修正（采纳 Reviewer-B）

"版本化时间政策未实现"不成立：`TimepointCompatibilityPolicy`（contracts.py:619）与 `EndpointCompatibilityPolicy` 存在且被视图层消费；缺口是渲染器 `_time_band` 自做单位换算、不读政策——F1 的又一实例。

## 4. 本轮已实施修复（RED 已由失败测试提供，GREEN 已验证）

1. **交接文档 historical 标记**：docs/handoffs/…-20260911.md:718 路径拆分+标记；`tools/check_no_legacy_refs.py` 通过。gate 六步中唯一失败解除。
2. **夹具 row_id 唯一化**：§3.2；`tests/integration/test_fixture_case_contracts.py` 5 passed。完整 integration+browser 重跑见 §6。

## 5. Reviewer-A P3 语义终审（gpt-5.6-luna，read-only 沙箱，2026-09-11 02:18 完成）

**结论：第二轮三项修复在真实渲染路径上成立；失败反例调用了会对子集重分组的私有 helper，不是实际档案页回归，但该入口仍有 P2 护栏风险。** 无新 P0/P1。完整报告：`packets/2026-09-11-takeover-review/runs/reviewer-a-last-message.md`。

四项 P2（全部采纳，进入连续实施第一批）：

1. **产品/overview helper 仍允许子集重分组**（report_b.py:3119-3138 按传入记录重分组；真实路径 3679-3692、3770-3782 先全池再投影）。处置"两者都要"：反例改走真实渲染/`_project_scientific_groups` 验证不变量 + 给全池裁决入口加显式模式/断言，拒绝详情子集进入。
2. **全池中的孤立提案被静默忽略**（semantic_grouping.py:110-117 缺任一 row_id 即 continue）。全池入口应要求所有 row_id 存在；页面局部投影保留显式 partial 模式。
3. **未支持域缺少 fail-closed 校验**（2586-2607 按页面重写 `_domain`；未知域可能被重分类或静默消失）。入口校验域白名单；域不一致时拒绝，不自动覆盖。
4. **uncovered 记录缺少科学分组隔离护栏**（3497-3502 回退分支不禁止真实记录）。纵向页对真实 uncovered 直接失败；仅允许明确标记的合成/非比较记录走回退。

关键裁决要点：Q1 真实档案页已满足"全局分组投影"（3690 全池一次裁决 → 3770-3782 档案页传全局组 → 3497-3502 covered 投影）；Q3 三类修复（同 ID 跨域拒绝、纵向系列、跨域提案拒绝）在当前字节上结构成立；Q4 longitudinal 裸调用存在可构造的同试验拆分场景（A@50、B@50 跨试验组后 A@12 无法并入），但真实路径先按试验分隔 trial_series 故不触发——列入护栏 4 一并堵住。

## 6. 重跑与回归（最终）

- `tests/integration + tests/browser/test_b_portal.py`：修复夹具后 **818 passed**（260.74s），无连带破坏。
- `bash tools/gate.sh` 六步：交接文档标记修复后重跑（结果追加于检查点；legacy 步骤单独验证已过）。
- 结论：2026-09-08 暂停点全部被中断验证恢复完毕且通过；P3 有界修复（第二轮）经 Reviewer-A 独立终审成立。P3 暂停点关闭，剩余缺口以 §7 顺序进入 v6 计划。

## 7. 处置顺序（进入计划 v6）

1. P3 暂停点收口：Reviewer-A 终审落定 + 产品页投影不变量以真实路径固化（正式测试，不改 tmp/ 证据）+ 完整 gate/integration/browser 绿。
2. 接线优先（F1 路线，四步不可换序）：类型化视图字段（F2）→ `_groups_for_page` 消费科学视图集 → 投影组来源改科学层 → 按域拆文件归 `reports/b`（F3 顺带）。先补"渲染器不得裁决"红灯合同（F5）。
3. 真实路线与闭包门：PubMed 可执行路线（复用既有 URL/XML 代码）+ `not_applicable` 适用性依据（F4）。
4. 语义提案链闭环：proposal 状态迁移+`review_receipt_id`（复用 SemanticAdjudicationReceipt 形状）→ `capabilities/semantic_review.py` 生产者接图节点 → 签发复用 review_issuer → 渲染器只消费已批准提案。
5. PNH 竖向端到端首验 → 8×3 铺开（P6 合同不变）。
6. 工程卫生：charts.js 等资产字节护栏（F8）、README/权威索引机器可检（F6）、脏树内容寻址清单、**不做中间提交**。
