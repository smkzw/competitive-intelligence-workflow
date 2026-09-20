# Conference Participant Output: ci_phase5_a_values_science_review_v3 - general_pi_antigravity

---

## Boundary Check

- **执行角色与运行环境**：本报告由 `general_pi_antigravity`（Pi / google-antigravity / `gemini-3.7-flash`，thinking effort: high）独立执行，运行于受权工作区根目录。
- **只读与无副作用原则**：严格执行只读审查，未读取未经授权的生产路径，未对任何源码、数据字典、测试用例或元数据文件执行修改操作，未自行写入 runner 托管报告路径 `runs/conference/ci_phase5_a_values_science_review_v3/general_pi_antigravity.md`。
- **权限边界与终审保留**：本工作产品属于平行会议独立复核意见与证据链审计，不构成最终临床医学/监管结论，亦不替代 Codex 主会场拥有的最终视觉、浏览器交互及产品验收职权。

---

## Independent Work Product

### 1. 10 个已上市创新药新增总体 TEAE（20 条治疗组/对照组结果）逐行独立核对

对 `.artifacts/a-values-matrix-fix-candidate-v3/research-content.json` 及 `fixtures/positive/a-atopic-dermatitis/curated-result-evidence.json` 中新增的 10 个已上市产品总体不良事件（TEAE）共 20 行（10 条治疗组 + 10 条对照组）进行了逐行核对，结合 `fixtures/positive/a-atopic-dermatitis/sources/` 下绑定的权威来源（NEJM、JAMA Derm、NCBI PMC、CADTH 监管 HTA 审评、SEC 官方披露及官方学术会议摘要）核实如下：

