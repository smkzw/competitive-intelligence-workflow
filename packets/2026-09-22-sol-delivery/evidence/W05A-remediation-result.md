# W05A v6：305px 跨浏览器稳定性小修

日期：2026-09-23  
工程：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`  
当前状态：**v5 独立复审结论仍为 FAIL；v6 已完成实现侧窄屏小修与决定性验证，待新的独立只读复审，不宣布 W05A PASS。**  
运行时请求：`gpt-5.6-sol:medium`；无可核验身份回执，记 **UNVERIFIED**。

## v6 限定边界

- 本轮只修真实45产品在 305/320px 布局宽度下的首屏稳定性：窄屏使用确定性三列阶段网格，压缩筛选摘要的无效换行，并让 section lead 在40px证据按钮下完整排版。
- 没有缩小正文或触控目标：页面 lead/section lead 为16px，阶段文字为14px，最小可见触控高度40px；没有隐藏阶段、字段或 lead，没有产生横向滚动。
- A 运行时的默认筛选状态由“默认显示全部 6 项”收敛为等义的“全部 6 项”，避免128.5px筛选列发生无必要换行；全部筛选能力不变。
- 只改 A 专属作者资产及其镜像、W05A浏览器测试、采集工具和本节证据。未改 B/C、共享 pointer/drawer 协议、来源数据、独立复审或历史证据；未执行 commit/push/delete/cleanup/reset/checkout/clean。
- v6 站点沿用独立复审过的 v5 同一真实45产品静态候选与 `data/report.js`，机械替换本轮 A 作者资产；未修改或补造来源数据。

## 保守 RED 与唯一决定性批

新增 305×568 高负载断言后，当前 v5 实现按预期 RED：

```text
core top=455.33 / height=161.97 / bottom=617.30
1 failed in 2.03s
```

日志：`evidence/W05A-remediation-logs/v6-305-red.log`，SHA-256 `0bdcdf69b4c88532cb734451766c065a1ea23b346c657149284dc8ca4489aba0`。

实现后只运行一次决定性批：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/browser/test_a_w05a_product.py::test_high_load_landscape_exposes_complete_core_unit_without_clipping \
  tests/browser/test_a_w05a_product.py::test_high_load_landscape_mobile_detail_and_complete_table_do_not_scroll_sideways \
  tests/browser/test_a_w05a_product.py::test_same_query_drives_chart_and_folded_table_and_saved_view_restores \
  tests/browser/test_a_portal.py::test_a_safety_details_are_paginated_and_fit_at_1024 \
  tests/browser/test_a_portal.py::test_a_matrix_bubble_and_legend_open_accessible_product_insight_drawer \
  -q --tb=short
```

结果：**`12 passed in 162.02s`**。该批覆盖305/320/390/1024/1440/1920高负载、305/320/390移动完整表、同 query、1024 safety 和稳定产品链接/抽屉回焦。日志 SHA-256：`b3411e5987ff73d7b64cdce2dd23b825b2cd66aff90dbec0ec433e45149dd908`。

## v6 真实浏览器指标

站点：`evidence/W05A-remediation-real-a-v6/`。  
receipt：`evidence/W05A-remediation-browser-v6/browser-receipt.json`，SHA-256 `c15c8a4a9dfafe34b3de33b4578044780ac1299ecebfba5dda8256af307700b6`。

| viewport | 模式 | core bbox `(x,y,w,h)` | 底边/首屏 | 产品/阶段 | 正文/阶段字体 | 最小触控 | 横滚 | console error |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 1920×1080 | matrix | 130,612.0,1660,129.2 | 741.2 / 完整 | 45/6 | 16/14 | 40 | 0 | 0 |
| 1440×900 | matrix | 50,610.4,1340,129.2 | 739.6 / 完整 | 45/6 | 16/14 | 40 | 0 | 0 |
| 1024×1366 | compact | 38,501.4,948,129.2 | 630.5 / 完整 | 45/6 | 16/14 | 40 | 0 | 0 |
| 390×844 | compact | 20,411.5,350,146.2 | 557.6 / 完整 | 45/6 | 16/14 | 40 | 0 | 0 |
| 320×568 | compact | 18,403.0,284,136.2 | 539.2 / 完整 | 45/6 | 16/14 | 40 | 0 | 0 |
| 305×568 | compact | 18,403.0,269,147.6 | 550.5 / 完整 | 45/6 | 16/14 | 40 | 0 | 0 |

