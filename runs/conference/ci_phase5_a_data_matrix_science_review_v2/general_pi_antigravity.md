# Conference Participant Output: ci_phase5_a_data_matrix_science_review_v2 - general_pi_antigravity

## Boundary Check

- **Authorized Working Directory**: 复核在授权工作区根目录（`.`）下独立执行，未读取或修改任何生产环境未授权路径。
- **Source Read/Edit Policy**: 严格遵守只读审阅原则，未对项目源码、测试文件或底层数据资产做任何未经授权的修改。
- **Runner-Managed Output Artifact**: 未调用文件写入工具生成报告路径 `runs/conference/ci_phase5_a_data_matrix_science_review_v2/general_pi_antigravity.md`，完整成果由 Runner/Codex 统一持久化。
- **Acceptance Scope**: 保持独立科学审计与证据链核查角色，输出明确的【接受 (ACCEPT)】复核结论及逐项证据清单；UI 实机渲染与最终交付验收归主会场 Codex。

---

## Independent Work Product

### 1. 核心复核结论与全景指标

**独立科学复核结论：【接受 (ACCEPT)】**

对特应性皮炎 A 类报告候选数据包 `cae2c3383b04b1987e51d675a21a13e99a9ed8f03718f0704e4cb09356a78f74`（对应 `.artifacts/a-data-matrix-recheck-candidate/research-content.json`）执行全面独立审计，确认该候选包彻底解决了上一阶段遗留的产品覆盖缺口、试验身份错配、跨试验混配风险及未量化定性推断等缺陷，满足高标准交付要求：

- **内容摘要（Digest）**：`cae2c3383b04b1987e51d675a21a13e99a9ed8f03718f0704e4cb09356a78f74`
- **候选文件**：`.artifacts/a-data-matrix-recheck-candidate/research-content.json`（文件大小 37,855,122 字节）
- **核心数据规模**：
  - 竞品产品（Products）：**38** 个
  - 临床试验（Trials）：**48** 项
  - 证据来源（Sources）：**74** 个
  - 结构化事实（Facts）：**17,107** 条
  - 科学声明（Claims）：**120** 条
  - 疗效数据行（Efficacy）：**6,780** 条
  - 安全性数据行（Safety）：**10,221** 条
- **产品结果状态分布（三态分流）**：
  - **有公开关键结果**：**25** 个（均包含双组疗效及安全性可比数值）
  - **已有部分公开结果**：**3** 个（疗效有量化对照，安全性未完整量化或跨设计，严格隔离）
  - **暂无公开关键结果**：**10** 个（具备多源检索闭环回执，确认无可用结果，保留空值）

---

### 2. 重点复核产品逐项事实核对矩阵

