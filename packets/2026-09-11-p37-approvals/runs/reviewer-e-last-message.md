## 结论（一句话）

暂不通过：四步筛选在同域、同快照、同初始桶条件下基本一致，但存在跨域/分桶遗漏、提交验证绕过、全局固定时间阈值及宿主字段泄漏。

## 发现清单

- [P1] `src/ci_workflow/application/semantic_review_task.py:117-130`；未按 `_domain` 隔离，可能发射跨域对；消费端在 `src/ci_workflow/renderers/portal/report_b.py:3013-3023` 必然拒绝，形成冗余工作项；最小修复：按域建 task，或在发射与验证时强制两行域相同。
- [P1] `src/ci_workflow/application/semantic_review_task.py:129`；生产者仅依据 `compare_clinical_constructs` 跳过 compatible，但消费端在 `src/ci_workflow/renderers/portal/report_b.py:193-215` 会先受 `origin` 限制，且初始键包含人群/时间窗 `:2801-2812`，因此某些 compatible 对可能被生产者遗漏、消费端仍不合并；最小修复：统一比较守卫与初始分桶语义，不能让两者使用不同的兼容全集。
- [P1] `src/ci_workflow/application/semantic_review_task.py:161-186`；验证器不比较提交摘要与 `task.pairs` 的摘要，也不重新验证当前对仍为 `undecided`。可用当前 records 的新摘要构造 expected pair 的正向提交，绕过陈旧 task/当前硬冲突；最小修复：重验 task、逐项匹配 `pair.row_digests`，并重新执行 `_guard_verdict`。
- [P2] `src/ci_workflow/application/semantic_review_task.py:161-186`；时间点不同且 `proposal.time_window_compatible=False` 的正向提交仍会被接受，但消费端 `src/ci_workflow/renderers/portal/report_b.py:215-221` 必然拒绝；最小修复：验证器执行消费端同等最终守卫。
- [P1] `src/ci_workflow/reports/b/semantic_contract.py:246-250`；全局硬编码 ±2 周，和“不把固定阈值套全部终点”的政策目标冲突；当前 YAML 又将 48–56 周归入同一 52 周窗 `policies/timepoints/compatibility-v1.yaml:26-31`；最小修复：按版本化、终点适用范围的时间窗策略比较，不使用统一 `delta > 2`。
- [P2] `src/ci_workflow/application/semantic_review_task.py:74-79`；两个 `product_id` 缺失时会被视为“同产品”，错误跳过；消费端同试验自动路径要求 product_id truthy `src/ci_workflow/renderers/portal/report_b.py:199-202`；最小修复：产品标识必须已知、非 unknown 且相等才可跳过。
- [P2] `src/ci_workflow/application/semantic_review_task.py:53-63`；宿主可见模型包含英文内部状态 `awaiting_host_review` 及内部 Python 类型名 `ApprovedSemanticMerge`，并额外暴露 schema/policy/task 元数据；最小修复：分离内部 envelope 与宿主 DTO，中文化指引并移除内部类型/状态名。
- [P2] `tests/application/test_semantic_review_task.py:42-45,71-115`；未覆盖跨域、分桶差异、陈旧 task、时间窗否决及未知 product_id，且 verdict 断言允许非 `undecided`；最小修复：补充上述负向测试并严格断言发射结果。

## Q1-Q4 逐项

### Q1

结论：不完全一致。

证据：

- 同试验同产品、unknown、确定性 compatible、措辞统一后的 undecided，分别对应生产者 `:126-130` 与消费端 `:193-221` 的主要路径。
- 但消费端无 proposal 时先检查 `origin`，不同初始桶直接返回 false `report_b.py:193-196`；初始桶还纳入 population/time-window `:2801-2812`。生产者没有这些分桶信息，可能把消费端不会自动合并的 compatible 对跳过。
- 生产者未隔离 `_domain`，而消费端跨域 proposal 在 `report_b.py:3013-3023` 直接拒绝。

因此既有应裁未裁，也有裁了必被消费端拒绝的冗余。

### Q2

结论：示例行为正确，但政策实现不一致。

证据：

- `semantic_contract.py:246-250` 中 48/50 周差值为 2，不产生时间冲突；48/52 周差值为 4，产生“观察窗差异超过近窗口范围”。
- 但该规则是所有终点统一适用的固定 ±2 周，未表达终点类型或医学适用范围；v1.3 要求近窗按医学语境处理，不能套用所有终点 `docs/specs/competitive-intelligence-workflow-design-v1.3.md:379-383`。

真正合并仍有提案、批准和最终守卫，因此这里首先造成的是错误遗漏/过度拆分，而不是模型越权合并。

### Q3

结论：部分完备，但存在任务快照和最终守卫绕过；返回值本身会被重新构造为新实例。

证据：

- 任务外观察对、重复提交、当前池外观察、当前摘要漂移分别由 `:173-185` 处理。
- 自审和外层 model_copy 伪造会在 `ApprovedSemanticMerge.model_validate` 及其嵌套验证中被拒绝 `:165-172`。
- 但 `expected` 只取 row-id 集合 `:162-163`，未核对 task 内摘要，也未重新执行当前 `_guard_verdict`。
- `validated.append(merge)` 使用的是 `:172` 重建后的实例，不会直接返回未重验的原始对象。

### Q4

结论：没有泄漏原始 row/source/receipt 内容，但严格按目标宿主字段边界仍有内部字段泄漏。

证据：

- `SemanticReviewPair` 的 row_id、摘要、试验、定义和裁决位位于 `:35-39`，基本符合目标。
- `SemanticReviewTask` 还公开 `schema_version/task_id/project_id/policy_version/state` `:53-58`；指引中直接出现内部类型名 `ApprovedSemanticMerge` `:59-63`。
- 其中英文状态和 Python 类型名属于不应交给宿主的内部协议表达。

## 范围声明

只读检查了目标文件、目标测试、`semantic_contract.py`、`semantic_grouping.py`、直接消费端、时间窗策略及 v1.3 相关条款；未修改文件、未运行 pytest、未访问旧中文工程。以上为静态逐行复核，不代表运行时或浏览器验收。

