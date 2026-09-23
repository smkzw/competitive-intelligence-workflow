# Task 8.5 HTML-PPT 投影合同（worker_01）

状态：结构合同已冻结；共享组装器、A/B/C 投影实现与浏览器终验分别由 worker_02 / worker_03 / Task 8.6 完成。
本文件是 deck 结构、数据映射与失败关闭的权威。不得用门户 DOM、PDF 布局或截图生成幻灯片。

## 1. 锁定输入

| 报告 | 路径 | 用途 | SHA-256 |
|---|---|---|---|
| A | `fixtures/positive/a-atopic-dermatitis/research-content.json` | 唯一内容源；只投影 `report_data` | `988c1607e08c7f9747a6feb493dcdaf66b6ccd7c26cafefe96e956622196fa1a` |
| A 包 | `fixtures/positive/a-atopic-dermatitis/research-package.json` | 仅核对其 `report_data` 与 content 同构；禁止投影 `scientific_review` / 原始 `sources[].content_text` | `2a2d789833b2f380639137ca50ab54a63c588c13c082a0cd8d6645eb6880c39b` |
| B | `fixtures/positive/b-pnh/inputs/report-data.json` | 唯一内容源 | `a37d7239bfc68f50d86ff732953c68769f1e70710d9e05e36f474941ce172e3b` |
| C | `fixtures/positive/c-atopic-dermatitis/inputs/report-data.json` | 唯一内容源 | `a59d7f88b3d8a2e163422c01f0d0981aa64bf2610cc6bb41852c58e9561ed2e6` |

当前快照事实（实现必须消费，不得改写输入）：

- A：适应症「特应性皮炎」；`report_data` 含 38 产品、49 试验、6780 条疗效、10228 条安全性、76 条监管、38 条企业、38 条专利、41 条历史、5 条来源局限。顶层 `sources`（86 条含原文）、`route_attempts`、`facts`、`claims`、`gate_status` 不得进入观众页。
- B：适应症「阵发性睡眠性血红蛋白尿」；产品伊普可泮；试验 APPLY-PNH（NCT04558918，关键确证，治疗组 62 / 对照 35）与 APPOINT-PNH（NCT04820530，单臂 40）。疗效仅第 24 周血红蛋白应答率；矩阵只接收封闭 typed 治疗—对照投影，APPOINT 单臂不生成伪差值点。基线仅人口学 + 基线血红蛋白；处置 54 条中 40 条 `not_publicly_disclosed`。
- C：适应症「中重度特应性皮炎」；3 产品 4 试验（CHRONOS / ADvocate2 / 奈莫利珠单抗疗效与安全性研究 / ADvantage）；48 条 `observations`，12 字段 × 4 试验。无独立 pattern 对象；一项证据完整研究可形成单条设计先例，多条先例不得排名。

## 2. 运行时与视觉资产（原样内联）

| 资产 | 路径 | SHA-256 |
|---|---|---|
| runtime.js | `assets/html-ppt/runtime.js` | `affadf9e344ec9da62cdd27942a41218983d2cb88a377eca540b7da622a990f7` |
| runtime.css | `assets/html-ppt/runtime.css` | `09df452da708ac80a9660bb49ff8603cfac85aec7e607852c99ca09a209517d0` |
| gx_fx.css | `contracts/kangzhe/design_specs/assets/htmlppt/gx_fx.css` | `7e2ba09538f2e9c59c07f2ad2c8f708828c71f5f8e71771c5aa337da6bb5a572` |
| gx_fx.js | `contracts/kangzhe/design_specs/assets/htmlppt/gx_fx.js` | `92cdb59102b888db0d046caeae34700cc29c97275dba626a652560603cb9c86b` |
| logo | `contracts/kangzhe/design_specs/assets/logo_bot.svg` | `8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae` |

单文件 HTML 内联顺序：kangzhe 主题 CSS → `gx_fx.css` → `runtime.css`；脚本：`runtime.js` → `gx_fx.js`。源码禁止 `src`/`href` 指向 `http(s):` / `ws(s):`。Logo 仅 Data URL。禁止改写 FX 选择器或运行时哈希。