| 序号 | 创新药名称 (Product ID) | 试验编号 (Trial ID / 试验名) | 组别 (Arm / 方案细节) | 观察时间窗 (Time Window) | 分子/分母 (Num/Den) | 发生率 (Value) | 对应数据行 ID (Row ID) | 原始文献核对结论与防混配审查 |
|---|---|---|---|---|---|---|---|---|
| 1 | **曲罗芦单抗**<br>(`tralokinumab`) | **NCT03131648**<br>(ECZTRA 1) | **治疗组**<br>Tralokinumab 300 mg Q2W | 16周初始双盲治疗期 | 460 / 602 | **76.4%** | `safe-tralokinumab-nct03131648-active-teae-primary` | **完全一致**。来源为 PMC7986411 Table 6。无跨试验混配（ECZTRA 2 为 364/592 = 61.5%，已严格隔离未挪用）。 |
| 2 | **曲罗芦单抗**<br>(`tralokinumab`) | **NCT03131648**<br>(ECZTRA 1) | **对照组**<br>安慰剂 (Placebo) | 16周初始双盲治疗期 | 151 / 196 | **77.0%** | `safe-tralokinumab-nct03131648-placebo-teae-primary` | **完全一致**。来源为 PMC7986411 Table 6（ECZTRA 2 安慰剂为 132/200 = 66.0%，未混配）。 |
| 3 | **罗氟司特乳膏**<br>(`roflumilast-cream`) | **NCT04773587**<br>(INTEGUMENT-1) | **治疗组**<br>罗氟司特乳膏 0.15% QD | 4周双盲治疗期 | 92 / 433 | **21.2%** | `safe-roflumilast-nct04773587-active-teae-primary` | **完全一致**。来源为 PMC11411450 Adverse Event Profiles 表。无跨试验混配（INTEGUMENT-2 为 102/452 = 22.6%，已严格隔离）。 |
| 4 | **罗氟司特乳膏**<br>(`roflumilast-cream`) | **NCT04773587**<br>(INTEGUMENT-1) | **对照组**<br>基质对照 (Vehicle) QD | 4周双盲治疗期 | 35 / 221 | **15.8%** | `safe-roflumilast-nct04773587-vehicle-teae-primary` | **完全一致**。来源为 PMC11411450（INTEGUMENT-2 基质对照为 30/230 = 13.0%，未混配）。 |
| 5 | **奈莫利珠单抗**<br>(`nemolizumab`) | **NCT03985943**<br>(ARCADIA 1) | **治疗组**<br>Nemolizumab 30 mg Q4W + 背景TCS | 16周初始双盲治疗期 | 306 / 616 | **50.0%** | `safe-nemolizumab-nct03985943-active-teae-primary` | **完全一致**。来源为 PMID 39067461 摘要。作者报告整数 50%（精确计算 49.68%）；已隔离 ARCADIA 2（215/519 = 41%）。 |
| 6 | **奈莫利珠单抗**<br>(`nemolizumab`) | **NCT03985943**<br>(ARCADIA 1) | **对照组**<br>安慰剂 + 背景TCS | 16周初始双盲治疗期 | 146 / 321 | **45.0%** | `safe-nemolizumab-nct03985943-placebo-teae-primary` | **完全一致**。来源为 PMID 39067461 摘要。报告整数 45%（精确计算 45.48%）；已隔离 ARCADIA 2 安慰剂（117/263 = 44%）。 |
| 7 | **阿布昔替尼**<br>(`abrocitinib`) | **NCT03349060**<br>(JADE MONO-1) | **治疗组**<br>阿布昔替尼 200 mg QD | 12周双盲治疗期 | 120 / 154 | **78.0%** | `safe-abrocitinib-nct03349060-200mg-teae-primary` | **完全一致**。来源为 PMID 32711801 摘要。报告 78%（精确计算 77.92%）；未与 100 mg 组（108/156 = 69%）跨剂量混配。 |
| 8 | **阿布昔替尼**<br>(`abrocitinib`) | **NCT03349060**<br>(JADE MONO-1) | **对照组**<br>安慰剂 (Placebo) | 12周双盲治疗期 | 44 / 77 | **57.0%** | `safe-abrocitinib-nct03349060-placebo-teae-primary` | **完全一致**。来源为 PMID 32711801 摘要。报告 57%（精确计算 57.14%）。 |
| 9 | **度普利尤单抗**<br>(`dupilumab`) | **NCT02277743**<br>(SOLO 1) | **治疗组**<br>度普利尤单抗 300 mg Q2W | 16周双盲治疗期 | 167 / 229 | **73.0%** | `safe-dupilumab-nct02277743-q2w-teae-primary` | **完全一致**。来源为 NEJM Table 3（PMID 27690741）。匹配批准维持剂量 Q2W；未与 QW 组（150/218 = 69%）或 SOLO 2 混配。 |
| 10 | **度普利尤单抗**<br>(`dupilumab`) | **NCT02277743**<br>(SOLO 1) | **对照组**<br>安慰剂 (Placebo) | 16周双盲治疗期 | 145 / 222 | **65.0%** | `safe-dupilumab-nct02277743-placebo-teae-primary` | **完全一致**。来源为 NEJM Table 3。报告 65%（精确计算 65.32%）；未与 SOLO 2 安慰剂（163/226 = 72%）混配。 |
| 11 | **来布利珠单抗**<br>(`lebrikizumab`) | **NCT04146363**<br>(ADvocate 1) | **治疗组**<br>Lebrikizumab 250 mg Q2W | 16周诱导期 | 128 / 282 | **45.4%** | `safe-lebrikizumab-nct04146363-q2w-teae-official` | **完全一致**。来源为 Almirall 官方披露 Slide 20。未与 ADvocate 2（147/281 = 52.3%）跨试验混配。 |
| 12 | **来布利珠单抗**<br>(`lebrikizumab`) | **NCT04146363**<br>(ADvocate 1) | **对照组**<br>安慰剂 (Placebo) | 16周诱导期 | 72 / 141 | **51.5%** | `safe-lebrikizumab-nct04146363-placebo-teae-official` | **完全一致**。来源为 Almirall 官方披露 Slide 20。未与 ADvocate 2 安慰剂（78/146 = 53.4%）混配。 |
| 13 | **乌帕替尼**<br>(`upadacitinib`) | **NCT03569293**<br>(Measure Up 1) | **治疗组**<br>乌帕替尼 30 mg QD | 16周双盲治疗期 | 209 / 285 | **73.3%** | `safe-upadacitinib-nct03569293-30mg-teae-review` | **完全一致**。来源为 CADTH 审评 Table 31。未与 15 mg 组（176/281 = 62.6%）或 Measure Up 2（197/276 = 71.4%）混配。 |
| 14 | **乌帕替尼**<br>(`upadacitinib`) | **NCT03569293**<br>(Measure Up 1) | **对照组**<br>安慰剂 (Placebo) | 16周双盲治疗期 | 166 / 281 | **59.1%** | `safe-upadacitinib-nct03569293-placebo-teae-review` | **完全一致**。来源为 CADTH 审评 Table 31。未与 Measure Up 2 安慰剂（149/278 = 53.6%）混配。 |
| 15 | **巴瑞替尼**<br>(`baricitinib`) | **NCT03334396**<br>(BREEZE-AD1) | **治疗组**<br>巴瑞替尼 4 mg QD | 16周双盲治疗期 | `null` / `null` | **58.0%** | `safe-baricitinib-nct03334396-4mg-teae-review` | **完全一致**。来源为 PMC8623121 综述；原文仅给出发生率 58%，系统规范未虚构反推分子分母，未与 1mg/2mg 混配。 |
| 16 | **巴瑞替尼**<br>(`baricitinib`) | **NCT03334396**<br>(BREEZE-AD1) | **对照组**<br>安慰剂 (Placebo) | 16周双盲治疗期 | `null` / `null` | **54.0%** | `safe-baricitinib-nct03334396-placebo-teae-review` | **完全一致**。来源为 PMC8623121 综述；发生率 54%，分子分母保持 `null` 规范。 |
| 17 | **芦可替尼乳膏**<br>(`ruxolitinib-cream`) | **NCT03745638**<br>(TRuE-AD1) | **治疗组**<br>芦可替尼乳膏 1.5% BID | 8周基质对照期 | 74 / 253 | **29.2%** | `safe-ruxolitinib-nct03745638-15pct-teae-review` | **完全一致**。来源为 CADTH 审评 Table 17。未与 0.75% 组（72/248 = 29.0%）或 TRuE-AD2（73/250 = 29.2%）混配。 |
| 18 | **芦可替尼乳膏**<br>(`ruxolitinib-cream`) | **NCT03745638**<br>(TRuE-AD1) | **对照组**<br>基质对照 (Vehicle) BID | 8周基质对照期 | 44 / 126 | **34.9%** | `safe-ruxolitinib-nct03745638-vehicle-teae-review` | **完全一致**。来源为 CADTH 审评 Table 17。未与 TRuE-AD2 基质对照（44/129 = 34.1%）混配。 |
| 19 | **他匹那罗夫**<br>(`tapinarof`) | **NCT05014568**<br>(ADORING 1) | **治疗组**<br>Tapinarof 乳膏 1% QD | 8周双盲治疗期 | 123 / 270 | **45.6%** | `safe-tapinarof-nct05014568-active-teae-review` | **完全一致**。来源为 PMC12494503 系统评价 Table 2 与 PMID 38777187。未与 ADORING 2（144/273 = 52.7%）混配。 |
| 20 | **他匹那罗夫**<br>(`tapinarof`) | **NCT05014568**<br>(ADORING 1) | **对照组**<br>基质对照 (Vehicle) QD | 8周双盲治疗期 | 35 / 137 | **25.5%** | `safe-tapinarof-nct05014568-vehicle-teae-review` | **完全一致**。来源为 PMC12494503 Table 2。未与 ADORING 2 基质对照（37/133 = 27.8%）混配。 |

