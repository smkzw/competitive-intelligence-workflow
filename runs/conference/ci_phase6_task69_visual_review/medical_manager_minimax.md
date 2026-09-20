Three font sizes used: 16px (body), 14px (tables/filter chips/buttons), and 20px (likely H2 or large text). 14px is below the 16px label minimum per core.md §0.7 (with ultra exception only for tables/axis labels with explicit `data-density=ultra`).

Now let me write the comprehensive review:

---

# B 类报告门户 · 真实医学经理视觉审阅报告

## 1. 边界与浏览器证据

-角色：懒惰、视觉敏感、不熟悉计算机和 AI 的资深临床试验医学经理
- 范围：仅访问 `output/acceptance/task-6.9/site/`26 个物理页面 + 子目录（products/、trials/、assets/、data/）
- 视口：1440×900、1280×900、1024×900、768×900，并附测 375×812移动
- 真实浏览器：headless Chromium（已通过 puppeteer 控制；含 `tab.ariaSnapshot`/PNG 截图）
- 已访问路径：首页 → 疗效 → 安全性 → 疗效/安全性矩阵 → 基线总览 → 试验完成情况总览 → 证据与局限 → 产品档案（fixture-product）→ 试验档案（nct-fixture-301）→ 4 个快速筛选按钮 → 全文搜索 "试验" / "澄明"
- 截图存放：`/tmp/portal_review/*.png`（共 40+ 张），本报告所述观察均来自这些截图与 DOM 探针

## 2. 真实医学经理完整试用结果

| 步骤 | 1440×900 | 1280×900 | 1024×900 | 768×900 |
| --- | --- | --- | --- | --- |
| 进入首页，首屏看到 logo + "总览 / 首页 / 图在前…" + 4 个产品快速筛选按钮 + "筛选条件 未设置筛选" + 章节标题 "图形定位 / 先看图形…" — **没有数据图形** | 顶部660px 全是导航/标题/筛选/章节文案 | 同左 | 同左 | 图表 y=700 起进入视口 |
| 向下滚动到第一张柱状图（EASI-75｜泰瑞奇单抗·澄明-3） | OK | OK | OK | OK |
| 点 "快速筛选产品 - 泰瑞奇单抗" | 其他 3 个产品图表隐藏 | 同左 | 同左 | 同左 |
| 滚到表后，回到顶部，进入 "疗效" | 图表同首页结构（4 张柱图+4 张表） | OK | OK | OK |
| 进入 "安全性" |看到 TEAE 热图：泰瑞奇单抗 =0（浅橙色），其他 70.5/74.8/69.3（深橙） | OK | OK | OK |
| 进入 "疗效与安全性矩阵" | **气泡图区域显示 "矩阵暂无可绘制覆盖值"**——中央交付物缺失 | 同左 | 同左 | 同左 |
| 进入 "基线与人群总览 / 试验完成情况总览 / 依从性 / 失访与退出" 等 | **看到 "暂无公开记录｜…未报告" 卡片 + 全表 "未列示 / 未报告"**，没有任何图表 | 同左 | 同左 | 同左 |
| 进入 "研究依据与局限" | 看到4 张橙色边框阅读提示卡 | OK | OK | OK |
| 顶部搜索框输入 "澄明" |弹 "未找到匹配页面或数据"（澄明-3 是数据集中的试验） | 同左 | 同左 | 同左 |
| 顶部搜索框输入 "试验" | 弹 15 条页面链接，OK | OK | OK | OK |
| 点击产品档案 "泰瑞奇单抗" | 看到产品基本信息 + 监管/合作/专利 + 7 张数据表 | OK | OK | 单列 |
| 点击试验档案 "澄明-3" | 看到试验基本信息 + 角色 + 5 张数据表 + "返回档案索引" | OK | OK | OK |

**核心节奏**：第一屏到图表的距离约 660px（=3 行 logo + 标题 + 元信息 + 筛选 + 章节标题），与"首屏直接看到最重要的竞品格局"的产品承诺不符；快速筛选工作；矩阵页气泡图缺失；基线/处置5 个 B 类核心页面无图表，仅以 "未报告" 占位。

