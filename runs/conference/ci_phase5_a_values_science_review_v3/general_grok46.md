I'll start from the assigned conference context and plan, then independently audit the 10 marketed-drug TEAE numbers against sources, NCT, dose, window, and arms.Context is loaded. Next I’ll pull the v3 research content, curated evidence, and the pre-fill audit so I can line-check NCT, dose, window, and arms.I’ll extract the new TEAE rows from the candidate JSON and the curated evidence list so I can check each drug against its source file.I have the 20 curated rows. I’ll extract the same records from `research-content.json` and read each bound source excerpt next.Candidate JSON hash does not match the conference digest, and placeholder “未公开” TEAE rows still sit beside the new values. I’ll verify each source excerpt and coverage counts next.Source files match their SHA256 bindings. I’ll now check how the report picks TEAE rows when both “未公开” placeholders and filled values exist.# Conference Participant Output: ci_phase5_a_values_science_review_v3 - general_grok46

## Boundary Check

- 工作目录：仓库根目录 `.`。未写文件、未改源码、未做科学审查接受、未做浏览器/视觉/PPT 终验。
- 已读：`context/ci_phase5_a_values_science_review_v3_conference_context.md`、`plans/codex_main_venue_ci_phase5_a_values_science_review_v3.md`、`.artifacts/a-values-matrix-fix-candidate-v3/research-content.json`、`fixtures/positive/a-atopic-dermatitis/curated-result-evidence.json`、对应 10 份本地来源摘录、`reviews/ci_phase5_a_values_matrix_fix_data_audit.md`、`docs/specs/competitive-intelligence-workflow-design-v1.2.md` §12.2、`src/ci_workflow/application/source_research_service.py` 门槛片段、`src/ci_workflow/reports/a/analysis.py` 安全性矩阵去歧义规则。
- 未读其他会商参与者正文；未检索外网；未打开生产路径。
- 身份核对：会议 Context 声称 candidate 摘要 `eb6684ad1bc32313c6af17ce174a4aaf34be46fdfb5e44c2eb88bd4fdc91b4d9`。磁盘实测 SHA-256 为 `d78b7c8b156554d8b23631ccc25d118f0475a37b52bf443ec3120d7e1eec9db7`（约 37.96 MB）。本复核绑定的是磁盘文件，不是 Context 摘要。
- `curated-result-evidence.json` 中 22 个 `content_file` 与声明 `content_sha256` 全部一致。10 个已上市新来源均已进入 candidate 的 `sources` 列表。
- 角色结论对 Codex 具建议性，不构成最终临床/监管/报告接受。

## Independent Work Product

### 审计对象

复核的是 A 类包中 **10 个已上市创新药、20 条治疗组/对照组总体不良事件新行**（不含克立硼罗、司普奇拜单抗的既有行）：

| 产品 | NCT / 试验 | 选用剂量 | 观察窗 | 治疗组 | 对照组 |
|---|---|---|---|---|---|
| 度普利尤单抗 | NCT02277743 SOLO 1 | 300 mg Q2W | 16 周双盲 | 167/229（73.0%） | 145/222（65.0%） |
| 曲罗芦单抗 | NCT03131648 ECZTRA 1 | 300 mg Q2W | 16 周初始双盲 | 460/602（76.4%） | 151/196（77.0%） |
| 来布利珠单抗 | NCT04146363 ADvocate 1 | 250 mg Q2W | 16 周诱导 | 128/282（45.4%） | 72/141（51.5%） |
| 奈莫利珠单抗 | NCT03985943 ARCADIA 1 | 30 mg Q4W + 背景外用 | 16 周初始双盲 | 306/616（50.0%） | 146/321（45.0%） |
| 阿布昔替尼 | NCT03349060 JADE MONO-1 | 200 mg QD | 12 周双盲 | 120/154（78.0%） | 44/77（57.0%） |
| 乌帕替尼 | NCT03569293 Measure Up 1 | 30 mg QD | 16 周双盲 | 209/285（73.3%） | 166/281（59.1%） |
| 巴瑞替尼 | NCT03334396 BREEZE-AD1 | 4 mg QD | 16 周双盲 | 58.0%（无 n/N） | 54.0%（无 n/N） |
| 芦可替尼乳膏 | NCT03745638 TRuE-AD1 | 1.5% BID | 8 周基质对照 | 74/253（29.2%） | 44/126（34.9%） |
| 他匹那罗夫 | NCT05014568 ADORING 1 | 1% QD | 8 周双盲 | 123/270（45.6%） | 35/137（25.5%） |
| 罗氟司特乳膏 | NCT04773587 INTEGUMENT-1 | 0.15% QD | 4 周双盲 | 92/433（21.2%） | 35/221（15.8%） |

