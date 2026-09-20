# Conference Participant Output: ci-phase6-final-visual-review - visual_single_object

## Boundary Check

- 第 2 轮续跑，同一会话，全程只读：未编辑任何源码或产物；仅对新候选 `b-pnh-responsive-visual-evidence-20260830` 启动临时静态服务（127.0.0.1:8932，用后已停止）与无头浏览器实测。
- 未写 runner 管理的报告路径；未做最终签收，Codex 保留最终权威。
- 新候选摘要核验：`browser-metrics.json` 中 `exact_content_digest = f1b37ba47459…3800381`，与指派一致；实测对象即该目录。旧候选（f094848b）本轮未再审。
- 覆盖范围声明核验：browser-metrics 记录 24 条路由 × 2 引擎 × 3 视口，截图目录实测 150 张 PNG，与指派相符。

## Independent Work Product

**总体结论：接受（accepted）**。第 1 轮三项阻断在新候选中全部实测解决；七域均通过；未发现新阻断项。

### 第 1 轮阻断复测（全部实测，非采信 JSON）

| 阻断 | 复测方法与结果 | 状态 |
|---|---|---|
| T-1：768 表格末列裁切 | 本地服务新候选，768 视口逐页实测 `table.scrollWidth > wrap.clientWidth`：overview（13 表）、safety、baseline-overview、disposition-overview、efficacy、efficacy-safety-matrix、participant-flow、screen-failure、adherence **全部 0 溢出**，文档级溢出亦 0。截图佐证：`chromium/safety-768.png`、`baseline-overview-768.png`、`disposition-overview-768.png`、`webkit/safety-768.png` 均显示堆叠卡片布局，"未列示/未公开/不适用/已报告值"完整可读、无半个字符裁切 | **已解决** |
| I-1：菜单→搜索不聚焦 | 768 下真实点击"菜单"：`document.activeElement = INPUT#global-search-input`，搜索框可见且有焦点环（`chromium/responsive-search-768.png` 视觉一致） | **已解决** |
| I-2：Escape 清空查询且面板不关 | 768 下真实输入"疗效"（10 条结果）→ 单次真实 Escape：MutationObserver 仅记录 hidden false→true 一次，**无重开**；`hidden=true`、`query="疗效"` 保留、焦点留在输入框。第 1 轮的"清空+重开默认列表"现象消失 | **已解决** |

### 第 1 轮轻微缺陷复测

- "APPOIN T–PNH" 断词：新候选 768 截图中试验名 "APPOINT–PNH" 完整不断行。**已解决**。
- 证据指标盲区（`clipped_text_count` 只测文档级）：本轮我以容器级度量（`table.scrollWidth ≤ wrap.clientWidth`）替代验证；建议 Codex 确认该指标是否已纳入新 browser-metrics 的断言口径（见下"有界问题"）。

### 七域逐项结论（新候选）

| 域 | 结论 | 证据 |
|---|---|---|
| 文字 | 接受 | 试验名断词已修复；截图未见乱码、截断字 |
| 版式与间距 | 接受 | 768/1024/1440 文档级溢出实测 0；卡片间距一致 |
| 配色 | 接受 | 治疗橙/对照蓝一致；状态色区分"已报告/未公开/不适用" |
| 图表 | 接受 | 首页/安全性页热图 768 完整入视口无需横拖（截图 + 0 溢出实测）；单臂气泡图有显式说明 |
| 表格 | 接受 | 768 全部改为堆叠卡片，分子/分母/披露状态完整；9 个复用表格页面容器级实测 0 溢出 |
| 交互 | 接受 | 菜单→搜索自动聚焦（实测）；单次 Escape 关结果且保留查询（实测）；抽屉 Enter/Space 打开、Escape 关闭、焦点返回（第 1 轮已验证，本轮截图 `interaction-drawer-1440.png` 显示抽屉焦点环与完整出处链） |
| 中文原生表达 | 接受 | "点击数值查看数据依据""披露状态：已报告值""原文未提供"等自然；无工程术语外泄 |

### 信息充分性（医学经理视角，维持第 1 轮判断）

疗效仅 1 个公开终点、安全性事件有限，属数据真实形态；"未公开/未列示/不适用/已报告值"四级区分清晰且抽屉可查证（来源版本、原文定位、章节/表/列）。不构成视觉阻断；建议签收记录注明跨产品对比深度有限。

## Evidence And Assumptions

**证据（实测）**
- 新候选本地服务 + 无头 Chromium：9 个含表页面 768 容器级溢出度量；菜单聚焦；真实 Escape + MutationObserver 追踪。
- 截图直接查看/放大：`chromium/safety-768`、`baseline-overview-768`、`disposition-overview-768`、`overview-768`、`responsive-search-768`、`interaction-drawer-1440`；`webkit/safety-768`。

**推断（[INFERENCE]）**
- WebKit 侧仅做截图级抽查（safety-768 堆叠卡片正常），未跑 WebKit 真实键盘；第 1 轮 WebKit 缺陷与 Chromium 同源，本轮修复为组件级，推断 WebKit 同步修复。
- 1024/1440 未逐页重测——第 1 轮该两档无缺陷，本轮变更集中在 ≤899px 断点与头部 JS；抽查 `interaction-drawer-1440.png` 正常。

**假设**
- 修复仅作用于门户共享组件（`portal.js`/表格断点），不影响科学内容；本轮未重核数据正确性（超出视觉审阅范围，由科学/数据角色覆盖）。

## Risks, Gaps, And Verification Needs

1. **WebKit 键盘路径未实测**：Escape/聚焦仅截图级佐证；若 Codex 要求双引擎交互证据，补一次 WebKit 键盘探针即可（browser-metrics 声称已含，未独立复现）。
2. **指标口径**：建议确认新 browser-metrics 是否已将容器级表格溢出纳入断言，避免旧盲区回归。
3. **第 1 轮证据矛盾闭环**：I-1/I-2 在原候选上"声明通过、实测失败"，本轮新候选实测通过——推断证据脚本断言已随修复一并校正，但我未审该脚本本身；如证据脚本未改，其对旧候选的"通过"声明仍是未解释的历史矛盾。

## Recommended Next Step

1. Codex 独立抽查 2–3 张代表截图（建议 `chromium/safety-768.png`、`chromium/responsive-search-768.png`）确认我的复测结论。
2. 有界问题待 Codex 决定：是否要求补 WebKit 真实键盘探针（我认为截图 + Chromium 实测已足够，WebKit 补测属可选加固）。
3. 我的角色结论：新候选 f1b37ba4 **七域全部接受**，第 1 轮阻断全部标记 resolved，无新阻断；视觉签收可由 Codex 裁决推进。