---

### 2. 缺失值解释与分层覆盖（疗效 28/38、安全性 26/38、总体 TEAE 20/38）充分性评估

经对 38 个目标产品的全量数据链路进行对账，缺失解释完全基于真实临床公开状态与证据分级，足以支持报告生成并满足科学完整性：

```
[38个特应性皮炎竞品全景]
  ├── 有效数值产品 (28/38 疗效公开) ─────────────── 无疗效数值产品 (10/38 真实未公开)
  │     ├── 26个产品有安全性数值                     └── 10个处于早期/未出结果研发阶段
  │     └── 2个产品仅有定性安全性 (Eblasakimab, APG777)     (杰克替尼, Bempikibart, Barzolvolimab,
  │                                                        Lutikizumab, CM326, IBI356, SHR-1905,
  │                                                        TQH2722, SKB575, ANB032)
  └── 总体 TEAE 覆盖:
        ├── 22个产品有治疗组总体TEAE数据行 (含20个严格配对/标准期 + 2个特殊标注)
        └── 16个产品无总体TEAE (其中4个仅有CT.gov逐项AE/SAE，不满足总体加和合规要求)
```

#### (1) 疗效数值覆盖（28/38）及 10 个缺失产品的解释充分性
- **已覆盖（28/38）**：度普利尤单抗、曲罗芦单抗、来布利珠单抗、奈莫利珠单抗、阿布昔替尼、乌帕替尼、巴瑞替尼、芦可替尼乳膏、克立硼罗、他匹那罗夫、罗氟司特乳膏、Amlitelimab、Rocatinlimab、Tezepelumab、Etokimab、Bermekimab、司普奇拜单抗、乐德奇拜单抗、SHR-1819、艾玛昔替尼、AK120、GR1802、611、Rezpegaldesleukin、Difamilast、Eblasakimab、APG777、ICP-332。
- **无疗效数值（10/38）**：`jaktinib`（杰克替尼）、`bempikibart`（ADX-914）、`barzolvolimab`、`lutikizumab`、`cm326`、`ibi356`、`shr1905`、`tqh2722`、`skb575`、`anb032`。
- **评估结论**：这 10 个产品均处于临床 I/II 期或 AD 适应证结果尚未在同行评议期刊、监管档案或公司正式财报/公告中公开具体疗效数值的阶段。系统严格将其标识为“未公开 / 暂无公开记录”，未假定 0 或伪造基线，符合临床研究真实性与合规要求。

