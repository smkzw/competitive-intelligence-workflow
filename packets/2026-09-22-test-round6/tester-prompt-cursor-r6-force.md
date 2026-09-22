# 【立即执行模式 · round-6】

被测对象改为 abc-v101：A/B/C 门户路径中的 abc-v100 全部替换为 abc-v101。其余任务不变（round-4 五项交互缺陷复测 + 回归）。你不得提问或等待，第一个动作就是开始测试。

---

# 【立即执行模式】

本提示词下方所有内容为你的任务。你不得创建任何任务管理条目、不得进入规划模式、不得向任何人提出确认问题或等待回复——你的第一个动作就是按提示词开始测试，所有歧义自行决策并记录。现在直接开始。

---

# 独立用户旅程复测：交互缺陷修复验证 · round-5（cursor/auto）

你是独立测试者，以真实用户身份复测 round-4 的 5 项交互缺陷是否修复，并回归检查关键旅程未被新改动破坏。

## 工作目录
`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`

## 清洁纪律
产物只写 `runs/test-round5-cursor/`（自行创建）。

## 被测对象（v100）
- A：`runs/pnh-vertical/abc-v100/reports/A/v1/html/overview.html`
- B：`runs/pnh-vertical/abc-v100/reports/B/v1/html/overview.html`
- C：`runs/pnh-vertical/abc-v100/reports/C/v1/html/overview.html`

## 复测清单（round-4 缺陷逐项验证 + 回归）
1. 【R4-BI-01】A product-overview：靶点筛选后"产品—机制分布"图按钮数是否随卡片收缩（round-4 卡片 45→3 图 34→34）——若未修，记录（该项归 R10 主线，可能未动）
2. 【R4-BI-03】B 安全页"观察时间"列与筛选面板：半翻译残片（"至30天 末次给药后 研究 drug"等）是否消除或带"（登记原文，未译）"标注
3. 【R4-BI-04】B 图表图例与表格组别命名是否一致
4. 【R4-CV】A safety.html 热图与明细表：事件列是否可区分不同测量（round-4 仅 6 个互异标签）；"无法归属"与"未公开"措辞是否区分
5. 【R4-A-矩阵】matrix.html 任何TEAE 轴气泡数与空态文案一致性
6. 【回归】A 产品→试验→证据抽屉返回；B 基线性别行组别显示；C "登记定义N"序号与页首解释；全站无 pageerror
7. 视口：1440 与 390 各走关键页

## 产出
`runs/test-round5-cursor/findings.json`（overall/journeys/broken_interactions/chinese_native_violations/regression_results/assumptions）；截图存 `runs/test-round5-cursor/shots/`。

## 执行纪律
读到提示词立即执行；不提问不等待；完成后退出码 0。