| 产品 ID / 名称 | 试验编号 / 阶段 / 样本量 | 来源凭证与取得方式 (SHA-256) | 疗效数值（治疗组 vs 对照组） | 安全性数值（治疗组 vs 对照组） | 公开状态 | 边界与隔离核验结论 |
|---|---|---|---|---|---|---|
| **GR1802** | `chictr2100051917`<br>(II期, N=120) | Wiley 期刊恢复摘录<br>`DOI: 10.1155/dth/6903760`<br>Hash: `695860ce...49c6` | 第16周 EASI-75:<br>**75.0%** (30/40) vs **32.5%** (13/40) | 任何 TEAE: **82.5%** (33/40) vs **85.0%** (34/40)<br>任何 SAE: **0.0%** (0/40) vs **10.0%** (4/40)<br>上呼吸道感染: **12.5%** (5/40) | 有公开关键结果 | **核验通过**。配对严密，分子分母齐备。未拆分 AESI 保持 `未公开` (`None`)，无外推。 |
| **611 (SSGJ-611)** | `nct05544591`<br>(II期, N=93) | PMC 原文 XML<br>`PMID: 40057938`<br>Hash: `4ae18e47...79db` | 第16周 EASI-75:<br>**60.0%** (18/30) vs **15.6%** (5/32) | 任何 TEAE: **63.3%** (19/30) vs **65.6%** (21/32)<br>任何 SAE: **3.3%** (1/30) vs **0.0%** (0/32)<br>上呼吸道感染: **6.7%** (2/30) | 有公开关键结果 | **核验通过**。纠正原包仅保留 III 期招募中试验的缺陷；II 期数据与 PMC 原文表完全一致。 |
| **艾玛昔替尼 (Ivarmacitinib)** | `nct04875169`<br>(III期, N=336) | JAMA Dermatology / PMC XML<br>`PMID: 40305055`<br>Hash: `b8b4fbe2...0363` | 第16周 EASI-75:<br>**66.1%** (74/112) vs **21.6%** (24/111) | 任何 TEAE: **66.1%** (74/112) vs **64.9%** (72/111)<br>任何 SAE: **1.8%** (2/112) vs **2.7%** (3/111) | 有公开关键结果 | **核验通过**。纠正原包漏投影 III 期结果缺陷；常见 AE 谱未在摘要拆分部分如实标记为 `未公开`。 |
| **ICP-332** | `nct05702268`<br>(II期, N=75) | JAMA Dermatology / PubMed XML<br>`PMID: 41533373`<br>Hash: `c17786f2...0828` | 第4周 EASI-75:<br>**64.0%** (16/25) vs **8.0%** (2/25) | 任何 TEAE: **76.0%** (19/25) vs **68.0%** (17/25)<br>血纤维蛋白原降低: **44.0%** (6/25) | 有公开关键结果 | **核验通过**。守住证据边界：原文虽述“均为轻中度”，但未单列 SAE 数据，SAE 严格记为 `未公开`，不臆测 SAE=0。 |
| **Rezpegaldesleukin** | `nct06136741`<br>(IIb期, N=396) | SEC 2025-09-18 Form 8-K<br>Exhibit 99.1/99.2 存档<br>Hash: `d4750e38...ec51` | 第16周 EASI-75:<br>**42.0%** vs **17.0%** (24µg/kg vs 安慰剂) | 任何 TEAE（不含注射部位反应）: **66.3%** vs **57.5%**<br>任何 SAE: **1.0%** vs **0.0%**<br>鼻咽炎: **9.6%** vs **13.7%**<br>头痛: **7.7%** vs **4.1%** | 有公开关键结果 | **核验通过**。TEAE 术语明确限定为“不含注射部位反应”，口径与 SEC 原表严格对应，杜绝混淆。 |
| **AK120** | `nct06035354`<br>(Ib/II期, N=427) | EADV 2025 Congress<br>Abstract 66 原 PDF<br>Hash: `b231ff61...26e6` | 第16周 EASI-75:<br>**57.5%** (23/40) vs **28.2%** (11/39) | 安慰剂对照期 TEAE: **71.1%** vs **69.2%**<br>高尿酸血症: **8.3%** (13/156)<br>上感: **5.8%** (9/156) | 有公开关键结果 | **核验通过**。闭合 II 期试验身份；全试验 9 例 SAE 因未按组拆分，SAE 字段如实保持 `未公开`。 |
| **Eblasakimab** | `nct05158023`<br>(IIb期, N=302) | ASLAN 2023 Form 20-F<br>SEC 官方存档<br>Hash: `f7dbeea2...04f5` | 第16周 EASI-75:<br>**52.0%** vs **24.0%** (600mg vs 安慰剂) | 任何 TEAE / SAE / 结膜炎: **未公开** | 已有部分公开结果 | **核验通过**。疗效数据完整；官方文档仅定性表述“耐受良好/结膜炎<6%”，无分组精确数值，安全性标记未公开。 |
| **APG777** | `nct06395948`<br>(II期, N=470) | Apogee 2025-08-11 8-K<br>Exhibit 99.1 存档<br>Hash: `3f038f42...bcf7` | 第16周 EASI 改善: **71.0%** vs **33.8%**<br>EASI-75: **66.9%** vs **24.6%**<br>vIGA 0/1: **34.9%** vs **17.3%**<br>EASI-90: **33.9%** vs **14.7%** | 任何 TEAE / SAE / 结膜炎: **未公开** | 已有部分公开结果 | **核验通过**。疗效四终点数值齐备；Topline 安全性未给出组别百分比，严格标注 `未公开`，不造假数据。 |
| **Difamilast** | `pmid34710557` (RCT)<br>`nct03961529` (单臂52周) | PubMed<br>`PMID: 34710557 / 35716332`<br>Hash: `b5049ea2...0d0a` | 第4周 IGA: **38.46%** vs **12.64%**<br>第52周 EASI-75: **55.4%** | 52周开放标签 TEAE: **72.3%** (120/166)<br>治疗相关 AE: **8.4%** (14/166) | 已有部分公开结果 | **核验通过**。严格分立两项试验，4周 RCT 疗效与52周单臂安全性各自独立，矩阵图禁止跨试验混配。 |
| **Bempikibart** | `nct05509023`<br>(II期, N=102) | ClinicalTrials.gov API v2<br>Hash: `267d1492...a1aa` | 暂无数值结果 | 暂无数值结果 | 暂无公开关键结果 | **核验通过**。彻底剔除误绑的斑秃试验（NCT06018428），修正为 AD 试验（NCT05509023），客观保留空值。 |

