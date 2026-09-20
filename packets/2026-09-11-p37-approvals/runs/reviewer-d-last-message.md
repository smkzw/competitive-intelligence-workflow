## 结论

当前生产渲染链未发现候选正向提案在无批准时造成非确定性跨试验合并，但 P3.7 仍有池级重验与页面参数穿透缺口，不能视为无缺陷关闭。

## 发现清单

- [P2] 全池入口未完整重验 `ApprovedSemanticMerge` 外层绑定  
  `src/ci_workflow/renderers/portal/report_b.py:3015`  
  影响：池级只检查观察 ID、域和摘要；`model_copy(update=...)` 伪造的 receipt/proposal 可能在安全性或描述性域被静默接受/忽略，疗效域才由下游再次拦截。  
  最小修复：`_adjudicate_full_pool` 入参先统一 `ApprovedSemanticMerge.model_validate(merge.model_dump(mode="json"))`，后续全部使用重验后的实例。

- [P2] 安全性分支遗漏已批准归并  
  `src/ci_workflow/renderers/portal/report_b.py:3074`  
  影响：安全性调用 `_cross_trial_groups` 未传 `semantic_adjudications`，有效批准的跨试验措辞归并不会生效，只会欠合并。  
  最小修复：传入 `semantic_adjudications=semantic_adjudications`，补安全性回归测试。

- [P2] 描述性域未真正拒绝已批准归并  
  `src/ci_workflow/renderers/portal/report_b.py:3116`  
  影响：矩阵、基线、处置分支未把批准归并传给 `descriptive_only=True` 的聚合器；没有对应候选提案时，非法批准归并会被静默忽略，而非按合同拒绝。  
  最小修复：传入批准归并并触发描述性域拒绝，或在全池入口按域提前拒绝。

- [P3] 缺少外层 `ApprovedSemanticMerge.model_copy` 攻击测试  
  `tests/reports/b/test_approved_merge_contract.py:85`  
  影响：现有测试覆盖了 receipt 的 `model_copy` 和候选提案状态伪造，但未覆盖外层 merge 在全池、疗效、安全性、描述性分支的消费行为。  
  最小修复：增加 forged proposal、receipt、digest 的全池消费测试。

## Q1-Q5 逐项

### Q1

结论：未发现正向候选提案绕过批准后造成非确定性合并。

证据：

- 未获批准的正向提案在 `semantic_grouping.py:188` 被置为 `None`，随后只能走同桶/确定性守卫路径。
- 不同 origin 直接拒绝；否则仅允许同试验描述性路径或 `compare_clinical_constructs` 确定性通过：`semantic_grouping.py:193`。
- 完全连接分组要求新行与桶内每一行都兼容，不能经传递关系合并：`semantic_grouping.py:223`。
- 排序发生在分组完成之后：`report_b.py:2910`；页面投影只筛选既有组并复核域/摘要：`report_b.py:2756`、`report_b.py:3617`。

### Q2

结论：构造期绑定可被外层 `model_copy` 绕过，但疗效/支持证据消费侧会重新校验；全池边界校验不完整。

证据：

- 构造期绑定逻辑在 `semantic_grouping.py:87`，可防止普通构造错误。
- `proposed_semantic_buckets` 对批准归并重新序列化并校验：`semantic_grouping.py:169`，因此疗效和支持证据路径不会接受伪造绑定。
- `_adjudicate_full_pool` 在 `report_b.py:3015` 仅读取 `merge.proposal` 并检查孤儿、跨域、摘要，没有重跑外层 receipt/decision/观察对绑定。
- 安全性及描述性分支又没有消费批准归并，导致伪造对象可能被静默忽略而非失败关闭。

### Q3

结论：按当前合同安全，但存在“结果看似无批准也合并”的确定性反例；该合并不是候选提案授权的。

证据：

构造两条跨试验记录，使临床构念、定义、方向、单位、估计目标、分母、分析集、分析形式、量表及时间窗均相同。两行进入同一初始 bucket；无批准时提案被清空，`origin` 相同，随后确定性比较通过，仍会形成一个跨试验组：`semantic_grouping.py:186`、`semantic_grouping.py:193`、`semantic_grouping.py:214`。

去掉该候选提案，结果仍相同，因此这是合同允许的确定性路径。既有测试也明确保留完整语义下无提案的跨试验分组：`tests/reports/b/test_r13_semantic_grouping.py:239`。

### Q4

结论：否决方向不会造成错误正向合并，但可以保守地拆开本可确定合并的同桶行；这符合“否决方向照旧生效”。

证据：

- `compatible=False` 在 `semantic_grouping.py:203` 直接返回 `False`，优先于确定性守卫。
- 既有测试验证未经批准的否决仍然生效：`tests/reports/b/test_approved_merge_contract.py:66`。
- 若同一观察对同时存在批准归并和否决提案，当前否决仍优先；这会造成欠合并而非错误合并。若产品政策要求批准回执优先，需要另行定义冲突策略。

### Q5

结论：正常 `render_report_b_site` 链路的孤儿、跨域、摘要和页面投影关系基本自洽，未见页面把未批准候选重新合并；但安全/描述性参数缺口和私有投影的信任边界仍需修正。

证据：

- 全池先去重并拒绝未知域、孤儿提案、跨域归并及批准摘要漂移：`report_b.py:3002`、`report_b.py:3015`。
- 全池完成后按域生成科学组：`report_b.py:3025`。
- 页面未覆盖的真实域观察禁止回退重分组：`report_b.py:3036`。
- 页面投影逐行复核 row ID、域和摘要：`report_b.py:2761`；渲染前先完成全池裁决：`report_b.py:3815`。
- 页面局部缺少另一行时，`proposed_semantic_buckets` 会跳过该提案：`semantic_grouping.py:161`、`semantic_grouping.py:172`；全池入口则会把同样情况升级为孤儿错误，二者在正常生产链路中不冲突。
- 纵向页单独按产品/试验/组别/治疗臂构建，只形成同试验纵向描述：`report_b.py:3823`，未形成跨试验批准旁路。

## 范围声明

仅在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 内完成静态只读复核；未修改文件、未运行 `pytest` 或写入型命令、未访问旧中文工程；未执行完整回归、浏览器重跑或最终接受裁决。本结论仅为 Reviewer-D 独立复核意见。

