# W05A v6 冻结候选独立复审

日期：2026-09-23  
唯一复审工程：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`  
角色：独立只读复审者  
请求运行时：`gpt-5.6-sol:medium`  
运行时身份：**UNVERIFIED**（本会话没有可核验的模型/effort 身份回执；未替换模型）

## 1. 最终裁决

| 裁决层 | 结论 | 说明 |
|---|---|---|
| v6 前端响应式硬门 | **PASS** | 305/320/390/1024/1440/1920 六档均通过；305 在独立 Chrome 保留 15px 垂直滚动条、实际内容宽仅 290px 的更苛刻条件下，完整核心单元底边仍为 562.6px，小于 568px。移动完整表为 45 条、每条 6 字段，无页面或局部横向滚动。 |
| v6 前端返修接受 | **PASS（限前端 W05A 返修范围）** | 1024 safety 详情几何、稳定产品链接、抽屉/回焦、同 query、45/45 守恒和三层旅程均有当前测试或浏览器证据。该结论不等于科学来源或全平台验收通过。 |
| W05A 正式整体门 | **FAIL** | P1-02 真实逐事实来源闭合仍为 0/4412，明确依赖 W07；来源 fixture 和报告级公共来源清单不得替代真实逐事实 PASS。另有 6 个共享交互失败和 2 个历史 A 合同差异在当前树上仍实际失败。 |
| RC / 发布 | **禁止宣布** | 本复审未覆盖全 gate、24 门户、B/C、三宿主或正式发布批准；存在明确未过门。 |

独立判断：v5 中唯一的 v6 定向阻断项——305/320 跨浏览器首屏稳定性——已经关闭。因此可以接受“**前端 W05A 实现/返修通过**”；但不能把它改写为“W05A 整体 PASS”。正式表述应为：**前端 W05A 实现可接受，真实来源验收明确依赖 W07，正式 W05A 总门未过。**

## 2. 复审范围与边界

本次完整阅读并交叉核对了：

- `PRD.md`、`DESIGN.md`、`PLAN.md`、`EXECUTION_RULES.md`、`ACCEPTANCE.md`、`STATUS.md`；
- `work_packages/W05A.md`；
- `evidence/W05A-independent-review.md`、`W05A-independent-rereview-v5.md`、`W05A-mixed-failure-triage.md`、`W05A-remediation-result.md`；
- `PAUSE_HANDOFF_20260923_065547.md`；
- `evidence/W05A-remediation-logs/*`，重点包括 `final-related-batch.log`、`final-attributable-green.log`、`source-closure-audit.json`、`v6-305-red.log`、`v6-decisive-batch.log`；
- v6 真实站点、`browser-receipt.json`、六档截图和 1440 旅程截图；
- 当前作者源、v6 资产、W05A 测试与采集工具。

未修改产品代码、测试、状态文件或历史证据；未执行测试修复、commit、push、reset、checkout、clean 或 delete。本报告是唯一写入文件。

## 3. 冻结资产和证据绑定

独立 SHA-256 复算结果：

| 对象 | SHA-256 | 绑定判断 |
|---|---|---|
| 作者源 `src/ci_workflow/renderers/portal/assets/portal.css` | `32c71f0c32fba3c4cd328f2d8c1f57c81eed743cc0e434c2cface9189d329257` | 与 v6 站点资产逐字节一致 |
| v6 `assets/portal.css` | `32c71f0c32fba3c4cd328f2d8c1f57c81eed743cc0e434c2cface9189d329257` | PASS |
| 作者源 `src/ci_workflow/renderers/portal/assets/report-a.js` | `740752d9452e955e35e84512d733cadf0e8da47ec50ab93a25d8493ceb471e45` | 与 v6 站点资产逐字节一致 |
| v6 `assets/report-a.js` | `740752d9452e955e35e84512d733cadf0e8da47ec50ab93a25d8493ceb471e45` | PASS |
| v6 `data/report.js` | `e4e8c181e56fc6e9c8fbdf511226561c877279813b5ad0532d766becd979a695` | 与 v5 数据资产一致；本轮未补造来源 |
| `tests/browser/test_a_w05a_product.py` | `4f0b70ea564159f63f8fd0ac41dde35bcf9ddf0e87c12f9db492fd6d15b3b749` | 与返修声明一致 |
| `tools/capture_w05a_browser.py` | `6f0bdb9abc796efe58dd90ecfe1f2b82c056c65b993e0439b709ae573a81c35e` | 与返修声明一致 |
| v6 `browser-receipt.json` | `c15c8a4a9dfafe34b3de33b4578044780ac1299ecebfba5dda8256af307700b6` | 与返修声明一致 |

v5 与 v6 静态站点递归比较只有 `assets/portal.css` 和 `assets/report-a.js` 不同；所有 HTML、45 个产品页、`data/report.js` 及其他资产均逐字节相同。v6 改动聚焦窄屏布局与等义筛选摘要，不构成来源数据变更。

截图 SHA-256：

- 1920：`805e5867660d56a9638c64f85ec677fb7621ca3906bf8af1c94c2bf92a955bd5`
- 1440：`2b02dcfed6bde377cce71780e759b55aeb0100aafe276792a98751f258566620`
- 1024：`c5bceacdc124096f2239ae6656c58f81be8e8f192ba780e9e801045d60e7d2ff`
- 390：`4edf71e631e8fdf5a2edabfe792ced8fe0a99de05d1db3174261d16d336ebd7d`
- 320：`9ab817ebb4c680d1d7f03809c542c87218b7fe5619617a6179f0b08157f7d872`
- 305：`232c7840b3276dd8cd1030380393c16664b2fb7af2881893d20cbfad4653f359`
- 1440 返回旅程：`bfd872256459bd68c6715aaa0be3f1c6ac1cdafcaa32156d795bfbcc5a926b7a`

## 4. 六 viewport 独立判定

### 4.1 冻结 receipt 与截图

| viewport | 布局 | receipt 核心单元 `top / bottom` | 内容判断 | 结论 |
|---|---|---:|---|---|
| 1920×1080 | matrix | 612.0 / 741.2 | 主内容宽 1760，占视口 91.7%；首屏完整出现 45 项、6 阶段摘要并进入真实横向靶点×阶段矩阵，不是装饰性空白或伪摘要 | PASS |
| 1440×900 | matrix | 610.4 / 739.6 | 主内容使用全宽；首屏完整出现 45/6 核心单元并进入带产品标签的矩阵实质内容 | PASS |
| 1024×1366 | compact | 501.4 / 630.5 | 使用紧凑阶段摘要和六个靶点折叠行；旧等高空白矩阵已消除；完整表入口与外部来源均可见 | PASS |
| 390×844 | compact | 411.5 / 557.6 | 45 项、6 阶段完整核心单元；卡片 gap/padding 紧凑，正文和临床标签可读 | PASS |
| 320×568 | compact | 403.0 / 539.2 | 首屏完整容纳 45/6 核心单元并开始露出下一层；无横向滚动 | PASS |
| 305×568 | compact | 403.0 / 550.5 | 最窄冻结截图仍完整容纳核心单元；按钮不叠压、三列阶段标签未裁切、section lead 完整 | PASS |

冻结 receipt 六档均记录：`project_count=45`、`stage_count=6`、最小触控高度 40px、正文/lead 最小 16px、阶段最小 14px、横向 overflow 0、console error 0。

### 4.2 第二浏览器环境复测

使用本机 Chrome 扩展浏览器打开同一 v6 静态站点并设置相同六档 viewport。该环境保留 15px 垂直滚动条，因此 `clientWidth` 比声明 viewport 更窄，构成对 v5 跨浏览器问题的直接复核：

| 请求 viewport | 实际 `clientWidth` | 核心单元 `top / bottom` | 45/6 | 字体/触控 | 结论 |
|---|---:|---:|---:|---|---|
| 1920×1080 | 1905 | 612.0 / 741.2 | 45/6 | 16px / 14px / 40px | PASS |
| 1440×900 | 1425 | 610.4 / 739.6 | 45/6 | 16px / 14px / 40px | PASS |
| 1024×1366 | 1009 | 501.4 / 630.6 | 45/6 | 16px / 14px / 40px | PASS |
| 390×844 | 375 | 411.5 / 557.7 | 45/6 | 16px / 14px / 40px | PASS |
| 320×568 | 305 | 403.0 / 550.6 | 45/6 | 16px / 14px / 40px | PASS |
| 305×568 | 290 | 415.0 / 562.6 | 45/6 | 16px / 14px / 40px | PASS |

最关键的 305 档即使实际内容宽收窄至 290px，底边仍留在 568px 首屏内；阶段标签均适配。该证据关闭 v5 的跨浏览器 305/320 阻断项。

## 5. 完整表、守恒和关键旅程

独立 Chrome 在 390/320/305 三档逐一展开首个靶点和“完整产品表”：

- 页面、靶点详情和完整表容器均无横向滚动；
- 完整表均为 45 条记录；每条均有 6 个 `dt` 字段；
- 可见产品控件最小高度约 40.4px，标签无裁切；
- 390/320/305 的实际 `clientWidth` 分别为 375/305/290px，结果均通过。

冻结 receipt 的 1440 旅程记录：宇宙→机制→产品→地域→试验→结果→证据→返回全部完成；机制、地域、试验、结果、证据五个锚点均为 true；证据抽屉与返回抽屉均可见；图表/完整表同 query 为 true；图表/表格产品数为 45/45。旅程截图与 receipt 绑定，且 v6 除两项作者资产外与 v5 页面/数据一致。

当前独立决定性批进一步覆盖同 query、保存视图恢复、稳定产品链接以及抽屉关闭后的回焦。因此本复审不发现 Top-N 截断、产品/阶段不守恒、字段不可达或回退断链。

## 6. 1024 safety 与稳定链接

当前独立决定性批包含并通过：

- `test_a_safety_details_are_paginated_and_fit_at_1024`
- `test_a_matrix_bubble_and_legend_open_accessible_product_insight_drawer`

结合 v5 后置浏览器探针，1024 safety 容器 `scrollWidth/clientWidth=948/948`、页面 overflow 0，第 2 页首行约 99.38px（低于 120px），关键维度列约 104.27px；稳定 `href` 不再被返回参数污染，点击时由运行时生成有状态导航。结论：**1024 safety 当前通过；稳定链接当前通过。**

## 7. 测试关系与剩余 8 项裁决

### 7.1 `355 passed / 10 failed` 与精确 `3/3`

历史规定相关批 `355 passed / 10 failed` 是一次混合状态快照。10 项失败中：

- 2 项是 W05A 可归因项：320 高负载核心单元和 1024 safety/链接相关项；随后精确批 `3 passed` 只证明这 3 个指定 nodeid 已修复；
- 其余 8 项没有被 `3/3` 覆盖，也不能被 `355 passed` 抵消。

v6 本次独立复跑决定性批结果为：

```text
12 passed in 160.98s
```

覆盖六档高负载、三档移动完整表、同 query、1024 safety、稳定链接/抽屉回焦。随后对剩余 8 项逐项精确复跑，结果为：

```text
8 failed in 290.33s
```

因此，“不可归因于本轮 W05A”只回答因果归属，不等于产品/科学验收风险消失。

### 7.2 六项共享既有基线失败（当前仍失败）

| nodeid | 当前信号 | 对 W05A 的裁决 |
|---|---|---|
| `test_pointer_bar_opens_same_row_evidence[chromium]` | drawer 始终 hidden，30s timeout | 共享 pointer/evidence-drawer 基线；不阻断本次 A 响应式返修接受，但阻断“共享交互已闭合”或全平台 PASS |
| `test_pointer_bar_opens_same_row_evidence[webkit]` | 同上 | 同上 |
| `test_pointer_bar_escape_returns_focus_to_exact_svg_mark[chromium]` | drawer 未打开，无法进入 Escape 回焦验证 | 共享键盘/可访问性交互未闭合；不能自动忽略 |
| `test_pointer_bar_escape_returns_focus_to_exact_svg_mark[webkit]` | 同上 | 同上 |
| `test_pointer_click_highlights_table_row[chromium]` | `got=None`, expected `row-ctrl-endpoint-a` | 共享 chart-table-sync 未闭合；不证明 v6 A 响应式回归，但仍是产品风险 |
| `test_pointer_click_highlights_table_row[webkit]` | 同上 | 同上 |

这 6 项运行通用 fixture 和共享协议，不是 v6 landscape 专属实现；v6 没有修复它们。归类为**共享既有基线**，需要由共享交互所有者闭合并做跨 Chromium/WebKit 复核。

### 7.3 两项历史 A 合同差异（当前仍失败）

| nodeid | 当前信号 | 裁决 |
|---|---|---|
| `test_a_home_efficacy_preserves_all_endpoints_and_timepoints` | 首页 efficacy DOM 的行集合少于测试要求的完整 endpoint/timepoint 集合 | 当前仍是完整观测可达性风险；是历史 A 合同差异，不是 v6 定向返修引入。需要产品/科学合同裁决：要求首屏/当前 DOM 全量，还是允许分页但必须建立可验证的全量可达合同。 |
| `test_a_safety_heatmap_uses_distinct_continuous_colors_within_each_event` | `teae_backgrounds` 为空，期望 4 种连续背景色 | 当前安全呈现已偏离旧 heatmap 编码合同。需要决定保留旧连续色合同，还是正式迁移到 observation/card 合同并同步验收；在裁决前不得宣称该合同 PASS。 |

这两项不阻断本次 landscape 响应式和 safety 详情几何的局部接受，但阻断“所有 A 产品合同均已闭合”的表述。

## 8. P1-02 真实逐事实来源边界

v6 `data/report.js` 与 v5 完全相同。独立只读解析结果：

```json
{
  "products": 45,
  "trials": 140,
  "efficacy": 3895,
  "safety": 517,
  "public_sources": 2,
  "fact_rows": 4412,
  "rows_with_source_field_path_and_source_text": 0,
  "rows_with_either_locator_or_source_text": 0
}
```

两个 `public_sources` 条目自身明确标注为“报告级来源清单；具体行级支持关系尚未在此展开”。它们不能证明 3895 条疗效和 517 条安全事实的 locator 与原文。来源完备 fixture 只能验证前端在有来源输入时如何展示，不能把当前真实载荷变成 PASS。

裁决：P1-02 **未闭合，依赖 W07**。它不推翻本次前端实现质量判断，但它是正式 W05A 整体门的硬阻断，因此 W05A 整体必须保持 **FAIL**。

## 9. P0–P3

| 等级 | 状态 | 项目 |
|---|---|---|
| P0 | 无新增 | 未发现导致页面不可用、数据丢失或错误发布的新增 P0。 |
| P1 | **OPEN** | P1-02 真实逐事实来源闭合：0/4412，阻断 W05A 正式整体门；依赖 W07。 |
| P1（共享） | **OPEN** | 6 个 pointer/drawer/focus/chart-table-sync 节点当前仍失败。不是 v6 A 响应式可归因回归，但属于真实交互与可访问性风险，阻断共享平台/全产品闭合。 |
| P1（已关闭） | CLOSED | v5 的 305/320 跨浏览器首屏稳定性；六档、独立 Chrome 和当前 12 项批均通过。 |
| P2 | **OPEN** | 首页疗效完整 endpoint/timepoint DOM 合同与旧 safety heatmap 连续色合同仍失败，需后续合同裁决与相应实现/测试闭合。 |
| P3 | 无新增 | 无需以低优先级问题稀释上述硬门。 |

## 10. 可复现证据

决定性前端批：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/browser/test_a_w05a_product.py::test_high_load_landscape_exposes_complete_core_unit_without_clipping \
  tests/browser/test_a_w05a_product.py::test_high_load_landscape_mobile_detail_and_complete_table_do_not_scroll_sideways \
  tests/browser/test_a_w05a_product.py::test_same_query_drives_chart_and_folded_table_and_saved_view_restores \
  tests/browser/test_a_portal.py::test_a_safety_details_are_paginated_and_fit_at_1024 \
  tests/browser/test_a_portal.py::test_a_matrix_bubble_and_legend_open_accessible_product_insight_drawer \
  -q --tb=short
```

结果：`12 passed in 160.98s`。

剩余 8 项精确批：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  'tests/browser/test_evidence_drawer.py::test_pointer_bar_opens_same_row_evidence[chromium]' \
  'tests/browser/test_evidence_drawer.py::test_pointer_bar_opens_same_row_evidence[webkit]' \
  'tests/browser/test_evidence_drawer.py::test_pointer_bar_escape_returns_focus_to_exact_svg_mark[chromium]' \
  'tests/browser/test_evidence_drawer.py::test_pointer_bar_escape_returns_focus_to_exact_svg_mark[webkit]' \
  'tests/browser/test_chart_table_sync.py::test_pointer_click_highlights_table_row[chromium]' \
  'tests/browser/test_chart_table_sync.py::test_pointer_click_highlights_table_row[webkit]' \
  tests/browser/test_a_portal.py::test_a_home_efficacy_preserves_all_endpoints_and_timepoints \
  tests/browser/test_a_portal.py::test_a_safety_heatmap_uses_distinct_continuous_colors_within_each_event \
  -q --tb=short
```

结果：`8 failed in 290.33s`。

来源解析可用 Node `vm` 只读加载 v6 `data/report.js`，统计 `efficacy`、`safety`、`public_sources` 以及每条事实的 `source_field_path`/`source_text`；结果见第 8 节。

## 11. 下一安全动作

1. **冻结并接受 v6 前端 W05A 返修范围**；不要再为已通过的六档响应式、1024 safety 或稳定链接做无证据改动。
2. 由 W07 提供真实逐事实来源输入与可审计 locator+原文映射；重新生成真实 A 载荷后，按新 payload 哈希重跑来源闭合和受影响页面验收。
3. 将 6 个共享失败交给共享 pointer/evidence-drawer/chart-table-sync 所有者；保留 Chromium/WebKit 双引擎和键盘焦点返回断言。
4. 对两项历史 A 差异做明确合同裁决；不得仅删除或放宽测试来制造绿色。
5. 在 P1-02、共享交互和所需合同裁决闭合前，维持 W05A 整体 **FAIL**，不得宣布 RC 或发布。

