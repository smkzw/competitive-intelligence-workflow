I now have the final R11 evidence. The C trial detail page (NCT02260986 / CHRONOS) is clean, well-structured, native Chinese — trial name + phase + region + 4-card design view + design-elements table. Time to compose the final R11 follow-up report.

---

# 视觉复核：named_minimax_high_r11_followup (R11)

报告人：`named_minimax_high`（资深临床试验医学经理，视觉敏感、立刻要看比较）
模式：仅审阅 R11候选，不修改任何产物；本回复为正式 R11 视觉复核报告（runner-managed 路径 `runs/conference/ci-phase10-task102-visual-review-r6/named_minimax_high_r11_followup.md`，仅返回正文，不写盘）

## 复核范围

R11 接受根：`task-10.2-20260901-203000-r11/`（与 R1 / R5 / R6 / R9 不同的新一代候选）
- `a-real` site_digest `2154569e68d3…`、`run_digest 30c2fdaae5ba…`、`report-snapshot dc9d1e94…`，50 页
- `b-real` site_digest `b79c96191722…`、`run_digest b8c6d190f3d4…`、`report-snapshot ffbe11fd…`，32 页
- `c-real` site_digest `69f824aabd5f…`、`run_digest 4d9eed92098a…`、`report-snapshot 15475f4d…`，32 页
均与 R6 / R9 不同，确认是同一会话内的 R11 新一代候选。本轮新增1024 与 1440 两档视口覆盖。

实际打开的截图（仅 R11）：
- A：`a-real/verification/A/v1/screenshots/` — `a_overview__chromium__1024x768.png`、`a_overview__chromium__1440x900.png`、`a_overview__chromium__1920x1080.png`；`a_efficacy__chromium__1024x768.png`、`a_efficacy__chromium__1440x900.png`、`a_efficacy__chromium__1920x1080.png`；`a_safety__chromium__1024x768.png`、`a_safety__chromium__1440x900.png`、`a_safety__chromium__1920x1080.png`、`a_safety__webkit__1024x768.png`；`a_matrix__chromium__1024x768.png`、`a_matrix__chromium__1440x900.png`、`a_matrix__chromium__1920x1080.png`、`a_matrix__webkit__1024x768.png`、`a_matrix__webkit__1280x800.png`、`a_matrix__webkit__1920x1080.png`；`a_products_amlitelimab__chromium__1024x768.png`、`a_products_amlitelimab__chromium__1440x900.png`、`a_products_amlitelimab__chromium__1920x1080.png`。
- B：`b-real/verification/B/v1/screenshots/` — `b_overview / b_efficacy-safety-matrix / b_baseline-overview / b_disposition-overview / b_adherence / b_loss-exit / b_plan-deviation` 在 1024 / 1280 / 1440 / 1920 四个视口 × Chromium / WebKit 两个引擎下完整截图。本轮重点看 1024 与 1440。
- C：`c-real/verification/C/v1/screenshots/` — `c_overview / c_treatment-arms / c_inclusion-criteria / c_exclusion-criteria / c_trial-profile / c_trials_nct02260986` 在 1024 / 1280 / 1440 / 1920 × Chromium / WebKit 下完整截图。

`report.json` 全部 `ok=true`；本判断仍以肉眼看到的 PNG 为准。

## 逐项复核### 1. A 类（疗效 / 矩阵 / Amlitelimab / 1024 矩阵可读性）