---

### 3. 38 个竞品产品全景状态分布及检索闭环证据

- **【有公开关键结果】（25 个产品）**：
  `dupilumab`、`tralokinumab`、`lebrikizumab`、`nemolizumab`、`abrocitinib`、`upadacitinib`、`baricitinib`、`ruxolitinib-cream`、`crisaborole`、`tapinarof`、`roflumilast-cream`、`amlitelimab`、`rocatinlimab`、`tezepelumab`、`etokimab`、`bermekimab`、`stapokibart`、`sim0718`、`shr-1819`、`ivarmacitinib`、`ak120`、`gr1802`、`ssgj-611`、`rezpegaldesleukin`、`icp-332`。
  *验证结果*：25 个产品均在同一试验内闭合了双组疗效和安全性维度数据。
- **【已有部分公开结果】（3 个产品）**：
  `difamilast`、`eblasakimab`、`apg777`。
  *验证结果*：疗效已公开发表，但安全性未有完整同试验对照分组数值，如实分类，避免误标为“暂无结果”。
- **【暂无公开关键结果】（10 个产品）**：
  `jaktinib`、`bempikibart`、`barzolvolimab`、`lutikizumab`、`cm326`、`ibi356`、`shr1905`、`tqh2722`、`skb575`、`anb032`。
  *检索闭环核验*：已逐一核查 PubMed、ClinicalTrials.gov、官方公告及多通道检索回执（`evidence/raw/wechat-*.json`）：
  - **杰克替尼 (Jaktinib)**：经检索确认截至数据截止日，AD 适应症 III 期试验仍在进行中，未检索到公开疗效/安全性数值，当前空值合规。
  - **TQH2722**：已闭合 II 期试验（NCT05970432）身份，检索结果显示仅有 I 期数据发布，II 期数值未见公开，标记为“检索未找到数值”。
  - **CM326 / IBI356 / SHR-1905 / SKB575 / Barzolvolimab / Lutikizumab**：均处于早期 I/II 期招募中或无结果披露。
  - **ANB032**：II 期未达主要终点提前终止，官方仅定性披露，无量化发生率。

---

## Evidence And Assumptions

### 1. 证据核验事实

1. **内容摘要唯一性与模型闭合**：
   - 候选文件路径：`.artifacts/a-data-matrix-recheck-candidate/research-content.json`
   - 计算得到的内容摘要 `content_digest`：`cae2c3383b04b1987e51d675a21a13e99a9ed8f03718f0704e4cb09356a78f74`
   - 通过 `FreshAResearchContent.model_validate()` 全量校验，Pydantic 合同与业务逻辑断言 100% 通过。
