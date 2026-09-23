# W05A v5 冻结候选独立复审

复审日期：2026-09-23  
唯一工程：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`  
候选站点：`evidence/W05A-remediation-real-a-v5/`  
候选浏览器证据：`evidence/W05A-remediation-browser-v5/`  
复审方式：只读源码、测试、日志、冻结站点和真实浏览器；除本报告外未修改工程文件，未执行修复、提交、推送、回滚、清理或删除。

## 1. 独立结论

### 1.1 运行时身份

请求运行时为 `gpt-5.6-sol:medium`。本会话及工程证据均未提供可核验的 model/effort 身份回执，因此身份结论为 **UNVERIFIED**；未替换为其他可声称身份。

### 1.2 双层 verdict

| 层次 | verdict | 说明 |
|---|---|---|
| W05A 前端返修主路径 | **CONDITIONAL PASS，但冻结门仍 FAIL** | 1920、1440、1024、390 的空间/密度，移动完整表，45/45 集合，同 query，三层下钻/回退，键盘关键旅程，1024 safety 几何和稳定链接均通过；但独立 in-app Chromium 在 `innerWidth=320` 且滚动条占 15px 时，核心单元底边为 617.35px，未在 568px 首屏完整出现，与固化 receipt/Playwright 的 542.42px 结果矛盾。320 硬门尚不能无条件接受。 |
| W05A 正式总门 | **FAIL** | 除 320 浏览器环境敏感性外，真实 A 的逐事实来源闭包仍为 0，明确依赖 W07；规定相关批还保留 8 个红项，其中 6 个是共享交互基线、2 个需要合同裁决。P0/P1 未归零，不能冻结为 RC。 |

这不是“来源 fixture 通过即可接受”的结论。更准确的边界是：**前端大部分返修可条件接受；真实来源验收明确依赖 W07；当前 W05A 正式总门未过。** 同时，320 的独立浏览器差异使前端本身也不能记为无条件 PASS。

### 1.3 严重度

- **P0=0**。
- **W05A-local P1=2**：320 首屏完整单元跨浏览器环境不稳定；真实逐事实来源未闭合。
- **共享平台 P1=1**：6 个 pointer/evidence-drawer/chart-table-sync 用例在 Chromium/WebKit 均失败；不由 W05A 引入且 v5 A 不加载这些共享脚本，但属于真实共享产品风险，阻断全产品/RC，不得因“不可归因”删除。
- **P2=2**：首页疗效“全部行必须同时在首页 DOM”与摘要页合同需裁决；旧 safety heatmap 精确 fixture 断言与当前真实页面需裁决。
- **P3=0**。

## 2. 候选身份与资产闭合

暂停交接列出的冻结源码哈希与本轮当前文件一致：

| 文件 | SHA-256 | 结论 |
|---|---|---|
| `src/.../assets/portal.css` | `50702bfff67e86b2996ab398133c081a54374508fe21b62cebede9be54c2489f` | 与交接一致；与 v5 `assets/portal.css` 逐字节一致 |
| `src/.../assets/report-a.css` | `9f1c024d6981caaaeffc86071fd2615a86ff744c4086bb206d44eebd55842bf4` | 与 v5 `assets/report-a.css` 逐字节一致 |
| `src/.../assets/report-a.js` | `395ee2babaab318c541b6fbeab379f811251ca6e1248d904e08c9a3bdb89c3fa` | 与交接一致；与 v5 `assets/report-a.js` 逐字节一致 |
| `templates/a/landscape.html.j2` | `f74844cb5ba9738b0d1d1db643bdb8775e4daaec5da3c6c014db781092f826f4` | 与交接一致 |
| `templates/a/safety.html.j2` | `5a22f58becb1949b94a48d969d1e549e8dabe09cc34353cbb761f4f6ce62bcf0` | 与交接一致 |
| `tests/browser/test_a_w05a_product.py` | `4346bc2e037192b2b6528a013c84cd49c018d4900898aa55422467242d353b2b` | 与交接一致 |
| v5 `browser-receipt.json` | `b347c19b96927623807df662e88351473f3a3236d38ada1d7c02e624ca111fe7` | 与交接一致 |

v5 `data/report.js` 本轮实算 SHA-256 为 `e4e8c181e56fc6e9c8fbdf511226561c877279813b5ad0532d766becd979a695`。当前源资产与 v5 资产一致，没有发现“源码已变而站点仍旧”的漂移。

## 3. 五 viewport 独立判定

固化截图全部独立目视复核；同时用 v5 真实站点做 DOM/交互复测。

| viewport | 判定 | 独立观察 |
|---|---|---|
| 1920×1080 | **PASS** | 主内容 1760px（91.7%）；核心 45 产品/6阶段分布完整，横向矩阵首屏可见 338.82px，已经出现产品单元，不是只加宽外壳。24px panel padding、40px 最小按钮、正文 16px、页面横向 overflow=0。 |
| 1440×900 | **PASS** | 主内容有效铺满；核心分布完整，矩阵首屏可见 160.39px，截图可见表头和首批产品，属于有意义矩阵内容。24px padding、40px 最小按钮、正文 16px、overflow=0。 |
| 1024×1366 | **PASS** | 改为紧凑模式，核心分布 129.19px、靶点折叠区 355px 均完整可见；不再由最高阶段列撑出等高空白。18px padding、40px 最小按钮、正文 16px、overflow=0。 |
| 390×844 | **PASS** | 核心分布 146.19px 完整可见，靶点分组首屏可见 291.54px；10px padding，控件最小 40px，正文 16px。移动完整表为 45 条卡片，每条 6 字段，`scrollWidth=clientWidth=335`。 |
| 320×568 | **FAIL（跨浏览器环境硬门）** | 固化 receipt/截图及 Playwright 高负载测试记录 core `y=406.23/h=136.19/bottom=542.42`，可完整显示；但本轮 in-app Chromium 的 `innerWidth=320`、内容宽 305px，文本换行后 core `y=455.37/h=161.98/bottom=617.35`，首屏仅可见 112.63px，矩阵明细可见 0px。页面仍无横滚、控件 40px、正文 16px，移动完整表仍为 45×6字段且 `scrollWidth=clientWidth=265`。该差异说明 320 门对滚动条/字体布局敏感，未达到可冻结的跨环境稳定性。 |

320 的核心单元不是旧版“单独数量条”：它确实包含完整 universe 的 6 阶段计数，合计 45 产品。但在本轮第二浏览器环境中，6个阶段未全部进入首屏，因此仍不能满足“首屏至少一个完整关键阅读单元”的冻结门。

## 4. 功能与关键旅程

| 合同 | verdict | 证据 |
|---|---|---|
| 完整 universe / 无 Top-N | **PASS** | v5 payload 为 45 产品；真实 DOM 图与表均为 45 个唯一产品且集合相等；正文无 `Top-N`。 |
| 阶段守恒 | **PASS** | 6阶段计数为 I期9、I/II期3、II期12、III期17、IV期2、未知2，总计45。 |
| 同 query | **PASS** | 选择 IV期后图与表均精确为 `eculizumab, sirolimus`，URL 为 `?phase=IV期`。 |
| 移动完整表 | **PASS** | 390/320 均为45条记录；每条字段精确为产品、靶点、技术类型、最高阶段、地域、开发状态；无内部或页面横向滚动，字段字号16px。 |
| 三层下钻/回退 | **PASS** | `adx-038` 洞察→完整产品档案→机制/地域/试验/结果/证据五锚点→返回；返回 URL 为 `landscape.html?focus=adx-038` 且洞察恢复。 |
| 稳定链接 | **PASS** | 洞察中的静态 `href` 仍为 `products/adx-038.html`；状态参数仅在实际导航时生成。 |
| 键盘关键旅程 | **PASS** | Enter 打开洞察，初始焦点到关闭按钮；ArrowRight 从疗效切到安全性；Escape 关闭并回焦精确 `adx-038` 产品按钮。 |
| 1024 safety 几何 | **PASS** | 真实 v5 第2/11页，当前筛选517条、每页50条；首行99.375px，维度列102.625px，容器 `933/933`，页面 overflow=0，正文16px。 |
| 浏览器 console | **PASS（本轮旅程）** | 本轮 v5 页面 error/warning 为空。 |

## 5. `355/10`、`3/3` 与剩余 8 项

### 5.1 日志关系

- `final-related-batch.log`：`355 passed / 10 failed`，日志 SHA-256 `d0faf97581e4242fbf0af663e0061186054159497ab40aa7fc11ed9aab22c1d8`。
- 10项失败由：320旧7产品响应式1项、1024 safety1项、A首页疗效1项、旧 safety heatmap1项、共享 pointer/drawer/sync 6项组成。
- `final-attributable-green.log`：`3 passed`，SHA-256 `be98f2fc974b219f5d34a671c71e6cc4c0a27a0f6c3a9e846b5f58f848ded77a`。这3项中，真正关闭 `355/10` 红项的是320旧7产品测试和1024 safety两项；稳定链接在 `355/10` 时已经通过，只是再次确认。
- 因此 `3/3` 不能改写成相关批全绿；数学关系是 **10项中关闭2项，剩8项**。
- 本轮独立复跑剩余8项，结果为 **`8 failed in 288.27s`**；全部逐项复现。
- 本轮另复跑真实规模/决定性 W05A 批：45产品五视口、390/320移动表、同query/保存恢复、320旧门、1024 safety、稳定链接，共 **`11 passed in 161.05s`**。

### 5.2 剩余8项逐项裁决

| nodeid | 当前结果 | 分类 | 是否阻断 W05A | 风险裁决 |
|---|---|---|---|---|
| `test_a_home_efficacy_preserves_all_endpoints_and_timepoints` | FAIL | **合同需裁决** | 当前不单独阻断，但禁止称相关批全绿 | 真实 v5 首页只呈现20个唯一 row 的摘要；专门疗效页的图与完整表均可达全部3895行。PRD要求全部观察可达、不默认选一个“最好”终点，但没有明确要求3895行同时驻留首页DOM。需决定首页是摘要还是全量容器；若坚持旧测试，W05A阻断。 |
| `test_a_safety_heatmap_uses_distinct_continuous_colors_within_each_event` | FAIL | **合同/fixture需裁决** | 当前不单独阻断，但测试债务必须关闭 | 测试精确查找 `data-heat-event="任何TEAE"` 得0；真实 v5 安全页有493个 heat cells、固定0–100%刻度及多种连续背景色，但事件标签为实际登记语义（如“严重不良事件”“Participants with TEAEs”等）。这不是“当前页面无热图”，而是旧 fixture/精确标签合同与真实语义漂移。 |
| `test_pointer_bar_opens_same_row_evidence[chromium]` | FAIL | **共享既有基线** | 不阻断 W05A 专属 A 站点；阻断共享产品/RC | 通用 drawer 保持 hidden。 |
| `test_pointer_bar_opens_same_row_evidence[webkit]` | FAIL | **共享既有基线** | 同上 | 与 Chromium 同因。 |
| `test_pointer_bar_escape_returns_focus_to_exact_svg_mark[chromium]` | FAIL | **共享既有基线** | 不阻断 W05A 专属 A 站点；阻断共享产品/RC | 抽屉未打开，后续回焦无法成立。 |
| `test_pointer_bar_escape_returns_focus_to_exact_svg_mark[webkit]` | FAIL | **共享既有基线** | 同上 | 与 Chromium 同因。 |
| `test_pointer_click_highlights_table_row[chromium]` | FAIL | **共享既有基线** | 不阻断 W05A 专属 A 站点；阻断共享产品/RC | 实际 `selectedRowId=None`。 |
| `test_pointer_click_highlights_table_row[webkit]` | FAIL | **共享既有基线** | 同上 | 与 Chromium 同因。 |

6个共享用例运行的是 `charts.js`/`evidence-drawer.js` fixture；v5 A 页面实际只加载 `portal.js` 与 `report-a.js`，不加载这两份共享脚本。本轮 A 专属洞察、证据、键盘和回焦旅程通过，因此没有证据把这6项归因给 W05A；但它们在两个浏览器均真实失败，仍是全产品共享交互风险，后续 B/C/共享图表和 RC 必须关闭。

## 6. 真实来源边界（P1-02）

本轮直接解析 v5 `data/report.js`：

- 产品45、试验140、疗效3895行、安全性517行；
- 报告级 `public_sources=2`；
- 4412条疗效/安全记录中，同时具有 `source_field_path` 与 `source_text` 的行数为0，任一字段非空的行数也为0；
- `user_edits=0`。

`source-closure-audit.json` 的确定性扫描进一步记录：解析英文工程152份 A payload，`fully_closed_count=0`，逐事实 locator+原文最大闭合行数仅1，且该1行是 W04 用户修订工件，不代表真实45产品 A。

因此：

1. 来源完备 fixture 只能证明前端“能显示来源层”，不能证明真实 A 已有来源。
2. 报告级 ClinicalTrials.gov 两条清单不能替代逐事实支持关系。
3. P1-02 是 W07 的真实来源构建依赖，不应要求 W05A 前端伪造 locator；但在正式 W05A 总门中，它仍是未通过的 P1。
4. 若只评价“前端代码是否正确消费合格来源输入”，可以条件接受；若评价 PRD/ACCEPTANCE 定义的完整 W05A 产品交付，必须保持 **FAIL**，直到 W07 提供真实来源并对同一候选重验。

## 7. 可复现证据

### 7.1 剩余8项复跑

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/browser/test_a_portal.py::test_a_home_efficacy_preserves_all_endpoints_and_timepoints \
  tests/browser/test_a_portal.py::test_a_safety_heatmap_uses_distinct_continuous_colors_within_each_event \
  tests/browser/test_evidence_drawer.py::test_pointer_bar_opens_same_row_evidence \
  tests/browser/test_evidence_drawer.py::test_pointer_bar_escape_returns_focus_to_exact_svg_mark \
  tests/browser/test_chart_table_sync.py::test_pointer_click_highlights_table_row \
  -q --tb=short
# 8 failed in 288.27s
```

