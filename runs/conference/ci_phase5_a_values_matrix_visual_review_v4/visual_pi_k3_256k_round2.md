针对 v5 做只读定向复核：先读绑定指标和截图，再核对首页与安全性页的矩阵/表格结构。绑定截图和指标已显示 1024 四列、768 为 2+2。接着用 v5 HTML 实渲染核 1280/1440 列名、768 表头隐藏和粘性碰撞。# Conference Participant Output: ci_phase5_a_values_matrix_visual_review_v4 - visual_pi_k3_256k_round2

## Boundary Check

- Same Grok Build session, directed round-2 visual recheck only. Codex remains final authority.
- Read-only. Did not modify project files or artifacts. Did not read other participant outputs. Did not search the web.
- Inspected only the assigned v5 packet: `overview.html`, `safety.html`, `final-v5/metrics.json`, and the four bound screenshots. Live Chromium was used solely to open those two HTML files at 768/1024/1280/1440.
- Did not write `visual_pi_k3_256k_round2.md`; this response is the report.

## Independent Work Product

上一轮两项阻断在 **final-v5** 上按四点复核。结论先写：**本轮四项定向视觉复核通过。** 不替代 Codex 终验。

### 1. 1024 / 1280 / 1440：四列并列、无横向拖动

**观察**

- 绑定截图 `overview-safety-matrix-1024.png`、`safety-safety-matrix-1024.png`：单一热图表头为「产品 | 任何TEAE | 任何SAE | 预先界定AESI | 鼻咽炎」，四事件列在同一矩阵内横排。
- 绑定 `metrics.json`：Chromium 与 WebKit 在 overview/safety 的 1024、1280、1440 均为 **1 个 heatmap、`eventCount: 4`**，`documentWidth` 等于 viewport，`chartClientWidth == chartScrollWidth`，heatmap `clientWidth == scrollWidth`。
- 本轮 Chromium 实开 v5 HTML：

| 页面 | 视口 | host 宽 | 块数 | 列名 | 页面溢出 | 图溢出 |
|---|---|---|---|---|---|---|
| overview / safety | 1024 | 924 | 1 | 任何TEAE, 任何SAE, 预先界定AESI, 鼻咽炎 | 0 | 0 |
| overview / safety | 1280 | 1100 | 1 | 同上四列 | 0 | 0 |
| overview / safety | 1440 | 1100 | 1 | 同上四列 | 0 | 0 |

- 安全性页 1024/1280/1440、视口高 900：四列表头均 `inViewport: true`。上一轮 1280/1440 的 3+1（鼻咽炎单独第二块）未再出现。

**推断：** 根因（host&lt;1250 时切 3 列）已改成宽屏固定 4 列一块。第四维不再需要滚过 38 行产品。

**结论：** 第 1 点通过。

### 2. 768：明确 2+2，两块均无横向拖动，数字/名/观察窗可辨

**观察**

- `safety-safety-matrix-768.png` 与 `safety-768.png`：上块「任何TEAE | 任何SAE」，下块「预先界定AESI | 鼻咽炎」，各 38 行。
- `metrics.json` Chromium/WebKit overview+safety@768：两个 heatmap，各 `eventCount: 2`，宽 668=668，页面 768=768。
- 实渲染：overview/safety@768 均为 `[["任何TEAE","任何SAE"],["预先界定AESI","鼻咽炎"]]`，`heatOverflow [0,0]`，`pageOverflow 0`。
- 截图中 73%、22.2%、未公开、16周双盲治疗期、乐德奇拜单抗换行、芦可替尼乳膏长观察窗换行后仍完整可读，未见列被裁切。

**推断：** 768 用两块各两列，而不是 3+1 或挤四列。换行发生在单元格内，不是横向拖动。

**结论：** 第 2 点通过。

### 3. 768 明细表：隐藏「试验」「人数」；「未公开」不再拆成「未公/开」

**观察**

