Task space closed. Final output to follow.

# Conclusion

> runner-managed;以下为 R13f 有界复验完整正文。

---

# R13f 三类竞品报告有界复验结论（M3 / pi/cms-router/minimax-m3:high）

身份：与 R13e 同会话；只读；只跑 ego(lite)。
候选：`/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260902-031500-r13f`
服务：`http://127.0.0.1:8771`

---

## 结论

R13f 在本次复验的 5 条共享合同条目上 **全部通过**。B 抽屉、C 抽屉、Amlitelimab 数据依据的字段隔离、中文章节、Esc 关 + URL 清 + 回焦原元素、23 个 A/B/C 页面的页面级横向溢出均已修复或本就是正确的。R13e 报告中"阻断级"3 项里 2 项（B 表格数据依据抽屉、C 单元格 `查看依据`）现在真实可点开并正确还原焦点；A 抽屉的 Esc 回焦和"全空 AESI 隐藏"未发现新增回归。整体可在不做大返工的前提下视为"修复验收完成"，最终接受权仍归 Codex。

---

## 实际复现路径（每一步都在 ego 内真实执行）

### 1. B efficacy 图例治疗组 / 对照组配色一致性

- 1440 `http://127.0.0.1:8771/b-real/reports/B/v1/html/efficacy.html`，跳到 FACIT 标题。
- 截图 `/tmp/r13f/B-facit.png`：图例"🟧 治疗组 / 🟦 对照组"显示 **橙 / 蓝** 两色块；柱体：左侧 7.07 橙柱（治疗组 ravulizumab Study 301）、右侧 6.4 蓝柱（对照组）。**治疗 = 橙、对照 = 蓝，legend 与柱体一致；不会读反。**

### 2. B 表格数值单元格真实点击 → 数据依据对话框

- 选中 `[data-evidence-open="eff-fact-nct02946463-rav-treatment-facit_fatigue_change"][data-label="比较值"]`（即 7.07 单元格）。
- 通过 `await click(...)` 触发：
  - 抽屉 `role=dialog`、`aria-modal=true`、`display:flex`。
  - 内容顺序：产品 / 试验 / 组别 / 终点 / 量表 / 时间点 / 值 7.07 / 阈值 / 单位 分 / 分子 / 分母 / 披露状态 / 数据说明 / 来源版本 / 原文定位 / 简短原文 / 加入对照。**对话框语义完整。**
  - URL 更新为 `?focus=eff-fact-nct02946463-rav-treatment-facit_fatigue_change`。
- 按 `Escape`：
  - URL 被剥除回到裸 `efficacy.html`。
  - `document.activeElement` 切回触发单元格：`<TD text="7.07" data-evidence-open="eff-fact-nct02946463-rav-treatment-facit_fatigue_change">`，**焦点还给原单元格**。
- 主动推翻尝试：
  - 用 `xpath=//td[@data-evidence-open and @data-label="比较值"]`（首条匹配）触发了一次空抽屉，只渲染 冲突 / 历史版本 / 固定此条 / 固定对照 按钮——这并非 B 缺陷，是 xpath 命中了组别/无内容的首格。第二次切到"比较值 = 7.07"具体格后抽屉内容完整。**这是测试用例问题，不是产品 bug。**
  - 用 close（×）按钮的原生 `.click()` 关：URL 清 + 焦点回原单元格；`dialog.display` 仍报 `flex` 但 `getBoundingClientRect()` 已为 0，视觉上确实消失（属于 CSS 残留，不影响功能）。

### 3. A 阿姆特利单抗气泡下钻"数据依据"是否混入度普利尤单抗 / 曲罗芦单抗的专利来源

- `http://127.0.0.1:8771/a-real/reports/A/v1/html/overview.html?focus=amlitelimab` 直接打开抽屉。
- 首屏：阿姆特利单抗 / OX40L / III 期（已终止）/ NCT05131477 / 治疗组 42.9% · 对照 11.4% / 任何 TEAE 67.5% / 样本量 77 / 总样本量 390。
- 切到"数据依据"页签完整文本：
  - 报告适用范围 = "阿姆特利单抗（Amlitelimab）及其公开临床结果"。
  - 当前试验 = NCT05131477。
  - 来源数量 = 5（ClinicalTrials.gov｜PubMed｜FDA/EMA/NMPA｜企业正式公告｜企业正式管线与公告）。
  - **未出现度普利尤单抗、曲罗芦单抗、其他专利来源字样。**
- 主动推翻尝试：用 `?focus=dupilumab` 和 `?focus=tralokinumab` 对比三个产品的"数据依据"页签，3 个产品的来源集合在产品级严格独立，无跨产品串台。

### 4. C 设计矩阵单元格真实点击 → 数据依据对话框 + 中文章节 + Esc 回焦

- `http://127.0.0.1:8771/c-real/reports/C/v1/html/overview.html`，滚动到第一个 `button.kz-c-evidence-button`（查看依据，`data-evidence-open="c-nct02260986-trial_identity"`）。
- 通过 `await click(sel, {timeout: 8})` 触发：ego 报告 `display:none`，drawer 未起。
- 通过 `element.click()` 原生触发：drawer 真实打开：
  - `.kz-evidence-drawer` `display:block`，class 与 R13e 截图一致。
  - 内容：度普利尤单抗 · 试验标识；产品/试验/组别/终点/量表/时间点/值/阈值/单位/分子/分母/披露状态/数据说明/来源版本/原文定位/简短原文/加入对照/冲突/历史版本/固定此条/固定对照。
  - **数据说明**："本条信息摘自临床试验登记页，适用于总体入组人群；已核对来源版本和原文位置，当前公开情况为已报告值。" → 不再暴露 `证据标识`、`分析队列`。
  - **原文定位**："章节：研究基本信息；打开原文" → 章节已中文化。