这 20 行已写入 `report_data.safety`，并有对应 `facts`（`row_ref=safety:<row_id>`，`source_id` 齐全）。`report_data.safety` 本身不带 `source_id`；谱系只在 facts。`claims` 对上述新行计数为 0。

### 逐行来源核对（跨试验 / 跨剂量 / 跨时间窗）

**未发现把试验 A 的人数接到试验 B 的 NCT 上。** 双试验论文均只取与 NCT 对应的那一列：SOLO 1 非 SOLO 2，ECZTRA 1 非 2，ARCADIA 1 非 2，INTEGUMENT-1 非 2，TRuE-AD1 非 AD2，ADORING 1 非 2。Q2W/QW、15/30 mg、100/200 mg、1/2/4 mg 也没有把一臂人数接到另一臂百分比上。

行级判定：

1. **度普利尤单抗** — 摘录 Table 3：Q2W 167/229（73%）、安慰剂 145/222（65%）。NCT、剂量、16 周、组别一致。未误用 QW 150/218（69%）。
2. **曲罗芦单抗** — Table 6 ECZTRA 1：460/602（76.4%）、151/196（77.0%）。与 n/N 一位小数一致。
3. **来布利珠单抗** — 公司幻灯第 20 页：128/282（45.4%）、72/141（51.5%）。NCT/剂量/16 周/组别与摘录一致。**安慰剂 72/141 = 51.063…%，不是 51.5%。** 治疗组 45.4% 与 128/282 一致。
4. **奈莫利珠单抗** — 摘要 ARCADIA 1：306/616（50%）、146/321（45%）。NCT 与 ARCADIA 2 未混用。**306/616 = 49.7%，146/321 = 45.5%，与写入的 50.0 / 45.0 冲突。**
5. **阿布昔替尼** — 摘要：200 mg 120/154（78%）、安慰剂 44/77（57%）；100 mg 108/156 未写入默认行。12 周窗与来源一致。**120/154 = 77.9%，44/77 = 57.1%，与 78.0 / 57.0 冲突。**
6. **乌帕替尼** — CADTH 表 31：30 mg 209/285（73.3%）、安慰剂 166/281（59.1%），与 n/N 一致。15 mg 176/281（62.6%）未写入默认行。窗 16 周一致。来源是 HTA 表，不是 Measure Up 1 主论文。
7. **巴瑞替尼** — 综述摘录仅给 4 mg 58%、安慰剂 54%，明确“不反推分子”。NCT/4 mg/16 周/组别与摘录一致。**无分母。** 2 mg 同为 58%，默认选 4 mg。
8. **芦可替尼乳膏** — CADTH 表 17：74/253（29.2%）、44/126（34.9%），与 n/N 一致。8 周基质对照窗与来源一致。
9. **他匹那罗夫** — 系统评价表 2：123/270（45.6%）、35/137（25.5%），与 n/N 一致。行名是 **Any AEs**，被映射为 `任何TEAE`。来源不是 ADORING 1 主报告原文表。
10. **罗氟司特乳膏** — INTEGUMENT-1：92/433（21.2%）、35/221（15.8%），与 n/N 一致。**4 周**是该关键试验设计，不是误贴 16 周数字。

### 最高影响缺陷（本角色必须挑出的问题）

**缺陷 A（阻断晋升，不是数字抄错）：7/10 新产品在 candidate 中同时保留 CT.gov 占位“未公开”行和论文/审评“已公开”行。**