### 7.2 决定性 W05A 复跑

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/browser/test_a_w05a_product.py::test_high_load_landscape_exposes_complete_core_unit_without_clipping \
  tests/browser/test_a_w05a_product.py::test_high_load_landscape_mobile_detail_and_complete_table_do_not_scroll_sideways \
  tests/browser/test_a_w05a_product.py::test_same_query_drives_chart_and_folded_table_and_saved_view_restores \
  'tests/browser/test_a_w05a_product.py::test_a_responsive_space_uses_canvas_and_keeps_a_complete_first_reading_unit[320-568-0.98-12]' \
  tests/browser/test_a_portal.py::test_a_safety_details_are_paginated_and_fit_at_1024 \
  tests/browser/test_a_portal.py::test_a_matrix_bubble_and_legend_open_accessible_product_insight_drawer \
  -q --tb=short
# 11 passed in 161.05s
```

### 7.3 核心证据路径

- `evidence/W05A-remediation-browser-v5/browser-receipt.json`
- `evidence/W05A-remediation-browser-v5/landscape-{1920x1080,1440x900,1024x1366,390x844,320x568}.png`
- `evidence/W05A-remediation-browser-v5/journey-return-1440x900.png`
- `evidence/W05A-remediation-logs/final-related-batch.log`
- `evidence/W05A-remediation-logs/final-attributable-green.log`
- `evidence/W05A-remediation-logs/source-closure-audit.json`
- `evidence/W05A-remediation-logs/post-batch-browser-probe-v2.json`

## 8. 下一安全动作

1. **不得宣布 RC、发布或 W05A 总 PASS。**
2. 在不改业务内容的前提下，先用正式目标 Chromium/WebKit 各自以320×568复测，并覆盖“非 overlay scrollbar / 内容宽约305px”情形；若核心单元不能完整首屏，做一次最小响应式修复，再一次性复跑上述11项。
3. 对首页疗效摘要和 safety heatmap 两项做明确合同裁决：保留“首页摘要+专页全量”则更新测试合同并提供迁移理由；若坚持旧全量首页DOM/精确事件标签，则实现必须修复。禁止直接删测或以“既有失败”忽略。
4. 将6个共享 pointer/drawer/sync 失败移交共享交互工作包，保留 Chromium/WebKit 原始失败；在 B/C、共享图表或 RC 前关闭。
5. W07 构建真实逐事实来源闭包后，用同一45产品候选重建 A，复核每条关键疗效/安全事实的 source version、locator、原文/合法摘录和页面来源区；fixture 通过不得计入真实来源 PASS。

**最终结论：W05A v5 冻结候选 FAIL；前端返修主路径大部分通过但仅可条件接受；正式 W05A 总门未过，不能进入 RC/发布。**