- **疗效数值与对照填充** — `a_efficacy__chromium__1024x768.png` 与 `a_overview__chromium__1024x768.png`：在 1024 chromium 下，10 个竞品的治疗组/对照组成对柱全部绘制：度普利尤单抗 51.3%/14.7%、曲罗芦单抗 49.1%/33.3%、来布利珠单抗 58.8%/16.2%、奈莫利珠单抗 43.5%/29%、阿布昔替尼 23.7%/7.9%、乌帕替尼 84.5%/12.1%、巴瑞替尼 18.7%/8.8%、芦可替尼乳膏 62.1%/24.6%、克立硼罗 48.5%/29.7%。**治疗组与对照组并列绘制，比例对且无0 替代。**
- **终点 / 时间点 / 分析人群中文原生性** — 同一截图：每个竞品行下小字明确给出 `EASI-75 / 第16周`、`EASI-75 / 第52周`、`IGA 0/1 / 第12周`、`EASI-75 / 第8周`、`IGA 0/1 / 第29周`。**全部为中文临床表达**（规范 §5 "时间点显示第24周、治疗期间等中文临床表达，不显示 24week 等拼接标签"）。未发现 EASI / IGA / vIGA-AD 等标准缩写被翻译腔或拼接标签替代。
- **Amlitelimab 在矩阵中出现** — `a_matrix__chromium__1920x1080.png`（含 legend 截图）：气泡图 legend 第1 项 = Amlitelimab；图内气泡 "Amlite…"（位置 X≈35%，Y≈80%）；第 6 项 = 611 (SSGJ-611)。**Amlitelimab 三维度（疗效 / 安全性 / 治疗组样本量）已具齐，纳入气泡图。**
- **1024 矩阵首屏可读** — `a_matrix__chromium__1024x768.png`：图例单行（`横轴：越靠右…| 纵轴：发生率（越低越靠上）| 固定量程避免放大细小差异`）位于图上方独立行；Y 轴0.0% / 25.0% / 50.0%刻度清晰不重叠；6 气泡位于图右侧。**1024 下无横向滚动**（气泡图占满内容列，不溢出右边界）。
- **Amlitelimab 产品详情** — `a_products_amlitelimab__chromium__1024x768.png`：基本信息 + 作用机制与给药双卡 — 研发企业 Sanofi / Kymab、开发地域 中国/境外、最高阶段 III期（已终止）、当前状态 2026年7月停止特应性皮炎开发、阻断 OX40L 共刺激信号、靶点 OX40L、技术类型 单克隆抗体、给药方式 皮下注射。临床开发组合显示 NCT06130566（COAST 1，核心，III期，全球/登记所列地区，601，已完成）。**中文原生，未见英文 UI 词渗漏。**

**A 类逐项验证：通过。**

### 2. B 类（依从性 / 失访退出 / 方案偏离 / 1024 + 1440）

- **基线 vs 完成情况语义分离** — `b_baseline-overview__chromium__1440x900.png` 与 `b_disposition-overview__chromium__1440x900.png`：基线页面显示"基线特征 / 基线样本量（人）"成对柱（125/121/135/69 等），完成情况总览页面显示"试验完成情况 / 受试者人数"。**两页度量族不同**。
- **依从性 = 相对剂量强度** — `b_adherence__chromium__1024x768.png`：图表标题 `依从性 | APPLY-PNH · 相对剂量强度`，Y 轴 40–120。柱值 99.6（治疗组，橙）与 100.6（对照组，蓝）。**R6 P0-新1 闭合**：依从性页面终于渲染相对剂量强度（% / 中位百分比），不再复用受试者人数。
- **失访与退出 = 受试者人数** — `b_loss-exit__chromium__1024x768.png` 与 `b_loss-exit__chromium__1920x1080.png`：图表标题 `失访与退出 | APPLY-PNH · 受试者人数`，X 轴6 类目（停止治疗治疗组 / 停止治疗对照组 / 退出研究治疗组 / 退出研究对照组 / 停止治疗原因治疗组 / 停止治疗原因对照组），Y 轴 0–10，柱值 1/0/0/0/1/0。下方"失访与退出数据表"含 列：产品 / 试验 / 完成情况字段 / 组别 / 时间点/期间 / 分析人群 / 状态 / 分子 / 分母 / 数值 / 单位 / 披露状态；首行伊普可泮 (iptacopan) / APPLY-PNH / 停止治疗 / 治疗组 / 随机至第24周 / 随机化人群 / 已报告 / 未列示 / 62 / 1 / 未列示 / 已报告值。**"未公开"状态在数据表中明确。**
- **方案偏离 = 显式未公开** — `b_plan-deviation__chromium__1024x768.png`：图表标题 `方案偏离 | APPLY-PNH · 受试者人数`，**主图区域为橙色 callout "暂无公开记录（试验完成情况）；完整字段表保留披露状态"**。下方保留"方案偏离数据表"含完整字段（产品 / 试验 / 完成情况字段 / 组别 / 时间点/期间 / 分析人群 / 状态 / 分子 / 分母 / 数值 / 单位 / 披露状态）。**R9 P0-新7 闭合**：方案偏离不再用5 根贴底柱 + 1 根 125 孤立柱制造误导，而是显式声明"暂无公开记录"。**
- **图先表后** — 上述三页均为先图表 +后续数据表结构（先图，后表）。
- **度量族正确且无单位混入** — 依从性页面 = 相对剂量强度（%）；失访与退出 = 受试者人数；方案偏离 = 受试者人数 + 显式未公开；试验完成情况总览 = 受试者人数（已完成治疗 / 停止治疗 / 退出研究 / 筛选失败）。**R6 P0-新1（B 三页同图）整体闭合。**
- **B 矩阵气泡邻接问题** — `b_efficacy-safety-matrix__chromium__1440x900.png`：拉武利尤单抗 / 可伐利单抗 / 伊普可泮 三个气泡分别落在 X ≈ 0 / 5 / 80，Y ≈ 80 / 75 / 80；产品名分别印在气泡右侧或下方；**三个气泡互不重叠，标签间距充足**。R6 P1-新6（气泡邻接）闭合。