硬几何（Task 8.4 + `track_htmlppt.md`）：每个 `.deck > section.slide` 逻辑尺寸 1280×720；内容页 class `content-slide`，封面/目录/章节/结束分别为 `cover-slide` / `toc-slide` / `section-slide` / `ending-slide`。正文逻辑字号下限 16px；常规正文 19px；内容页标题 32px 单行。每页一个 `aside.notes`；观众页不显示逐字稿。

## 3. 页面责任覆盖

目录权威：`docs/architecture/page-catalogs/{A,B,C}.yaml`（12 / 21 / 12 个静态页）。HTML-PPT 用 `data-page-responsibility` 绑定责任 id；封面/目录/摘要/结束页同属 `overview`。门户「完整表」责任仍由 HTML/PDF 承担；本介质只保留图表、数字块、简化对照和关键注释。

覆盖针（观众可见中文，禁止英文 PDF 表头腔）：

- A：竞争格局、产品总览、临床开发组合、疗效、安全性、疗效与安全性矩阵、中国与全球监管、企业与交易、专利与保护、历史与边缘观察、研究依据与局限。
- B：疗效、纵向结果、安全性、疗效与安全性矩阵、基线与人群总览、人口学、疾病语境、基线疾病严重程度、试验完成情况、受试者流转、依从性、失访与退出、筛败、补救治疗、禁用药、方案偏离、试验与暴露语境、亚组与支持证据、产品与试验档案、研究依据与局限。
- C：设计图谱、人群与疾病定义、入选标准、排除标准、分组、干预与对照、终点、定义与时间点、访视、疗程与随访、样本量、分析集与统计设计、试验档案、设计模式、可选路径、资料版本与局限。C 禁止套用结果汇报口径。

## 4. 三份 deck 结构

页码从 1 计。每页只回答一个演示问题。

### 4.1 A · 15 页基线（允许疗效续页）· 特应性皮炎竞品全景

| # | slide_id | class | 标题 | responsibility | 数据 | 视觉 |
|---|---|---|---|---|---|---|
| 1 | a-cover | cover | 特应性皮炎竞品全景 | overview | indication, cutoff | 英雄封面 |
| 2 | a-toc | toc | 目录 | overview | 下列页标题 | 2×2 目录卡 |
| 3 | a-summary | content | 首页摘要 | overview | 产品数/阶段/靶点计数 + 已上市中文名 | 数字块 + 结构图 |
| 4 | a-landscape | content | 竞争格局 | landscape | products.target/modality/phase/status | 靶点×阶段结构图 |
| 5 | a-products | content | 产品总览 | product-overview | 38 产品身份字段 | 目标—模态矩阵（计数，非全表） |
| 6 | a-clinical | content | 临床开发组合 | clinical-portfolio | trials × products | 产品—试验关系/阶段地域 |
| 7 | a-efficacy | content | 疗效 | efficacy | efficacy 终点族 | 分组柱（治疗组/对照并列） |
| 8 | a-safety | content | 安全性 | safety | safety 摘要行 | 热图（严重/特别关注/治疗期间） |
| 9 | a-matrix | content | 疗效与安全性矩阵 | matrix | 可成对的疗效点 × TEAE | 气泡图，无综合分 |
| 10 | a-regulatory | content | 中国与全球监管 | regulatory | regulatory.track 中国/境外 | 双轨时间/状态 |
| 11 | a-companies | content | 企业与交易 | companies-transactions | companies | 关系/权益数字块 |
| 12 | a-patents | content | 专利与保护 | patents-protection | patents | 保护注释，不把推断写成事实 |
| 13 | a-history | content | 历史与边缘观察 | historical-edge | history + 终止状态产品 | 状态分层 |
| 14 | a-limitations | content | 研究依据与局限 | evidence-limitations | report_data.sources | 来源/披露局限 |
| 15 | a-ending | ending | 谢谢 | overview | 适应症名 | 结束页 |

A 疗效族（不得按数值 Top-N）：