仍并存的产品：来布利珠单抗、奈莫利珠单抗、阿布昔替尼、乌帕替尼、巴瑞替尼、他匹那罗夫、罗氟司特乳膏。占位 facts 为 `disclosure_state=not_publicly_disclosed`，`source_id=ctgov-nct…`，`raw_value=None`。新行是另一 `row_id`。占位 **没有** `supersedes`。度普利尤单抗、曲罗芦单抗、芦可替尼乳膏无此占位。

`analysis.py` 对同一试验+组别只允许一条默认总体 TEAE；同一语境多条事实必须先消歧。占位窗是“主要对照期”，新行是 4/8/12/16 周具体窗，键可能不碰撞，因此 **既可能让热图继续吃空占位，也可能在 `matrix_default` 上直接门槛失败**。当前 `gate_status` 字符串为 `"passed"`，只说明内容包层通过，**不能**推断分析快照已消歧。

**缺陷 B（数值内部不一致，最严重的单格错误）：来布利珠单抗安慰剂 72/141 写成 51.5%。** 一位小数应为 51.1%。这不是期刊整数修约（那会是 51%），而是 n/N 与百分比对不上。

**缺陷 C（门槛合同）：巴瑞替尼 已公开 但无分母。** 设计 §12.2 要求成熟已出结果项目的安全性摘要含分母；`_assert_numeric_measure_valid` 同样要求已报告值有正分母。该行若进入分析快照，应按失败而不是热图可画点。

### 覆盖率 28/38、26/38、20/38 是否足以支持生成报告

磁盘计数（candidate `report_data`）：

- 任意疗效数值：28/38。无数值 10 个：杰克替尼、Bempikibart、Barzolvolimab、Lutikizumab、CM326、IBI356、SHR-1905、TQH2722、SKB575、ANB032。与会前审计名单一致。
- 任意安全性数值：26/38。无数值 12 个：上述 10 个 + Eblasakimab + APG777。
- 精确术语 `任何TEAE` 且治疗组有数：20/38。
- **双臂都有精确 `任何TEAE`：19/38。** `difamilast` 只有治疗组 72.3%（52 周成人开放标签），对照仍为未公开。所谓 20/38 **不是** 20 个可配对总体 TEAE。
- `startswith('任何TEAE')` 为 22/38，多出 Rezpegaldesleukin（不含注射部位反应）和 AK120（多剂量合并）。这两条被单独标记，未混进精确 20，这一区分是对的。

**结论：这三项分数不足以单独支持“可以生成 A 类正式报告”。**

理由（合同，不是口味）：

- §12.2 按产品成熟度逐项判断，禁止用总完成率掩盖缺口。`result_bearing` 触发后必须有可解释的核心疗效 **和** TEAE 或 SAE 摘要，且含组别、时间窗、分母。
- 10 个无疗效产品在包内多为 `暂无公开关键结果`。其中 **TQH2722、Bempikibart** 有检索/错 NCT 说明；其余 8 个在本清单里 **没有同等的双重穷尽记录**。早期项目允许显示“暂无公开结果”，但前提是穷尽后的真实状态，不是分数本身。
- Eblasakimab、APG777 的 TEAE `未公开` 附有“官方材料未给精确分组发生率”，这一条 **足以** 把缺失标成未公开而不是暂无记录，也 **不足以** 把它们当成已满足成熟项目安全性摘要。
- Rocatinlimab、Tezepelumab、Bermekimab、SHR-1819 仍是空占位，本轮没有补研说明。
- 20/38 还混入：**克立硼罗 CT.gov**（结局标题把 TEAE 与 SAE 写在同一 outcome，窗 Day 29/36 混合）；**司普奇拜单抗 71.3/66.3 无 n/N**，facts 的 URL 为 `https://cdn.most.gov.bd/image/6811f8ad5d179`，谱系不可信。这两条不在 10 药新行里，但会抬高 20/38。
- 7 个新产品的“未公开”占位未作废，报告层仍可能把已补的数显示成未公开，或因歧义无法出分析快照。

### 对初看起来“可补齐已上市 TEAE”的假设的反对