## 3. 缺陷清单

### P0 · 数据完整性 / 显示契约（阻断）

| # | 页面 | 宽度 | 复现 | 观察 | 最小修复建议 |
| --- | --- | --- | --- | --- | --- |
| **P0-1** | 安全性 / 产品档案 | 全宽 | 进入 safety.html，看 TEAE 热图第一行 "泰瑞奇单抗 · 澄明-3" | 单元格显示 **"0"** 与浅橙色填充；对照其他三产品 70.5/74.8/69.3 的深橙；同一 fixture 的 SAE 行显示 "未公开"区分正确。fixture `safety[0].value=0.0, disclosure_state=已公开, numerator=null, denominator=null` —— 没有 n/d 的"已公开 0" 在临床不可能（任何 anti-IL-13 16 周必出现注射部位反应、感染等 TEAE），且与页面文案 "未公开、未报告或不适用保持为状态，不以零值替代" 直接矛盾 | 数据侧把 `fixture-product 任何TEAE` 的 `value` 改为 null、`disclosure_state` 改为 `未公开`，或在 n/d 上提供真实0/真实分母；同步修正 product-trial profile 表里出现的 "已报告零值" 伪状态（与 schema 枚举不符）|
| **P0-2** | 疗效与安全性矩阵 | 全宽 | 进入 efficacy-safety-matrix.html | 整页只剩 "矩阵暂无可绘制覆盖值" 灰色卡片与1 张空表；缺气泡图 = 缺 B 类核心定位视图（产品 profile §3：横轴疗效 / 纵轴 TEAE / 气泡大小样本量）| 数据侧新增 `matrix` 节点（含 `x_value/y_value/size/产品/试验/披露状态`），或在矩阵页顶部加一段说明：当前 fixture 仅含 efficacy 与 safety 两个数组，矩阵需要同试验同时间窗的配对三元组，缺则按 v1.2 走 fail-closed 渲染整页而不是占位 |
| **P0-3** | 基线 / 试验完成情况系列 | 全宽 | 进入 baseline-overview / baseline-demographics / baseline-severity / baseline-disease-context / disposition-overview / participant-flow / adherence / loss-exit / screen-failure / rescue-treatment / prohibited-medication / plan-deviation / trial-exposure-context / subgroups-supporting-evidence | 13 张 B 类核心页全显示 "暂无公开记录" + 表中12 列均为 "未列示 / 组别未列示 / 时间点未列示 / 未报告"。项目合同 v1.2 §3 要求 B 类必须提供基线人口学、严重程度、随机/治疗/完成/退出、依从性、失访、筛败、退出原因、补救治疗、禁用药、PD 等图表与完整表；目前 fixture 数据集只有 efficacy(8) 与 safety(16) 两数组，缺 baseline / disposition / exposure / subgroup；占位页未替 fixture 注入数据即发布，违反 "A missing key-evidence threshold is fail-closed" | 数据侧注入 baseline 与 disposition 系列（至少人口学、IGA/EASI 基线、随机/完成/退出计数），或在导航里把这些占位页直接隐藏，提示 "fixture 未覆盖本节，预计 v1.3 注入"。当前占位页面不应作为正式门户成员 |

