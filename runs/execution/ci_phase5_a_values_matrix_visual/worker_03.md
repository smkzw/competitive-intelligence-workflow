页面结构已确认：首页 `overview.html`，安全性详情 `safety.html`。现在写探针脚本按三个视口实测。

筛选器分布在 `clinical-portfolio.html`（产品/靶点/分期/地区）和 `efficacy.html`（终点/时间点单选）。补一轮这两页的探针与交互。

交互探针完成。关键发现：终点/时间点筛选含原始英文注册库标题，且切换后标题拼接成长英文串。现在做真实视觉检查——逐张查看截图。

768 顶部视野两页渲染良好。继续看整页与疗效页。

768 整页在 ICP-332 行附近发现疑似文字重叠（行副标题与图例叠印）。用实时滚动截图确认是否为拼接伪影。

最后确认 768 下首页气泡矩阵区域与 1280 安全性热图分块。

所有检查完成，证据充分。整理报告。

# Execution Output: ci_phase5_a_values_matrix_visual - worker_03

## Boundary And Context Check

- 已读取初始集：`context/ci_phase5_a_values_matrix_visual_execution_context.md`、`plans/codex_execution_ci_phase5_a_values_matrix_visual.md`。
- 补充读取（均在工作区内，用于定位审查对象与交互选择器）：`context/ci_phase5_a_values_matrix_fix_execution_context.md`、`runs/execution/ci_phase5_a_values_matrix_fix/worker_01.md`、`worker_03.md`、`tests/browser/test_a_portal.py`、`src/ci_workflow/renderers/portal/assets/portal.css`（仅 grep 媒体查询与条形样式）。
- 审查对象（当前轮次最新生成物，2026-08-28 04:54）：`.artifacts/a-values-matrix-fix-final-v2/reports/A/v1/html/`，页面 `overview.html`（首页）、`efficacy.html`、`safety.html`、`clinical-portfolio.html`。
- 全程只读审查报告文件，未修改任何源码/数据/报告。仅在 `tmp/worker_03_visual/` 写入探针脚本、截图与指标 JSON（审查证据）。
- 未访问互联网，未做最终验收结论；以下为独立视觉实用性证据与发现，供 Codex 裁决。

## Work Performed

以真实浏览器（Playwright Chromium，本机可正常启动；前一轮 codex 子代理沙箱失败不适用于本环境）在 768、1280、1440 像素视口实际打开 4 个核心页面，完成：

1. 响应式分块：每页每视口的几何测量（文档/正文宽度 vs 视口、热图网格宽度与右边界）+ 整页与首屏截图逐张目视。
2. 字号：统计全部可见叶子元素计算字号分布；热图数值单元格最小字号、空单元格计数。
3. 中文标签：扫描文本截断（scrollWidth>clientWidth）、纯 ASCII 键名泄漏、筛选选项语种。
4. 交互筛选（真实点击，非静态断言）：
   - `efficacy.html` 终点/时间点单选：三个视口均点击，校验 `aria-pressed==1`、H2 标题联动、空态文案。
   - `clinical-portfolio.html` 靶点筛选：49→15 行收窄、URL 出现 `target=`。
   - `safety.html` 产品折叠面板（38 项）：展开→点选"曲罗芦单抗"→热图与表格联动、筛选后无横向溢出。
   - 768/1280 下"菜单"按钮展开导航（7 个链接可见）。
5. 针对性复验：对首页与疗效页条形图图例与末行的几何重叠，在 768/1024/1280/1440 四宽度做矩形相交测量并以实时滚动截图（非整页拼接）确认。

## Artifacts And Evidence

证据目录：`tmp/worker_03_visual/`（探针 `probe.py`、`probe2.py`；指标 `metrics.json`、`metrics2.json`；截图 33 张，含各视口首屏/整页、交互后、菜单展开、空态）。

关键截图：
- `overview@768-top.png`、`safety@768-top.png`、`safety@1440-top.png`、`overview@1440-top.png`：默认视野分块与中文标签正常。
- `overview@768-efficacy-bottom.png`、`efficacy-chart-bottom@1280.png`、`efficacy-chart-bottom@1440.png`：图例叠印缺陷实证（实时视口截图，排除拼接伪影）。
- `interact-efficacy@1280.png`、`interact-efficacy@768.png`：英文原始终点标题进入筛选项与选中态。
- `efficacy-empty-state@768.png`：无数据组合的空态文案。
- `interact-safety@768.png`、`safety-event-filter-open@768.png`：安全性筛选联动与事件标签现状。

测量结果摘要（证据）：
- 三个视口 × 四页面 `docScrollWidth == bodyScrollWidth == viewport`，无横向溢出；热图数值最小字号 16px、无空值单元格；页面最小可见字号 13px（仅次要注释），正文 14–16px。
- 交互全部生效：终点/时间点单选 `pressed==1` 且标题联动；靶点筛选 49→15 行且 URL 同步；产品筛选后热图显示 3 个百分比单元格、无溢出。