- 反对“10 个已上市药补上 20 行即可关闭总体 TEAE 缺口”：已上市实际是 **12** 个（另有克立硼罗、司普奇拜单抗）。10 行新数多数能对上摘录，但占位未取代、分母/修约/定义漂移未关。
- 反对“整数百分比可以连同精确 n/N 一起存成 x.0”：会把 49.7 显示成 50.0、45.5 显示成 45.0。热图一旦按 1 位小数渲染，就是错格。
- 反对“默认高剂量与疗效自动对齐”：乌帕替尼默认 30 mg（TEAE 73.3%，15 mg 仅 62.6%）；阿布昔替尼默认 200 mg；巴瑞替尼默认 4 mg，而疗效层同时有 2 mg EASI-75。设计禁止跨试验池化，**未禁止同一产品疗效 2 mg、安全性 4 mg 默认并排**。这是审稿人会抓的误导，不是抄数错误。
- 反对“观察窗不同只要格子上写了周数就可以并排比总体 TEAE”：4 周外用 21% 与 16 周系统药 73% 同轴，医学上不可比。标签存在不等于比较合法。
- 反对“`gate_status=passed` 等于可出正式报告”：内容包校验只要求已获批产品双臂有 `任何TEAE*` 数值；分析层还要分母、唯一默认矩阵记录、来源角色。两层合同不一致。

### 具体补救（给 Codex，不是自行改文件）

1. 用 `supersedes_fact_version_id` 作废 CT.gov `任何TEAE` 占位；每个试验+组别只留一条默认总体 TEAE。
2. 百分比政策二选一并全表执行：**(i)** 只展示来源原文整数/一位小数，n/N 另存且不强制反算相等；或 **(ii)** 一律由 n/N 算到 1 位小数。来布利珠单抗安慰剂在 (ii) 下必须改为 51.1，或改分母。
3. 巴瑞替尼改绑 BREEZE-AD1 主报告（PMID 31995838 一类）的 n/N；绑不上则保持未公开，禁止无分母“已公开”。
4. 乌帕替尼/阿布昔替尼/巴瑞替尼的默认疗效剂量与默认 TEAE 剂量锁定同一臂；15/100/2 mg 进细节层。
5. 他匹那罗夫若来源是 Any AEs，术语不要写成总体 TEAE，或换主报告 TEAE 表。
6. 20/38 重报为：精确术语双臂 19；治疗组 20（含地法米拉斯单臂）；若含 Rezpeg/AK120 变体则为 22。克立硼罗、司普奇拜单抗单独质控后再决定是否计入。
7. 10 个无疗效产品补双重穷尽说明，或维持门槛失败，不得靠 28/38 放行。

## Evidence And Assumptions

**Evidence（观察）**

- 磁盘 candidate SHA-256 `d78b7c8b…` ≠ Context `eb6684ad…`。
- 20 条新行的 n/N、NCT、剂量、窗、组别与本地摘录一致者：曲罗芦单抗、罗氟司特、乌帕替尼、芦可替尼、他匹那罗夫（人数），以及度普利尤单抗/阿布昔替尼/奈莫利珠单抗的 **n/N 和 NCT**（百分比另计）。
- 百分比与 n/N 一位小数不一致：来布利珠单抗安慰剂 51.5 vs 51.1；奈莫利珠单抗 50.0 vs 49.7、45.0 vs 45.5；阿布昔替尼 78.0 vs 77.9、57.0 vs 57.1；度普利尤单抗 73.0 vs 72.9、65.0 vs 65.3。
- 巴瑞替尼无 numerator/denominator；facts 原文写明未反推。
- 7 个产品占位 facts 仍为 `not_publicly_disclosed` + `ctgov-*`。
- 疗效 28/38、安全性 26/38 与会前审计名单一致；精确 `任何TEAE` 治疗组 20、双臂 19。
- `curated` 来源文件哈希 22/22 通过。
- 司普奇拜单抗 TEAE facts URL 指向孟加拉 MOST CDN 图。
- 克立硼罗 facts 原文是 CT.gov “Number of Participants With Treatment-Emergent Adverse Events (AEs) And Serious Adverse Events (SAEs)”，150/510 → 29.4%。

**Assumptions（推断）**