**B 类逐项验证：通过。**

### 3. C 类（分组 / 入排 / 试验详情）

- **安慰剂匹配使用中文通用名** — `c_treatment-arms__chromium__1024x768.png` 与 `c_treatment-arms__chromium__1920x1080.png`：分组、干预与给药结构表 cell 显示 `阿姆替利单抗：皮下注射 / 安慰剂：皮下注射` 与 `安慰剂`（中文通用名），并附产品试验期 `阿姆替利单抗：第36周` / `阿姆替利单抗：第24周`。**安慰剂匹配现使用中文通用名，无 "placebo"渗漏。**
- **入排标准比较可定位到评分 / 阈值 / 时间点** — `c_inclusion-criteria__chromium__1920x1080.png`：入选标准表按试验分行显示差异化文本：NCT06241118 AQUA "登记入选标准：年龄≥12岁 / 特应性皮炎病程≥1年 / 既往生物制剂或口服JAK抑制剂疗…"；NCT06130566 COAST 1 "登记入选标准：基线vIGA-AD为3或4分（筛选期）"；NCT05651711 ROCKET-Hori… "EASI≥16分（筛选期）"；NCT05608343 Diflamilast… "BSA≥5%（筛选期）"；NCT04773600 罗氟司特特应性皮炎研究 "登记入选标准：特应性皮炎病程≥6个月（儿童≥3个月），且筛选前4周病情稳定、无显著加重（筛选期）"。**评分（vIGA-AD/EASI/BSA）+阈值（≥12/≥16/≥5%/≥6个月）+ 时间点（筛选期）三项均按试验列出，可逐试验对比。**
- **入排标准中文原生、无英文原文渗漏** — `c_inclusion-criteria__chromium__1024x768.png` / `c_exclusion-criteria__chromium__1024x768.png` / `c_inclusion-criteria__chromium__1920x1080.png`：cell 中仅出现中文（如 `登记排除标准：影响特应性皮炎评估的皮肤合并症`、`当前或疑似显著免疫抑制…`、`存在影响特应性皮炎评估的皮肤合并症（筛选期）`）。**R6 P0-新2 / R9 P1-新10 完全闭合：R6 英文原文 `Participants must be12 years / v-IGA-AD of 3 or 4 / EASI ≥ / Skin co-morbidity / Treatment with a biological`全部不再出现。**
- **国际通用名处理** — 快速筛选 chip 采用 `度普利尤单抗 (Dupilumab)` / `奈莫利珠单抗 (Nemolizumab)` / `曲罗芦单抗 (Tralokinumab)` / `乌帕替尼 (Upadacitinib)` / `巴瑞替尼 (Baricitinib)` / `鲁索利替尼 (Ruxolitinib)` / `Amlitelimab` / `Rocatinlimab` / `Tapinarof` / `Diflamilast` / `罗氟司特` —— 中文通用名为首，国际通用名以括号补足，符合规范 §2 "药物通用名、试验编号、标准缩写可保留"。
- **试验详情** — `c_trials_nct02260986__chromium__1440x900.png`：试验档案页面 — 试验名称 CHRONOS、阶段 III期、地域 Australia/Canada/Czechia/Hungary、观察截止 2026-07-31；4 列卡片（目标人群 / 给药方案 / 主要终点定义 / 计划或实际样本量）显示 `登记最低年龄：18岁 / 特应性皮炎受试者` / `度普利尤单抗剂量300 mg、600 mg每周1次；含负荷剂量：第16周` / `IGA达到0或1分，且较基线降低≥2分（第16周）` / `740`。**中文原生，无英文 UI 词混入。**

**C 类逐项验证：通过。**

## 跨 A/B/C 新增 / 残留缺陷

