# Conference Participant Output: ci_phase6_task69_visual_review - visual_single_object

## Boundary Check

- 仅在工作区内读取：`output/acceptance/task-6.9/site/`（B 类门户成品）、`assets/portal/`（静态资源源）、`contracts/kangzhe/design_specs/core.md`、`track_site.md`（设计真源，作验收依据）。未读生产路径、未改任何文件。
- 驱动了真实 Chromium（headless）遍历全部 29 条静态路由 × 768/1280 视口，外加交互闭环实测。未做 WebKit 实机检查（本环境无 WebKit），未声明最终视觉/临床验收权——最终验收归 Codex。
- 未创建报告文件；本回复即完整产出，由 runner 持久化。
- 路由与包链说明：context 文件记录的包分支为 `night`，但本会话按北京 `day` 边界后的当前路由 `pi/kimi-code/k3-256k` 录取（新会话，未在边界前启动）——与 prompt 首行指示一致，无静默跳链。

## Independent Work Product

以"不熟悉计算机、视觉敏感的中文母语资深医学经理"角色完成全门户终验。**结论：发现一个真实 P1 缺陷（字号地板），两个 P2 视觉/IA 问题，一个需 Codex 裁决的数据覆盖面问题；交互、链接、零/缺失语义、中文原生性均通过。**

### 缺陷发现

**F1（P1，正文/标签字号低于设计真源地板）** — `contracts/kangzhe/design_specs/core.md §0.7` 规定 interactive 轨正文/标签默认下限 16px，高密度表体/轴标签可 14px 且 NEVER <13px。实测（computed style，7 页抽样）：
- 各页导语 `p.kz-page-lede` 类段落 = **14px**（这是 H1 下的主说明正文，非表体/轴标签）；
- 产品档案页正文段落（如"境外 · II期研究完成 · 2026-…"）= **13px**，触及 NEVER <13 硬线且不属于表体豁免；
- `kz-b-section-eyebrow`（"图形定位/完整数据表"）= 13px、`portal-page-kicker`（"总览/疗效与安全性"）= 14px、`kz-b-filter-quick__label` / 筛选摘要 / `kz-b-section-note` / `kz-b-evidence-hint` = 14px。
- 合规项：图表紧邻数据表单元格 14px（高密度表豁免）、图例 14px（轴标签豁免）、按钮 16px。
- 修复面小：这些是 CSS 类级集中定义（`portal.css` / `report-b.css`），把 eyebrow/kicker/lede/note/hint/档案正文提到 16px 即可全面修复；对"视觉敏感的资深用户"这是验收硬指标而非口味问题。

**F2（P2，同终点小多图 y 轴刻度不一致）** — 纵向结果/疗效页按组别拆分为单组小图：EASI-75 应答率治疗组轴 0–68.4、对照组轴 0–31.2（live `echarts.getModel()` 实测 extent）。同一终点同一单位的不同小图刻度不同，视觉比较条高会误导——对照组 31.2% 的柱子在视觉上几乎顶满，与 68.4% 的柱子高度观感接近。建议同终点同单位分组共享 `yAxis.max`（`charts.js` bar builder 已强制 min≤0，只需加组级共享 max）。注：我起初怀疑轴截断（截图底缘从 20 起），实测 axis extent min=0，撤回该疑点——截断不存在。

**F3（P2，信息架构疑问）** — "疗效与安全性矩阵"页面归属顶栏"试验与证据"分组（`site-nav-group` 结构确认），医学经理直觉会在"疗效与安全性"下拉里找它。属 IA 判断题，非硬错误，提请 Codex 裁决。

**F4（待 Codex 确认，数据覆盖面）** — 处置全模块（受试者流转、依从性、失访与退出、筛败与原因、补救治疗、禁用药使用、方案偏离）及基线各页在交付 site 中全部落"暂无公开记录/暂无可绘制值"空态；嵌入 JSON 证实行级为 `disclosure_state: "not_reported"`、`renderable: false`。门户 fail-closed 行为正确，但 Task 6.5–6.8 已建成基线/处置视图模型而验收 fixture 无对应事实行——若 B 类验收预期含非空处置/基线数据，这是 fixture 侧缺口而非门户缺陷。请 Codex 裁决验收数据范围。

### 通过项（实测证据）

