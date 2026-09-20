Delegated mode（执行模块角色：只读独立复核节点 Reviewer-A）

# 硬边界

1. 只读评审。不修改任何文件、不创建文件、不运行会产生写入的命令（pytest 会写缓存，禁止运行）。你的沙箱是 read-only。
2. 唯一允许的工作区：/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow。禁止访问路径含"竞品调研工作流"的旧中文工程（不读、不写、不盘点、不确认存在性）。
3. 不重派任务、不启动代理、不声称最终接受（final acceptance 由派发方持有）。
4. 结论必须基于你亲自读到的代码行，不允许引用本提示词中的叙述作为证据。

# 背景（供定位，不构成结论）

本工程生成 B 临床结果证据室 HTML 门户。合同要求：完整观察池一次裁决科学分组（complete-link，不允许传递兼容），所有物理页面（包括产品/试验档案页）只投影全局分组，不能按筛选子集重新决定科学分组；同一 row_id 跨域（疗效/安全）不得串事实；同试验纵向描述与跨试验可比是两种不同的组。

2026-09-08 两轮独立审阅后主线程做了修复：同 ID 跨域/跨摘要去重拒绝（_dedupe_records、_project_record 带域）；一次构建 within_trial_longitudinal 纵向系列；分域前拒绝跨域提案；站点重置移到校验后。最后独立复验被用户暂停中断。现在恢复。

# 派发方已运行的测试事实（你不需要重跑）

- tests/reports/b + tests/browser/test_b_semantic_proposals.py：278 passed。
- tmp/semantic-rereview-a4bUhi/test_rereview.py（第二轮反例 8 项）：全部通过。
- tmp/semantic-independent-w1RHFS/test_independent.py（第一轮反例 22 项）：29 passed / 1 FAILED（与上一条合跑计 30 项）。
- 失败详情：test_product_page_is_projection_of_global_groups（该文件 93-107 行）。输入：3 行 a/b/c，a=product-a/trial-a，b=product-b/trial-b，c=product-b/trial-c（52 周、第三种措辞）；提案 (a,b) 兼容、(b,c) 兼容。全局 efficacy 页分组结果 {{third},{first,second}}；把 product-b 的子集 {second,third} 直接喂给 _groups_for_page('product-trial-profiles', selected, ...) 得到 {{second,third}}（合并了）。测试期望产品页分区 == 全局分区 ∩ 选中行。
- 开发门 gate：Ruff/mypy strict 217 源/986 活跃单元合同/兼容 20/分层 7 全绿；唯一失败是 docs/handoffs/…-20260911.md:718 缺 historical: 标记（文档问题，与本评审无关）。

# 你的任务

先读代码（这些是主要证据源）：

1. src/ci_workflow/reports/b/semantic_grouping.py（165 行，全文）
2. src/ci_workflow/renderers/portal/report_b.py 重点函数：
   - _project_record（约 1671 行起）、_dedupe_records（约 2036 行起）
   - _project_scientific_groups（约 2748-2768 行）
   - _groups_for_page（约 2961-3139 行，含 product-trial-profiles 分支 3119-3138）
   - _cross_trial_groups（约 2861 行起）
   - _render_page_context（约 3464-3503 行：covered 走投影、uncovered 走每页重分组）
   - 主装配（约 3660-3704 行：detail_pool 全池一次裁决 + trial_series 纵向构建）
   - 档案页渲染（约 3769-3862 行：products/*/trials/* 从 detail_pool 筛选后传 scientific_groups）
3. src/ci_workflow/reports/b/semantic_contract.py（compare_clinical_constructs、unknown 判定）
4. 反例文件 tmp/semantic-independent-w1RHFS/test_independent.py 与 tmp/semantic-rereview-a4bUhi/test_rereview.py
5. 正式测试 tests/reports/b/test_semantic_grouping_proposals.py、tests/browser/test_b_semantic_proposals.py（了解正式合同已覆盖什么）

裁决问题（逐项给出结论与代码证据）：

Q1 失败反例裁决：真实渲染路径（_render_page_context + 档案页）是否已满足"产品页=全局分组投影"？如果是，_groups_for_page 直接接受子集并重分组是否仍构成合同风险（未来调用者绕过投影）？给出你认为正确的最小处置：改测试到真实路径 / 加防扩散护栏（例如对含域记录的子集调用直接拒绝或断言 uncovered 只允许合成状态记录）/ 两者都要 / 其他。注意不要建议大重写。

Q2 相邻场景挑战（第二轮暂停时留下的待查清单，逐项判定"已有缺陷/已被现有代码防住/纯理论"）：
- 孤立提案（引用不存在 row_id）
- 未支持域的记录进入分组
- 同一观察在多个页面重复投影
- overview 页拆域后与全局分组的一致性
- 纵向页 uncovered 残留走 _groups_for_page('longitudinal-results', …) 的行为
- _synthetic_status_records 合成记录与真实记录混布时分组身份
- 输入重排/产品页切片对 complete-link 稳定性的边界

Q3 第二轮三类修复（同 ID 跨域串事实、纵向系列丢失、跨域提案静默忽略）在当前字节上是否仍然成立（不是靠测试通过，而是靠代码结构）。

Q4 semantic_grouping.py 的 compatible() 内"同试验同产品 longitudinal 描述可同组"分支（135 行附近）与 complete-link 的交互：是否存在一个场景使同试验行被拆进跨试验组、破坏纵向系列？

# 输出格式（严格遵守）

输出 Markdown：

## 结论
一句话：第二轮修复是否成立；失败反例的定性。

## 发现清单
每条：`[P0|P1|P2|P3] 标题` + 文件:行号证据 + 影响 + 最小修复建议。没有发现就写"无"。

## Q1-Q4 逐项裁决
每项：结论 + 证据（文件:行）。

## 范围声明
你实际读过的文件；未覆盖的部分。
