# W03 第三次独立只读复审

日期：2026-09-22  
模式：`MODE=CONFERENCE`，从当前字节独立复审；未修改产品、测试、`STATUS` 或历史审阅。  
请求模型/effort：`gpt-5.6-sol:medium`。当前会话没有可核验的运行时 model/effort 回执，模型状态：**UNVERIFIED**。  
工程根：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`。未接触旧中文工程。  
当前 HEAD：`2df24bb441e555f20b233ad2011b4ffd3610655b`；工作树存在既有大量修改/未跟踪材料，本复审全部保留。

## 总体结论

**总体：FAIL。P0=0；P1=0；P2=1；P3=0。**

二审的四个 P1 与 HTML-PPT 单先例兼容缺口已从当前生产代码和直接重放关闭；F01/R01 继续通过。唯一未关闭项是浏览器冻结证据：固定 CAS、生成源码、C package、`data/report.js` 与 sitemap 均可从当前字节重建并得到相同哈希，但 manifest 中两张截图不是该 PNH 冻结站点的画面，生成脚本也没有在同一构建中启动浏览器或产生截图。因此第 6 项为 **FAIL（P2）**，W03 冻结浏览器证据不能整体接受。

本结论仅针对 W03 工程风险合同。即使修复该 P2，也不等于全部 24 门户、正式医学/统计判断、产品验收或 RC 接受。

## 决定性重放

使用工程现有 `.venv`，禁用 pytest cache 与 Python bytecode，定向执行 B typed 语义、两类矩阵伪造、Fresh C 内容与 `run_service` legacy 自报、固定 CAS 全链、单先例、HTML-PPT、冻结 manifest、F01 和 R01 共 12 个节点：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider <12 个明确 node id>
....... [100%]
12 passed in 29.01s
```

首次用系统 Python 的两次尝试均停在收集阶段（先缺项目导入路径，后缺 `jsonschema`），未进入测试体，不计产品结果；定位到当前工程 `.venv` 后才得到上述有效回执。

另以临时目录从固定 CAS 独立重建 A→C→C portal，观测：

```text
products: 45 | trials: 140
efficacy rows: 3895 | safety rows: 519
C package: trials 6 | products 5 | observations 258 | paths 4
package_matches True
report_js_matches True
sitemap_matches True
```

## 逐项判定

### 1. B `term_key` typed 语义贯穿 builder→`ReportBPortalData`→筛选/表

**PASS。**

- 生产 builder 只接受 `SAFETY_CONCEPTS` 受控键，并把 `term_key`、polarity、grade、seriousness、TEAE、relatedness、parent/children、count basis 原样投影：`packets/2026-09-11-pnh-vertical/build_pnh_b_audit.py:51-88`。
- B 门户语义投影优先读取并校验 typed `term_key`，以键本身作为 `clinical_concept`：`src/ci_workflow/renderers/portal/report_b.py:1026-1103`。
- 直接重放 `test_b_safety_term_key_survives_builder_payload_filter_and_table` 通过；反例 `absence_sae + negative_presence` 经 builder、JSON 模型、筛选记录和安全表仍为 `absence_sae`，没有降级为 generic。

### 2. B JSON Mapping 伪造与 canonical raw 重算

**PASS。**

- `TypedNumericProjection` 禁止额外字段，并从 raw value/unit、kind、n/N、direction、window、estimand、size basis 重新调用 `project_numeric`；伪造 plot value/unit/facet 会失败：`src/ci_workflow/renderers/portal/report_b.py:1265-1301`。
- 治疗/对照的 kind、unit、direction、window、estimand、facet 必须一致；安全轴必须为参与者比例 `%`；size 必须是正整数“人”且使用批准的 size basis：同文件 `:1304-1345`。
- 生产 builder 输出 `canonical_numeric_projection_v1` 的 raw 与 canonical 字段：`packets/2026-09-11-pnh-vertical/build_pnh_b_audit.py:1248-1342`。
- 两个 JSON 边界反例均按预期被拒：治疗 `g/L` 对控制 `%`；size 被伪造为 `%` 且清空 basis。参数化节点 2/2 通过。

### 3. Fresh C 普通内容与 `run_service` 不能自报 legacy 绕过 `instance_v1`

**PASS。**

- 新内容字段是 `Literal["instance_v1"]`，不存在调用者可选的 legacy 值：`src/ci_workflow/application/fresh_c_research_package.py:184-203`。
- 内容关闭时无 legacy 分支，统一执行逐 outcome 实例校验：同文件 `:248-309`。
- 普通 `FreshCResearchContent` 与实际 `run_service` 两个 `legacy_readonly_v0` 自报反例均失败关闭；对应两个测试节点通过。
- 全仓定向检索显示 `legacy_readonly_v0` 只剩两条拒绝测试，不存在生产可达开关。

### 4. 固定真实 CAS A main→B/C main、W01 ingest 与 manifest-only restore

**PASS。**