注：receipt 的最终精确 y 为 320/305 均 `402.97` 左右（表中四舍五入）；核心单元包含完整 universe 摘要与全部6阶段分布，不是单独数量条。305截图目视确认 section lead 完整、按钮无叠压、三列阶段标签未裁切。

截图位于 `evidence/W05A-remediation-browser-v6/landscape-{1920x1080,1440x900,1024x1366,390x844,320x568,305x568}.png`；1440旅程截图仍记录45/45、同 query、档案锚点、证据与返回均为 true。

## v6 资产绑定

- `portal.css` 作者源/镜像 SHA-256：`32c71f0c32fba3c4cd328f2d8c1f57c81eed743cc0e434c2cface9189d329257`。
- `report-a.js` 作者源/镜像 SHA-256：`740752d9452e955e35e84512d733cadf0e8da47ec50ab93a25d8493ceb471e45`。
- `tests/browser/test_a_w05a_product.py` SHA-256：`4f0b70ea564159f63f8fd0ac41dde35bcf9ddf0e87c12f9db492fd6d15b3b749`。
- `tools/capture_w05a_browser.py` SHA-256：`6f0bdb9abc796efe58dd90ecfe1f2b82c056c65b993e0439b709ae573a81c35e`。

## 当前验收边界

- `W05A-independent-rereview-v5.md` 的 v5 verdict 保持 **FAIL**，未被修改或追认。
- v6 仅关闭该报告指出的 305/320 跨浏览器首屏稳定性问题；当前状态是**待独立视觉/产品复审**。
- 真实逐事实来源闭合、共享 pointer/drawer、两个既有合同差异及全 gate/24门户/B/C/三宿主/RC 均不在本轮范围，状态未改变。

---

# W05A 独立复审 FAIL 连续返修结果（v5 历史）

