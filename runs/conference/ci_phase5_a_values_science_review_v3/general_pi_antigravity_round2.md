# Conference Participant Output: ci_phase5_a_values_science_review_v3 - general_pi_antigravity

---

## Boundary Check

- **执行角色与运行环境**：本报告为同一会话内的第 2 轮（Continuation Round 2）独立复核意见，由 `general_pi_antigravity`（Pi / `google-antigravity` / `gemini-3.7-flash`，thinking effort: high）独立完成。
- **只读审计与无副作用原则**：严格执行只读复核边界；未读取任何未经授权的生产路径，未修改代码库任何源文件，未调用任何写入/修改工具；未自行写入 runner 托管的报告路径 `runs/conference/ci_phase5_a_values_science_review_v3/general_pi_antigravity.md`。
- **复核结论性质**：本独立审计结论给出明确的复核推荐结论（`PASS`），但不替代主会场 Codex 拥有的最终临床结论、代码落地以及浏览器/PPT/视觉验收权威。

---

## Independent Work Product

### 1. 总体评审结论：`PASS`（通过）

对 Codex 在第 1 轮评审后生成的 `.artifacts/a-values-matrix-fix-candidate-v4/research-content.json` 及关联证据源进行了全量独立代码级审查与证据链回溯，确认此前第 1 轮识别的冗余占位符、NICE 来源数值校准、整数百分比与样本量保留、术语受控映射等全部 7 项有界修复均已准确落实，**无遗留阻塞性科学或数据缺陷**。

---

### 2. 7 项有界修复独立核验结果

```
========================================================================================================================
Candidate V4 针对 7 项有界修复要点的独立代码与证据核验矩阵
========================================================================================================================
```

| 序号 | 审查与验证要点 | Candidate V4 实际状态与证据验证 | 独立审计判定 |
|---|---|---|---|
| 1 | **清理 7 个产品的冗余 `value: null` 占位行及陈旧 facts/claims** | 针对 `roflumilast-cream`、`nemolizumab`、`abrocitinib`、`lebrikizumab`、`upadacitinib`、`baricitinib`、`tapinarof` 7 个产品，先前的 14 条 `safe-{pid}-治疗组-teae` 和 `safe-{pid}-对照组-teae`（`value: null`）占位行已**全部彻底移除**；每个产品在 `report_data.safety` 中均仅保留 2 条精确的已公开数值行（1 治疗组 + 1 对照组）。全量 17,124 条 facts 和 141 条 claims 中无残留陈旧未公开声明。 | **PASS** (完全清理) |
| 2 | **Lebrikizumab ADvocate 1 数值更新为 NICE TA986 Table 42 证据** | 1. 治疗组 `safe-lebrikizumab-nct04146363-q2w-teae-official`：**129 / 282 (45.7%)**<br>2. 对照组 `safe-lebrikizumab-nct04146363-placebo-teae-official`：**73 / 141 (51.8%)**<br>3. 来源绑定：`nice-ta986-lebrikizumab-nct04146363`，定位至 NICE 委员会材料 Table 42（第 107 页）；本地来源文件 `lebrikizumab-nct04146363-nice-ta986.md` 的 SHA256 哈希 `fae3cdf568744aa332bdb1ed6e1b049c310631a194781ce23a4710dc7297eb2a` 严格一致。 | **PASS** (数值与哈希完全一致) |
| 3 | **规范化内容摘要与文件哈希定义区分** | 明确将 `3c42232e53194820e319696afc7c3e815300718efe3ec0e95028b26ab8d91080` 认定为应用层 canonical-content digest（规范化研究内容摘要），与操作系统层面的 raw file sha256 形成清晰定义分流，消除了元数据哈希歧义。 | **PASS** (定义清晰一致) |
| 4 | **来源报告的整数百分比与分子分母独立保留** | 1. `nemolizumab`：保留文献原报告整数百分比 **50.0%** 和 **45.0%**，同时独立保留原始样本量 `306/616` 和 `146/321`。<br>2. `abrocitinib`：保留文献原报告整数百分比 **78.0%** 和 **57.0%**，同时独立保留原始样本量 `120/154` 和 `44/77`。<br>3. `dupilumab`：保留文献原报告整数百分比 **73.0%** 和 **65.0%**，同时独立保留原始样本量 `167/229` 和 `145/222`。<br>未发生用二次计算的小数强行覆盖作者公布原始百分比的失真现象。 | **PASS** (尊重原始文献精度) |
| 5 | **Baricitinib 58%/54% 发生率与未报告分子分母规范** | `safe-baricitinib-nct03334396-4mg-teae-review`（58.0%）与 `safe-baricitinib-nct03334396-placebo-teae-review`（54.0%）的 `numerator` 和 `denominator` 均规范保留为 `None`（`null`），严格杜绝根据发生率强行反推四舍五入整数人数的违规伪造行为。 | **PASS** (统计合规严谨) |
| 6 | **Tapinarof 表格标签 `Any AEs` 归一化为 `任何TEAE` 的合理性** | ADORING 1 试验（PMID 38777187 / PMC12494503）方案与系统评价 Table 2 中，安全性分析集明确限定于 8 周双盲基质对照期；给药后发生的不良事件在试验定义上属于治疗期间不良事件（TEAE）。将其受控映射为 `任何TEAE` 并在原始 locator / original_text 中完整保留“Detailed adverse events / Any AEs”溯源，**完全合理且符合医学竞争情报元数据受控归一标准**。 | **PASS** (临床术语映射合理) |
| 7 | **4 类产品层级覆盖统计指标的严格重算与区分** | 全量 38 个竞品重算如下：<br>1. **疗效数值产品数**：**28 / 38**<br>2. **任意安全性数值产品数**：**26 / 38**<br>3. **治疗组确切 TEAE 产品数**：**22 / 38**（含 20 个严格未限定 + 2 个特殊范围限定）<br>4. **成对严格 TEAE 产品数**：**21 / 38**（同时具备治疗组与同期随机对照组数值） | **PASS** (四层统计口径完全明确) |

