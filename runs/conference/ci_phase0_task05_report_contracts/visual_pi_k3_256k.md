All evidence gathered. Anchors verified independently (11 passed / 64 passed, venv python 3.13 required — system python3.9 fails collection on `tomllib`). Now the full mapping and verdict.

# Conference Participant Output: ci_phase0_task05_report_contracts - visual_pi_k3_256k

**Verdict: VETO** — 8 项否决（每项含文件、字段、最小修复），2 个需 Codex 裁决的决策点，1 个有界问题。

## Boundary Check

- 仅读取授权范围：`AGENTS.md`、会议上下文、资料包、主会计划、设计书 §12–16 全文本（含被折叠的 §14.3–15.7，已补读）、`contracts/kangzhe/manifest.json`、3 个页面目录、4 个筛选合同、4 个格式合同、3 组新合同测试，并检查 `contracts/kangzhe/` 包内容。
- 未读取任何其他参与者输出；未修改任何项目文件；未写 `runs/conference/.../visual_pi_k3_256k.md`（本报告交 runner 持久化）。
- 非模型锚点独立复跑：`pytest tests/contract/test_{page_catalogs,filter_contracts,format_contracts}.py` → **11 passed**；全库 → **64 passed**（需 `.venv/bin/python`，3.13；系统 python3.9 因缺 `tomllib` 在 collection 阶段失败，锚点只能在项目 venv 复现——记录为环境事实）。
- 未做最终视觉/PPT/浏览器验收；Codex 保留最终权威。

## Independent Work Product

### 1. §12–16 → 合同字段 → 测试 逐项映射（通过项摘要）

| 设计书条款 | 合同字段 | 测试 | 判定 |
|---|---|---|---|
| §12.3 A 固定 11 页面族 | `page-catalogs/A.yaml` 11 pages + `selection_policy.top_n_allowed:false` | `EXPECTED_PAGES["A"]` 精确集合断言 | ✓ |
| §13.8 B 页面族（基线 4 页、完成情况 8 页为真实页面族） | `B.yaml` 21 pages、`navigation_group`、`disposition-overview.empty_numeric_fallback` | `test_b_catalog_keeps_baseline_and_disposition_as_real_pages` | ✓ |
| §14.4 C 固定 12 类 | `C.yaml` 12 pages | `EXPECTED_PAGES["C"]` | ✓ |
| §14.3 精确下钻（药物—试验—入排/评分—时间点） | `C.yaml` 页职责 + `filter-contracts/C.yaml` `criterion-family/scale-score/assessment-time/operator-threshold-unit` | `test_report_filters_cover_...` C 集合断言 | ✓ |
| §14.1/14.3 不止一条候选路径、无唯一最佳 | `C.yaml` design-patterns 职责"至少两条有证据依据的可选设计路径" | 仅文本存在（见 R-3） | △ |
| §15.4 分层筛选、空结果不扩大、重置分离、URL 状态 | `common.yaml state_contract`、各报告 `applicability` | 两个精确等值断言 | ✓ |
| §15.4 全部筛选多选 + 中文 label | 各 `filters[].multiselect/label/url_key` | 正则 `\u4e00-\u9fff` 断言 | ✓ |
| §15.5 抽屉同页右侧、保持筛选/滚动/焦点、键盘 | `common.yaml evidence_drawer` 3 个布尔 | `test_common_filters_...` | ✓ |
| §16.1 同快照、coverage_set/projection、未解释差异即失败、筛选导出独立产物 | 四格式 `source_contract` 7 字段 | 逐字段断言 | ✓ |
| §16.1/15.3 HTML/PDF 图后完整表、禁删表；PPT 删表须等价+回执 | `content_contract` 两组对立字段 | `test_html_pdf_keep_complete_tables_...` | ✓ |
| §16.2 HTML ≥2 物理页、双协议、禁远程资产 | `html.yaml runtime` | 等值断言 | ✓ |
| §16.4 1280×720、`S` 演讲者视图、150–300 字、禁站点截图 | `html-ppt.yaml runtime` | 等值断言 | ✓ |
| §16.5 PPT Master 九步串行、可编辑对象、禁图片页 | `pptx.yaml runtime.serial_steps` 全序列 | 列表精确等值 | ✓ |
| §15.2 无 A/B/C 内部标签、无中英夹杂 | 目录 YAML 全文禁用串 | `FORBIDDEN_COPY` + 标题规则 | △（见 R-2） |
| §16.6 设计合同冻结绑定 | 四格式 `design_contract.manifest` → 项目清单 | 等值断言 | △（见 Q-1） |

