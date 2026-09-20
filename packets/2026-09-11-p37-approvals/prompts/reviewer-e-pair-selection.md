Delegated mode（执行模块角色：只读独立复核节点 Reviewer-E）

# 硬边界

只读评审（read-only 沙箱）；不修改文件、不跑 pytest；唯一工作区 /Users/smkzw/Documents/AI Products/competitive-intelligence-workflow；禁止访问旧中文工程；结论基于亲自读到的代码行。

# 评审对象

src/ci_workflow/application/semantic_review_task.py（新建，~220 行）与 tests/application/test_semantic_review_task.py。

这是 B 报告语义归并链的生产者：`build_semantic_review_task` 决定哪些跨试验观察对进入宿主复核工作项。对选择规则（本模块的科学决策核心）：

1. 同试验同产品对：跳过（试验内描述性合并，确定性）。
2. `_observation` 解析失败或缺未知关键语义（clinical_construct/definition 任一 unknown）：跳过（None）。
3. `compare_clinical_constructs(left, right).compatible` → "compatible"：跳过（确定性可比，无需模型）。
4. 否则把右侧措辞统一为左侧后重跑守卫：通过 → "undecided"（进入工作项，唯一可经提案+独立复核归并的对）；仍不通过 → "incompatible"：跳过（硬冲突，模型不可覆盖）。

`validate_semantic_review_submission`：外层 ApprovedSemanticMerge 整体重验（防 model_copy）、任务外对拒绝、重复拒绝、摘要与当前观察绑定、自审由 receipt 模型拒绝。

参考语义：src/ci_workflow/reports/b/semantic_grouping.py（消费端，已过 Reviewer-D 终审）、semantic_contract.py 的 compare_clinical_constructs 与 unknown 判定。

# 裁决问题

Q1 对选择规则与消费端 proposed_semantic_buckets 的合并语义是否一致：工作项选出的 "undecided" 对，是否恰好是消费端"有批准即可合并（守卫含时间窗）"的对？有无工作项遗漏（应裁未裁）或冗余（裁了也必被否）？
Q2 时间窗语义：步骤 4 的措辞统一不会改变时间轴；48/50 同窗、48/52 超窗这类判定完全由 compare_clinical_constructs 的时间规则承担——该规则的±2周等行为与"48/50周按医学语境处理，不把固定阈值套所有终点"的版本化政策目标是否冲突？（注意：本模块只做筛选，真正合并还须提案+批准+守卫。）
Q3 验证器是否有绕过：任务外/重复/伪造/陈旧摘要/池外观察的拒绝是否完备；返回值是否可能含未重验实例。
Q4 工作项模型是否泄漏内部字段给宿主（应只含 row_id/摘要/试验/定义/裁决位与中文指引）。

# 输出格式（严格）

## 结论（一句话）
## 发现清单（[P0-P3] + 文件:行 + 影响 + 最小修复；无则"无"）
## Q1-Q4 逐项（结论+证据）
## 范围声明