### P1 · 视觉/交互契约| # | 页面 | 宽度 | 复现 | 观察 | 最小修复建议 |
| --- | --- | --- | --- | --- | --- |
| **P1-1** | 全站页头 | 1440 / 1280 | 看截图 `overview_1440x900.png` 第 0-110像素 | logo + 标题组合在 1440 / 1280 出现 "特应性皮炎临床试验结果比" + "较" 拆3 行；header 高度被撑高至 100-110px，使首屏可视区损失近 1/8 | `.site-header__title` 加 `white-space: nowrap` 或允许横向滚动；logo 区压缩为左 121×25 + 右标题单行；或把标题改为 "B 类·特应性皮炎" 短副题 |
| **P1-2** | 全站页头 | 1024 / 768 | 看 `overview_1024x900.png`、`overview_768x900.png` | 768 时4 个分组下拉挤到第 2 行；搜索框被裁 | 1024 起改 hamburger 单列；保留 768 仅显示 logo + 标题 + "菜单" |
| **P1-3** | 安全性 / 全表 | 全宽 | 看 `safety_1440x900.png` 第一张热图 | X 轴只有一个 "比较" 列；治疗组 only，**完全缺少对照组**；项目合同 §3："横向比较必须同时显示试验组和安慰剂/对照组效应"；当前 fixture `safety[].arm` 全是 "治疗组" | 数据侧注入对照组 safety 行；或在图例/标题处明示 "当前仅披露治疗组，对照组待补" |
| **P1-4** | 安全性 / 全表 | 全宽 | 看 `safety_scroll1.png` 第三张热图 "多项可比指标 · 安全性：特别关注不良事件" | 4 行 AESI 分别是泰瑞奇-超敏反应 / 安澜-注射部位反应 / 瑞格替尼-带状疱疹 / 诺维-超敏反应 —— **4 个不同事件被强行同列对比**；医学经理会读成 "产品 A 安全性 ≈ B安全性"，实为 apples-to-oranges |拆为 4 张子图（每个事件一张）或在 X 轴注明 "各产品最常报告的 1 项 AESI（产品间不可比）"，禁止诱导对比 |
| **P1-5** | 首页 / 全页 | 全宽 | 点页头搜索 "澄明" | 提示 "未找到匹配页面或数据"——但澄明-3 是4 个试验之一；搜索索引只覆盖页面 slug，未包含产品/试验关键字 | 在 `data/search-index.js` 中追加 {keywords:[…], slug:`trials/nct-fixture-301`, title:`澄明-3`} 类条目 |
| **P1-6** | 全页"筛选条件"折叠面板 | 全宽 | 点击 "筛选条件 +"展开 | 8 个维度（靶点/机制、试验、组别、终点/事件、时间点、时间窗、披露状态）骨架齐全，但所有 option button innerText 为空，无法选择；快速筛选 chip（产品）可用，下钻筛选失效 | 注入 filter options 数据源（target/trial/group/element/time/time_window/disclosure_state 各维度的可选枚举）并绑定 data-option |
| **P1-7** | 全站 | 1280 / 1024 | 看 efficacy / safety柱图图例 | ECharts 默认 palette `#5070dd / #b6d634 / #ff994d / #0ca8df / #fb628b / #785db0 / #3fbe95` 与康哲色卡不符；对照组蓝 #5070dd ≠ 运营蓝 #407AAA（差 ~12色调）、绿 #b6d634 ≠ 数统绿 #587B3B | 把 ECharts `color` 改为康哲部门色：[#FF9900, #407AAA, #587B3B, #A85F34, #F79646]，或固定 `kz-orange /运营蓝 / 数统绿` 三色 |
| **P1-8** | 全站表格 | 全宽 | 看任意 chart-table | 表体14px（满足 ultra exception）；"快速筛选产品" chip 14px、过滤选项 button 14px、chart-legend 13px、evidence pinned hint 12px——违反 core.md §0.7 正文/标签下限 16px | 把 filter chip 与 legend 升16px；axis-label/表体 14px 仅限 ultra + 满足 §13.3 时保留 |
| **P1-9** | 全站 ECharts | 全宽 | 读取 chart option | axis-label fontSize=12（超14px ultra floor） | 全部 axis/legend 升 ≥14 |
| **P1-10** | 全页 | 全宽 | 点 "固定此条" 按钮 | 底部 `.kz-evidence-pinned` 区块在点击前后均为空，无内容注入；该功能实为占位 | 接入 pinned list 状态，把已 pin 的图表/记录插入 pinned区块，否则隐藏该区块 |

### P2 · 信息密度与中文原生

