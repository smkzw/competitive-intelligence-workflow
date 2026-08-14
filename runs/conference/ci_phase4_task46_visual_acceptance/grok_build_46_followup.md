上一轮停在准备阶段，没有验收结论。现在直接跑全站命令，并同时打开真实门户核对画面。入口不是 `index.html`，这点要查清。全站命令先跑起来，同时打开真实页面。验收命令已在跑。我先核对门户真实画面，再等命令出数。命令已退出 0，不能单凭这个结案。接下来核对我自己产出的 96 张图、两条 trace，并打开真实页面。# Task 4.6 全站视觉验收

**Verdict: REVISE**

验收器自己跑通了：16 路由 × Chromium/WebKit × 1280×800 / 1440×900 / 1920×1080，96 张原分辨率图、两条 trace，`site_digest` 与清单一致，自动缺陷模型无死链/溢出/双页脚/站外请求。**退出码 0 不能当通过。** 医学经理在真实画面上仍会卡住：详情页标题是 `product-01` / `trial-02` 这种机器名，而且全站导航和搜索都进不去这些页。验收器按文件打开它们，所以会假绿。

## P0 / P1 / P2

**P0**  
无。站点能出、清单 16 页齐、截图尺寸对得上，没有整站打不开或地图缺页。

**P1**

1. **详情页把程序员编号写进大标题。** 产品/试验页 H1 是「产品档案：product-01 / product-02」「试验档案：trial-02」。懒、不熟电脑的医学经理分不清这是哪个药、哪个试验。「锁定快照中对该对象的详细信息」也是系统腔。  
   复现：Chromium 1280 `a_products_product-01__chromium__1280x800.png`；WebKit 1440 `a_products_product-02__webkit__1440x900.png`；Chromium 1920 `a_trials_trial-02__chromium__1920x1080.png`。  
   合同把「英文/程序员标签侵入用户界面」算本任务范围；这不是 Phase 5–7 才补的医学正文。

2. **清单里的 3 个产品页 + 2 个试验页，门户里点不到。** 静态 HTML/JS 里没有 `products/product-*`、`trials/trial-*` 链接；搜索索引也只有 11 个静态页。验收器是 `file://` 直开，所以 `ok: true`。人从「总览 / 产品总览 / 临床开发组合」走，永远到不了详情。  
   复现：全站 `html/` 检索无详情链接；`product-overview.html` 只有两张不能点的「重点模块」卡。浏览器：Chromium/WebKit；视口：三档截图均如此。

**P2**

- 搜索框 1280 只露出「搜索页面或关键词..」。`a_overview__chromium__1280x800.png`
- Logo 链到 `clinical-portfolio.html` 不是首页/总览。
- 会议写入口是 `html/index.html`，目录里没有这个文件，真入口是 `overview.html`。验收器按注册表 `/a/overview` 是对的，文档路径是错的。
- 「重点模块」卡不可点、无图。按合同不算医学内容缺失的 P1。

## 命令与对账

```text
uv run python tools/verify_portal.py --report A --project .artifacts/task46-visual \
  --version v-fixture-001 --browser chromium --browser webkit --all-routes \
  --output-dir .artifacts/task46-visual/reviewer-grok
```

- 退出码 **0**，约 42s。stdout：`全站验收通过：16 个路由…`；`A_PORTAL_OK routes=16 browsers=2`
- 我的产物：`.artifacts/task46-visual/reviewer-grok/report.json`  
  `ok: true`，`run_digest=79cdfccaa22e…`，`site_digest=a91d7e77ef7eac0c50ded88ca12bc37f7f6fb391cb7c4c9cff14c61248c89bd4`（与 `html.manifest.json` artifact.sha256 一致），`manifest_id=artifact-manifest_faf5603d98b653ab12ae60f4`
- 路由 16：11 静态（与清单 `pages_or_sections` 一致）+ `product-01/02/03` + `trial-01/02`（与清单 `product_ids`/`trial_ids` 一致）。无 Top-N、无漏页、无额外 slug。
- 截图 96 张、96 次 check、96 个不同文件哈希；文件名 = 路由 × 浏览器 × 视口；像素 **32×1280×800、32×1440×900、32×1920×1080**，无尺寸错配、无空图。
- Trace：`traces/trace__chromium__79cdfccaa22e.zip`（2.5MB，188 项）、`trace__webkit__79cdfccaa22e.zip`（2.9MB，210 项），内含 `trace.trace`。

Codex 旧跑 `.artifacts/task46-visual/verification/A/v-fixture-001/report.json` 同样 16/96/`ok:true`。我没有改那份产物。

## 看过的画面

亲自打开并核对（含本跑 `reviewer-grok/screenshots/`）：

- 总览/首页 1280 Chromium、1920 WebKit：中文导航、浅底橙条、单一中文页脚；搜索截断。
- 医学结果、临床开发组合、产品总览、竞争格局：层次清楚，无串行、无横溢。
- 产品/试验详情 1280/1440/1920、Chromium+WebKit：机器 ID 标题，内容只有一张空卡片。

Playwright MCP 被占用，未能再挂一层实时点击下拉。静态页和 96 张原图足够判断导航与标题。

## 假绿

验收器只查站点地图一一对应，以及死链、控制台、站外请求、页脚、横溢、固定层遮挡。它**不会**查：标题是不是人话、详情页有没有入口。所以基础设施是绿的，医学经理仍过不去。这不是工具算错 16 页，是判定模型覆盖不到可用性。

## 剩余不确定

- 未在实机点开「竞品与开发」下拉和搜索框（MCP 锁）。截图里菜单是中文，结构完整。
- 未逐条回放 zip 里的每步 trace，只核了文件存在、体积和非空 timeline。
- 合成站没有真实疗效表，按合同不因此否决 Task 4.6。

医学经理结论：工具和截图账是平的；**门户还不能交给人用**，先改详情页中文名并在总览/产品总览给出能点进去的入口。
