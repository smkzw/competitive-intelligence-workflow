按 R5 追问继续只读复核：先读 follow-up 提示，再按其列出的证据做针对性复检。接下来只看 R5 验收目录：先确认报告与关键截图是否齐全，再逐项复核原先的阻断问题。C 类叠字似已改善；接着核对 B 类处置/矩阵、跨浏览器，以及 live 页是否仍泄漏内部字段。B 的 overview/disposition 截图仍像空 KPI；接着用 live HTML 核对渲染是否与截图一致，并检查内部字段泄漏。截图与 live 仍不一致；继续抽查 A 矩阵、C 终点页与 B 处置轴标签，确认是否仍有阻断级问题。# Visual Review R5: named_pi_cursor_default

## 复核范围

- **候选**：仅 `task-10.2-20260901-123524-r5/{a,b,c}-real`（R1 历史站不计入本轮放行）。
- **Deterministic**：三份 `verification/*/v1/report.json` 均为 `ok: true`、全路由 `violations: []`（Chromium/WebKit × 含 1280/1920）。
- **已目视 PNG（1280/1920，必要时补 WebKit）**：  
  A：`overview` / `efficacy` / `safety` / `matrix`  
  B：`overview` / `efficacy-safety-matrix` / `disposition-overview` / `baseline-demographics`  
  C：`overview` / `design-map` / `endpoint-timepoint-matrix` / `trial-profile` / `trials_nct02260986`
- **Live 只读核对（1280）**：A `overview.html`、`matrix.html`；B `overview.html`、`disposition-overview.html`；C `design-map.html`、`endpoint-timepoint-matrix.html`。
- **声明**：deterministic 绿灯 ≠ 医学经理主观放行；下列结论以实际 PNG + live 渲染为准。

## 已关闭问题

| 原问题 | R5 证据 | 状态 |
|---|---|---|
| C `design-map` / `endpoint-timepoint-matrix` 叠字不可读（原 P0） | Chromium/WebKit 1280/1920 PNG 表头、单元格可读；live 行内容（入选/终点定义等）完整 | **关闭** |
| 用户可见 `trial_identity`（原 P1） | live `body` 无该串；按钮可见文案为「试验标识」；`trial_identity` 仅存 `data-filter-value` | **关闭（可见层）** |
| A 首页首屏无疗效比较（原 P1） | live A overview 首屏即为「主要疗效」柱状图（治疗组/对照并列），其后才是安全热图/矩阵/格局 | **live 已关闭** |
| A/B 关键疗效、安全、气泡矩阵默认可读且无整页横向拖动 | A efficacy/safety/matrix、B efficacy-safety-matrix PNG+live：`pageHScroll=false`，轴含义中文可读 | **维持关闭** |
| C 试验详情缺顶部设计摘要（原 P2 倾向） | `c_trials_nct02260986` 首屏有阶段/随机盲法/终点等摘要卡 | **基本关闭** |

## 仍存问题

| 严重度 | 位置 | 问题 | 取证 | Remediation |
|---|---|---|---|---|
| **P1** | A overview / B overview / B disposition / B baseline 等验收 PNG | **截图与当前 live 不一致**：PNG 多为四个「—」空 KPI 或旧首屏（A overview PNG 仍是「竞争格局」大表）；live 已是图表。证据链不能支撑签字 | A/B overview、B disposition、B baseline PNG vs live | 浏览器验收必须等图表 hydrate 后再截；PNG SHA 绑定 `site_digest`；失败则 deterministic 视觉证据不得记通过 |
| **P1** | B `/b/disposition-overview` live | 一张图把「已筛选/已随机/完成治疗」**人数**与「相对剂量强度」混在同一纵轴，轴名却写「相对剂量强度」；扫一眼会误读 | live 图：125/62/35 与 100.6 同轴 | 分图或双轴；人数图轴名改为「例数/人数」；剂量强度单独成图并标注单位 |
| **P2** | C `/c/overview` PNG 1280/1920 | 首屏四张 KPI 全是「—」，无比较洞察 | `c_overview__chromium__{1280,1920}` | 填真实汇总，或去掉空卡、直接上设计比较缩略 |
| **P2** | C `/c/design-map` | 页名「设计图谱」，主体仍是长表，不是图谱/并排关系图 | PNG + live | 保留全字段表为下沉；首屏加试验×设计要素关系图或卡片式并排 |
| **P2** | B disposition 展开筛选项时 | 侧栏/芯片与主表表头区域视觉叠压，影响扫读 | live 滚动后截帧 | 筛选抽屉与表头分层/锁位，避免覆盖 |

**非阻断观察**：A matrix 气泡标签在密集区仍偏挤，但 1280 下图完整、轴说明清楚，不升 P1。

## 结论

| 对象 | Deterministic | 医学经理主观（对本轮 R5） |
|---|---|---|
| **A** | 通过 | **条件通过（live）**：疗效/安全/矩阵与首页层级已达可比较；但 overview 验收 PNG 失真，**不能仅凭截图包放行** |
| **B** | 通过 | **否决**：处置图轴语义错误（P1）+ overview/disposition/baseline 截图失真（P1） |
| **C** | 通过 | **通过（可读性）**：原 P0 叠字与可见字段泄漏已消；残留为空 KPI、名实不符图谱（P2） |
| **总体** | 机器全绿 | **否决** |

**一句话**：R5 已修好 C 类“打不开/读不懂”的硬伤，A 类 live 也比较像样；但 **验收截图仍经常拍到未渲染的空壳**，且 **B 处置图把人数和剂量强度糊在同一轴上**——这不是医学经理会签字的状态。先消全部 P1 并重绑截图证据后再送审。