1. 主要族：`endpoint` 匹配 `(?i)EASI[- ]?75`（当前 548 行 / 25 产品，含度普利尤单抗等已上市品种；字面 `endpoint=="EASI-75"` 会丢掉核心品种，禁止）。
2. 并列族：IGA 0 或 1 且较基线改善 ≥2 分。
3. 时间点优先：`第16周` → 含 `Week 16` → 其余按试验 `display_id`。
4. 锚定试验：`role` 为「核心」优先，再 `display_id`。
5. 臂：治疗组与对照组/安慰剂组并列；无对照则标注「无同期对照」，不得删除产品、不得填 0。
6. 单页系列不得超过 8；超出时按靶点分组增设 `a-efficacy-2`、`a-efficacy-3`…续页，不按效应值截断、不缩字。所有续页均绑定 `efficacy` 页面责任。

A 矩阵：气泡 x=所选疗效族治疗组值，y=治疗期间不良事件（倒序语义在注释中说明），r∝sqrt(治疗组 N)；无配对则不画点，改披露状态，禁止池化。

### 4.2 B · 24 页 · 不得删用户指定模块

| # | slide_id | class | 标题 | responsibility | 数据 | 失败关闭 |
|---|---|---|---|---|---|---|
| 1 | b-cover | cover | 阵发性睡眠性血红蛋白尿临床试验结果比较 | overview | indication | 禁止写成特应性皮炎 |
| 2 | b-toc | toc | 目录 | overview | 页标题 | |
| 3 | b-summary | content | 首页摘要 | overview | 伊普可泮 + 两试验角色 | 数字必须来自本快照 |
| 4 | b-efficacy | content | 疗效 | efficacy | `efficacy` + `efficacy_views.facts` | APPLY 82.3% vs 1.8%；APPOINT 92.2% 无对照 |
| 5 | b-longitudinal | content | 纵向结果 | longitudinal-results | 仅第24周 | 不得编造其他访视曲线 |
| 6 | b-safety | content | 安全性 | safety | `safety` + `safety_views`（teae/sae/aesi/common_ae） | 枚举必须译中文 |
| 7 | b-matrix | content | 疗效与安全性矩阵 | efficacy-safety-matrix | `matrix_view.rows` typed projections | APPOINT 单臂不得生成治疗—对照差值点 |
| 8 | b-baseline-overview | content | 基线与人群总览 | baseline-overview | `baseline_views.facts` | |
| 9 | b-demographics | content | 人口学 | baseline-demographics | 样本量/年龄/性别 | |
| 10 | b-disease-context | content | 疾病语境 | baseline-disease-context | **无该 domain 事实** | 披露矩阵；禁止用血红蛋白冒充语境 |
| 11 | b-severity | content | 基线疾病严重程度 | baseline-severity | 基线血红蛋白 8.9 / 8.9 / 8.2 g/dL | |
| 12 | b-disposition-overview | content | 试验完成情况总览 | disposition-overview | `disposition_views.facts` | 已披露与未披露分区 |
| 13 | b-flow | content | 受试者流转 | participant-flow | screened/randomized/treated/completed_* | 筛败未公开不得记 0 |
| 14 | b-adherence | content | 依从性 | adherence | 3 条均未公开 | 披露状态矩阵 |
| 15 | b-loss-exit | content | 失访与退出 | loss-exit | 失访/退出/停药均未公开 | 同上 |
| 16 | b-screen-failure | content | 筛败与原因 | screen-failure | 筛败未公开；筛选 120/120 已披露 | 不得把筛败派到随机组 |
| 17 | b-rescue | content | 补救治疗 | rescue-treatment | 全未公开 | |
| 18 | b-prohibited | content | 禁用药使用 | prohibited-medication | 全未公开 | |
| 19 | b-deviation | content | 方案偏离 | plan-deviation | 全未公开 | |
| 20 | b-exposure | content | 试验与暴露语境 | trial-exposure-context | trials 角色/样本量/臂 | |
| 21 | b-subgroups | content | 亚组与支持证据 | subgroups-supporting-evidence | **无亚组行** | 说明本快照未提供独立亚组结果；禁止捏造 |
| 22 | b-profiles | content | 产品与试验档案 | product-trial-profiles | 伊普可泮 + 两试验身份 | 必须能读到 NCT 与中文名 |
| 23 | b-limitations | content | 研究依据与局限 | evidence-limitations | `sources[].limitation` | |
| 24 | b-ending | ending | 谢谢 | overview | | |