- `safety.html` 仍有 8 列表头（产品/试验/组别/维度/事件/发生率/人数/观察窗）。
- `safety-768.png` 可见表头为 **产品、组别、维度、事件、发生率、观察窗**（6 列）。
- `metrics.json` `chromium-safety-768` / `webkit-safety-768`：`trialColumnDisplay: "none"`，`countColumnDisplay: "none"`，`splitUnpublished: false`，表 `668==668`。
- 实渲染 safety@768：`试验`、`人数` 的 `display: none`（含对应单元格）。可见首行：度普利尤单抗、治疗组、特别关注不良事件、预先界定AESI、未公开、主要对照期。发生率「未公开」几何 **68×60**，`innerText` 为完整「未公开」，无换行拆字。上一轮失败时该格约 53 px。

**推断：** 768 用隐藏两列换宽度，而不是 `overflow-wrap: anywhere` 拆「未公开」。60 px 行高来自「特别关注不良事件」等长字段换行，不是「未公开」被拆开。

**结论：** 第 3 点通过。

### 4. 热图与明细粘性表头不再与站点顶栏碰撞

**观察**

- 实测站点顶栏高度/底边均为 **68 px**。热图表头与明细 `thead` 的 `stickyTop` 为 **68px**。
- 滚动后粘住时：产品/任何TEAE/任何SAE/预先界定AESI/鼻咽炎（1024+）及 768 明细可见列，`top: 68`，`headerBottom: 68`，**overlap 0**。768–1440 均如此。
- 绑定指标 `stickyTop: "68px"` 与之一致。上一轮 `--header-h: 64px` 造成的 4 px 遮挡未再测到。
- `overview-safety-matrix-1024.png` 中段出现整条顶栏，是长图截取时 sticky 顶栏叠在热图中部的截图像素，不是表头钻进 Logo/标题；粘住的事件列名贴在橙线下方，未被顶栏文字盖住。

**推断：** 粘性偏移已与实测 68 px 顶栏对齐，几何重叠为 0。

**结论：** 第 4 点通过。

## Evidence And Assumptions

**Evidence**

- 产物：`.artifacts/a-values-matrix-fix-final-v5/reports/A/v1/html/{overview,safety}.html`
- 绑定：`reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v5/metrics.json` 及四张指定 PNG
- 本轮 Chromium 对上述两个 HTML 的 768/1024/1280/1440 几何测量（列名、块数、溢出、列 display、sticky overlap）

**Inference**

- 四列并列与 2+2 是布局修复，不是截图裁切造成的假象。
- 768 表可读性改善来自隐藏列，不是放大字号。

**Assumptions**

- 第 1 点的「同一矩阵」= 一个 heatmap 内四事件列，不要求首页首屏不滚动就看到热图（热图仍在格局/疗效之下）。
- 「可辨认」允许单元格内正常换行，不允许列溢出或「未公/开」类拆字。

**Uncertainty**

- 本轮未再跑 WebKit；WebKit 仅以绑定 `metrics.json` 为准（与 Chromium 同结构：4 列/2+2、无溢出、768 隐藏两列、`splitUnpublished: false`、`stickyTop: 68px`）。
- 绑定截图没有 1280/1440 矩阵 PNG；这两档靠 metrics + 本轮 Chromium。
- 未测展开「菜单」后顶栏变高时的 sticky。
- 未重做筛选交互（本轮四点范围外）。

## Risks, Gaps, And Verification Needs

- 剩余风险低，且限于本轮范围外：WebKit 像素级表头、菜单展开后的 header 高度、AESI 列大量「未公开」仍是医学内容问题而非本轮布局回归。
- Codex 终验仍应用 v5 实件在 768 与 1440 各打开 `safety.html` 看一眼四列表头与 768 表头六列。

**对 Codex 的问题：** 无。四点在指定范围内已闭合。若 Codex 需要 WebKit 像素截图补 1280/1440，那是终验补强，不是本轮失败。

## Recommended Next Step

Codex 可将本轮四点记为 **advisory pass**，并在终验中绑定 `.artifacts/a-values-matrix-fix-final-v5/` 与 `final-v5` 截图/metrics，不要再用 v4。本参与者不授权改文件，不替代最终接受。

**本轮四项定向视觉复核通过。**
