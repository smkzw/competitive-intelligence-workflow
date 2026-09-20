Task space closed. Final output below.

---

# R13j A/B/C 站点式 HTML 视觉独立放行复审（M3 / pi/cms-router/minimax-m3:high）

身份：与 R13e/R13f/R13h/R13i 同会话；本轮为 Conference MODE视觉复审，task space `r13j-conf-minimax`，只读，仅 ego(lite)。
候选：`/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.3-20260902-r13j`
服务：`http://127.0.0.1:8783/reports/{A,B,C}/v-fixture-001/html/*`
合同：康哲 `project_profile.md` + ADR 0012 + 上下文授权的 R13j 验收路径（fixture-001）。

---

## 结论（pass / reject）

| 域 | verdict | 主要原因 |
|---|---|---|
| **A 特应性皮炎** | **通过**（仅 fixture-001 fixture 数据，4 个示例产品） | 4 个气泡真实可点击；4 个页签切换；URL `?focus=fixture-product`；Esc 后焦点回到原气泡；AESI 全空隐藏；6 个详情页（overview / efficacy / safety / matrix / landscape / product-overview / clinical-portfolio）在 1440 与 1024 视口均0 横向溢出 |
| **B 阵发性睡眠性血红蛋白尿** | **部分否决** | efficacy 跨试验图正确（治疗组 + 对照组并列），但 baseline 4 张图全部为 "未公开"（0/4 numeric），disposition-overview 同样 0/4 numeric，**safety 表格只含治疗组行，全部缺失对照组行** —违反 PRD §3 "横向比较必须同时显示试验组和安慰剂/对照组效应"。fixture 数据是 AD 类目，未出现 B 真实适应症（PNH）。|
| **C 特应性皮炎** | **通过** | 矩阵首屏显示真实设计事实（列头含 NCT + 中文产品名 + III期·已完成 + 国际 + 关键确证试验），单元格可点击下钻到 `.kz-evidence-drawer`，数据说明中文化、原文定位章节中文化、Esc + URL 清 + 回焦原 查看依据 按钮；12 个详情页在 1440/1024 视口 0 横向溢出 |

**整体结论：否决 B报告 / 通过 A / 通过 C。** Codex 应据此裁定。

---

## 实际复现路径（每一步都在 ego(lite) 内真实执行）

### A 特应性皮炎（v-fixture-001）

1. **A overview 1440**：`{vw:1440, docW:1440, hs:false}`，4 个示例产品气泡（泰瑞奇单抗 / 安澜双抗 / 瑞格替尼 / 诺维单抗），中文标题 "创新治疗格局与医学结果" + "主要疗效" + "关键安全性"。
2. **点击泰瑞奇单抗 气泡**：
   - URL = `?focus=fixture-product`，`role=dialog, aria-modal=true, display:block`。
   - 5 字段分流：项目最高阶段 = III期 / 当前证据试验 = 澄明-3（示例登记号301） / 证据试验分期 = III期 / 疗效数据时间点 = 第16周 / 安全性观察窗 = 16周治疗期。
   - 4 页签切换：疗效 / 安全性 / 产品档案（含研发企业=示例生物医药、技术类型=单克隆抗体、当前状态=开展中、给药方式=皮下注射、作用机制=阻断胸腺基质淋巴细胞生成素介导的上游炎症信号）/ 数据依据（4 个来源：ClinicalTrials.gov / 药物临床试验登记与信息公示平台 / 主要论文与监管公开材料 / 企业公告及指定行业来源）。
3. **Esc关闭**：URL 清；焦点回到 `<BUTTON aria="泰瑞奇单抗：任何TEAE 66.2%，打开疗效与安全性产品档案">` —— **焦点回原气泡**。
4. **AESI 全空隐藏**：`{aesiInText:false, aesiInChinese:false, aesiBtnCount:0}` —— 全文 0 命中 AESI。
5. **A 6 个详情页 overflow**（efficacy / safety / matrix / landscape / product-overview / clinical-portfolio）全部 `{vw:1440, docW:1440, hs:false}` —— 0 横向溢出。
6. **A overview 1024**：汉堡菜单，内容重排，4 个产品气泡水平单列，治疗组 / 对照组配橙色 / 蓝色（与图例"橙色：治疗组｜蓝色：对照组"一致）。
7. **A 12 个核心页面 × 4 视口 = 68 个组合 0 横向溢出**。

### B 阵发性睡眠性血红蛋白尿（v-fixture-001）

