Task space closed. Final output follows.

# Conclusion

> runner-managed;以下为 R13i 有界复验完整正文。

---

# R13i 三类竞品报告有界复验（M3 / pi/cms-router/minimax-m3:high）

身份：与 R13e/R13f/R13h 同会话；只读；只跑 ego(lite)。
候选：`/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260902-020956-r13i`
服务：`http://127.0.0.1:8774`

---

## 结论

R13i 在共享合同的 4 条目标上整体显著优于 R13h。4 条里 3 条全部通过；1 条（B safety 数据依据抽屉标题）发现一个细颗粒度的英文残留，需要修但 **不构成阻断级**。R13h 留下的 3 个阻断/重要缺陷里：

- **A 阿姆特利单抗 抽屉五字段混口径** — ✅ **已修复**：5 个字段分别独立展示。
- **B safety 英文标签 + 缺色阶说明** — ✅ **已修复**：5 个英文标签全部消失；图首加上"颜色深浅仅表示同一图内发生率高低；不同图的色阶不可直接比较，也不构成安全性排序"。
- **C overview / design-map 顶部"二态徽章概览"抢首屏** — ✅ **已修复**：矩阵改为首屏正位；列头出现 NCT + 产品中文名 + 阶段 + 状态 + 地区；每格显示具体设计事实；旧二态网格消失。

整体可在不返工的前提下视为"修复验收完成"，最终接受权仍归 Codex。

---

## 实际复现路径（每一步都在 ego 内真实执行）

### Task 1：A 阿姆特利单抗 抽屉五字段分流 + tab + Esc + 回焦

- `http://127.0.0.1:8774/a-real/reports/A/v1/html/matrix.html?focus=amlitelimab` 点击触发气泡后：
  - **项目最高阶段** = III期（已终止）✓（独立字段，不再被混入"试验分期"或"当前状态"）
  - **当前证据试验** = 阿姆特利单抗（Amlitelimab）II期（安全性补充）临床研究（NCT05131477）✓
  - **证据试验分期** = II期（安全性补充）✓
  - **疗效数据时间点** = 第24周 ✓
  - **安全性观察窗** = 基线至第24周 ✓
  - URL `?focus=amlitelimab`；产品档案页签补出 Sanofi / Kymab、当前状态 "2026 年 7 月停止特应性皮炎开发，不再申报"，OX40L 共刺激信号机制。
- 切 安全性 / 数据依据 / 产品档案 三个页签均渲染完整；AESI 仍在 safety.html 全文字段为零（`{hasAESI:false, aesiCount:0}`）。
- 按 Esc：URL 清；`document.activeElement` 切回阿姆特利单抗气泡按钮（aria-label 含 NCT05131477 + 42.9% + 67.5% + 77 + Baseline through week 24）—— **焦点回原气泡**。
- 主动推翻尝试：tab 循环后再 Esc，焦点仍能回到阿姆特利单抗气泡按钮；连续两次 Esc 也不会丢失焦点指向。

### Task 2：B safety 中文标准名 + 色阶说明 + 数据依据抽屉

- 1440 `http://127.0.0.1:8774/b-real/reports/B/v1/html/safety.html`：视口 `{vw:1440, docW:1440, hs:false}`。
- **禁用英文标签审计**：在 `document.body.innerText` 全文检索 5 个英文标签（Breakthrough haemolysis / Discontinuation due to adverse event / Headache / Serious adverse reactions / Treatment discontinuations due to TEAE），结果 `{forbiddenEnglishFound:[]}` —— **全部 5 个英文标签消失**。
- **H3 标题**已全部中文化："安全性 · 特别关注不良事件 · 事件发生率 · 治疗期间 · 安全性分析集（来源分母）"、"安全性 · 任何严重不良事件 · 事件发生率 · 最长 48 周 · ..."、"安全性 · 任何治疗期间不良事件 · ..." 等等。
- **色阶说明**：页面顶部一段说明："颜色深浅仅表示同一图内发生率高低；不同图的色阶不可直接比较，也不构成安全性排序"—— 与 PRD 字面要求完全一致。
- 点击 `[data-evidence-open="safe-fact-real-apply-treatment-aesi"][data-label="发生率/数值"]`（即 iptacopan APPLY-PNH 治疗组 25.8%）：
  - 抽屉 `role=dialog, aria-modal=true, display:flex`，URL `?focus=safe-fact-real-apply-treatment-aesi`。
  - 抽屉 **标题**："伊普可泮（iptacopan） · **Adverse events of special interest**"—— ⚠️ **抽屉标题保留了英文**（数据点 / 字段名），这是页面层级修复之外的残留。
  - 抽屉正文产品 / 试验 / 组别 / 终点 / 时间点 / 值 25.8 / 阈值 / 单位 / 分子 16 / 分母 62 / 披露状态 / 数据说明 / 来源版本 / 原文定位 "章节：安全性结果；列：Iptacopan: 16/62 (25.8%)；打开原文" —— 中文均正确。
