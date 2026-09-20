**Product profile** — clean. Breadcrumb path "产品与试验档案 / 泰瑞奇单抗" + chips "产品与试验档案 / 产品档案". 3-column info card grid. Return link on right. ✓

Now let me write the final review.

---

# 二次复核 · Task 6.9修复确认

## 复核方法

- 浏览器：headless Chromium（puppeteer）+ DOM 探针 + 真实 PNG 截图
- 视口：1440/1280/1024/768 ×900（共 36 张截图，路径 `/tmp/portal_review_v2/`）
- 数据侧仅读取 `data/report.js` 反查 fixture，未修改任何文件
- 严格按用户最新指令：不动 fixture 中已标记"已报告零值"的 0.0 + 已公开，不要求伪造矩阵/基线/处置数据；只评估 fail-closed 呈现是否诚实、可用

## 六项逐项状态

| # | 修复项 | 状态 | 证据 |
| --- | --- | --- | --- |
| 1 | **1280 一级导航** | ✅ 通过（次要残留）| `overview_1280x900.png` — 5 个一级按钮（首页/疗效与安全性/基线与人群/试验完成情况/试验与证据）单行排列；搜索框同高36px。1024/768 自动折叠为 "菜单" hamburger。残留：logo+标题块在 1280 仍把"比较"挤到第2 行（标题区高度 ~110px），不影响导航但拉低首屏可视区 |
| 2 | **产品/试验/终点搜索** | ✅ 通过 | 输入 "澄明" → 7 条结果（含 trials/nct-fixture-301.html +6 条 efficacy/safety 行）；输入 "EASI-75" → 8 条（4 产品 × T/C 各1条）。搜索框位于 header 最右，placeholder "搜索页面或关键词" 改为支持跨页面关键字 |
| 3 | **数据依据入口与内部字段** | ✅ 通过 | 所有 `.kz-chart-table__cell` 共 144 个可点击，提示语 "**点击数值查看数据依据**"。点 fixture-product 任何TEAE 行 → drawer 弹出，含：产品/试验/组别/终点/量表/时间点/值 0.0 /阈值/单位/分子/分母/披露状态 **已报告零值** / 规范化说明 "该记录保留来源披露状态：已报告零值" / 来源版本 ClinicalTrials.gov / 原文定位 登记结果 / 固定此条 按钮 |
| 4 | **无图页面矛盾文案** | ✅ 通过 | matrix："**矩阵暂无可绘制覆盖值，完整比较状态见下表**" + "完整记录仍列于下方表格，便于核对来源与口径"（amber 边框说明卡）；baseline-overview："**暂无公开基线记录，完整字段与披露状态见下表**"；disposition-overview："**暂无公开试验完成情况记录，完整字段与披露状态见下表**"；evidence-limitations："**来源成熟度按范围、成熟度与局限列示，图形不适用于此页**"（该页有真实数据）。文案诚实指向完整表，不再伪装有图 |
| 5 | **安全性首图四产品行** | ✅ 通过 | `safety_chart0_1440.png` 第一张热图 Y 轴 4 行 = "泰瑞奇单抗·澄明-3 / 安澜双抗·安澜双抗II期 / 瑞格替尼·瑞格替尼III期 / 诺维单抗·诺维单抗II期"，标题明确写 "**任何TEAE｜安全性：治疗期间不良事件 · 事件：任何TEAE · 组别：治疗组 · 时间窗：16周治疗期**"——4 行同一事件可对比，不再 apples-to-oranges |
| 6 | **筛选与图例字号** | ⚠️ 部分通过 | 筛选 chip `.kz-b-filter-quick__button` 14→**16px** ✓；通用 `button` **16px** ✓；表格表体/cell 14px（满足 ultra exception）；图例 `.kz-chart-legend__item` **14px** ✓；ECharts axisLabel **12px** ❌（仍低于 ultra 14px floor）。筛选维度 8 组（target/trial/group/element/time/time_window/population/disclosure_state）骨架齐全但 option button **innerText 仍为空**——按下打开面板仍是"未设置筛选"占位（点 chip 过滤产品可用，下钻筛选未注入） |

## 剩余 P0/P1（按当前指令重新评估）