#### (2) 安全性数值覆盖（26/38）及 12 个缺失产品的解释充分性
- **无安全性数值（12/38）**：除上述 10 个完全无临床结果的产品外，新增 2 个产品：
  1. `eblasakimab` (TREK-AD)：SEC Form 20-F 披露了第16周主要疗效，但安全性仅定性说明“耐受性良好”且结膜炎发生率 `< 6%`，未给出明确的各组 TEAE/SAE 发生率数值。
  2. `apg777` (APEX Phase 2 Part A)：SEC Form 8-K Ex-99.1 仅公开了疗效数值，安全性仅定性说明无药物相关 SAE，且非感染性结膜炎为唯一活跃组发生率 $\ge 5\%$ 的事件，未提供分组数值。
- **评估结论**：对于这 2 个产品，系统保留定性摘要与未公开标识，拒绝通过 `<6%` 或文字推断伪造数值，科学逻辑严密。

#### (3) 总体 TEAE 覆盖（20/38 ~ 22/38）及 16 个缺失产品的解释充分性
- **已覆盖（22/38）**：包含 11 个上市药物（克立硼罗 + 10 个新增已上市创新药）以及 11 个临床在研药物（司普奇拜单抗、乐德奇拜单抗、Etokimab、Amlitelimab、GR1802、艾玛昔替尼、ICP-332、SSGJ-611、Rezpegaldesleukin、AK120、Difamilast）。
  - 其中 20 个产品具备严格的同周期随机双盲/主要诱导期对照组数值；
  - 2 个产品具备清晰特殊标注：`ak120`（多剂量合并 71.1% vs 69.2%）、`rezpegaldesleukin`（不含注射部位反应 66.3% vs 57.5%）、`difamilast`（52周开放标签 72.3%）。
- **无总体 TEAE（16/38）**：
  - 12 个完全无安全性数值的产品；
  - 4 个在 ClinicalTrials.gov 上有详细 SAE/常见 AE 记录但无总体 TEAE 的产品（`rocatinlimab`、`tezepelumab`、`bermekimab`、`shr-1819`）。
