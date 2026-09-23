# W05A 独立视觉/产品复核

复核日期：2026-09-23  
唯一工程：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`  
复核边界：只读产品源码、指定交付包、指定测试、真实 A 重放与实际浏览器；未修改产品、测试、`STATUS.md` 或既有证据。

## 1. 结论

**总状态：UNVERIFIED。** 当前会话未取得可核验的 `gpt-5.6-sol:medium` model/effort 身份回执，未替换模型身份。

**仅按工件与产品验收判定：FAIL。** P0=0，P1=3，P2=2，P3=0。失败不依赖实现者自评或测试数量，主要由以下本轮独立实查直接支持：

1. 真实 45 产品数据下，390×844 与 320×568 的核心图高分别为 **559.9px / 643.4px**；320 首屏实际只显示 66.8px 的“当前完整宇宙”摘要条，核心阶段×产品矩阵可见高度为 **0px**。receipt 的“完整阅读单元”统计的是摘要条，不是核心图。
2. 1024×1366 的核心图高 **850.4px**，首屏仅可见约 801.2px；首个 C5 靶点中产品集中于少数阶段，CSS 网格按最高列等高，造成大面积空白，未达到纵向高密度。
3. 真实重放 `public_sources=0`；3895 条疗效行与 517 条安全性行中，带 `source_field_path` 或 `source_text` 的行均为 **0**。页面实际只能显示“未绑定可核验的公共来源谱系”，无法完成逐事实来源回链验收。
4. 指定 W05A 测试独立复跑为 `9 passed in 5.54s`，但响应式夹具只有 **7 产品**；其 `<=520px` 窄屏图高断言没有覆盖真实 45 产品，所以不能排除当前真实数据回归。
5. “486 passed / 49 failed”没有随 W05A 证据提供完整 nodeid、原始失败日志、逐项根因与受影响范围；不能据概括排除 W05A 回归。

## 2. 严重性清单

### P0

- 无。

### P1

#### P1-01 真实 45 产品移动端/纵向密度硬门失败

- 需求要求关键图、结论和核心筛选尽量在首屏形成完整阅读单元，且不得以缩小字号、触控目标、隐藏数据或横向滚动实现；见 `PRD.md:64,79`、`work_packages/W05A.md:25,29`、`ACCEPTANCE.md:81,87`。
- 实际 DOM：
  - 1920×1080：图 `y=742.4, h=666.4`，首屏可见约 337.6px；摘要完整，核心矩阵不完整。
  - 1440×900：图 `y=740.8, h=804.4`，首屏可见约 159.2px；只看到摘要和矩阵表头。
  - 1024×1366：图 `y=564.8, h=850.4`，首屏可见约 801.2px；核心矩阵仍未完整，且存在大块空白列区。
  - 390×844：图 `y=455.8, h=559.9`，首屏可见约 388.2px；只展开首靶点，移动矩阵密集挤压为多列卡片。
  - 320×568：图 `y=499.8, h=643.4`，首屏仅可见约 68.2px，其中 66.8px 是摘要条；核心矩阵内容为 0px。
- receipt 的 `first_reading_unit` 在五档均指向 `.kz-a-landscape-overview`（44–66.8px），而 `chart` 底边分别到 1408.8/1545.2/1415.2/1015.7/1143.1px；见 `browser-receipt.json:75-111,187-223,299-335,411-447,523-559`。
- 测试只对 7 产品夹具断言窄屏图高 `<=520`；真实数据直接超过该门。夹具由 4 个基础产品加 3 个阶段产品组成，见 `tests/browser/test_a_w05a_product.py:15-47`；窄屏断言见 `tests/browser/test_a_w05a_product.py:122-177`。
- 320 展开完整表后，表宽 840px、容器宽 278px，`scrollWidth > clientWidth`，必须横向滚动；实现来源见 `portal.css:154-165`、`templates/a/landscape.html.j2:12-14`。
- 移动矩阵在 `<=820px` 改为阶段卡片自动排布，并默认只展开第一个靶点；见 `portal.css:417-431` 与 `report-a.js:1210-1246`。数据仍在 DOM 且可展开，但阶段×产品关系不能在 320/390 上一眼稳定比较，临床可读性不通过。

#### P1-02 真实 A 缺少可核验来源与逐事实定位

- 真实 payload：45 产品、140 试验、3895 疗效行、517 安全性行；但 `public_sources=0`，所有疗效/安全行的 `source_field_path` 与 `source_text` 均为空。证据文件为 `evidence/W05A-real-a/data/report.js:1`。
- 实际页面外部来源区显示“此报告未绑定可核验的公共来源谱系”；模板在无 `external_sources` 时只显示这一限制，见 `templates/a/base.html.j2:79-95`。
- 产品证据抽屉能列出试验和报告级说明，但代码明确说明报告级来源不代表当前产品逐事实支持，见 `report-a.js:582-613`。真实重放甚至没有报告级公共来源。
- 用户修订与原来源的分层代码存在，见 `report-a.js:1313-1334`、`report_a.py:1869-1974`，指定测试也覆盖空来源显示；但真实 A `user_edits=0` 且没有行级来源字段，因此本轮无法在真实数据上验证该层级。
- 这违反每页统一来源区与逐事实支持要求，不能以“来源类别”或试验清单替代。

#### P1-03 `486 passed / 49 failed` 回归证据未闭合

- 唯一可见材料只有实现报告中的数量和概括，见 `W05A-result.md:68-77`；W05A 证据目录没有对应完整 pytest 日志、49 个 nodeid、失败堆栈、逐项根因、与 W05A 影响分析或重跑关闭记录。
- 因此无法确认哪些失败属于旧预期，哪些是当前 typed projection、共享抽屉或真实运行合同回归；不能用 `237 passed` 或 `9 passed` 抵消。
- 在补齐逐项证据前，W05A 回归门保持未闭合。

### P2

#### P2-01 宽屏横向空间“图表层”通过，但首屏空间组织仍不足

- 1920 主内容宽 1760px（91.7%），1440 为全宽；矩阵实际横向铺开靶点与阶段列，并非只把外层容器变宽。对应令牌和网格见 `portal.css:50-53,74-80,104-116`。这一项本身 PASS。
- 但两个核心筛选在 1920/1440 仍各占整行、垂直堆叠，导致关键矩阵在 1440 首屏只露出约 159px。属于空间组织缺口，应与 P1-01 一并修复，而非仅继续加宽容器。

#### P2-02 可访问性只完成了关键旅程抽查，不能声明全量通过

- 本轮实际验证：产品按钮可键盘触发；抽屉初始焦点落在关闭按钮；方向键在 tabs 间移动；Escape 关闭并回焦原产品；焦点陷阱代码见 `report-a.js:680-719`。产品按钮有明确 `aria-label`，见 `report-a.js:1225-1232`。
- 320/390 的 landscape 关键控件最小高度为 40px，正文 16px；未靠缩小核心字号或触控目标通过。
- 未执行屏幕阅读器、对比度自动审计、200%/400% zoom、WebKit 或全部 45 产品详情页键盘遍历；故只能判关键旅程通过，不能判 WCAG 或全站可访问性通过。

### P3

- 无独立 P3；宽屏筛选重排已并入必须修复的首屏密度问题。

## 3. 逐 viewport 结论

| viewport | 本轮实际结论 | DOM/视觉依据 |
|---|---|---|
| 1920×1080 | **条件通过：横向利用 PASS；首屏核心图不完整** | 主内容 1760px，矩阵 1662px；阶段列真实横向展开。图从 742.4px 开始，底边 1408.8px，首屏仅见约 337.6px。|
| 1440×900 | **FAIL（首屏）** | 图从 740.8px 开始，仅约 159.2px 可见；截图只见摘要与表头，未形成核心图完整阅读单元。|
| 1024×1366 | **FAIL（纵向密度/空白）** | 图高 850.4px、底边 1415.2px；C5 产品集中少数阶段导致等高网格出现大面积空白。|
| 390×844 | **FAIL（真实数据覆盖与临床可读性）** | 图高 559.9px，超过测试上限 520px；仅首靶点展开，阶段卡片多列挤压，完整产品关系需继续滚动/展开。|
| 320×568 | **FAIL（首屏）** | 摘要底边 567.6px，但核心矩阵从约 573.6px 才开始；首屏核心图内容 0px。图高 643.4px；完整表还要求 840/278px 横向滚动。|

对应既有截图路径（本轮另以实时浏览器重新渲染并逐档核对，未把旧截图当作替代证据）：

- `evidence/W05A-browser/landscape-1920x1080.png`
- `evidence/W05A-browser/landscape-1440x900.png`
- `evidence/W05A-browser/landscape-1024x1366.png`
- `evidence/W05A-browser/landscape-390x844.png`
- `evidence/W05A-browser/landscape-320x568.png`

因唯一允许持久写入本报告，本轮实时浏览器截图仅在审阅会话中检查，未另存新文件；以上路径用于定位实现侧原截图，本轮 DOM 数值为独立重新测量结果。

## 4. 其他合同逐项结论

| 合同 | 结论 | 独立证据 |
|---|---|---|
| 完整 universe / 无 Top-N | PASS（当前真实 payload） | `REPORT_A.products=45`、唯一 ID=45；实时 DOM 图=45、表=45、集合逐 ID 相同；正文无 `Top-N`。策略文件见 `page-catalogs/A.yaml:5-11`。|
| 阶段守恒 | PASS（当前真实 payload） | 实际阶段为 I、I/II、II、III、IV、未标注→未知；DOM 阶段集合精确一致。映射代码见 `report-a.js:1166-1189`。真实数据本身没有临床前、II/III、III/IV 产品，不能凭合成夹具声称这些阶段在真实 A 已出现。|
| 图表同 query | PASS | 真实 A 选择 IV期后图与表均为 `eculizumab, sirolimus`，URL 为 `?phase=IV期`；过滤与重绘链见 `report-a.js:1434-1488`。|
| 三层下钻/回退 | PASS（抽查 eculizumab） | landscape 产品→洞察抽屉→完整产品档案；机制/地域/试验/结果/证据五锚点存在；打开证据抽屉后返回 landscape，`focus=eculizumab` 且抽屉恢复。模板见 `product.html.j2:5-17`。|
| 登记状态/批准事实分层 | PASS（展示层） | 产品档案分别显示“当前状态（登记记录口径）”和“监管批准事实”，见 `product.html.j2:8-11`。|
| 来源/用户修订层级 | FAIL / 真实数据未验证 | 分层实现存在，但真实 A 无公共来源、无行级 locator/text、无 user edit；见 P1-02。|
| localStorage allowlist | PASS（当前实现） | 实际保存内容仅 `schema_version/report/query.phase`；无 HTML、函数、会话。代码只收集页面声明维度并在恢复时检查 schema/report/数组，见 `report-a.js:1489-1549`。本轮临时 localStorage 已清空。|
| 键盘/焦点 | PASS（关键旅程） | tabs 方向键、Escape、回焦、焦点陷阱均实际通过；未扩张为全站 WCAG 结论。|
| console / 页面横向 overflow | PASS（抽查范围） | 本轮 11 个 A 顶层页在 1920 与 320 均 `documentElement.scrollWidth-innerWidth=0`；控制台 error/warning=0。注意完整表内部横向滚动仍真实存在，不应被“页面无溢出”掩盖。|

## 5. 可复现命令与本轮观测

### 5.1 指定测试独立复跑

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/browser/test_a_w05a_product.py -q --tb=short
# 9 passed in 5.54s
```

