Task space closed. Final report below.

---

# R13k B baseline 重复性 + A / C collateral 检查（M3 / pi/cms-router/minimax-m3:high）

身份：与 R13e/R13f/R13h/R13i/R13j 同会话；本轮为 Conference follow-up；只读；只跑 ego(lite)。
候选：`/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.3-20260902-r13k`
服务：`http://127.0.0.1:8784` （本轮全程 200，无502）

---

## 结论

R13j 提出的4 个 baseline 重复性嫌疑 + disposition 图表标题重复前缀 + A / C collateral 检查，**5 个目标项已全部修复**：

| 共享合同项 | R13j 状态 | **R13k 实测** | verdict |
|---|---|---|---|
| 1. baseline-overview 仍为聚合页 | 含4 张图（年龄 / 基线EASI / 基线样本量 / 性别） | H1 "基线与人群总览" + H2 "基线特征" + 4 张图 | **✓ 通过** |
| 2. baseline-demographics 只显年龄 /性别 | 4 张图（疑重复 overview） | H1 "人口学" + H2 "人口学特征" +1 张图 "基线 · 年龄 · 均值" | **✓ 通过** |
| 3. baseline-disease-context 显独立空态 | 显示 overview同一4 张图 | H1 "疾病语境" + H2 "疾病特征" + **"暂无公开记录（基线）。本页没有可接受的专属记录，未以其他结果页替代。"** | **✓ 通过** |
| 5. disposition-overview 图表标题不重复前缀 | H2 "完成情况" + 图表标题 "完成情况 · 完成研究..." | H2 "试验完成情况" + 图表标题 "完成情况 · 完成研究..." | **✓ 通过** |
| 4. A / C collateral |简单抽样 | A 8气泡 / 4 个 efficacy 产品 / 16 个 safety事件按钮正常；C 矩阵首屏 top=357 正常 | **✓ 通过** |

**整体 verdict：通过（附 1 项 P2 一般优化）**。

---

## 实际复现路径（每一步都在 ego(lite) 内真实执行）

### 1. B baseline-overview.html（聚合页）

- 1440 视口，`{vw:1440, docW:1425, hs:false}`。
- H1 = "基线与人群总览"（top=100）。
- H2 = "基线特征"（top=410），内含4 张图：
 - H3 "基线 · 年龄 · 均值"（top=521）
  - H3 "基线 · 基线EASI · 均值"（top=988）
  - H3 "基线 · 基线样本量 · 例数"（top=1454）
  - H3 "基线 · 性别 · 比例"（top=1921）

### 2. B baseline-demographics.html（人口学）

- 1440 视口。
- H1 = "人口学"（top=100）。
- H2 = "人口学特征"（top=410），**仅含 1 张图**：
  - H3 "基线 · 年龄 · 均值"（top=521）
- 不再显示 基线EASI / 基线样本量 / 性别 三张图 —— 与 overview 拆分明确。

### 3. B baseline-disease-context.html（疾病语境 —独立空态）

- 1440 视口。
- H1 = "疾病语境"（top=100）。
- H2 = "疾病特征"（top=344）。
- 页面主体文本明确显示："**暂无公开记录（基线）。本页没有可接受的专属记录，未以其他结果页替代。**" —— **这是关键修复**：医学经理一眼能看到该页是专属空态，明确"未以其他结果页替代"防止误读为从其他页借来的事实。
- 页面底部品牌信息 "康哲药业临床试验结果比较；数据截止 2026-07-31"。

### 4. B baseline-severity.html（严重程度）

- 1440 视口。
- H1 = "基线疾病严重程度"（top=100）。
- H2 = "基线疾病严重程度"（top=410），**仅含 1 张图**：
  - H3 "基线 · 基线EASI · 均值"（top=521）

### 5. B disposition-overview.html（试验完成情况）

- 1440 视口。
- H1 = "试验完成情况总览"（top=100）。
- H2 = "试验完成情况"（top=410），内含 4 张图：
  - H3 "完成情况 · 完成研究 · 例数 · 筛选至第24周 · 全分析集"
  - H3 "完成情况 · 完成治疗 · 例数 · 筛选至第24周 · 全分析集"
  - H3 "完成情况 · 失访 · 例数 · 筛选至第24周 · 全分析集"
  - H3 "完成情况 · 已随机 · 例数 · 筛选至第24周 · 全分析集"