### 2. 否决项（每项：文件 → 字段 → 最小可执行修复）

**V-1（最高影响）§13.6 基线筛选维度缺"靶点"和"地区"。**
§13.6 原文："基线页至少支持产品、**靶点**、试验、队列、组别、**地区**、基线分析人群、变量域、变量、统计形式、量表/单位和披露状态多选"。
- 文件：`docs/architecture/filter-contracts/B.yaml`
- 字段：`filters`（全表无 `region` 定义）；`profiles.b-baseline / b-baseline-demographics / b-baseline-disease / b-baseline-severity`（均无 `target-mechanism`、无 `region`）
- 后果：医学经理无法按靶点或地区切基线人群——这是基线比较的核心旅程；机器合同却可全绿。
- 最小修复：B.yaml `filters` 增加 `{id: region, label: 国家与地区, url_key: region, multiselect: true, domains: [基线特征, 试验概览]}`；四个基线 profile 前置 `target-mechanism` 并加入 `region`；`test_filter_contracts.py` 增断言 `{"target-mechanism","region"} <= set(profiles["b-baseline"])`。

**V-2 §13.5 气泡矩阵可调维度缺"分析人群/事件/分母"。**
§13.5 原文："用户可改变疗效终点、效应形式、时间点、**分析人群**、安全性维度/**事件**/窗口/**分母**、气泡大小、产品、试验和靶点"。
- 文件：`docs/architecture/filter-contracts/B.yaml`
- 字段：`profiles.b-matrix`（缺 `analysis-population`、`ae-term-grade`、`denominator-role`）；`filters[denominator-role].domains` 为 `[试验完成情况, 安全性]`，不含 `疗效与安全性矩阵`，即使想引用也被自身 domain 声明挡住
- 最小修复：`b-matrix` 增加 `analysis-population、ae-term-grade、denominator-role`；`denominator-role.domains` 追加 `疗效与安全性矩阵`；测试断言该三键 ⊆ b-matrix。

**V-3 §13.7 完成情况多选维度缺"靶点"。**
§13.7 原文："允许按产品、**靶点**、试验、阶段/期间、组别、分析人群、字段族、原因、分母角色、时间窗、计量对象和披露状态多选"。
- 文件：`docs/architecture/filter-contracts/B.yaml`
- 字段：`profiles.b-disposition` 及 8 个子页 profile（`b-participant-flow` 等）均无 `target-mechanism`；`b-disposition` 同时建议核查 `analysis-population` 与 `disposition-population` 的概念分工（§13.7 用"分析人群"，合同用"完成情况统计人群"——可接受，但应在注释中锚定）
- 最小修复：`b-disposition` 及适用子 profile 加 `target-mechanism`；`REQUIRED_B_DISPOSITION` 增 `target-mechanism`。

**V-4 §15.5 基线/处置证据抽屉缺强制字段：规范字段族、统计形式/计量对象、原因原文/规范原因、互斥穷尽标记。**
§15.5 第二段强制：抽屉还须显示"规范变量/字段族、来源原名与定义、**统计形式或计量对象**、量表/版本/方向、分母角色及分子/分母、时间窗或基线时间定义、**原因原文/规范原因及互斥穷尽标记**、兼容规则/差异标签、缺失/披露状态"。
- 文件：`docs/architecture/filter-contracts/common.yaml`
- 字段：`evidence_drawer.fields` 16 项中无规范字段族、统计形式/计量对象、原因、互斥穷尽；`profiles.baseline-observation / trial-disposition` 同样缺
- 后果：§13.7"原因非互斥不得画 100% 堆叠图"依赖用户在抽屉看到互斥/穷尽标记；缺失即给假完成留门——堆叠图误用时无任何机器合同能拦截。
- 最小修复：`fields` 增加 `canonical-field-family`、`statistic-form-or-measurement-object`、`reason-original-canonical`、`reason-mutual-exclusivity` 四键；加入 `baseline-observation`（前三者中适用项）与 `trial-disposition`（全部四键）profile；`REQUIRED_DRAWER_FIELDS` 同步扩展。