- 度普利尤单抗/阿布昔替尼/奈莫利珠单抗的整数百分比来自论文摘要/表的修约，不是跨表抄错。
- 来布利珠单抗 51.5% 更像幻灯或转写错误，不是标准整数修约。
- 高剂量默认是“与某条疗效口径联动”的产品决策，不是随机串剂量。
- 当前 `gate_status=passed` 未跑过 `build_efficacy_safety_summary` 的分母/唯一默认记录检查。

**Uncertainty**

- 未打开 NEJM/PMC/CADTH 原站；只核了仓库摘录。摘录本身若错，本复核不能发现。
- 未验证首页默认疗效臂是否已是 30 mg / 200 mg / 4 mg。
- 未验证 `matrix_default` 实际落在占位行还是新行。
- 未验证克立硼罗 CT.gov 该 outcome 是否就是总体 TEAE 人数。
- 未验证司普奇拜单抗 71.3/66.3 的真实文献。
- 巴瑞替尼主报告是否公开精确 n/N：本任务禁止外网，保持未知。

## Risks, Gaps, And Verification Needs

| 风险 | 为何重要 | 建议验证 |
|---|---|---|
| 对象摘要与磁盘文件不一致 | 可能审了错版本 | Codex 重算 SHA，确认 v3 冻结物 |
| 占位未取代 | 热图空值或分析门槛失败 | 查 `matrix_default` 与 fact 版本图 |
| 来布利珠单抗 51.5 vs 72/141 | 单格错误 | 对照 Almirall 第 20 页原图 |
| 巴瑞替尼无分母 | §12.2 / 分析层应失败 | 绑主报告或改回未公开 |
| 高剂量默认 | 已上市 JAK 的 TEAE 被抬高 | 与默认 EASI-75/IGA 臂对账 |
| 4/8/12/16 周同轴 | 安全性位置被外用短窗美化 | 默认矩阵是否强制同窗 |
| Any AE → 任何TEAE | 定义膨胀 | 他匹那罗夫主报告表 |
| 20/38 口径 | 双臂实为 19；混入克立硼罗/司普奇拜 | 重报分母 |
| 8 个无结果产品无穷尽记录 | 28/38 不能放行 | 补审计包或门槛失败 |
| 新行无 claims | 谱系只在 facts | 确认报告投影读 facts 还是 claims |
| 公司幻灯 / HTA / 综述 | 证据等级低于主报告 | 是否达到 A 类结果来源角色 |

**最重要反对、方案、决策点、给 Codex 的有界问题**

反对：把 v3 当作“已上市总体 TEAE 已关闭、可以生成报告”的科学通过稿。  
方案：先消歧占位、修来布利珠单抗安慰剂、补巴瑞替尼分母或降级披露状态，再重算覆盖率；28/26/20 不得当放行条件。  
决策点：百分比以原文还是以 n/N 为准；默认剂量用高剂量还是说明书常用剂量；A 类总体 TEAE 是否必须主报告而不能用 HTA/综述/幻灯。

给 Codex 的问题（会改变结论）：

1. 权威对象是 Context 的 `eb6684ad…` 还是磁盘 `d78b7c8b…`？若前者，本复核需重跑。
2. 占位 `not_publicly_disclosed` 是否必须 `superseded` 后才能出分析快照？
3. 无分母的“已公开”百分比是否允许进入 A 概览？
4. `result_bearing` 但 TEAE 明确未公开（Eblasakimab/APG777）是门槛失败，还是允许用 SAE/常见 AE 满足“TEAE **或** SAE”？
5. 20/38 的官方定义是治疗组有数，还是双臂配对？

**在 Codex 回答前的安全临时路径：** 不接受科学审查；不替换正式入口；不渲染以这些格子为权威的总体 TEAE 热图。内容包可继续当补数候选，但 7 个占位并存、来布利珠单抗安慰剂算术、巴瑞替尼无分母视为未关闭。

## Recommended Next Step

Codex 主会场应：**拒绝将本 v3 标为科学通过**；冻结并声明实际 SHA；只做占位取代 + 百分比/n/N 政策 + 巴瑞替尼分母（或降级）的定向修复后再开同一会话复核。在问题 1–5 未决前，覆盖率 28/38、26/38、20/38 **不够** 支持 A 类正式报告生成。本参与者输出为独立顾问意见，不是最终接受。