- 按 Esc：URL 清，焦点回原 TD（text=25.8）—— **焦点回原单元格**。
- 主动推翻尝试：检查整个 safety.html 是否还残留任何英文 safety 标签（包括 drawer title 之外）—— 全文 0 命中。

### Task 3：C overview + design-map 矩阵首屏

- 1440 `http://127.0.0.1:8774/c-real/reports/C/v1/html/overview.html`：
  - 视口 `{vw:1440, docW:1440, hs:false}`。
  - 页面顶部 H3 顺序："研究 × 设计要素横向矩阵"（top=357）—— **首屏第一内容块**（位于页面标题 299 之后）。
  - "设计字段公开情况概览" 二态徽章网格 **已移除**（R13h 旧顶部 17×20 网格 `已公开 / 未公开` 在 R13i 不再出现）。
  - 副标题 "行是设计领域与字段，列是研究；点击单元格内事实可查看完整原文与来源定位" + 右侧提示 "矩阵可横向滚动；首列与表头固定"。
  - 列头（截图 `/tmp/r13i/overview-top.png`）：
    - 第一列 = 设计领域 / 设计要素（粘性首列）
    - 第二列 = **NCT02260986** + **度普利尤单抗（Dupilumab）** + **III期：已完成** + **澳大利亚、加拿大、捷克、匈牙利** + **关键确证试验**
    - 字段分组：试验身份（含 试验标识 → CHRONOS）、人群与标准（含 目标人群 → "登记最低年龄 18 岁；特应性皮炎受试者"、入选标准 → "登记入选标准原文：Chronic AD that had been present for at least 3 years before the screening visit（筛选期）" 等）。
  - 单元格内容为真实中文设计事实，不再是 `已公开 / 未公开` 二态。
- `design-map.html` 同形态："研究 × 设计要素横向矩阵" top=357 同样为首屏内容；二态徽章概览不复存在。
- 矩阵列头含 **NCT + 产品中文名 + 阶段 + 状态 + 地区** 完整 5 类身份 ✓
- 点击 `[data-evidence-open="c-nct02260986-trial_identity"]` 查看依据按钮（用 `.click()`）：
  - 抽屉 `.kz-evidence-drawer {display:block}`，URL `?focus=c-nct02260986-trial_identity`。
  - 数据说明: "本条信息摘自临床试验登记页，适用于总体入组人群；已核对来源版本和原文位置，当前公开情况为已报告值。" —— 无 `证据标识 / 分析队列` 泄露。
  - 原文定位章节 = "研究基本信息" —— 中文化 ✓
  - 简短原文 = "Study to Assess the Efficacy and Long-term Safety of Dupilumab (REGN668/SAR231893) in Adult Participants With Moderate-to-Severe Atopic Dermatitis"（登记原文，按 PRD 允许作为来源原文呈现）。
- 按 Esc：URL 清；`document.activeElement = <BUTTON text="查看依据" data-evidence-open="c-nct02260986-trial_identity">` —— **焦点回原按钮**。
- 主动推翻尝试：在 1440 overview 上做了横向滚动测试，matrix 内部有局部滚动行为（容器 scrollWidth > clientWidth），但页面 `documentElement.scrollWidth === window.innerWidth === 1440`，未触发页面级横向滚动。

### Task 4：A/B/C 在 1024 / 1280 / 1440 / 1920 视口下无页面级横向溢出

- 17 个核心页面 × 4 视口 = **68 个组合全部** `{vw:docW, hs:false}` —— 0 个页面级横向溢出。

---

## 已修复项（与 R13h 对照）