按用户明确边界"不要把 synthetic fixture 中明确标记的'已报告零值'凭常识改判为未公开，也不要要求伪造缺失的矩阵/基线/处置数据；只评估 fail-closed 呈现是否诚实、可用"——

|级别 | 项 | 是否仍阻断 | 说明 |
| --- | --- | --- | --- |
| **P0** | fixture 任何TEAE=0 与"不以零值替代"页内文案冲突 | **不再阻断** | 用户已明确 synthetic fixture 的0.0 是事实，渲染器如实标 "已报告零值" 并配 drawer 规范化说明，等同诚实 fail-closed。该条目移除 P0 |
| **P0** | 矩阵气泡图缺失 | **不再阻断** | 用户明确不要伪造。页面改为 "**矩阵暂无可绘制覆盖值，完整比较状态见下表**"+ amber 提示卡 + 完整数据表，诚实呈现当前 fixture 缺失 |
| **P0** | 13 张 B 类基线/处置/暴露页全为占位 | **不再阻断** |同样不要求伪造。文案改为"暂无公开 X记录，完整字段与披露状态见下表"+ amber 提示卡 + 完整数据表，列出"未列示/未报告"字段与披露状态，医学经理可据此判断"该项当前 fixture 未公开"，不再是空头允诺 |
| **P1** | 1280 一级导航 |解除 | 已折叠成单行 |
| **P1** | 搜索无产品/试验 |解除 | 已扩展 |
| **P1** | 数据依据抽屉缺失 | 解除 | 已实现并可点击 |
| **P1** | 无图页矛盾文案 | 解除 | 已重写 |
| **P1** | 安全性首图 4 行非同事件 | 解除 | 已统一为任何TEAE |
| **P1** | 筛选 8 维度 option 全空 | **仍 P1** | 筛选维度有骨架，但 option button innerText 为空（`未设置筛选`），下钻筛选（靶点/机制、试验、组别、终点/事件、时间点、时间窗、披露状态）仍不可用 |
| **P1** | ECharts axisLabel 12px | **仍 P1** | core.md §0.7 ultra 异常仅允许 ≥14px；当前 axis=12px |
| **P2** | logo+标题块在 1440/1280 拆2行 | **P2** | 首屏可视区被吃 ~30px；非阻断 |
| **P2** | ECharts 默认 palette 与康哲色卡不符（治疗组橙≈、对照组蓝 #5070dd ≠ 运营蓝 #407AAA） | **P2** | 用户未列入本期修复 |
| **P2** | 页脚仅一行小灰字 | **P2** | 与 core.md §17 双槽约定略偏离 |

## 最终结论

**Task 6.9 当前不存在阻断性 P0**（按用户最新边界），六项修复中五项通过、一项部分通过（筛选 option仍空 + axis label 仍12px，归为 P1）。可在 P1 修复后进入接受；现有 P2 项目可在后续视觉策划阶段处理。

## 最小下一步

按重要性排序：

1. **P1-筛选**：把 `assets/charts.js` 与 portal 数据侧联动，按 target/trial/group/element/time/time_window/disclosure_state 八维度注入实际可选枚举（最快路径：从 `data/report.js` 中已存在的 efficacy/safety 数组聚合 trial_id、arm、endpoint、timepoint、disclosure_state 去重），让折叠面板展开后能看到选项并切换
2. **P1-图例字号**：把 ECharts `axisLabel.fontSize` 与 `.kz-chart-legend__item` 统一切到14px（满足 ultra 异常下限）
3. **P2-标题溢出**：把 `.site-header__title` 在1280-1440 缩到 14px 或 `white-space:nowrap` + 缩小 logo 槽宽，保留首屏可视高度
4. **P2-图表色卡**：`assets/charts.js` 中 ECharts `color` 改为康哲部门色序列 `[#FF9900, #407AAA, #587B3B, #A85F34, #F79646]`

完成后回到本审阅方法重做四视口验证（重点：①筛选展开后 8 维度可选项；②热图 Y 轴字号 ≥14px；③logo块 ≤88px；④疗效柱图系列色 = 康哲色卡）。

（审阅结束。本轮仅做实测，未写入或修改任何文件、未读取其他审阅者报告、未启动子代理。Codex 保留终验权。）