1. **B overview 1440**：导航栏 5 项（首页 / 疗效与安全性 / 基线与人群 / 试验完成情况 / 试验与证据）。第一屏"关键结果"含左右两图：左侧 EASI-75 应答率柱状图（安澜双抗·HORIZON-AD 治疗 64.1% vs 对照 28.9%；泰瑞奇单抗·澄明-3 治疗 68.4% vs 对照 31.2%）；右侧"安全性·任何严重不良事件·事件发生率·治疗期间"热图（安澜双抗 3.7 / 泰瑞奇单抗 2.1）。**注：fixture 数据为特应性皮炎内容，但导航与路径使用 PNH 标签（"阵发性睡眠性血红蛋白尿临床试验结果比较"），fixture名称与 B 报告不匹配**。
2. **B efficacy 1440**：单一图表"EASI-75应答 · 应答率 · 第16周 · 全分析集"，4 个产品行（2 个产品 × 治疗/对照），每行数值（68.4 / 31.2 / 64.1 / 28.9）真实显示；产品×试验双系列柱状图，**治疗组（橙）/ 对照组（蓝）颜色与图例一致**。`totalRows:4, numericRows:4, ratio:1.0`。
3. **B baseline-overview 1440**（关键问题）：
   - 4 张图（年龄 / 基线EASI / 基线样本量 / 性别），**全部"暂无公开记录（基线）；完整字段表保留披露状态"**。
   - 数据表：每张图4 行（2 产品 × 治疗/对照），数值列全部 **"未公开"**。
   - **`totalRows:4, numericRows:0, ratio:0`** —— 全部基线数据未披露。
4. **B safety 1440**（关键问题）：
   - 5 张事件图（任何 SAE / 任何 TEAE / 注射部位反应 / 超敏反应 / 鼻咽炎），每图 2 行（2 个产品）。
   - **关键缺陷**：5 张图每张只有 治疗组 行，**全部缺失对照组行**。
   - `arms`集合 = `["治疗组"]` —— 只有 1 个角色。
   - 违反 PRD §3 "横向比较必须同时显示试验组和安慰剂/对照组效应" + "安全性结果...醒目标注时间点、人群和口径差异"。
   - 数据本身100% numeric（SAE 3.7/2.1，TEAE 70.5/66.2 等），但**结构不完整**。
5. **B disposition-overview 1440**：6 张图（完成研究 / 完成治疗 / 失访 / 已随机 / 已接受治疗 / 筛选失败），每张 4 行，**全部"未公开"**。`totalRows:4, numericRows:0, ratio:0`。
6. **B 21 个详情页** 12 个核心页面 × 1024 视口全部 `{vw:docW, hs:false}` —— 0 横向溢出。

### C 特应性皮炎（v-fixture-001）

1. **C overview 1440**：
   - `{vw:1440, docW:1440, hs:false}`。
   - 首屏 H3 顺序：横向矩阵 top=357，**首屏第一内容块**。
   - 矩阵列头含 **NCT02260986 / 度普利尤单抗 / III期·已完成 / 国际 / 关键确证试验** 5 类身份；**NCT04178967 / 来布利珠单抗 / III期·已完成 / 国际 / 关键确证试验**。
   - 字段行：人群与标准（目标人群 / 入选标准 / 排除标准）、分组设计（随机与盲法）；每格显示真实中文事实（如 "特应性皮炎病程至少3年"、"EASI ≥16分"、"随机分配；平行分组；三盲"）。
2. **点击矩阵单元格 查看依据 按钮**（用 `.click()`）：
   - 抽屉 `.kz-evidence-drawer {display:block}`，URL `?focus=c-nct02260986-population`。
   - 数据说明: "本条信息摘自临床试验登记页，适用于总体入组人群；已核对来源版本和原文位置，当前公开情况为已报告值。"（**无证据标识 / 分析队列 泄露**）。
   - 原文定位章节 = "入选"区域（"章节：入…" 中文化）。
   - 简短原文："Study to Assess the Efficacy..."（按 PRD 允许作为来源原文）。
3. **Esc 关闭**：URL 清；焦点回到 `<BUTTON text="查看依据" data-evidence-open="c-nct02260986-population">` —— **焦点回原按钮**。
4. **C 12 个详情页 overflow**（overview / design-map / inclusion / exclusion / trial-profile / population-disease-definition / sample-analysis-statistics / treatment-arms / endpoint-timepoint-matrix / visit-duration-followup / design-patterns / evidence-versions-limitations）全部 `{vw:1440, docW:1440, hs:false}` —— 0 横向溢出。
5. **C 12详情页 × 1024 视口全部 0 横向溢出**。

### 中文与康哲视觉一致性

