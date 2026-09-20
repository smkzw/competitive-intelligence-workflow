Delegated fallback is active: I will run the assigned HTML-PPT visual review only and return the worker report. Reading the execution context and plan first.Context lists no source-of-truth files yet, so I’ll locate the three HTML-PPT decks and Task 8.6 readability criteria before reviewing pages.Found the three decks under `output/html-ppt/`. Next I’ll read Task 8.6 criteria and page manifests, then inspect each slide’s labels, density, and Chinese copy.Text audit is complete. Next I’ll inspect existing screenshots and SVG coordinates, then render remaining high-risk slides in the browser.# Execution Output: ci-phase8-task86-visual-baseline - worker_02

**Fallback:** 本角色按 Codex 声明的 `pi` fallback `cursor` / `cursor-grok-4.6` 执行（原一线 `grok-build` / `grok-4.6` 在可恢复会话前不可用）。未做 62 页 × 四视口实时 Chromium/WebKit 原图采集（属 worker_01 收集器范围）；本轮证据来自当前三份 HTML 的全页 DOM/SVG 只读解析，以及 Task 8.5 已存 1440×900 代表页截图的视觉审阅。不声明终验、不改锁定医学数据、不写生产路径、不写 runner 报告文件。

## Boundary And Context Check

- **任务边界：** 只读审查 `output/html-ppt/report-{a,b,c}.html` 共 62 页（A20+B24+C18），定位标签、数值、图例、留白、内容密度、中文表达缺陷，提供页级证据。不改主题/数据/运行时。
- **权威源：** 执行上下文 Source of Truth 仍为 TODO；实际审查对象按当前交付物绑定：
  - `output/html-ppt/report-a.html` sha256 `adcf8487aa85996d0d4886d7801a16a544f2b703cac5a331d4a7a7af085eb2e4`（manifest `input_sha256` `988c1607…` 为输入包哈希，与 HTML 文件哈希不同）
  - `output/html-ppt/report-b.html` sha256 `087d04b0aa1ddb0da26c5370fcf26e8bb328efc4705136194bbe0ecdb5740b1d`
  - `output/html-ppt/report-c.html` sha256 `fd2d47565bfdb1b12f6405c62ed53f9762eac67c92175302a5a6eba8d3064113`
- **合同口径（只读引用，非验收裁定）：** `.trellis/tasks/08-31-phase-8-task-86-html-ppt-visual-acceptance/prd.md` / `design.md`；8.5 移交三项：A 矩阵第二页标签留白/引线、C `75 %` 间距、B 92.2 与图例邻近。
- **未越权：** 未改 HTML/CSS/JS、未装包、未做安全测试、未做临床/监管终验、未写 `runs/execution/.../worker_02.md`。
- **证据分级：** 截图级 = 已见 1440×900 光栅；DOM 级 = 当前 HTML 原文；推断级单独标注。

## Work Performed

1. 绑定三份当前 HTML 与 manifest 的 62 个 `slide_id`，抽取每页标题、可见正文、SVG `<text>` 坐标、英文标识、百分号空格、蛇形字段名。
2. 对 Task 8.5 代表页截图做医学经理角色视觉审阅：`a-efficacy` `a-efficacy-3` `a-safety` `a-matrix` `a-matrix-2` `a-regulatory`；`b-efficacy` `b-matrix` `b-demographics` `b-flow`；`c-inclusion` `c-endpoints` `c-stats` `c-identity` `c-path-1`。
3. 用 SVG 坐标启发式核对柱顶数值与图例、矩阵标签邻近。
4. 产出全 62 页台账：确定性缺陷 / 密度与表达问题 / 未见图但 DOM 可证 / 本轮未见阻断。

## Artifacts And Evidence

本 worker **未创建**新文件。证据路径：

- 源：`output/html-ppt/report-a.html` `report-b.html` `report-c.html` 及对应 `.manifest.json`
- 既有光栅：`docs/acceptance/runs/8.5/screenshots/*.png`（非 8.6 最大化终验原图）
- 合同：`.trellis/tasks/08-31-phase-8-task-86-html-ppt-visual-acceptance/{prd,design}.md`；`docs/acceptance/runs/8.6/visual-research.md`；`docs/acceptance/runs/8.5/browser-contract-evidence.md`