日期：2026-09-23  
工程：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`  
当前状态：**前端硬门与可归因回归已完成实现侧返修，待新的独立视觉/产品复审；不宣布 W05A 最终 PASS。**  
运行时请求：`gpt-5.6-sol:medium`；无可核验身份回执，记 **UNVERIFIED**。

## 1. 本轮边界

- 只改 A/W05A 作者源、A 模板、对应共享镜像、W05A 测试与采集工具，以及本轮证据、`W05A-result.md`、`STATUS.md`。
- 未改 B/C 模板或视觉，未修改独立复审原文、历史冻结验收、无关测试；未执行 commit/push/reset/checkout/clean/delete。
- 保留所有既有脏树、W00–W04 证据和本轮 v1–v4 中间失败现场；v5 是当前实现侧候选。

## 2. 响应式 landscape 返修

1. `>=1200px` 使用完整横向靶点×阶段矩阵；两个核心筛选并排为双列工具区，矩阵不再因纵向堆叠而被推离首屏。
2. `<1200px` 改为完整阶段分布摘要 + 靶点折叠分组。1024 不再渲染按最高列等高的空白矩阵；每个靶点展开后按阶段单列呈现全部产品。
3. 390/320 的核心阶段分布直接覆盖当前完整 universe，真实 45 产品的 6 个阶段全部显示；靶点分组逐个展开后仍可进入原产品洞察和三层下钻。
4. 阶段摘要使用 14px 字号；按钮/summary 最小 40px。密度提升没有依赖缩小正文、缩小触控、丢字段或页面横向滚动。
5. landscape 完整表在 640px 以下切换为卡片/定义列表视图，产品、靶点、技术类型、最高阶段、地域、开发状态 6 字段全部显示；宽屏仍保留表格。同一筛选继续同时驱动图与两种完整表表达。

## 3. 当前可归因回归

### 3.1 产品档案链接

`test_a_matrix_bubble_and_legend_open_accessible_product_insight_drawer` 在本轮聚焦 RED、完整相关批和最终精确闭合中均通过。稳定 `href` 未再直接追加返回参数；点击时由 A 运行时生成有状态导航。

### 3.2 1024 安全性详情表

- 为 10 列设置显式比例，维度列实际为 **104.27px**。
- 试验全名、登记组名、安全语义与依据使用 40px 键盘可操作展开按钮；标准化产品、组别、维度、事件、值、人数和观察窗仍直接显示，完整原字段可展开访问。
- 最终实际浏览器探针：第 2 页首行 **99.38px**，低于 120px；容器 `scrollWidth/clientWidth=948/948`，页面 overflow=0。
- 最终精确回归中该 nodeid 通过。

### 3.3 6 项共享点击/焦点低置信项

聚焦 RED 与规定相关批均复现以下 6 项：

- `test_pointer_bar_opens_same_row_evidence[chromium]`
- `test_pointer_bar_opens_same_row_evidence[webkit]`
- `test_pointer_bar_escape_returns_focus_to_exact_svg_mark[chromium]`
- `test_pointer_bar_escape_returns_focus_to_exact_svg_mark[webkit]`
- `test_pointer_click_highlights_table_row[chromium]`
- `test_pointer_click_highlights_table_row[webkit]`

它们运行的是通用 `charts.js`/`evidence-drawer.js` fixture 页面，没有加载 A landscape renderer；失败分别为通用抽屉保持 hidden、pointer 没有选中表格行。W05A 改动只涉及 A 专属选择器、A JS 和 A 模板，没有证据显示当前失败由 W05A 引入。按用户边界，本轮不越界修改共享交互协议或这些无关测试；它们保留为既有共享基线失败，不计作已关闭。

## 4. 五 viewport 真实 45 产品证据

当前站点：`evidence/W05A-remediation-real-a-v5/`。  
当前 receipt：`evidence/W05A-remediation-browser-v5/browser-receipt.json`，SHA-256 `b347c19b96927623807df662e88351473f3a3236d38ada1d7c02e624ca111fe7`。

| viewport | 模式 | 主内容宽/占比 | panel宽 | padding/gap | core bbox (x,y,w,h) | core完整可见 | compact/matrix bbox (x,y,w,h) | 首屏明细可见高 | 图总高 | overflow | 最小触控 | console error |
|---|---|---:|---:|---:|---|---|---|---:|---:|---:|---:|---:|
| 1920×1080 | matrix | 1760 / 91.7% | 1712 | 24/20 | 130,612,1660,129.2 | 是 | 130,741.2,1660,1286.8 | 338.8 | 1418.0 | 0 | 40 | 0 |
| 1440×900 | matrix | 1440 / 100% | 1392 | 24/20 | 50,610.4,1340,129.2 | 是 | 50,739.6,1340,1403.6 | 160.4 | 1534.8 | 0 | 40 | 0 |
| 1024×1366 | compact | 1024 / 100% | 988 | 18/16 | 38,501.4,948,129.2 | 是 | 38,630.5,948,355 | 355.0 | 486.2 | 0 | 40 | 0 |
| 390×844 | compact | 390 / 100% | 374 | 10/10 | 20,406.2,350,146.2 | 是 | 20,552.4,350,343 | 291.6 | 491.2 | 0 | 40 | 0 |
| 320×568 | compact | 320 / 100% | 304 | 10/10 | 20,406.2,280,136.2 | 是 | 20,542.4,280,343 | 25.6 | 481.2 | 0 | 40 | 0 |

五档 core 都是“完整 universe 摘要 + 全阶段分布”，不是单独数量条；均统计 45 产品、6 阶段。320 的 core 底边为 **542.4px**，首屏内完整，同时开始露出下一层靶点分组。1440/1920 首屏均已进入完整横向矩阵实质内容。

浏览器截图：

- `evidence/W05A-remediation-browser-v5/landscape-1920x1080.png`
- `evidence/W05A-remediation-browser-v5/landscape-1440x900.png`
- `evidence/W05A-remediation-browser-v5/landscape-1024x1366.png`
- `evidence/W05A-remediation-browser-v5/landscape-390x844.png`
- `evidence/W05A-remediation-browser-v5/landscape-320x568.png`
- `evidence/W05A-remediation-browser-v5/journey-return-1440x900.png`

真实旅程仍为 45/45 图表集合相同，完成“宇宙→机制→产品→地域→试验→结果→证据→返回”；五个档案锚点、证据抽屉、返回后洞察恢复均为 true。

## 5. 来源 P1-02

确定性扫描证据：`evidence/W05A-remediation-logs/source-closure-audit.json`，SHA-256 `6b52ea5132c041e2daae37c488f047e21945c653007988db686d4b57bd6f49d9`。

- 搜索英文工程内 `runs/**/reports/A/**/data/report.js` 与 packet/evidence 对应 A 路径，共解析 **152** 份 A payload。
- 同时满足公共来源非空、且每条疗效/安全记录都具有 `source_field_path` 和 `source_text` 的候选：**0**。
- 任一候选中逐事实同时具备 locator+原文的最大行数：**1**；这只是 W04 单行用户修订工件，不能代表 45 产品真实 A 来源闭包。
- 公共来源清单最多 10 条，但其限制文字明确为报告级来源，不能替代逐事实支持关系。

因此 P1-02 当前状态为 **未闭合 / W07 依赖**。本轮没有伪造来源、没有修改历史 payload 补 locator，也没有把报告级来源写成逐事实 PASS。现有来源完备 fixture 的前端来源区、公共来源抽屉和用户修订/原来源分层仍在规定相关批中通过。

## 6. 测试与日志

### 集中 RED

命令覆盖 W05A 新高负载、两个当前回归和 6 项低置信共享点击/焦点。结果：

```text
14 failed, 10 passed in 291.86s
```

日志：`evidence/W05A-remediation-logs/focused-red.log`，SHA-256 `f191c8df626f8fdcb10a0481482f0ed661dc933e342264bba81d262a08c92477`。

### 唯一一次规定 W05A/A/W04 相关批

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/reports/a tests/browser/test_a_w05a_product.py tests/browser/test_a_portal.py tests/browser/test_filter_state.py tests/browser/test_a_public_source_drawer.py tests/browser/test_evidence_drawer.py::test_pointer_bar_opens_same_row_evidence tests/browser/test_evidence_drawer.py::test_pointer_bar_escape_returns_focus_to_exact_svg_mark tests/browser/test_chart_table_sync.py::test_pointer_click_highlights_table_row tests/unit/test_a_observation_numeric_contract.py tests/unit/test_report_a_safety_projection.py tests/contract/test_page_catalogs.py tests/integration/reports/test_a_report_portal.py tests/integration/test_w04_user_fact_edit.py tests/integration/test_a_public_provenance.py tests/integration/test_report_a_render_transaction.py -q --tb=short
```