| # | 页面 | 观察 | 最小修复 |
| --- | --- | --- | --- |
| **P2-1** | 全站 | efficacy 表的 "分子/分母" 列对所有已公开 record 都写 "未列示"——医学经理无法验证率 | 在 fixture 已公开 record 上回填 numerator/denominator，或在表头加 tooltip 说明"原文未给 n/d" |
| **P2-2** | 首页 / 安全性 | 图表与表格之间用大量留白隔开，单页 docH = 7508-9049px，医学经理需滚动 8-9 屏才能看到完整基线/暴露页 | 在视觉策划上做"图组 + 表组"压缩（每产品 1 张图 + 1 张紧凑表），或将图表高度由 340px 调到 260px |
| **P2-3** | 矩阵 / 占位页 | "暂无公开记录" / "未列示" 用语在 13 张 B 类核心页出现 ≥100 次，占据约 30% 字符总量 | 把占位行折叠为单行 "本节暂无公开记录（fixture 未覆盖）"，避免反复12 列 × 多行 |
| **P2-4** | 全站 | chart-titles 16px 粗体 + 行高 26.4px，与正文16/26.4 重叠，章节层级弱 | H2 升 20px /28px 或加左侧品牌橙竖条（已有，但与 body 节奏冲突） |
| **P2-5** | 全站 | 页脚仅一行小灰字 "康哲药业临床试验结果比较；数据截止 2026-07-31"，缺产品中心-医学部门固定槽（core.md §17 错误清单中明列页脚 "数据截止 + 来源" 格式） | 改成 "产品中心-医学部｜2026 年 7 月"（左）+ "数据快照 2026-07-31"（右）双槽 |
| **P2-6** |矩阵页 | 缺分轴说明（横轴 = 疗效？纵轴 = TEAE？气泡大小 = 样本量？） | 在 chart-card 标题下加 1 行 "横轴 EASI-75 应答率（治疗组）／纵轴 TEAE 发生率（治疗组）／气泡 治疗组样本量" |
| **P2-7** |试验档案 | "返回档案索引" 按钮放在 info card 右上，路径层 "产品与试验档案 / 澄明-3" 是纯文本 | 改用真实 `.kz-crumb` 控件（首页 > 产品与试验档案 > 澄明-3），并把"返回档案索引"合并到 crumb 末 |
| **P2-8** | 全站 chart | 单一系列气泡图配色与其他图无区别，没有"医疗主责/运营/数统/PV"识别 | 系列颜色按 §0.8.2 部门色映射：fixture=医学橙，competitor=运营蓝，oral=数统绿，historical=PV棕 |

### P3 · 审美与可读性

| # | 页面 | 观察 | 最小修复 |
| --- | --- | --- | --- |
| **P3-1** | 全站 | 表格隔行底色缺失，纯靠边框分区 | 给 `.kz-chart-table tbody tr:nth-child(even)` 加 `#F8F9FA` 底 |
| **P3-2** | 全站 | chart-card 28px padding + 浅橙边，区分度尚可，但与 page-head 视觉重复 | chart-card 改为左边4px 实心橙 + 浅底 |
| **P3-3** | 全站 | footer 字号 14px 比正文 16px 小2px，缺乏"页脚=最次要"层级 | footer 11-13px，色 #808080 |
| **P3-4** | 全站 | search input 与 nav 同高 36px，placeholder "搜索页面或关键词" 16px | placeholder 用 14px 灰色，避免与 active文本混淆 |

## 4. 视觉与中文原生性评价

**事实（可直接观察）**：

- 主强调 `#FF9900`、副强调 `#FFCC00`、风险红 `#C00000` 三个 CSS 变量均存在并使用- 全站默认浅底白 + 顶栏白底 + 橙激活条，符合 §0.8.3A 强制合同
- 字体栈 `"Microsoft YaHei", 微软雅黑, "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif`，含 macOS PingFang fallback
- 中文文案"特应性皮炎临床试验结果比较""筛选条件""数据依据""未设置筛选""阅读提示""适应症""观察截止"等均为临床/汇报语境原生表达，未出现 prompt/log/state 字段
- 页脚"康哲药业临床试验结果比较；数据截止 2026-07-31"为日期型合规文案
- 表头/caption "完整数据表" 等使用 aria-semantic caption + scope=col

**推断与审美建议**：

