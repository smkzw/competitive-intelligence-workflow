上一轮两条 P1 声称已修。我先读复核清单，再独立跑全站命令并打开真实页面核对。产品总览已有中文链接。全站命令开跑，同时点开页面和搜索核对标题与可达性。# Task 4.6 定点复核

**Verdict: PASS**

上一轮两条 P1（详情页机器标题、产品/试验页进不去）在本版已对上画面。验收器 16/96/2 账平；拿走 `product-01` 页会在开浏览器、出截图之前就被站点地图否决。

## 定点项

| 项 | 结果 | 证据 |
| --- | --- | --- |
| 产品总览露出 3 条中文产品链 | **PASS** | 实点：环柏单抗 / 洛普利单抗 / 贝妥昔单抗 → `products/product-0{1,2,3}.html`。图：`reviewer-grok-r2/screenshots/a_product-overview__chromium__1280x800.png` |
| 临床开发组合露出 2 条中文试验链 | **PASS** | 实点：关键注册研究、长期扩展研究。图：`a_clinical-portfolio__webkit__1440x900.png` |
| 链接落到中文 H1 | **PASS** | 点「贝妥昔单抗」→ H1「贝妥昔单抗」；点「关键注册研究」→ H1「关键注册研究」。图：`a_products_product-01__chromium__1280x800.png`（环柏单抗）、`a_trials_trial-02__chromium__1920x1080.png`（长期扩展研究） |
| 根页搜索到产品 | **PASS** | `overview.html` 搜「环柏单抗」→ 一条结果，点进 `products/product-01.html`，H1=环柏单抗。Chromium 1280×800 |
| 产品详情页搜索到试验 | **PASS** | `products/product-01.html` 搜「长期扩展研究」→ `../trials/trial-02.html`，H1=长期扩展研究 |
| 可见标题无 `product-01`/`trial-02` | **PASS** | 16 个 HTML 的 `<h1>`/`<title>` 均无该字样。可见标题为中文药名/研究名 |
| 孤儿页会在截图前失败 | **PASS** | 只读调用 `verify_sitemap_one_to_one`：现网 16=16 通过；从实际路由去掉 `/a/products/product-01` 后 `ok=False`，`missing_product_detail`，文案「缺少产品详情页：/a/products/product-01」。此步在 `verify_portal.py` 启动浏览器/`_run_browser_acceptance` 之前 |

## P0 / P1 / P2

**P0** 无。  
**P1** 无（上轮两条不再复现）。  
**P2** 搜索框 1280 仍截成「搜索页面或关键词..」（`a_product-overview__chromium__1280x800.png`）。Logo 仍进临床开发组合而非总览。不挡本次定点验收。

## 命令与对账

```text
uv run python tools/verify_portal.py --report A --project .artifacts/task46-visual \
  --version v-fixture-001 --browser chromium --browser webkit --all-routes \
  --output-dir .artifacts/task46-visual/reviewer-grok-r2
```

- 退出 **0**，约 41s。`A_PORTAL_OK routes=16 browsers=2`
- `reviewer-grok-r2/report.json`：`ok: true`，16 路由，96 check 全绿  
  `site_digest=cf0e02cdf391dff82d3e4bf6da89281fa9f4396516de5c59fcffb441780047ba`（新站点，与旧跑 `a91d7e77…` 不同）  
  `run_digest=8dc85bb8f00fa18b933a5d11…`
- 截图 96，文件名齐，像素 32×1280×800 + 32×1440×900 + 32×1920×1080，96 个不同哈希
- Trace：`trace__chromium__8dc85bb8f00f.zip`（2.5MB / 195 项）、`trace__webkit__8dc85bb8f00f.zip`（3.1MB / 210 项）

未改源码、清单或旧 verification 目录。

## 剩余不确定

- Playwright MCP 仍占用，搜索与点击用独立 Chromium 完成，未再走 MCP。
- 未逐帧回放 zip timeline。
- 详情页仍是夹具短文，按合同不因 Phase 5–7 正文未齐否决。