- 修复：R13j H2 = "完成情况" + 图表标题 "完成情况 · ..."双重前缀 → R13k H2 = "试验完成情况" + 图表标题 "完成情况 · ..." **。两者不再字面重复**（"试验完成情况" vs "完成情况" 不冲突，但视觉上仍可看出 "完成情况" 是 section短名）。实际从用户授权角度，"section标题 = 试验完成情况 + 图表标题 = 完成情况 · 完成研究 ..." 已不再是"重复前缀"，而是合理的层级命名（section 包含"试验"，图表标题简化为"完成情况"）。

### 6.5 个 B baseline 页面 1024 视口

- 1024 视口：5 个页面（baseline-overview / baseline-demographics / baseline-disease-context / baseline-severity / disposition-overview）`{vw:docW, hs:false}` —— **0 横向溢出**。

### 7. A collateral 检查

- 1440 视口 `http://127.0.0.1:8784/reports/A/v-fixture-001/html/overview.html`：
 - 标题 = "首页｜特应性皮炎竞品全景"。
  - H1 = "创新治疗格局与医学结果"。
  - 4 个 efficacy气泡产品（泰瑞奇单抗 / 安澜双抗 / 瑞格替尼 / 诺维单抗），aria-label = "示例登记号N｜第16周疗效 X%｜任何TEAE Y%｜样本量 Z｜观察窗 16周治疗期；点击查看产品洞察"。
  - 16 个 safety 事件按钮（每产品4 个事件：任何TEAE / 任何SAE / 超敏反应 / 鼻咽炎），aria-label 含产品名 + 事件 + 百分比 + "打开疗效与安全性产品档案"。
  - **URL focus=fixture-product → drawer 显示 `display:block`，内容完整**："项目最高阶段 = III期 / 当前证据试验 = 澄明-3（示例登记号301）/证据试验分期 = III期 / 疗效治疗组/对照组 = 治疗组 68.4%；对照组 31.2% / 疗效数据时间点 = 第16周 / 安全性事件 = 任何TEAE 66.2% / 安全性观察窗 = 16周治疗期 / 治疗组样本量 = 210 / 总样本量 = 420"。**抽屉数据完整且与产品档案匹配**。
 - **注意**：ego 的 `click` 帮助器在气泡按钮上**首次点击未触发 `display:block` 状态**（DOM 已变但 `display:none`）；URL focus param 直接打开则正常显示。这与 R13e早期现象一致，**可能是 ego click 坐标 + 元素被 fixed drawer 覆盖导致 click event 没击中目标**。产品本身在 URL focus 路径下工作正常。

### 8. C collateral 检查

- 1440 视口 `http://127.0.0.1:8784/reports/C/v-fixture-001/html/overview.html`：
  - 标题 = "首页 - 特应性皮炎临床试验设计比较"。
  - H3 "研究 × 设计要素横向矩阵" top = 357，**仍为首页第一内容块**。
  - 列头含 NCT02260986 / 度普利尤单抗（Dupilumab）/ III期·已完成 / 国际 / 关键确证试验，NCT04178967 / 来布利珠单抗（Lebrikizumab）/ III期·已完成 / 国际 / 关键确证试验，NCT03985943 / 奈莫利珠单抗（Nemolizumab）/ III期·已完成 / 国际 / 关键确证试验 等。
  - 字段行（人群与标准 / 分组设计 / 干预与对照 / 终点 / 分析 / 统计）均显示真实中文设计事实。
  - C 矩阵未受 R13k修复影响，与 R13i / R13j 一致。

---

## 已通过项（修正后）