**V-5 §15.7 确定性默认选择规则整体未冻结。**
§15.7："所有选择规则版本化并写入视图清单"，含锚定试验（明确禁止用疗效/安全性数值偏好）、首页终点族、常见 AE 行、基线变量顺序、完成情况固定字段序。三份目录仅冻结 `default_product_order`。
- 文件：`docs/architecture/page-catalogs/{A,B,C}.yaml`
- 字段：无 `selection_rules`/`view_manifest` 块；A 有 `anchor-trial` 筛选器却无默认锚定规则
- 后果：默认视图挑"最好看"的试验/终点是最高危的假完成向量，§15.7 专门为此前置禁止；合同零覆盖。
- 最小修复：每目录加版本化块，如 `selection_rules: {version: "1.0", anchor_trial: "注册角色>阶段>披露成熟度>稳定ID，禁用疗效/安全数值", endpoint_family: "…", common_ae_rows: "…", baseline_variable_order: "…", disposition_field_order: "…"}`（B 全填，A 填 anchor/endpoint/AE，C 可 `not_applicable`）；测试断言块存在、版本化且 A/B 的 `anchor_trial` 规则含"不使用疗效数值"语义锚串。

**V-6 §16.3 PDF 横向自动切换与书签未冻结。**
§16.3："宽表、森林图、纵向多系列、设计时间线和终点矩阵自动使用 A4 横向。横竖切换只能发生在分页边界，并保持书签、页码、页眉/页脚"。
- 文件：`docs/architecture/format-contracts/pdf.yaml`
- 字段：`runtime` 仅 `default_page: A4 纵向`；无横切规则、无书签字段；`verification` 无书签检查
- 后果：生成器把宽森林图缩进纵向页（缩字号假完成）仍可通过合同。
- 最小修复：`runtime` 加 `landscape_auto_switch: [宽表, 森林图, 纵向多系列, 设计时间线, 终点矩阵]`、`orientation_change_only_at_page_boundary: true`、`bookmarks_required: true`；`verification` 加"书签与页码正确"；测试逐字段断言。

**V-7 §16.4 HTML-PPT 视口验收矩阵与页码页型规则未冻结。**
§16.4："逐页视觉验收覆盖 1280×720、1920×1080、2048×1024 及用户实际最大化窗口"；"页码按合同页型规则显示，不能误加在封面、目录、章节首页或结束页"。
- 文件：`docs/architecture/format-contracts/html-ppt.yaml`
- 字段：`runtime` 无视口列表、无页码规则；`verification` 仅"逐页原分辨率视觉检查"
- 最小修复：`runtime` 加 `visual_acceptance_viewports: [1280×720, 1920×1080, 2048×1024, 用户实际最大化窗口]`、`page_number_excluded_page_types: [封面, 目录, 章节首页, 结束页]`；测试断言。

**V-8 §12.4/§13.5 气泡图轴向语义未冻结（TEAE 倒序标注 + 半径公式）。**
两节均强制："纵轴为原始 TEAE 发生率并倒序映射，明确标注'向上 = 发生率更低 = 观察到的安全性位置更有利'"，`r = k × sqrt(N/pi)`。
- 文件：`docs/architecture/page-catalogs/A.yaml`（`efficacy-safety-overview`）、`B.yaml`（`efficacy-safety-matrix`、`overview`）
- 字段：页面只有 `visuals: [疗效安全性气泡图]`，无轴向/标注/尺寸语义；`bubble-size` 筛选器存在但默认尺寸规则未冻结
- 后果：轴向画反（向上=更差）是医学解读级错误，纯视觉问题，合同不拦。
- 最小修复：在 A/B 相关页或公共块加 `bubble_chart_contract: {y_axis: 原始TEAE发生率倒序, y_axis_annotation: "向上 = 发生率更低 = 观察到的安全性位置更有利", x_axis_direction: 越右疗效信号越强, radius_formula: "r = k × sqrt(N/pi)", no_pooling: true, no_composite_score: true}`；测试断言标注原文。

### 3. 中文临床医学经理旅程复核

- 首页→完整比较下钻：三类均有门户+详情页、跨页 route、共享状态合同 ✓；但 V-5 意味着"首页第一眼看到什么"无确定性保证。
- 多选药物/试验/指标：全部 `multiselect: true` ✓。
- 空结果静默扩大：`empty_result: 保持当前范围并显示空状态，不自动扩大` + `no_auto_expand_on_empty` ✓ 双锚。
- 证据原位查看：右侧抽屉、保持筛选/滚动/焦点 ✓；但 V-4 使处置类证据的关键语义（互斥/穷尽、统计形式）在抽屉缺席。
- B 基线/完成情况、C 精确下钻：页面与下钻链完整；筛选维度缺口即 V-1/V-2/V-3。

