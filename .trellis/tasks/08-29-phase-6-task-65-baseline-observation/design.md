# Task 6.5 技术设计

## 数据流

`来源片段 + 试验/组别身份` → `BaselineObservation` → `BaselineCompatibilityKey` / Gate 转换 → 现有 `GateEvidenceBinding` → `B-v1 GateSpec` → 允许锁定候选快照或生成用户可读阻断包。

## 类型设计

在 `src/ci_workflow/reports/b/baseline.py` 建立小而封闭的枚举和模型：

- `BaselineVariableDomain`：人口学、疾病语境、基线严重程度；
- `BaselineDataType`：连续、分类、计数；
- `BaselineStatisticForm`：样本量、均值、标准差、中位数、四分位数、范围、人数、比例及来源明确的其他形式；
- `BaselineObservation`：保存 PRD 字段全集、原始事实、来源谱系和披露状态；
- `BaselineCompatibilityKey`：只由科学可比字段组成，不含展示标签或审阅状态；
- Gate 转换函数：只把四类关键观察映射到既有 B Gate 单元和 `GateEvidenceBinding`。

schema `schemas/baseline-observation.schema.json` 与 Pydantic 模型同源约束；不复制 GateSpec。

## 关键校验

1. 已报告连续值必须有统计形式、单位和分析人群；均值/中位数等中心值与各自离散度字段不混用。
2. 分类比例必须绑定分类水平和正分母；同时提供分子与比例时确定性复算，仅记录差异，不覆盖来源值。
3. 样本量是该组该基线分析人群的计数，不能从任一事件分母、试验总 N 或另一组推断。
4. 严重程度锚点保留量表/仪器、版本、方向、单位、理论范围和基线定义；未知字段用明确披露状态保存。
5. 只有同规范概念、量表/版本、方向、单位、基线定义、统计形式以及相同分类/分箱口径的观察共享比较键。
6. 稳定行标识包含产品、试验、队列、组别、规范概念、统计形式、分类水平/分箱和基线定义。

## Gate 接入

- 复用 `B-v1.yaml` 的 `b_baseline_sample_size`、`b_baseline_age`、`b_baseline_sex`、`b_baseline_severity_anchor`。
- 适用宇宙仍由 `ApplicableUniverseSnapshot` 决定；每个 group 独立派生四项结果。
- 转换只接受观察自身的 trial/group/fact version/locator，不聚合或借用。
- 披露缺口和冲突进入现有双重穷尽与阻断包；本模块不渲染第二套阻断语言。

## 回滚边界

新实现限于 baseline 模型、schema、两份目标测试及必要导出；不修改 Task 6.1–6.4 科学语义，不创建页面，不改变现有 Gate 评估器。
