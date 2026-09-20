Round 2 is a targeted check of the v4 repairs only. I’ll verify the seven Codex items against the new candidate, local NICE extract, and coverage counts.接下来按 7 项逐条核：占位是否删净、NICE 绑定、canonical digest、修约政策、巴瑞替尼分母、他匹那罗夫术语，以及覆盖率重算。# Conference Participant Output: ci_phase5_a_values_science_review_v3 - general_grok46

## Boundary Check

- 同一会话续轮 2。只读。未改文件，未读其他参与者正文，未做外网核原 PDF，未做浏览器/视觉终验，不代替 Codex 最终接受。
- 复核对象：`.artifacts/a-values-matrix-fix-candidate-v4/research-content.json`。
- 辅助只读：`fixtures/positive/a-atopic-dermatitis/sources/lebrikizumab-nct04146363-nice-ta986.md`、`tapinarof-nct05014568-adoring1.md`、`curated-result-evidence.json` 中 NICE 源绑定、`src/ci_workflow/application/source_research_service.py` 的 `_digest` 定义。
- 原始 pretty-printed 文件 SHA-256：`988c1607e08c7f9747a6feb493dcdaf66b6ccd7c26cafefe96e956622196fa1a`。按本轮指示，**不**把它和应用层 canonical digest 当成冲突。

## Independent Work Product

### 本轮裁定：**PASS**

七项指定修复在 v4 上均已落实。未发现足以推翻这七项修复的残留阻断缺陷。下面按项给出证据。本 PASS 只覆盖指定修复集，不是整份 A 类报告的科学终验。

### 1. 14 条空占位 — PASS

14 个旧 `row_id` 在 v4 全文中计数均为 0（safety 行、facts、claims 皆无）：

`safe-lebrikizumab-治疗组-teae`、`safe-lebrikizumab-对照组-teae`、`safe-nemolizumab-治疗组-teae`、`safe-nemolizumab-对照组-teae`、`safe-abrocitinib-治疗组-teae`、`safe-abrocitinib-对照组-teae`、`safe-upadacitinib-治疗组-teae`、`safe-upadacitinib-对照组-teae`、`safe-baricitinib-治疗组-teae`、`safe-baricitinib-对照组-teae`、`safe-tapinarof-治疗组-teae`、`safe-tapinarof-对照组-teae`、`safe-roflumilast-cream-治疗组-teae`、`safe-roflumilast-cream-对照组-teae`。

上述 7 个产品现在各只剩 2 条 `任何TEAE`（治疗组+对照），全部 `已公开` 且带数值。对应 facts 均为 `reported_value`。无“已公开数值 / 未公开空行”并存。

非本项范围的残留：`difamilast` 仍同时有治疗组已公开 72.3% 与 `safe-difamilast-pmid34710557-teae-nr` 未公开空行。不在这 7 个产品内，不构成本轮 BLOCK。

### 2. 来布利珠单抗 NICE TA986 — PASS

| 字段 | v4 |
|---|---|
| 试验 | `nct04146363` |
| 窗 | `16周诱导期` |
| 治疗组 | 129/282（45.7%），250 mg Q2W |
| 对照 | 73/141（51.8%），安慰剂 |
| 算术 | 129/282=45.744…→45.7；73/141=51.773…→51.8，与一位小数闭合 |
| facts 源 | `nice-ta986-lebrikizumab-nct04146363` |
| locator | Table 42 / Overview of TEAEs through Week 16 / Any TEAE / 第 107 页 |
| 旧 Almirall / 128/282 / 72/141 | v4 中为 0 |

本地摘录 `sources/lebrikizumab-nct04146363-nice-ta986.md` SHA-256 `fae3cdf568744aa332bdb1ed6e1b049c310631a194781ce23a4710dc7297eb2a`，与 curated 清单 `content_sha256` 一致。Candidate 内嵌 `content_text` 与该文件 **仅差文件末尾一个换行**（630 vs 629 字节）；数字、NCT、表号相同。Claim `curated-result-claim_28abdf537e47697e6ea1a21f` 已写 129/282（45.7%）。

### 3. Digest 定义 — PASS（独立复算）

应用层 canonical digest（`json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"` 的 SHA-256）=

`3c42232e53194820e319696afc7c3e815300718efe3ec0e95028b26ab8d91080`

与指定摘要一致。原始文件哈希不同，按本轮定义不是缺陷。

### 4. 整数百分比保留 — PASS（按本轮政策）

| 行 | 存值 | n/N | 若改算 1 位小数 |
|---|---:|---|---:|
| 奈莫利珠单抗 30 mg | 50.0 | 306/616 | 49.7 |
| 奈莫利珠单抗安慰剂 | 45.0 | 146/321 | 45.5 |
| 阿布昔替尼 200 mg | 78.0 | 120/154 | 77.9 |
| 阿布昔替尼安慰剂 | 57.0 | 44/77 | 57.1 |
| 度普利尤单抗 Q2W | 73.0 | 167/229 | 72.9 |
| 度普利尤单抗安慰剂 | 65.0 | 145/222 | 65.3 |

n/N 仍单独可见，未被改成“人工一位小数”。与来布利珠单抗已闭合的 45.7/51.8 不是同一政策。本轮指示视为有意保留，不要求反算。

### 5. 巴瑞替尼无 n/N — PASS（按本轮产品规则）

仍为 58.0% / 54.0%，`numerator`/`denominator` 为 null。原文：“来源未同时给出精确事件人数，未反推分子。” 未发现反推人数。按本轮“公开来源只给率、允许显式缺 n/N”，不构成 BLOCK。