- 品牌橙黄识别位正确（logo + 顶栏 + 卡片左边线 + 数据依据胶囊），但 ECharts 默认 palette 让治疗组橙与对照组蓝与康哲运营蓝 #407AAA 出现轻微色相偏差，敏感用户会察觉- 第一屏叙事良好（标题 + 阅读提示 + 适应症 + 截止 + 筛选），但首屏不出现数据图，与"首屏直接看到最重要的竞品格局"的产品承诺冲突，需要把图表区上移或在 nav 折叠区嵌入 mini-chart
- 安全矩阵"矩阵暂无可绘制覆盖值" + 5 张 B 类页"暂无公开记录"，把占位语直给临床用户，礼貌但削弱信心；建议占位改为 "本节数据未在当前 fixture 覆盖范围；尝试疗效 / 安全性 已有完整数据"，并把未覆盖页用置灰样式标记## 5. 是否存在 P0/P1

**存在 ≥ 6 个 P0/P1，Task 6.9 当前状态不可接受**：

- P0-1 数据完整性：fixture `safety[0].value=0.0 + 已公开 + numerator=null/denominator=null` 与安全性页面文案"不以零值替代"直接矛盾，是项目记忆反复警告的"零值 ≠ 未公开"红线
- P0-2 矩阵气泡图缺失：B 类核心定位视图未交付，整页仅 "矩阵暂无可绘制覆盖值" 占位
- P0-3 B 类 13 张基线/处置/暴露页全为占位：违反 v1.2 "A missing key-evidence threshold is fail-closed"，应隐藏占位而非发布
- P1-1/2 页头标题溢出：logo+标题在 1440/1280 拆 3 行，768 被迫隐藏搜索框
- P1-3 安全性缺对照组- P1-4 安全性 AESI 热图 4 行非同事件强行同列
- P1-6 筛选面板 8 个维度 option 全空
- P1-5搜索索引不含产品/试验关键字- P1-7 ECharts 配色偏离康哲色卡
- P1-8/9 字号 12-14px 违反正文16px 下限
- P1-10 "固定此条" 按钮无实际功能

**Codex 终验建议**：在未解决 P0-1/2/3 之前，不应进入"接受"状态。这些是数据契约与门户成员真实性问题，不是视觉细节。

## 6. 建议的最小下一步

1. **数据侧（执行 P0-1/2/3）**：在 fixture `output/acceptance/task-6.9/site/data/report.js` 中
   - 修正 `safety[0].value=0.0` → 改为 null 且 `disclosure_state=未公开`，并把 `已报告零值` 伪状态从渲染器移除
   - 新增 `matrix` 节点（每个产品/试验配 x_value=疗效指标值、y_value=TEAE 发生率、size=样本量），矩阵图恢复
   - 至少为 fixture-product 与澄明-3 注入 baseline / disposition 真实记录（人口学、IGA、EASI、随机/完成/退出/退出原因），让 5 张基线/处置页有真实图形而非 "未报告"
   - 给已公开 efficacy record 回填 numerator/denominator
   -注入对照组 safety 行

2. **渲染侧（执行 P1）**：
   - `.site-header__title` 设 `white-space:nowrap` + 略缩字号至 14px，或允许截断；导航 ≤1280 折叠为 hamburger
   - 在 `assets/charts.js` 把 ECharts 默认 color 改为康哲部门色（`#FF9900 / #407AAA / #587B3B / #A85F34 / #F79646`）
   -全文 axis/legend fontSize ≥14
   - 把 search-index 扩展至产品/试验
   - 修复 `kz-b-filter-group` 的 option 数据注入，使 8 个维度可选   - 移除 "固定此条"按钮或真正实现 pin列表

3. **视觉审阅闭环（执行 P2/P3）**：在数据 + 渲染修完后，回到本审阅方法重做 1440/1280/1024/768 四视口验证；尤其确认   - 首屏 ≤ 800px 视口能看到 ≥1 张数据图
   - 安全矩阵气泡图渲染且 X/Y/S 三轴有明确说明
   - 13 张占位页中至少 6 张呈现真实图形 + 真实表格
   - 泰瑞奇单抗 TEAE 行不再出现 "0" + 浅橙填充（要么是"未公开"灰，要么是已公开的真实非零数值）

---

（审阅结束。本报告仅基于浏览器实测 + fixture JSON 反查；未修改任何源文件、未启动子代理、未访问 peer 输出。Codex 保留终验权。）
