# 独立用户旅程测试：操作链轨 · round-4（cursor/auto）

你是独立测试者，以**真实临床研究用户**的身份完整走一遍 PNH 竞品报告 A/B/C 三个门户，用真实浏览器（ego lite / ego-browser skill）点击、滚动、筛选、展开、截图。不读源码代替体验；不信任生产者自述。

## 工作目录
`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`。

## 清洁纪律
- 你的全部工作产物只写入 `runs/test-round4-cursor/`（自行创建）；不读取其他测试者目录与既往轮 findings
- 浏览器从零打开本地文件，清缓存/新会话视角

## 被测对象（v97，本轮新候选）
- A：`runs/pnh-vertical/abc-v97/reports/A/v1/html/overview.html`
- B：`runs/pnh-vertical/abc-v97/reports/B/v1/html/overview.html`
- C：`runs/pnh-vertical/abc-v97/reports/C/v1/html/overview.html`

## 用户旅程（每条都真实操作并截图，1440 与 390 两个视口各走一遍关键页）
1. **A 全景导航**：机制/阶段筛选 → 点开一个产品 → 进入一个试验 → 打开证据抽屉 → 返回（记录每步是否可逆、有无死链、有无 pageerror）
2. **安全性热图**：切换严重/总体不良事件轴；检查事件列是否可区分不同测量（不再是同一名称堆叠 200 行）；点开任一格查看证据
3. **B 基线与安全表**：基线人口学页——性别行的组别是否显示（"第1组"等，不得"组别未列示"）；安全表"观察时间"列不得有整句英文；图表图例与表格名称是否一致（不得图上英文、表中中文）
4. **C 设计比较**：横向矩阵点击单元格 → 证据抽屉；"登记定义N"序号是否可理解（页首有解释文字）；聚合格"〔本格聚合N条登记明细〕"是否清晰
5. **图表交互**：图例开关、缩放（dataZoom）、窗口缩放后布局是否遮挡；柱状图**第一个柱子**是否显示数值标签
6. **诚实边界观感**：未公开/待核验是否显示为明确中文说明而非空白或占位符

## 产出
`runs/test-round4-cursor/findings.json`：overall（pass/partial/fail）、journeys（每条旅程的步骤/截图路径/结果）、broken_interactions（severity+evidence+复现步骤）、chinese_native_violations、assumptions。截图存 `runs/test-round4-cursor/shots/`。

## 执行纪律（最高优先级）
- 读到此提示词后**立即直接开始执行**，不创建任务、不规划、不提问、不等待
- 所有歧义自行决策并记录在 assumptions
- 完成后正常退出（退出码 0）