- **全路由健康**：29 路由 × 768/1280 共 58 次加载，整页横向溢出 0、控制台错误 0、page error 0。
- **离线闭环**：`file://` 下远程请求 0；`assets/` 内嵌 ECharts 6.1.0 + logo.svg 加载成功；全站内部链接完整性扫描 0 断链（含产品/试验档案页 8 条）。
- **缺失≠零语义**：安全性热图"泰瑞奇单抗·任何TEAE=0"携带披露状态"已报告零值"（嵌入数据 `reported_zero`），与"未列示/暂无公开记录"明确区分；抽屉/表格状态同步。
- **筛选→URL→恢复**：点击产品快捷筛选 → URL 增加 `?product=fixture-product`、32 行中 24 行隐藏、chip 高亮"已选 1 项"；带参重开后状态完整恢复。
- **数据依据面板**：点击数值 68.4 打开同页抽屉，含产品/试验/组别/时间点/值/披露状态/规范化说明/来源版本（ClinicalTrials.gov）/原文定位，全中文。
- **固定对照**：抽屉"固定此条"→ 固定面板并列展示定义/时间点/分母核对字段，URL 同步 `?focus=eff-fixture-t`。
- **全局搜索**：输入"热图"返回"安全性"结果。
- **首屏主图可见**：768×900 下首页主图 top=703px < 900，符合"默认桌面视野主图可见"。
- **中文原生性**：标题、导航、按钮、空态、表头全中文；工程泄漏扫描（Traceback/TODO/undefined/NaN/模型名等）仅在不可见的嵌入 JSON 数据载荷中命中 `null`，可见文本 0 命中。
- **设计语言**：浅色面积远高于 80%，橙黄仅用于强调/当前态，无风险红滥用；Logo 内嵌、浅色顶栏可读。

## Evidence And Assumptions

- **证据（实测）**：上述全部通过项与 F1/F2 的数字均来自真实浏览器 computed style、`echarts.getModel()` live extent、DOM/URL 状态与截图（`/var/folders/.../omp-sshots-*.webp` 系列）；链接完整性来自 shell 全量 href 存在性检查；字号地板引用 `core.md §0.7`、`track_site.md` L142。
- **推断**：F1 中"lede 段落属正文而非标签"是我的分类判断——即便按最宽松解释（归为辅助标签），§0.7 的"正文/标签默认下限 16px"同样覆盖；档案页 13px 正文在任何分类下都触 NEVER <13 硬线。
- **假设**：假定 `output/acceptance/task-6.9/site/` 即本次终验目标成品；假定 fixtures 数据即验收数据（F4 待裁决）。
- **不确定性**：① 1024/1440 视口本轮 sweep 未覆盖（只跑 768/1280；既有 `output/playwright/task-6.9-final` 截图存在但未复核其内容）；② WebKit 未测；③ `prefers-reduced-motion` 冻结与导出冻结动效未触发验证；④ 抽屉"原文未提供"是否为 fixture 真实来源状态，属数据侧问题，门户如实呈现。

## Risks, Gaps, And Verification Needs

- **R1**：F1 若不修，正好撞验收项"正文/控件默认不低于 16px"与设计真源 §0.7，按用户规则属不可放行的 P0/P1 级。
- **R2**：F2 在真实（非 fixture）数据下误导风险放大——真实竞品数据组间差异更依赖小多图可比性。
- **R3**：WebKit 缺口是验收清单明文项（"Chromium 与 WebKit 全路由"），必须由具备 WebKit 的执行者补齐；建议 Codex 直接复核。
- **验证需求**：F1 修复后需重跑 7 页字号抽样（脚本 10 行可复用）；F2 修复后需复测同终点小多图共享 max 且单图页不受影响。

## Recommended Next Step

1. Codex 裁决 F4（处置/基线空态是 fixture 事实还是数据缺口）与 F3（矩阵导航归属）。
2. 若进入修订轮：一处 CSS 类级修复字号（lede/kicker/eyebrow/note/hint/档案正文 →16px），一处 `charts.js` 组级共享 `yAxis.max`；两者均为低风险定点改动，随后我在本会话内同路由复测。
3. 修复后由 Codex 执行 WebKit 全路由与 `prefers-reduced-motion`/导出冻结检查并做最终视觉验收。
4. 我对 Codex 的有界提问：**处置与基线模块的"暂无公开记录"是否即 B 类验收的预期终态？** 若是，门户可视为除 F1/F2 外无实质缺陷；若否，缺口在 fixture/数据管线而非本门户，验收范围需相应调整。