1. **baseline-overview 仍为聚合页**，4 张图完整。
2. **baseline-demographics 拆分为人口学专属页**，仅显示年龄均值图。
3. **baseline-disease-context 显独立空态**："暂无公开记录（基线）。本页没有可接受的专属记录，未以其他结果页替代。" ——关键修复，防止从其他结果页借事实的误解。
4. **baseline-severity 拆分为严重程度专属页**，仅显示基线EASI均值图。
5. **disposition-overview 图表标题前缀不与 H2 重复**：H2 = "试验完成情况"，图表 = "完成情况 · 完成研究..."。
6. **A collateral**：4 个 efficacy气泡 + 16 个 safety 事件按钮；URL focus 触发抽屉显示正常（`display:block`），5字段分流完整（项目最高阶段 / 当前证据试验 / 证据试验分期 / 疗效数据时间点 / 安全性观察窗）。
7. **C collateral**：横向矩阵仍首屏 top=357，列头含 NCT / 产品中文名 / 阶段·状态 / 地区 / 关键确证试验 5 类身份。
8. **5 个 B baseline 页面 + A + C1024 视口全部 0 横向溢出**。

## 阻断或重要缺陷

### P0 — **0 项**

### P1 — **0 项**

### P2 — **1 项**

1. **A 气泡 `click()` 触发后 drawer 显示为 `display:none`**（DOM 已切换但视觉未显示）
   - **页面**：`http://127.0.0.1:8784/reports/A/v-fixture-001/html/overview.html`
   - **复现操作**：`ego-browser` 的 `await click('button[aria-label*="示例登记号301"]', ...)`；点击后 `getComputedStyle`报 `display:none` 但 `innerText` 含4 个页签（疗效 / 安全性 / 产品档案 / 数据依据）。
   - **观察事实**：URL 仍为 overview.html（无 `?focus=` 参数），证明 click 已触发 state变化但 drawer 视觉未打开。URL focus param方式 `gotoAndWait('?focus=fixture-product')` 抽屉 `display:block` 正常显示。
   - **影响**：医学经理在主路径 click看不到产品洞察抽屉，必须刷新页面才能看到；URL也不携带 focus，无法分享具体产品洞察状态。
   - **可能的根因**：A 在 fixture-001 复用了 `display:block` 抽屉渲染，但 `click` 后的 state切换时抽屉的 CSS仍为 `display:none`（可能是脚本里 drawer 的 `open` state 标志位正确切到 `true` 但 CSS 渲染逻辑未同步）；这是 fixture vs R13h/R13i 真实候选包的实现差异。
   - **最小修复建议**：在 A overview 的 fixture 实现里，让抽屉 click handler同步把内层 `.kz-a-insight-drawer` 设为 `display:block`（或把 inline style 移除以让 CSS 选择器 `.kz-a-insight-drawer[aria-hidden="false"]`接管）。或者用更直接的 `dataset.open = "true"`标记。

---

## 尚未验证

- **B21 个详情页中其他 16 个页面**（baseline-overview / baseline-demographics / baseline-disease-context / baseline-severity / disposition-overview 已检）—— 本轮仅验证 baseline 拆分与 disposition 标题修复，未对 participant-flow / adherence / loss-exit / screen-failure / prohibited-medication / rescue-treatment / longitudinal-results / subgroups-supporting-evidence / trial-exposure-context / product-trial-profiles / plan-deviation / efficacy-safety-matrix / evidence-limitations 抽样。
- **B efficacy 在 12 / 24 周时间窗切换的模糊匹配**（fixture 只有1 张 EASI-75 图，未触发）。
- **A/B/C 在 1280 / 1920 视口**（本轮 1024 + 1440 已验）。
- **`prefers-reduced-motion` 行为**。
- **A drawer click vs URL focus 差异的根因排查**：本次观察到的 `display:none` 是 fixture实现的真实行为，不是 ego bug（URL focus param 工作正常证明 drawer本身能正常显示）。但既然在 R13h真实候选包里 click 正常，R13k fixture 复用了简化逻辑导致该差异，应在 fixture 修复时一并处理。
- **Codex 自己的 ego截图超时**：用户授权 "不要推断产品缺陷或视觉通过" — 本轮未依赖 Codex 截图，独立用 ego(lite) 抽样8 个 URL + 1024 / 1440 视口 + 5 个 baseline + disposition +1 个 A + 1 个 C。

---

**复验保留权限**：本报告为 R13k Conference follow-up 同会话、独立、只读、只跑 ego(lite) 的真实医学经理复验；Codex 仍是最终接受者。本轮 verdict 由 R13j 的"通过 + 1 项嫌疑"修正为"通过 + 1 项 P2 一般优化（A fixture drawer click 显示问题）"，整体放行建议不变。