中文映射（观众页）：`teae`→治疗期间不良事件，`sae`→严重不良事件，`aesi`→特别关注不良事件，`common_ae`→常见不良事件，`treatment`→治疗组，`control`→对照组，`reported_value`→已公开，`not_publicly_disclosed`→未公开，`reported_zero`→已公开为零，`not_applicable`→不适用。

### 4.3 C · 18 页 · 元素对照 → 试验定位 → 可选路径

| # | slide_id | class | 标题 | responsibility | 数据 |
|---|---|---|---|---|---|
| 1 | c-cover | cover | 中重度特应性皮炎临床试验设计比较 | overview | indication |
| 2 | c-toc | toc | 目录 | overview | |
| 3 | c-summary | content | 首页摘要 | overview | 3 药 4 试验身份 |
| 4 | c-design-map | content | 设计图谱 | design-map | trials + grouping 观察 |
| 5 | c-population | content | 人群与疾病定义 | population-disease-definition | field=`target_population` |
| 6 | c-inclusion | content | 入选标准 | inclusion-criteria | field=`inclusion_criterion`；优先 scale/阈值/中文差标 |
| 7 | c-exclusion | content | 排除标准 | exclusion-criteria | field=`exclusion_criterion` |
| 8 | c-arms | content | 分组、干预与对照 | treatment-arms | grouping + experimental_arm + control_arm + dosing_regimen |
| 9 | c-endpoints | content | 终点、定义与时间点 | endpoint-timepoint-matrix | primary_endpoint_definition + primary_endpoint_timepoint |
| 10 | c-visits | content | 访视、疗程与随访 | visit-duration-followup | visit_schedule + dosing 时间 |
| 11 | c-stats | content | 样本量、分析集与统计设计 | sample-analysis-statistics | sample_size + analysis_population（后者多未公开） |
| 12 | c-dossiers | content | 试验档案 | trial-profile | 四试验身份卡：药名、NCT、评分、时间点 |
| 13 | c-identity | content | 试验定位核对 | trial-profile | 强制可同时读到药物、试验、量表/阈值、评估时间点 |
| 14 | c-patterns | content | 设计模式与权衡 | design-patterns | 从差标归纳；禁止唯一最佳 |
| 15 | c-path-1 | content | 可选路径一 | design-patterns | 单条完整先例可用 |
| 16 | c-path-2 | content | 可选路径二（兼容位） | design-patterns | 保留首版结构兼容，不作为真实渲染门 |
| 17 | c-limitations | content | 资料版本与局限 | evidence-limitations | 观众页说「登记版本」 |
| 18 | c-ending | ending | 谢谢 | overview | |

C 观众文案规则：禁止把 `source_text` 英文登记原文、`allocation=RANDOMIZED`、`The registry record does not` 作为正文。使用 `source_field_name`、`difference_labels_zh`、`randomization`/`blinding`、`scale`+`threshold_value`+`threshold_unit`、产品 `name`、试验 `display_id`/`name`。统计未公开写「登记记录未单独公开分析集」，不得推断。

可实现路径示例（非唯一结论）：路径一强调三盲 + 外用背景治疗的注册对照格局（CHRONOS）；路径二强调 IL-13 / IL-31RA 后续确证试验在入组阈值（EASI≥16）上的对齐与对照构造差异。禁止输出「最佳设计」。

## 5. 逐字稿、中文与禁用

- 每页 `aside.notes` 必须含 150–300 个汉字（`[\u4e00-\u9fff]` 计数），口语，且含至少一处 `<strong>`。
- 观众可见文本必须含汉字；禁止纯英文身份词、后端枚举、工程/日志/prompt 语。
- 禁用子串（大小写不敏感，作用于 `.slide` 去掉 `aside.notes` 后的可见文本，以及 notes 中的工程词）：`schema_version`、`gate_status`、`route_attempts`、`snapshot-`、`v-fixture`、`reported_value`、`not_publicly_disclosed`、`higher_is_better`、`workflow`、`prompt`、`playwright`、`chromium`、`RENDERER_`、`traceback`、`TODO`、`fixture run`、`scientific_review`、`content_text`。
- 未公开只用于真实 `disclosure_state` 或缺失模块；禁止主题页整页只有「未公开」而忽略已有数值。