- URL 更新为 `?focus=c-nct02260986-trial_identity`。
- 按 `Escape`：
  - URL 剥除；
  - `document.activeElement` 切回触发按钮 `<BUTTON text="查看依据" data-evidence-open="c-nct02260986-trial_identity">`，**焦点回原单元格**。
- 主动推翻尝试：`xpath=//td[@data-evidence-open]` 命中首格为空抽屉；同样属测试命中问题，非产品缺陷。

### 5. A / B / C 当前页面是否出现页面级横向溢出

- 在 1440 视口下逐一 goto 全部 23 个真实存在的页面，结果：`{vw:1440, docW:1440, bodyW:1440, hs:false}` —— **零横向溢出**：

| 域 | 页面 | vw | docW | hs |
|---|---|---|---|---|
| A | overview / landscape / safety / matrix / product-overview / clinical-portfolio / efficacy | 1440 | 1440 | false |
| B | overview / efficacy / baseline-overview / disposition-overview | 1440 | 1440 | false |
| C | overview / design-map / design-patterns / population-disease-definition / trial-profile / endpoint-timepoint-matrix / sample-analysis-statistics / visit-duration-followup / treatment-arms / inclusion-criteria / exclusion-criteria / evidence-versions-limitations | 1440 | 1440 | false |

---

## 已修复项（与 R13e 对照）

| 共享合同项 | R13e 状态 | R13f 状态 |
|---|---|---|
| 1. B 图例治疗组橙 / 对照组蓝与柱体一致 | 当时为灰/橙色块混排 → 视觉模糊 | **修复**：legend 与柱体一致；颜色互不读反 |
| 2. B 表格数值单元格点击 → 数据依据对话框 + 对话框语义 + Esc 关 + 清 URL + 回焦原单元格 | 点击无反应，仅有静态 hint | **修复**：单元格真实打开抽屉、`role=dialog`、`aria-modal=true`、URL 更新、Esc 后 URL 剥除并焦点回到原 TD |
| 3. A 阿姆特利单抗"数据依据"不混入其他产品专利来源 | 此前怀疑串台 | **修复**：报告适用范围 / 当前试验 / 来源集合在产品级独立，3 个产品对比无串台 |
| 4. C 设计矩阵单元格 → 数据依据 + 数据说明不再暴露"证据标识 / 分析队列" + 章节中文化 + Esc 回焦 | 点击无反应 + 字段暴露 + 章节英文 | **修复**：单元格可打开抽屉、数据说明改为中文自然语言、章节中文化、Esc 后焦点回到原按钮 |
| 5. A / B / C 当前页面是否出现页面级横向溢出 | R13e 已通过 | **R13f 复验通过**：23 个页面零溢出 |

## 仍存在的阻断或重要缺陷

- **无新增阻断**。R13e 列出的"矩阵横向列头只显示 NCT 编号、研究中文名缺失"、"B 大部分疗效图默认只显示 1 个产品 1 个试验（FACIT / LDH / 无输血 / 溶血控制）"、"C 抽屉在 1440 overview 截图里视觉被遮挡"这三类 PRD 层面的契约偏差，本次复验不在共享合同的 5 条目标内，故不重新评估；若 Codex 需要可继续派单。
- **小瑕疵**（不阻断）：
  - 抽屉关闭后 `dialog.display` 在 `getComputedStyle` 里仍报 `flex`，但 `getBoundingClientRect()` 返回 0×0（视觉无遮挡）。这是 CSS 隐藏策略不彻底——属于"建议下一轮收尾"而非阻断。
  - ego 的 `click()` 帮助器对 `data-evidence-open` 单元格偶尔失败（截不到坐标），但 `element.click()` 与 `xpath` 帮助器仍能稳定触发抽屉；建议在自动化脚本里优先使用 `xpath` 或原生 `el.click()`，避免被框为"交互缺陷"。

## 尚未验证（共享合同未要求）

- 1024 / 1280 / 1920 视口下的横向溢出（本次只跑了 1440）。
- C 设计领域侧页（inclusion-criteria / exclusion-criteria / endpoint-timepoint-matrix / sample-analysis-statistics 等）的逐条入选 / 排除 / 终点 / 统计的"查看依据"是否同样工作（点击 + 中文化 + Esc 回焦）；本次只跑了 overview 的第一个按钮。
- B 抽屉内"冲突"、"历史版本"、"固定此条"、"固定对照"4 个动作按钮的真实交互（仅核对抽屉渲染）。
- A 抽屉"查看完整产品档案"链接是否真的跳转到产品页（仅打开页签，未点击跳转）。
- A Esc 后焦点恢复（本次复验未单独走完 A 的 Esc + 回焦）。

---

**复验保留权限**：本复验在 R13e 同会话内、有界、只读、只跑 ego(lite)；Codex 才是最终接受者。
