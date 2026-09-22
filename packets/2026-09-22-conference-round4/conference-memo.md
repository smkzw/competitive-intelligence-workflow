# 独立会商备忘录：Round-4 收包裁决与根因分析

- **日期**：2026-09-22
- **会商角色**：独立会商者（与生产会话 GLM/ZCode 主线程、五路测试者均无共享上下文）
- **工作目录**：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`
- **被测提交**：`f3ba4d3`（R01–R13 修复轮），产物 `runs/pnh-vertical/abc-v97/reports/`
- **输入证据**：
  - 三路科学复核 verdict：`runs/pnh-vertical/abc-v97/state/scientific_review/{A,B,C}/verdict.json`（A r43 六项 / B r57 三项 / C r41 七项，均 veto、均 recoverable）
  - 对抗测试：`runs/test-round4-grok/findings.json`（73 探针 62 过，F01–F09）
  - 用户旅程：`runs/test-round4-cursor/findings.json`（overall=fail，BI-01–05 + 5 项中文原生）
  - 交付载荷真值：`runs/pnh-vertical/abc-v97/state/derived/report-{a,b,c}-data.json`
  - 上游纠偏背景：`/tmp/ci_v96_review/CI_workflow_v96_review/REVIEW.md`（R01–R13 条）
- **复验方法（全部本轮实做，非转述）**：
  1. 对 `f3ba4d3` 源码直接跑函数级探针：`classify_safety_concept`、`build_atrisk_crosswalk.lookup`、`resolve_indication_id`、`validate_endpoint_timepoint_pairs`、`pdf_native.projections.a._matrix_points`、`ReportAPortalData.model_validate`；
  2. 对 v97 交付载荷做行级统计（519 条安全行 / 146 条 any_teae / 93 条缺分母人单位行等）；
  3. 用真实 Chromium 打开 `127.0.0.1:8799` 上的 v97 门户，读 DOM 与 ECharts 实例（非截图判读）；
  4. 用 v97 自己的 evidence CAS（2 个 CT.gov 原始页、435 条 atRisk 记录）复算 crosswalk 借用路径。

---

## 假设

1. **复验真值=代码+交付产物**。三份 verdict、两份 findings 一律只作线索；凡与其不符处，以本轮探针输出为准并显式标注（本备忘录已出现两处：A r43 issue-4 的「28 个互异事件标签」、A r43 issue-5 的「crosswalk 标题变体未命中」主因）。
2. **本会商不改任何产品代码、不重跑构建、不改封存证据**，只产出本备忘录与可复跑的探针命令。
3. **只有 `runs/pnh-vertical/abc-v97` 是本轮候选快照**；`abc-v96` 不存在于仓库。`packets/2026-09-11-pnh-vertical/*` 被当作 f3ba4d3 下的现行构建器源码（[INFERENCE]：仓库内无 abc-v97→构建脚本的显式映射；依据是该构建器产出物与 v97 载荷逐字段一致——`safe-334-declared`/`safe-336-declared` 影子行、`term_key` 词表、519 行计数均可对上；另一副本 `packets/2026-09-20-test-round-1/builders/*` 视为同族）。
4. **「已修复」的判据**：当前源码下原失败探针不再复现**且**交付产物中该现象不再出现；只改注释、只加旁路、只在别的报告修，不算。
5. `docs/specs/...-v1.3.md` 与用户后续决策优先于旧记忆；v2.0 仍是 draft，本轮裁决不引用它作为验收依据。
6. 排期区分三类归属：**R10 产品闭环主线**（共同 revision / query-ViewState / 局部重算 / 原子 publish / 静态分享）、**R2.4 GateSpec/blocker 闭包主线**（其 PRD 明确排除门户视觉重构、真实药智浏览器、PDF/PPT、RC）、**本轮新增**。

---

## 一、裁决表 A：对抗测试（grok-4.7，F01–F09）

| # | 发现 | 状态 | 复验证据（本轮实做） | 根因层 |
|---|---|---|---|---|
| **F01** | crosswalk 请求缺失期别时借用他人期别人数 | **成立（潜伏，当前产物 0 次触发）** | `src/ci_workflow/reports/b/safety_denominator_crosswalk.py:75-90`：请求期别无候选（`scoped=[]`）时**不返回 None**，直接落到 `if len(values)==1:` 分支，其条件 `len({e.period…})==1 or period is not None` 在「调用方给了 period」时恒真 → 返回单值。X07 复现 `value=10.0`（探针）。用 v97 CAS 435 条真实 atRisk 穷举：可请求期别组合中 **1757 次**请求不存在期别仍返回值；但产物中 270 个「有分母的 (arm,term_key) 组合」**实际借用 0 次**。 | **合同模型**：保守性条件写反（`period is not None` 被判为放行理由，本意应是「唯一候选的期别==请求期别」） |
| **F02** | 特定指标被收进总体键（因 AE 停药 / 治疗相关） | **成立（阻断级，已在交付物中显形）** | `safety_concepts.py:17-36` 规则顺序 = any_teae → any_sae → death → aesi → discontinuation_ae → treatment_related_ae → grade_3_plus。探针：「Discontinuation due to serious adverse events」→`any_sae`、「Treatment-related serious adverse events」→`any_sae`、「Incidence of TEAEs Leading to Treatment Discontinuation」→`any_teae`、「…(TEAEs) of Special Interest」→`any_teae`、「Percentage of Participants With Serious TEAEs」→`any_teae`。交付载荷：519 条安全行 `any_teae=146 / any_sae=174 / death=135 / generic_ae=61 / unknown=3`，**因不良事件停药、特别关注、治疗相关、3 级及以上均为 0 条**。 | **合同模型 + 政策数据**：`_CONCEPT_RULES` 优先级与模块自身 docstring（「总体与特定分开…特定指标不得自动归入 any 键」）互相矛盾；文件第 1-5 行的分类原则没有对应实现 |
| **F03** | `non-TEAE` 缩写未被否定 | **成立（同族，交付面影响低）** | 探针 `non-TEAE`→`any_teae`。`_NEGATION_PATTERNS`（`:38-42`）只含 non-serious / not-serious / non-treatment-emergent；`any_teae` 左边界 `(?<![a-z])` 不排除连字符。对照 `Non-treatment-emergent adverse events`→`unknown`（被整句剥离）、`nonTEAE`→`unknown`（左邻字母） | 合同模型（否定表不完备） |
| **F04** | 无标点并列句后半句被否定式吞掉 | **成立** | 探针 `Non-serious adverse events and serious adverse events`→`unknown`；`Non-serious adverse events`→`unknown`（未回落 generic_ae）。否定式 `[^;,.)]*` 在无分号/句点时吞到句尾 | 合同模型（否定边界） |
| **F05** | `no` / `without` 否定未识别 | **成立** | 探针 `No serious adverse events`→`any_sae`；`Participants without serious adverse events`→`any_sae` | 合同模型（否定表不完备） |
| **F06** | 显式 `tp1` 与查询 `TP1` 未归一 | **成立** | `safety_denominator_crosswalk.py:114` `period=row.get("period") or period_of(title)`：调用方给的 `period` **原样入库不做大小写归一**，而 `period_of()` 输出的是 `TP1`。X08 复现：`lookup(period='TP1')`→`None`，conflict 记 `ambiguous_candidates`，`values=[7.0,9.0]`——**把不匹配期别的 9.0 也写进冲突理由**。同类证据（真实产物）：`report-b-data.json` 中 `arm_id=nct04469465-arm-danicopan-danicopan-tp2` 与 `arm_id=nct04469465-arm-danicopan-tp1` 对 LTE 行互串 | **政策数据 + 合同模型**：期别是未归一的自由字符串，却参与精确相等判定 |
| **F07** | 空白时间点算已配对；只有时间点的试验不算孤儿 | **成立（守卫失效）** | `src/ci_workflow/reports/c/endpoint_instances.py:80` `timepoint_ids[…].add(str(oid))` 只记 `outcome_id`，不看 `source_text` 是否空白；`build_endpoint_instances` 却把空白文本折叠成 `timepoint=None`。E05 复现：空白时间点不抛错，实例 `timepoint: null`。E06 复现：仅含时间点观察的试验（`T-ORPHAN`）返回 `[]`——孤儿检查 `for trial_id, ids in endpoint_ids.items()`（`:99`）只在「该试验同时有终点」时才可达 | **合同模型**：配对判据用 id 存在性代替内容非空；孤儿检验的迭代域缺一个方向 |
| **F08** | `p-n-h` 被解析为规范 PNH | **成立（低危）** | `src/ci_workflow/reports/b/registry_observation.py:78-88`：`needle` 与 canonical 同时 `casefold()` + 去空格 + 去连字符后做全等比较 → `p-n-h`→`pnh`。规范 id / 别名（PNH、Ulcerative Colitis、IPF）解析正确 | **合同模型**：为「容错输入」把连字符当噪声删掉，等于允许任意连字符插入的伪 id |
| **F09** | 缺样本量显示 `n=null` | **成立** | `src/ci_workflow/renderers/portal/assets/report-a.js:1185`（与交付副本 `reports/A/v1/html/assets/report-a.js` 逐字节相同，本轮 diff 验证）`el("small","", trial.role+"｜"+trial.status+"｜n="+trial.sample_size)`，`sample_size=null` 时字面输出 `n=null`；同页展开表与证据抽屉同一事实写「未公开」 | **渲染器显示层**：内部字段直接参与拼接，未过披露状态词表 |

**合计**：F01–F09 全部成立，其中 **F02 是本轮唯一「已在交付物中显形且阻断科学复核」的对抗类发现**；F01 是高危但当前零触发；F03–F05 属同一张否定/优先级表的三个缺口；F06/F07 是守卫语义错误；F08/F09 是低危表达层。

---

## 二、裁决表 B：用户旅程（cursor，BI-01–05 + 中文原生）

| # | 发现 | 状态 | 复验证据（Chromium 实机 + 源码） | 根因层 |
|---|---|---|---|---|
| **BI-01** | 靶点/状态筛选只收缩卡片，不收缩「产品—机制分布」图 | **成立** | 实机：`product-overview.html` 点击「Factor B」后卡片 45→3、隐藏 42；机制分布图产品按钮 **34→34 不变**，`data-view-digest` 仍为 `全部产品`。源码：`report-a.js:707-714` `visibleProductNames()` **只读 `selected.product`**；`target`/`status` 仅在 `applyFilters`（`:1330-1360`）里以 DOM `hidden` 方式作用于 `[data-target]/[data-status]` 元素，而 `renderLandscape`（`:1120-1165`，`product-map` 与 `landscape` 共用）走 `visibleProductNames()` 重绘 | **渲染器显示层**：同一筛选条件存在两套实现（DOM 隐藏 vs 数据重绘），数据侧只认一个维度 |
| **BI-02** | A 试验行含 NCT 但不可点击 | **部分成立** | 实机：`products/iptacopan.html` 三个 NCT 单元格均为 `<td>`，整页 `a` 元素中含 NCT 文本者 **0**。但 A 报告**没有 `trials/` 目录**（B/C 有），不存在「死链」目标 → 应表述为「A 缺试验级入口，与 B/C 结构不一致」 | **产品范围/合同**：A 的信息架构未定义试验页，属 R10 主线范围（不是渲染 bug） |
| **BI-03** | B「观察时间」列出现整句英文登记原文 | **成立（但已被现有惯例标注）** | 载荷 8 行 `time_window` 为英文长句（如 `Adverse events were monitored continuously from Screening to Day 253…`）；浏览器实测该值同时出现在**筛选按钮**（`data-filter-value` 带「（登记原文，未译）」）与表格「观察时间」列。另有半译残留：「基线 （第1天） 至30天 末次给药后 研究 drug （约 2年）」「Duration 研究 （2年）」各 14/2 行 | **构建器投影**：叙事型观察窗转写覆盖不足；**渲染器**：把登记长句当作 facet 值直接展示 |
| **BI-04** | 图例英文臂名 vs 表格中文组别，且图例中文截断 | **成立** | 实机读 ECharts SVG：图例文本为 `Eculizumab`、`Danicopan-Danicopan`（登记原名），表格「组别」列为 `治疗组（依库珠单抗）`、`治疗组（Danicopan-Danicopan (TP2)）`、`治疗组（Danicopan （治疗期1））`。源码：表格取 `arm_detail`（`report_b.py:2180-2184`，经 `_native_text`），图例/`_arm_label` 走 `_decode_arm_identifier`（`:1759-1784`）与 `_B_VARIABLE_TOKENS`（`:1408`）——**同一条臂的三种写法由三条链路分别产生** | **渲染器显示层 + 构建器投影**：组名解码未单源；同一臂在「表/图/图例」不一致 |
| **BI-05** | A 安全性 TEAE 轴大量同句式英文标题堆叠 | **成立（是 A r43 issue-4 的表现形式）** | 实机读热图可见文本：`治疗中出现的不良事件（登记）｜OLTP: Number of Participants With Treatment-emergent Adverse Events…（登记原文，未译）6人6/6人`。事件列（`data-normalized-term`）只有 6 个互异值（见第三节 A issue-4） | **渲染器结构层**：单一受控标签承担区分职责，被迫用英文长句补足人类可读信息 |
| **CV-1** | A safety 热图观察窗/TEAE 标题英文残留 | **成立** | 同上；探针统计 `report-a-data.json` 安全行含英文 `time_window` 的行存在，且都带「（登记原文，未译）」 | 被标注的合规残留，非未标注泄漏 |
| **CV-2** | B「观察时间」列半译/英文 | **成立** | 见 BI-03 | 同 BI-03 |
| **CV-3** | B 图例/表格命名不一致 | **成立** | 见 BI-04 | 同 BI-04 |
| **CV-4** | C 证据抽屉时间点字段英文（`Day 0 and Day 28`） | **成立，但与既有惯例冲突** | C 页面对量表/内容英文一律附「（登记原文，未译）」（`trials/nct05886244.html` 内计数 14 处、`B/safety.html` 60 处）；抽屉时间点未统一套用该标注 | **渲染器**：标注惯例只在部分字段落地 |
| **CV-5** | B/C 试验标题用英文登记题名作主显示 | **部分成立** | C 的 `h1` 已是中文（`NCT05886244 试验档案 / 试验名称：eculizumab III期临床研究`）；B 的**试验筛选按钮**仍为整句英文登记题名且**未加**「（登记原文，未译）」 | 同 BI-03（facet 值未本地化、未标注） |

---

## 三、裁决表 C：三路科学复核（A r43 / B r57 / C r41）

### A r43（六项，均与安全域概念分层/矩阵相关）

| issue | 状态 | 复验证据 | 根因层 |
|---|---|---|---|
| **p1 特定指标被归入总体键（第 1 页来源）** | **成立（阻断）** | 载荷 `safe-412/413` = `Incidence of Treatment-emergent Adverse Events (TEAEs) of Special Interest`，`term_key=any_teae`、`category=治疗中出现的不良事件（登记）`；`safe-414/415` = `Incidence of TEAEs Leading to Treatment Discontinuation`，同样 `any_teae`。探针直证分类器：两者均 →`any_teae`（F02 同根） | 合同模型（规则优先级） |
| **p2 特定指标被归入总体键（第 2 页来源，规模更大）** | **成立（阻断）** | `safe-350` `…Serious Adverse Events (SAEs), Grade 3 And Grade 4 AEs, And Events Leading To Discontinuation…`→`any_sae`；`safe-401` `Percentage of Participants With Serious TEAEs`→`any_teae`；`safe-428` 合并测量行→`any_teae`。全站 `discontinuation_ae/aesi/treatment_related_ae/grade_3_plus` 计数 **0** | 同上 |
| **matrix TEAE 轴恒空且理由与证据相反** | **成立（阻断）** | 实机 `matrix.html` 默认轴（`任何TEAE发生率`）：气泡 **0**，覆盖文案「安全性轴：登记只有组别计数、没有可比较的发生率（%）」；切 `任何SAE发生率`：气泡 **16**。源码：`report-a.js:267` `if (!categoryName && termKey === "any_teae") categoryName = "治疗期间不良事件";`，随后 `:274` 以 `row.category.indexOf(categoryName) === -1` 过滤；载荷 category 是 `治疗中出现的不良事件（登记）`（`safety_concepts.py:47`）→ **0/146 命中**；SAE 分支（`:268`「严重不良事件」）恰好是载荷 category 的子串（174/174 命中）。载荷另有 15 条 `%`、118 条带 atRisk 的 any_teae 行，证明「没有可比较发生率」不成立 | 渲染器显示层（硬编码标签与事实层词表脱节） |
| **安全明细表未携带原测量标题，同名行不可区分** | **成立（阻断，但复核给出的计数不准确）** | 实机：517 行里 `data-normalized-term` **6 个互异值**；热图 `data-heat-event` 也是 **6 个**（不是 verdict 写的 28）。可见热图单元文本 265 种（含值/分母拼接）。真缺陷在重复行：**11 组**行的「产品/试验/组别/类别/事件」五列完全相同（最大 9 行，`eculizumab｜NCT00867932｜Eculizumab｜治疗中出现的不良事件（登记）｜治疗期间不良事件`），原始测量分别来自不同登记测量却不可见。载荷含 30 个互异 `term`，但表格列不取 `measure_label`：事件列渲染自 `templates/a/safety.html.j2:11`（`data-normalized-term="{{ row.term_label }}"`，即 `_safety_term_projection` 的受控标签），而 `measure_label` 仅用于热图（`report-a.js:883/896`）与摘要 | 渲染器显示层 + 构建器投影（受控标签与原始标题的可见性分工错误） |
| **分母未配对写成「未公开」（非阻断）** | **部分成立：结论成立，归因不完整** | 93 条人单位行无分母。复算：(a) **55 条是 `generic_ae`**——`safety_concepts.py:80-84 CONCEPT_ATRISK_STAT` 只映射 `any_sae/any_teae/death`，`generic_ae` 根本不查 crosswalk，于是 AE 模块已披露的 `otherNumAtRisk`（如 NCT02352493 各组 8/3/3…）被写成「未公开」；(b) 26 条 `any_sae` 且 `arm="rVA576"`，AE 模块该试验只有 1 个事件组 `rVA576 Coversin`（atRisk 15）→ 组名粒度/命名不一致导致的漏配，不是期别前缀问题；(c) 8 条 NCT03818607 的 `Period 1: X` 才是 `_base_title`（`:33-40` 不剥 `Period N:`）未命中的真实案例。全部 93 条中 **58 条可被同标题 `other` 类 atRisk 无歧义归属**（值均 ≤ 风险人数） | 构建器投影（映射表缺项）+ 政策数据（跨模块组名粒度不统一） |
| **同一组别两套命名（安全侧无组名解码，非阻断）** | **成立** | 载荷 519/519 行 `arm_detail` 为空；实机安全页组别列直接显示 `Eculizumab`、`ABP 959`（登记原名，未加「（登记原文，未译）」），而疗效页显示「依库珠单抗」 | 构建器投影（A 安全行未接 `_native_arm_detail_zh`） |

### B r57（三项）

| issue | 状态 | 复验证据 | 根因层 |
|---|---|---|---|
| **1 筛选面板分面半翻译/内部标识** | **成立（阻断）** | `report_b.py:3813-3856 _filter_value_label_zh` 是「剥前缀键 + 去尾拉丁串」的启发式：`re.sub(r"[A-Za-z0-9_.\-]+$","",text)` 只删**尾部**拉丁串，句中拉丁原样保留 → 实测 B 试验 facet 按钮为整句英文登记题名（未标注）；B 安全页时间 facet 为英文长句（已标注） | 渲染器显示层（用正则修补上游未给的字段，而不是要求事实层给中文标签） |
| **2 `-declared` 声明臂影子行与期间行重复计数** | **成立（阻断）** | `report-b-data.json` `safety_views.facts` 中 NCT04469465：`safe-334`（`Danicopan-Danicopan (TP2)`，3/55）与 `safe-334-declared`（`Danicopan-Danicopan`，3/55）并列；`safe-336`（`Placebo-Danicopan (TP2)`，6/27）与 `safe-336-declared`（6/27）并列。生产端在 `build_pnh_a_payload.py:670-680` 生成影子行（仅供 B 门匹配），A 渲染器 `report_a.py:501-503` 显式丢弃，**B 侧无对应过滤** → 影子行进入事实集并展示 | 构建器投影 + 合同模型：内部匹配键写进事实集，靠各消费方自行过滤；事实层没有 `provenance_role` 之类的归属标记（另注：`report_a.py:509-511` 是 `continue` 之后的死代码） |
| **3 B 把登记状态呈现为「当前状态：已批准上市」，无口径限定** | **成立（阻断）** | 实机/产物：`B/v1/html/products/eculizumab.html` `<dt>当前状态</dt><dd>已批准上市</dd>`，全 B 门户检索「监管批准」/「待核验」= 0；A 同产品页为 `当前状态（登记记录口径）` + 独立字段 `监管批准事实：待核验（监管原始文件未接入，登记状态不构成批准证据）` | 渲染器显示层（R11 的披露不变量只在 A 落地，未跨报告传播） |

### C r41（七项）

| issue | 状态 | 复验证据 | 根因层 |
|---|---|---|---|
| **1 安全性终点被改写为「疗效评价」** | **成立（阻断）** | `endpoint-timepoint-matrix.html:275` 值列为「不良事件疗效评价（2年）」；`:132` facet `Number and Type of Adverse Events (AE)` → 标签「不良事件疗效评价」。源码：`report_c.py:17` 复用 `report_a.py::_native_endpoint_zh`，其 `scale_patterns`（`report_a.py:887-950`）只有 `(r"adverse event","不良事件")`（`:949`）而无安全域分支，随后 `:985` form 兜底为 **「疗效评价」** → 拼成「不良事件疗效评价」 | 渲染器显示层（A 的通用译文函数被 C 当医学语义分类器复用；无域判定） |
| **2 免疫原性终点被改写为「其他临床疗效指标应答人数」** | **成立（阻断）** | `trials/nct05886244.html` 中 `Number of Participants With Treatment-emergent Antidrug Antibodies (ADAs) to Eculizumab` → 「其他临床疗效指标应答人数」；同页 21 处「其他临床疗效指标」。同源镜像：`overview.html`/`design-map.html`/`trial-profile.html` 各 5 处该标签 + 7 处「疗效评价」，`evidence-limitations.html`/`endpoint-timepoint-matrix.html` 各 4 处 + 5 处 | 同 issue-1：`_native_endpoint_zh:952` 默认 measure=「其他临床疗效指标」，无免疫原性/PK 族 |
| **3 「量表」列把 PNH 克隆大小标为「血红蛋白」** | **成立（阻断）** | 数据层直证：`report-c-data.json` 的 `obs-nct04469465-secondary_endpoint_definition-sec13`，`scale="血红蛋白"`，`source_text="Change From Baseline in Paroxysmal Nocturnal Hemoglobinuria (PNH) RBC Clone Size at Week 12"`。源码：`packets/2026-09-20-test-round-1/builders/build_pnh_c_audit.py:133-141 _endpoint_form()` 第一分支 `"hemoglobin" in folded` 无词边界 → 命中 **Hemoglobinuria**。同族：`report_a.py:929-932` 已为同一事故加了顺序注释（r21 修在渲染器，未修到构建器） | 构建器投影（子串阶梯无序、无词边界） |
| **4 「内容」列残留未译英文与半译中文、无单位时间点** | **成立（阻断）** | `endpoint-timepoint-matrix.html` 中 `>2 years<` 与同行「时间点」列「2年」并列；`trials/nct03181633.html` 有 2 处裸单元 `>Baseline up to Week 169<`，全站 0 处带「（登记原文，未译）」。同页英文原文在**量表列**是带标注的（14 处） | 构建器投影：同一登记字段在「值列（原文）」与「时间点列（转写）」被渲染两次，转写未覆盖 `*_endpoint_timepoint` 的值列 |
| **5 人群柱图口径自相矛盾且全为 1** | **成立（阻断）** | `report-c.js:827` 标题「人群标准结构比较（柱高为登记原文已记录的结构分组数，非标准条目总数）」，`:713` X 轴 `公开条目（条）`、`:708` tooltip「公开条目：N条（按试验聚合）」；`:684-699` 按试验 `count += 1` 聚合 → 该页每试验仅 1 行（登记最低年龄）→ 6 柱全为 1 | 渲染器显示层（标题/坐标轴/tooltip 三套口径；聚合语义与标题互斥） |
| **6 「签名」内部术语外泄** | **成立** | `design-patterns.html` 四条路径「适用前提」均含「同一签名内试验共享分组方式…」；源头为构建器硬编码：`packets/2026-09-20-test-round-1/builders/build_pnh_c_audit.py:391`（`packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py:556` 同文），非渲染器生成 | 政策数据/构建器（文案在生产端写死） |
| **7 游离/总 C5 两行仅靠序号区分（非阻断）** | **成立** | `row-…-sec2` 与 `-sec3` 的「内容」「时间点」两列逐字相同（实测），仅 `（登记定义2）/（登记定义3）` 与抽屉英文原文可区分 | 构建器投影（缺少可区分标签，靠序号兜底） |

---

## 四、根因分层（同族合并）

### 层 1｜政策数据：一张概念表被复制成四个词表，字面互不相同

同一安全概念在四处有四个字面值：

| 位置 | 字面 |
|---|---|
| 事实层（构建器写载荷） | `治疗中出现的不良事件（登记）`（`safety_concepts.py:47`） |
| A 明细表事件列 | `治疗期间不良事件`（`report_a.py:470`） |
| A 矩阵过滤内部常量 | `治疗期间不良事件`（`report-a.js:267`） |
| A 热图标签函数 | `任何TEAE`（`report-a.js:47`） |
| B 侧 | `任何治疗期间不良事件`（`report_b.py:605`）/`治疗期间不良事件`（`:1829`） |

后果不是「中文不好看」，而是**精确匹配失效**：`report-a.js:274` 用 `indexOf` 匹配 category，SAE 分支因「严重不良事件」是 `严重不良事件（登记）` 的子串而侥幸命中，TEAE 分支因两个字面互不为子串而 **0/146 命中** → 阻断级矩阵空态。同一根因在**原生 PDF** 上是静默坏死：`src/ci_workflow/renderers/pdf_native/projections/a.py:156`（及 `:225`）用 `row.get("category") == "治疗期间不良事件"` 过滤；本轮复算 `_matrix_points(report-a-data)` → **45/45 个点 `status_zh='未公开'`**，PDF A 的安全轴整列丢失且不报错。**这是本轮三路复核与两路测试都未覆盖的交付缺陷**（PDF 不在 round-4 测试面内）。

同族第二例：`report_a.py:306 required_safety = {"治疗期间不良事件","严重不良事件","特别关注不良事件","常见不良事件"}` 与载荷 category 集合（`…（登记）` 后缀 + `死亡病例（登记）`/`不良事件（登记）`）**无一相同**；同时生产者只产出 `暂无公开关键结果`/`已有部分公开结果`（`build_pnh_a_payload.py:313/876`），`有公开关键结果` 在该路径不可达 → 门禁双重失效。实测把任一产品置为 `有公开关键结果`，校验立即以「关键安全性维度不完整」报错——即门禁一旦复活就会用错误词表误杀。

### 层 2｜合同模型：保守性条件被写成放行条件

三个守卫的失败模式同构——「拿不到应有证据时，退化成接受更弱的证据」：

1. `safety_denominator_crosswalk.py:75-90`：请求期别无候选 → 借用单值（F01）。
2. `endpoint_instances.py:80 + :99`：配对只看 id 存在（F07/E05）、孤儿检验迭代域缺向（F07/E06）。
3. `safety_concepts.py:17-36`：总体键优先于特定键，使「无法确认归属」的读法只可能更粗、不可能更细（F02/F03/F04/F05）。

再加上 `registry_observation.py:78-88`（连字符归一 → 伪 id 通过，F08）与 `safety_denominator_crosswalk.py:114`（期别原样入库 → 大小写不等，F06），共同指向一个结构性约定缺失：**没有「身份/口径字段必须先归一化并被显式声明，未声明即拒绝」的统一前置**。

### 层 3｜构建器投影：同一个登记字段被两条链路各渲染一次，口径不同

- 同一 AE 组名在不同模块粒度不同（`rVA576` vs `rVA576 Coversin`；`Period 1: X`）→ 分母漏配 35/93（A r43 issue-5）。
- 同一登记时间字段：值列给原文、时间点列给转写（C issue-4）；同一观察窗在 A 安全行给了英文长句、在疗效行给了中文（BI-03/CV-2）。
- 同一臂名：`arm_detail`/`arm_label`/图例序列名三链路（BI-04），A 安全行 519/519 未解码（A r43 issue-6）。
- 同一测量标题：受控标签进事件列、原始标题只进热图（A issue-4）。
- `_endpoint_form` 子串阶梯与渲染器词典并行（C issue-3）。

合并结论：**「登记字段 → 展示字段」的投影没有单一入口，而是每个报告、每个页面各自投影一次**；因此每次修一处，其余同族位置保留旧口径（r21 修渲染器未修构建器就是实例）。

### 层 4｜渲染器显示层：内部产物与匹配键泄漏到用户面

- 影子行（内部 B 门匹配键）进入 B 事实集并展示（B issue-2）。
- `n=null`（F09）、`签名`（C issue-6）、`Period 1:`/英文长句作为 facet 值（B issue-1）、A 的 R11 披露不变量未跨报告传播（B issue-3）、`visibleProductNames()` 只认一个维度导致图不随筛选收缩（BI-01）。

四层不是并列关系：**层 1（词表分裂）制造了层 4 可见的错误；层 2（守卫失效）让层 3 的错误进入事实集且无告警**。因此本轮出现「修完一轮、同族在新页面复现」是结构性的，不是执行不力。

---

## 五、举一反三（IPF / 2 型糖尿病推演）

| 根因 | 在 IPF（FVC/6MWD/DLCO/急性加重）或糖尿病（HbA1c/低血糖事件/胰岛素用量）下的复现形态 | 结构性修法（一次性，非逐页补丁） |
|---|---|---|
| 概念词表分裂 | IPF 常用的「急性加重」既是疗效终点又是安全事件（AE of special interest）；词表再分裂一次，A/B/C/PDF/PPT 各自再写一套字面，**同类「精确匹配 0 命中」会第三次出现** | 单一 `concept_catalog`（key → {label_zh, label_short_zh, domain, atRisk_stat, families}），事实层写 key，展示层只消费 key；渲染器与构建器**禁止**再出现中文概念字面常量（可用 lint 扫描 `治疗期间不良事件`/`其他临床疗效指标` 等字面） |
| 总体键优先于特定键 | 糖尿病「低血糖事件」「严重低血糖」「夜间低血糖」会被 `adverse events?` 泛化规则整体收进总体键，伪造发生率 | 分类器改为「先判特定族（含否定与限定词），再回落总体」，并把「无法确认」建模成一等状态；为每个 new indication 加互测矩阵（甲适应症规则不得命中乙适应症语料） |
| crosswalk 期别借用 | IPF/糖尿病多见 双盲期→开放扩展期（TP1/TP2/LTE/OLTP），期别语义更强，借用后果从「数字错」升级为「不同暴露时长混算」 | 期别作为一等身份：入口归一化 + 未声明即拒绝；把 F01/F06 的负向用例固化为仓库测试 |
| 时间/值双链路投影 | IPF 的 `Baseline up to Week 52`、糖尿病 `Week 24` 会同样出现「值列英文、时间点列中文」 | 登记字段到展示字段的投影收敛为一个函数；加一条不变量测试：「同一 row 的值列与时间点列不得一个含 ≥3 拉丁词、另一个为纯中文」 |
| 组名多链路 | IPF 队列（`Cohort A/B`、`Part 1/2`）与糖尿病剂量组会产生同类三写法 | 组名解码单源 + 与图例同源（B r51/r55/r56 已提出同源要求但未覆盖 `arm_detail` 链路） |
| 影子行/内部键入事实集 | 新适应症的 B 门配对会再生成一批 `-declared` 行，若仍无归属标记，重复计数自动复现 | 影子行移出 `*_views.facts`，改为独立匹配索引，或在事实层加 `provenance_role` 并由渲染器统一过滤 |
| 柱图语义 | 糖尿病「公开人群条目」同样会按试验计数→全 1 | 图表 spec 必须声明「柱高=什么」，并由构建期校验该声明与聚合代码一致（口径一致性测试，而非视觉检查） |

**验收含义**：只要上述六项不落地，第 4 适应症的同类缺陷不是「可能发生」，而是**必然按同构方式发生**；因此在这些项落地前，不建议用「再跑一轮 reviewer 全 accepted」作为扩适应症的前置证据。

---

## 六、修复排期建议

排序原则：**阻断科学复核收敛 > 数据事实正确性 > 中文原生 > 交互观感**。规模：S ≤ 1 日，M ≈ 2–4 日，L ≥ 1 周。**归属列**标注该项是否已落在既有主线，避免重复排期。

| 序 | 项 | 建议动作 | 规模 | 验证方式 | 归属 |
|---|---|---|---|---|---|
| **1** | **特定/总体概念分层（F02/F03/F04/F05；A r43 p1/p2；C issue-1/2 的域判定部分）** | 重排/重写 `safety_concepts._CONCEPT_RULES`：否定先行（补 non-TEAE / no / without，修 `[^;,.)]*` 边界）→ 特定族（停药/治疗相关/3 级及以上/AESI）→ 总体族 → generic；`_CONCEPT_CATEGORY_ZH` 与 `CONCEPT_ATRISK_STAT` 补 `generic_ae`。C 侧 `_native_endpoint_zh` 增加域判定：安全域走安全族标签，禁止回落「疗效评价」。**先用探针表（S01–S21）与 519 行载荷红绿对照** | **M** | ① 探针：S20/S21/S05/S12/S14/S15 转 pass；② 载荷：`discontinuation_ae/aesi/treatment_related_ae/grade_3_plus` 由 0 变为非 0，且 `any_teae` 146→下降；③ A r43 p1/p2 逐行复核 | 本轮新增（R02 的收敛项，v96 只修了否定，未修优先级） |
| **2** | **概念词表单源化 + 禁用字面常量** | 建立 `concept_catalog`；渲染器/构建器一律按 key 取中文；`report-a.js:267`、`report_a.py:470`、`pdf_native/projections/a.py:156/225`、`html_ppt/projections/a.py:247`、`report_b.py:605/1829` 全部改为读 catalog 产物。同时修 `report_a.py:306 required_safety` 词表（改为按 catalog 的 `domain=safety` 且要求「产品有公开结果」时才生效的显式集合） | **M** | ① 矩阵页 TEAE 轴 ≥1 气泡（当前 0，SAE 16）；② `_matrix_points` 由 45/45「未公开」变为含可比点；③ lint：源码中不再出现这些中文概念字面（除 catalog 定义处） | 本轮新增（**含一个未报缺陷：PDF A 安全轴坏死**） |
| **3** | **守卫语义修正（F01/F06/F07）** | crosswalk：期别入口归一 + 「唯一候选期别==请求期别」才返回，其余返回 None；冲突理由只列请求期别候选。endpoint_instances：配对要求时间点文本非空；孤儿检验补「有 timepoint 观察但无 endpoint 集合」的迭代域。`resolve_indication_id` 取消连字符删除（F08） | **S–M** | ① X07/X08/E05/E06/R12 转 pass；② 435 条真实 atRisk 上「请求不存在期别返回值」由 1757 降为 0；③ 既有 31 项 invariant 测试不回归 | 本轮新增 |
| **4** | **影子行归属（B issue-2）** | `-declared` 影子行移出 `*_views.facts`（改为独立匹配索引），或事实层加 `provenance_role` 且由渲染器统一过滤；清理 `report_a.py:509-511` 死代码 | **S** | ① NCT04469465 卡片不再出现 3/55、6/27 各两次；② 全站 `-declared` 行数为 0（或全部带标记且不展示） | 本轮新增 |
| **5** | **R11 披露不变量跨报告（B issue-3）** | 把 A 的「当前状态（登记记录口径）」+「监管批准事实：待核验」模板抽为共享渲染片段，B/C 复用 | **S** | B/C 产品页含两个独立字段且检索「监管批准」非 0 | 本轮新增（R11 的跨报告收敛） |
| **6** | **登记字段投影单源（A issue-4/5/6；C issue-3/4/7；BI-03/CV-2）** | 建「登记字段 → 展示字段」单一投影：值列与时间点列同源转写；原始测量标题进明细表可区分列；`_endpoint_form` 与渲染器词典合并为一处（含词边界与顺序）；组名解码单源并与图例同源；`generic_ae`→`other`、单事件组允许名称变体归属、「无法归属」与「未公开」分列 | **M** | ① A 安全明细表 `data-normalized-term` 互异值由 6 升到 ≥ 原始测量数（30）；② 11 组全同列重复行降为 0；③ C 量表列 clone-size 行显示「PNH 克隆」类；④ 93 条缺分母行中 58 条获得分母，其余显示「无法归属」而非「未公开」 | 本轮新增 |
| **7** | **中文原生/内部术语（B issue-1；C issue-4/6；CV-4/5；F09）** | facet 值不再暴露登记长句/英文题名：给「中文短标签 + 原文入 aria/title/抽屉」；「签名」改为「设计要素组合」；`n=null` 走披露状态词表；标注惯例统一到所有含 ≥3 拉丁词的展示文本 | **M** | ① B 试验/时间 facet 按钮无整句英文（或均带标注）；② 全站 `n=null`/`签名`/裸 `2 years` 为 0；③ 抽样 20 个 facet 人工判读 | 本轮新增（B verdict issue-1 阻断项） |
| **8** | **ViewState 与图/筛选一致（BI-01）** | `visibleProductNames()` 纳入 `target/status/phase/region` 等全部产品维度（或统一改为「筛选状态对象 → 行谓词」单函数），使 DOM 隐藏与数据重绘同源 | **S–M** | 靶点/状态筛选后机制分布图产品按钮数与卡片数一致；`data-view-digest` 随筛选变化 | **R10 主线**（query/ViewState 属其合同），只需把本缺陷登记为 R10 的验收用例，不另行排期 |
| **9** | **A 试验级入口（BI-02）** | 产品决定 A 是否提供试验页；若提供，NCT 需可点击并落到试验档案 | **M** | A 内可从试验行到达试验语境 | **R10/产品范围**（先决策，不排在缺陷队列） |
| **10** | **人群柱图口径（C issue-5）** | 二选一：改为「设计定义对照表」或删图保表；若保留图，图题/坐标轴/tooltip 共享同一 spec 字段 | **S** | 三处口径字符串一致，且柱高分母与聚合代码同源 | 本轮新增（v96 审阅已提「全为 1 的柱图不应再美化」，此处为落地） |
| **11** | **B/C 构建器参数化与跨适应症组名/粒度对齐** | `IndicationProfile` 抽取（payload/CAS/source_id/query/severity 锚点/role set），并把跨模块组名对齐（AE 事件组 vs 疗效组）纳入构建期校验 | **L** | 新增适应症只加 profile，不改千行脚本；跨模块组名不一致在构建期报错 | 与 round-2 会商 #4 同项（未落地，继续沿用原排期） |
| **12** | **门禁复活（报告 A 安全性完整性）** | `required_safety` 与 catalog 同源；生产者给出 `有公开关键结果` 的真实可达路径 | **S** | 置 `有公开关键结果` 的产品在维度齐全时通过、缺维度时报出**正确**缺失项 | 本轮新增（与 #2 同批） |

**实施顺序（收敛路径）**：先 **1+2**（一次改动同时解锁 A r43 的两条阻断项、矩阵空态、PDF 静默坏死与 5 项对抗发现）→ 并行 **3**（用现有探针做红绿回归）→ **4+5+12**（S 级，可与 2 并行）→ **6+7**（事实层稳定后再动展示，避免粉饰错误行）→ **10** → **8/9 归入 R10 主线** → **11** 保持原排期。

**不重复排期的项**：R10（共同 revision / query-ViewState / 局部重算 / 原子 publish / 静态分享）与其 PRD 已排除项、R2.4（逐对象 GateSpec 与 blocker 闭包，明确排除门户视觉重构/真实药智浏览器/三宿主/PDF-PPT/监测/RC）。上表仅有两项落在这两条主线内（#8、#9），且均只需登记为对应用例。

---

## 七、复验命令备忘（本会商已执行，可复跑）

```bash
cd "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow"

# F02–F05：概念分层优先级与否定表
python3 -c "import sys;sys.path.insert(0,'src');from ci_workflow.reports.b.safety_concepts import classify_safety_concept as c;[print(repr(x),'->',c(x)) for x in ['Discontinuation due to serious adverse events','Treatment-related serious adverse events','Incidence of TEAEs Leading to Treatment Discontinuation','Incidence of Treatment-emergent Adverse Events (TEAEs) of Special Interest','Non-serious adverse events and serious adverse events','No serious adverse events','non-TEAE']]"

# F01/F06：crosswalk 期别借用与大小写
python3 -c "import sys;sys.path.insert(0,'src');from ci_workflow.reports.b.safety_denominator_crosswalk import build_atrisk_crosswalk as b;r=[{'title':'Drug','period':'TP1','stat':'serious','num_at_risk':10}];w=b(r);print(w.lookup(stat='serious',period='TP2',title='Drug'))"

# 载荷统计：总体键吞掉特定指标 / TEAE 单位与分母可得性
python3 -c "import json,collections;d=json.load(open('runs/pnh-vertical/abc-v97/state/derived/report-a-data.json'));print(collections.Counter((r['term_key'],r['category']) for r in d['safety']))"

# 交付矩阵与 PDF A 矩阵（PDF 为静默坏死的同一根因）
python3 -c "import json,sys;sys.path.insert(0,'src');d=json.load(open('runs/pnh-vertical/abc-v97/state/derived/report-a-data.json'));from ci_workflow.renderers.pdf_native.projections.a import _matrix_points as m;pts=m(d,{p['id']:p for p in d['products']},{t['id']:t for t in d['trials']});import collections;print(collections.Counter(p['status_zh'] for p in pts))"

# 门禁复活测试
python3 -c "import json,sys,copy;sys.path.insert(0,'src');from ci_workflow.renderers.portal.report_a import ReportAPortalData as M;d=json.load(open('runs/pnh-vertical/abc-v97/state/derived/report-a-data.json'));d2=copy.deepcopy(d);d2['products'][0]['result_status']='有公开关键结果';M.model_validate(d2)"
```

浏览器侧（本会商使用 Chromium，端口 8799 绑定 127.0.0.1，收尾已关闭）：`A/v1/html/matrix.html`（默认轴气泡 0 / SAE 轴 16）、`A/v1/html/product-overview.html`（靶点筛选后卡片 45→3、图按钮 34→34）、`A/v1/html/safety.html`（517 行 / 事件列 6 个互异值 / 11 组全同列重复行）、`B/v1/html/safety.html`（图例英文 vs 表格中文、观察时间英文长句）、`C/v1/html/population-disease-definition.html`。

---

## 八、一句话结论

Round-4 的两路测试与三路复核**没有误报**：grok 的 F01–F09 逐条成立、cursor 的 BI-01–05 与中文原生五项基本成立（仅 BI-02 的「死链」表述不准确，应为「A 缺试验级入口」），A/B/C 十六项复核中十五项成立、一项（A issue-5）结论成立而归因需改写；真正的问题不在这些发现本身，而在于它们**同出一源**——安全/终点/组名的概念词表在事实层与四个展示层各写一遍（字面互不相同），加上保守性守卫被写成放行条件，于是「TEAE 轴 0/146 命中」「特性指标塌缩为总体键」「影子行重复计数」这类缺陷每修一处就在另一页复现；按本备忘录顺序先做「概念词表单源 + 守卫语义」两项，即可一次解锁 A r43 两条阻断项、B issue-1/2/3、C 前五项中的大部分，并顺带修掉三路复核都未覆盖的两个静默缺陷——**原生 PDF A 的安全轴已整列坏死（45/45 点「未公开」）与报告 A 安全性完整性门禁因词表脱节而永不触发**。