## 6. 失败关闭（构建必须抛错 / 测试必须红）

1. 输入文件哈希与 §1 不符。
2. 缺少 §4 任一 `slide_id`，或 B 删除基线/完成情况任一模块页。
3. 主题页在源数据存在数值时输出空卡或统一「未公开」。
4. 把 APPOINT 画成有对照的疗效差，或把疾病语境页画成血红蛋白。
5. 为 B 纵向结果编造非第 24 周点，或为亚组页编造估计值。
6. C 将单条或多条设计先例排名为唯一最佳。
7. 观众页出现英文登记原文主文案或禁用子串。
8. 单文件含外链资源属性，或 runtime/FX/Logo 哈希不匹配。
9. 任一 `.slide` 缺 `aside.notes`，或汉字数不在 [150,300]，或缺 `<strong>`。
10. 逻辑画布不是 1280×720，或使用 viewport 字号/页内媒体重排。
11. 从 PDF/门户截图或 DOM 拷贝生成页面。
12. 可见字号低于 16px（高密度标签下限）。

本步不代替 Task 8.6 最大化窗口逐页视觉终验。

## 7. 下游实现边界

- worker_02：`src/ci_workflow/renderers/html_ppt/` 共享组装 + A 投影；`tools/render_html_ppt.py`；A 候选与 A 测试。
- worker_03：B/C 投影、三份候选、结构/离线/逐字稿/字号/覆盖/基础浏览器测试。
- 清单必须绑定 §1 输入哈希与 §2 资产哈希。