### 8.5 移交三项（截图 + DOM 均复现，仍待 8.6 首修）

| ID | 页 | 类别 | 证据 | 建议（不改数） |
|---|---|---|---|---|
| H1 | `a-matrix-2` p14/20 | 标签/引线/留白 | 截图：`曲罗芦单抗` 与 `来布利珠单抗` 叠在两气泡之间，归属不清；`度普利尤单抗` 气泡压在 X 轴上。无刻度、无气泡面积图例。 | 引线外置、拉开相邻标签、轴刻度、气泡面积说明 |
| H2 | `c-endpoints` `c-dossiers` `c-identity` | 中文/数值排版 | DOM 三处 `EASI ≥ 75 %改善`（数字与 `%` 间空格）；截图 `c-endpoints` 右下卡、`c-identity` 第4行同文 | 改为 `EASI-75` 或 `75%` 无空格；勿改阈值 |
| H3 | `b-efficacy` p4/24 | 数值邻近图例 | 截图：`92.2` 贴住右上「治疗组」图例；SVG `92.2` x=855 y=33.2，图例「治疗组」x=880 y=20 | 图例外移或抬高 y 轴上限，保持 92.2 不变 |

### A 类页级台账（20）

| 页 | 判定 | 关键发现 |
|---|---|---|
| a-cover | 低危表达 | 开场纪律清楚；封面与逐字稿同屏时密度偏低（结构页，可接受） |
| a-toc | 通过倾向 | 四章目录可读 |
| a-summary | 术语 | 观众页出现 `EASI-75 族`（内部分组词）；KPI 与阶段柱并列，尚可扫读 |
| a-landscape / a-products | 密度不均 | 热图格字可读；左下空、右上满；靶点/剂型中英混排（IL-4Rα 等可保留） |
| a-clinical | 图例位置 | 图例「治疗组/对照组」在 SVG 顶栏，本页是试验阶段柱，图例语义易串页 |
| **a-efficacy** | **标签/命名** | 截图：`乐德奇拜单抗 (Rademikibart / SIM0718)` 三行、与邻柱不齐；`611 (SSGJ-611)` 三行；Y 轴 0/22/45/67/90 非十进制；轴无 `%`；中英/代号混用 |
| a-efficacy-2 | 中英混 | 中文通用名为主，较好；`APG777` 仅代号 |
| **a-efficacy-3** | **数值撞图例** | 截图：`ICP-332` 柱顶 `64.0` 与「治疗组」图例碰撞；6/8 柱为英文 INN |
| a-efficacy-4 | 标签 | SVG：`14.5`/`12.7` 间距约 10px；长标签 `Rezpegaldesleukin` |
| a-efficacy-5 | 中英混 | `Rocatinlimab` `Amlitelimab` `Bermekimab` 无中文对照 |
| **a-safety** | **0.0 vs 未公开** | 截图：度普利尤单抗 TEAE `0.0` 浅粉 vs 米色「未公开」接近；AESI 列全未公开仍占 1/3 宽；缺行头「产品」 |
| **a-matrix** | **标签碰撞/折行** | 截图：`Rezpegaldesleukin` 断成 `Rezpegaldesl` / `eukin`；`611` 与 `芦可替尼乳膏` 同簇；脚注「10 个配对」与可见气泡易数成 9；无轴刻度/引线；左下大留白 |
| **a-matrix-2** | **见 H1** | 另：未配对名单全英文，与图内中文名体系不一致 |
| **a-regulatory** | **中文误读** | 截图：「…三线」易读成三线治疗；KPI `12` 境外已获批 vs 总数 `76` 未解释其余境外记录；「不能讲成」「标签变更」口语/翻译腔 |
| a-companies | 表达 | `Regeneron / Sanofi` `LEO Pharma` `Lilly / Almirall` 可保留；三条「未公开条款不推测」重复 |
| a-patents | 密度低+重复 | 多行同一句「不得由药名推测核心专利范围 / 未公开/未核实」，医学经理扫读无增量 |
| a-history | 中英名单 | 停研名单以英文 INN 为主，与疗效页中文名不对齐 |
| a-limitations | 通过倾向 | 来源卡清楚；`ClinicalTrials.gov` 可保留 |
| a-ending | 通过倾向 | 结束页；装饰 SVG 无文字（非读数缺陷） |

