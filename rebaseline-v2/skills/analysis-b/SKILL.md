---
name: analysis-b
description: 基于已核实的疗效/安全性数据写要点（不跨不可比条件下结论）
tools: []
output: AnalysisResult
max_steps: 4
---
输入 data.results / data.safety / data.charts.groups。

写 3–6 条 finding：
- 只比较同一终点、同一时间点、同一统计形式的数据（charts.groups 已经分好组）；跨组只能描述，不能下优劣结论。
- 明确写出：时间点、分析人群、是否为安慰剂对照；跨试验比较必须加「非头对头」提示。
- status 不是「verified」的数字不得引用为结论依据，可提示「待核实」。
- 安全性：SAE 与全因死亡按组列出；比例只引用 data 中已有的 proportion。
report 固定为 "B"。
