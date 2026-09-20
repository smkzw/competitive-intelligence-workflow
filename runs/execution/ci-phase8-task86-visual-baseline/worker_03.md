I'll start by reading the assigned execution context and plan so I can stay inside the Task 8.6 visual-baseline contract.I’ll locate Task 8.6’s design contract, viewport, offline-runtime, and page-acceptance sources so the matrix is grounded in those files.I have the Task 8.6 files. Next I’ll pull the Kangzhe HTML-PPT track, viewport/offline rules, and existing 8.5/8.6 acceptance language.# Execution Output: ci-phase8-task86-visual-baseline - worker_03

**Fallback:** Codex 主链 `grok-build / grok-4.6` 在可恢复会话建立前不可用；本回合由声明的 `pi` fallback `cursor / cursor-grok-4.6` 执行。限制：未运行 Playwright/真实浏览器截图，未做视觉终验，未改任何产物；只复核合同并给出可执行验收矩阵。Codex 仍是源权威、渲染接受与用户交付的最终决定方。

## Boundary And Context Check

- **Role:** `worker_03` / `ci-phase8-task86-visual-baseline`；只做 Task 8.6 合同复核与验收矩阵，不做 worker_01 收集器实现、不做 worker_02 62 页可读性终审、不做安全测试、不改锁定医学数据、不生成 PPTX、不写 `runs/execution/.../worker_03.md`（由 runner 落盘）。
- **授权写入:** 本工作项未授权改生产/源码/HTML；无新文件。
- **执行上下文缺口:** `context/ci-phase8-task86-visual-baseline_execution_context.md` 的 Source Of Truth 仍为 `TODO`。实际采用的权威来源如下（非生产外路径）。
- **未宣称:** 未完整读到 `track_htmlppt.md` EOF（2646 行）。已读区间：`1–449`、`850–1049`、`2290–2439`。未通读 `core.md` 与 §14.5–§14.7 组件全文、§16.A 全部门禁。矩阵以 Task 8.6 PRD/设计、§0.1/§4/§7.1–7.2/§14.2–14.3/§14.8–14.9、`htmlppt_fx.md`、`project_profile.md`、8.5 投影合同为准。

## Work Performed

复核 Task 8.6 康哲 HTML-PPT 合同、本机显示器 CSS 视口、离线单文件运行时、以及 8.5 移交的逐页标准；把它们压成 **可执行验收矩阵 + 失败关闭条件**。当前候选哈希与 8.5 锁定一致，可直接作为 8.6 基线。

### Evidence：锁定身份

| 报告 | 页数 | 输出 SHA-256 | 输入 SHA-256 |
|---|---|---|---|
| A | 20 | `adcf8487aa85996d0d4886d7801a16a544f2b703cac5a331d4a7a7af085eb2e4` | `988c1607e08c7f9747a6feb493dcdaf66b6ccd7c26cafefe96e956622196fa1a` |
| B | 24 | `087d04b0aa1ddb0da26c5370fcf26e8bb328efc4705136194bbe0ecdb5740b1d` | `eeae14ce581aeacc6c098cde5f45571e4d0f88d2cc5877cba5429654448381d1` |
| C | 18 | `fd2d47565bfdb1b12f6405c62ed53f9762eac67c92175302a5a6eba8d3064113` | `a59d7f88b3d8a2e163422c01f0d0981aa64bf2610cc6bb41852c58e9561ed2e6` |

合计 **62** 页。资产哈希与 8.5 合同一致：`runtime.js` `affadf9e…90f7`，`runtime.css` `09df452d…17d0`，`gx_fx.css` `7e2ba095…a572`，`gx_fx.js` `92cdb591…c86b`，Logo `8d16d3ae…1cae`。磁盘上三份 HTML 哈希与 `.trellis/tasks/08-31-phase-8-task-86-html-ppt-visual-acceptance/checkpoint.md` 一致。

