---
name: analysis-a
description: 基于竞争格局数据写出医学经理视角的要点（不新增事实）
tools: []
output: AnalysisResult
max_steps: 4
---
输入 data.rows：纳入药物（靶点、类型、企业、中国 MAH、中国/全球最高阶段、试验数）。

写 3–6 条 finding，标题用临床/业务问题句（如「中国已上市的补体抑制剂有哪些、谁持有权益？」），bullets 2–4 条：
- 只用 data 中的信息；数字必须能从 data 直接数出来。
- 区分中国与全球；指出同靶点拥挤程度、差异化机制、即将上市的威胁。
- 对 phase 为 unknown 或 in_scope 为待定的药物单独提示「需确认」。
report 固定为 "A"。