2. **本地原始证据 SHA-256 哈希固化**：
   - `gr1802-chictr2100051917-wiley-recovered.md`: `695860ce75c054e4a183e017994bfde9b0ee397d4ce219dcdca53bd0742b49c6`
   - `bempikibart-nct05509023-ctgov.json`: `267d14926fb73a96c18da07598b464997d90f8b184e7a77ebc7597d94d2da1aa`
   - `ivarmacitinib-nct04875169-pmc.xml`: `b8b4fbe27c3695b9e2d01463145aeb0deef0f477ffd55b6af2e422a1c3f50363`
   - `icp332-nct05702268-pubmed.xml`: `c17786f29a46ae43a61d97dfdd0edf42ecec397dac78f91c7bb062d167e10828`
   - `ssgj611-nct05544591-pmc.xml`: `4ae18e47fe2b94f1c97a7a5bc8aa2ca469145610ec1f25368a1fefc340ee79db`
   - `rezpegaldesleukin-nct06136741-sec-20250918.md`: `d4750e38605c317ff9871143890250cf4fbf2a3562692095f9c5d15a5198ec51`
   - `ak120-nct06035354-eadv2025.md`: `b231ff61543ad4aa65103c8ba265efca0f2dc4b5952f483c74676fe42e4726e6`
   - `eblasakimab-nct05158023-sec-2023.md`: `f7dbeea27ee34c2bb80cb8975877dae81ba7dd7a3dc1e2d8376c6665bf7304f5`
   - `apg777-nct06395948-sec-20250811.md`: `3f038f4201bebeea812d4fa552d7e9f3b1451f03ce3764835848bb447781bcf7`
   - `difamilast-phase3-pubmed.md`: `b5049ea26ef7f53a4ea84411130dca078f44ff53e82729e1db87bf59485b0d0a`
3. **自动化测试与合同回归**：
   - 运行针对性合同测试与合并验证（`test_curated_result_evidence_merge.py`、`test_evidence_audit_contracts.py`、`test_evidence_view.py`）共 37 项测试全量 Passed。

### 2. 显式假设与审计前提

- **数据截止基线**：研究事实严格截止于 `2026-07-31`（快照锁定时间 `2026-08-18`），在此基线后外部发生的变化不属于本数据包的回溯要求。
- **技术故障与事实缺失区分原则**：对于因外部网站反爬 403、大文件解析受限导致的获取障碍，记录为技术路径恢复（如从 Crossref/OpenAlex/SEC 镜像恢复），不得假定为无证据。
- **医学定性描述不可推断原则**：对未给出具体分组发生率的描述（如“无明显差异”、“耐受良好”），严格记为 `未公开` (`None`)，不假定为 0。

---

## Risks, Gaps, And Verification Needs

### 1. 识别的潜在风险点与控制措施

1. **安全性终点定义差异的医学解释**：
   - *风险*：Rezpegaldesleukin 报告的 TEAE 明确为“排除注射部位反应后的发生率”，而其它竞品多为全口径 TEAE。
   - *控制*：数据包已在术语字段中显式标明 `任何TEAE（不含注射部位反应）`，并在描述中保留来源注释，有效防止了读者产生偏倚误解。
2. **多周期试验的数据隔离**：
   - *风险*：Difamilast 的 4 周有效性与 52 周长期安全性容易在矩阵图生成时被误关联。
   - *控制*：候选包通过拆分 `pmid34710557` 与 `nct03961529` 两项试验，并在渲染逻辑中限定仅绘制同试验双组数据，确保不会出现跨试验绘图。

### 2. 建议 Codex 确认的决策点与验证动作

1. **不可变正式研究包生成**：基于已接受的 `cae2c3383b04b1987e51d675a21a13e99a9ed8f03718f0704e4cb09356a78f74` 内容摘要，生成包含 `scientific_review` (status: `accepted`) 的最终 `research-package.json`。
2. **多视口实机视觉验收**：由 Codex 执行 1024、1280、1440、1920 px 视口下的 Chromium 与 WebKit 实机核验，确保安全性热图无需左右拖拽即可完整显示。

---

## Recommended Next Step

1. **主会场采纳科学复核结论**：Codex 记录 `general_pi_antigravity` 的独立【接受】复核意见。
2. **生成正式不可变研究包**：合入科学复核接受元数据，固化正式不可变交付包。
3. **全工程回归与正式切流**：更新交付入口，执行全工程回归测试，完成正式发布。