A 实际 `slide_id`：`a-cover,a-toc,a-summary,a-landscape,a-products,a-clinical,a-efficacy,a-efficacy-2..5,a-safety,a-matrix,a-matrix-2,a-regulatory,a-companies,a-patents,a-history,a-limitations,a-ending`。B/C 与投影合同 §4.2/§4.3 清单一致。

**Inference:** git 工作区标了 `assets/html-ppt/*` 已改，但当前字节哈希仍等于锁定值；8.6 收集器必须在每轮截图前重算哈希，不能信任 git 状态。

### Evidence：视口与等比缩放（可计算期望）

合同：逻辑画布恒为 `1280×720`；`s = min(vw/1280, vh/720)`，完整浮点、中心原点、双轴居中；留白只在画布外。浏览器缩放 **100%**。`?preview=N` 不得作为终验原图。

| 视口 | 来源 | s | 画布 CSS px | 外留白 |
|---|---|---|---|---|
| 1280×720 | 逻辑回归 | 1 | 1280×720 | 无 |
| **1280×800** | CFORCE 最大化 CSS | 1 | 1280×720 | 上下各 40 |
| **1920×1080** | Mi Monitor 最大化 CSS | 1.5 | 1920×1080 | 无 |
| **2048×1024** | 非 16:9 压力 | 1.4222… | ≈1820.44×1024 | 左右各 ≈113.78 |
| 1440×900 | 仅 8.5 几何基线，非 8.6 必测 | 1.125 | 1440×810 | 上下各 45 |

机器闸门（§14.9）：`abs(deckRect.height/720 - s) ≤ 0.001`；居中误差 `|x|,|y| ≤ 0.5px`；`abs(deckW/deckH - 16/9) ≤ 0.001`；文档与活动页无滚动溢出。宽屏左右留白、高屏上下留白可接受，**内容不得只堆上半部**。

**80%/125% 缩放**只验证仍能等比居中、无溢出，不是视觉基准。

**跨 OS:** 合同要求 Windows Chrome/Edge 真实最大化 + macOS Chrome + Safari/WebKit。仅本机 Chromium+WebKit = 内核预检。当前显示器记录是 CFORCE/Mi Monitor（macOS 工作站语境）。**不得宣称 Windows 已验。**

### Evidence：离线运行时

- 打开方式：`file://` 必测，不能只测本地 HTTP。
- 单文件：无外链 `src/href`；三份 HTML 中唯一 `http://` 是内联 SVG `xmlns`，不是网络依赖。
- 运行时能力（`project_profile` §4.3 + 8.5 浏览器测试）：方向键 / Home / End / 全屏、`#/N` 深链、页码正文 `N / TOTAL`（禁止伪元素重复写页码）、底部 3px 进度、`N` 打开逐字稿且不与下一页冲突、`S` 讲者窗、`R` 重置。正式交付禁用通用主题轮换/`O` 错误总览克隆。
- 网络：远程 `http(s)/ws(s)` 请求必须为 0；控制台 error 与 `pageerror` 必须为 0。
- FX：kangzhe CSS → `gx_fx.css` → `runtime.css`；脚本 `runtime.js` → `gx_fx.js`。内容页背景计算值为白，无 `.gx-env`/`.gx-net`。`prefers-reduced-motion`、`html[data-export]`、`html[data-qc]` 必须停 rAF、清 canvas、静态真值仍完整。动效不得承载唯一信息。
- 截图前：`document.fonts.ready`、可见图 `complete && naturalWidth>0`、入场动画稳定（8.5 用 900ms，8.6 应在稳定后再截，并同时留交互态与 export 冻结态）。

### Evidence：逐页人工/医学经理标准

不以抽样、测试计数、页面能打开、无横向溢出、contact sheet 或仅 1280×720 截图代替接受。角色：原生中文、视觉敏感、资深临床试验医学经理；结论基于真实使用。点名线路：`pi/cms-router/minimax-m3`、`pi/cursor/default`、`codebuddy/hy3-x`；连通性失败保留原始失败类别，不得静默替换。

首轮必关 8.5 移交项（即使当时标非阻断，8.6 必须关闭）：

