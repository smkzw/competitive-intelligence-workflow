# Task 6.8 技术设计

## 实现边界

新增 `src/ci_workflow/reports/b/disposition_views.py`，输入 `TrialDispositionObservation` 集合，输出不可变 `DispositionViewState`。不创建物理页面；Task 6.9 只消费本视图合同。

## 视图类型

- `DispositionSelectionState`：保存多选筛选、证据焦点与 repeated-param 网址往返。
- `DispositionTableRow`：一条事实的中文用户视图，保留原事实和全部来源语境。
- `DispositionChartPanel`：兼容事实桶、推荐图形、可绘制行与不可绘制状态行。
- `DispositionStatusMatrix`：筛选范围无可绘制数值时的试验 × 规范字段披露矩阵。
- `DispositionEvidenceLink`：表行、图点/节点、状态单元与证据定位的一对一引用。
- `DispositionFilterApplicability` / `DispositionFilterOption`：可用值和不适用原因；事实无靶点字段时禁用靶点筛选。
- `DispositionViewState`：来源事实、已选事实、面板、表、状态矩阵、证据和网址状态的同步快照。

## 图形选择

1. 单项试验且字段族为受试者流转：`consort_flow`；仅连接存在或有明确披露状态的规范节点，不推导流失人数。
2. 跨试验比例：按 `denominator_role + field + time_window + measure_object` 拆分分组比例柱状图或点图。
3. 人数/事件数：按计量对象和分母角色拆分点图/柱状图；事件数不得被标为受试者比例。
4. 原因集合只有全部 `reason_is_mutually_exclusive=True` 且 `reason_is_exhaustive=True` 时允许 `reason_stacked_100`；其余固定 `reason_independent_bar`。
5. 当前已选事实没有可绘制数值时输出 `status_matrix`；所有非数值状态保留中文标签。

## 同步与失败关闭

- 所有公共选择、证据聚焦和重置操作都通过源事实重新装配，再由 `assert_synchronized()` 比较表、面板、状态矩阵、证据和 URL。
- `model_copy(update=...)` 产生的失配状态不能通过公共操作传播。
- 未知焦点行清空并规范化网址，不得指向筛选范围之外的证据。
- 内部映射使用只读 `MappingProxyType`，序列化时显式转换。

## 回滚

新增模块、两份测试和 Task 6.8 验收记录可独立回滚；不触及 Task 6.7、GateSpec、模板或前端资产。
