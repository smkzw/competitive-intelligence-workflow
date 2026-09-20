I have all evidence. Producing the final independent visual review report.

---

# C 类竞品临床试验方案设计门户 — 独立视觉验收Runner-managed path: `runs/tests/ci-phase7-task75-minimax-visual-review.md`

## 0. 连通与身份

- **评审身份**：`pi/cms-router/minimax-m3`（独立视觉测试）。仅只读检查，未修改任何站点、源码、测试或截图，未启动会商，未调用后备模型。
- **冻结目录**：`reviews/ci-phase7-task75-report-c-portal/site/`（12 个 HTML + 4 个 NCT 详情 + assets + data）。
- **复算摘要**：`find . -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256` → **`47bb95b23ff74a12c83510726e8ea7e2ab4394e5c5fb185a7ab81fb9ca619d57`**，与会商上下文中声明的冻结摘要逐字符一致（已对比）。
- **截图批次**：观察目录 `observations/medical-manager-attack.json` 报告 `120` 页 × `2` 引擎（Chromium + WebKit），`740/740` 通过、`0` 缺陷。
- **数据来源**：4 个 NCT 登记快照（`fixtures/positive/c-atopic-dermatitis/sources/clinicaltrials/`）均进入逐试验详情与首页完整表格。

## 1. 实际查看的证据

视口覆盖 **1024 / 1280 / 1920**（PRD 接受范围），引擎覆盖 Chromium + WebKit，逐图复核：

| 页面 | 视口 | 引擎 | 截图 |
|---|---|---|---|
| 首页 | 1024 / 1920 | Chromium + WebKit | `chromium_overview_1024.png` / `chromium_overview_1920.png` / `webkit_overview_1024.png` / `webkit_overview_1920.png` |
| 入选标准 | 1024 / 1920 | Chromium + WebKit | `chromium_inclusion-criteria_1024.png` / `chromium_inclusion-criteria_1920.png` / `webkit_inclusion-criteria_1024.png` |
| 终点/时间点 | 1024 / 1920 | Chromium + WebKit | `chromium_endpoint-timepoint-matrix_1024.png` / `chromium_endpoint-timepoint-matrix_1920.png` |
| 样本量/分析集 | 1024 / 1920 | Chromium + WebKit | `chromium_sample-analysis-statistics_1024.png` / `chromium_sample-analysis-statistics_1920.png` |
| 设计模式 | 1024 / 1920 | Chromium + WebKit | `chromium_design-patterns_1024.png` / `chromium_design-patterns_1920.png` / `webkit_design-patterns_1920.png` |
| 试验档案（NCT02260986） | 1280 | Chromium + WebKit | `chromium_nct02260986_1280.png` / `webkit_nct02260986_1280.png` |
| 证据抽屉 | 1280 | Chromium + WebKit | `chromium_evidence_drawer_open_1280.png` / `webkit_evidence_drawer_open_1280.png` |

现场逐一核对的事实：

- 站点 `report-c.js` 的 `chartKind()` 将首页映射到 `design-coverage-matrix`（heatmap；`label.formatter` 对已报告格仅渲染"●"，对未公开渲染"未公开"），12 个设计要素 × 4 个试验。
- 站点 `overview.html` 的完整表格确实是 9 列（产品 / 试验编号 / 试验 / 设计要素 / 内容 / 时间点 / 量表 / 披露状态 / 数据依据），逐行 `tabindex=0`，点击打开抽屉。
- 站点 `design-patterns.html` 内嵌 `#kz-design-paths` 区段，给出**两条**候选路径：以 EASI 改善作为主要终点 / 以 IGA 达到清除或几乎清除作为主要终点，并各标注"主要取舍"。PRD 的"至少两条有证据支持的候选路径"达成。
- 证据抽屉在1280 渲染：12 行键值（产品 / 试验 / 组别 / 终点·事件·设计要素 / 量表 / 时间点 / 值 / 阈值 / 单位 / 分子 / 分母 / 披露状态 / 数据说明 / 来源版本 / 原文定位 / 简短原文）+ "加入对照"按钮，源版本 = ClinicalTrials.gov，"打开原文"链接到登记人读页。