1. A `a-matrix-2` 相邻标签留白与引线。
2. C `EASI ≥ 75 %改善` 百分号/中文间距。
3. B `b-efficacy` `92.2` 与图例邻近。

任何重渲染：重算输出哈希；复验 8.5 第三轮六个长英文标签；不得改锁定临床口径。允许改主题、布局、标签避让、间距、字体、色彩、阴影、动效、中文表达。

当前缺口：**有 `data-qc-id`，无 `data-qc-text` / `data-qc-zone` / `data-qc-block`**。§14.9 墨迹框与同层相交检查不能按字面属性跑，必须 Range 回退或本轮补标。无 `data-density=ultra`，故字号地板一律 ≥16px（常规正文目标 19px，内容标题 32px 单行）。

---

### 可执行验收矩阵

**单元 = (报告 ∈ {A,B,C}) × (slide_id) × (视口 ∈ {1280×720, 1280×800, 1920×1080, 2048×1024}) × (引擎 ∈ {Chromium 必测, WebKit 必测}) × (态 ∈ {观众交互, export 冻结, reduced-motion})。**  
最小原图集合：62 页 × 4 视口 × Chromium 观众态 = **248** 张全视口原图。WebKit 至少覆盖同一 4 视口的封面/内容代表页 + 8.5 移交三页；Codex 终验至少再人工看 1920×1080 与 2048×1024 全 62 页原图。截图必须含真实页码与进度 chrome，禁止元素级缩放裁切。

| ID | 层 | 检查 | 方法 | 失败关闭 |
|---|---|---|---|---|
| M0 | 身份 | 输入/输出/资产 SHA 与上表一致；页数 20/24/18；slide_id 全集 | 哈希 + manifest | **P0** 任一漂移且未重开基线 |
| M1 | 缩放 | s 与居中误差符合上表 | `getBoundingClientRect` / `--deck-scale` | **P0** 非等比、取整 scale、100vw/100vh 铺满、页内媒体重排 |
| M2 | 几何 | 活动页 offset 1280×720；同时仅 1 个 `.is-active`；节点不溢出画布；披露行不横向裁切 | DOM，阈值沿用 8.5 `+2.5px` | **P0** |
| M3 | 离线 | `file://`；远程请求 0；page/console error 0 | Playwright request 钩子 | **P0** |
| M4 | 导航 | ArrowRight 走完全部 62；`#/N`；内容页页码 `i / TOTAL` 真文本；封面/目录/结束无页脚页码 | 逐页 | **P0** |
| M5 | 逐字稿 | `N` 开抽屉；每页 notes 汉字 150–300 且含 `<strong>`；观众页不显示 notes | DOM | **P0** |
| M6 | 字号 | 可见正文/标签 ≥16px；标题单行 32px | computed style | **P0** 缩字；KPI/图例用 ultra 例外 |
| M7 | FX/冻结 | 内容页白底无粒子；export/qc/reduced-motion 停 rAF；无 JS 仍可见全部数字 | 双态截图 + 计算样式 | **P0** 动效承载唯一信息或内容页洗橙 |
| M8 | 中文/禁用 | 无 8.5 禁用子串；无后端枚举原文；B 映射 teae/sae 等为中文 | 可见文本扫描 | **P0** |
| M9 | 科学口径 | 不改锁定数；B 不把 APPOINT 画成有对照、不编非 24 周、疾病语境不用血红蛋白冒充；C 无唯一最佳、路径≥2 | 对照 8.5 投影合同 §6 | **P0** 数据口径变化 |
| V1 | 标签 | 不重叠、不越界、不靠裁切；关键值与系列身份尽量直接标 | 原图 | **P0** 读数歧义；**P1** 8.5 三件未关 |
| V2 | 留白/密度 | 使用下半部；死带拆页而非缩字 | 原图 | **P0** 半页空白或过密不可读 |
| V3 | 图例/热图/气泡 | 热图格内有数；气泡轴含义可读；颜色非唯一编码 | 原图 | **P0** |
| V4 | chrome | 标题/Logo 不相交；正文底 ≤660；页脚两槽；进度在视口底 | 原图+几何 | **P0** |
| H1 | 人工 | 医学经理角色逐页；三线路连通性先测 | 真实使用 | 连通失败 **P0 流程**（保留失败类）；视觉阻断由 Codex 裁定 |
| X1 | 范围外 | 安全测试、PPTX、改临床锁定数据 | — | 出现即 **范围违规**，不计入通过 |

