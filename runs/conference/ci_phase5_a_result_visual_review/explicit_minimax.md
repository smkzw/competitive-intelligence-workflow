The webkit safety screenshot confirms: products as rows (度普利尤单抗, 曲罗芦单抗, 来布利珠单抗, 奈莫利珠单抗, 阿布昔替尼, ...), safety dimensions as columns (任何TEAE, 任何SAE, 预先界定AESI, 鼻咽炎, 头痛). All 5 columns visible without horizontal scroll at 1280px. Chart appears before table (table is far below).

All evidence gathered. Let me write the report now.

---

# Pi / Minimax M3 独立视觉验收

## 实际操作与证据

**环境**：Chromium（headless via Playwright）1280×900/1800 视口；直接打开 `file://` 路径并以 DOM 度量与截图核对；附件中的5 张 PNG（chromium-overview-1280、chromium-safety-1280、chromium-safety-six-events-1280、webkit-overview-1280、webkit-safety-1280）均同步复核。

**1. 默认 1280px 下首页安全性矩阵与安全性详情页无横向溢出**
- `overview.html`：document/body滚动宽 = `1280`，main 滚动宽 = `1200`；首页 `[data-chart-id="home-safety"] .kz-a-heatmap` clientWidth = scrollWidth = `1100`，`getBoundingClientRect().right = 1190`，落在视口内（来自6 个 chromium 与 webkit×3 视口的 `browser-metrics.json`，第 1–3、10–12 行全部一致）。
- 行/列方向：行 =38 个产品，列 = 5 个关键安全性维度（任何TEAE / 任何SAE / 预先界定AESI / 鼻咽炎 / 头痛），与 brief「产品按行、关键安全性维度按列」一致（DOM 抓取 `data-heat-label="product"|"event"` 计数38/5）。
- `safety.html`：默认状态只有 1 个热图，grid `client=1100`=`scroll=1100`，5 列实际宽度 `221.938px 164.422px×3164.422px`，仍 `doc=body=1280`。

**2. 选择 6 个不良事件后自动拆成纵向两块、且无横向溢出**
- DOM 证据：`safety.html` 下选择 [预先界定AESI, 任何TEAE, 任何SAE, 常见AE谱, SKIN BACTERIAL INFECTION, Hand dermatitis] 后，`document.querySelectorAll('.kz-a-heatmap').length = 2`。
- 第 1 块：`gridTemplateColumns = '221.938px 164.422px×4'`，共 5 列；第 2 块：`gridTemplateColumns = '608.922px 451.078px'`，共 2 列（产品名 + 1事件）。
- 两块 `clientWidth = scrollWidth = 1100`；document/body 仍 = `1280`，无溢出。
- 截图 `chromium-safety-six-events-1280.png` 与本地截取 `six_first_block.png` / `six_second_block.png` 视觉确认两块上下排列、首块显示 5 列、首块尾部产品行（度普利尤单抗→TQH2722、SKB575 / HBM7575）行号连续、次块独立显示 Hand dermatitis 列（Tezepelumab=5%、其余"未公开"），与 `interaction-metrics.json` 中 `sixEventGrids=2, gridFits=[true,true], documentFits=true` 完全一致。
- 拆分逻辑落点 `assets/report-a.js:186`：`for (var offset = 0; offset < termData.length; offset += 5)`，固定 5 个事件为一块，故 6 → 2 块；视觉与代码一致。

**3. 报告不再只有少量数字；指定抽查值与发生率合法**
- `efficacy.html` 表格行数 = `6755`；`safety.html` 表格行数 = `10171`；且两页均存在大量以 "未公开" 之外的百分比单元格，幅度从 0.0% 到 84.6% 连续分布（首页热图可见 84.6%、84.6%、71.7%、71.3%、68.3% 等）。已不再「少量数字」。
- 抽样 4 个分数：
  - `178/543` 在 efficacy 表存在1 次（Rocatinlimab III期，EASI 75，第24 周，300 mg Q4W 治疗组，显示率 `32.8%`），与 `178/543=32.75%≈32.8%` 一致。
  - `411/602` 在 safety 表存在 1 次（曲罗芦单抗 III期，300 mg Q2W 治疗组，任何AE，显示率 `68.3%`），与 `411/602=68.27%≈68.3%` 一致。
  - `23/602` 在 efficacy 与 safety 各存在 1/2 次（safety 中为 曲罗芦单抗 300 mg Q2W + Initial Period Q2W，任何SAE，显示率 `3.8%`），与 `23/602=3.82%≈3.8%` 一致。
  - `150/510` 在 safety 表存在 1 次（克立硼罗 III期，AN2728 2% 软膏治疗组，任何TEAE，显示率 `29.4%`），与 `150/510=29.41%≈29.4%` 一致。
