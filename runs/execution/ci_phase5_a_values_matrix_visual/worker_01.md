The report is `.artifacts/a-values-matrix-fix-final-v2/reports/A/v1/html/overview.html`. Now I'll check for a way to render at exactly 1024px viewport.

The home page has a 主要疗效 chart and a 关键安全性 heat matrix. Now I'll render it at 1024px and measure overflow and readability.

# Execution Output: ci_phase5_a_values_matrix_visual - worker_01

## Boundary And Context Check

- 已读取指定的两份输入：`context/ci_phase5_a_values_matrix_visual_execution_context.md`、`plans/codex_execution_ci_phase5_a_values_matrix_visual.md`。
- 分配项：worker_01 —— 在 1024px 默认桌面视野实际打开首页，核验主要疗效替代时间点/IGA 主终点显示、安全性矩阵默认视野无横向拖动且数值可读。只审查，未改任何被审文件。
- 上下文 Source Of Truth 为 TODO（Codex 未填具体路径）。为确定被审工件，补充读取了目录结构：`plans/codex_execution_ci_phase5_a_values_matrix_fix.md`（确认本任务是该 fix 的后续视觉验收）、`.artifacts/a-values-matrix-fix-final-v2/manifests/current_run.json` 与 `reports/A/v1/html/data/sitemap.json`（确认最新 A 类正式报告快照及路由）。**被审对象确定为 `.artifacts/a-values-matrix-fix-final-v2/reports/A/v1/html/overview.html`（首页，路由 `/a/overview`，run `run_a3fe390154dd1db546f2828e`，生成于 2026-08-27T20:53Z，为最新 final 快照）**；相邻旧快照 `a-data-matrix-recheck-preview-v8` 非本次验收对象。
- 写入仅限于新增证据截图目录 `.artifacts/_visual_probe_values_matrix_visual_w01/`（沿用仓库既有 `_visual_probe_*` 先例）；未触碰 `runs/execution/.../worker_01.md`（由 runner 持久化），未改报告源文件。

## Work Performed

在 1024×768 视口（Chromium，项目 `.venv` 内 Playwright）以 `file://` 实际加载首页 `overview.html`，等待图表渲染后做 DOM 测量与截图，并核对原生分辨率下的可读性。结论如下。

**1. 主要疗效 —— 替代时间点 / IGA 主终点显示：通过（观察事实）**
- 卡片副标题明确承诺该行为："优先显示接近第16周的EASI-75；未采用该终点时显示IGA 0/1"。
- 实际渲染中替代终点与替代时间点真实出现且带中文标签：`IGA 0/1｜第12周`（阿布昔替尼）、`IGA 0/1｜第4周`（Difamilast）、`EASI-75｜第8周`（曲罗芦单抗、芦可替尼乳膏）、`EASI-75｜多时间点（含第16周）`（Amlitelimab）、`EASI-75｜第4周`、`IGA 0/1｜时间点见明细`（显式降级状态，非空白）。
- 条形数值标签（治疗组/对照组百分比）在 1024px 原生分辨率下逐条清晰可读；字号分布 14–16px（正文 14px、数值 14/16px），无低于 13px 的正文。

**2. 安全性矩阵 —— 默认视野与数值可读性：通过（观察事实）**
- 文档级无横向溢出：`documentElement.scrollWidth = 1024 = 视口宽`；全页面无任何元素宽度超过视口（wide_elements 为空）。
- 安全性矩阵容器 `data-chart-id="home-safety"`：clientWidth 924 / scrollWidth 924，无横向溢出，1024px 默认视野下无需横向拖动即可看到全部三列（产品 / 任何TEAE / 任何SAE）。
- 数值可读：百分比为加粗 14/16px（如 3.1%、22.2%、29.4%、0.6%），缺失状态以中文显式标注（"未公开""暂无公开记录"）并附观察窗说明（如"登记报告期""长期扩展期第8周至末次随访（最长52周）""AE：第1至29天；SAE：第1至36天"），热力色块与文字对比在原生分辨率截图中清晰。
- 主要疗效容器同样无横向溢出（924/924）。

**说明（推断，非缺陷）**：两个首页图形均为 DOM 渲染（无 `<canvas>`），条形图与热力矩阵为 HTML 结构——这是实际渲染形态，数值以文本节点存在，利于可读性与核对。安全性矩阵全高约 4055px，纵向滚动属正常，任务仅要求横向视野。元素截图中部出现的页头条为固定页头在整元素拼接截图中的捕获伪影，非页面缺陷。

## Artifacts And Evidence

- `.artifacts/_visual_probe_values_matrix_visual_w01/home_1024_viewport.png` — 1024×768 首屏（竞争格局卡，页面顶部正常）。
- `.artifacts/_visual_probe_values_matrix_visual_w01/home_1024_full.png` — 首页整页截图。
- `.artifacts/_visual_probe_values_matrix_visual_w01/home_efficacy_chart.png` — 主要疗效卡全元素截图（926×1743），原生分辨率复核过顶部 7 个产品：终点/时间点标签与百分比均清晰。
- `.artifacts/_visual_probe_values_matrix_visual_w01/home_safety_chart.png` — 安全性矩阵全元素截图（926×4055），原生分辨率复核过前 11 行：数值、缺失状态、观察窗小字均可读。
- DOM 测量 JSON（见下节输出）为量化证据。

## Commands And Observations

- 工具：Bash + 项目 `.venv` Playwright（已存在，未安装任何包）；脚本写至 `/tmp` 并已删除，截图写入上述证据目录。
- 探针 1（视口 1024×768，`wait_until=networkidle` + 1.5s）：`viewport_w=1024, doc_scrollWidth=1024, doc_overflow_x=false`；四个首页图形卡（竞争格局/主要疗效/关键安全性/疗效与安全性位置）rect 926px、client=scroll=924、均无横向溢出；无超宽元素；H2 序列完整。
- 疗效卡 innerText 证实 IGA 替代主终点逐产品出现；安全性卡 innerText 证实 TEAE/SAE 数值与中文缺失状态逐产品出现。
- 探针 2（computed style）：疗效卡字号 {16px×28, 14px×140, 13px×1}，替代标签集合含 `IGA 0/1｜第12周`、`IGA 0/1｜第4周`、`IGA 0/1｜时间点见明细`、`EASI-75｜第8周`、`EASI-75｜第4周`、`EASI-75｜多时间点（含第16周）`；安全卡字号 {16px×234, 14px×63, 13px×1}，两卡 `overflow_x=false`。

## Blockers Or Missing Environment

- 无环境阻塞。唯一前置缺口是上下文 Source Of Truth 未填工件路径，已通过 manifest/sitemap 自行定位为 `a-values-matrix-fix-final-v2/reports/A/v1/html/`；若 Codex 指定的验收对象实为其他快照，需告知后可在同一会话重跑本探针。
- 未验证项：1024px 以外的视野（worker_03 范围）、安全性详情页（worker_02 范围）、"查看数据依据"抽屉交互及打印/PDF 形态，均不在本分配项内。

## Rerun Requests Or Next Step

- 本工作项的两项核验（疗效替代时间点/IGA 主终点可见性、安全性矩阵 1024px 默认视野无横向滚动且数值可读）在我视野内均通过，无阻塞、无重跑请求。
- 建议 Codex 确认被审快照路径（final-v2 A/v1）即为验收对象；最终视觉验收与是否准入交付由 Codex 裁定。