## 2. 阻断项（按严重度）

### 🔴 高 — 首页与逐试验详情图完全失语，是首屏误导

**现象**：首页（`overview.html`）"试验设计要素概览"图表在 1024 / 1280 / 1920、Chromium / WebKit 一致渲染为 — 12 列热力格，11列为橙色实心 + 白色 "●"，仅最右侧"分析人群"列为浅灰 + "未公开"。四个试验的行看上去几乎**完全相同**，仅最后一格差异。

- **页面**：首页（`overview.html`）；首页"试验设计要素概览"（第一屏顶部主图）。
- **视口**：1024 / 1920（Chromium + WebKit）。
- **可复核现象**：`site/assets/report-c.js:344-396` 的 `matrixOption` 在 `kind === "design-coverage-matrix"` 时强制 `showFact = false`，`label.formatter` 只输出 "●" 或 "未公开"，**完全丢弃了元素事实值**（样本量、剂量、终点定义、时间点）。但页面 lead 写"呈现核心设计格局、关键模式和差异"——这与呈现出的"全部橙色点，差异 = 1 格"严重相悖。**首页图表对一名资深临床医学经理的判读价值 = 0**，并构成首屏误读风险（"看上去四个试验都完整"）。
- **页面**：逐试验详情（`trials/nct02260986.html`）。
- **视口**：1280（Chromium + WebKit）。
- **可复核现象**：CHRONOS 详情页"试验设计要素概览"也是同款 design-coverage-matrix，11 个橙色 ● + 1 个"分析人群"灰格——对单试验来说，**图表本身就是空话**：所有元素都在图上"已覆盖"，没有任何可读事实，无法帮医学经理快速定位差异。逐试验详情本应是"差异化呈现"，却被首页同款模板无差别复用。

**修复要点（仅指出，不改）**：将 `design-coverage-matrix` 的 `showFact` 改为 `true` 并把 `compactFact` 的12 字符上限提升到 ≥ 18，或在首页改用既有的 `treatment-structure-matrix / sample-size-bar` 组合突出真实差异。

### 🔴 高 — 设计模式页雷达图完全无法区分四个试验

**现象**：设计模式页（`design-patterns.html`）"试验设计要素覆盖"雷达图，**4 个序列完全重叠为同一颗小钻石**。Y 轴只有 4 个轴（目标人群 / 主要终点时间点 / 主要终点定义 / 随机与盲法），覆盖 4 个产品共 12 个设计要素中的 4 个。

- **页面**：`design-patterns.html`；"试验设计要素覆盖"。
- **视口**：1024 / 1920（Chromium + WebKit）。
- **可复核现象**：图例只有 NCT ID（无 CHRONOS / ADvocate2 / ADvantage / 奈莫利珠单抗疗效与安全性研究），四个序列因每个产品对四轴都"已报告"而退化到 `[1,1,1,1]` 同点，整张图对医学经理**完全无可分辨信号**。同一张图在 1024 还更小，更难看清。
- **联动问题**：图例使用纯 NCT ID（无中文/英文短名），与"试验设计要素覆盖"标题语义脱节；与样本量柱状图同样问题（下一条）。

**修复要点**：a)雷达 Y 轴覆盖 12要素或至少覆盖 ≥8 维；b) 图例 NCT +短名双标签；c) 数值由0/1 改为有梯度的"要素完整度"或改成 per-要素并列小图（small multiples）。

### 🟡 中 — 图与图例全用 NCT ID，中文临床语境未落地

**现象**：所有需要标试验的图（首页热力、雷达、样本量柱状、终点-时间点热力、入选标准热力）**仅使用 NCT ID**，过滤按钮在左侧列出了中文短名（如 "NCT02260986 · CHRONOS"），但图表本身不复用。