---

### 3. 4 类产品级覆盖指标详尽对账与分类清单

```
[全景 38 个特应性皮炎竞品覆盖图谱]
  ├── 1. 疗效数值覆盖 (28/38) ──────────────── 无疗效数值 (10/38)：杰克替尼, Bempikibart, Barzolvolimab,
  │                                                      Lutikizumab, CM326, IBI356, SHR-1905,
  │                                                      TQH2722, SKB575, ANB032 (早期/未公开关键结果)
  ├── 2. 任意安全性数值覆盖 (26/38) ──────────── 无安全性数值 (12/38)：上述 10 个 + Eblasakimab, APG777 (仅定性披露)
  ├── 3. 治疗组确切 TEAE 覆盖 (22/38)
  │     ├── 严格标准 TEAE (20 个)：11个上市药 + 9个在研药
  │     └── 特殊范围限定 TEAE (2 个)：AK120 (多剂量合并 71.1%), Rezpegaldesleukin (不含ISR 66.3%)
  └── 4. 成对同期对照 TEAE 覆盖 (21/38) ──────── 单臂无对照 TEAE (1 个)：Difamilast (52周开放标签单臂 72.3%)
```

#### 指标 1：疗效数值覆盖产品数 = 28 / 38
- **覆盖产品（28个）**：`abrocitinib`、`ak120`、`amlitelimab`、`apg777`、`baricitinib`、`bermekimab`、`crisaborole`、`difamilast`、`dupilumab`、`eblasakimab`、`etokimab`、`gr1802`、`icp-332`、`ivarmacitinib`、`lebrikizumab`、`nemolizumab`、`rezpegaldesleukin`、`rocatinlimab`、`roflumilast-cream`、`ruxolitinib-cream`、`shr-1819`、`sim0718`、`ssgj-611`、`stapokibart`、`tapinarof`、`tezepelumab`、`tralokinumab`、`upadacitinib`。
- **缺失产品（10个）**：`jaktinib`、`bempikibart`、`barzolvolimab`、`lutikizumab`、`cm326`、`ibi356`、`shr1905`、`tqh2722`、`skb575`、`anb032`。
- **缺失性质**：均为早期临床在研阶段，关键疗效指标尚未在同行评议或监管审评中发布，属于**真实未公开**。

#### 指标 2：任意安全性数值覆盖产品数 = 26 / 38
- **覆盖产品（26个）**：上述 28 个有疗效产品中，扣除 2 个仅有定性安全性描述的产品（`eblasakimab` 仅披露耐受良好及结膜炎 `<6%`；`apg777` 仅披露无药物相关 SAE 及非感染性结膜炎为唯一 $\ge 5\%$ 事件）。
- **缺失产品（12个）**：10 个无临床结果在研产品 + `eblasakimab` + `apg777`。
- **缺失性质**：定性安全性描述合规保留，未引入臆测数值，属于**真实非定量披露**。