### 6. 他匹那罗夫 Any AEs → 任何TEAE — PASS（未找到矛盾来源）

- 规范术语：`任何TEAE`
- locator.row：`Any AEs`
- original_text：`任何AE为123/270（45.6%）` / `35/137（25.5%）`
- 本地摘录仍写“任何 AE”，并引用 PMID 38777187 与系统评价表 2

包内没有另一张表给出不同的 TEAE 人数来否定这次归并。在“主研究把安全性定义为 TEAE 发生率、表行写作 Any AEs、原文标签保留”的前提下，可以接受为受控同义，而不是跨定义偷换。本角色未读 PMID 38777187 全文。

### 7. 覆盖率（禁止把治疗组 20 说成双臂 20）

| 口径 | 计数 |
|---|---:|
| 产品全集 | 38 |
| 任意疗效数值 | **28/38** |
| 任意安全性数值 | **26/38** |
| 精确术语 `任何TEAE`、已公开、**治疗组**有数 | **20/38** |
| 精确术语 `任何TEAE`、已公开、**治疗组+对照双臂** | **19/38** |

治疗组 20：abrocitinib, amlitelimab, baricitinib, crisaborole, difamilast, dupilumab, etokimab, gr1802, icp-332, ivarmacitinib, lebrikizumab, nemolizumab, roflumilast-cream, ruxolitinib-cream, sim0718, ssgj-611, stapokibart, tapinarof, tralokinumab, upadacitinib。

双臂 19 = 上表去掉 **difamilast**（仅治疗组）。

`startswith('任何TEAE')` 为治疗组 22 / 双臂 21，多出 ak120（多剂量合并）和 rezpegaldesleukin（不含注射部位反应）。不得并入精确 20/19。

无疗效 10：jaktinib, bempikibart, barzolvolimab, lutikizumab, cm326, ibi356, shr1905, tqh2722, skb575, anb032。  
无任何安全性数值 12：上述 10 + eblasakimab + apg777。

## Evidence And Assumptions

**Evidence**

- 14 个占位 `row_id` 在 v4 全文为 0；7 产品各 2 条已公开 `任何TEAE`。
- 来布利珠单抗 129/282（45.7%）、73/141（51.8%），源 `nice-ta986-lebrikizumab-nct04146363`；Almirall/128/282/72/141 为 0。
- 本地 NICE 摘录 SHA `fae3cdf5…`；内嵌文本仅缺末尾 `\n`。
- Canonical digest 独立复算 = `3c42232e…`；原始文件 SHA = `988c1607…`。
- 奈莫利珠单抗/阿布昔替尼/度普利尤单抗保持来源整数百分比，n/N 仍在。
- 巴瑞替尼 58/54，无 n/N，原文声明未反推。
- 他匹那罗夫 locator 保留 `Any AEs`。
- 覆盖率 28 / 26 / 20（治疗组）/ 19（双臂）。

**Inference**

- 指定的 v3 阻断项（占位并存、来布利珠单抗错格、digest 定义混淆）在 v4 已关掉。
- 整数百分比与 n/N 并存是政策选择，不是新的串组。
- 他匹那罗夫归并在当前包内没有被第二份数字推翻。

**Uncertainty**

- 未打开 NICE 委员会 PDF 原件；只核了仓库摘录。
- 未读 ADORING 1 主报告全文，不能独立证明 Any AEs ≡ TEAE。
- 未跑分析快照的 `matrix_default` / 分母门槛；`gate_status=passed` 只是内容包字段。
- 克立硼罗 CT.gov 混合窗、司普奇拜单抗无分母谱系，不在本轮 7 项内，仍未关闭。

## Risks, Gaps, And Verification Needs

| 残留 | 级别 | 说明 |
|---|---|---|
| 精确总体 TEAE 双臂 19，不是 20 | 报告口径 | 不得把 20 个治疗组产品写成 20 个配对产品 |
| NICE 文件 SHA 含末尾换行，内嵌文本不含 | 非阻断 | 数字一致 |
| difamilast 已公开+未公开并存 | 非本轮 7 产品 | 若默认矩阵扫全部产品，仍可能歧义 |
| 巴瑞替尼无分母 | 本轮按规则放行 | 气泡图若强制分母，需产品层例外 |
| 他匹那罗夫 Any AEs | 未找到矛盾源 | 终验若要求主报告表头=TEAE，需补 PMID 38777187 原文 |
| 4/8/12/16 周同轴、JAK 高剂量默认 | 未在本轮指定 | 不作为本次 BLOCK |

**反对：** 用 20/38 暗示双臂总体 TEAE 已齐。  
**方案：** 对外只写“治疗组精确总体 TEAE 20/38；双臂配对 19/38（缺地法米拉斯对照）”。  
**给 Codex 的问题（不阻断本轮 7 项）：** 正式入口是否在本 PASS 后立即替换，还是仍要过视觉/分析快照？地法米拉斯对照空行是否也要 `supersede`？

**安全临时路径：** 指定修复集可以关闭。整包生成仍由 Codex 终验；在分析快照确认默认矩阵不再指向已删占位之前，不要声称热图已验收。

## Recommended Next Step

Codex 可将 **v4 指定 7 项修复标为已核过（PASS）**，digest 使用 `3c42232e53194820e319696afc7c3e815300718efe3ec0e95028b26ab8d91080`。覆盖率必须分开写 28 / 26 / **20 治疗组** / **19 双臂**。本角色 **不** 接受整份 A 类报告的最终科学或视觉通过。