```json
{
  "schema_version": "8.5-projection-contract-v1",
  "inputs": {
    "A": {
      "path": "fixtures/positive/a-atopic-dermatitis/research-content.json",
      "sha256": "988c1607e08c7f9747a6feb493dcdaf66b6ccd7c26cafefe96e956622196fa1a",
      "payload_key": "report_data",
      "forbidden_root_keys": ["sources", "route_attempts", "facts", "claims", "gate_status"]
    },
    "B": {
      "path": "fixtures/positive/b-pnh/inputs/report-data.json",
      "sha256": "a37d7239bfc68f50d86ff732953c68769f1e70710d9e05e36f474941ce172e3b"
    },
    "C": {
      "path": "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json",
      "sha256": "a59d7f88b3d8a2e163422c01f0d0981aa64bf2610cc6bb41852c58e9561ed2e6"
    }
  },
  "assets": {
    "runtime_js": {"path": "assets/html-ppt/runtime.js", "sha256": "affadf9e344ec9da62cdd27942a41218983d2cb88a377eca540b7da622a990f7"},
    "runtime_css": {"path": "assets/html-ppt/runtime.css", "sha256": "09df452da708ac80a9660bb49ff8603cfac85aec7e607852c99ca09a209517d0"},
    "gx_fx_css": {"path": "contracts/kangzhe/design_specs/assets/htmlppt/gx_fx.css", "sha256": "7e2ba09538f2e9c59c07f2ad2c8f708828c71f5f8e71771c5aa337da6bb5a572"},
    "gx_fx_js": {"path": "contracts/kangzhe/design_specs/assets/htmlppt/gx_fx.js", "sha256": "92cdb59102b888db0d046caeae34700cc29c97275dba626a652560603cb9c86b"},
    "logo": {"path": "contracts/kangzhe/design_specs/assets/logo_bot.svg", "sha256": "8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae"}
  },
  "notes": {"min_han": 150, "max_han": 300, "require_strong": true},
  "canvas": {"width": 1280, "height": 720, "min_font_px": 16},
  "A_slide_ids": ["a-cover", "a-toc", "a-summary", "a-landscape", "a-products", "a-clinical", "a-efficacy", "a-safety", "a-matrix", "a-regulatory", "a-companies", "a-patents", "a-history", "a-limitations", "a-ending"],
  "A_slide_expansion": {
    "efficacy": {"prefix": "a-efficacy-", "responsibility": "efficacy", "max_series_per_slide": 8},
    "matrix": {"prefix": "a-matrix-", "responsibility": "matrix", "max_points_per_slide": 10},
    "minimum_total_slides": 15
  },
  "B_slide_ids": ["b-cover", "b-toc", "b-summary", "b-efficacy", "b-longitudinal", "b-safety", "b-matrix", "b-baseline-overview", "b-demographics", "b-disease-context", "b-severity", "b-disposition-overview", "b-flow", "b-adherence", "b-loss-exit", "b-screen-failure", "b-rescue", "b-prohibited", "b-deviation", "b-exposure", "b-subgroups", "b-profiles", "b-limitations", "b-ending"],
  "C_slide_ids": ["c-cover", "c-toc", "c-summary", "c-design-map", "c-population", "c-inclusion", "c-exclusion", "c-arms", "c-endpoints", "c-visits", "c-stats", "c-dossiers", "c-identity", "c-patterns", "c-path-1", "c-path-2", "c-limitations", "c-ending"],
  "coverage": {
    "A": {
      "a-cover": "overview", "a-toc": "overview", "a-summary": "overview",
      "a-landscape": "landscape", "a-products": "product-overview", "a-clinical": "clinical-portfolio",
      "a-efficacy": "efficacy", "a-safety": "safety", "a-matrix": "matrix", "a-regulatory": "regulatory",
      "a-companies": "companies-transactions", "a-patents": "patents-protection", "a-history": "historical-edge",
      "a-limitations": "evidence-limitations", "a-ending": "overview"
    },
    "B": {
      "b-cover": "overview", "b-toc": "overview", "b-summary": "overview",
      "b-efficacy": "efficacy", "b-longitudinal": "longitudinal-results", "b-safety": "safety",
      "b-matrix": "efficacy-safety-matrix", "b-baseline-overview": "baseline-overview",
      "b-demographics": "baseline-demographics", "b-disease-context": "baseline-disease-context",
      "b-severity": "baseline-severity", "b-disposition-overview": "disposition-overview",
      "b-flow": "participant-flow", "b-adherence": "adherence", "b-loss-exit": "loss-exit",
      "b-screen-failure": "screen-failure", "b-rescue": "rescue-treatment",
      "b-prohibited": "prohibited-medication", "b-deviation": "plan-deviation",
      "b-exposure": "trial-exposure-context", "b-subgroups": "subgroups-supporting-evidence",
      "b-profiles": "product-trial-profiles", "b-limitations": "evidence-limitations",
      "b-ending": "overview"
    },
    "C": {
      "c-cover": "overview", "c-toc": "overview", "c-summary": "overview",
      "c-design-map": "design-map", "c-population": "population-disease-definition",
      "c-inclusion": "inclusion-criteria", "c-exclusion": "exclusion-criteria",
      "c-arms": "treatment-arms", "c-endpoints": "endpoint-timepoint-matrix",
      "c-visits": "visit-duration-followup", "c-stats": "sample-analysis-statistics",
      "c-dossiers": "trial-profile", "c-identity": "trial-profile",
      "c-patterns": "design-patterns", "c-path-1": "design-patterns",
      "c-path-2": "design-patterns", "c-limitations": "evidence-limitations",
      "c-ending": "overview"
    }
  },
  "non_portal_responsibilities": {
    "A": ["evidence-limitations"],
    "B": ["evidence-limitations"],
    "C": []
  },
  "compatibility": {
    "C_second_path_slide_is_not_a_render_gate": true
  },
  "fail_close": {
    "B_missing_disease_context_domain": true,
    "B_missing_subgroup_rows": true,
    "B_longitudinal_only_week_24": true,
    "B_appoint_matrix_not_applicable": true,
    "C_min_design_paths": 1,
    "C_unique_best_forbidden": true,
    "A_easi75_literal_endpoint_forbidden": true
  }
}
```