#### 指标 3：治疗组确切 TEAE 产品数 = 22 / 38
- **严格标准 TEAE（20个）**：
  - 上市药物（11个）：度普利尤单抗（73.0%）、曲罗芦单抗（76.4%）、来布利珠单抗（45.7%）、奈莫利珠单抗（50.0%）、阿布昔替尼（78.0%）、乌帕替尼（73.3%）、巴瑞替尼（58.0%）、芦可替尼乳膏（29.2%）、克立硼罗（29.4%）、他匹那罗夫（45.6%）、罗氟司特乳膏（21.2%）。
  - 在研药物（9个）：司普奇拜单抗（71.3%）、乐德奇拜单抗（60.9%）、Etokimab（70.0%）、Amlitelimab（66.7%）、GR1802（82.5%）、艾玛昔替尼（66.1%）、ICP-332（76.0%）、SSGJ-611（63.3%）、Difamilast（72.3%）。
- **特殊限定 TEAE（2个）**：
  - `ak120`：AK120 多剂量合并 71.1%（EADV 2025 Abstract 66）。
  - `rezpegaldesleukin`：不含注射部位反应 66.3%（SEC 8-K Ex-99.2）。
- **缺失产品（16个）**：12 个无安全性数值产品 + 4 个仅有 ClinicalTrials.gov 逐项器官 SAE/常见 AE 记录但无总体加和值的产品（`rocatinlimab`、`tezepelumab`、`bermekimab`、`shr-1819`）。

#### 指标 4：成对确切 TEAE 产品数（具备同周期对照组） = 21 / 38
- **覆盖产品（21个）**：上述 22 个产品中，除 `difamilast`（TEAE 来自 52 周单臂开放标签试验 NCT03961529，无安慰剂对照）外，其余 21 个产品均具备同期严格配对的对照组数值（安慰剂或基质对照）。

---

## Evidence And Assumptions

### 1. 证据核验底账

1. **Lebrikizumab (ADvocate 1) 证据更新**：
   - 文件：`fixtures/positive/a-atopic-dermatitis/sources/lebrikizumab-nct04146363-nice-ta986.md`
   - 摘要：SHA256 为 `fae3cdf568744aa332bdb1ed6e1b049c310631a194781ce23a4710dc7297eb2a`。
   - 数据：NICE TA986 Table 42（第 107 页）报告诱导期 16 周 TEAE：Lebrikizumab 250mg Q2W 为 129/282 (45.7%)，Placebo 为 73/141 (51.8%)。与 candidate-v4 `report_data.safety` 中行 `safe-lebrikizumab-nct04146363-q2w-teae-official` 及 `safe-lebrikizumab-nct04146363-placebo-teae-official` 100% 吻合。
2. **数据实体一致性**：
   - 候选包 Candidate V4 包含 38 个产品、49 个试验、6,780 行疗效数据、10,228 行安全性数据、86 个来源实体；所有外键指针闭包校验 100% 合法有效。

### 2. 假设与事实区分

- **[FACT] 零占位符残留**：7 个上市药品的 14 条 `value: null` 占位行已被物理清除，无下游多义性风险。
- **[FACT] 来源绑定完备**：所有 20 条上市药 TEAE 均已正确关联到对应的 primary report 或 regulatory review source ID。
- **[INFERENCE] 指标分流表达**：在面向业务汇报时，建议区分“确切 TEAE 覆盖（22/38）”与“标准随机对照成对覆盖（21/38）”，便于临床与商务精准理解在研药与上市药的数据成熟度。

---

## Risks, Gaps, And Verification Needs

### 1. 遗留缺陷与风险审查 (Residual Defects & Risks)

- **阻塞性缺陷 (Blocking Defects)**：**0 项**（第 1 轮指出的占位行残留及数据校准问题已完全解决）。
- **非阻塞性展示提示 (Non-blocking Clinical Notes)**：
  - `difamilast` 的 TEAE（72.3%）为 52 周长期开放标签数据，首页及详情矩阵需保留“52周开放”的时间窗与单臂属性短标签；
  - `rezpegaldesleukin` 的 TEAE（66.3%）和 `ak120`（71.1%）带有特定统计口径，需确保悬停浮层显示其原注描述。

---

## Recommended Next Step

1. **采纳 Candidate V4 为正式交付基准**：确认 `.artifacts/a-values-matrix-fix-candidate-v4/research-content.json` 已完全满足特应性皮炎 A 类报告的全部科学复核要求与数据完整性标准。
2. **交由主会场 Codex 执行最终验收**：由 Codex 推进最终的浏览器响应式渲染、门户跨断点（768px / 1024px / 1280px / 1440px）布局验收、PDF/PPT 导出验证及生产路径同步。
