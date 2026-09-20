# Task 6.7 技术设计

## 数据流与边界

`来源片段 + 试验/期间/层级身份` → `TrialDispositionObservation` → Task 6.8 视图模型。新模块只保存和校验事实，不参与 B 关键证据门槛，不创建页面或图表。

实现文件：`src/ci_workflow/reports/b/disposition.py`；schema：`schemas/trial-disposition-observation.schema.json`。

## 类型

- `DispositionFieldFamily`：受试者流转、原因、依从性、补救治疗、禁用药、方案偏离。
- `DispositionField`：预定义的细分字段；允许 `source_other` 保存来源新增字段，但必须同时有来源原名与定义，不能冒充核心字段。
- `DispositionScopeLevel`：总体、队列、组别。
- `DispositionMeasureObject`：受试者、事件。
- `DispositionStatisticForm`：人数、事件数、比例、依从性汇总、来源其他。
- `DispositionDenominatorRole`：筛选、随机、治疗、安全性、分析集、期间起始及来源其他。
- `TrialDispositionObservation`：保存身份、字段、计量、原因、定义、来源和披露状态。

## 校验

1. 组别层级必须有 group_id；总体层级不得伪造 group_id；筛败字段只能使用总体/队列筛选语境。
2. count/event_count 必须是非负整数；比例必须在 0–1 或 0–100 的明确单位范围内。
3. 可复算比例仅在分子与正分母存在时派生，使用来源单位；不把结果写回来源报告比例。
4. 原因字段必须保留原因原文和规范原因，并显式记录互斥/穷尽的三态：是、否、来源未说明。
5. 依从性必须有定义/阈值；PD 必须声明计量对象和层级，事件数不得映射为受试者数。
6. 缺失、不适用和冲突状态继续复用现有域枚举，公共校验边界重验 `model_copy`。
7. 稳定行身份包含产品、试验、期间、队列、层级、组别、分析人群、规范字段、计量对象、统计形式、分母角色、时间窗和原因。

## 回滚

新增模块、schema、测试和 manifest 条目可独立回滚；不修改 Task 6.1–6.6、GateSpec/evaluator 或渲染层。
