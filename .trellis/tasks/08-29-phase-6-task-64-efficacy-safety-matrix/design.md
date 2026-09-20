# Task 6.4 技术设计

## 数据流

`EfficacyFactRow + SafetyFactRow + 治疗组样本量 + 筛选状态` → `MatrixComparisonRow` → `BubblePoint / MatrixCell` → `同步图表、完整表、提示、证据链接与 URL 状态`。

## 合同边界

1. `MatrixSelectionState` 保存全部可切换维度和稳定 URL 参数；默认值来自当前锁定快照，不在模板中推断。
2. `MatrixComparisonRow` 引用 Task 6.2/6.3 原始事实行，保存产品、靶点、试验、治疗与对照身份及比较状态。
3. `BubblePoint` 只在疗效、安全性和样本量满足所选语境时生成；保留原始值、方向、倒序标识和证据行标识。
4. `MatrixCell` 对不可绘制组合给出明确中文状态和原因，不生成零坐标或空白。
5. `MatrixViewState` 以一个选择状态确定性重建图、表、提示、证据链接和 URL；重置恢复同一默认状态。

## 关键计算

- 横轴为方向校正的试验内治疗—对照信号，越右表示所选疗效指标的观察信号越强；原始两组数值不变。
- 纵轴保存原始 TEAE/所选安全性发生率，视图设置 `safety_axis_reversed=True`，不创建转换后的安全性分数。
- 气泡半径 `r = k × sqrt(N / pi)`；验证 `pi × r² / k² = N`。
- 任何缺失或不兼容都产生矩阵状态，不进入可绘制点集合。

## 交互一致性

所有派生表面保存同一个 `comparison_row_id` 和事实行 ID 集；筛选变化只重建视图，不改写事实。URL 采用稳定排序的中文友好参数值/内部稳定 ID，重置可复现。

## 兼容与回滚

新代码限于 `reports/b/pages.py` 和两份目标测试。复用 Task 6.2/6.3 模型，不修改其科学语义；不创建物理模板。