### B 类页级台账（24）

| 页 | 判定 | 关键发现 |
|---|---|---|
| b-cover / b-toc | 通过倾向 | 适应症与阅读纪律清楚 |
| b-summary | 可读 | APPLY 62/35、APPOINT 40 单臂披露清楚 |
| **b-efficacy** | **见 H3** | 两柱组间横向留白过大 |
| b-longitudinal | 结构空 | 仅重复第24周三点；模块存在但无纵向曲线——符合数据，版式仍显空 |
| b-safety | 通过倾向 | 四列热图可读；0.0 突破性溶血有脚注 |
| **b-matrix** | **留白/图例/表达** | 截图：单点挤右上，坐标区大部分空；无刻度；气泡面积写在卡片里；HTML 为「治疗—对照」，截图易读成「治疗一对照」；「APPLY」气泡+卡片+底栏三重重复 |
| b-baseline-overview | 通过倾向 | 12/9/3/0 域计数清楚 |
| **b-demographics** | **密度/扫读** | 截图：9 张重复卡、`已公开`×9；同一臂拆左右栏，年龄与样本量不对齐；宜改 3×4 表（不改数） |
| b-disease-context / b-subgroups | 空模块披露 | 结构正确；大留白；底栏带「禁止」口吻，偏内部质检句 |
| b-severity | 单位 | DOM：`8.9g/dL` `8.2g/dL` 缺空格，建议 `8.9 g/dL` |
| b-disposition-overview | 通过倾向 | 14 已公开 / 40 未公开 分区清楚 |
| **b-flow** | **密度+结构** | 截图：`APPLY-PNH APPLY 治疗组` 双重前缀；APPOINT 左右列从「治疗/对照」变成「时间步切分」，CONSORT 扫读失败 |
| **b-adherence** | **英文字段** | DOM 三行指标字面 `adherence`，非「依从性」 |
| b-loss-exit | 密度 | ~816 字符，未公开行堆叠，重复试验名前缀 |
| b-screen-failure | 重复结构 | 筛选 120 已公开 + 筛败未公开，可扫读 |
| **b-rescue** | **英文字段** | `rescue_treatment` ×3 |
| **b-prohibited** | **英文字段** | `prohibited_medication` ×3 |
| **b-deviation** | **英文字段+密度** | `protocol_deviation` / `major_protocol_deviation` / `protocol_deviation_leading_to_exclusion` 蛇形英文；页字符 ~709 |
| b-exposure / b-profiles | 通过倾向 | NCT 与臂信息可读 |
| **b-limitations** | **中英** | `APPLY-PNH primary report` 应用「主要试验报告」 |
| b-ending | 通过倾向 | 同 A 结束页 |

### C 类页级台账（18）

| 页 | 判定 | 关键发现 |
|---|---|---|
| c-cover / c-toc | 通过倾向 | 设计比较、不讲疗效的纪律清楚 |
| c-summary | 命名不一 | 三药四试验卡片可读；奈莫利珠单抗试验用描述名、其余用 CHRONOS/ADvocate2 |
| c-design-map | 命名不一 | 同上；盲法/例数可读 |
| c-population | 通过倾向 | 年龄/病程差标清楚 |
| **c-inclusion** | **字段错位** | 截图：CHRONOS 卡正文是「评估时点 筛选期」而非入选阈值；后三项 `EASI ≥ 16 分`；底栏「对齐」「十六分」口语+中文数字 |
| c-exclusion | 信息薄 | 四卡多为「评估时点 筛选期/基线前」，排除内容本身弱 |
| c-arms | 密度+套话 | ~655 汉字；「试验组干预已公开；对照为对照臂登记项」重复四次，医学经理难一次抓住给药差 |
| **c-endpoints** | **见 H2** | 另：半角分号；底栏「落在…」「百分之七十五」翻译腔；卡内空白大 |
| c-visits | 通过倾向 | 时点可读 |
| **c-stats** | **标题过载** | 截图：无任何检验/α/把握度；右栏四次「登记记录未单独公开分析集」；标题含「统计设计」名不副实 |
| c-dossiers | H2 再现 | `终点 EASI ≥ 75 %改善`；「时间点 评估时点 第16周」叠词 |
| **c-identity** | **H2+内部口吻** | 第4行 `75 %`；CHRONOS「入组 评估时点 筛选期」；底栏「本页强制同时给出…」是验收指令不是讲稿 |
| c-patterns | 表达 | 与入选页相同的「对齐/十六分」问题 |
| **c-path-1** | **术语** | 截图：「人群差标」「路径一落到 CHRONOS」「不是推荐标准」；大留白；数字全汉字 |
| c-path-2 | 表达 | 「入组对齐」「对照仍是对照臂」重复；可用，但非医学汇报句 |
| c-limitations | 重复 | 四卡同一句「不外推此后方案修订」 |
| c-ending | 通过倾向 | 结束页 |

