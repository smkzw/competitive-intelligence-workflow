Delegated mode（执行模块角色：只读独立复核节点 Reviewer-D）

# 硬边界

1. 只读评审，沙箱 read-only。不修改文件、不运行写入型命令（禁止 pytest）。
2. 唯一工作区：/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow。禁止访问旧中文工程。
3. 不重派、不声称最终接受。结论基于你亲自读到的代码行。

# 背景

本工程 B 报告（临床结果证据室）今天落地了 P3.7 核心变更：**候选语义提案不再授权正向跨试验合并；正向合并必须携带绑定独立复核回执的 ApprovedSemanticMerge**。合同依据："LLM 归并提案受确定性边界和独立复核约束；提案身份和来源声明摘要只是候选完整性机制，不是实际独立复核者签发 accepted 的替代"。

# 变更位置

1. src/ci_workflow/reports/b/semantic_grouping.py：
   - 新增 `ApprovedSemanticMerge`（merge_id + proposal + SemanticAdjudicationReceipt；模型级绑定校验：提案必须 compatible、回执 decision 必须 compatible、观察对一致、构造期再校验防 model_copy）。
   - `proposed_semantic_buckets` 新参数 `approved_merges`：正向候选提案若无对应已批准归并则"降级为无提案"（回退确定性路径）；否决方向照旧生效；描述性域拒绝已批准归并；重复/摘要漂移拒绝。
2. src/ci_workflow/renderers/portal/report_b.py：`ReportBPortalData.semantic_adjudications` 字段；`_groups_for_page`/`_cross_trial_groups`/`_adjudicate_full_pool`/`_render_page_context`/渲染循环全链穿透；全池孤儿归并与跨域归并拒绝、摘要绑定。
3. 测试：tests/reports/b/test_approved_merge_contract.py（6 项新合同）；既有正向提案用例升级为已批准形式（tests/reports/b/test_semantic_grouping_proposals.py、test_full_pool_adjudication_guards.py、tests/browser/test_b_semantic_proposals.py——两处陈旧裁决夹具被新池护栏正确拦截后清理）。

主线程已运行：B 领域+语义浏览器 295 绿；完整 integration/browser/gate 回归进行中。

# 你的任务

读上述三个文件的相关段落（semantic_grouping.py 全文 200 行级；report_b.py 重点：字段定义 ~1180、_cross_trial_groups ~2870-2960、_adjudicate_full_pool ~2990-3030、_groups_for_page ~3040-3120、_render_page_context uncovered 段 ~3600-3630、渲染循环 ~3870-3990；三个测试文件全文）。裁决：

Q1 批准语义是否有旁路：存在任何路径使候选正向提案在无批准时仍导致合并（直接或经传递/排序/页面投影）？
Q2 ApprovedSemanticMerge 的绑定校验是否可被 model_copy(update=...) 绕过（项目质量规范 .trellis/spec/backend/quality-guidelines.md 明令防此攻击）？消费侧（proposed_semantic_buckets/池校验）是否重新校验？
Q3 "正向无批准→降级为确定性路径"的设计：降级后同一对行是否会经由同桶 origin+guard 意外合并（即批准缺失被绕过）？给出可构造反例或确认安全。
Q4 否决方向不要求批准：是否有场景使这变成漏洞（例如 compatible=False 提案被用来强行拆开本应确定合并的同桶行）？
Q5 池级孤儿/跨域/摘要三重校验与页面级局部跳过（"另一物理页持有该观察"）的交互是否自洽；页面投影是否可能消费未在全池批准的归并。

# 输出格式（严格）

## 结论
一句话。
## 发现清单
每条 `[P0-P3] 标题` + 文件:行 + 影响 + 最小修复。
## Q1-Q5 逐项
结论 + 证据。
## 范围声明