## Evidence And Assumptions

**证据（直接观察）**
- 11 passed / 64 passed 亲自复跑（`.venv/bin/python`，4.05s）；系统 python3.9 collection 失败（缺 `tomllib`）。
- §13.6/§13.7/§13.5/§15.5/§15.7/§16.2–16.4 原文逐句比对合同字段，缺口如上 V-1…V-8，均给出原文引文。
- `contracts/kangzhe/` 磁盘实况：仅 `design.md` + `design_specs/`，**不存在** `design_share_v2.md` / `design_v2.md` 两个独立文件。

**假设**
- A-1：Task 0.5 的"机器合同完整反映 §12–16"意味着凡 §12–16 中可机器断言的强制性呈现/筛选/验收条款，都应在三类 YAML 或其测试中有锚点；纯实现期行为（如真实浏览器视口检查的执行）只需在合同 verification 清单中登记。
- A-2：§13.6 基线筛选列举中的"靶点、地区"为规范性最低集（"至少支持"），§15.4 为通用层，二者不冲突，§13.6 优先。

## Risks, Gaps, And Verification Needs

- **Q-1（有界问题，需 Codex 裁决）**：§16.6 要求包内原样保存 `design_share_v2.md`（SHA `113cc55f…`）与 `design_v2.md`（SHA `8d8dc9f6…`）双文件、`design.md` 固定解析到 share 版；实际包仅单 `design.md`（`fa30cea6…`），manifest `compatibility_stubs` 把 share/v2 两个名字都映射到上游入口哈希 `e513b4c5…`，而这两个文件在包内不存在。manifest 记录的用户指令（"内化为项目自己的 design spec，后续不用同步通用版"）按附录 D 优先级可覆盖冻结策略，但未显式授权放弃双文件/双摘要结构。**为何重要**：四份格式合同的 `design_contract` 全部指向该 manifest，若 §16.6 双文件义务仍有效，则当前绑定本身不完整。**安全 provisional 路径**：本轮不否决格式合同的 manifest 绑定（内部一致、测试通过），由 Codex 确认用户指令是否构成对 §16.6 双文件条款的显式修订；若否，单独开修复项。
- **R-1**：`FORBIDDEN_COPY` 仅 5 个手选禁用串、标题仅查 3 个模式。`GateSpec`、`prompt`、`覆盖率`、`检索次数` 等 §15.2 明禁词不在列。残留风险低（目录文本当前干净），但建议禁用表对齐 §15.2 全文枚举。
- **R-2**：§13.7 五态（未公开/来源未列示/技术不可用/不适用/明确为 0）到 §8.4 类型的确定性映射不在本轮工件中——属数据合同层，但 `disclosure-status` 筛选器的取值枚举无出处，后续数据合同落地时需回链，否则筛选值与状态矩阵可能分叉。
- **R-3**：C 的"至少两条候选路径、无唯一最佳"仅存在于职责文本，无机器锚（如 `design-patterns` 页加 `min_candidate_paths: 2`、`unique_recommendation_allowed: false`）。建议随 V-5 一并冻结。
- **R-4**：§16.2 HTML 生成后检查清单（链接、控制台、数据完整性、筛选联动、溢出、键盘、真实视觉）在 `html.yaml verification` 中只有 4 项；缺链接/控制台/溢出/键盘。未单列否决（runtime.accessibility 部分覆盖键盘），但建议与 V-7 同批补齐。
- **验证需求**：修复后复跑三组合同测试应仍全绿并新增 ≥8 条断言；全库 64→≥72 passed；Ruff 过三份测试文件。

## Recommended Next Step

1. Codex 裁决 Q-1（§16.6 双文件义务是否被用户冻结指令取代）。
2. 按 V-1…V-8 的最小修复补丁三类 YAML + 三份测试（全部为纯增量字段，无破坏性变更；V-1/V-2/V-3/V-4 可一个 commit，V-5/V-8 一个，V-6/V-7/R-3/R-4 一个）。
3. 修复后由我或另一独立上下文复核缺口清单归零，再进入下一轮会议验收。
