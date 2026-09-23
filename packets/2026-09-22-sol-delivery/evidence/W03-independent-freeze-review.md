# W03 最终 P2 浏览器 freeze 独立只读核验

日期：2026-09-22  
模式：`MODE=CONFERENCE`；仅核验第三次独立复审遗留的最后一个 P2，不复审已通过的科学 P1。  
工程根：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`；未接触旧中文工程根。  
当前 HEAD：`2df24bb441e555f20b233ad2011b4ffd3610655b`；工作树已有大量修改和未跟踪材料，本次均予保留。  
请求模型/effort：`gpt-5.6-sol:medium`；当前会话没有可核验的运行时 model/effort 回执，模型状态：**UNVERIFIED**。  
执行方式：独立只读核验；未派子代理，未提交、清理或修改产品、测试、历史审阅及冻结证据。唯一仓库写入为本报告。

## 结论

**PASS。P0=0；P1=0；P2=0；P3=0。**

第三次独立复审在 `W03-independent-rereview-2.md:86-115` 指出的唯一 P2 已由当前 freeze v2 证据关闭：固定 CAS 与 manifest 所列当前源码可重建出完全相同的 C package、`report.js`、sitemap 和两页 HTML；两条浏览器 journey 的载荷试验集合、现场 DOM 集合和截图均对应同一组 6 个真实 PNH NCT；route、console、页面、journey、截图与 manifest 哈希均可核；旧合成四项截图仍保留但未被当前 manifest 引用；对应测试保留原有哈希检查并增加了试验集合、route、DOM、console、页面与截图绑定检查，没有通过删除检查绕过。

本结论只接受 **W03 最后一个 P2 的工程风险证据**。它不是正式医学或统计判断，不是产品验收，也不是 RC 接受；科学 P1 本次未复审。

## 核验结果

### 1. 固定 CAS/当前源码可重建当前冻结字节 — PASS

- freeze v2 manifest 绑定两份固定 CAS、11 个当前源码、保留的 `report.js`/sitemap、两页、两份 journey 与两张截图：`packets/2026-09-22-sol-delivery/evidence/W03-browser-freeze/site.manifest.json:2-116`。
- 逐项重算 manifest 的 19 个文件绑定（2 CAS、11 source、2 journey、2 screenshot、retained report、retained sitemap），观测为 `binding_count 19`、`all_hashes_match True`。
- 在 `/tmp` 独立临时目录中导入当前 `tools/build_w03_browser_freeze.py`，把其 evidence 输出重定向到临时目录后，从固定 CAS 执行 A main → C main → `render_report_c_site`。有效重放观测：

```text
products: 45 | trials: 140
efficacy rows: 3895 | safety rows: 519
C package: trials 6 | products 5 | observations 258 | paths 4
rebuilt_package_match True
rebuilt_report_match True
rebuilt_sitemap_match True
page endpoint-timepoint-matrix ... match True
page treatment-arms ... match True
```

- 重建 SHA-256 与 manifest 完全一致：C package `2c6381e93c68dd80c40636b0a3739ba89eafdcc8a5ae7f3b85dd9b142f76a310`；`report.js` `fff71397b08d24b8ed3ef21f9736298ca16b9814ee88df143e4f12af21b1882d`；sitemap `001ca757ea8f827e11af64ca1ab097422a8938cc10a1443237152cba25013d01`；两页分别为 `823d3d400298e4fc4fd269b584275fef77554d6b899bf736f5845245e183eaee` 与 `ab502f8a645f6da03906d2d49773511b203ce2983b4319766ba27d22dcee8b93`。
- 首次临时重建调用因复核脚本未先创建临时父目录，在进入产品 builder 前以 `FileNotFoundError` 终止；修正临时前置目录后上述有效重放通过。首次调用不计产品结果，且未触及仓库文件。
- 生成链和绑定逻辑见 `tools/build_w03_browser_freeze.py:38-65,67-141`；`--site-root` 空目录保护见同文件 `:144-163`。

### 2. 两条 journey、report.js 与现场 DOM 的 6 个 PNH NCT 一致 — PASS

- `report.js` 的 indication 为“阵发性睡眠性血红蛋白尿症”，6 个 trial 标题均明确为 PNH 研究；唯一试验集合为：

```text
NCT02591862
NCT02605993
NCT03181633
NCT04170023
NCT04469465
NCT05886244
```

- endpoint/timepoint journey 的 payload 与 DOM 集合均为上述 6 项，断言均为 true：`packets/2026-09-22-sol-delivery/evidence/W03-browser-freeze/journeys/endpoint-timepoint-matrix.json:10-39`。
- treatment-arm journey 的 payload 与 DOM 集合均为上述 6 项，断言均为 true：`packets/2026-09-22-sol-delivery/evidence/W03-browser-freeze/journeys/treatment-arms.json:10-39`。
- 为避免只信任既有 JSON 回执，另从临时重建站点启动仅绑定 `127.0.0.1:8876` 的 HTTP 服务，以 Playwright CLI/Chromium、`1720×1100` 分别打开两页，现场 fetch `data/report.js` 并从 `document.body.innerText` 提取 NCT。两页均观测：`payload=[6 个上述 NCT]`、`dom=[6 个上述 NCT]`，两集合完全相等；浏览器会话和临时服务随后正常关闭。
- 第一次浏览器读取误把页面即时变量假定为 `window.REPORT_C`，得到 `undefined`；随后按实际页面结构现场 fetch `data/report.js` 后有效复跑通过。该复核脚本假设错误不计产品结果。

### 3. sitemap、route、console、页面与截图哈希 — PASS

- 保留 sitemap 含 18 条 C route，其中两条目标 route 分别映射到 `endpoint-timepoint-matrix.html` 和 `treatment-arms.html`：`packets/2026-09-22-sol-delivery/evidence/W03-browser-freeze/data/sitemap.json:1`。
- 独立解析结果：两份 journey 的 `catalog_route` 均与 manifest page route 一致，sitemap path 均与 journey `served_path` 一致；两页 `console_clean True`。既有回执中的 console 也均为 `errors=[]`、`warnings=[]`：两份 journey 各 `:37-39`。
- endpoint/timepoint 截图 SHA-256 为 `9c945099649d8a6b8347a4b88e4fcfa7e81cf589056f0750c55a3e5137894188`；arm 截图为 `67652ce43ba8b57ce3a411092361b4098eba2b418644a9b987d0be4b5144bd54`。manifest、journey 与实际文件三方一致：manifest `:93-115`，journey 各 `:41-44`。
- 直接视觉检查两张实际 PNG：页面标题分别为“终点、定义与时间点”和“分组、干预与对照”，画面列头/来源可见上述 6 个 PNH NCT；未见旧 `NCT00000001`–`NCT00000004` 或阿尔法/贝塔单抗合成内容。

### 4. 旧合成截图未被当前 manifest 引用 — PASS

- 旧文件 `output/playwright/W03-repair-C-endpoint-instances.png` 与 `output/playwright/W03-repair-C-arm-relations.png` 仍存在，未被删除。
- 独立集合比较观测：`old_screenshot_count 2`、`old_refs_intersection []`。当前 manifest 只引用 `W03-browser-freeze-C-endpoint-timepoint.png` 与 `W03-browser-freeze-C-arm-relations.png`：`site.manifest.json:105-115`。
- 对应测试还显式拒绝 manifest 中出现 `W03-repair-C-`：`tests/contract/test_w03_production_consumer_closure.py:317-325`。

### 5. 未以删除检查绕过 — PASS（以可核现有/前次审阅证据为限）

- 第三次复审记录的旧测试范围仅能证明 manifest 所列文件自身哈希；当前测试仍保留并扩大该检查：保留 `report.js`/sitemap 哈希和全部 CAS/source/journey/screenshot 文件哈希检查：`tests/contract/test_w03_production_consumer_closure.py:287-315`。
- 当前测试新增且实际执行：schema v2、6-trial 集合、两 journey/两 screenshot 数量、旧截图排除、两条 route、runner、report.js 哈希、payload/DOM 集合、三个布尔断言、console、page hash、截图文件及 manifest 三方绑定：同文件 `:317-343`。
- 当前相关工具/测试/packet 为未跟踪材料，Git 无法提供提交基线的逐行增删证明；因此本项不声称存在可审计提交历史。依据第三次审阅的旧检查描述与当前完整定义，旧哈希检查仍在且检查面增加，未见通过删除相关检查取得通过的证据。

## 定向测试与命令观测

执行：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider \
  tests/contract/test_w03_production_consumer_closure.py::test_w03_browser_freeze_rebinds_report_data_sources_and_screenshots
```

结果：**`1 passed in 0.30s`，exit 0**。

另完成的只读决定性检查：

- manifest 19 个当前文件绑定逐项 SHA-256：全部匹配；
- 固定 CAS/当前源码临时重建：package、report.js、sitemap、两页 HTML 全部匹配；
- 两页独立 Chromium 现场观测：report.js 与 DOM 各为相同 6 个 PNH NCT，控制台各 `0 errors / 0 warnings`；
- 旧截图集合与 manifest 当前截图引用集合：交集为空；
- 两张当前截图直接视觉核验：与 PNH 页面及 6 个 NCT 一致。

## 模型状态与接受边界

- 审阅请求为 `gpt-5.6-sol:medium`，但当前运行环境未提供可核验的 model/effort 运行时回执：**UNVERIFIED**。本报告不把名称请求或文本自述当作运行时身份凭证。
- **已接受：** W03 第三次复审遗留的最后一个 P2 浏览器 freeze 工程证据。
- **未复审：** 已通过的科学 P1/F01–F06/R01。
- **不由本报告接受：** 正式医学/统计判断、完整产品验收、24 门户、全 viewport/全浏览器矩阵、真实 PNH v107、RC 或发布决定。
