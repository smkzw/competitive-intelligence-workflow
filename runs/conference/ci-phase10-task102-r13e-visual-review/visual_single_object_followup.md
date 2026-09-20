### 结论

基于 `ego-browser`（ego lite）对候选包 `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260902-031500-r13f`（本地服务 `http://127.0.0.1:8771`）的有界复验，**5 项共享复验目标全部通过**：
1. B `efficacy.html` 图例（治疗组橙色 `#FF9900` / 对照组蓝色 `#407AAA`）与 ECharts 柱体填充完全一致，未出现颜色倒置。
2. B 表格数值单元格点击后唤起具备完整语义（`role="dialog"`、`aria-modal="true"`）的数据依据对话框，按 Escape 键平滑关闭、清空 Hash 并精准回焦原 `TD`。
3. A 阿姆特利单抗（Amlitelimab）产品洞察的“数据依据”页签仅展示自身 5 项来源，未混入度普利尤单抗（US7608693B2）或曲罗芦单抗（WO2005007699A2）专利。
4. C 设计矩阵单元格点击后成功打开数据依据对话框，“数据说明”已清除“证据标识/分析队列”等内部字段，“原文定位”章节完成中文化（如“章节：研究基本信息”），按 Escape 键正常关闭并回焦至原矩阵按钮。
5. A/B/C 涵盖的 15 个核心页面在 1024px、1280px、1440px、1920px 四档视口下页面级横向溢出均为 0（`overflow = false`）。

---

### 实际复现路径

1. **B 疗效图例与柱体颜色**：
   - 路径：`http://127.0.0.1:8771/b-real/reports/B/v1/html/efficacy.html`
   - 操作：通过 `ego-browser` 检查 `div#kz-chart-0`（FACIT疲劳量表变化图）的 ECharts 实例 Option 及 SVG 图元。
   - 观测：`series[0]` 为“治疗组”（`itemStyle.color: "#FF9900"`，柱体 `fill: "rgb(255,168,0)"`，数值 7.07），图例第一项为治疗组橙色；`series[1]` 为“对照组”（`itemStyle.color: "#407AAA"`，柱体 `fill: "#407AAA"`，数值 6.4），图例第二项为对照组蓝色。

2. **B 表格数值单元格点击与 Escape 回焦**：
   - 路径：`http://127.0.0.1:8771/b-real/reports/B/v1/html/efficacy.html`
   - 操作：真实点击表格第一行“Study 301（CHAMPION-301）”治疗组数据单元格 `TD`；检查 DOM 属性；随后分发 `Escape` 按键。
   - 观测：唤起 `div#kz-evidence-drawer-panel`，具有 `role="dialog"`、`aria-modal="true"`、`tabindex="-1"`、`aria-labelledby="kz-evidence-drawer-title"`；按 Escape 后抽屉关闭（`isClosed: true`），URL Hash 为空，当前聚焦元素恢复为触发单元格 `TD`（`activeElementText: "Study 301（CHAMPION-301）"`）。

3. **A 阿姆特利单抗数据依据来源隔离**：
   - 路径：`http://127.0.0.1:8771/a-real/reports/A/v1/html/efficacy.html` 与 `overview.html`
   - 操作：点击 `DIV.kz-a-bar-row.kz-a-product-trigger[data-product-id="amlitelimab"]` 打开产品洞察抽屉，点击切换至“数据依据”页签，提取全文进行正则检索。
   - 观测：来源清单仅包含 ClinicalTrials.gov (NCT05131477)、PubMed、FDA/EMA/NMPA、企业公告、企业管线 5 项来源；全文检测 `US7608693`、`度普利尤单抗`、`Dupilumab`、`WO2005007699`、`曲罗芦单抗`、`Tralokinumab` 均为 `false`。

4. **C 设计矩阵下钻、中文化与 Escape 回焦**：
   - 路径：`http://127.0.0.1:8771/c-real/reports/C/v1/html/design-map.html`
   - 操作：分别真实点击 NCT02260986（CHRONOS）、NCT04178967（ADvocate2）、NCT03131648（ECZTRA 7）、鲁索利替尼 III期等单元格按钮 `BUTTON.kz-c-matrix-cell-trigger`，检查抽屉文案并执行 Escape 退出。
   - 观测：
     - 数据说明为：“本条信息摘自临床试验登记页，适用于总体入组人群；已核对来源版本和原文位置，当前公开情况为已报告值。”彻底去除了“证据标识”“分析队列”及 `c-nct...`。
     - 原文定位显示：“章节：研究基本信息；打开原文”，英文“Identification”已中文化。
     - 按 Escape 后抽屉关闭，焦点精确还给对应的 `BUTTON.kz-c-matrix-cell-trigger`。

5. **A/B/C 全页面四视口横向溢出检测**：
   - 路径：A（5页）、B（5页）、C（5页）共 15 个 HTML 页面。
   - 操作：通过 CDP `Emulation.setDeviceMetricsOverride` 切换 1024px、1280px、1440px、1920px 宽度，提取 `document.documentElement.scrollWidth` 与 `window.innerWidth`。
   - 观测：60 组视口测试中 `docScrollWidth === window.innerWidth` 均为 `true`，无全局横向滚动条。

---

### 已修复项

1. **Report B 疗效图表视觉对应一致性**：柱状图治疗组（橙色）与对照组（蓝色）在图例、系列定义与 SVG 渲染层完全统一。
2. **Report B 抽屉无障碍语义与键盘交互**：抽屉面板具备标准对话框无障碍属性，Escape 键关闭后实现焦点精确恢复至触发单元格。
3. **Report A 产品数据依据精准关联**：阿姆特利单抗彻底剔除度普利尤单抗和曲罗芦单抗的跨产品专利干扰。
4. **Report C 设计矩阵说明专业度与本地化**：“数据说明”去除底层工程/数据库元数据字段，转为规范医学文本，“原文定位”章节标题完成汉化。
5. **A/B/C 全站响应式几何约束**：1024/1280/1440/1920 四档视口均保持零页面级溢出，大矩阵横向滚动完全收敛在局部容器内部。

---

### 仍存在的阻断或重要缺陷

- **无阻断缺陷**：5 项复验目标全部满足验收合同。
- **医学经理一般优化关注项（非阻断）**：
  - 在 1024px 视口下查看 Report C `design-map.html` 大矩阵向下深翻时，吸顶表头高度（约 140px~160px）仍占有一定纵向视野。若后续有工程迭代空间，可考虑在吸顶状态下折叠为精简胶囊。

---

### 尚未验证

- 未对移动端（如手机/平板小于 768px）进行专项视口验证（超出当前 1024~1920 桌面端验证范围）。
- 未对除 A/B/C 已抽样 15 个核心页面外的边缘附属静态页面（如 `historical-edge.html`、`patents-protection.html`）进行逐像素肉眼审校。