- 闭包测试实际执行 A `main()`、B `main()`、C `main()`，不是手工拼一行：`tests/contract/test_w03_production_consumer_closure.py:216-246`。
- A 生成 3895 条疗效和 519 条安全行，消费行均携带非空精确 `source_field_path/source_text`：同文件 `:230-237`；本次真实执行得到相同计数。
- 对 B 的全部 package facts 和 C 的全部 derived facts 分别调用生产 W01 `ingest_research_evidence`，再把导出的 manifest 恢复到空目录：同文件 `:248-276`。
- 该完整节点在本次 12 节点重放中通过；C 为 6 个试验、258 条 observations。没有使用实现者报告中的 “93 passed” 代替本次执行。

### 5. C 单先例 HTML-PPT 基础兼容且不改变 HTML 产品门

**PASS。**

- HTML-PPT 锁定合同已设 `C_min_design_paths=1`，第二路径仅为兼容位且不是 render gate：`docs/acceptance/runs/8.5/projection-contract.md:129-130,242-250`。
- 投影文案明确“单条完整先例可用”，不再写“至少两条”：`src/ci_workflow/renderers/html_ppt/projections/c_pages.py:237-253,267-281`。
- 测试锁定单先例门与兼容位：`tests/html_ppt/test_projection_contract.py:192-221`；Fresh C 的单 evidence-backed precedent 节点也通过。
- `C_min_design_paths` 只出现在 HTML-PPT 合同和其测试中，没有进入 `report_c.py` 或 Fresh C/HTML portal 生产门；本次未发现通过删减 HTML 门户页面或缩小 HTML coverage 来过关。

### 6. 浏览器 freeze manifest 对 report.js、CAS、生成源码、截图/站点的绑定

**FAIL（P2）。**

通过部分：

- manifest 所列两份固定 CAS、四份当前生成源码、保留的 `data/report.js` 均存在且哈希匹配：`packets/2026-09-22-sol-delivery/evidence/W03-browser-freeze/site.manifest.json:6-39`。
- 从当前 CAS 和源码在临时目录重建后，C package、`report.js`、sitemap 三个哈希分别与 manifest 完全相同。故“当前数据字节可重建”成立。

失败部分：

- manifest 两张截图画面显示的是特应性皮炎合成试验 `NCT00000001`–`NCT00000004`、阿尔法/贝塔单抗；冻结 `report.js` 实际只含 PNH 试验 `NCT02591862`、`NCT02605993`、`NCT03181633`、`NCT04170023`、`NCT04469465`、`NCT05886244`。两者不是同一站点数据。
- 生成脚本只在固定路径发现既有 PNG 后抄入其文件哈希，见 `tools/build_w03_browser_freeze.py:72-102`；脚本没有 Playwright/Chromium/WebKit 调用，也不生成截图。当前两张 PNG 的修改时间为 20:43，而 manifest/`report.js` 为 21:39，也符合“先有无关截图，后被列入 manifest”的观测。
- manifest 仅保存 sitemap 哈希，没有保留 sitemap；没有逐站点文件清单/哈希。当前测试 `tests/contract/test_w03_production_consumer_closure.py:287-302` 只证明“manifest 中列出的任意文件自身哈希匹配”，不能证明截图来自所列 `report.js` 或该次站点构建。

直接反例命令/观测：

```text
冻结 report.js 唯一 NCT：
NCT02591862 NCT02605993 NCT03181633 NCT04170023 NCT04469465 NCT05886244

截图直接视觉检查：
NCT00000001 NCT00000002 NCT00000003 NCT00000004

AST 检查 build_w03_browser_freeze.py：browser_or_screenshot_call False
retained_sitemap_exists False
manifest_site_file_hashes False
```

最小修复：让 freeze builder 在同一个临时站点构建中启动浏览器、访问固定 route/viewport 并当场生成截图；manifest 记录浏览器、route、viewport、截图和对应 DOM/可访问性快照或页面数据身份。至少保留 sitemap 并列出全部实际站点文件哈希（含模板/共享资产消费者）；测试须断言截图页面的试验身份来自保留的 `report.js`，而不是只校验 PNG 自身哈希。修复后重建一次 freeze 并仅复跑本项即可。

### 7. F01 / R01 保持

**PASS。**

- F01：生产 denominator lookup 要求完整 study/module/group/measure object/population/window/source version；只有同模块同组或带 mapping id 的 `source_declared/audited_mapping` 可建立关系，标题只能否决不能创建关系；不完整身份直接 `None`：`src/ci_workflow/reports/b/safety_denominator_crosswalk.py:90-152`。同 N、缺身份、跨期负例本次通过。
- R01：intervention 只按显式 `armGroupLabels` 绑定；缺 label 或未知 label 产生 `blocking=True`，不回退 arm1：`src/ci_workflow/reports/c/arm_interventions.py:7-42`。未绑定 intervention 阻断节点本次通过。

## 接受边界

- **W03 工程风险合同：FAIL**，仅因 P2 浏览器截图/站点冻结绑定不真实。
- **已确认的局部工程通过：** B typed 语义、B canonical 数值边界、Fresh C instance 门、真实固定 CAS A→B/C 与 W01 restore、C 单先例兼容、F01、R01。
- **仍为 UNVERIFIED：** 请求模型 `gpt-5.6-sol:medium` 的运行时身份；全 gate；24 门户；全 viewport/全页 Chromium/WebKit；真实 PNH v107；正式医学、统计、产品和 RC 接受。

本复审未派子代理，未提交、推送、清理或修改任何产品/测试/状态/历史报告；唯一写入为本报告。