| 共享合同项 | R13h 状态 | R13i 状态 |
|---|---|---|
| 1. A 阿姆特利单抗抽屉 5 字段混口径 | 5 字段糅在一起（项目最高阶段 / 当前证据试验 / 证据试验分期 / 疗效时间点 / 安全性观察窗 无法一眼分流） | **修复**：5 字段分行列出；URL focus + Esc + 回焦原气泡均正确 |
| 2. B safety 英文标签 + 缺色阶说明 | Breakthrough haemolysis / Discontinuation due to AE / Headache / Serious adverse reactions / Treatment discontinuations due to TEAE 全部英文 | **修复**：5 个英文标签全部消失，全文字段 0 命中；图首加"颜色深浅仅在同一图内比较"说明；数据依据抽屉身份一致 |
| 3. C overview / design-map 首屏矩阵 vs 二态徽章 | 顶部仍以"设计字段公开情况概览"二态网格占据首屏；下方真正的横向矩阵在第二屏之后；列头缺 NCT / 产品 / 阶段 / 状态 / 地区 | **修复**：横向矩阵变为首屏内容块；列头含 NCT02260986 + 度普利尤单抗 + III期：已完成 + 澳大利亚加拿大捷克匈牙利 + 关键确证试验；二态徽章网格消失；每格显示具体中文设计事实 |
| 4. A/B/C 在 1024 / 1280 / 1440 / 1920 视口下无页面级横向溢出 | 56 个组合 0 溢出 | **复验通过**：68 个组合仍 0 溢出 |

## 仍存在的阻断或重要缺陷

- **无新增阻断**。
- **1 个细颗粒度残留**（重要但不阻断）：
  - **B safety 数据依据抽屉的标题** 仍写英文 "Adverse events of special interest"（在产品名 · 事件名 一行），尽管页面层和表层都已中文化（"特别关注不良事件 / 安全性事件"）。建议在抽屉标题事件字段也走同一中文映射，否则医学经理分享截图时会出现"页内中文 / 抽屉英文"的视觉不一致。
- R13h 列出的"大部分 B 疗效图仍只 1 个产品"问题本次复验不在共享合同范围内，未重新抽样；如需再验可单独派单。

## 一般优化

1. **C overview 第一列"设计领域 / 设计要素"用粘性列位置，但 `field/sticky` 行为在 1024 视口下仍偶尔与左侧筛选栏争夺左侧空白** —— 建议增加 z-index 与最小宽度保障。
2. **C overview 顶部第一列字段分组（试验身份 / 人群与标准 / 干预与终点 / 分析与判断）的展开/折叠交互未明确**：当前显示为展开状态，没有折叠按钮，长表一直展开导致全文 1500+ 行渲染。
3. **B safety "数据说明 / 来源版本 / 原文定位" 三段文字密度偏大**：在 1024 视口下抽屉宽度紧贴右边缘，建议增加抽屉最大宽度的媒体查询控制。
4. **A 抽屉"项目最高阶段 / 当前证据试验 / 证据试验分期"三段对阿姆特利单抗这种 III 期已终止 + II 期补充试验 的产品做了正确拆分，但其它已完成 III 期的产品（如 度普利尤单抗）三段可能输出重复内容** —— 建议 PRD 端允许该模板字段当输入数据相同时合并为单行 "项目最高阶段与证据试验分期一致"。

## 尚未验证

- B efficacy / baseline / disposition / overview 全部视口 × 全部图在 R13h 留下的"B 单产品图清单"是否仍单产品 —— 共享合同未要求重测，本次只验 safety。
- B 数据依据抽屉标题英文残留是否在所有事件名（非 AESI / 非 AESI 子事件）上都修复 —— 本次只点了 AESI 一格。
- C trials/<nct>.html 系列其他试验档案（NCT02260986 之外）的 R13i 状态。
- C 抽屉右侧浮层在 1024 / 1280 视口下的视觉布局 —— 0 溢出已验，但抽屉浮层是否与主区遮挡未视觉确认。
- 主动推翻尝试：用 `xpath=//td[@data-evidence-open]` 命中首格（组别 / 安全性事件等无值格）会出现"抽屉只渲染控制区（× / 冲突 / 历史版本 / 固定此条 / 固定对照）" —— 仍是测试命中问题，非产品 bug；建议自动化加 `data-label="比较值" / "发生率/数值"` + textContent 双重定位。

---

**复验保留权限**：本报告为 R13e / R13f / R13h 同会话、有界、只读、只跑 ego(lite) 的真实医学经理复审；Codex 仍是最终接受者。