- **页面 / 视口**：首页 / 设计模式 / 样本量 / 终点时间点 / 入选标准 — 全部视口。
- **可复核现象**：
  - `report-c.js:374-379`（Y 轴）/ `:385-391`（label formatter）/ 图例 `trial` 字段：Y 轴 `data: trials` 直接来自 `row.trial_display_id`，只输出 NCT编号。
  - 雷达图图例 `series: trials.map(...)` 也只用 NCT ID。
  - PRD 允许"试验编号、药物通用名和必要缩写可保留"，但**完全省略中文/英文短名**让医学经理必须回查过滤按钮才能认出试验。对视觉敏感、不熟电脑操作的用户尤其不友好。
- **同时**：筛选条件侧栏里出现的"未公开 / 已报告值"等表达在图与表格中是统一的，但**9 列完整表格**里"披露状态"列里出现"已报告值 / 未公开"，与"不适用"等并列在同一列 — 这在医学语境下是对的，但首页没有出现任何"不适用"行（因为每行有具体字段），因此该列的语义稳定性在首页图表里完全不可见。
- **修复要点**：所有图 Y 轴 / 图例改为 "NCT ID · 短名" 双标签；同一字符截断策略在所有图上保持一致。

### 🟡 中 — 1024 视口"时间点"列被截断，事实表无法完整阅读

**现象**：入选标准 / 终点时间点 / 设计模式等页9 列完整表格在 1024 视口下，"时间点"列把"（筛选..." "(基线"截断在右边缘；"内容"列把"IGA达到0或1分，且较基线降低≥2分（第16周）"挤到换行，行高不一致。

- **页面**：入选标准 / 终点时间点 / 设计模式 / 试验档案。
- **视口**：1024（Chromium + WebKit）。
- **可复核现象**：`webkit_inclusion-criteria_1024.png`、`chromium_sample-analysis-statistics_1024.png` 中可见"（筛选..."和"(基线"被表格列宽截断，鼠标悬停才看到完整；`evidence_drawer_open_1280.png` 同一现象在 1280 也轻微出现——右栏抽屉压在表格上，"时间点"列右侧半字被压。
- **修复要点**：在 1024 视口改两栏布局（图左、抽屉右）以避免压字；或在表格 `td` 上加 `text-overflow: ellipsis` + `title`提示，避免半字截断。

### 🟡 中 — PRD 要求"图在前、表格在后"，但首页图表传递事实为 0

**现象**：PRD 4 行："图在前、同一事实集的完整表格在后；空白、未公开、不适用和路径未解析必须准确区分。"

- **首页图**没有事实（详见高项）——图与表格不在同一事实集上。图给"是否覆盖"，表格给"是什么"。
- **9 列完整表格**对"空白 / 未公开 / 不适用"区分明确：12 行出现 "已报告值" 与 "未公开"两种状态，"不适用" 仅出现在量表与时间点列。**状态切分做到了**。
- **"路径未解析"**字段（`unresolved_due_to_route`）在抽屉与表格中均未出现 — 实际 0 例，可接受。
- **修复要点**：把首页图的 `showFact` 打开（已在高项提），让图和表落在同一事实集上。

### 🟢 低 — 站点脚注日期与观察截止日期写在多处，缺唯一锚点

**现象**：footer写 "数据截止 2026-08-30"，首页 `kz-c-page-meta` 写 "观察截止：2026-08-30"，抽屉"数据说明"也带日期。**三处文案、同一日期**，无版本号或快照指纹可见。

- **修复要点**：在 footer 追加 `__SNAPSHOT_ID__ = snapshot-c-atopic-dermatitis-001` 与 `__ROW_SET_DIGEST__` 的截短指纹（8字符）以便人工对账。**不阻断**。

### 🟢 低 — 试验详情页 H1 用 NCT ID 而非中文/英文名

**现象**：`trials/nct02260986.html` H1 = "NCT02260986试验档案"，副元信息"试验名称：CHRONOS / 阶段：III期 / 地域：国际 / 观察截止：2026-08-30"。名号在 H1 之后才出现。