- 「人数直接显示为大于100% 的发生率」检查：对两页表格所有 `n/m` 形式文本运行 `n>m` 判定，结果数组为空；`browser-metrics.json` 的 `percentOver100` 字段在所有 18 个视口记录里也都是 `[]`；`interaction-metrics.json` 的 `efficacyPercentOver100=0`。无「>100%」渲染。

**4. 首页、详情页的图在表之前**
- 首页 `overview.html`：4 个 `.kz-a-summary` 块顺序为「竞争格局图(top=230) → 主要疗效柱状图(top=2149) → 关键安全性热图(top=2599) → 疗效/安全性散点(top=4547)」；表格出现在更靠下区域，热图与柱状图均先于任何明细表格。
- `efficacy.html`：单一 section 内 `kz-chart` top=638、`kz-a-table-wrap` top=938（差 300px），图先表后。
- `safety.html`：单一 section 内 `kz-chart` top=597、`kz-a-table-wrap` top=2576（差近 2000px，因热图本身纵向很高），仍图先表后。
- 截图 `overview_efficacy_area.png` 与 `overview_safety_area.png` 视觉确认：图表全部位于表格之上。

**5. 其他真实阻断项排查（针对本次两项修复）**
- 关键数值仍存在：表格里仍有大量 `0.0%` 行，但都属于"真实公开但发生率为 0"或"未公开显示"（前者有真实比例、后者是显式标注"未公开"），不构成数值缺失。
- 控制台：`browser-metrics.json` 全部 18 个 viewport 条目 `consoleErrors: []`，无 JS 错误。
- 4 个抽样之外，继续随机抽 `2/52=3.8%、50/75=66.7%、19/52=36.5%、121/505=24.0%` 等共 ~30 个样本，分母均 ≥ 分子，显示率合理。

## 阻断问题

无。本次两项修复（疗效/安全性数值不再稀疏、安全热图默认无横向溢出、6 事件自动拆成纵向两块且仍不溢出）均经 DOM 度量、抽样核对、视觉截图与 `browser-metrics.json` / `interaction-metrics.json` 三重证据验证通过。

## 非阻断建议

1. **首页热图首屏密度**：38 行产品在 1280 视口下需要滚动约 1700px 才能见底；建议在首页把热图固定窗口高度并加内部滚动，使医学经理首屏内能同时看到头/尾若干产品，减少上下翻转次数（不阻塞本次验收）。
2. **6 事件拆分后第 2 块空白较多**：次块 gridTemplateColumns 为 `608.922px 451.078px`，左侧产品名列在只有 1 个事件时显得过宽；可考虑把"零数据"块改为折叠为一条摘要行（如"其余产品未公开 Hand dermatitis"），或将单事件块退化为更窄的列表样式，减小纵向滚动（不阻塞）。
3. **首页热图仍有大量"未公开"灰格**：5 列里 3 列在大量产品上为"未公开"；属数据真实缺失，但可在热图下方挂一行"按事件查看公开度"的迷你摘要条，引导医学经理优先查看公开度高的列（不阻塞）。
4. **表头与英文术语残留**：表格中部分长字段仍以英文出现（如 `Baseline and Week 24`、`FAS: All randomized participants...`），与「中文原生」原则不符；属既有问题，非本次两项验收范围。
5. **筛选默认展开行为**：当前打开页面时事件/产品筛选区是折叠的，需点开"展开选择"才能看到选项；老用户不一定知道；建议在首次访问时把筛选区默认展开或加新手提示（不阻塞）。

## 结论

**通过**。两项修复在 1280px 默认宽度下：安全性首页/详情页热图均无横向溢出、6 事件自动拆为两块且仍无溢出；疗效/安全性表格行数从原"少量数字"跃升至 6755/10171 行，4 个抽样分数178/543=32.8%、411/602=68.3%、23/602=3.8%、150/510=29.4% 全部存在且渲染为合法发生率，无 ">100%" 显示。图表先于表格呈现，38 行产品与 5 个关键安全性维度默认全部可见。