夹具规模复核：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from tests.browser.test_a_w05a_product import _stage_payload
p = _stage_payload()
print(len(p['products']), sorted({x['phase'] for x in p['products']}))
PY
# 7 ['I/II期', 'III期', 'II期', 'IV期', 'I期', '临床前', '未标注']
```

### 5.2 源码/真实重放绑定

```bash
shasum -a 256 \
  src/ci_workflow/renderers/portal/assets/portal.css \
  evidence/W05A-real-a/assets/portal.css \
  src/ci_workflow/renderers/portal/assets/report-a.css \
  evidence/W05A-real-a/assets/report-a.css \
  src/ci_workflow/renderers/portal/assets/report-a.js \
  evidence/W05A-real-a/assets/report-a.js
```

三对哈希分别一致：

- `portal.css`: `7e91536d7fd39f77ec8c5a91037a05420f0e141d6a25129cf0a519b62c93d9d3`
- `report-a.css`: `9f1c024d6981caaaeffc86071fd2615a86ff744c4086bb206d44eebd55842bf4`
- `report-a.js`: `d4482903ca322e5fd2f76bf6c459fcc1469159f47e8aa2d0d16596d7a20d2842`

真实 `report.js` SHA-256：`548c24e9c573f925c8b42f38f545f98846b5ac8d90e32e07c781c3801dfecb9b`。

### 5.3 实时 DOM 指标口径

本轮在本地只读 HTTP 重放 `evidence/W05A-real-a/landscape.html`，逐档设置 1920×1080、1440×900、1024×1366、390×844、320×568，读取：

- `.portal-main/.kz-a-panel/.portal-page-head/.kz-a-workspace-bar` bounding box；
- 两个 `[data-filter-dimension]` bounding box；
- `[data-chart-id="landscape-full"]`、`.kz-a-landscape-overview`、`.kz-a-landscape-grid` bounding box；
- 图/表产品 ID 集合、阶段集合、可见触控高度、页面 scrollWidth、控制台日志；
- 320 展开完整表后的 `.kz-a-table-wrap.clientWidth/scrollWidth = 278/840`。

## 6. 必须修复项

1. **用真实 45 产品 payload 建立响应式回归。** 测试必须直接断言真实 390/320 图高、核心矩阵（不是摘要条）首屏可见量、展开后可读性、产品/阶段集合和无裁切；不能继续只用 7 产品夹具代表真实负载。
2. **重构 1024/390/320 的阶段×产品表达。** 避免按最高阶段列等高造成大片空白；移动端建议按靶点→阶段分组的纵向紧凑清单/分区，而不是把 6 个阶段挤成多列小格。所有 45 产品继续可达且集合守恒。
3. **首屏门改为核心阅读单元。** `complete_reading_unit_visible` 必须绑定至少一个临床可读的核心图/矩阵内容，不得继续把 44–66.8px 的数量摘要当核心图完成。
4. **消除移动完整表的横向滚动依赖。** 至少提供无横向滚动的卡片/定义列表/列折叠替代视图，同时保留全部字段可达；不得隐藏关键数据。
5. **补齐真实 A 来源闭包。** 为真实疗效/安全行提供 source version、原文/合法摘录、结构化 locator 和逐事实支持关系；每页来源区应有可核验链接、类型、公开日期、数据截止与限制。真实 A 有来源后再复测用户修订/原来源分层。
6. **闭合 49 个失败。** 提供完整 nodeid、原始日志、失败分类、根因、是否受 W05A 影响及重跑结果；所有 W05A 相关失败必须关闭后才能重新申请独立复核。

## 7. 可后置项

- WebKit、200%/400% zoom、屏幕阅读器和对比度全量审计可进入下一轮，但不得据当前键盘抽查宣称全站无障碍通过。
- W05B/W05C、24 门户、三宿主、离线分享和 RC 不属于本次 W05A 工件复核；继续保持未验。
- 1920/1440 的筛选区可改为任务适配的两列或紧凑工具栏，以把矩阵进一步上提；应与 P1-01 同次修复验证。

## 8. 未验范围与限制

- 运行时 `gpt-5.6-sol:medium` 身份/effort 无可核验回执：**UNVERIFIED**。
- 未运行全 gate；`486/49` 无逐项证据，不能视为已归因。
- 未验证真实 user edit，因为该真实 A payload 的 `user_edits=0`。
- 未检查 WebKit、全部 45 产品详情页、全部表格字段的键盘遍历、屏幕阅读器、缩放/高对比模式。
- 未作正式医学、监管、法务或发布批准；本报告只给工程产品复核结论。

## 9. 本轮审阅步骤与健康度

1. 完整读取 PRD/DESIGN/PLAN/EXECUTION_RULES/ACCEPTANCE/STATUS/W05A/result/receipt/指定测试：**完成**。
2. 核对作者源与真实重放资产哈希：**通过**。
3. 五 viewport 实时 DOM 与截图复核：**失败（响应式硬门）**。
4. 真实 universe/阶段/无 Top-N/同 query：**通过**。
5. 三层下钻、证据抽屉、回退、键盘焦点：**关键旅程通过**。
6. 来源/用户修订真实层级：**失败/未覆盖**。
7. localStorage allowlist、console、顶层页横向 overflow：**抽查通过**。
8. 486/49 回归证据：**未闭合**。

**下一安全动作：** 先修 P1-01/P1-02，并补齐 P1-03 的完整失败证据；冻结新的真实 45 产品 A 重放后，再进行同样五档的独立只读复核。