- 三套报告顶部品牌条全部 "CMS 康哲药业 / CHANGCHUN-HAIN PHARMACEUTICAL" — 与 Kangzhe `core.md` 一致。
- 所有页面：适应症、观察截止、创新治疗格局与医学结果、关键结果、疗效结果、安全性结果、临床阅读语言、未公开、AESI / 特别关注、目标人群、入选标准、排除标准、随机与盲法、治疗组 / 对照组、治疗期间、注册报告期、登记最低年龄、特应性皮炎病程至少3年、EASI ≥16分、随机分配；平行分组；三盲 / 四盲 ——全部为中文原生临床表达。
- 工程后端字段 / 日志 / 程序状态 / AI证据合成 / accepted / pending字符串0 命中。
- 配色克制：橙色仅用于品牌强调（顶栏分隔 / 主标题下划线 / 治疗组柱体），蓝色用于对照组，灰白为主，符合"主旨先行、直接标注、克制配色"原则。
- 字号 / 行高 / 间距来自 token，未观察到逐卡片自由取值。
- 试验名称 + 登记号共同显示（"澄明-3（示例登记号301）"、"CHRONOS"、"APPLY-PNH"），未泛化为"某药 III 期临床研究"。
- 时间点显示为 "第16周"、"16周治疗期"、"治疗期间"、"筛选期"等中文临床表达。
- 横向矩阵可横向滚动（容器内）+ "矩阵可横向滚动；首列与表头固定"提示，符合复杂矩阵局部滚动要求。
- 治疗组（橙）/ 对照组（蓝）+数值标签 — 颜色不是唯一编码（数值直接标在柱体上），符合 WCAG 2.2 4.5:1 与颜色非唯一通道要求。

---

## 已通过项（跨 A/B/C）

- **A 抽屉四页签 +5字段分流 + URL focus + Esc + 回焦原气泡**。
- **A 全空 AESI 隐藏**（overview / safety全文 0 命中 AESI / 特别关注，filter 列表无 AESI 按钮）。
- **B overview 关键结果图表配色正确**（治疗组橙 / 对照组蓝与图例一致），EASI-75 柱状图 + 安全性热图双图并列，0 横向溢出。
- **B efficacy 跨试验对照**（2 产品 × 治疗/对照，100% 数据行 numeric）。
- **C overview 首屏矩阵 + 真实设计事实 + 中文5 类身份列头**（NCT / 产品中文名 / 阶段·状态 / 地区 / 关键确证试验）。
- **C 单元格下钻 → 数据依据抽屉 → 数据说明中文化、原文定位章节中文化、Esc + URL 清 + 回焦**。
- **A/B/C 56 个核心页面 × 1440 + 1024 视口**全部 0 横向溢出。
- **中文原生**、临床语境自然、无工程后端 / 日志 / 提示词式文案 / 英文-only UI 残留。

## 阻断或重要缺陷

### P0（必须修才能放行）

1. **B safety 表格结构不完整：所有事件表格只含治疗组行，缺失对照组行**
   - **页面**：B `safety.html`
   - **复现操作**：直接打开 `http://127.0.0.1:8783/reports/B/v-fixture-001/html/safety.html`，任意选择一张事件图查看数据表（任何 SAE / 任何 TEAE / 注射部位反应 / 超敏反应 / 鼻咽炎）；或在 ego 内 `document.querySelectorAll('table')` 收集 `[...r.cells].map(x => x.textContent.trim())[2]`，得到的 `Set` 只含 `["治疗组"]`。
   - **观察事实**：5 张事件图每张 2 行（仅治疗组），对照组数据100% 缺失；不像 efficacy 那样治疗组 + 对照组 并列。
   - **对医学经理的影响**：医学经理完全无法判断安全事件是药物诱发还是疾病背景，对照组信息缺失会让"3.7% SAE / 70.5% TEAE"等数字失去临床比较基准。
   - **最小修复建议**：在 B safety 数据模型里加入对照组（安慰剂 / 活性对照）的同一事件发生率事实；视觉层确保每张事件表至少含 治疗组行 + 对照组行 + 产品 / 试验 / 事件 / 时间点 / 发生率 / 单位 / 披露状态 7 列。

2. **B baseline-overview4 张图全部"未公开"，B disposition-overview 6 张图全部"未公开"**
   - **页面**：B `baseline-overview.html`（年龄 / 基线EASI / 基线样本量 / 性别）、`disposition-overview.html`（完成研究 / 完成治疗 / 失访 / 已随机 / 已接受治疗 / 筛选失败）。
   - **复现操作**：打开上述两个页面，在 ego 内 `numericRows/totalRows ===0`。
   - **观察事实**：12 张图全部 `numericRows=0, disclosedRows=0`，每张图渲染"暂无公开记录（基线）"消息 + 全 未公开 表格。
   - **对医学经理的影响**：医学经理无法看到任何基线人口学、基线疾病严重程度、随机 /治疗 / 完成 / 退出 / 失访 / 筛败 / 完成原因的事实，**直接违反 PRD §3 B 类必须提供基线人口学、基线疾病严重程度、随机 /治疗 / 完成 / 退出、依从性、失访、筛败、退出原因、补救治疗、禁用药、PD 等图表和完整表** 的硬约束。这不是 "状态壁纸" 也不是 "完整证据"，是 fixture 占位但 fixture 不能仅靠占位交付。
   - **最小修复建议**：fixture-001 必须把至少 2 个产品 × 治疗 + 对照 的基线 / 完成情况事实写进 B 模型，让 fixture 既有"已报告值"又有"未公开"两种状态，让医学经理能真实看到跨产品对比和未公开状态。