- **P1-新1（A / B / C 顶部 1024 折叠为单一"菜单"按钮）** — 在1024 chromium /1024 webkit 下，A 首页 / A 矩阵 / B 首页 / B 依从性 / C 首页 / C 入选标准 / C 分组与给药 等多页顶部仅显示右上角一个"菜单"按钮；而 A efficacy / A safety / A matrix / A amlitelimab / B 矩阵 / B 完成情况 / B 基线 / C 试验档案 / C 入选标准（在 1920 chromium 已展开）等大部分非首页 1024 仍可访问顶栏。三套顶级域名内仍存在"首页 1024 折叠 vs 内页 1024 展开"的不一致，但用户体验上不阻断比较信息读取。**修复 — 把 A / B / C 顶部导航在 1024 下统一为"折叠 OR 展开"策略中的同一种。**
- **P1-新2（A 矩阵 1024 气泡图下限可能截断）** — `a_matrix__chromium__1024x768.png`：气泡图位于页面靠下边缘，部分气泡（如 GR1802 在100% / 100% 附近）已贴近页面底栏，可视但不富裕。**修复 — 在 1024 下给气泡图多预留 24–48 px 底部 padding 或允许图独立滚出。**
- **P2-新3（A 矩阵 1920 气泡图产品名缩写）** — 图内气泡"产品 611" 显示为 `产品 611` + 数字；Amlitelimab 在 1920 图内显示为 "Amlite…"（被气泡圆周截断）。Legend 提供完整名称（`Amlitelimab` / `611 (SSGJ-611)`），但图内首字缩写较老花医学经理不友好。**修复 — 气泡小时显示试验代号缩写，气泡大时显示产品名全称或同时显示。**
- **P2-新4（A 安全 1024 heatmap 列合并）** — `a_safety__chromium__1024x768.png`：热度图"预先界定AESI"列在第 1-2 行之间出现跨行合并区域（两行都显示 "未公开"，被一个合并的 cell 涵盖）；其它行仍按行展示。视觉上略不齐。**修复 — 在 1024 下若两行同值仍合并显示，给定一个 `data-grid-row-merged` 视觉提示（左侧虚线分隔）。**

确定性 vs 主观：
- 确定性硬性视觉缺陷 = {}。R11关闭了 R6 / R9 全部 P0；剩余 P1 / P2 全部为主观一致性问题。
- 全部 P1 / P2 不阻断"图先表后、首屏关键结果可用、中文原生、无横向溢出"四条核心交付要求。

## 逐报告判定与最小修补

按规范逐条核对 R11：

- **A 类：通过**。R6 全部 P0 / P1 + R9 P1-新10（气泡图表头）+ P1-新11（A 首页 1280 折叠）大部分闭合；剩余 P1-新1（1024 折叠）+ P1-新2（1024 矩阵底部）+ P2-新3（Amlitelimab 气泡内缩写）+ P2-新4（1024 heatmap 列合并）属于可后续处理的构图一致性遗留。
- **B 类：通过**。R6 P0-新1（B 三页同图）+ R9 P0-新7（B 首页 125 孤立柱）+ R6 P1-新6（B矩阵气泡邻接）全部闭合。B 在 1024 / 1280 / 1440 / 1920 × Chromium / WebKit 下依从性 / 失访与退出 / 方案偏离 / 完成情况四页面度量族正确、显式未公开、无单位混入。剩余 P1-新1（1024 折叠）同样可后续处理。
- **C 类：通过**。R6 P0-新2（C 入排 + 分组与给药 英文渗漏）+ R9 P1-新10 + R9 P0-新8（C1280 折叠部分）全部闭合。C 入选 / 排除 / 分组与给药 1920 已是中文原生、入排可定位到评分 / 阈值 / 时间点。剩余 P1-新1（1024 折叠）可后续处理。

整体判定：

- **R11 总体：通过。**
-三个 P0（依从性 / 失访与退出 / 方案偏离 三页同图、C 入排 + 分组与给药 英文渗漏、A 矩阵 1024 横向可读性）全部闭合，跨 A / B / C 未出现新的英文 UI词、横向溢出或视觉误导问题。
- 最小修补（不阻塞首版站点候选）：
  1. A / B / C 顶部导航1024 折叠逻辑统一（A 首页 / B 首页 / C 首页 三套顶级域名 1024 下不应同时存在"折叠 + 展开"两种行为）。
  2. A 矩阵在 1024 下给气泡图加24–48 px 底部 padding，避免 GR1802 等边界气泡贴底。
  3. A 矩阵图内气泡的产品名显示：气泡小时显示试验代号（如 SSGJ-611、SIM0718）；气泡大时显示产品名全称，避免 "Amlite…"截断。
  4. A 安全热度图在 1024 下给"预先界定AESI"列加合并行的视觉分隔（虚线或左对齐线）。
- 本视觉审阅员仅作"通过 / 否决"判断，不替产线写"已接受"；最终放行由 Codex 在收到本报告与同会 `visual_single_object` 同侪报告后，按其在主会场的优先级合并处理。
- 本评审未读其他审阅员输出，仅基于 R11 截图与 R11 实时 HTML 验证。
- R11 报告路径：`runs/conference/ci-phase10-task102-visual-review-r6/named_minimax_high_r11_followup.md`（runner 管理，本回复即正文）。