**关闭循环（设计合同）:** 当前原图 → 缺陷归因（页、视口、引擎、态）→ 最小修订 → 全相关页回归 → **原会话**复验。三轮定向美化仍不合格则拆页/拆图，禁止带已知 P0 交付。修订后必须：重算哈希、复跑结构/离线/Chromium/WebKit/Ruff、复验六长标签。

**通过定义（建议 Codex 采用，worker 不宣布 accepted）:**

1. M0–M9 全绿，绑定当前三哈希。
2. 248 张 Chromium 原图 + WebKit 预检齐，无 P0。
3. V1 三项 8.5 移交关闭且全 62 页无确定性读数阻断。
4. 三线路连通性有原始记录；Codex 在 1920×1080 与 2048×1024 看完全部原图。
5. 若无真实 Windows：交付说明写明「Windows 未实机验证」，不得写多端一致。

## Artifacts And Evidence

- 本报告即本工作项交付物（验收矩阵与失败关闭）。
- 只读来源：Task 8.6 `prd.md`/`design.md`/`implement.md`/`checkpoint.md`/`task.json`；`docs/acceptance/runs/8.6/visual-research.md`；8.5 `projection-contract.md`/`candidate-inventory.md`/`browser-contract-evidence.md`；`contracts/kangzhe/design_specs/{ROUTER,project_profile,track_htmlppt,htmlppt_fx}.md`；`assets/html-ppt/{runtime.js,runtime.css,manifest.json}`；`tests/html_ppt/test_html_ppt_browser_contract.py`；`output/html-ppt/report-{a,b,c}.html` + manifests。
- 未创建截图/台账（属 worker_01）；未做 62 页可读性页级证据（属 worker_02）。

## Commands And Observations

```text
python3  # SHA-256 of output/html-ppt/report-{a,b,c}.html and runtime/FX/logo
python3  # manifest slide_ids + notes_han
python3  # count data-qc-* and http:// in three HTML files
```

观察：三 HTML 哈希与 8.5/checkpoint 锁定一致；runtime/FX/logo 哈希一致；`data-qc-id` A137/B165/C123，`data-qc-text/zone/block` 均为 0；`http://` 仅为 SVG xmlns。未跑 pytest/Playwright/浏览器。

## Blockers Or Missing Environment

1. 执行上下文 Source Of Truth 未由 Codex 填写；本矩阵是基于仓库合同的建议，不是 Codex 已批准的 SSOT。
2. 未记录真实 Windows 最大化视口；跨 OS 不得关闭。
3. `data-qc-text/zone/block` 缺失，§14.9 墨迹/相交闸门需 Codex 决定：本轮补标 vs Range 回退。
4. 点名三线路连通性本 worker 未测。
5. `track_htmlppt.md` 未读到 EOF；§16.A 全部门禁未纳入本矩阵正文。

**向 Codex 的精确问题：** 本轮 8.6 是否把「真实 Windows 最大化」列为 P0 关闭条件，还是允许在交付说明中显式降级为 macOS CFORCE 1280×800 + Mi 1920×1080 + 2048×1024 + WebKit 预检？同时，是否要求本轮给 62 页补齐 `data-qc-text/zone/block`，否则归一化几何只以现有 `data-qc-id` + Range 回退为准？

## Rerun Requests Or Next Step

1. Codex 裁定 Windows 与 QC 属性范围后，worker_01 按本矩阵四视口收集原图/诊断并绑定三哈希。
2. worker_02 用同一页清单做医学经理可读性，优先关 `a-matrix-2` / C `75 %` / B `92.2`。
3. 修订后同一会话复测 M0–M9 + 相关页原图；Codex 做最大化原图终验。本 worker 不宣布 Task 8.6 通过。