- **修复要点**：H1 改成 "CHRONOS · NCT02260986 试验档案" 或 "NCT02260986（CHRONOS）试验档案"，让首屏直接显示试验名。

## 3. 可接受项（不阻断）

- **首屏 1024 / 1280 / 1920 在不横向拖动时主图均可完整阅读**（首页热力图、样本量柱、雷达、热力图都能在视口内整体呈现）。
- **首屏中文导航/品牌行**正常渲染（"CMS 康哲药业 CHINA MEDICAL · 中重度特应性皮炎临床试验设计比较"），与 PRD "不解释 C 类报告或系统工作方式" 的简化首屏要求一致。
- **页面级筛选按钮"度普利尤单抗（Dupilumab）/ Lebrikizumab / 奈莫利珠单抗（Nemolizumab）"** 显示中英双语通用名，符合 PRD。
- **9 列完整表格**结构在所有页面一致：产品 / 试验编号 / 试验 / 设计要素 / 内容 / 时间点 / 量表 / 披露状态 / 数据依据。PRD 要求"九列表格"达成。
- **证据抽屉**：12 行键值表 + "打开原文"链接 + ClinicalTrials.gov 源版本 + 中文化的"未按组别拆分"等组别表达——这是整个门户最稳的一块。
- **候选路径**：`design-patterns.html` 的"以 EASI 改善作为主要终点路径"和"以 IGA 达到清除或几乎清除作为主要终点路径"两条路径并列、各带"主要取舍"，无排名。**PRD 要求达成**。
- **披露状态切分**：表格里"已报告值 / 未公开"出现正确，"不适用"出现在量表与时间点列，未出现 "None / null / Python None / 占位文字" 等。
- **中文临床表达**：诊断中文行文地道，未暴露程序员标签（无 kebab-case、URL 字段名、`__C_` 前缀、`status_matrix` 内部名等出现在用户可见文本）。
- **网页 / 抽屉键盘可达性**：观察报告 `passed_checks` 中包含大量键盘与 `aria-pressed` 校验；HTML 中 `tabindex=0` 写在表格行上；`aria-controls` / `aria-haspopup` 用于导航组抽屉。

## 4. 结论

**不通过（独立测试意见）**。

**核心理由**：
1. **首页与逐试验详情的第一张图（设计要素概览）全部失语**——首页在 4 引擎 × 3 视口下统一呈现为"4试验 × 12 要素中 11 橙 ● + 1 未公开"，与页面 lead "呈现核心设计格局、关键模式和差异"严重相悖。这是**首屏视觉**，对一位视觉敏感、不熟电脑的中文资深临床医学经理构成**直接误读**。
2. **设计模式页雷达图同样失语**——4 序列完全重叠为一颗小钻石，图例仅 NCT ID，无任何试验区分信号。
3. 上述两项并非局部打磨，而是 `report-c.js:344-396` 的 `showFact=false` 分支在首页/试验详情两类页同时启用造成的**系统性失语**；同文件 `chartKind()` 把首页固定为 `design-coverage-matrix`，没有差异化方案。

**可通过路径（不改码前提下提示）**：
- 把首页图切换为 `treatment-structure-matrix` 或 `sample-size-bar` 等真正承载事实的图（或在 overview启用 `showFact`），让"图在前、表格在后"在同一事实集上成立。
- 设计模式页雷达扩展到 8–12 轴、按维度分组，避免四个序列全部同分。
- 全图图例补 NCT ID + 短名双标签；9列表在 1024 视口加 `ellipsis` 与 `title`。
- 试验详情页 H1 调整顺序，让试验名出现在首位。

**Codex 最终验收权保留**：本报告仅为独立视觉测试意见。是否在 `final-candidate/site/` 之外重新出图、以哪些图替换首页与试验详情图、由 Codex 决定；本测试者未触任何文件、未启动会商、未声明最终通过。