### 跨报告模式（推断 + 证据）

1. **直接标注不足：** A/B 气泡矩阵无轴刻度、少引线，违反 8.6「标签不重叠、无需反复对照图例」。
2. **产品身份不统一：** 中文通用名 / INN / 代号混用；长 INN 硬折行。
3. **未公开模块用内部英文字段当观众标签：** B 依从/补救/禁用药/偏离。
4. **空模块与稀疏页用重复纪律句填空白**，医学经理会读成质检清单。
5. **数字体例分裂：** 图内阿拉伯数字 vs 底栏「百分之七十五」「第十六周」「一百二十人」。
6. **图例占绘图区：** A 续2 的 64.0、B 的 92.2 同类。

**不确定性：** 8.5 截图是否与当前 HTML 像素级一致——DOM 已确认 H1–H3 与蛇形字段仍在当前哈希中；矩阵气泡是否物理重叠需 worker_01 新原图。未在 1280×800 / 1920×1080 / 2048×1024 / 1280×720 上逐页复验溢出。

## Commands And Observations

| 工具 | 目标 | 观察 |
|---|---|---|
| glob / eval | 定位三份 HTML | `output/html-ppt/report-{a,b,c}.html`，62 `data-slide-id` |
| Python HTML/SVG 解析 | 全页密度、英文、碰撞启发式 | A/B 矩阵与疗效柱顶邻近；C 三处 `75 %`；B 蛇形字段 |
| inspect_image | 8.5 代表页 PNG | 复现 H1–H3、安全热图 0.0/未公开、流转双重前缀、入选字段错位 |
| 未执行 | Playwright 四视口 62 页 | 避免与 worker_01 收集器抢写；本角色无授权产出目录 |

未跑 pytest/ruff（非本项）。未改任何源文件。

## Blockers Or Missing Environment

- 执行上下文未列出权威源路径；已用当前 `output/html-ppt` 三文件，请 Codex 确认是否即为绑定哈希。
- 本 fallback **未**完成 62×4 视口真实渲染；缺 Chromium/WebKit 原图则不能关闭「逐页视觉接受」。
- 无授权截图输出目录，故未落盘新 PNG。
- 不阻塞阅读的环境：现有 8.5 PNG + 当前 HTML 足够做**首轮缺陷台账**，不够做终验。

请 Codex 确认：

1. 上述三份 HTML 哈希是否即为 Task 8.6 绑定对象？
2. 观众页是否允许出现 `adherence` 等字段名，还是必须中文医学用语（推荐后者，不改锁定数值）？
3. `EASI-75 族` 是否为冻结术语？若否，建议改为「EASI-75 同类终点」。

## Rerun Requests Or Next Step

1. **最小修订优先级（供后续实施角色，非本 worker 动刀）：**  
   P0：H1 a-matrix-2 引线/留白；H2 去掉 `75 %` 空格（三页）；H3 92.2 离开图例；B 四页蛇形字段中文化；a-efficacy-3 的 64.0 避让图例。  
   P1：a-matrix 长 INN 折行与引线；a-safety 0.0/未公开色差；a-regulatory「三线」；c-inclusion CHRONOS 字段；c-identity/c-stats 去掉「强制/统计设计」名实不符；b-flow 分组表头。  
   P2：稀疏页并卡、数字体例统一、气泡轴刻度。
2. 待 worker_01 台账后，用同一哈希对 P0 页做 1280×800 与 1920×1080 回归截图。
3. Codex 终验前：医学经理角色只看原图，不看本台账标签。

**本 worker 不声称 62 页视觉通过。**