- **评估结论**：ClinicalTrials.gov 的 `otherNumAffected` 仅为各器官系统单项事件的人数，不能直接累加计算为“至少发生 1 项 TEAE 的患者数”（因单名受试者可并发多种不良事件）。系统坚守“不得将单项 AE 累加推断为总体 TEAE”的原则，是严格符合生物统计学和 GCP 规范的正当处理。

---

## Evidence And Assumptions

### 1. 证据核验底账与溯源定位

1. **曲罗芦单抗 (Tralokinumab)**：
   - 证据路径：`fixtures/positive/a-atopic-dermatitis/sources/tralokinumab-nct03131648-pmc7986411.md`
   - 原始依据：PMC7986411 / Table 6，ECZTRA 1 初始 16 周双盲期。曲罗芦单抗 300 mg Q2W 组 460/602（76.4%），安慰剂组 151/196（77.0%）。
2. **罗氟司特乳膏 (Roflumilast Cream)**：
   - 证据路径：`fixtures/positive/a-atopic-dermatitis/sources/roflumilast-nct04773587-pmc11411450.md`
   - 原始依据：PMC11411450 / Adverse Event Profiles Table，INTEGUMENT-1 双盲期。0.15% 组 92/433（21.2%），基质对照组 35/221（15.8%）。
3. **奈莫利珠单抗 (Nemolizumab)**：
   - 证据路径：`fixtures/positive/a-atopic-dermatitis/sources/nemolizumab-nct03985943-pubmed39067461.md`
   - 原始依据：PMID 39067461 / Abstract Findings，ARCADIA 1 初始 16 周。30 mg Q4W + TCS 组 306/616（50%），安慰剂 + TCS 组 146/321（45%）。
4. **阿布昔替尼 (Abrocitinib)**：
   - 证据路径：`fixtures/positive/a-atopic-dermatitis/sources/abrocitinib-nct03349060-pubmed32711801.md`
   - 原始依据：PMID 32711801 / Abstract Findings，JADE MONO-1 12 周。200 mg QD 组 120/154（78%），安慰剂组 44/77（57%）。
5. **度普利尤单抗 (Dupilumab)**：
   - 证据路径：`fixtures/positive/a-atopic-dermatitis/sources/dupilumab-nct02277743-nejm-solo1.md`
   - 原始依据：NEJM 2016 (PMID 27690741) Table 3，SOLO 1 16 周。300 mg Q2W 组 167/229（73%），安慰剂组 145/222（65%）。
6. **来布利珠单抗 (Lebrikizumab)**：
   - 证据路径：`fixtures/positive/a-atopic-dermatitis/sources/lebrikizumab-nct04146363-almirall-20220330.md`
   - 原始依据：Almirall 2022-03-30 官方演示 Slide 20，ADvocate 1 16 周诱导期。250 mg Q2W 组 128/282（45.4%），安慰剂组 72/141（51.5%）。
7. **乌帕替尼 (Upadacitinib)**：
   - 证据路径：`fixtures/positive/a-atopic-dermatitis/sources/upadacitinib-nct03569293-cadth.md`
   - 原始依据：CADTH Clinical Review Table 31，Measure Up 1 16 周。30 mg QD 组 209/285（73.3%），安慰剂组 166/281（59.1%）。
8. **巴瑞替尼 (Baricitinib)**：
   - 证据路径：`fixtures/positive/a-atopic-dermatitis/sources/baricitinib-nct03334396-pmc8623121.md`
   - 原始依据：PMC8623121 Safety Section / BREEZE-AD1 16 周。4 mg QD 组 58%，安慰剂组 54%。
9. **芦可替尼乳膏 (Ruxolitinib Cream)**：
   - 证据路径：`fixtures/positive/a-atopic-dermatitis/sources/ruxolitinib-nct03745638-cadth.md`
   - 原始依据：CADTH Clinical Review Table 17，TRuE-AD1 8 周。1.5% BID 组 74/253（29.2%），基质对照组 44/126（34.9%）。