发现的缺陷（按严重度）：

1. **【确认缺陷｜跨全部宽度】条形图图例与末行叠印。** `home-efficacy`（首页主要疗效）与 `efficacy-full`（疗效页）两张图的图例"橙色：治疗组｜蓝色：对照组"（`.kz-a-chart-note`）与末行条形行几何重叠约 19–20px（768/1024/1280/1440 均 `overlap=true`）。768 首页目视可见 ICP-332 行副标题"EASI-75｜第…周"与图例文字互相叠印、不可辨读；1280/1440 疗效页 APG777 行"对照组"标签与图例叠印。根因推断：图表容器未为图例预留独立行高。建议最小修复：图例改为文档流内独立一行（或图表底部增加约 24px 内边距）。
2. **【中文标签缺陷】疗效终点/时间点筛选暴露未归一英文注册库原文。** 终点筛选 1469 个选项大多为 ClinicalTrials.gov 英文 outcome 标题；选中后 H2 直接拼接英文原文加硬编码后缀，实测标题变为"第16周Percentage Change From Baseline in EASI (Eczema Area and Severity Index) (Part 2)（Week 24）应答率"。除语种问题外存在临床语义问题（推断）：change-from-baseline 类指标被冠以"应答率"不成立。时间点选项亦混入"Baseline to weeks 24, 28, …"等原文。建议：终点维度仅暴露归一中文短名（如 EASI-75/IGA 0/1/EASI 较基线变化率），原始英文标题收进"查看数据依据"或 title 提示；标题后缀按指标类型区分"应答率/较基线变化"。
3. **【观察｜建议】安全性事件筛选标签语种与大小写混杂。** 设计保留了原始术语（符合修复轮要求），但同屏出现"SKIN BACTERIAL INFECTION / Hand dermatitis / TIBIA FRACTURE / 头痛 / 皮肤感染"，全大写与首字母大写并存，中文医学经理扫读一致性差。建议归一名为主、原文括注，或至少统一英文大小写。
4. **【轻微｜非阻断】768 下极窄对照组条形（7.9%、8.8%）文字超出条宽。** CSS 未裁切（无 `overflow:hidden`），文字仍完整可读，仅视觉上伸出色条。

通过项（目视+测量）：768 下筛选区垂直堆叠、热图单元格观察窗中文短标签（"登记报告期""第16周双盲治疗期"等）换行完整；"未公开/暂无公开记录"灰色状态清晰；菜单折叠与展开正常；空态文案为得体中文（"当前选择下暂无可比较数据，请清除部分条件后继续查看"）；1440 下完整导航与双列筛选布局正常。

## Commands And Observations

- `mkdir -p tmp/worker_03_visual && .venv/bin/python`（Playwright 启动冒烟）→ `chromium ok`，真实浏览器可用。
- `.venv/bin/python tmp/worker_03_visual/probe.py` → 6 组布局指标 + 2 组交互；首轮点击产品筛选超时，定位为 `<details class="kz-a-filter-disclosure">` 默认折叠（设计行为），修正为先点 summary 后通过。
- `.venv/bin/python tmp/worker_03_visual/probe2.py` → efficacy/clinical-portfolio 三视口指标与交互，结果见 `metrics2.json`。
- 内联探针：图例重叠四宽度几何测量 → 全部 `overlap: True`；字号分布统计；菜单展开验证。
- 工具与目标记录：Playwright Chromium → `file://.artifacts/a-values-matrix-fix-final-v2/reports/A/v1/html/{overview,efficacy,safety,clinical-portfolio}.html`；Read/Grep → 上下文、计划、测试与 CSS；ReadMediaFile → 上述截图目视。

## Blockers Or Missing Environment

无环境阻塞。本机 Playwright Chromium 正常启动（前一轮 worker_03 报告的沙箱 `MachPortRendezvousServer` 限制在本执行环境不存在）。未安装任何包。

## Rerun Requests Or Next Step

- 请 Codex 裁决两项缺陷的处置：（1）图例叠印——影响全部宽度且 768 下文字不可辨读，建议授权最小 CSS 修复后重跑本探针；（2）终点/时间点英文原文标签与"应答率"后缀——涉及术语归一策略与临床语义，超出视觉执行边界。
- 修复后重跑命令：`.venv/bin/python tmp/worker_03_visual/probe.py && .venv/bin/python tmp/worker_03_visual/probe2.py`（只读，约 2 分钟），重点复验 `efficacy-chart-bottom@*.png` 与交互后 H2 标题。
- 1024 像素的图例重叠我仅做了几何确认（`overlap=true`），其完整视觉验收属 worker_01/02 范围；本 worker 不宣称最终视觉验收。