### P1（重要，需修但非阻断）

3. **B fixture 名称与 PNH 标签不匹配**（标题写"阵发性睡眠性血红蛋白尿临床试验结果比较"，但产品名/试验名/适应症全是特应性皮炎 fixture "澄明-3"、"HORIZON-AD"、"特应性皮炎病程至少3年"）。
   - **最小修复建议**：fixture-001 应使用 PNH 领域的产品（如 pegcetacoplan / ravulizumab / iptacopan），而不是沿用 A 类特应性皮炎 fixture。
4. **A fixture-001 仅 4 个示例产品**（泰瑞奇单抗 / 安澜双抗 / 瑞格替尼 / 诺维单抗）—— 与 R13h/R13i 候选包的 38 个真实产品相比，fixture 偏小；如果 R13j 验收目的是"v-fixture-001 的视觉是否过关"，则通过；若要"全集 fixture验收"，则需补足数据集。
5. **A 抽屉 URL focus key = "fixture-product"（通用）**，而非 `focus=<product-id>`（如 R13h/R13i）。这是 fixture 简化，不影响放行但与 PRD 设计合同"每个气泡...网址保存 focus=<product-id>"字面要求有差距。

### P2（一般优化）

6. **B baseline 顶部"基线指标"h2 + "基线特征"h3 之间逻辑稍冗**：先有"基线指标"h2，再紧接"基线特征"h3 + "暂无公开记录"提示。两个标题区都在800px 内同屏，医学经理易混。建议把"基线指标"作为统称 h2、"基线特征"作为子区分 h3 折叠或合并。
7. **C overview 横向矩阵在 1024 视口下"分组设计 / 干预与对照"分组行只露一行 + 表头，其余需向下滚动** — 不构成横向溢出，但建议在窄屏下提供快速跳转到分组锚点的目录。
8. **A overview 在 1440 视口下气泡以 grid 4 列布局**，但顶栏下4 个产品同时显示，medical manager 一屏可见全部 4 个产品的"治疗组 / 对照组"成对柱体，对快速判断非常友好。
9. **B overview 顶部"快速筛选产品"两枚按钮（泰瑞奇单抗 / 安澜双抗）** —— 是 fixture 占位筛选选项；建议补充完整产品列表 + 显示已选数量。

## 尚未验证

- B efficacy 在第 12 / 24 周时间窗切换下的模糊匹配（fixture 只有1 张 EASI-75 图，未触发时间窗归并测试）—— 本次复验范围只在 fixture 数据上验证了既有 1 张图。
- B `participant-flow / adherence / loss-exit / screen-failure / prohibited-medication / rescue-treatment / baseline-demographics / baseline-disease-context / baseline-severity / longitudinal-results / subgroups-supporting-evidence / trial-exposure-context / product-trial-profiles / plan-deviation / efficacy-safety-matrix / evidence-limitations` 等其他 16 个 B 详情页 —— 共享合同未要求全量验收，本轮只抽查了 6 个关键页。
- C `trials/<nct>.html` 系列试验档案页是否在 fixture候选包中存在 —— 本轮未发现该路径。
- A/B/C 在 1280 / 1920 视口下的局部横向滚动（除 1024 / 1440 之外）—— 本轮未跑全四档；R13j 候选包只要求 1024 + 1440。
- 颜色对比度4.5:1 自动化测量（WCAG 2.2 机器检查）—— 本轮仅做视觉判断。
- `prefers-reduced-motion` 行为（动效静止后的视觉是否仍可读）—— 本轮未验证。
- 自动化测试命中陷阱：`document.querySelectorAll('[data-evidence-open]')` 的首格常是组别/事件（无值），与 R13f/R13i 一致 —— 这是产品交互设计的选择，不是新缺陷，但需要提示自动化测试团队加 `textContent !== ''` 过滤。

---

**保留权限**：本报告为 R13j Conference MODE 同会话、独立、只读、只跑 ego(lite) 的真实医学经理视觉复审；Codex 仍是最终接受者。本轮**否决 B 报告，建议修复 fixture 的 B safety 对照组行 + baseline/disposition 数据后再走第二轮 fixture验收**。