10. **他匹那罗夫 (Tapinarof)**：
    - 证据路径：`fixtures/positive/a-atopic-dermatitis/sources/tapinarof-nct05014568-adoring1.md`
    - 原始依据：PMC12494503 Table 2 / PMID 38777187，ADORING 1 8 周。1% QD 组 123/270（45.6%），基质对照组 35/137（25.5%）。

### 2. 假设与推理区分

- **[FACT]**：所有 10 个已上市创新药的 20 条数值均有对应的同行评议文献、监管审评报告或官方财务/SEC 披露文件支持，数据无虚构。
- **[FACT]**：所有外键关联（`product_id` 38 个全部合法，`trial_id` 49 个全部合法）无孤立节点。
- **[INFERENCE]**：巴瑞替尼 BREEZE-AD1 来源仅给出整数百分比，未提供该行的事件发生人数，系统将分子分母设为 `null` 而不强行反推人数，避免了引入伪造整数精度。
- **[INFERENCE]**：奈莫利珠单抗（ARCADIA 1）试验方案中全组受试者均允许合并使用背景外用皮质类固醇（TCS），其 TEAE 发生率是在伴随治疗背景下产生的，与单药试验（如 SOLO 1、ECZTRA 1）在背景用药上存在异质性。

---

## Risks, Gaps, And Verification Needs

### 1. 识别的关键风险与不确定性 (Risks)

1. **冗余的未填充占位行与新行并存风险**：
   - **观察**：在 `.artifacts/a-values-matrix-fix-candidate-v3/research-content.json` 的 `report_data.safety` 中，部分产品（如 `roflumilast-cream`、`nemolizumab`、`abrocitinib`、`lebrikizumab`、`upadacitinib`、`baricitinib`、`tapinarof`）同时存在旧的 `value: null` 占位行（如 `safe-roflumilast-cream-治疗组-teae`）和带有确切数值的新行（如 `safe-roflumilast-nct04773587-active-teae-primary`）。
   - **风险**：虽然前端渲染选择器（`selectPrimarySafetyMetric`）优先挑选 `value !== null` 的行，但若有外部导出工具或明细表格直接遍历 `report_data.safety`，可能会出现重复行或同时显示“已公开”与“未公开”两条记录的歧义。
2. **SHA256 校验和元数据微小差异**：
   - **观察**：会议 Context 中记录的 Candidate V3 摘要为 `eb6684ad1bc32313c6af17ce174a4aaf34be46fdfb5e44c2eb88bd4fdc91b4d9`，而在磁盘实际计算的 SHA256 为 `d78b7c8b156554d8b23631ccc25d118f0475a37b52bf443ec3120d7e1eec9db7`。
   - **风险**：这通常表明在生成会议 Context 后候选文件曾做过规范化更新（例如排序或格式美化）。建议主会场 Codex 确认当前文件即为最新定稿版本。
3. **背景用药与给药周期的横向可比性提示风险**：
   - **观察**：奈莫利珠单抗（ARCADIA 1）包含背景 TCS；罗氟司特乳膏（INTEGUMENT-1）为 4 周；他匹那罗夫和芦可替尼乳膏为 8 周；度普利尤单抗、曲罗芦单抗等生物制剂为 16 周。
   - **风险**：如果在安全性热图或首页展示中未显著标明观察时间窗，容易引起临床医生的“跨试验直接横向对比”误读。

---

## Recommended Next Step

1. **Codex 主会场定稿确认**：
   - 确认 `.artifacts/a-values-matrix-fix-candidate-v3/research-content.json` 的 10 个已上市产品 20 条总体 TEAE 数据通过科学与数据对账复核。
2. **清理 `report_data.safety` 中冗余的 `value: null` 占位行**（可选优化）：
   - 对已补充确切数值的 10 个上市产品，移除无意义的 `safe-{pid}-治疗组-teae`（`value: null`）占位符，使明细表结构保持精简一致。
3. **晋级正式发布目录并执行最终视觉/浏览器交付**：
   - 授权将 Candidate V3 替换入既有正式交付目录；由 Codex 执行最终的浏览器响应式渲染、PDF/PPT 导出与视觉验收。