结果：

```text
10 failed, 355 passed in 614.98s
```

日志：`evidence/W05A-remediation-logs/final-related-batch.log`，SHA-256 `d0faf97581e4242fbf0af663e0061186054159497ab40aa7fc11ed9aab22c1d8`。

10 项中：6 项为上述共享 pointer/evidence-drawer 基线；2 项为混合批已分诊的首页疗效全 DOM/旧安全 heatmap 契约差异；2 项为本轮 320 七阶段与安全表 selector/行高，随后同批修复。

### 可归因项最终精确闭合

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider 'tests/browser/test_a_w05a_product.py::test_a_responsive_space_uses_canvas_and_keeps_a_complete_first_reading_unit[320-568-0.98-12]' tests/browser/test_a_portal.py::test_a_safety_details_are_paginated_and_fit_at_1024 tests/browser/test_a_portal.py::test_a_matrix_bubble_and_legend_open_accessible_product_insight_drawer -q --tb=short
```

结果：

```text
3 passed in 156.26s
```

日志：`evidence/W05A-remediation-logs/final-attributable-green.log`，SHA-256 `be98f2fc974b219f5d34a671c71e6cc4c0a27a0f6c3a9e846b5f58f848ded77a`。

实际浏览器补充探针：`post-batch-browser-probe-v2.json`，记录 320 七阶段核心单元和 1024 安全表几何/字段展开；SHA-256 `3d3e59c87268eff7fd6234810536ab0e424b412de11c87c8284ae9b284f98b5e`。

### 静态质量

- Ruff：通过。
- strict mypy（采集工具）：通过。
- `node --check report-a.js`：通过。
- 作者源/镜像 `portal.css`、`report-a.js`：逐字节一致。
- 限定 `git diff --check`：通过。

日志：`evidence/W05A-remediation-logs/static-quality.log`，SHA-256 `c6b2a60c7e21a17b7465b1579abcc9c239f9bef9424e12b3b8b87545619292a3`。

## 7. 当前未闭合项

1. P1-02 真实 A 逐事实来源闭包：仓库无合格输入，依赖 W07；明确未 PASS。
2. 规定相关批仍有 8 项非本轮可归因失败：6 项共享 pointer/evidence-drawer，2 项旧 A 首页疗效/安全 heatmap 合同差异。原始日志保留，未通过改测试掩盖。
3. 新实现尚待新的独立视觉/产品复审；本实现者不宣布最终 PASS。
4. 全 gate、24 门户、B/C、三宿主、WebKit 全站、缩放/屏幕阅读器、RC 均未验。
